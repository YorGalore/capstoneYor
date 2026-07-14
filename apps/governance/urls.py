from django.urls import path

from . import views

app_name = "governance"

urlpatterns = [
    path("konfigurasi/", views.konfigurasi, name="konfigurasi"),
    path("konfigurasi/kata-kunci/tambah/", views.add_keyword, name="add_keyword"),
    path("konfigurasi/kata-kunci/<int:pk>/toggle/", views.toggle_keyword, name="toggle_keyword"),
    path("konfigurasi/kata-kunci/<int:pk>/hapus/", views.delete_keyword, name="delete_keyword"),
    path("konfigurasi/domain/tambah/", views.add_domain, name="add_domain"),
    path("konfigurasi/domain/<int:pk>/hapus/", views.delete_domain, name="delete_domain"),
    path("konfigurasi/domain/<int:pk>/uji-koneksi/", views.test_domain_connection, name="test_domain_connection"),
    path("konfigurasi/integrasi/<int:pk>/toggle/", views.toggle_integration, name="toggle_integration"),
    path("konfigurasi/pindai/", views.run_scan, name="run_scan"),
    path("konfigurasi/jadwal/<int:job_id>/ubah/", views.update_schedule, name="update_schedule"),
    path("konfigurasi/koleksi/toggle/", views.toggle_collection, name="toggle_collection"),
    path("pengawasan/", views.pengawasan, name="pengawasan"),
    path("konfigurasi/izin/", views.permission_matrix, name="permission_matrix"),
    path("konfigurasi/izin/ubah/", views.toggle_permission, name="toggle_permission"),
    path("dev-ops/", views.runtime_settings, name="runtime_settings"),
    path("dev-ops/apify/simpan/", views.save_apify_token, name="save_apify_token"),
    path("dev-ops/apify/cabut/", views.revoke_apify_token, name="revoke_apify_token"),
    path("dev-ops/setting/simpan/", views.save_runtime_setting, name="save_runtime_setting"),
]
