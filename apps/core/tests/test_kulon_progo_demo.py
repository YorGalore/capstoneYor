from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.analytics.models import (
    Alert,
    DailyBrief,
    GovernmentProgram,
    Mention,
    PoliticalActor,
)
from apps.core.demo_kulon_progo import (
    DEMO_PASSWORD,
    DEMO_USERNAME,
    DOMAINS,
    KEYWORDS,
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

        self.assertEqual(mentions.count(), 14)
        self.assertEqual(mentions.filter(sentiment=Mention.SENTIMENT_POSITIVE).count(), 7)
        self.assertEqual(mentions.filter(sentiment=Mention.SENTIMENT_NEUTRAL).count(), 4)
        self.assertEqual(mentions.filter(sentiment=Mention.SENTIMENT_NEGATIVE).count(), 3)
        self.assertEqual(mentions.filter(sentiment_model="demo-curated-v1").count(), 14)
        self.assertTrue(mentions.filter(author_handle="Kominfo Kulon Progo").exists())
        self.assertTrue(mentions.filter(content_snippet__icontains="Garongan").exists())

        self.assertEqual(PoliticalActor.objects.filter(project=project).count(), 3)
        self.assertEqual(GovernmentProgram.objects.filter(project=project).count(), 5)
        self.assertTrue(Alert.objects.filter(project=project, status=Alert.STATUS_ACTIVE).exists())

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
        self.assertEqual(ScheduledJob.objects.filter(project=project).count(), 5)
        brief = DailyBrief.objects.get(project=project)
        self.assertEqual(brief.status, DailyBrief.STATUS_DRAFT)
        self.assertGreaterEqual(brief.issues.count(), 1)
        self.assertTrue(brief.issues.filter(title="Dugaan Pungli Garongan").exists())

    def test_seed_is_idempotent(self):
        _tenant, project = seed_kulon_progo_demo()
        first = {
            "mentions": Mention.objects.filter(project=project).count(),
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
                "actors": PoliticalActor.objects.filter(project=project).count(),
                "programs": GovernmentProgram.objects.filter(project=project).count(),
                "briefs": DailyBrief.objects.filter(project=project).count(),
                "jobs": ScheduledJob.objects.filter(project=project).count(),
            },
        )
