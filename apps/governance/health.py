"""Collector health (REQ-CS-07).

The worst failure this platform has is a silently dead collector: the dashboards keep
rendering, the numbers stay plausible, and nobody notices that no new data has arrived
for a week. Decisions then get made on a frozen picture of public opinion.

So health is not just "did the last run raise an error". A collector that reports success
and returns nothing, or has not run at all, is also broken — and that is the failure mode
that hides.
"""
from django.utils import timezone

from .models import CollectionRun

HEALTHY = "healthy"
STALE = "stale"
DEGRADED = "degraded"
DOWN = "down"

STATUS_LABELS = {
    HEALTHY: "Sehat",
    STALE: "Tidak ada data baru",
    DEGRADED: "Terganggu",
    DOWN: "Mati",
}

DOWN_AFTER_FAILURES = 3
# Longer than the slowest sensible cadence, so a normal gap between runs does not read
# as an outage, but short enough that a day-long silence is caught the same day.
STALE_AFTER_MINUTES = 12 * 60

# How far back to look when scoring a source.
WINDOW = 50


def _classify(consecutive_failures, last_success_at, now):
    if consecutive_failures >= DOWN_AFTER_FAILURES:
        return DOWN
    if last_success_at is None:
        return DOWN
    if consecutive_failures > 0:
        return DEGRADED
    age_minutes = (now - last_success_at).total_seconds() / 60
    if age_minutes > STALE_AFTER_MINUTES:
        # Nothing errored. It just stopped. This is the one that gets missed.
        return STALE
    return HEALTHY


def collection_health(now=None, project=None):
    """Per-source health, newest activity first. Sources that have never run are absent
    rather than invented — reporting a status for a collector that was never configured
    would be a fabrication."""
    now = now or timezone.now()
    report = []

    run_queryset = CollectionRun.objects.all()
    if project is not None:
        run_queryset = run_queryset.filter(project=project)
    sources = run_queryset.values_list("source", flat=True).distinct()
    for source in sorted(sources):
        runs = list(
            run_queryset.filter(source=source).order_by("-started_at")[:WINDOW]
        )
        if not runs:
            continue

        # A skipped run is normal backpressure (the previous cycle was still in flight),
        # not an error, so it neither breaks nor extends a failure streak.
        graded = [r for r in runs if r.status != CollectionRun.STATUS_SKIPPED]

        consecutive_failures = 0
        for r in graded:
            if r.status != CollectionRun.STATUS_FAILED:
                break
            consecutive_failures += 1

        last_success = next(
            (r for r in graded if r.status == CollectionRun.STATUS_COMPLETED), None
        )
        last_failure = next(
            (r for r in graded if r.status == CollectionRun.STATUS_FAILED), None
        )
        completed = [r for r in graded if r.status == CollectionRun.STATUS_COMPLETED]

        last_success_at = last_success.finished_at or last_success.started_at if last_success else None

        status = _classify(consecutive_failures, last_success_at, now)
        report.append({
            "source": source,
            "status": status,
            "status_label": STATUS_LABELS[status],
            "consecutive_failures": consecutive_failures,
            "last_success_at": last_success_at,
            "last_run_at": runs[0].finished_at or runs[0].started_at,
            "last_error": last_failure.error if last_failure else "",
            "success_rate": round(len(completed) / len(graded), 2) if graded else 0.0,
            "items_last_success": last_success.items_found if last_success else 0,
            "runs_considered": len(runs),
        })

    return report
