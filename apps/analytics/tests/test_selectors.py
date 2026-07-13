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


from apps.analytics.models import PoliticalIssue
from apps.coordination.seed import seed_coordination
from apps.core.seed import seed_core
from apps.analytics.seed import seed_analytics


class WarRoomSummaryTest(TestCase):
    def test_war_room_summary_shape(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=100)
        seed_coordination()
        issue = PoliticalIssue.objects.get(title="Distribusi Pangan Wilayah Timur")

        summary = selectors.war_room_summary(issue)
        self.assertEqual(summary["issue"], issue)
        self.assertGreaterEqual(summary["coordinated_cluster_count"], 0)
        self.assertIn("negative_points", summary["timeline_chart"])
        self.assertIsInstance(summary["hotspots"], list)


class NarasiSummaryTest(TestCase):
    def test_narasi_summary_splits_by_coalition(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=100)
        issue = PoliticalIssue.objects.get(title="Distribusi Pangan Wilayah Timur")

        summary = selectors.narasi_summary(issue)
        self.assertEqual(summary["issue"], issue)
        self.assertEqual(len(summary["coalitions"]), 2)
        total_share = sum(c["share_pct"] for c in summary["coalitions"])
        self.assertGreater(total_share, 0)
        self.assertIn("series", summary["overlay_chart"])

    def test_narasi_summary_includes_dominant_themes(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=100)
        issue = PoliticalIssue.objects.get(title="Distribusi Pangan Wilayah Timur")

        summary = selectors.narasi_summary(issue)
        for coalition_data in summary["coalitions"]:
            themes = coalition_data["dominant_themes"]
            self.assertTrue(themes, "expected non-empty dominant themes for seeded coalition")
            for entry in themes:
                self.assertIn("theme", entry)
                self.assertIn("pct", entry)
                self.assertTrue(entry["theme"])
            # not all identical percentages -- weighted pool should show variation
            pcts = [entry["pct"] for entry in themes]
            self.assertGreater(len(set(pcts)), 1)


class RegionalSummaryTest(TestCase):
    def test_regional_summary_ranks_and_drills_down(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=300)

        summary = selectors.regional_summary(project)
        self.assertLessEqual(len(summary["province_rows"]), 10)
        self.assertIsNotNone(summary["selected"])
        self.assertIn("regencies", summary["selected"])

    def test_regional_summary_respects_selected_province(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=300)

        summary = selectors.regional_summary(project, selected_province="Maluku")
        self.assertEqual(summary["selected"]["name"], "Maluku")

    def test_regional_summary_heat_tiles_cover_all_provinces_with_real_variation(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=300)

        summary = selectors.regional_summary(project)
        heat_tiles = summary["heat_tiles"]
        # every province with any mentions is present, not just the top 10
        self.assertGreater(len(heat_tiles), 10)
        for tile in heat_tiles:
            self.assertIn("name", tile)
            self.assertGreater(tile["count"], 0)
            self.assertGreaterEqual(tile["intensity"], 0)
            self.assertLessEqual(tile["intensity"], 1)
            self.assertIn("flagged", tile)
        # the highest-volume tile should have full intensity, showing real variation
        self.assertAlmostEqual(max(t["intensity"] for t in heat_tiles), 1.0)
        intensities = {t["intensity"] for t in heat_tiles}
        self.assertGreater(len(intensities), 1, "expected varied intensity across provinces")

    def test_regional_summary_selected_includes_trend_chart(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=300)

        summary = selectors.regional_summary(project, selected_province="Maluku")
        trend_chart = summary["selected"]["trend_chart"]
        self.assertIn("points", trend_chart)
        self.assertIn("area_path", trend_chart)
        self.assertIn("labels", trend_chart)
        self.assertEqual(len(trend_chart["labels"]), 3)
        self.assertTrue(trend_chart["points"], "expected non-degenerate trend points")

    def test_regional_summary_selected_dominant_themes_exclude_blank(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=300)

        summary = selectors.regional_summary(project, selected_province="Maluku")
        themes = summary["selected"]["dominant_themes"]
        self.assertIsInstance(themes, list)
        for entry in themes:
            self.assertIn("theme", entry)
            self.assertIn("pct", entry)
            self.assertTrue(entry["theme"])
