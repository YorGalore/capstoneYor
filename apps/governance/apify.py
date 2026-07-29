"""Apify credential management (FR-2A.3/2A.4, REQ-DC-01/08): the token is entered
at runtime, validated with a live call to the Apify API, stored encrypted, and
only ever displayed masked. It can be rotated and revoked without a redeploy.

`verify_token` performs the only real network call; tests patch it at that
boundary rather than hitting Apify.
"""
import http.client
import json
import os
import urllib.error
import urllib.request

from django.utils import timezone

from . import crypto
from .models import ApifyCredential

APIFY_ME_URL = "https://api.apify.com/v2/users/me"
VERIFY_TIMEOUT_SECONDS = 10


class ApifyTokenInvalid(Exception):
    """Raised when a token fails live validation against the Apify API."""


def verify_token(token):
    """Real connectivity/auth probe against the Apify API. Returns True when the
    token authenticates successfully."""
    request = urllib.request.Request(
        APIFY_ME_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "PantauConfigConsole/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=VERIFY_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError):
        return False
    return bool(payload.get("data", {}).get("id"))


def store_token(token, updated_by, project):
    """Validate, encrypt, and store a token as the active credential (FR-2A.4)."""
    token = token.strip()
    if not verify_token(token):
        ApifyCredential.objects.create(
            project=project,
            masked_token=crypto.mask(token),
            token_encrypted="",
            status=ApifyCredential.STATUS_INVALID,
            last_verified_at=timezone.now(),
        )
        raise ApifyTokenInvalid("Token Apify gagal divalidasi terhadap API langsung.")

    # Rotation: supersede any prior active credential.
    ApifyCredential.objects.filter(
        project=project, status=ApifyCredential.STATUS_ACTIVE
    ).update(
        status=ApifyCredential.STATUS_REVOKED
    )
    return ApifyCredential.objects.create(
        project=project,
        masked_token=crypto.mask(token),
        token_encrypted=crypto.encrypt(token),
        status=ApifyCredential.STATUS_ACTIVE,
        last_verified_at=timezone.now(),
    )


def get_environment_token():
    """Return the deployment fallback without persisting or logging it."""
    return (
        os.environ.get("APIFY_API_TOKEN", "").strip()
        or os.environ.get("APIFY_KEY", "").strip()
        or None
    )


def get_active_token(project, *, allow_environment_fallback=True):
    """Resolve a project credential first, then the deployment-wide fallback."""
    cred = ApifyCredential.objects.filter(
        project=project, status=ApifyCredential.STATUS_ACTIVE
    ).order_by("-id").first()
    if cred is not None and cred.token_encrypted:
        return crypto.decrypt(cred.token_encrypted)
    if allow_environment_fallback:
        return get_environment_token()
    return None


def credential_source(project):
    """Expose readiness to the UI without exposing any credential value."""
    cred = ApifyCredential.objects.filter(
        project=project,
        status=ApifyCredential.STATUS_ACTIVE,
    ).exclude(token_encrypted="").order_by("-id").first()
    if cred is not None:
        return "project"
    if get_environment_token():
        return "environment"
    return "missing"


def revoke(updated_by, project):
    ApifyCredential.objects.filter(
        project=project, status=ApifyCredential.STATUS_ACTIVE
    ).update(
        status=ApifyCredential.STATUS_REVOKED, token_encrypted=""
    )
