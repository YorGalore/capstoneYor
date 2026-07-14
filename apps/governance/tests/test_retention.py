"""Tests for the data retention purge (REQ-LC-01, REQ-LC-02, REQ-LC-04).

This is the only routine in the platform that destroys data, and it is scheduled, so
nobody is watching when it runs. Every test here is about it deleting the right rows and
nothing else — an over-eager purge is unrecoverable and would take an open investigation
down with it.
"""
from django.test import TestCase
from django.utils import timezone

from apps.analytics.models import Author, Mention, PoliticalIssue
from apps.core.models import Platform, Project, Tenant
from apps.coordination.models import ClusterAccount, CoordinationCluster
from apps.governance import retention
from apps.governance.models import AuditLogEntry


class RetentionTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        self.platform = Platform.objects.create(
            slug="x", display_name="X", method=Platform.METHOD_APIFY
        )
        self.issue = PoliticalIssue.objects.create(
            title="Distribusi bansos",
            status=PoliticalIssue.STATUS_ACTIVE,
            opened_at=timezone.now(),
            owner_label="Humas",
        )

    def _mention(self, days_old, handle="warga", issue=None, content="teks"):
        author, _ = Author.objects.get_or_create(platform=self.platform, handle=handle)
        return Mention.objects.create(
            project=self.project,
            platform=self.platform,
            author=author,
            author_handle=handle,
            issue=issue,
            content_snippet=content,
            sentiment=Mention.SENTIMENT_NEUTRAL,
            emotion=Mention.EMOTION_TRUST,
            posted_at=timezone.now() - timezone.timedelta(days=days_old),
        )

    def test_mentions_older_than_the_retention_window_are_purged(self):
        old = self._mention(days_old=400)
        retention.set_retention_days(365, actor="Super Admin")

        result = retention.purge(self.project)

        self.assertEqual(result["deleted"], 1)
        self.assertFalse(Mention.objects.filter(pk=old.pk).exists())

    def test_mentions_inside_the_window_are_kept(self):
        recent = self._mention(days_old=10)
        retention.set_retention_days(365, actor="Super Admin")

        retention.purge(self.project)

        self.assertTrue(Mention.objects.filter(pk=recent.pk).exists())

    def test_retention_disabled_by_default_deletes_nothing(self):
        # Silently destroying a ministry's data because nobody set a policy would be
        # indefensible. No configured policy means no deletion.
        self._mention(days_old=5000)

        result = retention.purge(self.project)

        self.assertEqual(result["deleted"], 0)
        self.assertEqual(Mention.objects.count(), 1)

    def test_a_dry_run_reports_what_it_would_delete_without_deleting(self):
        self._mention(days_old=400)
        retention.set_retention_days(365, actor="Super Admin")

        result = retention.purge(self.project, dry_run=True)

        self.assertEqual(result["deleted"], 1)
        self.assertEqual(Mention.objects.count(), 1)

    def test_evidence_in_an_open_coordination_investigation_is_never_purged(self):
        """A flagged cluster is an open investigation. Deleting the posts underneath it
        because they crossed a date boundary destroys the evidence for a case a human is
        still reviewing, and the cluster would then point at nothing.
        """
        evidence = self._mention(days_old=400, handle="buzzer01", issue=self.issue)
        cluster = CoordinationCluster.objects.create(
            issue=self.issue,
            cluster_code="KLASTER-09",
            score="0.82",
            status=CoordinationCluster.STATUS_FLAGGED,
            detected_at=timezone.now(),
        )
        ClusterAccount.objects.create(
            cluster=cluster, handle="buzzer01", role=ClusterAccount.ROLE_HUB
        )
        retention.set_retention_days(365, actor="Super Admin")

        result = retention.purge(self.project)

        self.assertTrue(Mention.objects.filter(pk=evidence.pk).exists())
        self.assertEqual(result["deleted"], 0)
        self.assertEqual(result["protected"], 1)

    def test_a_closed_investigation_no_longer_protects_its_mentions(self):
        # Once a human has reviewed the cluster and called it organic, the case is shut
        # and the ordinary retention policy applies again.
        old = self._mention(days_old=400, handle="buzzer01", issue=self.issue)
        cluster = CoordinationCluster.objects.create(
            issue=self.issue,
            cluster_code="KLASTER-10",
            score="0.82",
            status=CoordinationCluster.STATUS_REVIEWED_ORGANIC,
            detected_at=timezone.now(),
        )
        ClusterAccount.objects.create(
            cluster=cluster, handle="buzzer01", role=ClusterAccount.ROLE_HUB
        )
        retention.set_retention_days(365, actor="Super Admin")

        retention.purge(self.project)

        self.assertFalse(Mention.objects.filter(pk=old.pk).exists())

    def test_a_purge_is_written_to_the_audit_log(self):
        # REQ-LC-04: destroying records is an act that must be attributable after the fact.
        self._mention(days_old=400)
        retention.set_retention_days(365, actor="Super Admin")

        retention.purge(self.project, actor="Penjadwal")

        entry = AuditLogEntry.objects.filter(action__startswith=retention.PURGE_ACTION).first()
        self.assertIsNotNone(entry)
        self.assertIn("Penjadwal", entry.actor_label)

    def test_a_dry_run_is_not_audited_as_a_deletion(self):
        self._mention(days_old=400)
        retention.set_retention_days(365, actor="Super Admin")

        retention.purge(self.project, dry_run=True)

        self.assertFalse(
            AuditLogEntry.objects.filter(action__startswith=retention.PURGE_ACTION).exists()
        )

    def test_purge_is_scoped_to_one_project(self):
        other_project = Project.objects.create(tenant=self.tenant, name="Proyek B")
        author, _ = Author.objects.get_or_create(platform=self.platform, handle="lain")
        theirs = Mention.objects.create(
            project=other_project,
            platform=self.platform,
            author=author,
            author_handle="lain",
            content_snippet="teks",
            sentiment=Mention.SENTIMENT_NEUTRAL,
            emotion=Mention.EMOTION_TRUST,
            posted_at=timezone.now() - timezone.timedelta(days=400),
        )
        retention.set_retention_days(365, actor="Super Admin")

        retention.purge(self.project)

        self.assertTrue(Mention.objects.filter(pk=theirs.pk).exists())
