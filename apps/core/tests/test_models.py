from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.core.models import AnalystProfile, Platform, Province, Regency, Project, Tenant


class CoreModelsTest(TestCase):
    def test_tenant_project_str(self):
        tenant = Tenant.objects.create(name="Kemenko PMK")
        project = Project.objects.create(tenant=tenant, name="Program Pangan Rakyat")
        self.assertEqual(str(tenant), "Kemenko PMK")
        self.assertEqual(str(project), "Program Pangan Rakyat")

    def test_platform_str(self):
        platform = Platform.objects.create(
            slug="x", display_name="X (Twitter)", method=Platform.METHOD_INTERNAL
        )
        self.assertEqual(str(platform), "X (Twitter)")

    def test_province_and_regency(self):
        province = Province.objects.create(name="Maluku", population_online=800000)
        regency = Regency.objects.create(province=province, name="Kota Ambon")
        self.assertEqual(str(regency), "Kota Ambon, Maluku")

    def test_analyst_profile(self):
        tenant = Tenant.objects.create(name="Kemenko PMK")
        user = get_user_model().objects.create_user(
            username="dewi.anjani", first_name="Dewi", last_name="Anjani"
        )
        profile, _ = AnalystProfile.objects.update_or_create(
            user=user,
            defaults={"tenant": tenant, "role_label": "Analis Humas"},
        )
        self.assertIn("Analis Humas", str(profile))

    def test_political_monitoring_flag_is_derived_from_the_governance_grant(self):
        from django.utils import timezone

        from apps.governance.models import PoliticalMonitoringPermission

        tenant = Tenant.objects.create(name="Kemenko PMK")
        user = get_user_model().objects.create_user(username="analis.satu")
        profile, _ = AnalystProfile.objects.update_or_create(
            user=user, defaults={"tenant": tenant}
        )
        self.assertFalse(profile.has_political_monitoring_permission)

        grant = PoliticalMonitoringPermission.objects.create(
            user=user, approved_by="Kepatuhan", approved_at=timezone.now(), active=True
        )
        self.assertTrue(profile.has_political_monitoring_permission)

        # Revoking the grant must immediately revoke the displayed flag too.
        grant.active = False
        grant.save()
        self.assertFalse(profile.has_political_monitoring_permission)

    def test_new_user_automatically_gets_an_analyst_profile(self):
        Tenant.objects.create(name="Kemenko PMK")
        user = get_user_model().objects.create_user(username="baru.pengguna")
        self.assertTrue(AnalystProfile.objects.filter(user=user).exists())
