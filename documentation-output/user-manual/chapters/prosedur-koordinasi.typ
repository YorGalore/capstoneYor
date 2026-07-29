#import "/_shared/style.typ": *

= Prosedur: Deteksi Perilaku Tidak Otentik Terkoordinasi

Halaman Deteksi Koordinasi (`/koordinasi/`) menampilkan daftar klaster (Coordinated Inauthentic Behavior/CIB) dengan skor dan status, beserta panel detail (jaringan amplifikasi, sinyal koordinasi, sampel teks terduplikasi) untuk klaster yang dipilih.

== Membuka daftar klaster dan memeriksa bukti

*Tujuan.* Meninjau klaster aktivitas yang terdeteksi berpotensi tidak otentik/terkoordinasi beserta bukti pendukungnya.

*Peran yang berlaku.* Tenant Admin, Platform Super Admin, Analis, Peninjau.

*Prasyarat.* Login dengan akun yang memiliki akses ke halaman ini.

*Langkah-langkah.*
1. Buka halaman *Deteksi Perilaku Tidak Otentik Terkoordinasi* (`/koordinasi/`).
2. Amati daftar klaster; klaster pertama otomatis terpilih dan menampilkan detailnya.
3. Klik klaster lain pada daftar untuk melihat detailnya.
4. Pada panel detail, tinjau jaringan akun, sinyal koordinasi (dengan skor), dan sampel teks terduplikasi.

#screenshot("/testing-report/screenshots/koordinasi_lihat-detail-klaster_tenant-admin_02_evidence.png", [Detail klaster koordinasi menampilkan jaringan akun, sinyal, dan sampel teks terduplikasi sebagai bukti.])

*Hasil yang diharapkan.* Daftar klaster tampil dengan skor dan status; detail klaster yang dipilih menampilkan bukti pendukung yang cukup rinci untuk mendukung keputusan lanjutan.

*Perubahan status.* Tidak ada; ini murni tampilan.

#belum_tersedia[
  Halaman ini belum menyediakan kontrol pencarian atau filter klaster (mis. berdasarkan status atau skor) -- hanya daftar berurutan berdasarkan skor.
]

== Menandai klaster sebagai organik (false positive)

*Tujuan.* Menandai sebuah klaster yang setelah ditinjau ternyata bukan aktivitas tidak otentik (false positive).

*Peran yang berlaku.* Tenant Admin, Platform Super Admin.

*Prasyarat.* Klaster yang akan ditandai berstatus "Ditandai".

*Langkah-langkah.*
1. Buka detail klaster yang berstatus "Ditandai".
2. Klik tombol *Tandai organik (false positive)*.
3. Muat ulang halaman untuk memverifikasi.

#screenshot("/testing-report/screenshots/koordinasi_tandai-organik_tenant-admin_04_setelah-tandai.png", [Status klaster berubah menjadi "Ditinjau — Organik" setelah ditandai.])

*Hasil yang diharapkan.* Pesan sukses muncul dan status klaster berubah menjadi "Ditinjau — Organik", bertahan setelah halaman dimuat ulang.

*Perubahan status.* Ditandai → Ditinjau — Organik.

== Mengeskalasi klaster ke tinjauan analis senior

*Tujuan.* Mengirim klaster yang memerlukan penilaian lebih lanjut ke analis senior.

*Peran yang berlaku.* Tenant Admin, Platform Super Admin. (Analis dan Peninjau ditolak 403 saat mencoba aksi ini -- lihat "Pemecahan masalah".)

*Prasyarat.* Klaster yang akan dieskalasi berstatus "Ditandai".

*Langkah-langkah.*
1. Buka detail klaster yang ingin dieskalasi.
2. Klik tombol *Kirim ke tinjauan analis senior*.

#screenshot("/testing-report/screenshots/ISS-KOORDINASI-001_reverifikasi_diperbaiki.png", [Badge status klaster berubah menjadi "Dieskalasi" setelah eskalasi, bertahan setelah halaman dimuat ulang.])

*Hasil yang diharapkan.* Pesan sukses tampil ("&lt;kode klaster&gt; dikirim ke tinjauan analis senior."), dan badge status klaster pada halaman berubah dari "Ditandai" menjadi "Dieskalasi".

*Perubahan status.* Ditandai → Dieskalasi. Tercatat juga pada log audit internal sebagai peristiwa eskalasi.

*Pemecahan masalah.*
- *Peran Peninjau mencoba mengeskalasi atau menandai klaster organik:* ditolak dengan 403 Forbidden, status klaster tidak berubah -- akses tulis pada modul ini dibatasi ketat pada peran di atas Peninjau.
- *Mengatur sel Deteksi Koordinasi pada Matriks Izin Halaman (lihat Bab 7.7) menjadi "Tolak" untuk suatu peran:* kini benar-benar memblokir akses peran tersebut ke `/koordinasi/` dengan 403 Forbidden.
