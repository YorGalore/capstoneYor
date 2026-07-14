from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.core.seed import DEMO_PASSWORD, DEMO_USERNAME, seed_core


class AuthFlowTest(TestCase):
    def test_anonymous_request_redirects_to_login(self):
        response = self.client.get("/ringkasan/")
        self.assertRedirects(response, "/accounts/login/?next=/ringkasan/", fetch_redirect_response=False)

    def test_login_with_valid_credentials_redirects_to_ringkasan(self):
        seed_core()
        response = self.client.post("/accounts/login/", {
            "username": DEMO_USERNAME,
            "password": DEMO_PASSWORD,
        })
        self.assertRedirects(response, "/ringkasan/", fetch_redirect_response=False)
        self.assertTrue(response.wsgi_request.user.is_anonymous is False)

    def test_login_with_invalid_credentials_shows_error(self):
        seed_core()
        response = self.client.post("/accounts/login/", {
            "username": DEMO_USERNAME,
            "password": "wrong-password",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)

    def test_logout_ends_the_session(self):
        seed_core()
        demo_user = get_user_model().objects.get(username=DEMO_USERNAME)
        self.client.force_login(demo_user)

        self.client.post("/accounts/logout/")

        response = self.client.get("/ringkasan/")
        self.assertRedirects(response, "/accounts/login/?next=/ringkasan/", fetch_redirect_response=False)

    def test_profile_page_shows_analyst_info(self):
        seed_core()
        demo_user = get_user_model().objects.get(username=DEMO_USERNAME)
        self.client.force_login(demo_user)

        response = self.client.get("/profil/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Analis Humas")
        self.assertContains(response, "Kemenko PMK")
