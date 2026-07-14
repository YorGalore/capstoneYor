from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.analytics import briefs
from apps.analytics.models import (
    DailyBrief, DailyBriefIssue, DailyBriefRun, Issue, Mention, Category, SubCategory,
)
from apps.core.models import Platform, Project, Tenant
from apps.governance.models import RegulatoryDocument


class BriefGenerationTest(TestCase):
    def setUp(self):
        self.platform = Platform.objects.create(slug="x", display_name="X")
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        self.cat = Category.objects.create(name="Ekonomi")
        self.sub = SubCategory.objects.create(category=self.cat, name="Pangan")
        self.issue = Issue.objects.create(
            subcategory=self.sub, name="Distribusi Bansos", keywords=["bansos"]
        )
        RegulatoryDocument.objects.create(
            title="Permensos 1/2024",
            source_ref="Permensos No. 1/2024 Pasal 12",
            body=(
                "Penyaluran bantuan sosial kepada keluarga penerima manfaat dilakukan "
                "paling lambat 14 hari sejak penetapan."
            ),
        )
        self.yesterday = (timezone.now() - timedelta(days=1)).date()

    def _mention(self, sentiment, text="bansos terlambat disalurkan"):
        posted = timezone.now() - timedelta(days=1)
        m = Mention.objects.create(
            project=self.project, platform=self.platform, author_handle="@a",
            content_snippet=text, sentiment=sentiment, emotion=Mention.EMOTION_ANGER,
            posted_at=posted,
        )
        DailyBriefIssue  # noqa: B018 - keep import used
        from apps.analytics.models import IssueLabel
        IssueLabel.objects.create(mention=m, issue=self.issue, source=IssueLabel.SOURCE_AUTO)
        return m

    def test_generates_draft_requiring_human_review(self):
        for _ in range(8):
            self._mention(Mention.SENTIMENT_NEGATIVE)
        for _ in range(2):
            self._mention(Mention.SENTIMENT_POSITIVE)

        brief = briefs.generate(self.project, self.yesterday, triggered_by="sistem")

        # FR-30.2: never auto-published — always a draft pending review.
        self.assertEqual(brief.status, DailyBrief.STATUS_DRAFT)
        self.assertEqual(brief.issues.count(), 1)
        item = brief.issues.first()
        self.assertFalse(item.approved)
        self.assertIn("Distribusi Bansos", item.title)
        self.assertEqual(item.mention_count, 10)
        self.assertEqual(item.negative_pct, 80)

    def test_generated_content_is_labeled_a_draft(self):
        for _ in range(5):
            self._mention(Mention.SENTIMENT_NEGATIVE)
        brief = briefs.generate(self.project, self.yesterday, triggered_by="sistem")
        # FR-31.4: AI-generated narrative must be labeled draft pending review.
        self.assertIn("DRAF", brief.issues.first().content.upper())

    def test_brief_cites_regulatory_passage_with_visible_source(self):
        for _ in range(5):
            self._mention(Mention.SENTIMENT_NEGATIVE)
        brief = briefs.generate(self.project, self.yesterday, triggered_by="sistem")

        context = brief.issues.first().regulatory_context
        self.assertTrue(context)
        # FR-31.2/31.4: the source passage travels with the citation for verification.
        self.assertIn("Permensos", context[0]["source_ref"])
        self.assertIn("bantuan sosial", context[0]["passage"])

    def test_high_negative_issue_gets_elevated_risk(self):
        for _ in range(9):
            self._mention(Mention.SENTIMENT_NEGATIVE)
        brief = briefs.generate(self.project, self.yesterday, triggered_by="sistem")
        self.assertIn(brief.issues.first().risk_level, {"medium", "high"})

    def test_issues_without_signal_are_not_shortlisted(self):
        # Only positive, low-volume chatter -> nothing worth briefing leadership on.
        self._mention(Mention.SENTIMENT_POSITIVE)
        brief = briefs.generate(self.project, self.yesterday, triggered_by="sistem")
        self.assertEqual(brief.issues.count(), 0)

    def test_records_a_run_for_each_generation_attempt(self):
        self._mention(Mention.SENTIMENT_NEGATIVE)
        briefs.generate(self.project, self.yesterday, triggered_by="sistem")
        self.assertEqual(DailyBriefRun.objects.count(), 1)
        self.assertTrue(DailyBriefRun.objects.first().succeeded)


class ConcurrencyGuardTest(BriefGenerationTest):
    """FR-30.6: a scheduled regeneration and a manual request arriving close
    together must not produce duplicate or corrupted output."""

    def test_second_concurrent_generation_is_rejected_by_the_status_claim(self):
        self._mention(Mention.SENTIMENT_NEGATIVE)
        # Simulate a generation already in flight for the same date.
        DailyBrief.objects.create(
            project=self.project, brief_date=self.yesterday,
            status=DailyBrief.STATUS_GENERATING,
        )

        with self.assertRaises(briefs.BriefAlreadyGenerating):
            briefs.generate(self.project, self.yesterday, triggered_by="manual")

    def test_regeneration_replaces_issues_rather_than_duplicating_them(self):
        for _ in range(5):
            self._mention(Mention.SENTIMENT_NEGATIVE)
        briefs.generate(self.project, self.yesterday, triggered_by="sistem")
        briefs.generate(self.project, self.yesterday, triggered_by="manual")

        brief = DailyBrief.objects.get(project=self.project, brief_date=self.yesterday)
        self.assertEqual(brief.issues.count(), 1)  # not duplicated
        self.assertEqual(brief.runs.count(), 2)    # but both attempts recorded


class ReviewWorkflowTest(BriefGenerationTest):
    def _draft(self):
        for _ in range(5):
            self._mention(Mention.SENTIMENT_NEGATIVE)
        return briefs.generate(self.project, self.yesterday, triggered_by="sistem")

    def test_analyst_can_edit_and_approve_an_issue(self):
        brief = self._draft()
        item = brief.issues.first()

        briefs.edit_issue(item, content="Teks hasil suntingan analis.", edited_by="Dewi")
        briefs.approve_issue(item, approved_by="Dewi")

        item.refresh_from_db()
        self.assertEqual(item.content, "Teks hasil suntingan analis.")
        self.assertTrue(item.approved)
        self.assertEqual(item.edited_by, "Dewi")

    def test_reorder_issues(self):
        brief = self._draft()
        second = DailyBriefIssue.objects.create(
            brief=brief, title="Isu kedua", content="x", order=1
        )
        first = brief.issues.first()

        briefs.reorder(brief, [second.id, first.id])

        self.assertEqual(list(brief.issues.values_list("id", flat=True)), [second.id, first.id])

    def test_finalize_locks_the_brief(self):
        brief = self._draft()
        briefs.approve_issue(brief.issues.first(), approved_by="Dewi")

        briefs.finalize(brief, finalized_by="Pimpinan")

        brief.refresh_from_db()
        self.assertEqual(brief.status, DailyBrief.STATUS_FINAL)
        self.assertTrue(brief.is_locked)
        self.assertEqual(brief.finalized_by, "Pimpinan")

    def test_finalized_brief_cannot_be_edited(self):
        brief = self._draft()
        item = brief.issues.first()
        briefs.approve_issue(item, approved_by="Dewi")
        briefs.finalize(brief, finalized_by="Pimpinan")

        # FR-30.4: no further edits once locked.
        with self.assertRaises(briefs.BriefLocked):
            briefs.edit_issue(item, content="ubah setelah final", edited_by="Dewi")

    def test_finalized_brief_cannot_be_regenerated(self):
        brief = self._draft()
        briefs.approve_issue(brief.issues.first(), approved_by="Dewi")
        briefs.finalize(brief, finalized_by="Pimpinan")
        with self.assertRaises(briefs.BriefLocked):
            briefs.generate(self.project, self.yesterday, triggered_by="sistem")

    def test_cannot_finalize_with_unapproved_issues(self):
        brief = self._draft()
        with self.assertRaises(briefs.BriefNotReviewed):
            briefs.finalize(brief, finalized_by="Pimpinan")
