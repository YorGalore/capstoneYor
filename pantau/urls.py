from django.contrib import admin
from django.urls import include, path

from pantau.health import healthz

urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("apps.core.urls")),
    path("", include("apps.analytics.urls")),
    path("", include("apps.coordination.urls")),
    path("", include("apps.governance.urls")),
]
