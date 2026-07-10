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
        profile = AnalystProfile.objects.create(
            user=user, tenant=tenant, role_label="Analis Humas",
            has_political_monitoring_permission=True,
        )
        self.assertIn("Analis Humas", str(profile))
