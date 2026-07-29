#import "/_shared/style.typ": *

= Prosedur: Umpan Sebutan

Umpan Sebutan (`/umpan/`) menampilkan daftar sebutan/mention media sosial dan berita yang terkumpul, dengan kolom Waktu, Platform, Penulis, Sentimen, Koreksi, Interaksi, dan Konten.

== Melihat dan memfilter Umpan Sebutan

*Tujuan.* Meninjau sebutan media sosial/berita yang masuk dan menyaringnya berdasarkan platform.

*Peran yang berlaku.* Tenant Admin, Platform Super Admin, Analis, Peninjau (seluruhnya memiliki akses baca bawaan).

*Prasyarat.* Login dengan akun yang memiliki akses ke halaman Umpan Sebutan.

*Langkah-langkah.*
1. Buka halaman *Umpan Sebutan* (`/umpan/`).
2. Amati daftar mention pada tabel utama.
3. Untuk menyaring, pilih salah satu platform pada dropdown "Semua platform".
4. Klik tombol *Saring*.

#screenshot("/testing-report/screenshots/feed_filter-platform_tenant-admin_02_hasil.png", [Hasil penyaringan Umpan Sebutan berdasarkan platform, tercermin pada parameter URL.])

*Hasil yang diharapkan.* Daftar mention terfilter sesuai platform yang dipilih; parameter `platform=` muncul pada URL dan dropdown tetap menampilkan pilihan Anda.

*Perubahan status.* Tidak ada perubahan status data; ini murni tampilan.

*Pemecahan masalah.*
- *Pencarian penulis tidak menemukan hasil:* halaman menampilkan pesan "Belum ada mention yang cocok." -- ini kondisi normal untuk pencarian tanpa hasil, bukan error.
- *Kontrol paginasi tidak muncul:* wajar bila jumlah mention pada tenant Anda tidak melebihi 25 baris.
- Belum ada kontrol pengurutan (sort) kolom di halaman ini -- lihat Bab 5.

== Mengoreksi sentimen mention

*Tujuan.* Mengoreksi label sentimen (Positif/Negatif/Netral) sebuah mention yang salah diklasifikasikan oleh sistem otomatis.

*Peran yang berlaku.* Tenant Admin, Platform Super Admin, Analis. (Peninjau dapat melihat Umpan Sebutan tetapi ditolak saat mencoba mengoreksi -- akses tulis dibatasi terpisah dari akses baca.)

*Prasyarat.* Anda berada di halaman Umpan Sebutan dan menemukan mention yang sentimennya perlu dikoreksi.

*Langkah-langkah.*
1. Buka halaman *Umpan Sebutan* (`/umpan/`).
2. Pada baris mention yang ingin dikoreksi, pilih nilai sentimen baru (mis. "Positif") pada kontrol Koreksi.
3. Klik tombol *Koreksi*.
4. Muat ulang halaman untuk memverifikasi perubahan tersimpan.

#screenshot("/testing-report/screenshots/feed_koreksi-sentimen_tenant-admin_02_sukses.png", [Pesan sukses setelah mengoreksi sentimen sebuah mention.])

*Hasil yang diharapkan.* Sentimen mention berubah dan pesan sukses tampil. Setelah memuat ulang halaman, label sentimen baru tetap tersimpan (perubahan bersifat permanen).

*Perubahan status.* Label sentimen mention berubah dari nilai lama ke nilai yang Anda pilih (mis. dari "Negatif" menjadi "Positif").

*Pemecahan masalah.*
- *Memilih nilai sentimen di luar pilihan yang valid:* ditolak oleh server dengan pesan error, dan data mention tidak berubah.
- *Menekan tombol "kembali" (back) setelah koreksi berhasil:* aman -- aplikasi menggunakan pola simpan-dan-muat-ulang sehingga tidak akan memicu pengiriman ulang data yang tidak disengaja (lihat Bab 5).
- *Mengoreksi mention yang tidak ada (mis. tautan lama/rusak):* server menolak permintaan; Anda tidak perlu khawatir data lain ikut berubah.
