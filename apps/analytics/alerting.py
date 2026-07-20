"""Alert rule evaluation engine (FR-12).

Evaluates each active rule against a rolling window of mentions and raises an
Alert when its condition is breached. Every triggered alert is persisted with its
rule, timestamp, and the numbers that caused it, so it can be reviewed after the
fact (FR-12.3). Delivery (email/push/webhook, FR-12.2) is a separate concern —
this module records the trigger; the Notification service sends it.
"""
from django.db.models import Count, Q
from django.utils import timezone

from .models import Alert, AlertRule, Mention


def _window_qs(project, rule):
    since = timezone.now() - timezone.timedelta(minutes=rule.window_minutes)
    return Mention.objects.filter(project=project, posted_at__gte=since)


def _evaluate(project, rule):
    """Return (breached, detail, severity) for one rule."""
    qs = _window_qs(project, rule)

    if rule.condition_type == AlertRule.CONDITION_NEGATIVE_RATIO:
        row = qs.aggregate(
            total=Count("id"),
            negative=Count("id", filter=Q(sentiment=Mention.SENTIMENT_NEGATIVE)),
        )
        total = row["total"]
        if not total:
            return False, "", Alert.SEVERITY_INFO
        ratio = row["negative"] / total
        if ratio < rule.threshold:
            return False, "", Alert.SEVERITY_INFO
        pct = round(ratio * 100)
        severity = Alert.SEVERITY_CRITICAL if ratio >= 0.8 else Alert.SEVERITY_WARNING
        return (
            True,
            f"Rasio negatif {pct}% dari {total} sebutan dalam {rule.window_minutes} menit "
            f"(ambang {round(rule.threshold * 100)}%).",
            severity,
        )

    if rule.condition_type == AlertRule.CONDITION_VOLUME_SPIKE:
        total = qs.count()
        if total < rule.threshold:
            return False, "", Alert.SEVERITY_INFO
        return (
            True,
            f"{total} sebutan dalam {rule.window_minutes} menit "
            f"(ambang {int(rule.threshold)}).",
            Alert.SEVERITY_WARNING,
        )

    return False, "", Alert.SEVERITY_INFO


def evaluate_rules(project, issue=None):
    """Evaluate the project's active rules; raise and return newly triggered Alerts."""
    if issue is not None and issue.project_id != project.pk:
        raise ValueError("The alert issue must belong to the evaluated project.")

    triggered = []
    for rule in AlertRule.objects.filter(project=project, is_active=True):
        breached, detail, severity = _evaluate(project, rule)
        if not breached:
            continue
        # Don't re-raise a rule that is already firing and unresolved.
        if Alert.objects.filter(
            project=project, rule=rule, status=Alert.STATUS_ACTIVE
        ).exists():
            continue

        alert = Alert.objects.create(
            project=project,
            rule=rule,
            issue=issue,
            severity=severity,
            title=rule.name,
            detail=detail,
            triggered_at=timezone.now(),
            status=Alert.STATUS_ACTIVE,
        )
        # Deliver over the rule's channel (FR-12.2). Lazy import: notifications
        # pulls in mail/webhook machinery this module otherwise never needs.
        from . import notifications

        notifications.deliver_alert(alert)
        triggered.append(alert)
    return triggered
