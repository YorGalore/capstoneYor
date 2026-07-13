from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from apps.core.seed import seed_core
from apps.core.selectors import get_active_project


class GetActiveProjectTest(TestCase):
    def test_returns_none_for_anonymous_user(self):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        self.assertIsNone(get_active_project(request))

    def test_returns_project_for_demo_user(self):
        tenant, project = seed_core()
        demo_user = get_user_model().objects.get(username="dewi.anjani")
        request = RequestFactory().get("/")
        request.user = demo_user
        self.assertEqual(get_active_project(request), project)
