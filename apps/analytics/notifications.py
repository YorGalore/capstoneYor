"""Outbound notification delivery (FR-12.2).

``alerting`` records that a rule breached; this module is the Notification
service that actually tells someone. Every attempt — sent, failed, or skipped —
is persisted as a NotificationDelivery so what left the platform is auditable.

Delivery must never take down the caller: a broken SMTP relay while an alert is
firing is precisely the moment the alert itself still has to be recorded, so
each channel handler swallows and logs its own failure.
"""
import json
import logging
import urllib.request

from django.conf import settings
from django.core.mail import send_mail

from apps.core.models import AnalystProfile

from .models import (
    AlertRule, BrowserPushSubscription, DailyBrief, NotificationDelivery,
)

logger = logging.getLogger(__name__)

WEBHOOK_URL_KEY = "alerts.webhook_url"
WEBHOOK_TIMEOUT_SECONDS = 10


def recipient_emails(project):
    """Email addresses of the tenant's analysts — the alert audience."""
    return sorted(
        AnalystProfile.objects.filter(tenant=project.tenant)
        .exclude(user__email="")
        .values_list("user__email", flat=True)
        .distinct()
    )


def _record(project, kind, channel, subject, recipients, status, detail="", alert=None, brief=None):
    return NotificationDelivery.objects.create(
        project=project, kind=kind, channel=channel, subject=subject[:255],
        recipients=list(recipients), status=status, detail=detail[:500],
        alert=alert, brief=brief,
    )


def _send_email(subject, body, recipients):
    """Returns (status, detail)."""
    if not recipients:
        return NotificationDelivery.STATUS_SKIPPED, "Tidak ada penerima dengan alamat email."
    backend = getattr(settings, "EMAIL_BACKEND", "")
    if backend == "django.core.mail.backends.console.EmailBackend":
        return (
            NotificationDelivery.STATUS_SKIPPED,
            "Backend email masih console; SMTP belum dikonfigurasi.",
        )
    try:
        send_mail(
            subject, body,
            getattr(settings, "DEFAULT_FROM_EMAIL", None) or "pantau@localhost",
            recipients, fail_silently=False,
        )
        return NotificationDelivery.STATUS_SENT, f"{len(recipients)} penerima."
    except Exception as exc:
        logger.exception("Pengiriman email notifikasi gagal")
        return NotificationDelivery.STATUS_FAILED, str(exc)


def _send_webhook(payload):
    """POST the payload to the operator-configured webhook URL. Returns (status, detail, url)."""
    from apps.governance.runtime import get_setting

    url = (get_setting(WEBHOOK_URL_KEY) or "").strip()
    if not url:
        return (
            NotificationDelivery.STATUS_SKIPPED,
            f'Runtime setting "{WEBHOOK_URL_KEY}" belum dikonfigurasi.',
            url,
        )
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=WEBHOOK_TIMEOUT_SECONDS) as response:
            return NotificationDelivery.STATUS_SENT, f"HTTP {response.status}", url
    except Exception as exc:
        logger.exception("Pengiriman webhook notifikasi gagal")
        return NotificationDelivery.STATUS_FAILED, str(exc), url


def _send_push(project, payload):
    """Deliver standards-based Web Push to browsers that explicitly opted in."""
    private_key = getattr(settings, "WEBPUSH_VAPID_PRIVATE_KEY", "")
    contact = getattr(settings, "WEBPUSH_VAPID_CONTACT", "")
    subscriptions = list(
        BrowserPushSubscription.objects.filter(
            project=project, user__is_active=True, is_active=True
        ).select_related("user")
    )
    recipients = [subscription.masked_endpoint for subscription in subscriptions]
    if not subscriptions:
        return (
            NotificationDelivery.STATUS_SKIPPED,
            "Belum ada browser pengguna yang mengaktifkan notifikasi.",
            recipients,
        )
    if not private_key or not contact:
        return (
            NotificationDelivery.STATUS_SKIPPED,
            "WEBPUSH_VAPID_PRIVATE_KEY/CONTACT belum dikonfigurasi.",
            recipients,
        )

    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        return (
            NotificationDelivery.STATUS_FAILED,
            "Dependensi pywebpush belum terpasang.",
            recipients,
        )

    sent = 0
    failures = []
    for subscription in subscriptions:
        try:
            webpush(
                subscription_info=subscription.subscription_info,
                data=json.dumps(payload, ensure_ascii=False),
                vapid_private_key=private_key,
                vapid_claims={"sub": contact},
                ttl=300,
            )
            sent += 1
        except WebPushException as exc:
            response = getattr(exc, "response", None)
            if response is not None and response.status_code in (404, 410):
                subscription.is_active = False
                subscription.save(update_fields=["is_active", "updated_at"])
            failures.append(str(exc))
        except Exception as exc:
            failures.append(str(exc))

    if sent:
        detail = f"{sent}/{len(subscriptions)} browser menerima notifikasi."
        if failures:
            detail += f" {len(failures)} gagal."
        return NotificationDelivery.STATUS_SENT, detail, recipients
    return (
        NotificationDelivery.STATUS_FAILED,
        (failures[0] if failures else "Semua pengiriman Web Push gagal.")[:500],
        recipients,
    )


def deliver_alert(alert):
    """Deliver one triggered Alert over its rule's channel. Never raises."""
    project = alert.project
    subject = f"[PANTAU] {alert.get_severity_display()}: {alert.title}"
    body = (
        f"{alert.detail}\n\n"
        f"Proyek: {project.name}\n"
        f"Terpicu: {alert.triggered_at:%d %b %Y %H:%M %Z}\n"
        f"Aturan: {alert.rule.name}"
    )

    channel = alert.rule.channel
    if channel == AlertRule.CHANNEL_EMAIL:
        recipients = recipient_emails(project)
        status, detail = _send_email(subject, body, recipients)
        return _record(
            project, NotificationDelivery.KIND_ALERT, channel, subject,
            recipients, status, detail, alert=alert,
        )

    if channel == AlertRule.CHANNEL_WEBHOOK:
        status, detail, url = _send_webhook({
            "kind": "alert",
            "severity": alert.severity,
            "title": alert.title,
            "detail": alert.detail,
            "project": project.name,
            "triggered_at": alert.triggered_at.isoformat(),
        })
        return _record(
            project, NotificationDelivery.KIND_ALERT, channel, subject,
            [url] if url else [], status, detail, alert=alert,
        )

    if channel == AlertRule.CHANNEL_PUSH:
        status, detail, recipients = _send_push(project, {
            "kind": "alert",
            "title": subject,
            "body": alert.detail,
            "severity": alert.severity,
            "url": "/insiden/",
            "triggered_at": alert.triggered_at.isoformat(),
        })
        return _record(
            project, NotificationDelivery.KIND_ALERT, channel, subject,
            recipients, status, detail, alert=alert,
        )

    return _record(
        project, NotificationDelivery.KIND_ALERT, channel, subject, [],
        NotificationDelivery.STATUS_FAILED,
        f"Kanal notifikasi tidak dikenal: {channel}", alert=alert,
    )


def brief_already_sent(brief):
    return NotificationDelivery.objects.filter(
        brief=brief,
        kind=NotificationDelivery.KIND_BRIEF,
        status=NotificationDelivery.STATUS_SENT,
    ).exists()


def send_brief(brief):
    """Email a finalized daily brief to the tenant's analysts. Never raises."""
    project = brief.project
    subject = f"[PANTAU] Brief Eksekutif Harian — {brief.brief_date:%d %B %Y}"

    if brief.status != DailyBrief.STATUS_FINAL:
        return _record(
            project, NotificationDelivery.KIND_BRIEF, AlertRule.CHANNEL_EMAIL, subject,
            [], NotificationDelivery.STATUS_SKIPPED,
            "Brief belum final — hanya brief final yang didistribusikan.", brief=brief,
        )

    sections = []
    for index, item in enumerate(brief.issues.all(), start=1):
        sections.append(
            f"{index}. {item.title} (risiko {item.risk_level}, "
            f"{item.mention_count} sebutan, {item.negative_pct}% negatif)\n{item.content}"
        )
    body = (
        f"Brief Eksekutif Harian {brief.brief_date:%d %B %Y} — {project.name}\n"
        f"Difinalisasi oleh {brief.finalized_by}.\n\n" + "\n\n".join(sections)
    )

    recipients = recipient_emails(project)
    status, detail = _send_email(subject, body, recipients)
    return _record(
        project, NotificationDelivery.KIND_BRIEF, AlertRule.CHANNEL_EMAIL, subject,
        recipients, status, detail, brief=brief,
    )
