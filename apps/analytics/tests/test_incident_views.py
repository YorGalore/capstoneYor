from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.analytics.models import Incident, OPD
from apps.core.models import AnalystProfile, Project, Tenant


class IncidentBoardAccessTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        user = get_user_model().objects.create_user(username="analis", password="rahasia123")
        AnalystProfile.objects.create(
            user=user, tenant=self.tenant, role=AnalystProfile.ROLE_ANALYST
        )
        self.client.force_login(user)

    def test_board_lists_confirmed_incidents(self):
        Incident.objects.create(
            project=self.project, title="Jalan Rusak", severity=Incident.SEVERITY_HIGH,
            is_confirmed=True,
        )
        response = self.client.get(reverse("analytics:insiden"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jalan Rusak")

    def test_board_hides_another_tenants_incidents(self):
        other = Tenant.objects.create(name="Instansi B")
        other_project = Project.objects.create(tenant=other, name="Proyek B")
        Incident.objects.create(
            project=other_project, title="Rahasia Tetangga",
            severity=Incident.SEVERITY_HIGH, is_confirmed=True,
        )
        response = self.client.get(reverse("analytics:insiden"))
        self.assertNotContains(response, "Rahasia Tetangga")

    def test_board_separates_candidates_from_confirmed(self):
        Incident.objects.create(
            project=self.project, title="Sudah Dikonfirmasi",
            severity=Incident.SEVERITY_HIGH, is_confirmed=True,
        )
        Incident.objects.create(
            project=self.project, title="Masih Kandidat",
            severity=Incident.SEVERITY_LOW, is_confirmed=False,
        )
        response = self.client.get(reverse("analytics:insiden"))
        self.assertEqual(len(response.context["board"]["confirmed"]), 1)
        self.assertEqual(len(response.context["board"]["candidates"]), 1)

    def test_board_filters_by_severity(self):
        Incident.objects.create(
            project=self.project, title="Kritis", severity=Incident.SEVERITY_CRITICAL,
            is_confirmed=True,
        )
        Incident.objects.create(
            project=self.project, title="Ringan", severity=Incident.SEVERITY_LOW,
            is_confirmed=True,
        )
        response = self.client.get(reverse("analytics:insiden"), {"severity": "critical"})
        self.assertContains(response, "Kritis")
        self.assertNotContains(response, ">Ringan<")
