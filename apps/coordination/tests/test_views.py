from django.test import TestCase

from apps.core.seed import seed_core
from apps.analytics.seed import seed_analytics
from apps.coordination.models import CoordinationCluster
from apps.coordination.seed import seed_coordination
from apps.governance.models import AuditLogEntry


class CoordinationViewsTest(TestCase):
    def setUp(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=100)
        seed_coordination()

    def test_koordinasi_view_renders(self):
        response = self.client.get("/koordinasi/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Klaster-07")

    def test_mark_cluster_organic_updates_status_and_logs_audit(self):
        response = self.client.post("/koordinasi/Klaster-07/tandai-organik/")
        self.assertRedirects(response, "/koordinasi/?cluster=Klaster-07")
        cluster = CoordinationCluster.objects.get(cluster_code="Klaster-07")
        self.assertEqual(cluster.status, CoordinationCluster.STATUS_REVIEWED_ORGANIC)
        self.assertTrue(AuditLogEntry.objects.filter(target="Klaster-07").exists())

    def test_escalate_cluster_logs_audit_without_changing_status(self):
        self.client.post("/koordinasi/Klaster-07/eskalasi/")
        cluster = CoordinationCluster.objects.get(cluster_code="Klaster-07")
        self.assertEqual(cluster.status, CoordinationCluster.STATUS_FLAGGED)
        self.assertTrue(
            AuditLogEntry.objects.filter(action__icontains="tinjauan analis senior").exists()
        )
