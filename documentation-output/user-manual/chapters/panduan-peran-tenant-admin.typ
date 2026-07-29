#import "/_shared/style.typ": *

= Panduan Peran: Tenant Admin

== Apa yang bisa Anda lihat dan lakukan

Tenant Admin memiliki akses penuh ke seluruh halaman operasional PANTAU untuk tenant Anda: Ringkasan, Umpan Sebutan, War Room, Narasi, Regional, Sosiograf, Laporan, Ekspor Data, Sorotan Eksekutif, Taksonomi Isu, Insiden, Deteksi Koordinasi, Konsol Konfigurasi, dan Dasbor Pengawasan. Dua halaman yang eksklusif Platform Super Admin -- Matriks Izin Halaman dan Pengaturan Dev/Ops -- tidak dapat diakses (percobaan akses langsung menghasilkan 403 Forbidden, dan tautannya tidak tampil di sidebar Anda).

Tenant Admin adalah peran dengan tanggung jawab operasional terluas sehari-hari: mengatur apa yang dipantau (kata kunci, domain, aktor politik, program pemerintah), meninjau dan memfinalisasi Sorotan Eksekutif, mengelola taksonomi isu, dan menindaklanjuti klaster koordinasi tidak otentik.

== Alur kerja tipikal

1. *Menyiapkan cakupan pemantauan* -- tambahkan kata kunci, domain, aktor politik, dan program pemerintah yang perlu dipantau. Lihat Bab 7.7, bagian "Mengelola Kata Kunci Pemantauan", "Mengelola Domain Pantauan", "Mengelola Aktor Politik Publik", dan "Mengelola Program Pemerintah Terlacak".
2. *Meninjau Umpan Sebutan* dan mengoreksi sentimen yang keliru. Lihat Bab 7.1.
3. *Memantau War Room* pada isu yang sedang aktif dan mencatat aksi respons institusi. Lihat Bab 7.2.
4. *Meninjau Insiden* yang terdeteksi, menambah catatan, dan mengubah status penanganan. Lihat Bab 7.3.
5. *Menyusun dan memfinalisasi Sorotan Eksekutif (Brief) harian* untuk pimpinan/juru bicara. Lihat Bab 7.4.
6. *Mengelola Taksonomi Isu* -- melabeli konten pada antrean tinjauan manual dan menggabungkan isu yang tumpang tindih. Lihat Bab 7.5.
7. *Meninjau klaster Deteksi Koordinasi* -- memeriksa bukti, menandai organik, atau mengeskalasi ke tinjauan analis senior. Lihat Bab 7.6.
8. *Mengunduh data* melalui Laporan & Ekspor bila diperlukan analisis lanjutan di luar aplikasi. Lihat Bab 8.

Semua prosedur di atas telah diverifikasi berfungsi (dengan beberapa catatan yang dijelaskan pada masing-masing prosedur) menggunakan akun Tenant Admin.
