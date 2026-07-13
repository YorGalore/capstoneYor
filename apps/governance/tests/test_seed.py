from django.test import TestCase

from apps.core.seed import seed_core
from apps.governance.models import (
    AuditLogEntry, MonitoredDomain, PlatformIntegration, PoliticalMonitoringPermission,
)
from apps.governance.seed import seed_governance


class SeedGovernanceTest(TestCase):
    def test_seed_governance_creates_expected_rows(self):
        tenant, project = seed_core()
        seed_governance(tenant)

        self.assertEqual(PlatformIntegration.objects.count(), 5)
        self.assertFalse(PlatformIntegration.objects.get(platform__slug="facebook").is_active)
        self.assertEqual(MonitoredDomain.objects.count(), 4)
        self.assertGreaterEqual(
            PoliticalMonitoringPermission.objects.filter(active=True).count(), 3
        )
        self.assertEqual(AuditLogEntry.objects.count(), 10)
        self.assertEqual(
            AuditLogEntry.objects.filter(action__icontains="dikecualikan").count(), 2
        )

    def test_seed_governance_is_idempotent(self):
        tenant, project = seed_core()
        seed_governance(tenant)
        seed_governance(tenant)
        self.assertEqual(PlatformIntegration.objects.count(), 5)
