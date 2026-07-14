from django.test import TestCase

from apps.analytics.models import (
    Author, Category, Issue, IssueLabel, Mention, SubCategory,
)
from apps.core.models import Platform, Project, Tenant
from apps.governance.ingestion import ingest_items


class IngestionTest(TestCase):
    def setUp(self):
        self.platform = Platform.objects.create(slug="x", display_name="X")
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        self.items = [
            {
                "external_id": "tw-abc123", "url": "https://x.com/u/1",
                "content": "Program pangan berhasil dan meningkat", "author": "warga_a",
                "engagement": {"likes": 10}, "engagement_count": 12, "reach": 900,
                "platform": "x", "matched_keyword": "pangan",
            },
            {
                "external_id": "tw-def456", "url": "https://x.com/u/2",
                "content": "krisis pangan gagal", "author": "warga_b",
                "engagement": {"likes": 1}, "engagement_count": 1, "reach": 50,
                "platform": "x", "matched_keyword": "pangan",
            },
        ]

    def test_ingest_creates_mentions_and_authors(self):
        summary = ingest_items(self.project, self.platform, self.items)
        self.assertEqual(summary["created"], 2)
        self.assertEqual(Mention.objects.count(), 2)
        self.assertEqual(Author.objects.count(), 2)

    def test_ingest_links_author_and_engagement(self):
        ingest_items(self.project, self.platform, self.items)
        mention = Mention.objects.get(external_id="tw-abc123")
        self.assertEqual(mention.author.handle, "warga_a")
        self.assertEqual(mention.engagement_count, 12)
        self.assertEqual(mention.reach_estimate, 900)
        self.assertEqual(mention.matched_keyword, "pangan")
        self.assertTrue(mention.is_scraped)

    def test_ingest_dedups_by_external_id(self):
        ingest_items(self.project, self.platform, self.items)
        summary = ingest_items(self.project, self.platform, self.items)
        self.assertEqual(summary["created"], 0)
        self.assertEqual(summary["duplicates"], 2)
        self.assertEqual(Mention.objects.count(), 2)

    def test_ingest_auto_labels_against_taxonomy(self):
        category = Category.objects.create(name="Ekonomi")
        sub = SubCategory.objects.create(category=category, name="Pangan")
        issue = Issue.objects.create(subcategory=sub, name="Harga Pangan", keywords=["pangan"])

        ingest_items(self.project, self.platform, self.items)

        label = IssueLabel.objects.get(mention__external_id="tw-abc123")
        self.assertEqual(label.issue, issue)
        self.assertEqual(label.source, IssueLabel.SOURCE_AUTO)

    def test_ingest_scores_sentiment_from_content(self):
        ingest_items(self.project, self.platform, self.items)
        positive = Mention.objects.get(external_id="tw-abc123")
        negative = Mention.objects.get(external_id="tw-def456")
        self.assertEqual(positive.sentiment, Mention.SENTIMENT_POSITIVE)
        self.assertEqual(negative.sentiment, Mention.SENTIMENT_NEGATIVE)
