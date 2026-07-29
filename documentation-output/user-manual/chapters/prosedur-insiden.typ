#import "/_shared/style.typ": *

= Prosedur: Insiden

Halaman Insiden (`/insiden/`) menampilkan papan ringkasan insiden dalam dua bagian ("Insiden Terkonfirmasi" dan "Kandidat") beserta ringkasan jumlah per status (Terkonfirmasi, Kandidat, Kritis, Terbuka). Detail tiap insiden tersedia pada `/insiden/<id>/`, berisi ringkasan AI, lini masa, dan formulir tindakan (tugaskan OPD, ubah status, catat).

== Melihat papan Insiden dan membuka detail

*Tujuan.* Memantau insiden yang terdeteksi sistem dan meninjau lini masa penanganannya.

*Peran yang berlaku.* Tenant Admin, Platform Super Admin, Analis, Peninjau.

*Prasyarat.* Login dengan akun yang memiliki akses ke halaman Insiden.

*Langkah-langkah.*
1. Buka halaman *Insiden* (`/insiden/`).
2. Amati ringkasan jumlah insiden per status di bagian atas.
3. Klik salah satu kartu insiden pada bagian "Insiden Terkonfirmasi" atau "Kandidat".

#screenshot("/testing-report/screenshots/insiden_detail_tenant-admin_02_awal.png", [Halaman detail insiden dengan ringkasan AI, lini masa, dan formulir tindakan.])

*Hasil yang diharapkan.* Halaman detail menampilkan ringkasan AI, lini masa kejadian, dan tiga formulir tindakan: tugaskan OPD, ubah status, dan catat.

*Perubahan status.* Tidak ada; ini murni tampilan.

== Menambah catatan pada lini masa insiden

*Tujuan.* Mendokumentasikan perkembangan penanganan sebuah insiden.

*Peran yang berlaku.* Tenant Admin, Platform Super Admin, Analis (berdasarkan pola yang sama dengan War Room, akses tulis dimaksudkan untuk peran Analis ke atas).

*Prasyarat.* Anda berada di halaman detail insiden yang relevan.

*Langkah-langkah.*
1. Buka detail insiden yang ingin dicatat.
2. Isi kolom catatan.
3. Klik tombol *Catat*.

#screenshot("/testing-report/screenshots/insiden_catat_tenant-admin_03_sukses.png", [Pesan sukses dan catatan baru yang tampil di lini masa insiden.])

*Hasil yang diharapkan.* Catatan tersimpan, pesan sukses tampil, dan catatan terlihat di lini masa.

*Perubahan status.* Tidak ada perubahan status insiden; entri baru ditambahkan ke lini masa.

*Pemecahan masalah.*
- *Mengosongkan kolom catatan:* ditolak dengan pesan error "Catatan tidak boleh kosong."
- *Peran Peninjau mencoba menambah catatan, mengubah status, menugaskan OPD, atau mengonfirmasi kandidat:* seluruh aksi tulis ini ditolak dengan 403 Forbidden -- Peninjau dapat melihat papan dan detail insiden tetapi tidak dapat mengubah data apa pun.

== Mengubah status insiden

*Tujuan.* Memperbarui status penanganan sebuah insiden (mis. dari sedang ditangani menjadi selesai).

*Peran yang berlaku.* Tenant Admin, Platform Super Admin.

*Prasyarat.* Anda berada di halaman detail insiden dan mengetahui status baru yang diizinkan.

*Langkah-langkah.*
1. Buka detail insiden.
2. Pada formulir *Ubah status*, pilih status baru yang diizinkan (mis. "Selesai").
3. Klik tombol *Ubah status*.

#screenshot("/testing-report/screenshots/insiden_ubah-status_tenant-admin_05_sukses.png", [Status insiden berubah setelah pembaruan berhasil.])

*Hasil yang diharapkan.* Status insiden berubah sesuai pilihan Anda dan pesan sukses tampil. Status ditampilkan sebagai gabungan tiga informasi, contohnya "Kritis · Ditangani · Kulon Progo" (tingkat keparahan · status penanganan · wilayah), yang berubah menjadi mis. "Kritis · Selesai · Kulon Progo" setelah pembaruan.

*Perubahan status.* Status penanganan insiden berpindah sesuai transisi yang Anda pilih pada formulir.

*Pemecahan masalah.*
- *Mengubah status insiden yang sudah tidak ada/tautan usang:* server menolak dengan halaman tidak ditemukan; tidak ada perubahan data.
