from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.analytics.models import (
    Category, DailyBrief, Issue, IssueLabel, Mention, SubCategory,
)
from apps.core.models import AnalystProfile, Platform, Project, Tenant
from apps.governance.models import RegulatoryDocument

User = get_user_model()


class BriefViewTest(TestCase):
    def setUp(self):
        self.platform = Platform.objects.create(slug="x", display_name="X")
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        cat = Category.objects.create(name="Ekonomi")
        sub = SubCategory.objects.create(category=cat, name="Pangan")
        self.issue = Issue.objects.create(
            subcategory=sub, name="Distribusi Bansos", keywords=["bansos"]
        )
        RegulatoryDocument.objects.create(
            title="Permensos 1/2024", source_ref="Permensos No. 1/2024 Pasal 12",
            body="Penyaluran bantuan sosial dilakukan paling lambat 14 hari sejak penetapan.",
        )
        self.yesterday = (timezone.now() - timedelta(days=1)).date()
        for _ in range(6):
            m = Mention.objects.create(
                project=self.project, platform=self.platform, author_handle="@a",
                content_snippet="bansos terlambat disalurkan ke warga",
                sentiment=Mention.SENTIMENT_NEGATIVE, emotion=Mention.EMOTION_ANGER,
                posted_at=timezone.now() - timedelta(days=1),
            )
            IssueLabel.objects.create(mention=m, issue=self.issue, source=IssueLabel.SOURCE_AUTO)

        self.analyst = User.objects.create(username="analis")
        AnalystProfile.objects.update_or_create(
            user=self.analyst,
            defaults={"tenant": self.tenant, "role": AnalystProfile.ROLE_ANALYST},
        )
        self.client.force_login(self.analyst)

    def test_analyst_can_open_brief_page(self):
        response = self.client.get(reverse("analytics:brief"))
        self.assertEqual(response.status_code, 200)

    def test_generate_creates_draft_and_shows_draft_label(self):
        self.client.post(reverse("analytics:generate_brief"), {"tanggal": str(self.yesterday)})
        brief = DailyBrief.objects.get(project=self.project, brief_date=self.yesterday)
        self.assertEqual(brief.status, DailyBrief.STATUS_DRAFT)

        page = self.client.get(f"{reverse('analytics:brief')}?tanggal={self.yesterday}")
        self.assertContains(page, "DRAF")
        # FR-31.4: the retrieved source passage is visible for verification.
        self.assertContains(page, "Permensos No. 1/2024 Pasal 12")

    def test_finalize_blocked_until_every_issue_approved(self):
        self.client.post(reverse("analytics:generate_brief"), {"tanggal": str(self.yesterday)})
        brief = DailyBrief.objects.get(project=self.project, brief_date=self.yesterday)

        self.client.post(reverse("analytics:finalize_brief", args=[brief.pk]))

        brief.refresh_from_db()
        self.assertEqual(brief.status, DailyBrief.STATUS_DRAFT)  # still not final

    def test_approve_then_finalize_locks_the_brief(self):
        self.client.post(reverse("analytics:generate_brief"), {"tanggal": str(self.yesterday)})
        brief = DailyBrief.objects.get(project=self.project, brief_date=self.yesterday)
        item = brief.issues.first()

        self.client.post(
            reverse("analytics:review_brief_issue", args=[item.pk]), {"action": "approve"}
        )
        self.client.post(reverse("analytics:finalize_brief", args=[brief.pk]))

        brief.refresh_from_db()
        self.assertEqual(brief.status, DailyBrief.STATUS_FINAL)
        self.assertTrue(brief.is_locked)

    def test_editing_a_finalized_brief_is_refused(self):
        self.client.post(reverse("analytics:generate_brief"), {"tanggal": str(self.yesterday)})
        brief = DailyBrief.objects.get(project=self.project, brief_date=self.yesterday)
        item = brief.issues.first()
        self.client.post(
            reverse("analytics:review_brief_issue", args=[item.pk]), {"action": "approve"}
        )
        self.client.post(reverse("analytics:finalize_brief", args=[brief.pk]))

        self.client.post(
            reverse("analytics:review_brief_issue", args=[item.pk]),
            {"action": "save", "content": "diubah setelah final"},
        )

        item.refresh_from_db()
        self.assertNotEqual(item.content, "diubah setelah final")
