from .models import AnalystProfile


def get_active_project(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return None
    profile = AnalystProfile.objects.select_related("tenant").filter(user=user).first()
    if profile is None:
        return None
    return profile.tenant.projects.first()
