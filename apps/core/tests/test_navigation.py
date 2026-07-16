from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase

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
