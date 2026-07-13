from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(pattern_name="analytics:ringkasan", permanent=False)),
    path("", include("apps.analytics.urls")),
    path("", include("apps.coordination.urls")),
    path("", include("apps.governance.urls")),
]
