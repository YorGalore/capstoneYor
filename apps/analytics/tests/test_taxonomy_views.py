from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.analytics import taxonomy
from apps.analytics.models import (
    Category, Issue, IssueLabel, IssueMergeHistory, Mention, SubCategory,
)
from apps.core.models import AnalystProfile, Platform, Project, Tenant

User = get_user_model()


class TaxonomyViewTest(TestCase):
    def setUp(self):
        self.platform = Platform.objects.create(slug="x", display_name="X")
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        self.cat = Category.objects.create(name="Ekonomi")
        self.sub = SubCategory.objects.create(category=self.cat, name="Energi")
        self.bbm = Issue.objects.create(subcategory=self.sub, name="Harga BBM", keywords=["bbm"])
        self.pangan = Issue.objects.create(subcategory=self.sub, name="Harga Pangan", keywords=["pangan"])

        self.unlabeled = self._mention("berita cuaca hari ini")
        self.super_admin = self._user("super", AnalystProfile.ROLE_SUPER_ADMIN)
        self.analyst = self._user("analis", AnalystProfile.ROLE_ANALYST)

    def _mention(self, text):
        return Mention.objects.create(
            project=self.project, platform=self.platform, author_handle="@a",
            content_snippet=text, sentiment=Mention.SENTIMENT_NEUTRAL,
            emotion=Mention.EMOTION_TRUST, posted_at=timezone.now(),
        )

    def _user(self, name, role):
        user = User.objects.create(username=name)
        AnalystProfile.objects.update_or_create(
            user=user, defaults={"tenant": self.tenant, "role": role}
        )
        return user

    def test_analyst_denied_taxonomy_tool_page(self):
        self.client.force_login(self.analyst)
        response = self.client.get(reverse("analytics:taxonomy"))
        self.assertEqual(response.status_code, 403)

    def test_super_admin_sees_review_queue(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse("analytics:taxonomy"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "berita cuaca hari ini")

    def test_manual_assign_labels_mention(self):
        self.client.force_login(self.super_admin)
        response = self.client.post(
            reverse("analytics:assign_issue", args=[self.unlabeled.pk]),
            {"issue": self.bbm.pk},
        )
        self.assertEqual(response.status_code, 302)
        label = IssueLabel.objects.get(mention=self.unlabeled)
        self.assertEqual(label.issue, self.bbm)
        self.assertEqual(label.source, IssueLabel.SOURCE_MANUAL)

    def test_merge_via_view(self):
        m = self._mention("pangan mahal")
        taxonomy.assign_issue(m, self.pangan, by="a")
        self.client.force_login(self.super_admin)

        self.client.post(reverse("analytics:merge_issues"), {
            "source": [self.pangan.pk], "target": self.bbm.pk,
        })

        self.pangan.refresh_from_db()
        self.assertFalse(self.pangan.is_active)
        self.assertEqual(IssueLabel.objects.get(mention=m).issue, self.bbm)
        self.assertTrue(IssueMergeHistory.objects.exists())

    def test_unmerge_via_view(self):
        m = self._mention("pangan mahal")
        taxonomy.assign_issue(m, self.pangan, by="a")
        history = taxonomy.merge_issues([self.pangan.pk], self.bbm.pk, performed_by="admin")
        self.client.force_login(self.super_admin)

        self.client.post(reverse("analytics:unmerge_issues", args=[history.pk]))

        self.pangan.refresh_from_db()
        self.assertTrue(self.pangan.is_active)
        self.assertEqual(IssueLabel.objects.get(mention=m).issue, self.pangan)
