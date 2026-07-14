"""Tests for the environment-driven production configuration.

These are not cosmetic. A misparsed DATABASE_URL points the platform at the wrong
database; a DJANGO_DEBUG typo that silently reads as False (or worse, True) turns a
security control off without anyone noticing. Every guard here exists to make a
misconfiguration fail loudly at boot instead of quietly at runtime.
"""
import os
from pathlib import Path
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from pantau import env

BASE = Path("/app")


class GetBoolTest(SimpleTestCase):
    def test_reads_common_true_spellings(self):
        for raw in ("1", "true", "True", "TRUE", "yes", "on"):
            with self.subTest(raw=raw), mock.patch.dict(os.environ, {"FLAG": raw}):
                self.assertIs(env.get_bool("FLAG", default=False), True)

    def test_reads_common_false_spellings(self):
        for raw in ("0", "false", "False", "no", "off"):
            with self.subTest(raw=raw), mock.patch.dict(os.environ, {"FLAG": raw}):
                self.assertIs(env.get_bool("FLAG", default=True), False)

    def test_unset_falls_back_to_the_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIs(env.get_bool("FLAG", default=True), True)

    def test_empty_string_is_treated_as_unset(self):
        # docker compose expands an undefined variable to "" rather than omitting it,
        # so "" must mean "not configured", not "false".
        with mock.patch.dict(os.environ, {"FLAG": ""}):
            self.assertIs(env.get_bool("FLAG", default=True), True)

    def test_an_unrecognised_value_is_rejected_rather_than_guessed(self):
        # DJANGO_DEBUG=maybe must not quietly resolve to False. A flag that governs a
        # security control has to fail loudly when it is not understood.
        with mock.patch.dict(os.environ, {"FLAG": "maybe"}):
            with self.assertRaises(ImproperlyConfigured):
                env.get_bool("FLAG", default=False)


class GetListTest(SimpleTestCase):
    def test_splits_on_commas_and_strips_surrounding_whitespace(self):
        with mock.patch.dict(os.environ, {"HOSTS": "pantau.go.id, 10.0.0.4 ,localhost"}):
            self.assertEqual(
                env.get_list("HOSTS", default=[]),
                ["pantau.go.id", "10.0.0.4", "localhost"],
            )

    def test_blank_entries_are_dropped(self):
        with mock.patch.dict(os.environ, {"HOSTS": "a,,b,"}):
            self.assertEqual(env.get_list("HOSTS", default=[]), ["a", "b"])

    def test_unset_falls_back_to_the_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(env.get_list("HOSTS", default=["fallback"]), ["fallback"])


class DatabaseConfigTest(SimpleTestCase):
    def test_parses_a_postgres_url(self):
        cfg = env.database_config("postgres://pantau:s3cret@db:5432/pantaudb", base_dir=BASE)
        self.assertEqual(cfg["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(cfg["NAME"], "pantaudb")
        self.assertEqual(cfg["USER"], "pantau")
        self.assertEqual(cfg["PASSWORD"], "s3cret")
        self.assertEqual(cfg["HOST"], "db")
        self.assertEqual(cfg["PORT"], "5432")

    def test_accepts_the_postgresql_scheme_alias(self):
        cfg = env.database_config("postgresql://u:p@db:5432/n", base_dir=BASE)
        self.assertEqual(cfg["ENGINE"], "django.db.backends.postgresql")

    def test_percent_encoded_password_is_decoded(self):
        # A generated password containing "@" or "/" arrives percent-encoded. Handing
        # the raw escape sequence to the driver authenticates with the wrong password,
        # which surfaces as a baffling "password authentication failed" at boot.
        cfg = env.database_config(
            "postgres://u:p%40ss%2Fword@db:5432/n", base_dir=BASE
        )
        self.assertEqual(cfg["PASSWORD"], "p@ss/word")

    def test_keeps_connections_warm_across_requests(self):
        # Every gunicorn worker otherwise opens a fresh Postgres connection per
        # request, which is pure latency on a dashboard that issues many small reads.
        cfg = env.database_config("postgres://u:p@db:5432/n", base_dir=BASE)
        self.assertEqual(cfg["CONN_MAX_AGE"], 60)

    def test_falls_back_to_sqlite_when_no_url_is_configured(self):
        cfg = env.database_config(None, base_dir=BASE)
        self.assertEqual(cfg["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(cfg["NAME"], BASE / "db.sqlite3")

    def test_an_unsupported_scheme_is_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            env.database_config("mysql://u:p@db:3306/n", base_dir=BASE)


class SecretKeyTest(SimpleTestCase):
    def test_uses_the_configured_key(self):
        with mock.patch.dict(os.environ, {"DJANGO_SECRET_KEY": "a-real-key"}):
            self.assertEqual(env.get_secret_key(debug=False), "a-real-key")

    def test_debug_mode_falls_back_to_a_throwaway_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertTrue(env.get_secret_key(debug=True))

    def test_production_without_a_secret_key_refuses_to_start(self):
        # Booting with a known key means every session cookie and password-reset token
        # in the deployment is forgeable by anyone who has read this repository.
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ImproperlyConfigured):
                env.get_secret_key(debug=False)

    def test_production_rejects_the_development_key_even_if_passed_explicitly(self):
        # Copying the dev key into DJANGO_SECRET_KEY must not be a way around the guard.
        with mock.patch.dict(os.environ, {"DJANGO_SECRET_KEY": env.DEV_SECRET_KEY}):
            with self.assertRaises(ImproperlyConfigured):
                env.get_secret_key(debug=False)


class AllowedHostsTest(SimpleTestCase):
    def test_debug_defaults_to_loopback(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                env.get_allowed_hosts(debug=True), ["localhost", "127.0.0.1", "[::1]"]
            )

    def test_production_requires_hosts_to_be_declared(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ImproperlyConfigured):
                env.get_allowed_hosts(debug=False)

    def test_production_rejects_a_wildcard_host(self):
        # ALLOWED_HOSTS=["*"] disables Host-header validation, which is what makes
        # cache-poisoning and password-reset-link poisoning possible.
        with mock.patch.dict(os.environ, {"DJANGO_ALLOWED_HOSTS": "pantau.go.id,*"}):
            with self.assertRaises(ImproperlyConfigured):
                env.get_allowed_hosts(debug=False)

    def test_production_accepts_explicit_hosts(self):
        with mock.patch.dict(os.environ, {"DJANGO_ALLOWED_HOSTS": "pantau.go.id"}):
            self.assertEqual(env.get_allowed_hosts(debug=False), ["pantau.go.id"])
