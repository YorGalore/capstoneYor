from .models import AnalystProfile
from .permissions import user_can_access

_LOGGED_OUT_DEFAULTS = {
    "instansi": "",
    "proyek": "",
    "analyst_profile": None,
    "can_view_feed": False,
    "can_view_taxonomy": False,
    "can_view_konfigurasi": False,
    "can_view_pengawasan": False,
}


def tenant_context(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return dict(_LOGGED_OUT_DEFAULTS)
    profile = AnalystProfile.objects.select_related("tenant").filter(user=user).first()
    if profile is None:
        return dict(_LOGGED_OUT_DEFAULTS)
    project = profile.tenant.projects.first()
    return {
        "instansi": profile.tenant.name,
        "proyek": project.name if project else "",
        "analyst_profile": profile,
        "can_view_feed": user_can_access(user, "feed"),
        "can_view_taxonomy": user_can_access(user, "taxonomy"),
        "can_view_konfigurasi": user_can_access(user, "konfigurasi"),
        "can_view_pengawasan": user_can_access(user, "pengawasan"),
    }
