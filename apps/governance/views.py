from django.shortcuts import render
from django.utils import timezone

from .models import (
    ApifyCredential, AuditLogEntry, MonitoredDomain, PlatformIntegration,
    PoliticalMonitoringPermission, PolicyAcknowledgment,
)


def konfigurasi(request):
    integrations = PlatformIntegration.objects.select_related("platform").order_by("platform__display_name")
    credential = ApifyCredential.objects.order_by("-last_verified_at").first()
    domains = MonitoredDomain.objects.order_by("domain")
    return render(request, "governance/konfigurasi.html", {
        "active_nav": "konfigurasi",
        "integrations": integrations,
        "credential": credential,
        "domains": domains,
    })


def pengawasan(request):
    from apps.core.models import AnalystProfile

    permissions = PoliticalMonitoringPermission.objects.filter(active=True).select_related("user")
    total_users = AnalystProfile.objects.count()
    political_query_count = AuditLogEntry.objects.filter(
        action__icontains="kueri", timestamp__gte=timezone.now() - timezone.timedelta(days=30)
    ).count()
    excluded_profile_count = AuditLogEntry.objects.filter(action__icontains="dikecualikan").count()
    audit_entries = AuditLogEntry.objects.all()[:20]
    policy_ack = PolicyAcknowledgment.objects.order_by("-approved_at").first()

    return render(request, "governance/pengawasan.html", {
        "active_nav": "pengawasan",
        "permissions": permissions,
        "permission_count": permissions.count(),
        "total_users": total_users,
        "political_query_count": political_query_count,
        "excluded_profile_count": excluded_profile_count,
        "audit_entries": audit_entries,
        "policy_ack": policy_ack,
    })
