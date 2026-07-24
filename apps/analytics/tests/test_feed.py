from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.analytics.models import Mention
from apps.core.models import AnalystProfile, Platform, Project, Tenant

User = get_user_model()


class FeedViewTest(TestCase):
    def setUp(self):
        self.x = Platform.objects.create(slug="x", display_name="X")
        self.ig = Platform.objects.create(slug="instagram", display_name="Instagram")
        self.tenant_a = Tenant.objects.create(name="Instansi A")
        self.tenant_b = Tenant.objects.create(name="Instansi B")
        self.project_a = Project.objects.create(tenant=self.tenant_a, name="Proyek A")
        self.project_b = Project.objects.create(tenant=self.tenant_b, name="Proyek B")

        self._mention(self.project_a, self.x, "@pos_a", Mention.SENTIMENT_POSITIVE)
        self._mention(self.project_a, self.ig, "@neg_a", Mention.SENTIMENT_NEGATIVE)
        self._mention(self.project_b, self.x, "@only_b", Mention.SENTIMENT_POSITIVE)

        self.super_admin = self._user("super", AnalystProfile.ROLE_SUPER_ADMIN, self.tenant_a)
        self.analyst = self._user("analis", AnalystProfile.ROLE_ANALYST, self.tenant_a)

    def _mention(self, project, platform, handle, sentiment):
        return Mention.objects.create(
            project=project, platform=platform, author_handle=handle,
            content_snippet="teks", sentiment=sentiment, emotion=Mention.EMOTION_TRUST,
            posted_at=timezone.now(),
        )

    def _user(self, name, role, tenant):
        user = User.objects.create(username=name)
        AnalystProfile.objects.update_or_create(
            user=user, defaults={"tenant": tenant, "role": role}
        )
        return user

    def test_analyst_has_feed_access_by_default(self):
        # ISS-FW-001: sentiment correction (FR-5.3) is core Analyst work, so read
        # access to the feed it operates on must not require a manual grant.
        self.client.force_login(self.analyst)
        response = self.client.get(reverse("analytics:feed"))
        self.assertEqual(response.status_code, 200)

    def test_viewer_has_read_only_feed_access_by_default(self):
        # Feed joined DASHBOARD_PAGES (ISS-FW-001), so Peninjau's default read
        # access follows too — consistent with every other dashboard page.
        # Write access (sentiment correction) stays blocked; see test_correction.py.
        viewer = self._user("peninjau", AnalystProfile.ROLE_VIEWER, self.tenant_a)
        self.client.force_login(viewer)
        response = self.client.get(reverse("analytics:feed"))
        self.assertEqual(response.status_code, 200)

    def test_super_admin_sees_feed(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse("analytics:feed"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "@pos_a")

    def test_feed_is_tenant_scoped(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse("analytics:feed"))
        self.assertContains(response, "@pos_a")
        self.assertNotContains(response, "@only_b")

    def test_feed_filters_by_platform(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse("analytics:feed"), {"platform": "instagram"})
        self.assertContains(response, "@neg_a")
        self.assertNotContains(response, "@pos_a")

    def test_feed_filters_by_sentiment(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse("analytics:feed"), {"sentiment": "negative"})
        self.assertContains(response, "@neg_a")
        self.assertNotContains(response, "@pos_a")

    def test_feed_filters_by_author(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse("analytics:feed"), {"author": "pos_a"})
        self.assertContains(response, "@pos_a")
        self.assertNotContains(response, "@neg_a")

    def test_feed_does_not_link_to_legacy_demo_source(self):
        mention = Mention.objects.filter(project=self.project_a).first()
        mention.source_url = "https://demo.pantau.local/kulon-progo/berita/13"
        mention.save(update_fields=["source_url"])

        self.client.force_login(self.super_admin)
        response = self.client.get(reverse("analytics:feed"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(
            response,
            'href="https://demo.pantau.local/kulon-progo/berita/13"',
        )
