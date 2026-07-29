#import "/_shared/style.typ": *

= Masuk dan Keluar Aplikasi

== Masuk (Login)

*Tujuan.* Masuk ke PANTAU menggunakan akun yang telah dibuatkan oleh administrator.

*Peran yang berlaku.* Semua peran (Platform Super Admin, Tenant Admin, Analis, Peninjau).

*Prasyarat.* Anda telah memiliki nama pengguna dan kata sandi yang diberikan oleh administrator tenant/platform.

*Langkah-langkah.*
1. Buka halaman login aplikasi (`/accounts/login/`).
2. Isi kolom nama pengguna dengan nama pengguna Anda.
3. Isi kolom kata sandi.
4. Klik tombol *Masuk*.

#screenshot("/testing-report/screenshots/auth_login-valid_dewi-anjani_01_ringkasan.png", [Tampilan halaman Ringkasan setelah login berhasil.])

*Hasil yang diharapkan.* Anda diarahkan (redirect) ke halaman *Ringkasan* (`/ringkasan/`). Sidebar di sisi kiri menampilkan nama instansi/tenant Anda dan jabatan Anda.

*Perubahan status.* Tidak ada perubahan status data; ini membuat sesi login aktif.

*Pemecahan masalah.*
- *Nama pengguna atau kata sandi salah:* pesan error yang tampil sengaja bersifat umum ("Nama pengguna atau kata sandi salah.") baik untuk kata sandi yang salah maupun nama pengguna yang tidak terdaftar -- ini praktik keamanan yang wajar, bukan indikasi bug. Periksa kembali ejaan nama pengguna dan kata sandi Anda, atau hubungi administrator untuk verifikasi/reset akun.
- *Kolom dibiarkan kosong:* peramban akan mencegah pengiriman formulir sampai kedua kolom diisi (validasi wajib bawaan peramban).
- *Nama atau jabatan yang tampil di sidebar tidak sesuai dugaan:* label peran di sidebar diambil dari kolom jabatan bebas teks (mis. "Analis Humas"), *bukan* nama peran akses (Platform Super Admin/Tenant Admin/Analis/Peninjau). Untuk memastikan peran akses Anda yang sebenarnya, lihat halaman *Profil* (`/profil/`), atau tanyakan kepada administrator. Beberapa akun uji juga tidak menampilkan nama pengguna di sidebar karena data nama depan/belakang belum diisi -- ini kosmetik dan tidak memengaruhi akses.

== Keluar (Logout)

*Tujuan.* Mengakhiri sesi login Anda dengan aman, terutama pada perangkat bersama.

*Peran yang berlaku.* Semua peran.

*Prasyarat.* Anda sedang dalam sesi login aktif.

*Langkah-langkah.*
1. Buka halaman *Profil* (`/profil/`), atau gunakan tautan Keluar yang tersedia di sidebar/header.
2. Klik tombol *Keluar*.

*Hasil yang diharapkan.* Anda diarahkan kembali ke halaman login (`/accounts/login/`). Setelah logout, mencoba mengakses halaman yang memerlukan login (mis. `/pengawasan/`) akan mengarahkan Anda kembali ke halaman login dengan parameter `next` yang menyimpan tujuan semula, sehingga Anda otomatis diarahkan ke halaman tersebut setelah login ulang.

*Perubahan status.* Sesi login diakhiri.

*Pemecahan masalah.*
- *Menekan tombol "kembali" (back) pada peramban setelah logout:* aplikasi tidak menampilkan konten halaman yang pernah login dari cache peramban (bfcache) -- Anda akan tetap melihat halaman login. Ini perilaku aman yang sudah diverifikasi.
- *Ingin memastikan Anda benar-benar keluar di perangkat bersama:* setelah logout, coba akses langsung salah satu URL dasbor (mis. `/ringkasan/`) melalui address bar; jika Anda diarahkan ke halaman login, sesi sudah berakhir dengan benar.
