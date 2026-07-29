#import "/_shared/style.typ": *

= Persyaratan Sistem

== Peramban (browser)

PANTAU adalah aplikasi web yang diakses melalui peramban modern. Pengujian dilakukan menggunakan mesin peramban berbasis Chromium. Disarankan menggunakan versi terbaru dari peramban berbasis Chromium (Google Chrome, Microsoft Edge) untuk hasil terbaik. JavaScript harus diaktifkan karena beberapa kartu (mis. status live pemicu koleksi data pada Konsol Konfigurasi) melakukan polling AJAX di latar belakang.

== Lebar layar dan tampilan responsif

Pengujian tampilan dilakukan pada tiga lebar viewport yang mewakili desktop, tablet, dan ponsel:

- Desktop -- 1440 x 900 piksel
- Tablet -- 834 x 1112 piksel
- Ponsel -- 390 x 844 piksel

Untuk halaman publik (login, landing page, formulir onboarding), ketiga ukuran ini tampil baik tanpa overflow horizontal yang mengganggu.

#belum_tersedia[
  Untuk halaman-halaman *dasbor* (Umpan Sebutan, War Room, Insiden, Sorotan Eksekutif, Taksonomi Isu, Konsol Konfigurasi, Deteksi Koordinasi, dan kemungkinan seluruh halaman dasbor lain yang berbagi kerangka tata letak yang sama), sidebar navigasi *tidak menyusut* (tidak menjadi menu hamburger/off-canvas) pada lebar ponsel (390px). Sidebar tetap tampil sebagai kolom lebar tetap, menyisakan ruang yang sangat sempit untuk konten utama.

  Dampak paling terasa pada halaman *Taksonomi Isu*: pada lebar ponsel, kolom "Konten" dan tombol aksi "Labeli" pada tabel Antrean Tinjauan Manual tidak terlihat/tidak dapat dijangkau tanpa scroll horizontal yang tidak jelas indikatornya. Dampak serupa (meski lebih ringan) juga teramati pada halaman Sorotan Eksekutif (Brief).

  *Rekomendasi bagi pengguna:* jika memungkinkan, gunakan PANTAU pada layar tablet (834px ke atas) atau desktop untuk pekerjaan yang melibatkan tabel data (Taksonomi Isu, Konsol Konfigurasi). Akses dari ponsel paling nyaman untuk halaman ringkas seperti War Room atau untuk sekadar memantau, bukan untuk entri data intensif.
]

== Akun pengguna

PANTAU tidak menyediakan pendaftaran mandiri untuk pengguna internal. Akun dibuat oleh administrator tenant atau administrator platform. Hubungi administrator tenant Anda (lihat Bab 13, Dukungan) untuk permintaan akun baru atau reset kata sandi.
