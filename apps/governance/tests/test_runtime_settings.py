from django.test import TestCase

from apps.governance.models import RuntimeSetting
from apps.governance.runtime import (
    RESERVED_KEYS,
    RuntimeSettingReserved,
    get_setting,
    masked_value,
    set_setting,
)


class RuntimeSettingServiceTest(TestCase):
    def test_secret_value_is_encrypted_at_rest_but_readable(self):
        set_setting("nlp.api_key", "super-secret-token", updated_by="root", is_secret=True)
        row = RuntimeSetting.objects.get(key="nlp.api_key")
        self.assertNotIn("super-secret-token", row.value)  # ciphertext at rest
        self.assertEqual(get_setting("nlp.api_key"), "super-secret-token")

    def test_non_secret_value_stored_plainly(self):
        set_setting("collection.default_cadence", "hourly", updated_by="root")
        row = RuntimeSetting.objects.get(key="collection.default_cadence")
        self.assertEqual(row.value, "hourly")
        self.assertEqual(get_setting("collection.default_cadence"), "hourly")

    def test_masked_value_shows_only_last_four(self):
        set_setting("nlp.api_key", "abcdefghij9999", updated_by="root", is_secret=True)
        row = RuntimeSetting.objects.get(key="nlp.api_key")
        masked = masked_value(row)
        self.assertTrue(masked.endswith("9999"))
        self.assertNotIn("abcdefghij", masked)

    def test_reserved_key_cannot_be_set_via_console(self):
        reserved = next(iter(RESERVED_KEYS))
        with self.assertRaises(RuntimeSettingReserved):
            set_setting(reserved, "http://evil", updated_by="root")

    def test_set_updates_existing_value(self):
        set_setting("collection.default_cadence", "hourly", updated_by="root")
        set_setting("collection.default_cadence", "daily", updated_by="root")
        self.assertEqual(get_setting("collection.default_cadence"), "daily")
        self.assertEqual(RuntimeSetting.objects.filter(key="collection.default_cadence").count(), 1)

    def test_missing_key_returns_default(self):
        self.assertIsNone(get_setting("does.not.exist"))
        self.assertEqual(get_setting("does.not.exist", default="fallback"), "fallback")
