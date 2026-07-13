from django.urls import path

from . import views

app_name = "coordination"

urlpatterns = [
    path("koordinasi/", views.koordinasi, name="koordinasi"),
]
