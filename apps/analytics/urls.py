from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("ringkasan/", views.ringkasan, name="ringkasan"),
    path("war-room/", views.war_room, name="war_room"),
    path("narasi/", views.narasi, name="narasi"),
    path("regional/", views.regional, name="regional"),
]
