#import "/_shared/style.typ": *

= Panduan Peran: Platform Super Admin

== Apa yang bisa Anda lihat dan lakukan

Platform Super Admin memiliki akses penuh ke seluruh halaman PANTAU, termasuk dua halaman yang eksklusif untuk peran ini:

- *Matriks Izin Halaman* (`/konfigurasi/izin/`) -- mengatur kombinasi peran x halaman mana yang diizinkan/ditolak. Pembatasan yang diatur di sini kini ditegakkan seragam di seluruh 16 halaman pada registry.
- *Pengaturan Dev/Ops* (`/dev-ops/`) -- mengelola kredensial Apify tingkat sistem dan pengaturan runtime.
- *Permintaan Demo* (`/mulai/permintaan/`) -- meninjau daftar permintaan demo publik yang masuk lewat formulir onboarding, tanpa perlu mengandalkan Django Admin.

Selain ketiga halaman khusus tersebut, Super Admin juga memiliki akses penuh yang sama dengan Tenant Admin ke seluruh modul analitik (Ringkasan, Umpan Sebutan, War Room, Narasi, Regional, Sosiograf, Laporan, Ekspor Data, Sorotan Eksekutif, Taksonomi Isu, Insiden), Deteksi Koordinasi, Konsol Konfigurasi, dan Dasbor Pengawasan.

Catatan: peran "Platform Super Admin" pada aplikasi (field `role` di profil analis) tetap independen dari status staf Django (`is_staff`/`is_superuser`) -- login ke Django Admin (`/admin/`) dengan akun Super Admin aplikasi tidak otomatis memberi izin melihat/mengubah data di sana. Gunakan halaman *Permintaan Demo* di atas untuk verifikasi OnboardingRequest alih-alih Django Admin.

== Alur kerja tipikal

1. *Meninjau dan mengatur akses peran* -- lihat @sec-matriks-izin di Bab 7 untuk cara membuka dan mengubah Matriks Izin Halaman.
2. *Mengelola kredensial dan pengaturan sistem* -- lihat @sec-devops di Bab 7 untuk Pengaturan Dev/Ops.
3. *Menjalankan seluruh alur kerja operasional* yang juga tersedia bagi Tenant Admin -- lihat Bab 6.2 (Panduan Peran: Tenant Admin) untuk daftar lengkap serta tautan ke prosedur terkait di Bab 7: Umpan Sebutan, War Room, Insiden, Sorotan Eksekutif, Taksonomi Isu, Deteksi Koordinasi, Konsol Konfigurasi, dan Laporan & Ekspor.
4. *Memantau Dasbor Pengawasan* (`/pengawasan/`) -- lihat catatan pada Bab 6.2.
5. *Meninjau permintaan demo publik* pada `/mulai/permintaan/`.
