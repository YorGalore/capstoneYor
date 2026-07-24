from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.analytics.models import (
    Category, Incident, IncidentEvent, Issue, IssueLabel, Mention, OPD,
    SubCategory,
)
from apps.core.models import AnalystProfile, Platform, Project, Province, Regency, Tenant


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

    def test_board_never_hides_a_still_open_incident_regardless_of_age(self):
        # Fix 3: the window filter must not silently drop unresolved work — the
        # worst failure mode for a board meant to surface it.
        old = timezone.now() - timedelta(days=30)
        still_open = Incident.objects.create(
            project=self.project, title="Insiden Lama Masih Terbuka",
            severity=Incident.SEVERITY_HIGH, status=Incident.STATUS_OPEN,
        )
        Incident.objects.filter(pk=still_open.pk).update(created_at=old)
        old_closed = Incident.objects.create(
            project=self.project, title="Insiden Lama Sudah Ditutup",
            severity=Incident.SEVERITY_HIGH, status=Incident.STATUS_CLOSED,
        )
        Incident.objects.filter(pk=old_closed.pk).update(created_at=old)

        response = self.client.get(reverse("analytics:insiden"))

        self.assertContains(response, "Insiden Lama Masih Terbuka")
        self.assertNotContains(response, "Insiden Lama Sudah Ditutup")

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

    def test_generate_response_creates_draft_and_logs_event(self):
        from apps.governance.models import RegulatoryDocument
        RegulatoryDocument.objects.create(
            title="Standar Pelayanan Minimal Jalan",
            source_ref="Permen PU No. 1/2014",
            body="Jalan rusak berlubang wajib diperbaiki oleh penyelenggara jalan.",
        )
        response = self.client.post(
            reverse("analytics:insiden_response_generate", args=[self.incident.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.incident.refresh_from_db()
        self.assertIn("Permen PU No. 1/2014", self.incident.draft_response)
        event = self.incident.events.filter(
            kind=IncidentEvent.KIND_RESPONSE_DRAFTED
        ).last()
        self.assertEqual(event.logged_by, "Operator Satu")

    def test_save_response_persists_edited_text(self):
        response = self.client.post(
            reverse("analytics:insiden_response_save", args=[self.incident.pk]),
            {"draft_response": "Tanggapan resmi hasil suntingan."},
        )
        self.assertEqual(response.status_code, 302)
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.draft_response, "Tanggapan resmi hasil suntingan.")

    def test_save_response_rejects_empty_text(self):
        self.client.post(
            reverse("analytics:insiden_response_save", args=[self.incident.pk]),
            {"draft_response": "   "},
        )
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.draft_response, "")

    def test_generate_response_rejects_another_tenants_incident(self):
        other = Tenant.objects.create(name="Instansi B")
        other_project = Project.objects.create(tenant=other, name="Proyek B")
        foreign = Incident.objects.create(
            project=other_project, title="Milik Tetangga", severity=Incident.SEVERITY_LOW,
        )
        response = self.client.post(
            reverse("analytics:insiden_response_generate", args=[foreign.pk])
        )
        self.assertEqual(response.status_code, 404)

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

    def test_detail_page_only_offers_legal_status_transitions(self):
        # Fix 5: from `open`, only `assigned` and `closed` are legal; the picker
        # must not offer `resolved` (or `in_progress`) at all.
        response = self.client.get(
            reverse("analytics:insiden_detail", args=[self.incident.pk])
        )
        self.assertEqual(self.incident.status, Incident.STATUS_OPEN)
        allowed_values = [value for value, _label in response.context["allowed_status_choices"]]
        self.assertEqual(set(allowed_values), {Incident.STATUS_ASSIGNED, Incident.STATUS_CLOSED})
        self.assertNotContains(response, f'value="{Incident.STATUS_RESOLVED}"')

    def test_detail_rejects_another_tenants_incident(self):
        other = Tenant.objects.create(name="Instansi B")
        other_project = Project.objects.create(tenant=other, name="Proyek B")
        foreign = Incident.objects.create(
            project=other_project, title="Milik Tetangga", severity=Incident.SEVERITY_LOW,
        )
        response = self.client.get(reverse("analytics:insiden_detail", args=[foreign.pk]))
        self.assertEqual(response.status_code, 404)


class IncidentWriteAccessTest(TestCase):
    """ISS-FW-003: insiden is a DASHBOARD_PAGES member (Peninjau gets default read
    access to the board), so mutation actions need their own role check."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        self.viewer = get_user_model().objects.create(username="peninjau.insiden")
        AnalystProfile.objects.update_or_create(
            user=self.viewer,
            defaults={"tenant": self.tenant, "role": AnalystProfile.ROLE_VIEWER},
        )
        self.client.force_login(self.viewer)
        self.opd = OPD.objects.create(
            project=self.project, name="Dinas Pekerjaan Umum", slug="pu-viewer", abbr="PU"
        )
        self.incident = Incident.objects.create(
            project=self.project, title="Jalan Rusak", severity=Incident.SEVERITY_HIGH,
        )

    def test_viewer_can_view_board_and_detail(self):
        self.assertEqual(self.client.get(reverse("analytics:insiden")).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("analytics:insiden_detail", args=[self.incident.pk])).status_code,
            200,
        )

    def test_viewer_cannot_promote_candidate(self):
        response = self.client.post(reverse("analytics:insiden_promote", args=[self.incident.pk]))
        self.assertEqual(response.status_code, 403)
        self.incident.refresh_from_db()
        self.assertFalse(self.incident.is_confirmed)

    def test_viewer_cannot_assign_opd(self):
        response = self.client.post(
            reverse("analytics:insiden_assign", args=[self.incident.pk]), {"opd": self.opd.pk},
        )
        self.assertEqual(response.status_code, 403)
        self.incident.refresh_from_db()
        self.assertIsNone(self.incident.assigned_opd)

    def test_viewer_cannot_change_status(self):
        response = self.client.post(
            reverse("analytics:insiden_status", args=[self.incident.pk]),
            {"status": Incident.STATUS_ASSIGNED},
        )
        self.assertEqual(response.status_code, 403)

    def test_viewer_cannot_add_note(self):
        response = self.client.post(
            reverse("analytics:insiden_note", args=[self.incident.pk]),
            {"description": "Catatan dari peninjau"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.incident.events.filter(description="Catatan dari peninjau").exists())

    def test_viewer_cannot_generate_response(self):
        response = self.client.post(
            reverse("analytics:insiden_response_generate", args=[self.incident.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_viewer_cannot_trigger_refresh(self):
        response = self.client.post(reverse("analytics:insiden_refresh"))
        self.assertEqual(response.status_code, 403)


class DemoSeedTest(TestCase):
    def setUp(self):
        # seed_kulon_progo_demo() reuses the shared platform/reference rows created
        # by seed_core(); apps/core/tests/test_kulon_progo_demo.py follows the same
        # pattern.
        from apps.core.seed import seed_core

        seed_core()

    def test_demo_seed_creates_opds_for_assignment(self):
        from apps.core import demo_kulon_progo

        demo_kulon_progo.seed_kulon_progo_demo()

        self.assertTrue(OPD.objects.filter(slug="pu").exists())
        self.assertTrue(OPD.objects.filter(slug="dlh").exists())

    def test_demo_seed_produces_a_board_an_operator_can_actually_triage(self):
        # The demo is how this feature gets evaluated. A seed that leaves the board
        # empty demonstrates nothing, so pin both that detection finds something and
        # that the results span severity tiers rather than landing all on one.
        from apps.analytics import incidents
        from apps.analytics.models import Incident
        from apps.core import demo_kulon_progo

        _tenant, project = demo_kulon_progo.seed_kulon_progo_demo()

        found = incidents.refresh_candidates(project)

        self.assertGreaterEqual(len(found), 3, "demo seed detects no incidents")
        severities = {incident.severity for incident in found}
        self.assertIn(Incident.SEVERITY_CRITICAL, severities)
        self.assertGreater(
            len(severities), 1, "every demo incident landed on the same severity"
        )

    def test_demo_seed_is_idempotent(self):
        from apps.core import demo_kulon_progo

        demo_kulon_progo.seed_kulon_progo_demo()
        demo_kulon_progo.seed_kulon_progo_demo()

        self.assertEqual(OPD.objects.filter(slug="pu").count(), 1)


class IncidentRefreshTriggerTest(TestCase):
    """Fix 1: detection must be reachable from the UI, not just the URL."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        user = get_user_model().objects.create_user(username="analis", password="rahasia123")
        AnalystProfile.objects.update_or_create(
            user=user,
            defaults={"tenant": self.tenant, "role": AnalystProfile.ROLE_ANALYST},
        )
        self.client.force_login(user)

        self.platform = Platform.objects.create(slug="x", display_name="X")
        self.province = Province.objects.create(name="DI Yogyakarta")
        self.regency = Regency.objects.create(province=self.province, name="Depok")
        cat = Category.objects.create(name="Infrastruktur")
        sub = SubCategory.objects.create(category=cat, name="Jalan")
        self.issue = Issue.objects.create(subcategory=sub, name="Jalan Rusak")
        for _ in range(8):
            mention = Mention.objects.create(
                project=self.project, platform=self.platform, regency=self.regency,
                author_handle="@warga", content_snippet="jalan berlubang",
                sentiment=Mention.SENTIMENT_NEGATIVE, emotion=Mention.EMOTION_ANGER,
                posted_at=timezone.now(),
            )
            IssueLabel.objects.create(
                mention=mention, issue=self.issue, source=IssueLabel.SOURCE_AUTO
            )

    def test_board_has_a_reachable_refresh_trigger(self):
        response = self.client.get(reverse("analytics:insiden"))
        self.assertContains(response, reverse("analytics:insiden_refresh"))

    def test_posting_to_refresh_creates_candidates_and_redirects(self):
        self.assertEqual(Incident.objects.filter(project=self.project).count(), 0)

        response = self.client.post(reverse("analytics:insiden_refresh"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Incident.objects.filter(project=self.project).count(), 1)
