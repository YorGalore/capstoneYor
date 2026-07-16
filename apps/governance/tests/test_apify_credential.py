from unittest import mock

from django.test import TestCase

from apps.core.models import Project, Tenant
from apps.governance import apify
from apps.governance.models import ApifyCredential


class ApifyCredentialTest(TestCase):
    def setUp(self):
        tenant = Tenant.objects.create(name="Instansi Apify")
        self.project = Project.objects.create(tenant=tenant, name="Proyek Apify")

    def test_store_valid_token_encrypts_and_masks(self):
        with mock.patch.object(apify, "verify_token", return_value=True):
            cred = apify.store_token(
                "apify_api_0123456789abcd", updated_by="root", project=self.project
            )
        self.assertEqual(cred.status, ApifyCredential.STATUS_ACTIVE)
        self.assertTrue(cred.masked_token.endswith("abcd"))
        self.assertNotIn("0123456789abcd", cred.token_encrypted)
        self.assertEqual(apify.get_active_token(self.project), "apify_api_0123456789abcd")

    def test_store_invalid_token_is_rejected(self):
        with mock.patch.object(apify, "verify_token", return_value=False):
            with self.assertRaises(apify.ApifyTokenInvalid):
                apify.store_token("bad-token", updated_by="root", project=self.project)
        self.assertIsNone(apify.get_active_token(self.project))

    def test_revoke_clears_active_token(self):
        with mock.patch.object(apify, "verify_token", return_value=True):
            apify.store_token(
                "apify_api_0123456789abcd", updated_by="root", project=self.project
            )
        apify.revoke(updated_by="root", project=self.project)
        self.assertIsNone(apify.get_active_token(self.project))
        self.assertEqual(
            ApifyCredential.objects.latest("id").status, ApifyCredential.STATUS_REVOKED
        )

    def test_rotate_replaces_token(self):
        with mock.patch.object(apify, "verify_token", return_value=True):
            apify.store_token(
                "apify_api_oldoldold1111", updated_by="root", project=self.project
            )
            apify.store_token(
                "apify_api_newnewnew2222", updated_by="root", project=self.project
            )
        self.assertEqual(apify.get_active_token(self.project), "apify_api_newnewnew2222")

    def test_rotation_and_revoke_do_not_touch_another_project(self):
        other_tenant = Tenant.objects.create(name="Instansi Apify B")
        other_project = Project.objects.create(tenant=other_tenant, name="Proyek Apify B")
        with mock.patch.object(apify, "verify_token", return_value=True):
            apify.store_token("apify_api_projectA1111", "root", self.project)
            apify.store_token("apify_api_projectB2222", "root", other_project)
            apify.store_token("apify_api_projectA3333", "root", self.project)

        self.assertEqual(apify.get_active_token(self.project), "apify_api_projectA3333")
        self.assertEqual(apify.get_active_token(other_project), "apify_api_projectB2222")
        apify.revoke("root", self.project)
        self.assertIsNone(apify.get_active_token(self.project))
        self.assertEqual(apify.get_active_token(other_project), "apify_api_projectB2222")
