from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.core.models import AnalystProfile, Tenant
from apps.core.seed import DEMO_USERNAME, seed_core


class NavigationSmokeTest(TestCase):
    def test_sidebar_and_topbar_render_without_error(self):
        request = RequestFactory().get("/ringkasan/")
        html = render_to_string(
            "core/_sidebar.html", {"active_nav": "ringkasan"}, request=request
        )
        self.assertIn("PANTAU", html)
        self.assertIn("Ringkasan", html)

        topbar_html = render_to_string(
            "core/_topbar.html",
            {"instansi": "Kemenko PMK", "proyek": "Program Pangan Rakyat"},
            request=request,
        )
        self.assertIn("Kemenko PMK", topbar_html)

    def test_root_renders_public_landing_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pahami apa yang publik")
        self.assertNotContains(response, "48.291")
        self.assertNotContains(response, "● LIVE")

    def test_all_screen_routes_resolve(self):
        from django.utils import timezone

        from apps.governance.models import PoliticalMonitoringPermission

        seed_core()
        demo_user = get_user_model().objects.get(username=DEMO_USERNAME)
        # /narasi/ is a political-monitoring view: it requires the separate,
        # compliance-approved grant (FR-29.1), not merely an admin role.
        PoliticalMonitoringPermission.objects.create(
            user=demo_user, approved_by="Kepatuhan", approved_at=timezone.now(), active=True
        )
        self.client.force_login(demo_user)
        for path in [
            "/ringkasan/", "/war-room/", "/narasi/", "/regional/",
            "/koordinasi/", "/konfigurasi/", "/pengawasan/",
        ]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)

    def test_narasi_denied_without_political_monitoring_permission(self):
        seed_core()
        self.client.force_login(get_user_model().objects.get(username=DEMO_USERNAME))
        self.assertEqual(self.client.get("/narasi/").status_code, 403)


class SidebarDisabledLinkTest(TestCase):
    """UX-ISSUE-001: a role denied 'konfigurasi'/'pengawasan' must see a
    non-clickable label instead of a link that leads to a 403."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.viewer = get_user_model().objects.create(username="peninjau.sidebar")
        AnalystProfile.objects.update_or_create(
            user=self.viewer,
            defaults={"tenant": self.tenant, "role": AnalystProfile.ROLE_VIEWER},
        )

    def test_viewer_sees_disabled_konfigurasi_and_pengawasan_links(self):
        self.client.force_login(self.viewer)
        response = self.client.get(reverse("analytics:ringkasan"))
        self.assertContains(
            response, '<span class="pantau-nav-item disabled" title="Akses dibatasi">Konfigurasi</span>',
            html=True,
        )
        self.assertContains(
            response, '<span class="pantau-nav-item disabled" title="Akses dibatasi">Pengawasan</span>',
            html=True,
        )

    def test_dashboard_includes_accessible_mobile_navigation_controls(self):
        self.client.force_login(self.viewer)
        response = self.client.get(reverse("analytics:ringkasan"))
        self.assertContains(response, 'id="pantau-nav-toggle"')
        self.assertContains(response, 'for="pantau-nav-toggle"')
        self.assertContains(response, 'aria-label="Buka navigasi"')

    def test_tenant_admin_sees_active_konfigurasi_and_pengawasan_links(self):
        tenant_admin = get_user_model().objects.create(username="admin.sidebar")
        AnalystProfile.objects.update_or_create(
            user=tenant_admin,
            defaults={"tenant": self.tenant, "role": AnalystProfile.ROLE_TENANT_ADMIN},
        )
        self.client.force_login(tenant_admin)
        response = self.client.get(reverse("analytics:ringkasan"))
        self.assertContains(response, 'href="/konfigurasi/"')
        self.assertContains(response, 'href="/pengawasan/"')

    def test_sidebar_shows_rbac_role_alongside_job_title(self):
        # AUTH-ISSUE-001: role_label is free text and can drift from the
        # technical RBAC role, so both must be visible.
        self.viewer.analyst_profile.role_label = "Staf Humas"
        self.viewer.analyst_profile.save(update_fields=["role_label"])
        self.client.force_login(self.viewer)
        response = self.client.get(reverse("analytics:ringkasan"))
        self.assertContains(response, "Staf Humas")
        self.assertContains(response, "Peninjau")
