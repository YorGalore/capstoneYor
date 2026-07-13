from django.contrib.auth import get_user_model, login
from django.contrib.auth.models import AnonymousUser

from .seed import DEMO_USERNAME


class DemoUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if isinstance(request.user, AnonymousUser):
            User = get_user_model()
            demo_user = User.objects.filter(username=DEMO_USERNAME).first()
            if demo_user is not None:
                request.user = demo_user
                login(request, demo_user, backend="django.contrib.auth.backends.ModelBackend")
        return self.get_response(request)
