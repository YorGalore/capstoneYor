from datetime import date
from unittest import mock

from django.test import TestCase

from apps.analytics.models import Mention
from apps.core.models import Platform, Project, Tenant
from apps.governance import comment_crawler, orchestrator
from apps.governance.ingestion import ingest_items
from apps.governance.models import MonitoringKeyword


class CommentNormalizationTest(TestCase):
    def test_instagram_comment_is_linked_to_parent_and_has_stable_url(self):
        item = {
            "postUrl": "https://www.instagram.com/p/ABC/",
            "commentId": "c1",
            "text": "Pelayanannya lambat",
            "username": "warga",
            "commentLikeCount": 4,
            "timestamp": "2026-07-22T10:00:00Z",
        }
        record = comment_crawler.extract_comment("instagram", item, "pemkab")
        self.assertEqual(record["content_type"], Mention.CONTENT_COMMENT)
        self.assertEqual(record["content"], "Pelayanannya lambat")
        self.assertEqual(record["engagement_count"], 4)
        self.assertIn("#pantau-comment-c1", record["url"])
        self.assertTrue(record["parent_external_id"].startswith("ig-"))

    def test_facebook_nested_comment_shape_is_normalized(self):
        item = {
            "postUrl": "https://www.facebook.com/posts/1",
            "comment": {
                "id": "fb-c1",
                "text": "Terima kasih",
                "created_at": "2026-07-22T10:00:00Z",
                "author": {"name": "Warga A"},
                "likes": 3,
            },
        }
        record = comment_crawler.extract_comment("facebook", item)
        self.assertEqual(record["author"], "Warga A")
        self.assertEqual(record["engagement_count"], 3)

    @mock.patch("apps.governance.comment_crawler._run_and_fetch_items")
    def test_historical_comments_are_filtered_to_reporting_window(self, runner):
        runner.return_value = [
            {
                "postUrl": "https://www.instagram.com/p/ABC/",
                "commentId": "inside",
                "text": "Dalam periode",
                "username": "a",
                "timestamp": "2026-07-24T10:00:00Z",
            },
            {
                "postUrl": "https://www.instagram.com/p/ABC/",
                "commentId": "outside",
                "text": "Di luar periode",
                "username": "b",
                "timestamp": "2026-07-29T10:00:00Z",
            },
        ]
        rows = comment_crawler.collect(
            "instagram",
            [{
                "url": "https://www.instagram.com/p/ABC/",
                "matched_keyword": "MBG",
            }],
            token="tok",
            start_date=date(2026, 7, 21),
            end_date=date(2026, 7, 27),
        )
        self.assertEqual(
            [row["external_id"] for row in rows],
            ["cm-instagram-inside"],
        )


class CommentIngestionTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek")
        self.platform = Platform.objects.create(
            slug="instagram-comments-test",
            display_name="Instagram Test",
            channel_type=Platform.CHANNEL_SOCIAL,
        )

    def test_ingestion_links_comment_to_existing_parent(self):
        parent_items = [{
            "external_id": "ig-parent",
            "url": "https://www.instagram.com/p/ABC/",
            "content": "Posting induk",
            "author": "pemkab",
            "engagement": {"comments": 12},
        }]
        ingest_items(self.project, self.platform, parent_items)
        comment_items = [{
            "external_id": "cm-instagram-c1",
            "parent_external_id": "ig-parent",
            "url": "https://www.instagram.com/p/ABC/#comment-c1",
            "content": "Komentar negatif gagal",
            "author": "warga",
            "content_type": Mention.CONTENT_COMMENT,
            "engagement": {"likes": 2},
        }]
        ingest_items(self.project, self.platform, comment_items)

        parent = Mention.objects.get(external_id="ig-parent")
        comment = Mention.objects.get(external_id="cm-instagram-c1")
        self.assertEqual(parent.reported_comment_count, 12)
        self.assertEqual(comment.parent, parent)
        self.assertEqual(comment.content_type, Mention.CONTENT_COMMENT)


class CommentOrchestrationTest(TestCase):
    def setUp(self):
        tenant = Tenant.objects.create(name="Instansi")
        self.project = Project.objects.create(
            tenant=tenant,
            name="Proyek",
            collect_comments=True,
            comment_posts_per_run=2,
            comments_per_post=5,
        )
        self.platform = Platform.objects.create(
            slug="x",
            display_name="X",
            channel_type=Platform.CHANNEL_SOCIAL,
        )
        self.keyword = MonitoringKeyword.objects.create(
            project=self.project, keyword="pemkab", created_by="tester"
        )

    @mock.patch("apps.governance.orchestrator.comment_crawler.collect")
    @mock.patch("apps.governance.orchestrator.apify_crawler.collect")
    def test_enabled_project_runs_bounded_comment_collection(self, collect_posts, collect_comments):
        collect_posts.return_value = [{
            "external_id": "tw-parent",
            "url": "https://x.com/pemkab/status/1",
            "content": "pemkab",
            "author": "pemkab",
            "engagement_count": 10,
            "engagement": {"comments": 2},
        }]
        collect_comments.return_value = []

        run = orchestrator.collect_platform(
            self.project, self.platform, [self.keyword], token="token"
        )

        self.assertEqual(run.status, run.STATUS_COMPLETED)
        collect_comments.assert_called_once()
        self.assertEqual(collect_comments.call_args.kwargs["max_comments_per_post"], 5)

    @mock.patch(
        "apps.governance.orchestrator.comment_crawler.collect",
        side_effect=RuntimeError("actor komentar unavailable"),
    )
    @mock.patch("apps.governance.orchestrator.apify_crawler.collect")
    def test_comment_failure_preserves_successful_parent_posts(
        self, collect_posts, _collect_comments
    ):
        collect_posts.return_value = [{
            "external_id": "tw-parent-partial",
            "url": "https://x.com/pemkab/status/partial",
            "content": "pemkab",
            "author": "pemkab",
            "engagement_count": 10,
            "engagement": {"comments": 2},
        }]

        run = orchestrator.collect_platform(
            self.project, self.platform, [self.keyword], token="token"
        )

        self.assertEqual(run.status, run.STATUS_COMPLETED)
        self.assertIn("Koleksi komentar gagal", run.error)
        self.assertTrue(
            Mention.objects.filter(external_id="tw-parent-partial").exists()
        )
