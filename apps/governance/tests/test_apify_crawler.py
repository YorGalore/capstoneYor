from unittest import mock

from django.test import TestCase

from apps.governance import apify_crawler as ac


class ActorInputTest(TestCase):
    def test_twitter_input_uses_all_keywords_with_recency_window(self):
        run_input = ac.build_actor_input("x", ["bansos", "pangan"], max_results=50)
        self.assertEqual(len(run_input["searchTerms"]), 2)
        self.assertIn("bansos lang:in since:", run_input["searchTerms"][0])
        self.assertIn("until:", run_input["searchTerms"][0])
        self.assertEqual(run_input["maxItems"], 50)
        self.assertEqual(run_input["queryType"], "Top")

    def test_youtube_uses_first_keyword_only_shorts(self):
        run_input = ac.build_actor_input("youtube", ["subsidi", "bbm"], max_results=30)
        self.assertEqual(run_input["query"], "subsidi")
        self.assertEqual(run_input["type"], "shorts")
        self.assertEqual(run_input["geo"], "ID")

    def test_instagram_converts_keywords_to_hashtag_urls(self):
        run_input = ac.build_actor_input("instagram", ["harga pangan"], max_results=10)
        self.assertEqual(
            run_input["startUrls"], ["https://www.instagram.com/explore/tags/hargapangan"]
        )

    def test_tiktok_first_keyword_and_region(self):
        run_input = ac.build_actor_input("tiktok", ["bansos"], max_results=10)
        self.assertEqual(run_input["keyword"], "bansos")
        self.assertEqual(run_input["region"], "ID")

    def test_facebook_first_keyword(self):
        run_input = ac.build_actor_input("facebook", ["bansos"], max_results=5)
        self.assertEqual(run_input["query"], "bansos")
        self.assertEqual(run_input["maxResults"], 5)

    def test_default_max_results_per_platform(self):
        self.assertEqual(ac.default_max_results("x"), 1000)
        self.assertEqual(ac.default_max_results("facebook"), 20)
        self.assertEqual(ac.default_max_results("tiktok"), 100)


class ExtractionTest(TestCase):
    def test_external_id_prefix_and_stable_hash(self):
        item = {"url": "https://x.com/u/1", "text": "hi"}
        a = ac.extract_platform_content("x", item)
        b = ac.extract_platform_content("x", item)
        self.assertTrue(a["external_id"].startswith("tw-"))
        self.assertEqual(a["external_id"], b["external_id"])  # stable

    def test_item_without_url_is_dropped(self):
        self.assertIsNone(ac.extract_platform_content("x", {"text": "no url"}))

    def test_tiktok_engagement_and_reach(self):
        item = {
            "webVideoUrl": "https://tiktok.com/@a/video/1",
            "text": "pangan naik",
            "authorMeta": {"name": "akun_a"},
            "playCount": 5000, "diggCount": 120, "shareCount": 8, "commentCount": 15,
        }
        out = ac.extract_platform_content("tiktok", item)
        self.assertEqual(out["reach"], 5000)
        self.assertEqual(out["engagement"]["likes"], 120)
        self.assertEqual(out["engagement_count"], 120 + 8 + 15)
        self.assertEqual(out["author"], "akun_a")

    def test_twitter_engagement(self):
        item = {
            "url": "https://x.com/u/2", "text": "harga bbm",
            "author": {"userName": "warga"},
            "likeCount": 10, "retweetCount": 3, "replyCount": 2, "viewCount": 900,
        }
        out = ac.extract_platform_content("x", item)
        self.assertEqual(out["engagement"]["likes"], 10)
        self.assertEqual(out["engagement_count"], 10 + 3 + 2)
        self.assertEqual(out["reach"], 900)
        self.assertEqual(out["author"], "warga")


class CollectTest(TestCase):
    def test_collect_runs_actor_and_normalizes(self):
        raw = [
            {"url": "https://x.com/u/1", "text": "pangan", "likeCount": 4, "author": {"userName": "a"}},
            {"text": "no url dropped"},
        ]
        with mock.patch.object(ac, "_run_and_fetch_items", return_value=raw) as runner:
            results = ac.collect("x", ["pangan"], max_results=10, token="tok")
        runner.assert_called_once()
        self.assertEqual(len(results), 1)  # url-less item dropped
        self.assertEqual(results[0]["platform"], "x")
        self.assertEqual(results[0]["matched_keyword"], "pangan")
