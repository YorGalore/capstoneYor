from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from apps.core.seed import DEMO_USERNAME, seed_core
from apps.analytics.seed import seed_analytics
from apps.coordination.models import CoordinationCluster
from apps.coordination.seed import seed_coordination
from apps.governance.models import AuditLogEntry


class CoordinationViewsTest(TestCase):
    def setUp(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=100)
        seed_coordination()
        self.demo_user = get_user_model().objects.get(username=DEMO_USERNAME)
        self.client.force_login(self.demo_user)

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

    def test_escalate_cluster_rejects_get(self):
        audit_count_before = AuditLogEntry.objects.count()
        response = self.client.get("/koordinasi/Klaster-07/eskalasi/")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(AuditLogEntry.objects.count(), audit_count_before)

    def test_mark_cluster_organic_rejects_get(self):
        audit_count_before = AuditLogEntry.objects.count()
        response = self.client.get("/koordinasi/Klaster-07/tandai-organik/")
        self.assertEqual(response.status_code, 405)
        cluster = CoordinationCluster.objects.get(cluster_code="Klaster-07")
        self.assertEqual(cluster.status, CoordinationCluster.STATUS_FLAGGED)
        self.assertEqual(AuditLogEntry.objects.count(), audit_count_before)

    def test_mark_cluster_organic_rolls_back_on_audit_failure(self):
        cluster_before = CoordinationCluster.objects.get(cluster_code="Klaster-07")
        self.assertEqual(cluster_before.status, CoordinationCluster.STATUS_FLAGGED)
        audit_count_before = AuditLogEntry.objects.count()

        with patch(
            "apps.coordination.views.record_audit_entry",
            side_effect=Exception("boom"),
        ):
            with self.assertRaises(Exception):
                self.client.post("/koordinasi/Klaster-07/tandai-organik/")

        cluster_after = CoordinationCluster.objects.get(cluster_code="Klaster-07")
        self.assertEqual(cluster_after.status, CoordinationCluster.STATUS_FLAGGED)
        self.assertEqual(AuditLogEntry.objects.count(), audit_count_before)

    def test_escalate_cluster_rejects_post_without_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        audit_count_before = AuditLogEntry.objects.count()

        response = csrf_client.post("/koordinasi/Klaster-07/eskalasi/")

        self.assertEqual(response.status_code, 403)
        cluster = CoordinationCluster.objects.get(cluster_code="Klaster-07")
        self.assertEqual(cluster.status, CoordinationCluster.STATUS_FLAGGED)
        self.assertEqual(AuditLogEntry.objects.count(), audit_count_before)
