from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.analytics.models import Incident, IncidentEvent, OPD
from apps.core.models import AnalystProfile, Project, Tenant


class IncidentBoardAccessTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        user = get_user_model().objects.create_user(username="analis", password="rahasia123")
        # A post_save signal already auto-creates a profile for a new user when a
        # Tenant exists, so create() would violate the OneToOne constraint. Every
        # other test module in this codebase uses update_or_create here.
        AnalystProfile.objects.update_or_create(
            user=user,
            defaults={"tenant": self.tenant, "role": AnalystProfile.ROLE_ANALYST},
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


class IncidentActionTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        user = get_user_model().objects.create_user(
            username="operator", password="rahasia123", first_name="Operator", last_name="Satu"
        )
        # A post_save signal already auto-creates a profile for a new user when a
        # Tenant exists, so create() would violate the OneToOne constraint. Every
        # other test module in this codebase uses update_or_create here.
        AnalystProfile.objects.update_or_create(
            user=user,
            defaults={"tenant": self.tenant, "role": AnalystProfile.ROLE_ANALYST},
        )
        self.client.force_login(user)
        self.opd = OPD.objects.create(
            project=self.project, name="Dinas Pekerjaan Umum", slug="pu", abbr="PU"
        )
        self.incident = Incident.objects.create(
            project=self.project, title="Jalan Rusak", severity=Incident.SEVERITY_HIGH,
        )

    def test_promote_confirms_the_candidate(self):
        response = self.client.post(
            reverse("analytics:insiden_promote", args=[self.incident.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.incident.refresh_from_db()
        self.assertTrue(self.incident.is_confirmed)

    def test_assign_records_the_acting_user_not_the_system(self):
        self.client.post(
            reverse("analytics:insiden_assign", args=[self.incident.pk]),
            {"opd": self.opd.pk},
        )
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.assigned_opd, self.opd)
        event = self.incident.events.filter(kind=IncidentEvent.KIND_ASSIGNED).last()
        self.assertEqual(event.logged_by, "Operator Satu")

    def test_invalid_transition_is_refused_without_a_server_error(self):
        response = self.client.post(
            reverse("analytics:insiden_status", args=[self.incident.pk]),
            {"status": Incident.STATUS_RESOLVED}, follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, Incident.STATUS_OPEN)

    def test_actions_reject_another_tenants_incident(self):
        other = Tenant.objects.create(name="Instansi B")
        other_project = Project.objects.create(tenant=other, name="Proyek B")
        foreign = Incident.objects.create(
            project=other_project, title="Milik Tetangga", severity=Incident.SEVERITY_LOW,
        )
        response = self.client.post(
            reverse("analytics:insiden_promote", args=[foreign.pk])
        )
        self.assertEqual(response.status_code, 404)
        foreign.refresh_from_db()
        self.assertFalse(foreign.is_confirmed)

    def test_detail_page_shows_narrative_and_timeline(self):
        self.incident.ai_summary = "Ringkasan terukur."
        self.incident.save()
        incidents_url = reverse("analytics:insiden_detail", args=[self.incident.pk])
        response = self.client.get(incidents_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ringkasan terukur.")

    def test_detail_rejects_another_tenants_incident(self):
        other = Tenant.objects.create(name="Instansi B")
        other_project = Project.objects.create(tenant=other, name="Proyek B")
        foreign = Incident.objects.create(
            project=other_project, title="Milik Tetangga", severity=Incident.SEVERITY_LOW,
        )
        response = self.client.get(reverse("analytics:insiden_detail", args=[foreign.pk]))
        self.assertEqual(response.status_code, 404)
