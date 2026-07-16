from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase

from apps.governance import portal_crawler


class PortalRegistryTest(SimpleTestCase):
    def test_all_kulon_progo_demo_publishers_have_adapters(self):
        self.assertSetEqual(
            set(portal_crawler.PORTALS),
            {
                "jogja.tribunnews.com",
                "jogjapolitan.harianjogja.com",
                "jogja.antaranews.com",
                "www.prolimannews.id",
                "rri.co.id",
                "jogja.viva.co.id",
                "www.detik.com",
                "www.purworejo24.com",
                "kominfo.kulonprogokab.go.id",
            },
        )

    @mock.patch("apps.governance.portal_crawler._get")
    @mock.patch("apps.governance.portal_crawler._robots_allows", return_value=True)
    def test_reachable_uses_registered_starter(self, mock_robots, mock_get):
        domain = mock.Mock(domain="rri.co.id", feed_url="")
        mock_get.return_value = (b"<rss />", "application/xml", "https://rri.co.id/rss")

        self.assertTrue(portal_crawler.check_reachable(domain))
        mock_robots.assert_called_once_with("https://rri.co.id/rss")
        mock_get.assert_called_once_with("https://rri.co.id/rss")


class PortalParserTest(SimpleTestCase):
    def test_rss_parser_reads_full_content(self):
        raw = b"""<?xml version='1.0'?><rss xmlns:content='urn:content'><channel><item>
        <title>Pemkab Kulon Progo berhasil</title><link>https://example.id/a</link>
        <description><![CDATA[Ringkasan berita]]></description>
        <content:encoded><![CDATA[<p>Isi artikel yang lengkap untuk dianalisis.</p>]]></content:encoded>
        <pubDate>Wed, 15 Jul 2026 09:00:00 +0700</pubDate>
        </item></channel></rss>"""
        item = portal_crawler.parse_rss(raw)[0]
        self.assertEqual(item["title"], "Pemkab Kulon Progo berhasil")
        self.assertEqual(item["body"], "Isi artikel yang lengkap untuk dianalisis.")
        self.assertEqual(item["posted_at"].year, 2026)

    def test_news_sitemap_parser_reads_title_date_and_url(self):
        raw = b"""<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'
        xmlns:news='http://www.google.com/schemas/sitemap-news/0.9'><url>
        <loc>https://example.id/a</loc><news:news>
        <news:publication_date>2026-07-15T09:00:00+07:00</news:publication_date>
        <news:title>Bupati Kulon Progo membuka acara</news:title>
        </news:news></url></urlset>"""
        item = portal_crawler.parse_sitemap(raw)[0]
        self.assertEqual(item["link"], "https://example.id/a")
        self.assertIn("Bupati Kulon Progo", item["title"])
        self.assertEqual(item["posted_at"].year, 2026)

    def test_article_parser_prefers_newsarticle_jsonld(self):
        raw = b"""<html><head><script type='application/ld+json'>
        {"@type":"NewsArticle","headline":"Judul JSON-LD",
        "datePublished":"2026-07-15T09:00:00+07:00",
        "description":"Ringkasan", "articleBody":"Isi lengkap berita."}
        </script></head><body><h1>Judul tampilan</h1></body></html>"""
        article = portal_crawler.parse_article(raw, "text/html; charset=utf-8")
        self.assertEqual(article["title"], "Judul JSON-LD")
        self.assertEqual(article["body"], "Isi lengkap berita.")


class PortalCrawlTest(SimpleTestCase):
    @mock.patch.object(
        portal_crawler, "_get",
        side_effect=portal_crawler.PortalCrawlError(
            "gagal membuka https://example.id/robots.txt: HTTP Error 404: Not Found"
        ),
    )
    def test_missing_robots_file_allows_public_resource(self, _get):
        self.assertTrue(portal_crawler._robots_allows("https://example.id/feed/"))

    @mock.patch.object(portal_crawler, "_robots_allows", return_value=True)
    @mock.patch.object(portal_crawler, "_get")
    def test_listing_opens_only_keyword_matching_article(self, get, _robots):
        listing = b"""<a href='/berita/a'>Bupati Kulon Progo membuka acara</a>
        <a href='/berita/b'>Pertandingan sepak bola</a>"""
        article = b"""<article><h1>Bupati Kulon Progo membuka acara</h1>
        <p>Pemerintah Kabupaten Kulon Progo menjelaskan program kepada warga.</p></article>"""
        get.side_effect = [
            (listing, "text/html; charset=utf-8", "https://test.portal/"),
            (article, "text/html; charset=utf-8", "https://test.portal/berita/a"),
        ]
        spec = portal_crawler.PortalSpec(
            "listing", "https://test.portal/", ("https://test.portal/berita/",)
        )
        domain = SimpleNamespace(domain="test.portal", feed_url="")
        with mock.patch.dict(portal_crawler.PORTALS, {"test.portal": spec}):
            items = portal_crawler.crawl(domain, ["Bupati Kulon Progo"])

        self.assertEqual(len(items), 1)
        self.assertIn("Pemerintah Kabupaten", items[0]["body"])
        self.assertEqual(get.call_count, 2)

    @mock.patch.object(portal_crawler, "_robots_allows", return_value=False)
    def test_denied_starter_fails_closed(self, _robots):
        domain = SimpleNamespace(domain="rri.co.id", feed_url="")
        with self.assertRaises(portal_crawler.PortalCrawlError):
            portal_crawler.crawl(domain, ["Kulon Progo"])
