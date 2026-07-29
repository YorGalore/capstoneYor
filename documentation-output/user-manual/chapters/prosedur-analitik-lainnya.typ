#import "/_shared/style.typ": *

= Prosedur: Regional, Sosiograf, dan Narasi

Tiga halaman analitik berikut bersifat murni tampilan (tidak ada aksi tulis/formulir yang diuji): Regional, Sosiograf, dan Perbandingan Narasi.

== Melihat Regional

*Tujuan.* Meninjau distribusi narasi/sebutan berdasarkan wilayah.

*Peran yang berlaku.* Platform Super Admin, Tenant Admin, Analis, Peninjau.

*Prasyarat.* Login dengan akun yang memiliki akses ke halaman ini (seluruh peran memiliki akses bawaan).

*Langkah-langkah.*
1. Buka halaman *Regional* (`/regional/`).
2. Tinjau visualisasi distribusi wilayah yang ditampilkan.

#screenshot("/testing-report/screenshots/regional_lihat_tenant_admin_01_akses.png", [Halaman Regional.])

*Hasil yang diharapkan.* Halaman termuat (HTTP 200) untuk seluruh peran yang diuji.

*Perubahan status.* Tidak ada; murni tampilan.

== Melihat Sosiograf

*Tujuan.* Meninjau sosiograf interaksi (analisis jaringan aktor).

*Peran yang berlaku.* Platform Super Admin, Tenant Admin, Analis, Peninjau.

*Prasyarat.* Login dengan akun yang memiliki akses ke halaman ini (seluruh peran memiliki akses bawaan).

*Langkah-langkah.*
1. Buka halaman *Sosiograf* (`/sosiograf/`).
2. Tinjau jaringan interaksi aktor yang ditampilkan.

#screenshot("/testing-report/screenshots/sosiograf_lihat_tenant_admin_01_akses.png", [Halaman Sosiograf.])

*Hasil yang diharapkan.* Halaman termuat (HTTP 200) untuk seluruh peran yang diuji.

*Perubahan status.* Tidak ada; murni tampilan.

== Melihat Perbandingan Narasi

*Tujuan.* Menganalisis perbandingan narasi/isu politik antar kubu atau aktor.

*Peran yang berlaku.* Tenant Admin, Platform Super Admin (memiliki izin "Pemantauan Politik" pada akun uji).

*Prasyarat.* Anda memiliki izin "Pemantauan Politik" yang diberikan administrator, terpisah dari izin akses halaman biasa.

*Langkah-langkah.*
1. Buka halaman *Perbandingan Narasi* (`/narasi/`).
2. Tinjau perbandingan narasi yang ditampilkan.

#screenshot("/testing-report/screenshots/narasi_lihat_tenant_admin_01_akses.png", [Halaman Perbandingan Narasi.])

*Hasil yang diharapkan.* Halaman termuat (HTTP 200) untuk akun yang telah diberi izin Pemantauan Politik.

*Perubahan status.* Tidak ada; murni tampilan.

#belum_tersedia[
  *Analis dan Peninjau pada pengujian ini menerima 403 Forbidden saat membuka halaman Narasi*, karena akun uji untuk kedua peran tersebut belum diberi izin "Pemantauan Politik" -- sebuah gerbang izin per-pengguna yang terpisah dari matriks izin peran x halaman biasa. Ini bukan indikasi kerusakan; ini bekerja sesuai desain. Jika pekerjaan Anda memerlukan akses ke Narasi, minta administrator tenant Anda memberikan izin Pemantauan Politik pada akun Anda secara khusus.
]
