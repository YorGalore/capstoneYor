from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.analytics.models import Mention
from apps.core.seed import DEMO_USERNAME, seed_core
from apps.governance.models import AuditLogEntry, MonitoredDomain, MonitoringKeyword, PlatformIntegration
from apps.governance.seed import seed_governance


class KonfigurasiViewTest(TestCase):
    def setUp(self):
        self.tenant, self.project = seed_core()
        seed_governance(self.tenant)
        self.client.force_login(get_user_model().objects.get(username=DEMO_USERNAME))

    def test_konfigurasi_view_renders(self):
        response = self.client.get("/konfigurasi/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Konsol Konfigurasi")
        self.assertContains(response, "antaranews.com")
        self.assertContains(response, "Nonaktif")

    def test_add_keyword_creates_row_and_audit_entry(self):
        response = self.client.post("/konfigurasi/kata-kunci/tambah/", {"keyword": "Subsidi BBM"})
        self.assertRedirects(response, "/konfigurasi/")
        self.assertTrue(MonitoringKeyword.objects.filter(keyword="subsidi bbm").exists())
        self.assertTrue(AuditLogEntry.objects.filter(action__icontains="Menambahkan kata kunci").exists())

    def test_add_keyword_rejects_duplicate(self):
        # "pangan" is already seeded by seed_governance() in setUp.
        response = self.client.post("/konfigurasi/kata-kunci/tambah/", {"keyword": "pangan"})
        self.assertRedirects(response, "/konfigurasi/")
        self.assertEqual(MonitoringKeyword.objects.filter(keyword="pangan").count(), 1)

    def test_toggle_keyword_flips_active_state(self):
        keyword = MonitoringKeyword.objects.create(keyword="banjir")
        self.client.post(f"/konfigurasi/kata-kunci/{keyword.pk}/toggle/")
        keyword.refresh_from_db()
        self.assertFalse(keyword.is_active)

    def test_delete_keyword_removes_row(self):
        keyword = MonitoringKeyword.objects.create(keyword="banjir")
        self.client.post(f"/konfigurasi/kata-kunci/{keyword.pk}/hapus/")
        self.assertFalse(MonitoringKeyword.objects.filter(pk=keyword.pk).exists())

    def test_add_domain_creates_row(self):
        response = self.client.post("/konfigurasi/domain/tambah/", {
            "domain": "example-berita.co.id", "adapter": "RSS",
            "feed_url": "https://example-berita.co.id/rss.xml",
        })
        self.assertRedirects(response, "/konfigurasi/")
        self.assertTrue(MonitoredDomain.objects.filter(domain="example-berita.co.id").exists())

    def test_delete_domain_removes_row(self):
        domain = MonitoredDomain.objects.get(domain="tribunnews.com")
        self.client.post(f"/konfigurasi/domain/{domain.pk}/hapus/")
        self.assertFalse(MonitoredDomain.objects.filter(pk=domain.pk).exists())

    @patch("apps.governance.views.scraping.check_reachable", return_value=True)
    def test_test_domain_connection_marks_active_on_success(self, mock_check):
        domain = MonitoredDomain.objects.get(domain="tribunnews.com")
        self.client.post(f"/konfigurasi/domain/{domain.pk}/uji-koneksi/")
        domain.refresh_from_db()
        self.assertEqual(domain.status, MonitoredDomain.STATUS_ACTIVE)
        self.assertIsNotNone(domain.last_tested_at)
        mock_check.assert_called_once()

    @patch("apps.governance.views.scraping.check_reachable", return_value=False)
    def test_test_domain_connection_marks_needs_review_on_failure(self, mock_check):
        domain = MonitoredDomain.objects.get(domain="antaranews.com")
        self.client.post(f"/konfigurasi/domain/{domain.pk}/uji-koneksi/")
        domain.refresh_from_db()
        self.assertEqual(domain.status, MonitoredDomain.STATUS_NEEDS_REVIEW)

    def test_toggle_integration_flips_active_state(self):
        integration = PlatformIntegration.objects.get(platform__slug="facebook")
        self.assertFalse(integration.is_active)
        self.client.post(f"/konfigurasi/integrasi/{integration.pk}/toggle/")
        integration.refresh_from_db()
        self.assertTrue(integration.is_active)

    @patch("apps.governance.views.scraping.run_scan")
    def test_run_scan_persists_summary_and_audit_entry(self, mock_run_scan):
        mock_run_scan.return_value = {"sources_scanned": 2, "new_mentions": 3, "errors": []}
        response = self.client.post("/konfigurasi/pindai/")
        self.assertRedirects(response, "/konfigurasi/")
        mock_run_scan.assert_called_once()
        self.assertTrue(
            AuditLogEntry.objects.filter(action__icontains="Menjalankan pemindaian berita langsung").exists()
        )

    def test_run_scan_blocked_without_active_keywords(self):
        MonitoringKeyword.objects.update(is_active=False)
        response = self.client.post("/konfigurasi/pindai/")
        self.assertRedirects(response, "/konfigurasi/")
        self.assertEqual(Mention.objects.filter(is_scraped=True).count(), 0)


class PengawasanViewTest(TestCase):
    def test_pengawasan_view_renders(self):
        tenant, project = seed_core()
        seed_governance(tenant)
        self.client.force_login(get_user_model().objects.get(username=DEMO_USERNAME))
        response = self.client.get("/pengawasan/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dasbor Pengawasan")
        self.assertContains(response, "dilarang keras")
