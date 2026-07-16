from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.core.models import AnalystProfile, OnboardingRequest, Tenant


class LandingAndOnboardingTest(TestCase):
    def test_landing_is_public_and_lists_core_capabilities(self):
        response = self.client.get(reverse("core:landing"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Monitoring lintas kanal")
        self.assertContains(response, "Deteksi koordinasi")
        self.assertContains(response, "Governance &amp; audit")

    def test_a_signed_in_analyst_is_sent_to_the_dashboard_rather_than_the_sales_page(self):
        """Before the landing page existed, "/" redirected into the app. It now serves
        marketing copy to everyone, so an analyst who bookmarked the root — or clicks the
        logo on their way back — is told to "Masuk" and offered a demo booking while
        already signed in. The public page is for the public; a known user goes to work.
        """
        tenant = Tenant.objects.create(name="Instansi A")
        user = get_user_model().objects.create_user(username="analis", password="pw12345678")
        AnalystProfile.objects.update_or_create(
            user=user,
            defaults={"tenant": tenant, "role": AnalystProfile.ROLE_ANALYST, "role_label": "Analis"},
        )
        self.client.force_login(user)

        response = self.client.get(reverse("core:landing"))

        self.assertRedirects(response, reverse("analytics:ringkasan"))

    def test_government_onboarding_is_preselected(self):
        response = self.client.get(reverse("core:onboarding") + "?type=government")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].initial["organization_type"], "government")
        self.assertEqual(
            list(response.context["form"].fields["organization_type"].choices),
            list(OnboardingRequest.ORGANIZATION_CHOICES),
        )
        self.assertContains(response, "onboarding.css")

    def test_valid_onboarding_is_saved_and_redirected(self):
        response = self.client.post(reverse("core:onboarding"), {
            "organization_type": "brand", "organization_name": "Nusantara Labs",
            "contact_name": "Ayu Laras", "work_email": "ayu@nusantara.id",
            "phone": "+628123456789", "role": "Head of Communications",
            "monitoring_goal": "Memantau reputasi dan kampanye", "platforms": "X, Instagram",
            "team_size": "6-20", "consent": "on",
        })
        self.assertRedirects(response, reverse("core:onboarding_success"))
        request = OnboardingRequest.objects.get()
        self.assertEqual(request.organization_name, "Nusantara Labs")
        self.assertEqual(request.status, "new")

    def test_consent_is_required(self):
        response = self.client.post(reverse("core:onboarding"), {
            "organization_type": "government", "organization_name": "Dinas Informasi",
            "contact_name": "Budi", "work_email": "budi@example.go.id", "phone": "0812",
            "role": "Analis", "monitoring_goal": "Memantau program prioritas",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("consent", response.context["form"].errors)
        self.assertFalse(OnboardingRequest.objects.exists())
