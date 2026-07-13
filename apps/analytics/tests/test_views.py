from django.test import TestCase

from apps.core.seed import seed_core
from apps.analytics.seed import seed_analytics


class RingkasanViewTest(TestCase):
    def test_ringkasan_renders_kpis(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=200)
        response = self.client.get("/ringkasan/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Total Sebutan")
        self.assertContains(response, "Komposisi Sentimen")
