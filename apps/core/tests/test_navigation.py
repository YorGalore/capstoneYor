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

    def test_root_redirects_to_ringkasan(self):
        seed_core()
        self.client.force_login(get_user_model().objects.get(username=DEMO_USERNAME))
        response = self.client.get("/")
        self.assertRedirects(response, "/ringkasan/", fetch_redirect_response=False)

    def test_all_screen_routes_resolve(self):
        seed_core()
        self.client.force_login(get_user_model().objects.get(username=DEMO_USERNAME))
        for path in [
            "/ringkasan/", "/war-room/", "/narasi/", "/regional/",
            "/koordinasi/", "/konfigurasi/", "/pengawasan/",
        ]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
