from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from apps.core.seed import DEMO_USERNAME


class FullFlowSmokeTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo_data")

    def setUp(self):
        self.client.force_login(get_user_model().objects.get(username=DEMO_USERNAME))

    def test_all_seven_screens_render_with_seeded_data(self):
        checks = [
            ("/ringkasan/", "Total Sebutan"),
            ("/war-room/", "WAR ROOM NARASI"),
            ("/narasi/", "Pangsa Suara"),
            ("/regional/", "Distribusi Narasi Regional"),
            ("/koordinasi/", "Deteksi Perilaku"),
            ("/konfigurasi/", "Konsol Konfigurasi"),
            ("/pengawasan/", "Dasbor Pengawasan"),
        ]
        for path, expected_text in checks:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertContains(response, expected_text, msg_prefix=path)

    def test_disabled_nav_items_have_no_route(self):
        response = self.client.get("/ringkasan/")
        content = response.content.decode()
        self.assertIn("Umpan Sebutan", content)
        self.assertNotIn('href="/umpan-sebutan/"', content)
