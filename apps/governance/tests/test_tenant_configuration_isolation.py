from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.core.models import AnalystProfile, Platform, Project, Tenant
from apps.governance import apify, orchestrator
from apps.governance.models import (
    ApifyCredential,
    CollectionRun,
    MonitoredDomain,
    MonitoringKeyword,
    PlatformIntegration,
    ScheduledJob,
)


class TenantConfigurationIsolationTest(TestCase):
    def setUp(self):
        self.tenant_a = Tenant.objects.create(name="Instansi A")
        self.project_a = Project.objects.create(tenant=self.tenant_a, name="Proyek A")
        self.tenant_b = Tenant.objects.create(name="Instansi B")
        self.project_b = Project.objects.create(tenant=self.tenant_b, name="Proyek B")
        self.user_a = get_user_model().objects.create_user("analyst-a")
        AnalystProfile.objects.update_or_create(
            user=self.user_a,
            defaults={"tenant": self.tenant_a, "role": AnalystProfile.ROLE_TENANT_ADMIN},
        )
        self.client.force_login(self.user_a)

        self.platform = Platform.objects.create(
            slug="x", display_name="X", method=Platform.METHOD_APIFY
        )
        self.integration_a = PlatformIntegration.objects.create(
            project=self.project_a,
            platform=self.platform,
            method=PlatformIntegration.METHOD_APIFY,
        )
        self.integration_b = PlatformIntegration.objects.create(
            project=self.project_b,
            platform=self.platform,
            method=PlatformIntegration.METHOD_APIFY,
        )
        self.keyword_a = MonitoringKeyword.objects.create(
            project=self.project_a, keyword="pangan-a"
        )
        self.keyword_b = MonitoringKeyword.objects.create(
            project=self.project_b, keyword="rahasia-b"
        )
        self.domain_a = MonitoredDomain.objects.create(
            project=self.project_a, domain="a.example", adapter="RSS"
        )
        self.domain_b = MonitoredDomain.objects.create(
            project=self.project_b, domain="b.example", adapter="RSS"
        )

    def test_configuration_page_only_lists_active_project_rows(self):
        response = self.client.get("/konfigurasi/")
        self.assertContains(response, "pangan-a")
        self.assertContains(response, "a.example")
        self.assertNotContains(response, "rahasia-b")
        self.assertNotContains(response, "b.example")

    def test_cannot_mutate_another_projects_objects_by_guessing_ids(self):
        self.assertEqual(
            self.client.post(
                f"/konfigurasi/kata-kunci/{self.keyword_b.pk}/toggle/"
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                f"/konfigurasi/domain/{self.domain_b.pk}/hapus/"
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                f"/konfigurasi/integrasi/{self.integration_b.pk}/toggle/"
            ).status_code,
            404,
        )

    def test_new_configuration_is_owned_by_active_project(self):
        self.client.post("/konfigurasi/kata-kunci/tambah/", {"keyword": "subsidi"})
        self.client.post(
            "/konfigurasi/domain/tambah/",
            {"domain": "news.example", "adapter": "RSS", "feed_url": ""},
        )
        self.assertTrue(
            MonitoringKeyword.objects.filter(project=self.project_a, keyword="subsidi").exists()
        )
        self.assertTrue(
            MonitoredDomain.objects.filter(project=self.project_a, domain="news.example").exists()
        )

    def test_tenant_admin_manages_only_own_apify_credential(self):
        with mock.patch.object(apify, "verify_token", return_value=True):
            apify.store_token("apify_api_TENANT_B_2222", "admin-b", self.project_b)
            response = self.client.post(
                "/konfigurasi/apify/simpan/",
                {"token": "apify_api_TENANT_A_1111"},
                follow=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "apify_api_TENANT_A_1111")
        self.assertEqual(apify.get_active_token(self.project_a), "apify_api_TENANT_A_1111")
        self.assertEqual(apify.get_active_token(self.project_b), "apify_api_TENANT_B_2222")
        self.assertEqual(
            ApifyCredential.objects.filter(
                project=self.project_a,
                status=ApifyCredential.STATUS_ACTIVE,
            ).count(),
            1,
        )

        self.client.post("/konfigurasi/apify/cabut/")
        self.assertIsNone(apify.get_active_token(self.project_a))
        self.assertEqual(apify.get_active_token(self.project_b), "apify_api_TENANT_B_2222")

    def test_schedule_mutation_is_project_scoped(self):
        job_b = ScheduledJob.objects.create(
            project=self.project_b,
            job_type=ScheduledJob.JOB_COLLECT,
            cadence_minutes=60,
        )
        response = self.client.post(
            f"/konfigurasi/jadwal/{job_b.pk}/ubah/",
            {"cadence_minutes": "5", "enabled": "on"},
        )
        self.assertEqual(response.status_code, 404)

    @mock.patch.object(orchestrator.apify_crawler, "collect", return_value=[])
    def test_orchestrator_uses_only_project_configuration(self, collect):
        self.integration_a.is_active = False
        self.integration_a.save(update_fields=["is_active"])
        runs = orchestrator.run_apify_collection(self.project_a, token="tok")
        self.assertEqual(runs, [])
        collect.assert_not_called()

    @mock.patch.object(orchestrator.apify_crawler, "collect", return_value=[])
    def test_overlap_and_collection_ledger_are_per_project(self, collect):
        CollectionRun.objects.create(
            project=self.project_b,
            source="x",
            status=CollectionRun.STATUS_RUNNING,
        )
        runs = orchestrator.run_apify_collection(self.project_a, token="tok")
        self.assertEqual(runs[0].project, self.project_a)
        self.assertEqual(runs[0].status, CollectionRun.STATUS_COMPLETED)
        collect.assert_called_once()


class ConfigurationMutationPermissionTest(TestCase):
    def setUp(self):
        tenant = Tenant.objects.create(name="Instansi")
        self.project = Project.objects.create(tenant=tenant, name="Proyek")
        self.user = get_user_model().objects.create_user("viewer")
        AnalystProfile.objects.update_or_create(
            user=self.user,
            defaults={"tenant": tenant, "role": AnalystProfile.ROLE_VIEWER},
        )
        self.client.force_login(self.user)

    def test_configuration_mutations_enforce_page_permission(self):
        endpoints = [
            ("/konfigurasi/kata-kunci/tambah/", {"keyword": "x"}),
            ("/konfigurasi/domain/tambah/", {"domain": "x.test", "adapter": "RSS"}),
            ("/konfigurasi/apify/simpan/", {"token": "secret"}),
            ("/konfigurasi/apify/cabut/", {}),
            ("/konfigurasi/pindai/", {}),
        ]
        for url, payload in endpoints:
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url, payload).status_code, 403)
