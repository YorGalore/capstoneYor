from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("mulai/", views.onboarding, name="onboarding"),
    path("mulai/berhasil/", views.onboarding_success, name="onboarding_success"),
    path("profil/", views.profile, name="profile"),
]
