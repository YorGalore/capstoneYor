from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.analytics.models import (
    Category, Issue, IssueLabel, Mention, SubCategory,
)
from apps.core.models import Platform, Project, Tenant
from apps.governance.ingestion import ingest_items


class EmotionAndConfidenceTest(TestCase):
    def setUp(self):
        self.platform = Platform.objects.create(slug="x", display_name="X")
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")

    def test_ingest_stores_confidence_model_and_emotion_labels(self):
        ingest_items(self.project, self.platform, [{
            "external_id": "tw-e1", "url": "https://x.com/e1",
            "content": "warga marah dan takut karena krisis pangan gagal",
            "author": "a", "engagement_count": 0, "reach": 0,
            "platform": "x", "matched_keyword": "pangan",
        }])
        m = Mention.objects.get(external_id="tw-e1")
        self.assertEqual(m.sentiment, Mention.SENTIMENT_NEGATIVE)
        self.assertGreater(m.sentiment_confidence, 0.0)
        self.assertEqual(m.sentiment_model, "lexicon-v1")
        self.assertIn("anger", m.emotion_labels)
        self.assertIn("fear", m.emotion_labels)


class EnrichCommandTest(TestCase):
    def setUp(self):
        self.platform = Platform.objects.create(slug="x", display_name="X")
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")

    def test_enrich_backfills_unscored_mentions(self):
        # A mention that predates the NLP layer: no model recorded, no emotion labels.
        m = Mention.objects.create(
            project=self.project, platform=self.platform, author_handle="@a",
            content_snippet="program berhasil dan bermanfaat",
            sentiment=Mention.SENTIMENT_NEUTRAL, emotion=Mention.EMOTION_TRUST,
            posted_at=timezone.now(), sentiment_model="", emotion_labels=[],
        )
        out = StringIO()
        call_command("enrich", stdout=out)
        m.refresh_from_db()
        self.assertEqual(m.sentiment, Mention.SENTIMENT_POSITIVE)
        self.assertEqual(m.sentiment_model, "lexicon-v1")
        self.assertTrue(m.emotion_labels)

    def test_enrich_also_auto_labels_against_taxonomy(self):
        category = Category.objects.create(name="Ekonomi")
        sub = SubCategory.objects.create(category=category, name="Pangan")
        issue = Issue.objects.create(subcategory=sub, name="Harga Pangan", keywords=["pangan"])
        m = Mention.objects.create(
            project=self.project, platform=self.platform, author_handle="@a",
            content_snippet="harga pangan melonjak di pasar",
            sentiment=Mention.SENTIMENT_NEUTRAL, emotion=Mention.EMOTION_TRUST,
            posted_at=timezone.now(), sentiment_model="",
        )

        call_command("enrich", stdout=StringIO())

        self.assertEqual(IssueLabel.objects.get(mention=m).issue, issue)
