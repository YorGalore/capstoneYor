from django.test import TestCase
from django.utils import timezone

from apps.analytics.models import PoliticalIssue
from apps.coordination.models import (
    ClusterAccount, CoordinationCluster, CoordinationSignal, DuplicateTextSample,
)


class CoordinationModelsTest(TestCase):
    def setUp(self):
        self.issue = PoliticalIssue.objects.create(
            title="Distribusi Pangan Wilayah Timur", opened_at=timezone.now(),
            owner_label="Tim Respons Cepat",
        )

    def test_cluster_ordering_by_score_desc(self):
        low = CoordinationCluster.objects.create(
            issue=self.issue, cluster_code="Klaster-03", score="0.68", detected_at=timezone.now(),
        )
        high = CoordinationCluster.objects.create(
            issue=self.issue, cluster_code="Klaster-07", score="0.91", detected_at=timezone.now(),
        )
        self.assertEqual(list(CoordinationCluster.objects.all()), [high, low])

    def test_cluster_relations(self):
        cluster = CoordinationCluster.objects.create(
            issue=self.issue, cluster_code="Klaster-07", score="0.91",
            detected_at=timezone.now(), account_count=62,
        )
        ClusterAccount.objects.create(
            cluster=cluster, handle="@suara_timur88", role=ClusterAccount.ROLE_HUB,
            reach=640000, post_count=31,
        )
        CoordinationSignal.objects.create(
            cluster=cluster, signal_type=CoordinationSignal.SIGNAL_TIME_SYNC, score="0.91",
        )
        DuplicateTextSample.objects.create(
            cluster=cluster, account_handle="@suara_timur88", posted_at=timezone.now(),
            text="sample", highlighted_phrase="rakyat timur",
        )
        self.assertEqual(cluster.accounts.count(), 1)
        self.assertEqual(cluster.signals.count(), 1)
        self.assertEqual(cluster.duplicate_samples.count(), 1)
