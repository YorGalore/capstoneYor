from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.core.models import AnalystProfile, Platform, Province, Regency
from apps.core.seed import seed_core


class SeedCoreTest(TestCase):
    def test_seed_core_creates_reference_data(self):
        tenant, project = seed_core()
        self.assertEqual(tenant.name, "Kemenko PMK")
        self.assertEqual(project.tenant, tenant)
        self.assertEqual(Platform.objects.count(), 7)
        self.assertGreaterEqual(Province.objects.count(), 10)
        self.assertTrue(Regency.objects.filter(province__name="Maluku").exists())
        demo_user = get_user_model().objects.get(username="dewi.anjani")
        profile = AnalystProfile.objects.get(user=demo_user)
        # Political monitoring is a separate, compliance-approved grant recorded in
        # governance (FR-29.1) — seeding core alone must not confer it.
        self.assertFalse(profile.has_political_monitoring_permission)

    def test_seed_core_is_idempotent(self):
        seed_core()
        seed_core()
        self.assertEqual(Platform.objects.count(), 7)
