from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.analytics.exports import BATCH_SIZE, iter_export_rows
from apps.analytics.models import Mention
from apps.core.models import AnalystProfile, Platform, Project, Tenant

User = get_user_model()


class ExportHelperTest(TestCase):
    def setUp(self):
        self.platform = Platform.objects.create(slug="x", display_name="X")
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")

    def _bulk(self, project, n):
        Mention.objects.bulk_create([
            Mention(
                project=project, platform=self.platform, author_handle=f"@u{i}",
                content_snippet="teks", sentiment=Mention.SENTIMENT_NEUTRAL,
                emotion=Mention.EMOTION_TRUST, posted_at=timezone.now(),
            )
            for i in range(n)
        ])

    def test_respects_row_cap(self):
        self._bulk(self.project, 5)
        rows = list(iter_export_rows(Mention.objects.all(), max_rows=3))
        self.assertEqual(len(rows), 3)

    def test_returns_all_rows_under_cap(self):
        self._bulk(self.project, 4)
        rows = list(iter_export_rows(Mention.objects.all(), max_rows=10000))
        self.assertEqual(len(rows), 4)

    def test_pulls_data_in_batches(self):
        self._bulk(self.project, 250)
        # 250 rows at batch size 100 must be fetched in 3 batched queries,
        # never one unbounded query (FR-20.3).
        with self.assertNumQueries(3):
            list(iter_export_rows(Mention.objects.all(), max_rows=10000, batch_size=BATCH_SIZE))


class ExportViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.platform = Platform.objects.create(slug="x", display_name="X")
        self.tenant_a = Tenant.objects.create(name="Instansi A")
        self.tenant_b = Tenant.objects.create(name="Instansi B")
        self.project_a = Project.objects.create(tenant=self.tenant_a, name="Proyek A")
        self.project_b = Project.objects.create(tenant=self.tenant_b, name="Proyek B")
        Mention.objects.create(
            project=self.project_a, platform=self.platform, author_handle="@only_a",
            content_snippet="teks", sentiment=Mention.SENTIMENT_NEUTRAL,
            emotion=Mention.EMOTION_TRUST, posted_at=timezone.now(),
        )
        Mention.objects.create(
            project=self.project_b, platform=self.platform, author_handle="@only_b",
            content_snippet="teks", sentiment=Mention.SENTIMENT_NEUTRAL,
            emotion=Mention.EMOTION_TRUST, posted_at=timezone.now(),
        )
        self.user_a = User.objects.create(username="user_a")
        AnalystProfile.objects.update_or_create(
            user=self.user_a,
            defaults={"tenant": self.tenant_a, "role": AnalystProfile.ROLE_ANALYST},
        )

    def test_csv_export_is_tenant_scoped(self):
        self.client.force_login(self.user_a)
        response = self.client.get("/ekspor/mention/?format=csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        body = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn("@only_a", body)
        self.assertNotIn("@only_b", body)

    def test_xlsx_export_content_type(self):
        self.client.force_login(self.user_a)
        response = self.client.get("/ekspor/mention/?format=xlsx")
        self.assertEqual(response.status_code, 200)
        self.assertIn("spreadsheetml", response["Content-Type"])

    def test_csv_export_applies_the_same_filters_as_the_feed(self):
        Mention.objects.create(
            project=self.project_a,
            platform=self.platform,
            author_handle="@matching",
            content_snippet="keluhan transportasi",
            matched_keyword="transportasi",
            sentiment=Mention.SENTIMENT_NEGATIVE,
            emotion=Mention.EMOTION_ANGER,
            content_type=Mention.CONTENT_COMMENT,
            posted_at=timezone.now(),
        )
        self.client.force_login(self.user_a)

        response = self.client.get(
            "/ekspor/mention/",
            {
                "format": "csv",
                "sentiment": Mention.SENTIMENT_NEGATIVE,
                "q": "transportasi",
                "content_type": Mention.CONTENT_COMMENT,
                "from": timezone.localdate().isoformat(),
                "to": timezone.localdate().isoformat(),
            },
        )
        body = b"".join(response.streaming_content).decode("utf-8")

        self.assertIn("@matching", body)
        self.assertNotIn("@only_a", body)
        self.assertNotIn("@only_b", body)

    def test_viewer_role_denied_export(self):
        viewer = User.objects.create(username="viewer1")
        AnalystProfile.objects.update_or_create(
            user=viewer, defaults={"tenant": self.tenant_a, "role": AnalystProfile.ROLE_VIEWER}
        )
        self.client.force_login(viewer)
        response = self.client.get("/ekspor/mention/?format=csv")
        self.assertEqual(response.status_code, 403)
