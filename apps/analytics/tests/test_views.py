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


from apps.coordination.seed import seed_coordination


class WarRoomViewTest(TestCase):
    def test_war_room_renders(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=100)
        seed_coordination()
        response = self.client.get("/war-room/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WAR ROOM NARASI")


class NarasiViewTest(TestCase):
    def test_narasi_renders_both_coalitions(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=100)
        response = self.client.get("/narasi/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Koalisi Nusantara Raya")
        self.assertContains(response, "Koalisi Perubahan Bersatu")
