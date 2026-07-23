from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.core.models import AnalystProfile, OnboardingRequest, Tenant

User = get_user_model()


class OnboardingRequestsViewTest(TestCase):
    """ONB-ISSUE-003: Super Admin needs a first-party path to verify onboarding
    submissions, since AnalystProfile.role is not wired into Django-admin staff
    permissions."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.request_obj = OnboardingRequest.objects.create(
            organization_type="government", organization_name="Dinas Kominfo",
            contact_name="Budi", work_email="budi@example.go.id", phone="0812",
            role="Analis", monitoring_goal="Memantau program prioritas",
        )
        self.super_admin = User.objects.create(username="super.onboarding")
        AnalystProfile.objects.update_or_create(
            user=self.super_admin,
            defaults={"tenant": self.tenant, "role": AnalystProfile.ROLE_SUPER_ADMIN},
        )
        self.tenant_admin = User.objects.create(username="admin.onboarding")
        AnalystProfile.objects.update_or_create(
            user=self.tenant_admin,
            defaults={"tenant": self.tenant, "role": AnalystProfile.ROLE_TENANT_ADMIN},
        )

    def test_super_admin_sees_the_request(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse("core:onboarding_requests"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dinas Kominfo")
        self.assertContains(response, "budi@example.go.id")

    def test_tenant_admin_forbidden(self):
        self.client.force_login(self.tenant_admin)
        response = self.client.get(reverse("core:onboarding_requests"))
        self.assertEqual(response.status_code, 403)


class OnboardingSuccessPageTest(TestCase):
    """ONB-ISSUE-001 / ONB-ISSUE-002: the confirmation page must not be reachable
    without a real submission in the same session, and a near-duplicate
    submission must not create a second row."""

    def _valid_payload(self, **overrides):
        payload = {
            "organization_type": "brand", "organization_name": "Nusantara Labs",
            "contact_name": "Ayu Laras", "work_email": "ayu@nusantara.id",
            "phone": "+628123456789", "role": "Head of Communications",
            "monitoring_goal": "Memantau reputasi dan kampanye", "platforms": "X, Instagram",
            "team_size": "6-20", "consent": "on",
        }
        payload.update(overrides)
        return payload

    def test_success_page_unreachable_without_prior_submission(self):
        response = self.client.get(reverse("core:onboarding_success"))
        self.assertRedirects(response, reverse("core:onboarding"))

    def test_success_page_reachable_immediately_after_a_real_submission(self):
        self.client.post(reverse("core:onboarding"), self._valid_payload())
        response = self.client.get(reverse("core:onboarding_success"))
        self.assertEqual(response.status_code, 200)

    def test_second_visit_to_success_page_redirects_away(self):
        self.client.post(reverse("core:onboarding"), self._valid_payload())
        self.client.get(reverse("core:onboarding_success"))  # consumes the flag
        response = self.client.get(reverse("core:onboarding_success"))
        self.assertRedirects(response, reverse("core:onboarding"))

    def test_near_duplicate_submission_does_not_create_a_second_row(self):
        self.client.post(reverse("core:onboarding"), self._valid_payload())
        self.assertEqual(OnboardingRequest.objects.count(), 1)

        response = self.client.post(reverse("core:onboarding"), self._valid_payload())
        self.assertRedirects(response, reverse("core:onboarding_success"))
        self.assertEqual(OnboardingRequest.objects.count(), 1)

    def test_different_organization_is_not_treated_as_a_duplicate(self):
        self.client.post(reverse("core:onboarding"), self._valid_payload())
        self.client.post(
            reverse("core:onboarding"),
            self._valid_payload(organization_name="Organisasi Lain", work_email="lain@example.id"),
        )
        self.assertEqual(OnboardingRequest.objects.count(), 2)
