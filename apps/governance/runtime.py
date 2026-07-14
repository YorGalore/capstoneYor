"""Runtime Settings service (FR-2A.9-11): database-backed configuration that is
preferred over static environment values, with encrypted secrets, masked display,
and a reserved set of keys that cannot be edited through the Configuration Console.
"""
from . import crypto
from .models import RuntimeSetting

# Reserved internal keys (e.g. service-to-service base URLs). Editing these
# through the console could silently break inter-service communication, so they
# are managed only via an engineering-controlled deployment change (FR-2A.11).
RESERVED_KEYS = {
    "internal.bff_base_url",
    "internal.identity_base_url",
    "internal.event_bus_url",
}


class RuntimeSettingReserved(Exception):
    """Raised when attempting to edit a reserved runtime setting via the console."""


def get_setting(key, default=None):
    row = RuntimeSetting.objects.filter(key=key).first()
    if row is None:
        return default
    if row.is_secret and row.value:
        return crypto.decrypt(row.value)
    return row.value


def set_setting(key, value, updated_by, is_secret=False, scope="platform", allow_reserved=False):
    if key in RESERVED_KEYS and not allow_reserved:
        raise RuntimeSettingReserved(f"Pengaturan '{key}' dilindungi dan tidak dapat diubah di sini.")
    stored = crypto.encrypt(value) if (is_secret and value) else value
    row, _ = RuntimeSetting.objects.update_or_create(
        key=key,
        defaults={
            "value": stored,
            "is_secret": is_secret,
            "scope": scope,
            "updated_by": updated_by,
        },
    )
    return row


def masked_value(row):
    """Display-safe value: masked for secrets, raw for non-secrets (FR-2A.10)."""
    if not row.is_secret:
        return row.value
    if not row.value:
        return ""
    return crypto.mask(crypto.decrypt(row.value))


def is_reserved(key):
    return key in RESERVED_KEYS
