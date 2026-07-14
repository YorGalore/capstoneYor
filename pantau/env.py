"""Environment-driven configuration for the production image.

Every helper here fails loudly rather than falling back to a permissive default. A
platform that boots with a published SECRET_KEY, an unvalidated Host header, or a
silently-misread DEBUG flag is worse than one that refuses to boot at all: the first
is a security incident nobody notices, the second is an error message.
"""
import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.core.exceptions import ImproperlyConfigured

# Used only when DEBUG is on. Publicly known by definition — it lives in the repo —
# which is exactly why get_secret_key() refuses it in production.
DEV_SECRET_KEY = "dev-only-secret-key-change-before-production"

TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}

# Reconnecting to Postgres on every request is pure latency on a dashboard that
# issues many small reads; a minute of reuse is well inside Postgres' idle timeout.
CONN_MAX_AGE = 60

ENGINES = {
    "postgres": "django.db.backends.postgresql",
    "postgresql": "django.db.backends.postgresql",
    "sqlite": "django.db.backends.sqlite3",
}


def get_bool(name, default):
    raw = os.environ.get(name, "").strip()
    if not raw:
        # docker compose expands an undefined variable to "" rather than omitting it,
        # so an empty value means "not configured", not "false".
        return default
    lowered = raw.lower()
    if lowered in TRUE_VALUES:
        return True
    if lowered in FALSE_VALUES:
        return False
    raise ImproperlyConfigured(
        f"{name}={raw!r} is not a recognised boolean. "
        f"Use one of {sorted(TRUE_VALUES | FALSE_VALUES)}."
    )


def get_list(name, default):
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


def get_secret_key(debug):
    key = os.environ.get("DJANGO_SECRET_KEY", "").strip()
    if debug:
        return key or DEV_SECRET_KEY
    if not key:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be set when DEBUG is off. Generate one with: "
            "python -c \"from django.core.management.utils import get_random_secret_key as k; print(k())\""
        )
    if key == DEV_SECRET_KEY:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY is the development key, which is published in this "
            "repository. Every session cookie and password-reset token would be forgeable."
        )
    return key


def get_allowed_hosts(debug):
    hosts = get_list("DJANGO_ALLOWED_HOSTS", default=[])
    if debug:
        return hosts or ["localhost", "127.0.0.1", "[::1]"]
    if not hosts:
        raise ImproperlyConfigured(
            "DJANGO_ALLOWED_HOSTS must list the hostnames this deployment answers to "
            "when DEBUG is off (e.g. DJANGO_ALLOWED_HOSTS=pantau.go.id)."
        )
    if "*" in hosts:
        raise ImproperlyConfigured(
            "DJANGO_ALLOWED_HOSTS may not contain '*' when DEBUG is off. A wildcard "
            "disables Host-header validation, which is what makes cache poisoning and "
            "poisoned password-reset links possible. List the hostnames explicitly."
        )
    return hosts


def database_config(url, base_dir):
    """Translate a DATABASE_URL into Django's DATABASES["default"] entry.

    Hand-rolled rather than pulling in dj-database-url: this project deliberately keeps
    its dependency surface small (the Apify client is stdlib urllib for the same reason),
    and we only ever need to speak two schemes.
    """
    if not url:
        return {
            "ENGINE": ENGINES["sqlite"],
            "NAME": Path(base_dir) / "db.sqlite3",
        }

    parsed = urlparse(url)
    engine = ENGINES.get(parsed.scheme)
    if engine is None:
        raise ImproperlyConfigured(
            f"DATABASE_URL scheme {parsed.scheme!r} is not supported. "
            f"Use one of {sorted(ENGINES)}."
        )
    if engine == ENGINES["sqlite"]:
        return {"ENGINE": engine, "NAME": Path(base_dir) / (parsed.path.lstrip("/") or "db.sqlite3")}

    return {
        "ENGINE": engine,
        "NAME": parsed.path.lstrip("/"),
        "USER": unquote(parsed.username or ""),
        # A generated password containing "@" or "/" arrives percent-encoded. Passing
        # the raw escape sequence through would authenticate with the wrong password.
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port) if parsed.port else "",
        "CONN_MAX_AGE": CONN_MAX_AGE,
    }
