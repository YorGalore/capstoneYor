#import "/_shared/style.typ": *

= Prosedur: War Room

War Room (`/war-room/`) adalah dasbor isu aktif untuk respons cepat: menampilkan KPI, grafik volume, dan panel Log Aksi Respons yang menjadi linimasa auditable atas tindakan institusi terhadap sebuah isu/krisis narasi.

== Melihat War Room dan isu aktif

*Tujuan.* Memantau isu aktif dan riwayat aksi respons yang telah dicatat.

*Peran yang berlaku.* Analis, Tenant Admin, Platform Super Admin, Peninjau (lihat catatan di bawah untuk Peninjau).

*Prasyarat.* Login dengan akun yang memiliki akses War Room.

*Langkah-langkah.*
1. Buka halaman *War Room* (`/war-room/`).
2. Amati KPI dan grafik volume pada bagian atas halaman.
3. Gulir ke panel *Log Aksi Respons* untuk melihat linimasa tindakan yang sudah tercatat.

#screenshot("/testing-report/screenshots/warroom_lihat_analis_01_awal.png", [Halaman War Room dengan panel Log Aksi Respons.])

*Hasil yang diharapkan.* Halaman termuat dengan KPI, grafik, dan linimasa Log Aksi Respons yang terlihat.

*Perubahan status.* Tidak ada; ini murni tampilan.

== Mencatat aksi respons

*Tujuan.* Mendokumentasikan tindakan resmi yang telah diambil institusi dalam menanggapi sebuah isu, sebagai bagian dari linimasa audit War Room.

*Peran yang berlaku.* Analis, Tenant Admin, Platform Super Admin. (Peninjau dapat melihat linimasa War Room tetapi ditolak 403 saat mencoba mengirim aksi respons.)

*Prasyarat.* Anda berada di halaman War Room untuk isu yang relevan.

*Langkah-langkah.*
1. Buka halaman *War Room* (`/war-room/`).
2. Pada formulir *Log Aksi Respons*, pilih jenis aksi.
3. Isi kolom deskripsi aksi.
4. Klik tombol *Catat aksi*.
5. Muat ulang halaman untuk memverifikasi aksi tampil di linimasa.

#screenshot("/testing-report/screenshots/warroom_log-aksi_analis_03_setelah-reload.png", [Aksi respons baru terlihat di linimasa War Room setelah halaman dimuat ulang.])

*Hasil yang diharapkan.* Aksi respons tercatat dan tetap terlihat di linimasa Log Aksi Respons setelah halaman dimuat ulang.

*Perubahan status.* Tidak ada perubahan status isu; entri baru ditambahkan ke linimasa aksi respons.

*Pemecahan masalah.*
- *Pesan sukses tidak selalu tampak jelas setelah submit:* pada sebagian pengujian, indikator pesan sukses di layar tidak selalu konsisten muncul meskipun data berhasil tersimpan. Jangan hanya mengandalkan pesan sukses -- selalu muat ulang halaman dan periksa langsung apakah entri Anda muncul di linimasa.
- *Mengosongkan kolom deskripsi:* seharusnya ditolak server dengan pesan "Jenis aksi dan deskripsi wajib diisi.", namun pesan penolakan ini tidak selalu tampil jelas di antarmuka pada pengujian. Sebaiknya selalu isi kolom deskripsi sebelum mengklik Catat aksi untuk menghindari kebingungan.
- *Mencatat aksi pada isu yang sudah tidak ada/tautan usang:* server menolak dengan halaman tidak ditemukan.
- *Menekan tombol "kembali" setelah submit berhasil:* aman, tidak memicu pengiriman ulang (pola simpan-dan-muat-ulang).
- *Peran Peninjau mencoba mengirim aksi respons:* ditolak dengan 403 Forbidden, tidak ada entri baru tercatat -- linimasa audit War Room hanya dapat ditulis oleh peran Analis ke atas.
