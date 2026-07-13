from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.core.models import Platform, Tenant
from apps.governance.models import (
    AuditLogEntry, MonitoredDomain, PlatformIntegration,
    PoliticalMonitoringPermission, PolicyAcknowledgment,
)


class GovernanceModelsTest(TestCase):
    def test_platform_integration_str(self):
        platform = Platform.objects.create(
            slug="facebook", display_name="Facebook", method=Platform.METHOD_APIFY
        )
        integration = PlatformIntegration.objects.create(
            platform=platform, method=PlatformIntegration.METHOD_APIFY, is_active=False
        )
        self.assertIn("nonaktif", str(integration))

    def test_monitored_domain_default_status(self):
        domain = MonitoredDomain.objects.create(domain="kompas.com", adapter="generik-berita")
        self.assertEqual(domain.status, MonitoredDomain.STATUS_ACTIVE)

    def test_audit_log_orders_most_recent_first(self):
        first = AuditLogEntry.objects.create(actor_label="Sistem", action="A", target="X")
        second = AuditLogEntry.objects.create(actor_label="Sistem", action="B", target="Y")
        self.assertEqual(list(AuditLogEntry.objects.all()), [second, first])

    def test_policy_acknowledgment(self):
        tenant = Tenant.objects.create(name="Kemenko PMK")
        ack = PolicyAcknowledgment.objects.create(
            tenant=tenant, approved_by="Tenant Admin",
            approved_at=timezone.now(), next_review_at=timezone.now() + timezone.timedelta(days=365),
        )
        self.assertEqual(ack.tenant, tenant)

    def test_political_monitoring_permission(self):
        user = get_user_model().objects.create_user(username="siti.rahmawati")
        permission = PoliticalMonitoringPermission.objects.create(
            user=user, approved_by="R. Hartono (Kepatuhan)", approved_at=timezone.now(),
        )
        self.assertTrue(permission.active)
