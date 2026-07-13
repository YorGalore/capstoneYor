from django.test import TestCase

from apps.core.seed import seed_core


class DemoUserMiddlewareTest(TestCase):
    def test_requests_are_auto_authenticated_as_demo_user(self):
        seed_core()
        response = self.client.get("/admin/")
        self.assertEqual(response.wsgi_request.user.username, "dewi.anjani")
