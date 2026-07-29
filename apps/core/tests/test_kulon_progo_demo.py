from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.analytics.models import (
    Alert,
    Coalition,
    DailyBrief,
    GovernmentProgram,
    Incident,
    Mention,
    PoliticalActor,
    PoliticalIssue,
)
from apps.core.demo_kulon_progo import (
    DEMO_PASSWORD,
    DEMO_USERNAME,
    DOMAINS,
    INCIDENT_CLUSTERS,
    KEYWORDS,
    NARRATIVE_PERSPECTIVES,
    NARRATIVE_UNATTRIBUTED_COUNT,
    NEWS_ITEMS,
    PROGRAMS,
    PROJECT_NAME,
    TENANT_NAME,
    seed_kulon_progo_demo,
)
from apps.core.models import AnalystProfile, Project, Tenant
from apps.core.seed import seed_core
from apps.governance.models import MonitoredDomain, MonitoringKeyword, ScheduledJob


class KulonProgoDemoSeedTest(TestCase):
    def setUp(self):
        # Creates the shared platform/reference rows the contextual fixture uses.
        self.national_tenant, self.national_project = seed_core()

    def test_creates_a_separate_contextual_tenant(self):
        tenant, project = seed_kulon_progo_demo()

        self.assertEqual(tenant.name, TENANT_NAME)
        self.assertEqual(project.name, PROJECT_NAME)
        self.assertNotEqual(tenant, self.national_tenant)
        self.assertEqual(Tenant.objects.count(), 2)
        self.assertEqual(Project.objects.count(), 2)
        self.assertFalse(Mention.objects.filter(project=self.national_project).exists())

        user = get_user_model().objects.get(username=DEMO_USERNAME)
        self.assertTrue(user.check_password(DEMO_PASSWORD))
        profile = AnalystProfile.objects.get(user=user)
        self.assertEqual(profile.tenant, tenant)
        self.assertEqual(profile.role, AnalystProfile.ROLE_TENANT_ADMIN)
        self.assertTrue(profile.has_political_monitoring_permission)

    def test_report_aligned_news_distribution_and_local_entities(self):
        _tenant, project = seed_kulon_progo_demo()
        mentions = Mention.objects.filter(project=project)
        curated = mentions.filter(sentiment_model="demo-curated-v1")

        self.assertEqual(curated.count(), 26)
        self.assertEqual(curated.filter(sentiment=Mention.SENTIMENT_POSITIVE).count(), 13)
        self.assertEqual(curated.filter(sentiment=Mention.SENTIMENT_NEUTRAL).count(), 7)
        self.assertEqual(curated.filter(sentiment=Mention.SENTIMENT_NEGATIVE).count(), 6)
        self.assertTrue(mentions.filter(author_handle="Kominfo Kulon Progo").exists())
        self.assertTrue(mentions.filter(content_snippet__icontains="Garongan").exists())
        self.assertFalse(mentions.filter(source_url__contains="demo.pantau.local").exists())

        self.assertEqual(PoliticalActor.objects.filter(project=project).count(), 7)
        self.assertEqual(
            GovernmentProgram.objects.filter(project=project).count(), len(PROGRAMS)
        )
        self.assertTrue(Alert.objects.filter(project=project, status=Alert.STATUS_ACTIVE).exists())

    def test_social_buzz_and_coordination_cluster_enrich_the_demo(self):
        from apps.coordination.models import CoordinationCluster

        _tenant, project = seed_kulon_progo_demo()
        mentions = Mention.objects.filter(project=project)
        social = mentions.filter(sentiment_model="demo-social-v1")

        self.assertEqual(social.count(), 220)
        # Derived rather than hardcoded: a bare total silently breaks whenever a
        # fixture layer is added, which says nothing about whether the addition
        # was correct. Assert each layer instead.
        incident_total = sum(cluster["total"] for cluster in INCIDENT_CLUSTERS)
        incident = mentions.filter(sentiment_model="demo-incident-v1")
        narrative = mentions.filter(sentiment_model="demo-narrative-v1")
        self.assertEqual(incident.count(), incident_total)
        self.assertEqual(
            narrative.count(),
            sum(item["count"] for item in NARRATIVE_PERSPECTIVES)
            + NARRATIVE_UNATTRIBUTED_COUNT,
        )
        self.assertEqual(
            mentions.count(),
            len(NEWS_ITEMS) + social.count() + incident_total + narrative.count(),
        )
        self.assertTrue(social.exclude(platform__slug="berita").exists())
        self.assertFalse(social.filter(platform__slug="berita").exists())

        cluster = CoordinationCluster.objects.get(issue__project=project)
        self.assertEqual(cluster.cluster_code, "Klaster-KP-01")
        self.assertTrue(cluster.accounts.exists())
        self.assertTrue(cluster.signals.exists())
        self.assertTrue(cluster.duplicate_samples.exists())

    def test_narrative_page_has_local_perspectives_themes_and_trends(self):
        _tenant, project = seed_kulon_progo_demo()
        issue = PoliticalIssue.objects.get(
            project=project, title="Dugaan Pungli Lurah Garongan"
        )
        narrative = Mention.objects.filter(
            project=project, issue=issue, sentiment_model="demo-narrative-v1"
        )

        self.assertEqual(narrative.filter(is_political=True).count(), 96)
        self.assertEqual(narrative.filter(coalition__isnull=False).count(), 84)
        self.assertSetEqual(
            set(
                narrative.filter(coalition__isnull=False)
                .values_list("coalition__name", flat=True)
                .distinct()
            ),
            {item["name"] for item in NARRATIVE_PERSPECTIVES},
        )
        self.assertGreaterEqual(
            narrative.exclude(theme="").values("theme").distinct().count(), 8
        )

        user = get_user_model().objects.get(username=DEMO_USERNAME)
        self.client.force_login(user)
        response = self.client.get("/narasi/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dugaan Pungli Lurah Garongan")
        self.assertContains(response, "Narasi Penanganan &amp; Klarifikasi")
        self.assertContains(response, "Narasi Kritik &amp; Akuntabilitas")
        self.assertContains(response, "proses pemeriksaan berjalan")
        self.assertContains(response, "desakan penyelesaian")
        self.assertNotContains(response, "Koalisi Nusantara Raya")

    def test_reseed_clears_legacy_fake_source_urls(self):
        _tenant, project = seed_kulon_progo_demo()
        mention = Mention.objects.filter(project=project).first()
        mention.source_url = "https://demo.pantau.local/kulon-progo/berita/13"
        mention.save(update_fields=["source_url"])

        seed_kulon_progo_demo()

        mention.refresh_from_db()
        self.assertIsNone(mention.source_url)

    def test_incident_detail_has_labeled_generated_evidence(self):
        _tenant, project = seed_kulon_progo_demo()
        incident = Incident.objects.get(
            project=project, title="Jalan Rusak Wates–Sentolo"
        )

        self.assertEqual(
            incident.evidence_image_path,
            "analytics/img/incidents/jalan-rusak-wates-sentolo-simulasi-ai.webp",
        )
        self.assertTrue(incident.evidence_is_simulated)

        user = get_user_model().objects.get(username=DEMO_USERNAME)
        self.client.force_login(user)
        response = self.client.get(f"/insiden/{incident.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bukti visual insiden")
        self.assertContains(response, "Simulasi AI")
        self.assertContains(
            response,
            "bukan foto lokasi atau bukti verifikasi lapangan",
        )

    def test_local_monitoring_configuration_and_reviewable_brief(self):
        _tenant, project = seed_kulon_progo_demo()

        self.assertSetEqual(
            set(MonitoringKeyword.objects.filter(project=project).values_list("keyword", flat=True)),
            set(KEYWORDS),
        )
        self.assertSetEqual(
            set(MonitoredDomain.objects.filter(project=project).values_list("domain", flat=True)),
            {domain for domain, _adapter, _feed_url in DOMAINS},
        )
        configured_domains = MonitoredDomain.objects.filter(project=project)
        self.assertFalse(configured_domains.filter(feed_url="").exists())
        self.assertFalse(configured_domains.exclude(adapter__startswith="portal-").exists())
        from apps.governance.seed import DEFAULT_SCHEDULES

        self.assertEqual(
            ScheduledJob.objects.filter(project=project).count(), len(DEFAULT_SCHEDULES)
        )
        brief = DailyBrief.objects.get(project=project)
        self.assertEqual(brief.status, DailyBrief.STATUS_DRAFT)
        self.assertGreaterEqual(brief.issues.count(), 1)
        self.assertTrue(brief.issues.filter(title="Dugaan Pungli Garongan").exists())

    def test_seed_is_idempotent(self):
        _tenant, project = seed_kulon_progo_demo()
        first = {
            "mentions": Mention.objects.filter(project=project).count(),
            "coalitions": Coalition.objects.filter(
                mentions__project=project
            ).distinct().count(),
            "actors": PoliticalActor.objects.filter(project=project).count(),
            "programs": GovernmentProgram.objects.filter(project=project).count(),
            "briefs": DailyBrief.objects.filter(project=project).count(),
            "jobs": ScheduledJob.objects.filter(project=project).count(),
        }

        seed_kulon_progo_demo()

        self.assertEqual(
            first,
            {
                "mentions": Mention.objects.filter(project=project).count(),
                "coalitions": Coalition.objects.filter(
                    mentions__project=project
                ).distinct().count(),
                "actors": PoliticalActor.objects.filter(project=project).count(),
                "programs": GovernmentProgram.objects.filter(project=project).count(),
                "briefs": DailyBrief.objects.filter(project=project).count(),
                "jobs": ScheduledJob.objects.filter(project=project).count(),
            },
        )
