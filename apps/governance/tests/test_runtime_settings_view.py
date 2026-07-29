from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.core.models import AnalystProfile
from apps.core.seed import DEMO_USERNAME, seed_core
from apps.governance import apify
from apps.governance.models import ApifyCredential, AuditLogEntry, RuntimeSetting

User = get_user_model()


class RuntimeSettingsViewTest(TestCase):
    def setUp(self):
        self.tenant, self.project = seed_core()
        self.super_admin = User.objects.get(username=DEMO_USERNAME)
        self.tenant_admin = User.objects.create(username="tadmin")
        AnalystProfile.objects.update_or_create(
            user=self.tenant_admin,
            defaults={"tenant": self.tenant, "role": AnalystProfile.ROLE_TENANT_ADMIN},
        )

    def test_super_admin_can_open_dev_ops_page(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse("governance:runtime_settings"))
        self.assertEqual(response.status_code, 200)

    def test_tenant_admin_forbidden_from_dev_ops_page(self):
        self.client.force_login(self.tenant_admin)
        response = self.client.get(reverse("governance:runtime_settings"))
        self.assertEqual(response.status_code, 403)

    def test_save_apify_token_stores_and_audits_and_never_shows_raw(self):
        self.client.force_login(self.super_admin)
        before = AuditLogEntry.objects.count()
        with mock.patch.object(apify, "verify_token", return_value=True):
            response = self.client.post(
                reverse("governance:save_apify_token"),
                {"token": "apify_api_SECRET99abcd"},
                follow=True,
            )
        self.assertEqual(response.status_code, 200)
        cred = ApifyCredential.objects.filter(status=ApifyCredential.STATUS_ACTIVE).latest("id")
        self.assertTrue(cred.masked_token.endswith("abcd"))
        self.assertEqual(AuditLogEntry.objects.count(), before + 1)
        # The raw token must never be rendered back to the browser.
        self.assertNotContains(response, "apify_api_SECRET99abcd")

    def test_invalid_apify_token_reports_error(self):
        self.client.force_login(self.super_admin)
        with mock.patch.object(apify, "verify_token", return_value=False):
            self.client.post(
                reverse("governance:save_apify_token"),
                {"token": "bad"},
                follow=True,
            )
        self.assertIsNone(apify.get_active_token(self.project))

    def test_save_runtime_setting(self):
        self.client.force_login(self.super_admin)
        self.client.post(
            reverse("governance:save_runtime_setting"),
            {"key": "collection.default_cadence", "value": "hourly", "is_secret": ""},
        )
        self.assertEqual(RuntimeSetting.objects.get(key="collection.default_cadence").value, "hourly")

    def test_real_nlp_provider_can_be_tested_from_dev_ops(self):
        from apps.analytics.nlp.base import Classification
        from apps.analytics.nlp.http_provider import HttpNlpProvider

        provider = mock.Mock(model_version="http:model-nyata")
        provider.classify.return_value = Classification(
            sentiment="positive",
            confidence=0.87,
            emotions=["joy"],
            model_version="http:model-nyata",
        )
        self.client.force_login(self.super_admin)
        with mock.patch.object(
            HttpNlpProvider, "from_config", return_value=provider
        ):
            response = self.client.post(
                reverse("governance:test_nlp_connection"),
                {"sample": "layanan berhasil"},
                follow=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Provider NLP aktif")
        self.assertTrue(
            AuditLogEntry.objects.filter(
                action="Menguji koneksi provider NLP"
            ).exists()
        )
