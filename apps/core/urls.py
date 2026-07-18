from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("mulai/", views.onboarding, name="onboarding"),
    path("mulai/berhasil/", views.onboarding_success, name="onboarding_success"),
    path("artikel/<slug:slug>/", views.article_detail, name="artikel_detail"),
    path("profil/", views.profile, name="profile"),
]
