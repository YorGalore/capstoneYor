#import "/_shared/style.typ": *

= Pendahuluan

== Apa itu PANTAU

PANTAU adalah platform pemantauan media sosial dan narasi politik berbasis web yang ditujukan untuk instansi pemerintah (kementerian, pemerintah kabupaten/kota, dan organisasi perangkat daerah/OPD terkait). Platform ini mengumpulkan sebutan (mention) dari media sosial dan pemberitaan daring, mengelompokkannya ke dalam isu/narasi, mendeteksi lonjakan aktivitas (insiden) dan pola perilaku tidak otentik yang terkoordinasi, serta membantu tim humas menyusun respons krisis (War Room) dan ringkasan eksekutif harian (Sorotan Eksekutif/Brief).

PANTAU bersifat multi-tenant: setiap *Tenant* (misalnya satu kabupaten) memiliki satu atau lebih *Project* yang menjadi batas isolasi data. Setiap pengguna terhubung ke satu tenant dan bekerja dalam batas proyek tenant tersebut.

== Untuk siapa buku panduan ini

Buku ini ditujukan untuk pengguna operasional PANTAU pada empat peran berikut:

- *Platform Super Admin* -- mengelola pengaturan lintas-tenant, matriks izin halaman, dan pengaturan Dev/Ops.
- *Tenant Admin* -- mengelola konfigurasi pemantauan tenant (kata kunci, domain, aturan peringatan, aktor politik, program pemerintah) serta menjalankan hampir seluruh alur kerja analitik dan Sorotan Eksekutif.
- *Analis* -- menjalankan tugas analisis harian: memantau War Room, meninjau isu, dan (bila diberi izin tambahan) mengoreksi sentimen pada Umpan Sebutan.
- *Peninjau* -- peran hanya-baca (read-only) yang dimaksudkan untuk memantau dasbor tanpa mengubah data.

Setiap bab prosedur pada buku ini mencantumkan peran yang berlaku (*Peran yang berlaku*) berdasarkan hasil pengujian akses nyata terhadap aplikasi, bukan asumsi dari desain.

== Bagaimana buku ini disusun

Buku ini dibagi menjadi tiga bagian besar:

1. *Dasar* (Bab 2--5): persyaratan sistem, cara masuk/keluar dari aplikasi, gambaran umum antarmuka, dan pola navigasi yang berulang di banyak halaman (filter, pencarian, paginasi).
2. *Panduan per peran* (Bab 6): ringkasan halaman dan alur kerja tipikal untuk masing-masing dari keempat peran.
3. *Prosedur per modul* (Bab 7--9): langkah demi langkah untuk setiap alur kerja utama -- Umpan Sebutan, War Room, Insiden, Sorotan Eksekutif, Taksonomi Isu, Deteksi Koordinasi, Konsol Konfigurasi, Laporan & Ekspor -- disusul penjelasan status/lencana yang muncul di aplikasi.

Bagian penutup (Bab 10--13) berisi pemecahan masalah, pertanyaan yang sering diajukan, daftar istilah, dan informasi dukungan.

== Dasar penyusunan

Seluruh prosedur dalam buku ini disusun dari hasil pengujian fungsional (QA) yang dilakukan langsung terhadap aplikasi PANTAU yang berjalan, menggunakan akun uji pada keempat peran. *Tidak ada langkah dalam buku ini yang ditulis berdasarkan asumsi desain semata* -- setiap prosedur mencerminkan perilaku aplikasi yang benar-benar teramati. Di beberapa tempat, hasil pengujian menunjukkan sebuah fitur belum berfungsi penuh, tidak tersedia, atau tidak dapat diverifikasi; pada kondisi tersebut, buku ini menandainya secara eksplisit dengan kotak "Belum tersedia / belum terverifikasi" alih-alih menuliskan langkah-langkah yang belum tentu benar.

Buku ini adalah dokumen pendamping dari Laporan Pengujian (Testing Report) PANTAU yang disusun secara terpisah. Detail teknis mendalam mengenai temuan pengujian, tingkat keparahan isu, dan rekomendasi perbaikan berada di laporan tersebut; buku ini berfokus pada cara memakai aplikasi sebagaimana adanya saat ini.
