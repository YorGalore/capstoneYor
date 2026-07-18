from django.test import SimpleTestCase, TestCase

from apps.core.articles import ARTICLES, get_article


class ArticleContentTest(SimpleTestCase):
    def test_six_articles_with_unique_slugs(self):
        self.assertEqual(len(ARTICLES), 6)
        slugs = [a["slug"] for a in ARTICLES]
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_every_article_has_required_fields_and_body(self):
        required_keys = {"slug", "title", "excerpt", "category", "read_minutes", "body"}
        for article in ARTICLES:
            self.assertTrue(required_keys.issubset(article.keys()), article["slug"])
            self.assertIsInstance(article["read_minutes"], int)
            self.assertGreater(len(article["body"]), 0)
            for kind, text in article["body"]:
                self.assertIn(kind, {"h", "p"})
                self.assertTrue(text.strip())

    def test_get_article_looks_up_by_slug(self):
        first = ARTICLES[0]
        self.assertEqual(get_article(first["slug"]), first)
        self.assertIsNone(get_article("tidak-ada-slug-seperti-ini"))

    def test_every_article_body_has_at_least_2000_words(self):
        for article in ARTICLES:
            word_count = sum(len(text.split()) for _, text in article["body"])
            self.assertGreaterEqual(word_count, 2000, article["slug"])


class ArticleDetailViewTest(TestCase):
    def test_known_slug_returns_200_with_title_and_related_links(self):
        article = ARTICLES[0]
        response = self.client.get(f"/artikel/{article['slug']}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, article["title"])
        other = ARTICLES[1]
        self.assertContains(response, other["title"])

    def test_unknown_slug_returns_404(self):
        response = self.client.get("/artikel/slug-yang-tidak-ada/")
        self.assertEqual(response.status_code, 404)

    def test_landing_page_links_to_every_article(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        for article in ARTICLES:
            self.assertContains(response, f"/artikel/{article['slug']}/")
