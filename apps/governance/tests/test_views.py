from django.test import TestCase

from apps.core.seed import seed_core
from apps.governance.seed import seed_governance


class KonfigurasiViewTest(TestCase):
    def test_konfigurasi_view_renders(self):
        tenant, project = seed_core()
        seed_governance(tenant)
        response = self.client.get("/konfigurasi/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Konsol Konfigurasi")
        self.assertContains(response, "kompas.com")
        self.assertContains(response, "Nonaktif")
