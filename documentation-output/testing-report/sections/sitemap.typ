= Peta Situs (Sitemap)

Peta berikut disusun berdasarkan hasil eksplorasi langsung terhadap aplikasi PANTAU (server uji `http://127.0.0.1:8010/`) menggunakan akun `dewi.anjani` (peran `super_admin`, dapat mengakses seluruh halaman). Setiap butir menunjukkan rute (URL) dan judul halaman dalam Bahasa Indonesia sebagaimana tampak pada `<title>` browser dan/atau tajuk halaman.

- *Beranda Publik* (dapat diakses tanpa login; saat sudah login `/` otomatis dialihkan ke `/ringkasan/`)
  - `/` — Pahami apa yang publik katakan. Rasakan. Gerakkan. (landing page)
  - `/mulai/` — Mulai dari kebutuhan, bukan kerumitan. (formulir permintaan demo)
  - `/mulai/berhasil/` — Terima kasih. Mari mulai memetakan sinyal. (konfirmasi permintaan)
  - `/artikel/<slug>/` — Detail Artikel (contoh: `/artikel/media-monitoring-untuk-pemerintah/`)
  - `/accounts/login/` — Masuk

- *Analitik* (menu utama setelah login)
  - `/ringkasan/` — Ringkasan (halaman awal setelah login)
  - `/umpan/` — Umpan Sebutan
  - `/taksonomi/` — Taksonomi Isu
  - `/narasi/` — Perbandingan Narasi
  - `/war-room/` — War Room
  - `/insiden/` — Insiden
    - `/insiden/<id>/` — Detail Insiden (route tersedia di kode, belum dapat diverifikasi karena data uji belum memiliki insiden)
  - `/regional/` — Regional
  - `/sosiograf/` — Sosiograf
  - `/brief/` — Sorotan (Sorotan Eksekutif)
  - `/laporan/` — Laporan
  - `/ekspor/mention/` — Ekspor Sebutan (unduhan CSV, bukan halaman)

- *Koordinasi*
  - `/koordinasi/` — Deteksi Koordinasi (Deteksi Perilaku Tidak Otentik Terkoordinasi)

- *Tata Kelola*
  - `/konfigurasi/` — Konsol Konfigurasi (kata kunci, domain, integrasi, kubu, aktor, program, aturan peringatan, token Apify, penjadwalan koleksi)
  - `/pengawasan/` — Dasbor Pengawasan
  - `/konfigurasi/izin/` — Matriks Izin Halaman (khusus `super_admin`)
  - `/dev-ops/` — Pengaturan Dev/Ops (khusus `super_admin`)
  - `/profil/` — Profil (akun pengguna yang sedang login)

Di luar peta modul di atas, `/healthz/` adalah endpoint pemeriksaan kesehatan (mengembalikan JSON, bukan halaman) dan `/admin/` adalah panel Django Admin bawaan yang berdiri di luar tata letak PANTAU.
