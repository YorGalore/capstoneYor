from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.analytics import briefs
from apps.analytics.models import (
    Category, DailyBrief, DailyBriefIssue, Issue, IssueLabel, Mention, SubCategory,
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
        self.yesterday = timezone.localdate() - timedelta(days=1)
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


class BriefWriteAccessTest(TestCase):
    """ISS-BTX-002: brief is a DASHBOARD_PAGES member (Peninjau gets default read
    access), so the write actions need their own role check independent of the
    page-level gate. Builds brief data directly rather than through
    generate_brief(), which stays out of scope for this fix set."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        self.brief = DailyBrief.objects.create(
            project=self.project, brief_date=timezone.now().date(), status=DailyBrief.STATUS_DRAFT,
        )
        self.item = DailyBriefIssue.objects.create(
            brief=self.brief, title="Distribusi Bansos", content="isi draf", risk_level="medium",
        )
        self.viewer = User.objects.create(username="peninjau.brief")
        AnalystProfile.objects.update_or_create(
            user=self.viewer,
            defaults={"tenant": self.tenant, "role": AnalystProfile.ROLE_VIEWER},
        )
        self.client.force_login(self.viewer)

    def test_viewer_can_view_brief_page(self):
        self.assertEqual(self.client.get(reverse("analytics:brief")).status_code, 200)

    def test_viewer_cannot_generate_brief(self):
        response = self.client.post(
            reverse("analytics:generate_brief"), {"tanggal": str(self.brief.brief_date)}
        )
        self.assertEqual(response.status_code, 403)

    def test_viewer_cannot_review_issue(self):
        response = self.client.post(
            reverse("analytics:review_brief_issue", args=[self.item.pk]),
            {"action": "approve"},
        )
        self.assertEqual(response.status_code, 403)
        self.item.refresh_from_db()
        self.assertFalse(self.item.approved)

    def test_viewer_cannot_finalize_brief(self):
        response = self.client.post(reverse("analytics:finalize_brief", args=[self.brief.pk]))
        self.assertEqual(response.status_code, 403)
        self.brief.refresh_from_db()
        self.assertEqual(self.brief.status, DailyBrief.STATUS_DRAFT)


class BriefReopenTest(TestCase):
    """ISS-BTX-001: a finalized brief needs an emergency correction path,
    restricted to Tenant Admin / Super Admin."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        self.brief = DailyBrief.objects.create(
            project=self.project, brief_date=timezone.now().date(),
            status=DailyBrief.STATUS_FINAL, finalized_by="Kepala Humas", finalized_at=timezone.now(),
        )
        self.tenant_admin = User.objects.create(username="admin.brief")
        AnalystProfile.objects.update_or_create(
            user=self.tenant_admin,
            defaults={"tenant": self.tenant, "role": AnalystProfile.ROLE_TENANT_ADMIN},
        )
        self.analyst = User.objects.create(username="analis.brief")
        AnalystProfile.objects.update_or_create(
            user=self.analyst,
            defaults={"tenant": self.tenant, "role": AnalystProfile.ROLE_ANALYST},
        )

    def test_tenant_admin_can_reopen_final_brief(self):
        self.client.force_login(self.tenant_admin)
        response = self.client.post(reverse("analytics:reopen_brief", args=[self.brief.pk]))
        self.assertRedirects(
            response, f"{reverse('analytics:brief')}?tanggal={self.brief.brief_date}"
        )
        self.brief.refresh_from_db()
        self.assertEqual(self.brief.status, DailyBrief.STATUS_DRAFT)
        self.assertEqual(self.brief.finalized_by, "")
        self.assertIsNone(self.brief.finalized_at)

    def test_analyst_cannot_reopen_final_brief(self):
        # Even though Analyst can otherwise write to brief, reopening a finalized
        # institutional record is deliberately restricted further.
        self.client.force_login(self.analyst)
        response = self.client.post(reverse("analytics:reopen_brief", args=[self.brief.pk]))
        self.assertEqual(response.status_code, 403)
        self.brief.refresh_from_db()
        self.assertEqual(self.brief.status, DailyBrief.STATUS_FINAL)

    def test_cannot_reopen_a_brief_that_is_not_final(self):
        self.brief.status = DailyBrief.STATUS_DRAFT
        self.brief.save(update_fields=["status"])
        self.client.force_login(self.tenant_admin)
        response = self.client.post(reverse("analytics:reopen_brief", args=[self.brief.pk]))
        self.assertRedirects(
            response, f"{reverse('analytics:brief')}?tanggal={self.brief.brief_date}"
        )
        self.brief.refresh_from_db()
        self.assertEqual(self.brief.status, DailyBrief.STATUS_DRAFT)


class BriefTemplateRenderingTest(TestCase):
    """ISS-BTX-004 / ISS-BTX-005: the risk chip must render the Indonesian label,
    never the raw RISK_LABELS dict or the bare risk_level code."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        self.brief = DailyBrief.objects.create(
            project=self.project, brief_date=timezone.now().date(), status=DailyBrief.STATUS_DRAFT,
        )
        DailyBriefIssue.objects.create(
            brief=self.brief, title="Distribusi Bansos", content="isi draf", risk_level="medium",
        )
        self.analyst = User.objects.create(username="analis.tampilan")
        AnalystProfile.objects.update_or_create(
            user=self.analyst,
            defaults={"tenant": self.tenant, "role": AnalystProfile.ROLE_ANALYST},
        )
        self.client.force_login(self.analyst)

    def test_risk_chip_shows_indonesian_label_not_raw_dict(self):
        response = self.client.get(f"{reverse('analytics:brief')}?tanggal={self.brief.brief_date}")
        self.assertContains(response, "Risiko: Sedang")
        self.assertNotContains(response, "{'low':")

    def test_print_view_shows_indonesian_label_not_raw_code(self):
        response = self.client.get(reverse("analytics:brief_print", args=[self.brief.pk]))
        self.assertContains(response, "Risiko: Sedang")
        self.assertNotContains(response, "Risiko: medium")


class DraftBannerStrippedOnFinalizeTest(TestCase):
    """ISS-BTX-005: the generation-time draft disclaimer must not survive into a
    finalized brief's stored content."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        self.brief = DailyBrief.objects.create(
            project=self.project, brief_date=timezone.now().date(), status=DailyBrief.STATUS_DRAFT,
        )
        self.item = DailyBriefIssue.objects.create(
            brief=self.brief, title="Distribusi Bansos",
            content=briefs.DRAFT_BANNER + "\n\n## Distribusi Bansos\n\nIsi.",
            approved=True,
        )

    def test_finalize_strips_the_draft_banner_from_content(self):
        briefs.finalize(self.brief, finalized_by="Kepala Humas")
        self.item.refresh_from_db()
        self.assertNotIn(briefs.DRAFT_BANNER, self.item.content)
        self.assertTrue(self.item.content.startswith("## Distribusi Bansos"))

    def test_reopen_then_finalize_again_does_not_error_on_already_stripped_content(self):
        briefs.finalize(self.brief, finalized_by="Kepala Humas")
        briefs.reopen(self.brief, actor="Kepala Humas")
        self.item.refresh_from_db()
        self.item.approved = True
        self.item.save(update_fields=["approved"])
        briefs.finalize(self.brief, finalized_by="Kepala Humas")
        self.item.refresh_from_db()
        self.assertNotIn(briefs.DRAFT_BANNER, self.item.content)
