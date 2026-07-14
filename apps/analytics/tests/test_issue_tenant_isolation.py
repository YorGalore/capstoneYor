"""Tenant isolation for PoliticalIssue (FR-1.2).

PoliticalIssue had no project foreign key, so issues were global: every tenant's War Room
picked `PoliticalIssue.objects.filter(status=ACTIVE).first()` out of one shared pool. In a
platform where one tenant is a ministry monitoring a food-subsidy backlash and another is
a different institution entirely, showing one the other's issue — or letting one log a
response action against it — is the whole ballgame.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.analytics.models import PoliticalIssue, ResponseAction
from apps.core.models import AnalystProfile, Platform, Project, Tenant


def make_analyst(username, tenant):
    user = get_user_model().objects.create_user(username=username, password="pw12345678")
    AnalystProfile.objects.update_or_create(
        user=user,
        defaults={
            "tenant": tenant,
            "role": AnalystProfile.ROLE_SUPER_ADMIN,
            "role_label": "Super Admin",
        },
    )
    return user


class IssueTenantIsolationTest(TestCase):
    def setUp(self):
        Platform.objects.create(slug="x", display_name="X", method=Platform.METHOD_APIFY)

        self.tenant_a = Tenant.objects.create(name="Kemenko PMK")
        self.project_a = Project.objects.create(tenant=self.tenant_a, name="Pangan")
        self.tenant_b = Tenant.objects.create(name="Kementerian Lain")
        self.project_b = Project.objects.create(tenant=self.tenant_b, name="Energi")

        # Created first, so a global "first active issue" query would return this one.
        self.issue_b = PoliticalIssue.objects.create(
            project=self.project_b,
            title="Rahasia tenant B",
            status=PoliticalIssue.STATUS_ACTIVE,
            opened_at=timezone.now(),
            owner_label="Humas B",
        )
        self.issue_a = PoliticalIssue.objects.create(
            project=self.project_a,
            title="Isu tenant A",
            status=PoliticalIssue.STATUS_ACTIVE,
            opened_at=timezone.now(),
            owner_label="Humas A",
        )

        self.analyst_a = make_analyst("analis.a", self.tenant_a)

    def test_war_room_never_shows_another_tenants_issue(self):
        self.client.force_login(self.analyst_a)
        response = self.client.get(reverse("analytics:war_room"))
        self.assertNotContains(response, "Rahasia tenant B")
        self.assertContains(response, "Isu tenant A")

    def test_narasi_never_shows_another_tenants_issue(self):
        # Narasi is gated on the Political Monitoring permission (FR-29.1). Grant it, so
        # this test exercises tenant isolation rather than passing on the 403 and telling
        # us nothing about the leak.
        from apps.governance.models import PoliticalMonitoringPermission

        PoliticalMonitoringPermission.objects.create(
            user=self.analyst_a,
            approved_by="Super Admin",
            approved_at=timezone.now(),
            active=True,
        )
        self.client.force_login(self.analyst_a)
        response = self.client.get(reverse("analytics:narasi"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Rahasia tenant B")

    def test_an_analyst_cannot_log_a_response_against_another_tenants_issue(self):
        """The IDOR: the issue id came straight off the URL with no ownership check, so
        tenant A could write into tenant B's War Room timeline by guessing an integer."""
        self.client.force_login(self.analyst_a)

        self.client.post(
            reverse("analytics:log_response", args=[self.issue_b.pk]),
            {"action_type": ResponseAction.ACTION_CHOICES[0][0], "description": "sabotase"},
        )

        self.assertFalse(ResponseAction.objects.filter(issue=self.issue_b).exists())

    def test_an_analyst_can_still_log_a_response_on_their_own_issue(self):
        self.client.force_login(self.analyst_a)

        self.client.post(
            reverse("analytics:log_response", args=[self.issue_a.pk]),
            {"action_type": ResponseAction.ACTION_CHOICES[0][0], "description": "siaran pers"},
        )

        self.assertTrue(ResponseAction.objects.filter(issue=self.issue_a).exists())


class CoordinationDetectionScopeTest(TestCase):
    """The scheduled CIB job iterated every active issue in the database, so it ran one
    tenant's detection against another tenant's issues on every cadence."""

    def setUp(self):
        Platform.objects.create(slug="x", display_name="X", method=Platform.METHOD_APIFY)
        self.tenant_a = Tenant.objects.create(name="A")
        self.project_a = Project.objects.create(tenant=self.tenant_a, name="Pa")
        self.tenant_b = Tenant.objects.create(name="B")
        self.project_b = Project.objects.create(tenant=self.tenant_b, name="Pb")

        PoliticalIssue.objects.create(
            project=self.project_b, title="Isu B", status=PoliticalIssue.STATUS_ACTIVE,
            opened_at=timezone.now(), owner_label="B",
        )
        PoliticalIssue.objects.create(
            project=self.project_a, title="Isu A", status=PoliticalIssue.STATUS_ACTIVE,
            opened_at=timezone.now(), owner_label="A",
        )

    def test_scheduled_detection_only_considers_its_own_projects_issues(self):
        from unittest import mock

        from apps.governance import scheduling

        with mock.patch("apps.coordination.detection.detect", return_value=[]) as detect:
            scheduling._run_detect_coordination(self.project_a)

        considered = [call.args[1].title for call in detect.call_args_list]
        self.assertEqual(considered, ["Isu A"])
