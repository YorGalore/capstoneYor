from django.test import TestCase

from apps.core.seed import seed_core
from apps.analytics.models import Alert, Coalition, Mention, PoliticalIssue
from apps.analytics.seed import seed_analytics


class SeedAnalyticsTest(TestCase):
    def test_seed_analytics_creates_mentions_and_political_data(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=200)

        self.assertEqual(Mention.objects.filter(project=project).count(), 200 + 1400)
        self.assertTrue(Mention.objects.filter(is_political=True).exists())
        self.assertEqual(Coalition.objects.count(), 2)
        self.assertTrue(
            PoliticalIssue.objects.filter(title="Distribusi Pangan Wilayah Timur").exists()
        )
        self.assertEqual(Alert.objects.count(), 5)

    def test_seed_analytics_is_idempotent(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=200)
        seed_analytics(project, mention_count=200)
        self.assertEqual(Mention.objects.filter(project=project).count(), 200 + 1400)
