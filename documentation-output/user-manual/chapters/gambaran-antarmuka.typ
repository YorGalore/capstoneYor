#import "/_shared/style.typ": *

= Gambaran Umum Antarmuka

Setelah masuk, Anda mendarat di halaman *Ringkasan* (`/ringkasan/`), landing page dasbor PANTAU. Seluruh halaman dasbor (Ringkasan, Umpan Sebutan, War Room, Narasi, Regional, Sosiograf, Laporan, Sorotan Eksekutif, Taksonomi Isu, Insiden, Deteksi Koordinasi, Konsol Konfigurasi, Dasbor Pengawasan, dan halaman khusus Super Admin) berbagi kerangka tata letak yang sama: sidebar navigasi di kiri dan area konten di kanan.

#screenshot("/testing-report/screenshots/auth_login-valid_humas-kulonprogo_01_ringkasan.png", [Kerangka tata letak dasbor PANTAU: sidebar navigasi di kiri, konten di kanan.])

== Sidebar navigasi

Sidebar di sisi kiri layar menampilkan:

- Identitas tenant/instansi dan jabatan pengguna yang sedang login.
- Daftar tautan menu ke setiap modul yang tersedia untuk peran Anda (Ringkasan, Umpan Sebutan, War Room, Narasi, Regional, Sosiograf, Laporan, Sorotan Eksekutif, Taksonomi Isu, Insiden, Deteksi Koordinasi, dan untuk peran yang berwenang: Konsol Konfigurasi, Dasbor Pengawasan, serta khusus Platform Super Admin: Matriks Izin Halaman dan Pengaturan Dev/Ops).
- Tautan ke halaman Profil dan tombol Keluar.

Untuk halaman yang tidak dapat diakses peran Anda (Umpan Sebutan, Taksonomi Isu, Konfigurasi, Pengawasan), tautan menu secara otomatis tampil non-aktif ("Akses dibatasi") bila peran Anda tidak memiliki izin ke halaman tersebut, sehingga Anda tidak perlu mengklik untuk mengetahuinya.

== Header dan identitas halaman

Sebagian besar halaman dasbor tidak menampilkan judul H1 yang mencolok; judul halaman terlihat pada tab peramban (elemen `<title>`) dan pada tautan menu sidebar yang sedang aktif/tersorot.

== Kartu dan panel

Konten pada sebagian besar halaman disusun dalam bentuk kartu (card) -- misalnya Konsol Konfigurasi berisi lebih dari sepuluh kartu berbeda (Platform Terpantau, Kredensial Apify, Kata Kunci, Domain, Trigger Koleksi Manual, Aturan Peringatan, Kubu, Aktor Politik, Program Pemerintah, Kesehatan Kolektor, Penjadwalan, dan Riwayat Siklus Koleksi) dalam satu halaman panjang. Setiap kartu umumnya memiliki tabel/daftar data dan formulir aksi terkait di bagian bawahnya.

== Halaman tunggal dengan sub-aksi POST

Beberapa halaman -- terutama Konsol Konfigurasi (`/konfigurasi/`) dan Taksonomi Isu (`/taksonomi/`) -- adalah halaman tunggal (single-page): seluruh sub-aksi (menambah kata kunci, menggabungkan isu, dan sebagainya) dikirim sebagai permintaan POST ke URL yang sama, bukan berpindah ke sub-halaman terpisah. Setelah aksi berhasil/gagal, Anda akan tetap berada di halaman yang sama dengan pesan hasil (sukses/error) tampil di bagian atas.
