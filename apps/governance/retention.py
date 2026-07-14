"""Data retention purge (REQ-LC-01, REQ-LC-02, REQ-LC-04).

This is the only routine in the platform that destroys data, and the scheduler runs it
unattended. Two rules follow from that:

1. **No policy means no deletion.** Silently destroying a ministry's archive because
   nobody ever configured a retention window would be indefensible. Retention is off
   until someone sets it, deliberately.

2. **An open investigation is never purged.** A flagged coordination cluster is a case a
   human is still reviewing. Deleting the posts under it because they crossed a date
   boundary destroys the evidence and leaves the cluster pointing at nothing.
"""
from django.utils import timezone

from apps.analytics.models import Mention
from apps.coordination.models import ClusterAccount, CoordinationCluster

from .runtime import get_setting, set_setting
from .services import record_audit_entry

RETENTION_DAYS_KEY = "retention.days"
# 0 means "no retention policy configured" — keep everything.
RETENTION_DISABLED = 0

# Distinct prefix so a deletion can be told apart from a mere policy change when reading
# the audit log back — they are very different acts.
PURGE_ACTION = "Purge retensi"


def retention_days():
    raw = get_setting(RETENTION_DAYS_KEY)
    try:
        return max(int(raw), RETENTION_DISABLED)
    except (TypeError, ValueError):
        return RETENTION_DISABLED


def set_retention_days(days, actor):
    set_setting(RETENTION_DAYS_KEY, str(int(days)), updated_by=actor)
    record_audit_entry(
        actor_label=actor,
        action=f"Menetapkan kebijakan retensi data: {days} hari",
        target=RETENTION_DAYS_KEY,
    )


def _protected_mention_ids(project, candidates):
    """Mentions that are evidence in an open coordination investigation.

    Scoped to the accounts actually named in a still-flagged cluster on the same issue,
    rather than blanket-protecting the whole issue: over-retention is its own compliance
    problem, and REQ-LC exists to make the platform hold less, not more.
    """
    # PoliticalIssue carries no project FK (it is global today), so clusters cannot be
    # filtered by project here. That is safe: `candidates` is already scoped to this
    # project, so intersecting against it cannot protect another tenant's rows.
    open_clusters = CoordinationCluster.objects.filter(
        status=CoordinationCluster.STATUS_FLAGGED
    )
    if not open_clusters.exists():
        return set()

    protected = set()
    for cluster in open_clusters.select_related("issue"):
        handles = ClusterAccount.objects.filter(cluster=cluster).values_list("handle", flat=True)
        protected.update(
            candidates.filter(
                issue=cluster.issue, author__handle__in=list(handles)
            ).values_list("pk", flat=True)
        )
    return protected


def purge(project, now=None, dry_run=False, actor="Sistem"):
    """Delete mentions past the retention window for one project.

    Returns ``{"deleted", "protected", "cutoff"}``. With ``dry_run`` the counts are what
    *would* happen and nothing is removed — the only safe way to look before you leap on
    an unrecoverable operation.
    """
    now = now or timezone.now()
    days = retention_days()
    if days == RETENTION_DISABLED:
        return {"deleted": 0, "protected": 0, "cutoff": None}

    cutoff = now - timezone.timedelta(days=days)
    candidates = Mention.objects.filter(project=project, posted_at__lt=cutoff)

    protected = _protected_mention_ids(project, candidates)
    deletable = candidates.exclude(pk__in=protected)
    count = deletable.count()

    if dry_run:
        return {"deleted": count, "protected": len(protected), "cutoff": cutoff}

    deletable.delete()

    if count or protected:
        record_audit_entry(
            actor_label=actor,
            action=(
                f"{PURGE_ACTION} ({days} hari): {count} sebutan dihapus, "
                f"{len(protected)} dilindungi (investigasi terbuka)"
            ),
            target=f"project:{project.pk}",
        )

    return {"deleted": count, "protected": len(protected), "cutoff": cutoff}
