from django.test import TestCase

from apps.core.seed import seed_core
from apps.analytics.seed import seed_analytics
from apps.coordination.models import CoordinationCluster
from apps.coordination.seed import seed_coordination


class SeedCoordinationTest(TestCase):
    def test_seed_coordination_creates_clusters(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=100)
        seed_coordination()

        self.assertEqual(CoordinationCluster.objects.count(), 4)
        flagged = CoordinationCluster.objects.filter(status=CoordinationCluster.STATUS_FLAGGED)
        self.assertEqual(flagged.count(), 2)
        top = CoordinationCluster.objects.first()
        self.assertEqual(top.cluster_code, "Klaster-07")
        self.assertEqual(top.accounts.count(), 3)

    def test_seed_coordination_is_idempotent(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=100)
        seed_coordination()
        seed_coordination()
        self.assertEqual(CoordinationCluster.objects.count(), 4)

    def test_seed_coordination_noop_without_issue(self):
        seed_coordination()
        self.assertEqual(CoordinationCluster.objects.count(), 0)
