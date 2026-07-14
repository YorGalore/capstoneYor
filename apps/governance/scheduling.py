"""Cadence scheduler (REQ-SC-01, REQ-SC-02, REQ-SC-05) and the collection kill switch
(REQ-LC-03).

The platform can be deployed and still not monitor anything: collection, alerting, brief
generation and CIB detection were all management commands waiting for a human. This runs
them on a per-project cadence.

Deliberately a database-backed loop rather than Celery/Redis. The job set is small and
fixed, the cadences are minutes not milliseconds, and Postgres already gives us exactly
the primitive a scheduler needs — ``SELECT ... FOR UPDATE SKIP LOCKED`` — so two
scheduler replicas cannot run the same job twice. Adding a broker would add an operational
component and a failure mode without adding a capability.
"""
import logging

from django.db import transaction
from django.utils import timezone

from .models import ScheduledJob
from .services import record_audit_entry

logger = logging.getLogger(__name__)

COLLECTION_ENABLED_KEY = "collection.enabled"

# A dead upstream (expired token, network partition) must not be retried every cadence
# forever: that burns Apify quota, floods the log, and fixes nothing. Back off
# geometrically, but keep checking often enough to notice recovery within the hour.
BACKOFF_FACTOR = 2
MAX_BACKOFF_MINUTES = 60


def collection_enabled():
    """REQ-LC-03. Default on — a platform that stops collecting because a setting was
    never written would be a silent outage."""
    from .runtime import get_setting

    return (get_setting(COLLECTION_ENABLED_KEY) or "1").strip().lower() not in {
        "0", "false", "no", "off",
    }


def set_collection_enabled(enabled, actor):
    """Halt or resume all collection, platform-wide.

    Audited on purpose: stopping collection for an entire institution — or quietly
    restarting it — is exactly the kind of act that needs a name and a timestamp on it.
    """
    from .runtime import set_setting

    set_setting(COLLECTION_ENABLED_KEY, "1" if enabled else "0", updated_by=actor)
    record_audit_entry(
        actor_label=actor,
        action=("Mengaktifkan kembali koleksi data" if enabled else "Menghentikan koleksi data (kill switch)"),
        target="collection.enabled",
    )


# --- job handlers -----------------------------------------------------------------
# Each takes a Project and returns a short human-readable detail string. Anything raised
# is caught by the runner and recorded against the job.

def _run_collect(project):
    from . import apify, orchestrator

    token = apify.get_active_token()
    if not token:
        raise RuntimeError("Tidak ada token Apify aktif.")
    runs = orchestrator.run_apify_collection(project, token)
    items = sum(r.items_found for r in runs)
    return f"{len(runs)} sumber, {items} item"


def _run_evaluate_alerts(project):
    from apps.analytics import alerting

    triggered = alerting.evaluate_rules(project)
    return f"{len(triggered)} peringatan baru"


def _run_detect_coordination(project):
    from apps.analytics.models import PoliticalIssue
    from apps.coordination import detection

    flagged = 0
    for issue in PoliticalIssue.objects.filter(
        project=project, status=PoliticalIssue.STATUS_ACTIVE
    ):
        flagged += len(detection.detect(project, issue))
    return f"{flagged} klaster ditandai untuk tinjauan"


def _run_generate_brief(project):
    from apps.analytics import briefs

    brief_date = (timezone.now() - timezone.timedelta(days=1)).date()
    brief = briefs.generate(project, brief_date, triggered_by="Penjadwal")
    # Never auto-finalized: a scheduled brief is still a draft awaiting human review
    # (FR-30.2). The scheduler produces the draft; it does not speak for the institution.
    return f"Draf brief {brief_date} — {brief.issues.count()} isu"


def _run_purge_retention(project):
    from . import retention

    result = retention.purge(project, actor="Penjadwal")
    return f"{result['deleted']} dihapus, {result['protected']} dilindungi"


HANDLERS = {
    ScheduledJob.JOB_COLLECT: _run_collect,
    ScheduledJob.JOB_EVALUATE_ALERTS: _run_evaluate_alerts,
    ScheduledJob.JOB_DETECT_COORDINATION: _run_detect_coordination,
    ScheduledJob.JOB_GENERATE_BRIEF: _run_generate_brief,
    ScheduledJob.JOB_PURGE_RETENTION: _run_purge_retention,
}

# Jobs the kill switch stops. Halting collection must not also blind the analysts:
# alerting and briefs run over data already held, and that is what people need most
# during the incident that made someone hit the switch.
COLLECTION_JOBS = {ScheduledJob.JOB_COLLECT}


def due_jobs(now=None):
    now = now or timezone.now()
    return ScheduledJob.objects.filter(enabled=True, next_run_at__lte=now).select_related(
        "project"
    )


def _reschedule(job, now, failed):
    """Set the next run.

    Always forward from *now*, never by adding cadences to the missed slot. If the
    scheduler was down for a day, a 15-minute job is 96 windows overdue; replaying them
    would fire 96 collection runs at once — a self-inflicted stampede against Apify and
    96 duplicate briefs. Run once, then resume the normal cadence.
    """
    minutes = job.cadence_minutes
    if failed:
        minutes = min(
            job.cadence_minutes * (BACKOFF_FACTOR ** job.consecutive_failures),
            MAX_BACKOFF_MINUTES,
        )
    job.next_run_at = now + timezone.timedelta(minutes=minutes)


def run_job(job):
    """Execute one job, recording the outcome on the job itself.

    Never raises: a single broken job must not take down the scheduler loop and with it
    every other project's monitoring.
    """
    now = timezone.now()

    if job.job_type in COLLECTION_JOBS and not collection_enabled():
        # Checked here, at the moment work is about to happen — not when the job was
        # scheduled. A kill switch has to work when someone is panicking.
        job.last_status = ScheduledJob.STATUS_SKIPPED
        job.last_detail = "Koleksi dihentikan (kill switch aktif)"
        job.last_run_at = now
        _reschedule(job, now, failed=False)
        job.save()
        return job

    handler = HANDLERS.get(job.job_type)
    try:
        if handler is None:
            raise RuntimeError(f"Jenis pekerjaan tidak dikenal: {job.job_type}")
        detail = handler(job.project)
    except Exception as exc:
        logger.exception("Pekerjaan terjadwal gagal: %s (%s)", job.job_type, job.project_id)
        job.consecutive_failures += 1
        job.last_status = ScheduledJob.STATUS_FAILED
        job.last_error = str(exc)[:500]
        job.last_detail = ""
        job.last_run_at = now
        _reschedule(job, now, failed=True)
        job.save()
        return job

    job.consecutive_failures = 0
    job.last_status = ScheduledJob.STATUS_OK
    job.last_error = ""
    job.last_detail = (detail or "")[:255]
    job.last_run_at = now
    _reschedule(job, now, failed=False)
    job.save()
    return job


def run_due(now=None):
    """Run every job whose time has come. Returns the jobs that were run."""
    now = now or timezone.now()
    ran = []

    for candidate in list(due_jobs(now).values_list("pk", flat=True)):
        with transaction.atomic():
            # SKIP LOCKED is what makes a second scheduler replica safe: it takes the
            # jobs this one has not claimed rather than blocking on them or, worse,
            # running the same collection twice and paying Apify twice for it.
            job = (
                ScheduledJob.objects.select_for_update(skip_locked=True)
                .filter(pk=candidate, enabled=True, next_run_at__lte=now)
                .select_related("project")
                .first()
            )
            if job is None:
                continue
            ran.append(run_job(job))

    return ran
