from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.analytics.models import Mention
from apps.core.models import AnalystProfile, Platform, Project, Tenant
from apps.core.selectors import (
    get_active_tenant,
    scope_to_tenant,
    visible_projects,
)

User = get_user_model()


class TenantIsolationTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.platform = Platform.objects.create(slug="x", display_name="X")

        self.tenant_a = Tenant.objects.create(name="Instansi A")
        self.tenant_b = Tenant.objects.create(name="Instansi B")
        self.project_a = Project.objects.create(tenant=self.tenant_a, name="Proyek A")
        self.project_b = Project.objects.create(tenant=self.tenant_b, name="Proyek B")

        self._mention(self.project_a, "@a1")
        self._mention(self.project_a, "@a2")
        self._mention(self.project_b, "@b1")

        self.user_a = User.objects.create(username="user_a")
        AnalystProfile.objects.update_or_create(
            user=self.user_a, defaults={"tenant": self.tenant_a, "role": AnalystProfile.ROLE_ANALYST}
        )

    def _mention(self, project, handle):
        return Mention.objects.create(
            project=project,
            platform=self.platform,
            author_handle=handle,
            content_snippet="teks",
            sentiment=Mention.SENTIMENT_NEUTRAL,
            emotion=Mention.EMOTION_TRUST,
            posted_at=timezone.now(),
        )

    def _request(self, user):
        request = self.factory.get("/ringkasan/")
        request.user = user
        return request

    def test_get_active_tenant(self):
        self.assertEqual(get_active_tenant(self._request(self.user_a)), self.tenant_a)

    def test_visible_projects_only_active_tenant(self):
        projects = visible_projects(self._request(self.user_a))
        self.assertIn(self.project_a, projects)
        self.assertNotIn(self.project_b, projects)

    def test_scope_to_tenant_excludes_other_tenant_mentions(self):
        scoped = scope_to_tenant(Mention.objects.all(), self._request(self.user_a))
        handles = set(scoped.values_list("author_handle", flat=True))
        self.assertEqual(handles, {"@a1", "@a2"})

    def test_ringkasan_view_excludes_other_tenant_mentions(self):
        self.client.force_login(self.user_a)
        response = self.client.get("/ringkasan/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["summary"]["total_mentions"], 2)
