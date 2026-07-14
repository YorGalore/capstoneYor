from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.core.seed import DEMO_USERNAME, seed_core
from apps.analytics.seed import seed_analytics


class RingkasanViewTest(TestCase):
    def test_ringkasan_renders_kpis(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=200)
        self.client.force_login(get_user_model().objects.get(username=DEMO_USERNAME))
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
        self.client.force_login(get_user_model().objects.get(username=DEMO_USERNAME))
        response = self.client.get("/war-room/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WAR ROOM NARASI")


class NarasiViewTest(TestCase):
    def test_narasi_renders_both_coalitions(self):
        from django.utils import timezone

        from apps.governance.models import PoliticalMonitoringPermission

        tenant, project = seed_core()
        seed_analytics(project, mention_count=100)
        demo_user = get_user_model().objects.get(username=DEMO_USERNAME)
        # Political-narrative views require the compliance-approved grant (FR-29.1).
        PoliticalMonitoringPermission.objects.create(
            user=demo_user, approved_by="Kepatuhan", approved_at=timezone.now(), active=True
        )
        self.client.force_login(demo_user)
        response = self.client.get("/narasi/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Koalisi Nusantara Raya")
        self.assertContains(response, "Koalisi Perubahan Bersatu")
        self.assertContains(response, "Tema dominan (klaster topik)")
        self.assertContains(response, "capaian distribusi tahap 2")
        self.assertContains(response, "keterlambatan wilayah timur")


class RegionalViewTest(TestCase):
    def test_regional_view_renders_and_drill_down(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=300)
        self.client.force_login(get_user_model().objects.get(username=DEMO_USERNAME))
        response = self.client.get("/regional/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Distribusi Narasi Regional")

        province_name = response.context["summary"]["province_rows"][0]["name"]
        drill_response = self.client.get(f"/regional/?provinsi={province_name}")
        self.assertEqual(drill_response.context["summary"]["selected"]["name"], province_name)
