"""Tests for the container health endpoint.

Gunicorn behind an orchestrator needs a probe that answers honestly: a process that
is accepting sockets but cannot reach Postgres is not healthy, and reporting it as
healthy is how a broken deploy gets rolled out to every replica.
"""
from unittest import mock

from django.conf import settings
from django.db import OperationalError, connection
from django.test import SimpleTestCase, TestCase


class HealthEndpointTest(TestCase):
    def test_probe_is_reachable_without_authenticating(self):
        # LoginRequiredMiddleware is global, so without an explicit exemption the probe
        # gets a 302 to the login page — which an orchestrator reads as "not healthy"
        # and a load balancer may read as "healthy". Neither is the truth.
        response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 200)

    def test_reports_database_connectivity(self):
        response = self.client.get("/healthz/")
        self.assertEqual(response.json()["database"], "ok")

    def test_reports_unhealthy_when_the_database_is_unreachable(self):
        with mock.patch.object(
            connection, "ensure_connection", side_effect=OperationalError("down")
        ):
            response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["database"], "error")


class StaticFilesConfigTest(SimpleTestCase):
    def test_whitenoise_is_installed_to_serve_static_files(self):
        # Gunicorn does not serve static files and DEBUG=False disables Django's
        # static handler, so without WhiteNoise every stylesheet 404s in production.
        self.assertIn(
            "whitenoise.middleware.WhiteNoiseMiddleware", settings.MIDDLEWARE
        )

    def test_whitenoise_runs_immediately_after_the_security_middleware(self):
        # Ordering is load-bearing: above SecurityMiddleware it bypasses the security
        # headers; further down it sits behind session/auth work it does not need.
        middleware = list(settings.MIDDLEWARE)
        security = middleware.index("django.middleware.security.SecurityMiddleware")
        whitenoise = middleware.index("whitenoise.middleware.WhiteNoiseMiddleware")
        self.assertEqual(whitenoise, security + 1)

    def test_static_root_is_configured_for_collectstatic(self):
        self.assertTrue(settings.STATIC_ROOT)
