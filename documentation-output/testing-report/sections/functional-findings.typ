#import "../../_shared/style.typ": *

= Temuan Fungsional <sec-functional>

Bagian ini menceritakan kembali kasus uji yang paling relevan dari `test-cases.csv` (154 baris), dikelompokkan per modul. Daftar penuh dan lengkap dengan langkah, hasil yang diharapkan, hasil aktual, serta seluruh referensi tangkapan layar tersedia sebagai deliverable terpisah (`test-cases.csv`); bagian ini fokus pada pola yang berarti bagi pembaca.

== Konsol Konfigurasi

Modul dengan cakupan pengujian terbesar (36 kasus uji): kartu Platform Terpantau, Kata Kunci, Domain, Kubu Politik, Aktor Politik, Program Pemerintah, Aturan Peringatan, Kredensial Apify, Trigger Koleksi Manual, Kesehatan Kolektor, Penjadwalan, dan Riwayat Siklus Koleksi. Seluruh alur tambah/validasi-negatif/hapus/toggle untuk Kata Kunci, Domain, Kubu, dan Aturan Peringatan berjalan konsisten (data valid tersimpan, field kosong dan duplikat ditolak dengan pesan yang jelas). Dua pola tidak ideal namun bukan blocker fungsional tercatat: (1) form domain menerima nilai malformasi (tanpa titik/TLD, mengandung spasi) karena tidak ada validator format (TC-KONFIGURASI-020, lihat ISS-KONFIGURASI-004); (2) Aktor Politik hanya bisa dinonaktifkan, tidak bisa dihapus permanen -- pola "tambah tapi tidak bisa hapus" yang berbeda dari Kubu/Kata Kunci/Domain/Program (TC-KONFIGURASI-034, ISS-KONFIGURASI-005).

#screenshot("/testing-report/screenshots/konfigurasi_tambah-domain_tenant-admin_04a_sukses.png", "Penambahan domain pantauan baru pada Konsol Konfigurasi berhasil dengan validasi keunikan yang berfungsi.")

== Sorotan Eksekutif (Daily Brief)

16 kasus uji menelusuri state machine penuh: buat draf -> tinjau/setujui isu per isu -> finalisasi -> versi cetak. Alur happy-path berjalan baik untuk Tenant Admin, termasuk validasi negatif (tanggal kosong, finalisasi tanpa isu ditinjau, percobaan finalisasi ganda semuanya ditolak dengan benar). Dua masalah tampilan tercatat: chip risiko pada setiap kartu isu menampilkan representasi dict Python mentah alih-alih label terjemahan tunggal (ISS-BTX-004), dan banner draft "menunggu tinjauan manusia" tetap tertanam pada versi cetak brief yang sudah Final (ISS-BTX-005). Tidak ditemukan jalur untuk membatalkan finalisasi/merevisi brief yang sudah dikunci (ISS-BTX-001) -- lihat @sec-proposed untuk usulan alur perbaikannya. Yang paling signifikan: peran Peninjau berhasil men-trigger pembuatan draf brief melalui POST langsung ke `/brief/buat/` (ISS-BTX-002, High), dibahas di @sec-exec-summary.

#screenshot("/testing-report/screenshots/brief_finalisasi_admin_06_sukses.png", "Finalisasi brief berhasil -- namun perhatikan chip risiko yang menampilkan representasi dict Python mentah alih-alih label Indonesia tunggal (ISS-BTX-004).")

== Umpan Sebutan (Feed)

15 kasus uji. Koreksi sentimen mention (fitur inti FR-5.3) berfungsi end-to-end untuk Tenant Admin: filter platform, paginasi, pencarian penulis, dan submit koreksi seluruhnya bekerja sesuai ekspektasi, termasuk penolakan `mention_id` palsu dan nilai sentimen tidak valid. Namun peran Analis -- yang secara fungsional bertanggung jawab atas koreksi sentimen -- mendapat 403 saat mengakses `/umpan/` karena `feed` tidak termasuk `DASHBOARD_PAGES` default (F-FW-001, ISS-FW-001, Low); pengujian alur happy-path dialihkan ke Tenant Admin sebagai konsekuensinya. Fitur pengurutan (sort) tidak tersedia secara desain (Not Available, bukan bug).

#screenshot("/testing-report/screenshots/feed_koreksi-sentimen_tenant-admin_02_sukses.png", "Koreksi sentimen mention berhasil tersimpan pada Umpan Sebutan.")

== War Room

10 kasus uji. Alur log respons happy-path (Analis mengisi form, submit, entri muncul di linimasa setelah reload) berjalan baik secara fungsional. Namun probe otorisasi eksplisit (F-FW-018, F-FW-019) mengonfirmasi bahwa `log_response` tidak memiliki pengecekan peran apa pun -- peran Peninjau berhasil menulis ke linimasa audit resmi ini (ISS-FW-002, Critical), temuan paling serius pada laporan ini bersama celah Koordinasi.

#screenshot("/testing-report/screenshots/warroom_log-aksi_analis_02_sukses.png", "Log aksi respons War Room berhasil dicatat oleh peran Analis -- linimasa yang sama juga berhasil ditulis oleh peran Peninjau pada probe otorisasi terpisah.")

== Insiden

7 kasus uji. Papan Insiden, detail insiden, penambahan catatan pada lini masa, dan transisi status seluruhnya berfungsi untuk Tenant Admin, termasuk penolakan catatan kosong dan `incident_id` palsu. Sama seperti War Room, probe otorisasi menemukan bahwa `insiden_note` memakai `@require_page('insiden')` -- tapi karena `insiden` termasuk `DASHBOARD_PAGES` yang default `True` untuk viewer, Peninjau tetap lolos menambah catatan pada lini masa insiden (F-FW-026, ISS-FW-003, High).

== Taksonomi Isu

10 kasus uji. Pelabelan konten pada antrean tinjauan manual dan penggabungan (merge) dua isu berfungsi dan persisten setelah reload; unmerge tidak tersedia di UI. Validasi negatif (gabung tanpa memilih source/target) ditangani dengan benar.

#screenshot("/testing-report/screenshots/taksonomi_gabung_admin_03_setelah-gabung.png", "Penggabungan dua isu pada Taksonomi Isu berhasil dan tercermin pada riwayat setelah reload halaman.")

== Deteksi Koordinasi

10 kasus uji. Daftar klaster, detail/evidence klaster, dan aksi "tandai organik" (false positive) berfungsi untuk Tenant Admin. Namun eskalasi klaster ke tinjauan analis senior hanya mencatat entri audit log tanpa mengubah status klaster yang terlihat di UI manapun pada modul ini (TC-KOORDINASI-003, ISS-KOORDINASI-001, Medium) -- lihat @sec-proposed. Fungsi pencarian/filter klaster tidak tersedia (Not Available). Yang paling kritis: baik aksi eskalasi/tandai-organik maupun akses halaman itu sendiri tidak digerbang peran sama sekali (ISS-KOORDINASI-002 dan ISS-KOORDINASI-003), dibahas di @sec-exec-summary.

#screenshot("/testing-report/screenshots/koordinasi_lihat-klaster_tenant-admin_01_daftar.png", "Daftar klaster Deteksi Koordinasi pada tampilan Tenant Admin.")

== Laporan, Ekspor, dan Analitik Lain (Narasi, Regional, Sosiograf)

Halaman Laporan (4 kasus uji: akses, filter periode 7/30/90 hari, cetak brief dari arsip, tombol ekspor) berfungsi baik. Ekspor mention (5 kasus uji) berhasil menghasilkan file CSV dan XLSX yang valid dan menegakkan otorisasi dengan benar (403 untuk Peninjau); satu-satunya catatan adalah tidak adanya ekspor granular per-filter (ISS-BTX-003, Enhancement). Narasi (Blocked untuk Analis dan Peninjau karena gerbang izin Pemantauan Politik terpisah -- bekerja sesuai desain), Regional, dan Sosiograf (masing-masing 3 kasus uji) seluruhnya menampilkan halaman dengan benar untuk peran yang berwenang.

#screenshot("/testing-report/screenshots/laporan_lihat_admin_01_halaman-awal.png", "Halaman Laporan menampilkan pusat rekap analitik dengan filter periode.")

== Tata Kelola (Konfigurasi Izin, Pengawasan, Dev-Ops)

Matriks Izin Halaman (4 kasus uji) menampilkan matriks dengan benar dan toggle sel non-reserved tersimpan persisten -- namun sebagaimana dibahas di @sec-rbac, toggle ini secara diam-diam tidak berefek untuk 5 dari 16 halaman yang terdaftar. Dasbor Pengawasan (4 kasus uji) dan Dev-Ops (3 kasus uji, termasuk simpan token Apify palsu dan runtime setting baru) berfungsi dan menegakkan akses khusus Super Admin/Tenant Admin dengan benar.

#screenshot("/testing-report/screenshots/pengawasan_lihat-dasbor_dewi-anjani_01.png", "Dasbor Pengawasan tampil untuk peran Super Admin.")

== Autentikasi, Onboarding, dan Profil

Login/logout (9 kasus uji) berfungsi penuh termasuk penolakan kredensial salah dan proteksi halaman setelah logout (redirect ke login, tombol "back" browser tidak membuka ulang halaman terproteksi). Satu catatan kosmetik: label peran yang tampil di sidebar berasal dari `role_label` (jabatan bebas teks, default "Analis Humas") bukan peran RBAC teknis -- bahkan Super Admin tampil sebagai "Analis Humas" (AUTH-ISSUE-001, Low). Formulir onboarding publik (6 kasus uji) menerima submission valid dan menolak field kosong/email tidak valid, namun tidak mendeteksi duplikat (ONB-ISSUE-002) dan halaman konfirmasi dapat diakses langsung tanpa submission sebelumnya (ONB-ISSUE-001). Verifikasi data onboarding via Django admin terblokir untuk Super Admin karena peran aplikasi tidak dipetakan ke `is_staff` (ONB-ISSUE-003, Blocked).

#screenshot("/testing-report/screenshots/auth_login-valid_dewi-anjani_01_ringkasan.png", "Login berhasil dan redirect ke /ringkasan/ -- perhatikan label peran di sidebar yang menampilkan jabatan bebas teks, bukan peran RBAC teknis.")
