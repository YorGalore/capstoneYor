import urllib.error
from datetime import date
from unittest import mock

from django.test import TestCase

from apps.governance import apify_crawler as ac


class ActorInputTest(TestCase):
    def test_twitter_input_uses_all_keywords_with_recency_window(self):
        run_input = ac.build_actor_input("x", ["bansos", "pangan"], max_results=50)
        self.assertEqual(len(run_input["searchTerms"]), 2)
        self.assertIn("bansos lang:id since:", run_input["searchTerms"][0])
        self.assertIn("until:", run_input["searchTerms"][0])
        self.assertEqual(run_input["maxItems"], 50)
        self.assertTrue(run_input["includeSearchTerms"])

    def test_youtube_uses_all_keywords_with_total_bound(self):
        run_input = ac.build_actor_input("youtube", ["subsidi", "bbm"], max_results=30)
        self.assertEqual(run_input["searchQueries"], ["subsidi", "bbm"])
        self.assertEqual(run_input["maxResults"], 15)
        self.assertEqual(run_input["maxResultsShorts"], 0)

    def test_instagram_converts_keywords_to_hashtag_urls(self):
        run_input = ac.build_actor_input("instagram", ["harga pangan"], max_results=10)
        self.assertEqual(
            run_input["directUrls"],
            ["https://www.instagram.com/explore/tags/hargapangan/"],
        )
        self.assertEqual(run_input["resultsLimit"], 10)

    def test_tiktok_uses_all_queries_and_bounded_result_count(self):
        run_input = ac.build_actor_input("tiktok", ["bansos"], max_results=10)
        self.assertEqual(run_input["searchQueries"], ["bansos"])
        self.assertEqual(run_input["resultsPerPage"], 10)
        self.assertEqual(run_input["videoSearchDateFilter"], "PAST_24_HOURS")

    def test_facebook_uses_all_keywords(self):
        run_input = ac.build_actor_input("facebook", ["bansos"], max_results=5)
        self.assertEqual(run_input["query"], '"bansos"')
        self.assertEqual(run_input["searchType"], "latest")
        self.assertEqual(run_input["resultsCount"], 5)

    def test_facebook_compacts_long_keyword_list_under_actor_limit(self):
        run_input = ac.build_actor_input(
            "facebook",
            [
                "Bupati Kulon Progo",
                "Pemkab Kulon Progo",
                "MBG Kulon Progo",
                "SMPN 3 Wates",
                "SPPG Karangwuni",
            ],
            max_results=25,
        )
        self.assertLessEqual(len(run_input["query"]), 100)
        self.assertIn("Kulon Progo", run_input["query"])
        self.assertIn("SMPN 3 Wates", run_input["query"])

    def test_default_max_results_per_platform(self):
        self.assertEqual(ac.default_max_results("x"), 100)
        self.assertEqual(ac.default_max_results("facebook"), 50)
        self.assertEqual(ac.default_max_results("tiktok"), 100)

    def test_history_window_is_sent_to_date_capable_actors(self):
        start = date(2026, 7, 21)
        end = date(2026, 7, 27)
        twitter = ac.build_actor_input(
            "x", ["MBG Kulon Progo"], 25, start_date=start, end_date=end
        )
        facebook = ac.build_actor_input(
            "facebook", ["MBG Kulon Progo"], 25, start_date=start, end_date=end
        )
        self.assertIn("since:2026-07-21", twitter["searchTerms"][0])
        self.assertIn("until:2026-07-28", twitter["searchTerms"][0])
        self.assertEqual(twitter["end"], "2026-07-28")
        self.assertEqual(facebook["startDate"], "2026-07-21")
        self.assertEqual(facebook["endDate"], "2026-07-27")


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

    def test_historical_timestamp_is_normalized(self):
        out = ac.extract_platform_content(
            "facebook",
            {
                "url": "https://facebook.com/posts/1",
                "message": "MBG Kulon Progo",
                "timestamp": 1784595600,
                "comments_count": 4,
            },
        )
        self.assertIsNotNone(out["posted_at"])
        self.assertEqual(out["content"], "MBG Kulon Progo")
        self.assertEqual(out["engagement"]["comments"], 4)


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

    def test_historical_collect_drops_rows_outside_window_or_without_date(self):
        raw = [
            {
                "url": "https://x.com/u/in",
                "text": "pangan",
                "createdAt": "2026-07-24T03:00:00Z",
            },
            {
                "url": "https://x.com/u/out",
                "text": "pangan",
                "createdAt": "2026-07-29T03:00:00Z",
            },
            {"url": "https://x.com/u/unknown", "text": "pangan"},
        ]
        with mock.patch.object(ac, "_run_and_fetch_items", return_value=raw):
            results = ac.collect(
                "x",
                ["pangan"],
                max_results=10,
                token="tok",
                start_date=date(2026, 7, 21),
                end_date=date(2026, 7, 27),
            )
        self.assertEqual([row["url"] for row in results], ["https://x.com/u/in"])


class ApifyNetworkBoundaryTest(TestCase):
    def test_transport_failure_raises_typed_collection_error(self):
        with mock.patch.object(
            ac.urllib.request,
            "urlopen",
            side_effect=urllib.error.URLError("network down"),
        ):
            with self.assertRaises(ac.ApifyCollectionError) as raised:
                ac._run_and_fetch_items("actor-id", {"query": "pangan"}, "tok")

        self.assertIn("network down", str(raised.exception))

    def test_invalid_json_raises_typed_collection_error(self):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b"not-json"
        with mock.patch.object(ac.urllib.request, "urlopen", return_value=response):
            with self.assertRaises(ac.ApifyCollectionError):
                ac._run_and_fetch_items("actor-id", {"query": "pangan"}, "tok")

    def test_genuine_empty_dataset_is_successful(self):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b"[]"
        with mock.patch.object(ac.urllib.request, "urlopen", return_value=response):
            items = ac._run_and_fetch_items("actor-id", {"query": "pangan"}, "tok")

        self.assertEqual(items, [])

    def test_non_list_json_raises_typed_collection_error(self):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'{"error":"actor failed"}'
        with mock.patch.object(ac.urllib.request, "urlopen", return_value=response):
            with self.assertRaises(ac.ApifyCollectionError):
                ac._run_and_fetch_items("actor-id", {"query": "pangan"}, "tok")
