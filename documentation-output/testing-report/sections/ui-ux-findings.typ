#import "../../_shared/style.typ": *

= Temuan UI/UX

Temuan pada bagian ini disintesis dari catatan (`notes`) pada `test-cases.csv` dan `issue-register.csv` yang bersifat pengalaman pengguna, bukan kegagalan fungsional murni.

== Navigasi Menampilkan Tautan ke Halaman yang Akan Ditolak

Sidebar (`templates/core/_sidebar.html`) sudah menerapkan pola yang benar untuk "Umpan Sebutan" dan "Taksonomi Isu": tautan dinonaktifkan (`can_view_feed`, `can_view_taxonomy`) untuk peran yang tidak berwenang. Namun pola ini tidak diterapkan konsisten -- tautan "Konfigurasi" dan "Pengawasan" selalu dirender sebagai tautan aktif untuk semua peran yang login, termasuk Analis dan Peninjau yang dikonfirmasi menerima 403 Forbidden saat benar-benar mengklik salah satunya (UX-ISSUE-001, Medium). Pengguna melihat tautan yang tampak dapat diklik, mengkliknya, lalu mendapat halaman error tanpa penjelasan kontekstual di navigasi itu sendiri -- menimbulkan kesan aplikasi "rusak" meski server menolak dengan benar.

#screenshot("/testing-report/screenshots/pengawasan_lihat-dasbor_qa-peninjau_01.png", "Peran Peninjau menerima halaman ditolak saat mengklik tautan Pengawasan yang tetap tampil aktif di sidebar.")

== Umpan Balik Validasi Formulir

Pola validasi negatif pada Konsol Konfigurasi (field kosong, nilai duplikat, ambang di luar rentang) konsisten menampilkan pesan kesalahan yang jelas di seluruh kartu (Kata Kunci, Domain, Kubu, Aktor, Program, Aturan Peringatan) -- ini adalah salah satu pola UI paling konsisten yang ditemukan pada aplikasi. Pengecualian: form domain menerima nilai tanpa validasi format sama sekali (spasi, tanpa TLD) dan menampilkannya seolah sukses tersimpan (ISS-KONFIGURASI-004), tidak konsisten dengan kartu lain yang menolak input tidak valid secara eksplisit.

== Representasi Data Mentah Bocor ke Tampilan

Dua temuan pada modul Sorotan Eksekutif menunjukkan representasi data internal (Python) bocor langsung ke tampilan yang dibaca pengguna akhir/pimpinan: chip risiko menampilkan seluruh dict `RISK_LABELS` mentah diikuti nilai `risk_level` mentah alih-alih satu label terjemahan (ISS-BTX-004, Medium; juga muncul pada versi cetak, ISS-BTX-005, Low). Ini adalah kelas masalah UI yang sama menyerang dokumen resmi institusi -- brief final yang dicetak untuk spokesperson.

== Label Peran Tidak Mencerminkan Hak Akses Sebenarnya

Sidebar menampilkan `AnalystProfile.role_label`, sebuah field jabatan bebas teks (default "Analis Humas") yang tidak disinkronkan dengan field `role` yang sebenarnya menentukan RBAC. Dikonfirmasi: akun `dewi.anjani` dengan `role=super_admin` tetap menampilkan "Analis Humas" di sidebar, tidak menyebut "Super Admin" sama sekali (AUTH-ISSUE-001, Low). Ini membuat troubleshooting akses ("kenapa saya tidak bisa akses X") sulit dilakukan pengguna sendiri karena antarmuka tidak pernah menunjukkan peran RBAC teknis mereka secara eksplisit.

#screenshot("/testing-report/screenshots/auth_login-valid_qa-peninjau_01_ringkasan.png", "Sidebar menampilkan jabatan bebas teks, bukan label peran RBAC (Peninjau) yang sebenarnya menentukan akses akun ini.")

== Konfirmasi dan Visibilitas Status

Aksi tulis pada umumnya memberi umpan balik yang jelas dan persisten setelah reload (koreksi sentimen, catatan insiden, label taksonomi, penambahan entri konfigurasi). Pengecualian mencolok: eskalasi klaster koordinasi hanya tercatat di audit log yang tidak ditampilkan di UI manapun pada modul itu, sehingga tim tidak dapat membedakan klaster yang sudah dieskalasi dari yang belum tanpa membuka log terpisah (ISS-KOORDINASI-001, Medium) -- inkonsistensi visibilitas status dibanding pola konfirmasi yang sudah baik di modul lain.

== Halaman yang Bermakna Ganda

Halaman konfirmasi onboarding publik (`/mulai/berhasil/`) menampilkan pesan sukses penuh terlepas dari apakah pengguna baru saja submit formulir atau sekadar mengunjungi URL secara langsung, tanpa cara memverifikasi data yang "tersimpan" (ONB-ISSUE-001, Low) -- berpotensi menyesatkan pengguna publik yang menemukan tautan tersebut lewat berbagi tautan atau bookmark lama.
