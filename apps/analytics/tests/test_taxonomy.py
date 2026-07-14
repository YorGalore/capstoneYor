from django.test import TestCase
from django.utils import timezone

from apps.analytics import taxonomy
from apps.analytics.models import (
    Category, Issue, IssueLabel, IssueMergeHistory, Mention, SubCategory,
)
from apps.core.models import Platform, Project, Tenant


class TaxonomyTestBase(TestCase):
    def setUp(self):
        self.platform = Platform.objects.create(slug="x", display_name="X")
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        self.cat = Category.objects.create(name="Ekonomi")
        self.sub = SubCategory.objects.create(category=self.cat, name="Energi")
        self.bbm = Issue.objects.create(subcategory=self.sub, name="Harga BBM", keywords=["bbm", "pertamax"])
        self.pangan = Issue.objects.create(subcategory=self.sub, name="Harga Pangan", keywords=["pangan", "beras"])

    def _mention(self, text):
        return Mention.objects.create(
            project=self.project, platform=self.platform, author_handle="@a",
            content_snippet=text, sentiment=Mention.SENTIMENT_NEUTRAL,
            emotion=Mention.EMOTION_TRUST, posted_at=timezone.now(),
        )


class AutoLabelTest(TaxonomyTestBase):
    def test_auto_label_assigns_matching_issue(self):
        m = self._mention("harga pertamax naik lagi")
        label = taxonomy.auto_label(m)
        self.assertEqual(label.issue, self.bbm)
        self.assertEqual(label.source, IssueLabel.SOURCE_AUTO)

    def test_unmatched_mention_goes_to_review_queue(self):
        m = self._mention("berita cuaca hari ini")
        self.assertIsNone(taxonomy.auto_label(m))
        self.assertIn(m, taxonomy.review_queue(self.project))

    def test_manual_label_not_overwritten_by_auto(self):
        m = self._mention("harga pertamax naik")  # would auto-map to BBM
        taxonomy.assign_issue(m, self.pangan, by="analis")  # manual override to Pangan
        taxonomy.auto_label(m)  # must NOT overwrite the manual decision (FR-3A.3)
        m.refresh_from_db()
        self.assertEqual(m.issue_label.issue, self.pangan)
        self.assertEqual(m.issue_label.source, IssueLabel.SOURCE_MANUAL)


class MergeTest(TaxonomyTestBase):
    def test_merge_moves_labels_and_deactivates_sources(self):
        m1 = self._mention("bbm")
        m2 = self._mention("pangan")
        taxonomy.assign_issue(m1, self.bbm, by="a")
        taxonomy.assign_issue(m2, self.pangan, by="a")

        history = taxonomy.merge_issues([self.pangan.id], self.bbm.id, performed_by="admin")

        self.pangan.refresh_from_db()
        self.assertFalse(self.pangan.is_active)
        self.assertEqual(IssueLabel.objects.filter(issue=self.bbm).count(), 2)
        self.assertIsInstance(history, IssueMergeHistory)

    def test_unmerge_restores_previous_state(self):
        m2 = self._mention("pangan")
        taxonomy.assign_issue(m2, self.pangan, by="a")
        history = taxonomy.merge_issues([self.pangan.id], self.bbm.id, performed_by="admin")

        taxonomy.unmerge(history)

        self.pangan.refresh_from_db()
        m2.refresh_from_db()
        self.assertTrue(self.pangan.is_active)
        self.assertEqual(m2.issue_label.issue, self.pangan)
        history.refresh_from_db()
        self.assertIsNotNone(history.reversed_at)

    def test_preview_top_content(self):
        m = self._mention("pangan mahal")
        m.engagement_count = 99
        m.save()
        taxonomy.assign_issue(m, self.pangan, by="a")
        preview = taxonomy.preview_top_content(self.pangan)
        self.assertIn(m, preview)
