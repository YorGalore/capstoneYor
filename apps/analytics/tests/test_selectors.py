from django.test import TestCase
from django.utils import timezone

from apps.core.models import Platform, Project, Tenant
from apps.analytics.models import Mention
from apps.analytics import selectors


class RingkasanSummaryTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Kemenko PMK")
        self.project = Project.objects.create(tenant=self.tenant, name="Program Pangan Rakyat")
        self.platform = Platform.objects.create(
            slug="x", display_name="X (Twitter)", method=Platform.METHOD_INTERNAL
        )

    def test_summary_counts_and_breakdowns(self):
        now = timezone.now()
        Mention.objects.create(
            project=self.project, platform=self.platform, author_handle="@a",
            content_snippet="s", sentiment=Mention.SENTIMENT_POSITIVE, emotion=Mention.EMOTION_TRUST,
            posted_at=now, engagement_count=10,
        )
        Mention.objects.create(
            project=self.project, platform=self.platform, author_handle="@b",
            content_snippet="s", sentiment=Mention.SENTIMENT_NEGATIVE, emotion=Mention.EMOTION_ANGER,
            posted_at=now, engagement_count=5,
        )
        summary = selectors.ringkasan_summary(self.project)
        self.assertEqual(summary["total_mentions"], 2)
        self.assertEqual(summary["total_interactions"], 15)
        self.assertEqual(summary["unique_authors"], 2)
        positive = next(s for s in summary["sentiment_breakdown"] if s["key"] == Mention.SENTIMENT_POSITIVE)
        self.assertEqual(positive["count"], 1)
        self.assertEqual(positive["pct"], 50)

    def test_summary_excludes_political_mentions(self):
        now = timezone.now()
        Mention.objects.create(
            project=self.project, platform=self.platform, author_handle="@political",
            content_snippet="s", sentiment=Mention.SENTIMENT_NEUTRAL, emotion=Mention.EMOTION_TRUST,
            posted_at=now, is_political=True,
        )
        summary = selectors.ringkasan_summary(self.project)
        self.assertEqual(summary["total_mentions"], 0)
