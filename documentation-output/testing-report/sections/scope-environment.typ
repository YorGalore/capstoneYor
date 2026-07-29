#import "../../_shared/style.typ": *

= Ruang Lingkup dan Lingkungan Pengujian

== Yang Diuji

Pengujian mencakup seluruh 24 rute pada `page-inventory.csv`: seluruh halaman modul Analitik, Koordinasi, dan Tata Kelola untuk keempat peran (sejauh relevan berdasarkan matriks izin default), seluruh halaman publik/onboarding sebagai pengguna anonim, serta perbandingan langsung antara akses yang diharapkan dan akses aktual untuk 68 kombinasi peran x halaman (`role-permission-matrix.csv`). Selain navigasi GET, pengujian juga mencakup pengiriman `POST` langsung ke endpoint aksi (mis. koreksi sentimen, log respons War Room, eskalasi klaster koordinasi, aksi CRUD Konsol Konfigurasi) untuk memverifikasi penegakan otorisasi di sisi server, bukan hanya di UI. Tangkapan layar responsif diambil pada tiga lebar viewport (1440x900, 834x1112, 390x844) untuk halaman-halaman utama.

== Yang Tidak Diuji / Di Luar Lingkup

#belum_tersedia[
  Koleksi data langsung dari Apify (media sosial nyata) tidak dipicu dengan token API produksi yang valid -- pengujian trigger koleksi manual (`konfigurasi_trigger-koleksi-social_tenant-admin_05c_setelah-klik.png`) memverifikasi bahwa guard aplikasi menolak dengan benar ketika token Apify tenant tidak tersedia/tidak persisten di lingkungan uji, bukan menguji hasil koleksi sungguhan. Demikian pula, verifikasi data `OnboardingRequest` melalui Django admin terblokir (ONB-006, lihat @sec-gap) karena akun Platform Super Admin tidak dipetakan ke `is_staff`/izin model Django, sehingga jalur itu tidak dapat diuji sampai selesai.
]

Detail Insiden (`/insiden/<id>/`) ada di kode namun tidak dapat diverifikasi karena basis data uji tidak memiliki data insiden berstatus tersebut pada saat pengujian dijalankan. Pengujian aksesibilitas mendalam (navigasi keyboard penuh, kontras warna terukur dengan alat otomatis) tidak dilakukan sebagai kategori tersendiri -- lihat @sec-a11y untuk cakupan yang sesungguhnya dijalankan (verifikasi visual responsif).

== Lingkungan dan Perkakas

- *Target uji*: server pengembangan PANTAU (`http://127.0.0.1:8010/`), berjalan di atas *salinan basis data pengembangan yang diisolasi* dari basis data produksi, dan diberi data seed realistis untuk tenant "Kabupaten Kulon Progo".
- *Browser*: Playwright dengan Chromium headless.
- *Metode*: kombinasi interaksi UI terskrip (klik, isi form, submit) dan request HTTP langsung (`page.request`) untuk probe otorisasi yang perlu melewati UI (mis. POST langsung ke endpoint aksi tanpa elemen UI yang mengeksposnya).

== Akun Uji

#table(
  columns: (auto, auto, 1fr),
  stroke: 0.5pt + rgb("#cccccc"),
  table.header[*Akun*][*Peran (RBAC)*][*Catatan*],
  [`dewi.anjani`], [Platform Super Admin], [Akses penuh ke seluruh halaman termasuk Matriks Izin dan Dev-Ops.],
  [`humas.kulonprogo`], [Tenant Admin], [Akun utama untuk alur kerja tenant Kabupaten Kulon Progo (Konfigurasi, Brief, Umpan Sebutan, dll).],
  [`qa.analis`], [Analis], [Digunakan untuk memverifikasi batas akses peran Analis, termasuk War Room dan probe otorisasi.],
  [`qa.peninjau`], [Peninjau (viewer)], [Digunakan secara ekstensif untuk probe otorisasi read-only -- akun ini yang membuktikan seluruh temuan Critical/High kontrol akses pada laporan ini.],
)
