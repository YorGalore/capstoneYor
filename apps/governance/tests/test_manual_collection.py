from datetime import date
from unittest import mock

from django.test import TestCase

from apps.core.models import Project, Tenant
from apps.governance import scheduling
from apps.governance.models import CollectionRun, ManualCollectionRequest


class ManualCollectionWorkerTest(TestCase):
    def setUp(self):
        tenant = Tenant.objects.create(name="Instansi")
        self.project = Project.objects.create(tenant=tenant, name="Proyek")

    @mock.patch("apps.governance.orchestrator.run_news_collection")
    def test_worker_claims_and_completes_news_request(self, collect):
        run = CollectionRun.objects.create(
            project=self.project,
            source="news:example.id",
            status=CollectionRun.STATUS_COMPLETED,
            items_found=4,
        )
        collect.return_value = [run]
        request = ManualCollectionRequest.objects.create(
            project=self.project,
            collection_type=ManualCollectionRequest.TYPE_NEWS,
            requested_by="Operator",
        )

        processed = scheduling.run_pending_manual_collections()

        request.refresh_from_db()
        self.assertEqual(processed, [request])
        self.assertEqual(request.status, ManualCollectionRequest.STATUS_COMPLETED)
        self.assertEqual(request.items_found, 4)
        self.assertIsNotNone(request.started_at)
        self.assertIsNotNone(request.finished_at)

    @mock.patch("apps.governance.apify.get_active_token", return_value=None)
    def test_social_request_fails_clearly_without_token(self, get_token):
        request = ManualCollectionRequest.objects.create(
            project=self.project,
            collection_type=ManualCollectionRequest.TYPE_SOCIAL,
            requested_by="Operator",
        )

        scheduling.run_pending_manual_collections()

        request.refresh_from_db()
        self.assertEqual(request.status, ManualCollectionRequest.STATUS_FAILED)
        self.assertIn("Token Apify", request.detail)

    @mock.patch("apps.governance.orchestrator.run_apify_collection")
    @mock.patch("apps.governance.apify.get_active_token", return_value="tok")
    def test_history_request_forwards_window_and_bound(self, _token, collect):
        collect.return_value = []
        request = ManualCollectionRequest.objects.create(
            project=self.project,
            collection_type=ManualCollectionRequest.TYPE_SOCIAL,
            requested_by="Operator",
            history_start_date=date(2026, 7, 21),
            history_end_date=date(2026, 7, 27),
            max_results_per_platform=75,
        )

        scheduling.run_pending_manual_collections()

        collect.assert_called_once_with(
            self.project,
            "tok",
            start_date=date(2026, 7, 21),
            end_date=date(2026, 7, 27),
            max_results=75,
        )
        request.refresh_from_db()
        self.assertEqual(request.status, ManualCollectionRequest.STATUS_FAILED)

    @mock.patch("apps.governance.orchestrator.run_news_collection")
    def test_failed_source_is_visible_on_manual_request(self, collect):
        run = CollectionRun.objects.create(
            project=self.project,
            source="news:rusak.id",
            status=CollectionRun.STATUS_FAILED,
            error="upstream timeout",
        )
        collect.return_value = [run]
        request = ManualCollectionRequest.objects.create(
            project=self.project,
            collection_type=ManualCollectionRequest.TYPE_NEWS,
            requested_by="Operator",
        )

        scheduling.run_pending_manual_collections()

        request.refresh_from_db()
        self.assertEqual(request.status, ManualCollectionRequest.STATUS_FAILED)
        self.assertIn("upstream timeout", request.detail)
