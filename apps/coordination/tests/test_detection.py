from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.analytics.models import Author, Mention, PoliticalIssue
from apps.coordination import detection
from apps.coordination.models import CoordinationCluster, CoordinationSignal
from apps.core.models import Platform, Project, Tenant


class SignalTest(TestCase):
    def test_text_similarity_detects_near_duplicates(self):
        a = "Bantuan tak kunjung sampai, rakyat timur kembali jadi penonton"
        b = "Bantuan tidak kunjung sampai, rakyat timur kembali jadi penonton!!"
        self.assertGreater(detection.text_similarity(a, b), 0.7)

    def test_text_similarity_low_for_different_text(self):
        self.assertLess(
            detection.text_similarity("harga bbm naik", "cuaca cerah di jakarta"), 0.3
        )

    def test_time_sync_score_high_when_posts_cluster_in_time(self):
        now = timezone.now()
        times = [now, now + timedelta(seconds=30), now + timedelta(seconds=45)]
        self.assertGreater(detection.time_sync_score(times), 0.7)

    def test_time_sync_score_low_when_posts_spread_out(self):
        now = timezone.now()
        times = [now, now + timedelta(hours=8), now + timedelta(hours=20)]
        self.assertLess(detection.time_sync_score(times), 0.3)

    def test_time_sync_needs_at_least_two_posts(self):
        self.assertEqual(detection.time_sync_score([timezone.now()]), 0.0)


class DetectionEngineTest(TestCase):
    def setUp(self):
        self.platform = Platform.objects.create(slug="x", display_name="X")
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        self.issue = PoliticalIssue.objects.create(
            project=self.project,
            title="Distribusi Pangan", opened_at=timezone.now(), owner_label="Humas"
        )
        self.now = timezone.now()

    def _mention(self, handle, text, offset_seconds=0):
        author, _ = Author.objects.get_or_create(platform=self.platform, handle=handle)
        return Mention.objects.create(
            project=self.project, platform=self.platform, author=author, author_handle=handle,
            content_snippet=text, sentiment=Mention.SENTIMENT_NEGATIVE,
            emotion=Mention.EMOTION_ANGER, issue=self.issue,
            posted_at=self.now + timedelta(seconds=offset_seconds),
        )

    def test_detects_coordinated_cluster_of_near_duplicate_synchronized_posts(self):
        text = "Bantuan tak kunjung sampai, rakyat timur kembali jadi penonton"
        self._mention("@akun_a", text, 0)
        self._mention("@akun_b", text + "!!", 20)
        self._mention("@akun_c", text.replace("tak", "tidak"), 40)

        clusters = detection.detect(self.project, self.issue, threshold=0.5)

        self.assertEqual(len(clusters), 1)
        cluster = clusters[0]
        self.assertEqual(cluster.status, CoordinationCluster.STATUS_FLAGGED)
        self.assertGreaterEqual(float(cluster.score), 0.5)
        self.assertEqual(cluster.account_count, 3)
        self.assertEqual(cluster.accounts.count(), 3)
        self.assertTrue(cluster.signals.filter(
            signal_type=CoordinationSignal.SIGNAL_TEXT_SIMILARITY
        ).exists())
        self.assertTrue(cluster.duplicate_samples.exists())

    def test_organic_distinct_posts_are_not_flagged(self):
        self._mention("@warga_1", "harga bbm naik lagi ya", 0)
        self._mention("@warga_2", "cuaca hari ini cerah sekali di kota", 5000)
        self._mention("@warga_3", "semoga pendidikan makin maju kedepannya", 9000)

        clusters = detection.detect(self.project, self.issue, threshold=0.5)

        self.assertEqual(clusters, [])

    def test_single_account_repeating_itself_is_not_a_cluster(self):
        text = "Bantuan tak kunjung sampai rakyat timur jadi penonton"
        self._mention("@akun_a", text, 0)
        self._mention("@akun_a", text + "!", 30)

        # A cluster requires coordination *between* accounts (FR-26.1).
        self.assertEqual(detection.detect(self.project, self.issue, threshold=0.5), [])

    def test_detection_never_takes_automated_action(self):
        text = "Bantuan tak kunjung sampai, rakyat timur kembali jadi penonton"
        self._mention("@akun_a", text, 0)
        self._mention("@akun_b", text + "!!", 20)

        clusters = detection.detect(self.project, self.issue, threshold=0.5)

        # Flagged for human review only — never auto-actioned (FR-26.2).
        self.assertEqual(clusters[0].status, CoordinationCluster.STATUS_FLAGGED)
