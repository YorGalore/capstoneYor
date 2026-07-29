#import "/_shared/style.typ": *

= Panduan Peran: Peninjau

== Apa yang bisa Anda lihat dan lakukan

Peninjau dirancang sebagai peran hanya-baca (read-only). Berdasarkan matriks izin bawaan yang diuji, Peninjau memiliki akses lihat ke: Ringkasan, Umpan Sebutan, War Room, Regional, Sosiograf, Laporan, Sorotan Eksekutif, Insiden, Deteksi Koordinasi, dan Profil.

Peninjau *tidak* memiliki akses ke: Ekspor Data, Taksonomi Isu, Konsol Konfigurasi, Dasbor Pengawasan, Matriks Izin Halaman, dan Pengaturan Dev/Ops. Mencoba mengakses halaman-halaman ini (atau endpoint unduhan ekspor) akan menghasilkan 403 Forbidden.

#belum_tersedia[
  *Narasi (Perbandingan Narasi) memerlukan izin tambahan terpisah* yang belum diberikan ke akun uji Peninjau pada pengujian ini -- lihat penjelasan yang sama pada Bab 6.3 (Panduan Peran: Analis).
]

Batas "hanya-baca" kini ditegakkan penuh: pada War Room (mencatat aksi respons), Insiden (menambah catatan/ubah status/tugaskan/konfirmasi), dan Deteksi Koordinasi (mengeskalasi/menandai organik klaster), tombol aksi tulis akan menolak permintaan Peninjau dengan 403 Forbidden meskipun tombolnya masih tampil pada halaman (server selalu menjadi penjaga terakhir, terlepas dari tampilan tombol di UI). Peninjau juga tidak dapat membuat/menyunting/memfinalisasi draf Sorotan Eksekutif maupun mengoreksi sentimen pada Umpan Sebutan -- keduanya akses baca saja.

== Alur kerja tipikal

1. *Memantau Ringkasan dan War Room* untuk gambaran umum isu aktif. Lihat Bab 7.2.
2. *Memantau papan Insiden* dan meninjau lini masa insiden yang sedang berjalan. Lihat Bab 7.3.
3. *Membaca Sorotan Eksekutif* yang telah difinalisasi tim. Lihat Bab 7.4.
4. *Meninjau daftar dan detail klaster Deteksi Koordinasi* sebagai bahan pemantauan. Lihat Bab 7.6.
5. *Melihat Regional, Sosiograf, dan Laporan* untuk konteks tambahan. Lihat Bab 7.8 dan Bab 8.
