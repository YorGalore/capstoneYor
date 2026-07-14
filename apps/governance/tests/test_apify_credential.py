from unittest import mock

from django.test import TestCase

from apps.governance import apify
from apps.governance.models import ApifyCredential


class ApifyCredentialTest(TestCase):
    def test_store_valid_token_encrypts_and_masks(self):
        with mock.patch.object(apify, "verify_token", return_value=True):
            cred = apify.store_token("apify_api_0123456789abcd", updated_by="root")
        self.assertEqual(cred.status, ApifyCredential.STATUS_ACTIVE)
        self.assertTrue(cred.masked_token.endswith("abcd"))
        self.assertNotIn("0123456789abcd", cred.token_encrypted)
        self.assertEqual(apify.get_active_token(), "apify_api_0123456789abcd")

    def test_store_invalid_token_is_rejected(self):
        with mock.patch.object(apify, "verify_token", return_value=False):
            with self.assertRaises(apify.ApifyTokenInvalid):
                apify.store_token("bad-token", updated_by="root")
        self.assertIsNone(apify.get_active_token())

    def test_revoke_clears_active_token(self):
        with mock.patch.object(apify, "verify_token", return_value=True):
            apify.store_token("apify_api_0123456789abcd", updated_by="root")
        apify.revoke(updated_by="root")
        self.assertIsNone(apify.get_active_token())
        self.assertEqual(
            ApifyCredential.objects.latest("id").status, ApifyCredential.STATUS_REVOKED
        )

    def test_rotate_replaces_token(self):
        with mock.patch.object(apify, "verify_token", return_value=True):
            apify.store_token("apify_api_oldoldold1111", updated_by="root")
            apify.store_token("apify_api_newnewnew2222", updated_by="root")
        self.assertEqual(apify.get_active_token(), "apify_api_newnewnew2222")
