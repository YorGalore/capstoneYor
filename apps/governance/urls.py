from django.urls import path

from . import views

app_name = "governance"

urlpatterns = [
    path("konfigurasi/", views.konfigurasi, name="konfigurasi"),
    path("pengawasan/", views.pengawasan, name="pengawasan"),
]
