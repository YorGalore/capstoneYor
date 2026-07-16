from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.analytics.models import Mention
from apps.core.seed import seed_core

from ..models import MonitoredDomain, MonitoringKeyword
from ..scraping import ScrapeError, run_scan, score_sentiment


class ScoreSentimentTest(TestCase):
    def test_positive_words_win(self):
        self.assertEqual(score_sentiment("program ini berhasil dan mendapat apresiasi luas"), Mention.SENTIMENT_POSITIVE)

    def test_negative_words_win(self):
        self.assertEqual(score_sentiment("warga kecewa karena distribusi bansos gagal"), Mention.SENTIMENT_NEGATIVE)

    def test_no_signal_is_neutral(self):
        self.assertEqual(score_sentiment("pemerintah mengadakan rapat koordinasi"), Mention.SENTIMENT_NEUTRAL)


class RunScanTest(TestCase):
    def setUp(self):
        self.tenant, self.project = seed_core()
        from apps.core.models import Platform
        self.platform = Platform.objects.get(slug="berita")
        self.domain = MonitoredDomain.objects.create(
            project=self.project,
            domain="contoh-berita.co.id", adapter="RSS", feed_url="https://contoh-berita.co.id/rss.xml",
        )
        self.keyword = MonitoringKeyword.objects.create(project=self.project, keyword="pangan")

    @patch("apps.governance.scraping.fetch_feed")
    def test_matching_item_creates_mention(self, mock_fetch):
        mock_fetch.return_value = [{
            "title": "Distribusi pangan berhasil di wilayah timur",
            "link": "https://contoh-berita.co.id/artikel-1",
            "description": "warga mengapresiasi program ini",
            "posted_at": timezone.now(),
        }]
        result = run_scan(
            project=self.project, platform=self.platform,
            domains=[self.domain], keywords=[self.keyword],
        )
        self.assertEqual(result["new_mentions"], 1)
        mention = Mention.objects.get(source_url="https://contoh-berita.co.id/artikel-1")
        self.assertTrue(mention.is_scraped)
        self.assertEqual(mention.matched_keyword, "pangan")
        self.assertEqual(mention.sentiment, Mention.SENTIMENT_POSITIVE)
        self.keyword.refresh_from_db()
        self.assertEqual(self.keyword.match_count, 1)

    @patch("apps.governance.scraping.fetch_feed")
    def test_non_matching_item_is_skipped(self, mock_fetch):
        mock_fetch.return_value = [{
            "title": "Timnas menang pertandingan persahabatan",
            "link": "https://contoh-berita.co.id/artikel-2",
            "description": "",
            "posted_at": timezone.now(),
        }]
        result = run_scan(
            project=self.project, platform=self.platform,
            domains=[self.domain], keywords=[self.keyword],
        )
        self.assertEqual(result["new_mentions"], 0)
        self.assertFalse(Mention.objects.filter(source_url="https://contoh-berita.co.id/artikel-2").exists())

    @patch("apps.governance.scraping.fetch_feed")
    def test_rerun_does_not_duplicate_mentions(self, mock_fetch):
        mock_fetch.return_value = [{
            "title": "Program pangan diperluas",
            "link": "https://contoh-berita.co.id/artikel-3",
            "description": "",
            "posted_at": timezone.now(),
        }]
        run_scan(project=self.project, platform=self.platform, domains=[self.domain], keywords=[self.keyword])
        result = run_scan(project=self.project, platform=self.platform, domains=[self.domain], keywords=[self.keyword])
        self.assertEqual(result["new_mentions"], 0)
        self.assertEqual(Mention.objects.filter(source_url="https://contoh-berita.co.id/artikel-3").count(), 1)

    @patch("apps.governance.scraping.fetch_feed")
    def test_fetch_failure_marks_domain_needs_review(self, mock_fetch):
        mock_fetch.side_effect = ScrapeError("connection timed out")
        result = run_scan(project=self.project, platform=self.platform, domains=[self.domain], keywords=[self.keyword])
        self.assertEqual(result["new_mentions"], 0)
        self.assertEqual(len(result["errors"]), 1)
        self.domain.refresh_from_db()
        self.assertEqual(self.domain.status, MonitoredDomain.STATUS_NEEDS_REVIEW)

    def test_domain_without_feed_url_is_skipped(self):
        blank_domain = MonitoredDomain.objects.create(
            project=self.project, domain="belum-ada-feed.co.id", adapter="RSS"
        )
        result = run_scan(project=self.project, platform=self.platform, domains=[blank_domain], keywords=[self.keyword])
        self.assertEqual(result["sources_scanned"], 0)

    @patch("apps.governance.scraping.portal_crawler.crawl")
    def test_custom_adapter_uses_portal_crawler_and_stores_article_body(self, crawl):
        self.domain.adapter = "portal-listing"
        self.domain.save(update_fields=["adapter"])
        crawl.return_value = [{
            "title": "Bupati membahas pangan",
            "link": "https://contoh-berita.co.id/artikel-custom",
            "description": "",
            "body": "Isi lengkap program pangan berhasil dan mendapat apresiasi warga.",
            "posted_at": timezone.now(),
        }]
        result = run_scan(
            project=self.project, platform=self.platform,
            domains=[self.domain], keywords=[self.keyword],
        )
        self.assertEqual(result["new_mentions"], 1)
        mention = Mention.objects.get(source_url="https://contoh-berita.co.id/artikel-custom")
        self.assertIn("Isi lengkap", mention.content_snippet)
        self.assertEqual(mention.sentiment_model, "lexicon-v1")
        self.assertIsNotNone(mention.author)
