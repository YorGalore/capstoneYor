#import "/_shared/style.typ": *

= Panduan Peran: Analis

== Apa yang bisa Anda lihat dan lakukan

Berdasarkan matriks izin bawaan (default) yang diuji, Analis memiliki akses ke: Ringkasan, Umpan Sebutan (termasuk koreksi sentimen), War Room, Regional, Sosiograf, Laporan, Ekspor Data, Sorotan Eksekutif, Insiden, Deteksi Koordinasi, dan Profil.

Analis *tidak* memiliki akses bawaan ke: Taksonomi Isu, Konsol Konfigurasi, Dasbor Pengawasan, Matriks Izin Halaman, dan Pengaturan Dev/Ops. Mencoba membuka halaman-halaman ini akan menghasilkan 403 Forbidden.

#belum_tersedia[
  *Narasi (Perbandingan Narasi) memerlukan izin tambahan terpisah.* Selain matriks izin peran x halaman, halaman Narasi digerbangi izin "Pemantauan Politik" per-pengguna yang terpisah. Akun uji Analis pada pengujian ini belum diberi izin tersebut sehingga menerima 403 saat membuka `/narasi/`, meskipun Tenant Admin dan Platform Super Admin (yang sudah diberi izin ini) dapat mengaksesnya dengan normal. Ini bekerja sesuai desain -- hubungi administrator tenant Anda jika pekerjaan Anda memerlukan akses ke Narasi.
]

== Alur kerja tipikal

1. *Memantau War Room* untuk isu aktif dan mencatat aksi respons yang telah dilakukan tim. Lihat Bab 7.2.
2. *Meninjau Insiden* yang terdeteksi dan menambahkan catatan pada lini masa. Lihat Bab 7.3.
3. *Meninjau isu pada Sorotan Eksekutif* bila diberi akses menulis pada tenant Anda. Lihat Bab 7.4.
4. *Meninjau klaster Deteksi Koordinasi*. Lihat Bab 7.6.
5. *Melihat Regional dan Sosiograf* untuk konteks distribusi wilayah dan jaringan interaksi. Lihat Bab 7.8.
6. *Mengunduh data mention* melalui halaman Laporan bila diberi akses ekspor. Lihat Bab 8.
