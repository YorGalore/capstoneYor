from datetime import datetime, timedelta, timezone as datetime_timezone

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.analytics import media_report_pdf, selectors
from apps.analytics.models import (
    ActorSentimentAssessment, Category, Issue, IssueLabel, Mention, PoliticalActor,
    SubCategory,
)
from apps.core.models import AnalystProfile, Platform, Project, Tenant
from apps.governance.models import MonitoringKeyword


class MediaAnalysisReportTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Pemkab Uji")
        self.project = Project.objects.create(tenant=self.tenant, name="Monitoring Media")
        self.news = Platform.objects.create(
            slug="berita-uji", display_name="Berita Uji",
            channel_type=Platform.CHANNEL_NEWS,
        )
        self.social = Platform.objects.create(
            slug="social-uji", display_name="Social Uji",
            channel_type=Platform.CHANNEL_SOCIAL,
        )
        category = Category.objects.create(name="Kesehatan Uji")
        subcategory = SubCategory.objects.create(category=category, name="Pangan Uji")
        self.issue = Issue.objects.create(
            subcategory=subcategory,
            name="Keamanan Pangan Uji",
            keywords=["keracunan uji", "makanan uji"],
        )
        self.actor = PoliticalActor.objects.create(
            project=self.project,
            name="Pemkab Uji",
            actor_type=PoliticalActor.TYPE_ORGANIZATION,
            keywords=["pemkab uji"],
        )
        MonitoringKeyword.objects.create(
            project=self.project, keyword="pemkab uji", created_by="tester"
        )
        self.start = datetime(2026, 7, 21, 8, tzinfo=datetime_timezone.utc)

    def _mention(self, *, platform, sentiment, day=0, content_type=Mention.CONTENT_POST,
                 parent=None, reported_comments=0, url=None):
        mention = Mention.objects.create(
            project=self.project,
            platform=platform,
            author_handle=f"author-{Mention.objects.count()}",
            content_snippet="pemkab uji membahas keracunan uji",
            sentiment=sentiment,
            sentiment_confidence=0.9,
            sentiment_model="test-model",
            emotion=Mention.EMOTION_ANGER,
            posted_at=self.start + timedelta(days=day),
            source_url=url,
            content_type=content_type,
            parent=parent,
            reported_comment_count=reported_comments,
        )
        IssueLabel.objects.create(mention=mention, issue=self.issue)
        mention.political_actors.add(self.actor)
        return mention

    def test_report_separates_channels_and_includes_date_endpoints(self):
        self._mention(
            platform=self.news, sentiment=Mention.SENTIMENT_NEUTRAL, day=0,
            url="https://news.example.test/a",
        )
        self._mention(
            platform=self.social, sentiment=Mention.SENTIMENT_NEGATIVE, day=6,
            url="https://social.example.test/p/1",
        )
        self._mention(
            platform=self.social, sentiment=Mention.SENTIMENT_POSITIVE, day=7,
            url="https://social.example.test/p/2",
        )

        summary = selectors.laporan_summary(
            self.project,
            start_date=self.start.date(),
            end_date=(self.start + timedelta(days=6)).date(),
        )

        self.assertEqual(summary["total_mentions"], 2)
        news = next(row for row in summary["channel_rows"] if row["key"] == "news")
        social = next(row for row in summary["channel_rows"] if row["key"] == "social")
        self.assertEqual(news["count"], 1)
        self.assertEqual(social["count"], 1)
        self.assertEqual(summary["quality"]["source_coverage_pct"], 100)

    def test_comments_are_first_class_and_coverage_is_disclosed(self):
        parent = self._mention(
            platform=self.social,
            sentiment=Mention.SENTIMENT_NEUTRAL,
            reported_comments=20,
            url="https://social.example.test/p/parent",
        )
        self._mention(
            platform=self.social,
            sentiment=Mention.SENTIMENT_NEGATIVE,
            content_type=Mention.CONTENT_COMMENT,
            parent=parent,
            url="https://social.example.test/p/parent#comment-1",
        )

        summary = selectors.laporan_summary(
            self.project, start_date=self.start.date(), end_date=self.start.date()
        )

        self.assertEqual(summary["quality"]["post_count"], 1)
        self.assertEqual(summary["quality"]["comment_count"], 1)
        self.assertEqual(summary["comment_analysis"]["parent_count"], 1)
        self.assertEqual(summary["comment_analysis"]["parent_coverage_pct"], 100)
        negative = next(
            row for row in summary["comment_analysis"]["sentiment_breakdown"]
            if row["key"] == Mention.SENTIMENT_NEGATIVE
        )
        self.assertEqual(negative["pct"], 100)

    def test_actor_sentiment_is_independent_from_global_mention_sentiment(self):
        mention = self._mention(
            platform=self.news,
            sentiment=Mention.SENTIMENT_NEGATIVE,
            url="https://news.example.test/actor",
        )
        ActorSentimentAssessment.objects.create(
            mention=mention,
            actor=self.actor,
            sentiment=Mention.SENTIMENT_NEUTRAL,
            confidence=0.95,
            source=ActorSentimentAssessment.SOURCE_MANUAL,
        )

        summary = selectors.laporan_summary(
            self.project, start_date=self.start.date(), end_date=self.start.date()
        )
        actor_row = summary["actor_rows"][0]
        neutral = next(
            row for row in actor_row["sentiment_breakdown"]
            if row["key"] == Mention.SENTIMENT_NEUTRAL
        )
        self.assertEqual(neutral["pct"], 100)
        self.assertEqual(actor_row["manual_count"], 1)

    def test_pdf_renderer_produces_a_real_pdf(self):
        self._mention(
            platform=self.news,
            sentiment=Mention.SENTIMENT_NEGATIVE,
            url="https://news.example.test/pdf",
        )
        summary = selectors.laporan_summary(
            self.project, start_date=self.start.date(), end_date=self.start.date()
        )
        content = media_report_pdf.build(
            summary,
            institution=self.tenant.name,
            project_name=self.project.name,
            generated_by="Analyst",
        )
        self.assertTrue(content.startswith(b"%PDF-"))
        self.assertGreater(len(content), 5000)


class MediaAnalysisPdfViewTest(TestCase):
    def setUp(self):
        tenant = Tenant.objects.create(name="Pemkab Uji")
        self.project = Project.objects.create(tenant=tenant, name="Monitoring Media")
        user = get_user_model().objects.create_user(username="analyst", password="secret")
        AnalystProfile.objects.update_or_create(
            user=user,
            defaults={"tenant": tenant, "role": AnalystProfile.ROLE_SUPER_ADMIN},
        )
        self.client.force_login(user)

    def test_platform_generates_downloadable_pdf(self):
        response = self.client.get(
            reverse("analytics:laporan_pdf"),
            {"from": "2026-07-21", "to": "2026-07-27"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("analisis-media-20260721-20260727.pdf", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF-"))
