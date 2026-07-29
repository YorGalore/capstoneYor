from django.test import TestCase
from django.utils import timezone

from apps.core.models import Platform, Project, Tenant
from apps.analytics.models import Alert, AlertRule, Mention
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

    def test_recent_alerts_only_returns_the_supplied_projects_alerts(self):
        other_tenant = Tenant.objects.create(name="Kementerian Lain")
        other_project = Project.objects.create(tenant=other_tenant, name="Proyek Lain")
        own_rule = AlertRule.objects.create(
            project=self.project, name="Own", condition_summary="own",
            channel=AlertRule.CHANNEL_EMAIL,
        )
        other_rule = AlertRule.objects.create(
            project=other_project, name="Other", condition_summary="other",
            channel=AlertRule.CHANNEL_EMAIL,
        )
        own_alert = Alert.objects.create(
            project=self.project, rule=own_rule, severity=Alert.SEVERITY_WARNING,
            title="Own alert", detail="own", triggered_at=timezone.now(),
        )
        Alert.objects.create(
            project=other_project, rule=other_rule, severity=Alert.SEVERITY_CRITICAL,
            title="Other alert", detail="other", triggered_at=timezone.now(),
        )

        self.assertEqual(selectors.recent_alerts(self.project), [own_alert])


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
    def test_narasi_summary_uses_configured_actor_camps(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=100)
        issue = PoliticalIssue.objects.get(title="Distribusi Pangan Wilayah Timur")

        summary = selectors.narasi_summary(issue)
        self.assertEqual(summary["issue"], issue)
        self.assertEqual(len(summary["camps"]), 2)
        total_share = sum(c["share_pct"] for c in summary["camps"])
        self.assertEqual(total_share, 100)
        self.assertTrue(all(camp["actors"] for camp in summary["camps"]))
        self.assertTrue(all(camp["overlay_points"] for camp in summary["camps"]))

    def test_narasi_summary_includes_dominant_themes(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=100)
        issue = PoliticalIssue.objects.get(title="Distribusi Pangan Wilayah Timur")

        summary = selectors.narasi_summary(issue)
        for camp_data in summary["camps"]:
            themes = camp_data["dominant_themes"]
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


class SosiografSummaryTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi Sosiograf")
        self.project = Project.objects.create(
            tenant=self.tenant, name="Proyek Sosiograf"
        )
        self.platform = Platform.objects.create(
            slug="sosio-x", display_name="Sosio X"
        )
        self.issue = PoliticalIssue.objects.create(
            project=self.project,
            title="Isu Jaringan",
            status=PoliticalIssue.STATUS_ACTIVE,
            opened_at=timezone.now(),
            owner_label="Tim",
        )

    def _mention(self, handle, *, parent=None, theme="tema sama", reach=100):
        return Mention.objects.create(
            project=self.project,
            platform=self.platform,
            author_handle=handle,
            content_snippet=f"konten {handle}",
            theme=theme,
            sentiment=Mention.SENTIMENT_NEUTRAL,
            emotion=Mention.EMOTION_TRUST,
            posted_at=timezone.now(),
            reach_estimate=reach,
            content_type=(
                Mention.CONTENT_COMMENT if parent else Mention.CONTENT_POST
            ),
            parent=parent,
        )

    def test_edges_require_observed_interaction_not_shared_theme(self):
        parent = self._mention("@induk", reach=300)
        self._mention("@pembalas", parent=parent, reach=200)
        self._mention("@tema_saja", reach=100)

        summary = selectors.sosiograf_summary(self.project)

        self.assertEqual(summary["edge_count"], 1)
        self.assertIn("balasan/komentar", summary["edges"][0]["evidence"])
        self.assertFalse(summary["edges"][0]["coordinated"])

    def test_actionable_coordination_cluster_creates_grounded_edge(self):
        from apps.coordination.models import ClusterAccount, CoordinationCluster

        self._mention("@pusat", reach=300)
        self._mention("@penguat", reach=200)
        cluster = CoordinationCluster.objects.create(
            issue=self.issue,
            cluster_code="JARINGAN-1",
            score=0.90,
            status=CoordinationCluster.STATUS_ESCALATED,
            account_count=2,
            detected_at=timezone.now(),
        )
        ClusterAccount.objects.create(
            cluster=cluster,
            handle="@pusat",
            role=ClusterAccount.ROLE_HUB,
        )
        ClusterAccount.objects.create(
            cluster=cluster,
            handle="@penguat",
            role=ClusterAccount.ROLE_AMPLIFIER,
        )

        summary = selectors.sosiograf_summary(self.project)

        self.assertEqual(summary["edge_count"], 1)
        self.assertTrue(summary["edges"][0]["coordinated"])
        self.assertIn("JARINGAN-1", summary["edges"][0]["evidence"])
