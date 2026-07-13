from .models import AnalystProfile


def tenant_context(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"instansi": "", "proyek": "", "analyst_profile": None}
    profile = AnalystProfile.objects.select_related("tenant").filter(user=user).first()
    if profile is None:
        return {"instansi": "", "proyek": "", "analyst_profile": None}
    project = profile.tenant.projects.first()
    return {
        "instansi": profile.tenant.name,
        "proyek": project.name if project else "",
        "analyst_profile": profile,
    }
