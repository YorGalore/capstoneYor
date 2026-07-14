from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from apps.analytics.models import Mention
from apps.core.models import Platform, Project, Tenant
from apps.governance import apify, orchestrator
from apps.governance.models import MonitoringKeyword, PlatformIntegration


class CollectCommandTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        self.platform = Platform.objects.create(
            slug="x", display_name="X", method=Platform.METHOD_APIFY
        )
        PlatformIntegration.objects.create(
            platform=self.platform, method=PlatformIntegration.METHOD_APIFY, is_active=True
        )
        MonitoringKeyword.objects.create(keyword="pangan", is_active=True)

    def test_command_runs_collection_when_token_present(self):
        items = [{
            "external_id": "tw-9", "url": "https://x.com/9", "content": "pangan",
            "author": "a", "engagement_count": 1, "reach": 5, "platform": "x",
            "matched_keyword": "pangan",
        }]
        out = StringIO()
        with mock.patch.object(apify, "get_active_token", return_value="tok"), \
             mock.patch.object(orchestrator.apify_crawler, "collect", return_value=items):
            call_command("collect", stdout=out)
        self.assertEqual(Mention.objects.count(), 1)
        self.assertIn("Siklus koleksi selesai", out.getvalue())

    def test_command_aborts_without_token(self):
        err = StringIO()
        with mock.patch.object(apify, "get_active_token", return_value=None):
            call_command("collect", stderr=err)
        self.assertEqual(Mention.objects.count(), 0)
        self.assertIn("token Apify", err.getvalue())
