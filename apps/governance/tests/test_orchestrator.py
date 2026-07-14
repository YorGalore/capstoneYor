from decimal import Decimal
from unittest import mock

from django.test import TestCase

from apps.analytics.models import Mention
from apps.core.models import Platform, Project, Tenant
from apps.governance import orchestrator
from apps.governance.models import CollectionRun, MonitoringKeyword, PlatformIntegration


class OrchestratorTest(TestCase):
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

        self.fake_items = [
            {
                "external_id": "tw-1", "url": "https://x.com/1", "content": "pangan bagus",
                "author": "a", "engagement_count": 3, "reach": 100, "platform": "x",
                "matched_keyword": "pangan",
            },
            {
                "external_id": "tw-2", "url": "https://x.com/2", "content": "pangan buruk",
                "author": "b", "engagement_count": 1, "reach": 20, "platform": "x",
                "matched_keyword": "pangan",
            },
        ]

    def test_run_apify_collection_ingests_and_records_run(self):
        with mock.patch.object(orchestrator.apify_crawler, "collect", return_value=self.fake_items):
            runs = orchestrator.run_apify_collection(self.project, token="tok")
        self.assertEqual(len(runs), 1)
        run = runs[0]
        self.assertEqual(run.status, CollectionRun.STATUS_COMPLETED)
        self.assertEqual(run.items_found, 2)
        self.assertGreater(run.cost_estimate, Decimal("0"))
        self.assertEqual(Mention.objects.filter(project=self.project).count(), 2)

    def test_overlap_is_skipped(self):
        CollectionRun.objects.create(source="x", status=CollectionRun.STATUS_RUNNING)
        with mock.patch.object(orchestrator.apify_crawler, "collect", return_value=self.fake_items) as c:
            runs = orchestrator.run_apify_collection(self.project, token="tok")
        c.assert_not_called()
        self.assertEqual(runs[0].status, CollectionRun.STATUS_SKIPPED)
        self.assertEqual(Mention.objects.count(), 0)

    def test_no_token_runs_nothing(self):
        with mock.patch.object(orchestrator.apify_crawler, "collect") as c:
            runs = orchestrator.run_apify_collection(self.project, token=None)
        c.assert_not_called()
        self.assertEqual(runs, [])

    def test_cost_estimate_uses_pricing(self):
        # 2000 X items at ~$0.40 / 1000 → ~0.80
        cost = orchestrator.estimate_cost("x", 2000)
        self.assertEqual(cost, Decimal("0.8000"))

    def test_failed_actor_marks_run_failed(self):
        with mock.patch.object(orchestrator.apify_crawler, "collect", side_effect=RuntimeError("boom")):
            runs = orchestrator.run_apify_collection(self.project, token="tok")
        self.assertEqual(runs[0].status, CollectionRun.STATUS_FAILED)
        self.assertIn("boom", runs[0].error)
