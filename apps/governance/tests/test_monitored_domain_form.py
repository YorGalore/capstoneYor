from django.test import TestCase

from apps.core.models import Project, Tenant
from apps.governance.forms import MonitoredDomainForm


class MonitoredDomainFormValidationTest(TestCase):
    """ISS-KONFIGURASI-004: the domain field previously accepted any string that
    was merely unique — no format check at all."""

    def setUp(self):
        tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=tenant, name="Proyek A")

    def _form(self, domain):
        return MonitoredDomainForm(
            {"domain": domain, "adapter": "RSS", "feed_url": "https://example.go.id/rss.xml"},
            project=self.project,
        )

    def test_rejects_domain_with_whitespace(self):
        form = self._form("domain tanpa titik dan spasi")
        self.assertFalse(form.is_valid())
        self.assertIn("domain", form.errors)

    def test_rejects_domain_without_a_tld(self):
        form = self._form("localhost")
        self.assertFalse(form.is_valid())
        self.assertIn("domain", form.errors)

    def test_accepts_well_formed_domain(self):
        form = self._form("jogja.tribunnews.com")
        self.assertTrue(form.is_valid())

    def test_accepts_domain_with_hyphen(self):
        form = self._form("berita-terkini.go.id")
        self.assertTrue(form.is_valid())
