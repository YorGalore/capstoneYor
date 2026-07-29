#import "/_shared/style.typ": *

= Prosedur: Konsol Konfigurasi, Matriks Izin, dan Dev/Ops

== Konsol Konfigurasi

Konsol Konfigurasi (`/konfigurasi/`) adalah halaman tunggal berisi banyak kartu untuk mengatur cakupan pemantauan tenant Anda: Platform Terpantau, Kredensial Apify, Kata Kunci, Domain, Trigger Koleksi Manual, Aturan Peringatan, Kubu, Aktor Politik, Program Pemerintah, Kesehatan Kolektor, Penjadwalan, dan Riwayat Siklus Koleksi. Seluruh sub-aksi (tambah/ubah/hapus) dikirim sebagai POST ke halaman yang sama.

*Peran yang berlaku untuk seluruh prosedur di bagian ini.* Tenant Admin, Platform Super Admin. Analis dan Peninjau menerima 403 Forbidden saat mencoba mengakses `/konfigurasi/` secara langsung, termasuk untuk sub-aksi POST (mis. menambah kata kunci) -- penegakan ini konsisten di seluruh kartu pada halaman ini.

=== Mengaktifkan/menonaktifkan Platform Terpantau

*Tujuan.* Mengatur platform media sosial/berita mana yang aktif dipantau.

*Prasyarat.* Anda berada di kartu Platform Terpantau pada Konsol Konfigurasi.

*Langkah-langkah.*
1. Buka *Konsol Konfigurasi* (`/konfigurasi/`).
2. Pada kartu *Platform Terpantau*, klik tombol status pada baris platform yang ingin diubah.

#screenshot("/testing-report/screenshots/konfigurasi_toggle-platform_tenant-admin_01_setelah-toggle.png", [Status platform berubah dari Aktif menjadi Nonaktif.])

*Hasil yang diharapkan.* Status berpindah antara "● Aktif" dan "● Nonaktif", dan bertahan setelah halaman dimuat ulang.

*Perubahan status.* Aktif ↔ Nonaktif. Kartu ini hanya menyediakan toggle status; tidak ada formulir tambah/hapus platform baru (daftar platform bersifat bawaan sistem).

=== Menyimpan kredensial Apify tenant

*Tujuan.* Menyimpan token API Apify yang digunakan untuk koleksi data social media tenant Anda.

*Prasyarat.* Anda memiliki token Apify yang valid dari penyedia.

*Langkah-langkah.*
1. Pada kartu *Kredensial Apify*, isi kolom token.
2. Klik tombol *Validasi & simpan*.

#screenshot("/testing-report/screenshots/konfigurasi_apify-token_tenant-admin_02b_setelah-simpan.png", [Hasil validasi token Apify.])

*Hasil yang diharapkan.* Token divalidasi langsung ke API Apify sebelum disimpan; token yang valid akan tersimpan dan ditandai aktif untuk tenant Anda.

*Perubahan status.* Tidak ada token aktif → token aktif tersimpan (jika valid).

*Pemecahan masalah.*
- *Token tidak valid:* pesan "Token Apify tidak valid — validasi API langsung gagal." tampil dan token tidak disimpan.
- Token yang sudah tersimpan tidak pernah ditampilkan kembali dalam bentuk utuh/mentah di layar manapun setelah disimpan, sebagai praktik keamanan kredensial yang baik.

=== Mengelola Kata Kunci Pemantauan

*Tujuan.* Menambah, menonaktifkan, atau menghapus kata kunci yang dipantau sistem.

*Prasyarat.* Anda berada di kartu Kata Kunci Pemantauan.

*Langkah-langkah (menambah).*
1. Isi kolom kata kunci pada kartu *Kata Kunci Pemantauan*.
2. Klik tombol *+ Tambah kata kunci*.

*Langkah-langkah (menonaktifkan/menghapus).*
1. Klik toggle nonaktif pada tag kata kunci yang dimaksud untuk menonaktifkannya tanpa menghapus.
2. Klik tombol hapus (X) pada tag untuk menghapusnya secara permanen.

#screenshot("/testing-report/screenshots/konfigurasi_tambah-kata-kunci_tenant-admin_03a_sukses.png", [Kata kunci baru berhasil ditambahkan sebagai tag aktif.])

*Hasil yang diharapkan.* Kata kunci baru muncul sebagai tag aktif di daftar; kata kunci yang dihapus tidak lagi muncul di daftar.

*Perubahan status.* Kata kunci tidak ada → aktif → (opsional) nonaktif → (opsional) dihapus permanen. Kartu ini memiliki siklus CRUD penuh.

*Pemecahan masalah.*
- *Kolom kata kunci dikosongkan:* dicegah oleh validasi wajib pada peramban.
- *Kata kunci yang sama sudah ada dalam proyek:* ditolak dengan pesan "Kata kunci ini sudah ada dalam proyek aktif."

=== Mengelola Domain Pantauan

*Tujuan.* Menambah, menguji koneksi, atau menghapus domain berita yang dipantau.

*Prasyarat.* Anda berada di kartu Situs & Domain Pantauan.

*Langkah-langkah (menambah).*
1. Isi kolom domain (mis. `contoh.example.id`), pilih adapter (mis. "RSS"), dan isi feed URL bila diperlukan.
2. Klik tombol *+ Tambah domain*.

*Langkah-langkah (menguji koneksi domain yang sudah ada).*
1. Klik tombol *Uji koneksi* pada baris domain yang dimaksud.

*Langkah-langkah (menghapus).*
1. Klik tombol *Hapus* pada baris domain yang dimaksud.

#screenshot("/testing-report/screenshots/konfigurasi_uji-koneksi-domain_tenant-admin_04f_hasil.png", [Hasil uji koneksi sebuah domain pantauan.])

*Hasil yang diharapkan.* Domain baru muncul di daftar; uji koneksi menampilkan pesan hasil (mis. "Koneksi ke '&lt;domain&gt;' berhasil."); domain yang dihapus tidak lagi muncul di daftar.

*Perubahan status.* Domain tidak ada → tersimpan → (opsional) dihapus. Status uji koneksi domain dapat berubah antara Aktif/Perlu tinjauan sesuai hasil pengujian.

*Pemecahan masalah.*
- *Kolom domain/adapter dikosongkan:* dicegah oleh validasi wajib pada peramban.
- *Domain duplikat dalam proyek yang sama:* ditolak dengan pesan "Domain ini sudah dipantau dalam proyek aktif."
- *Format domain tidak wajar (mengandung spasi, tanpa titik):* saat ini sistem *tidak* menolak nilai semacam ini -- nilai yang jelas bukan format domain (mis. "domain tanpa titik dan spasi") dapat tersimpan tanpa pesan validasi format. Periksa kembali ejaan domain secara manual sebelum menyimpan, karena sistem tidak akan mengoreksi Anda. Domain yang salah format berpotensi gagal secara diam-diam pada tahap koleksi berikutnya, bukan pada saat Anda menyimpannya.

=== Memicu koleksi manual (Berita & Social Media)

*Tujuan.* Menjalankan siklus koleksi data secara manual di luar jadwal otomatis.

*Prasyarat.* Untuk koleksi Social Media, token Apify tenant harus sudah tersimpan dan aktif (lihat "Menyimpan kredensial Apify tenant" di atas).

*Langkah-langkah.*
1. Pada kartu *Trigger Koleksi Manual*, klik tombol *Mulai Berita* dan/atau *Mulai Social Media*.
2. Amati status live pada kartu (diperbarui otomatis via polling).

#screenshot("/testing-report/screenshots/konfigurasi_trigger-koleksi-berita_tenant-admin_05b_setelah-klik.png", [Status kartu Trigger Koleksi Berita setelah diklik.])

*Hasil yang diharapkan.* Trigger masuk antrean proses asinkron (worker); status kartu berubah mengikuti progres (mis. "Dalam antrean" → diproses → selesai/gagal).

*Perubahan status.* Siap → Dalam antrean/Diproses → Selesai atau Gagal.

*Pemecahan masalah.*
- *Trigger Social Media gagal/tertahan:* jika token Apify tenant belum tersimpan/aktif, sistem menolak trigger dengan pesan yang meminta Anda menyimpan token aktif terlebih dahulu -- ini perilaku yang benar sesuai desain, bukan bug.
- Hasil trigger bergantung pada ketersediaan worker asinkron di lingkungan server Anda; status yang tertahan lama di "Diproses" dapat menandakan worker belum berjalan -- hubungi administrator platform bila ini terjadi berkelanjutan.

=== Mengelola Aturan Peringatan

*Tujuan.* Mengatur kondisi otomatis yang memicu peringatan (mis. lonjakan sentimen negatif).

*Prasyarat.* Anda berada di kartu Aturan Peringatan.

*Langkah-langkah (menambah).*
1. Isi nama aturan, pilih kondisi (mis. "Rasio sentimen negatif melewati ambang"), isi ambang batas, jendela waktu (menit), dan kanal notifikasi.
2. Klik tombol *+ Tambah aturan*.

*Langkah-langkah (menonaktifkan/menghapus).*
1. Klik toggle nonaktif pada aturan yang dimaksud.
2. Klik tombol hapus untuk menghapus permanen.

#screenshot("/testing-report/screenshots/konfigurasi_tambah-aturan-peringatan_tenant-admin_06a_sukses.png", [Aturan peringatan baru tersimpan dan muncul di tabel.])

*Hasil yang diharapkan.* Aturan baru muncul di tabel Aturan Peringatan dengan ringkasan kondisi otomatis.

*Perubahan status.* Aturan tidak ada → aktif → (opsional) nonaktif → (opsional) dihapus. Siklus CRUD penuh.

*Pemecahan masalah.*
- *Nama aturan dikosongkan:* ditolak (wajib diisi).
- *Ambang batas di luar rentang wajar untuk kondisi yang dipilih* (mis. mengisi ambang 5 untuk kondisi rasio sentimen negatif yang seharusnya pecahan 0–1): ditolak dengan pesan validasi spesifik, mis. "Untuk rasio negatif, ambang adalah pecahan 0–1 (mis. 0.5)."

=== Mengelola Kubu Politik

*Tujuan.* Mendaftarkan kubu/faksi politik untuk keperluan analisis perbandingan narasi.

*Prasyarat.* Anda berada di kartu Entitas Politik & Program Terlacak, bagian Kubu.

*Langkah-langkah (menambah).*
1. Isi nama kubu (warna dapat dibiarkan bawaan).
2. Klik tombol *+ Tambah kubu*.

*Langkah-langkah (menghapus).*
1. Klik tombol "X" pada tag kubu yang dimaksud.

#screenshot("/testing-report/screenshots/konfigurasi_tambah-kubu_tenant-admin_07a_sukses.png", [Kubu politik baru tersimpan sebagai tag.])

*Hasil yang diharapkan.* Kubu baru muncul sebagai tag pada daftar; kubu yang dihapus tidak lagi muncul.

*Perubahan status.* Kubu tidak ada → tersimpan → (opsional) dihapus. Tidak ada aksi edit/toggle untuk kartu ini secara desain.

*Pemecahan masalah.*
- *Nama kubu dikosongkan:* ditolak (wajib diisi).
- *Nama kubu duplikat:* ditolak dengan pesan "Kubu dengan nama ini sudah ada."

=== Mengelola Aktor Politik Publik

*Tujuan.* Mendaftarkan tokoh/aktor politik publik yang perlu dilacak.

*Prasyarat.* Anda berada di bagian Aktor Politik Publik.

*Langkah-langkah (mendaftarkan).*
1. Isi nama aktor, jenis (mis. Partai), kata kunci terkait, dan akun media sosial.
2. Klik tombol *+ Daftarkan aktor*.

*Langkah-langkah (menonaktifkan/mengaktifkan).*
1. Klik toggle status pada baris aktor yang dimaksud.

*Langkah-langkah (menghapus permanen).*
1. Klik tombol *Hapus* (✕) pada baris aktor yang dimaksud.

#screenshot("/testing-report/screenshots/ISS-KONFIGURASI-005_reverifikasi_diperbaiki.png", [Tombol "Hapus" kini tersedia pada baris Aktor Politik Publik, konsisten dengan kartu Kubu/Kata Kunci/Domain/Program.])

*Hasil yang diharapkan.* Aktor baru muncul di tabel Aktor Politik Publik; status aktor dapat dibalik antara Aktif/Nonaktif; aktor yang dihapus tidak lagi muncul di tabel setelah dimuat ulang.

*Perubahan status.* Tidak terdaftar → terdaftar (aktif) → (opsional) nonaktif ↔ aktif, atau dihapus permanen.

*Pemecahan masalah.*
- *Nama aktor dikosongkan:* ditolak (wajib diisi).
- Jika Anda salah mendaftarkan aktor (mis. typo nama), gunakan tombol Hapus untuk membersihkannya sepenuhnya, alih-alih hanya menonaktifkan.

=== Mengelola Program Pemerintah Terlacak

*Tujuan.* Mendaftarkan program pemerintah yang perlu dipantau narasinya.

*Prasyarat.* Anda berada di bagian Program Pemerintah Terlacak.

*Langkah-langkah (menambah).*
1. Isi nama program, instansi penanggung jawab, dan kata kunci terkait.
2. Klik tombol *+ Tambah program*.

*Langkah-langkah (menghapus).*
1. Klik tombol *Hapus* pada baris program yang dimaksud.

#screenshot("/testing-report/screenshots/konfigurasi_tambah-program_tenant-admin_09a_sukses.png", [Program pemerintah baru tersimpan di tabel.])

*Hasil yang diharapkan.* Program baru muncul di tabel; program yang dihapus tidak lagi muncul.

*Perubahan status.* Tidak ada → tersimpan → (opsional) dihapus. Siklus CRUD (tambah + hapus).

*Pemecahan masalah.*
- *Nama program dikosongkan:* ditolak (wajib diisi).

=== Mengubah penjadwalan koleksi data

*Tujuan.* Mengatur seberapa sering (kadensi) sebuah pekerjaan koleksi data dijalankan otomatis.

*Prasyarat.* Anda berada di kartu Penjadwalan Pekerjaan.

*Langkah-langkah.*
1. Ubah nilai kadensi (dalam menit) pada baris pekerjaan yang dimaksud.
2. Klik tombol *Simpan*.

#screenshot("/testing-report/screenshots/konfigurasi_ubah-jadwal_tenant-admin_11a_sukses.png", [Kadensi penjadwalan berhasil diperbarui.])

*Hasil yang diharapkan.* Kadensi baru tersimpan dan bertahan setelah halaman dimuat ulang.

*Perubahan status.* Kadensi lama → kadensi baru.

*Pemecahan masalah.*
- *Mengisi kadensi 0 menit:* ditolak oleh server (mencegah pekerjaan berjalan tanpa henti/runaway job), nilai kembali ke nilai sebelumnya.

=== Melihat Kesehatan Kolektor dan Riwayat Siklus Koleksi

*Tujuan.* Memantau status kesehatan tiap sumber koleksi data dan riwayat siklus koleksi yang sudah berjalan.

*Prasyarat.* Tidak ada; kedua kartu ini bersifat hanya-baca (view-only), tidak ada formulir tambah/hapus/ubah.

*Langkah-langkah.*
1. Buka kartu *Kesehatan Kolektor* untuk melihat status per sumber (status, kegagalan berturut-turut, sukses terakhir, tingkat sukses, galat terakhir).
2. Buka kartu *Riwayat Siklus Koleksi* untuk melihat riwayat (sumber, status, item, estimasi biaya, waktu selesai).

#screenshot("/testing-report/screenshots/konfigurasi_lihat-kesehatan-kolektor_tenant-admin_10_view.png", [Tabel Kesehatan Kolektor.])

*Hasil yang diharapkan.* Kedua tabel menampilkan data historis/status terkini secara akurat.

*Perubahan status.* Tidak ada; halaman ini murni pemantauan.

=== Kartu Koleksi Data (kill switch)

*Tujuan.* Menghentikan seluruh koleksi data tenant Anda dalam keadaan darurat.

*Prasyarat.* Gunakan dengan hati-hati -- tombol ini menghentikan seluruh koleksi data, bukan per sumber.

*Langkah-langkah.*
1. Buka kartu *Koleksi Data*.
2. Amati status koleksi (berjalan/dihentikan).
3. Klik tombol *■ Hentikan Semua Koleksi* hanya bila Anda memang bermaksud menghentikan seluruh koleksi data tenant.

#screenshot("/testing-report/screenshots/konfigurasi_lihat-kill-switch-koleksi_tenant-admin_13_view.png", [Kartu Koleksi Data dengan tombol penghenti darurat.])

*Hasil yang diharapkan.* Status koleksi berpindah antara berjalan dan dihentikan.

*Perubahan status.* Berjalan ↔ Dihentikan (tenant-wide).

*Pemecahan masalah.*
- Karena dampaknya menyeluruh pada tenant, pastikan Anda benar-benar bermaksud menghentikan seluruh koleksi data sebelum mengklik tombol ini; tidak ada konfirmasi tambahan sebelum tombol dieksekusi pada pengujian ini.

== Matriks Izin Halaman <sec-matriks-izin>

Matriks Izin Halaman (`/konfigurasi/izin/`) mengatur kombinasi peran x halaman mana yang diizinkan atau ditolak.

*Peran yang berlaku.* Platform Super Admin saja. Tenant Admin, Analis, dan Peninjau menerima 403 Forbidden saat mencoba mengakses halaman ini secara langsung.

=== Melihat matriks dan mengubah sebuah sel

*Tujuan.* Meninjau dan menyesuaikan akses suatu peran ke suatu halaman.

*Prasyarat.* Login sebagai Platform Super Admin.

*Langkah-langkah.*
1. Buka *Matriks Izin Halaman* (`/konfigurasi/izin/`).
2. Amati tabel peran x halaman; sel dengan ikon gembok terkunci untuk kombinasi yang memang dicadangkan (mis. seluruh kolom Platform Super Admin, dan baris Matriks Izin Halaman & Pengaturan Dev/Ops untuk peran lain).
3. Klik sel yang tidak terkunci (mis. Regional x Analis) untuk mengganti nilainya antara "Izin" dan "Tolak".
4. Muat ulang halaman untuk memverifikasi perubahan tersimpan.

#screenshot("/testing-report/screenshots/izin_lihat-matriks_dewi-anjani_00_awal.png", [Matriks Izin Halaman menampilkan 16 baris halaman x 4 kolom peran.])

*Hasil yang diharapkan.* Perubahan pada sel tersimpan dan bertahan setelah halaman dimuat ulang; dapat dikembalikan ke nilai semula dengan mengklik kembali.

*Perubahan status.* Izin ↔ Tolak untuk kombinasi peran x halaman yang dipilih.

*Pemecahan masalah.*
- Mengubah sel matriks menjadi "Tolak" untuk halaman apa pun pada registry (termasuk Ringkasan, War Room, Perbandingan Narasi, Regional, dan Deteksi Perilaku Tidak Otentik Terkoordinasi) kini benar-benar memblokir akses peran tersebut, diverifikasi menghasilkan 403 Forbidden ketika diakses langsung. Ini berlaku seragam di seluruh 16 halaman pada registry.

== Pengaturan Dev/Ops <sec-devops>

Pengaturan Dev/Ops (`/dev-ops/`) berisi kartu Kredensial Apify tingkat sistem dan Runtime Settings.

*Peran yang berlaku.* Platform Super Admin saja. Tenant Admin, Analis, dan Peninjau menerima 403 Forbidden.

=== Menyimpan runtime setting baru

*Tujuan.* Menambahkan/mengubah pengaturan runtime tingkat sistem.

*Prasyarat.* Login sebagai Platform Super Admin.

*Langkah-langkah.*
1. Buka *Pengaturan Dev/Ops* (`/dev-ops/`).
2. Isi kolom kunci (key) pengaturan dan nilainya.
3. Klik tombol *Simpan*.

#screenshot("/testing-report/screenshots/devops_simpan-runtime-setting_dewi-anjani_02_hasil.png", [Runtime setting baru tersimpan dan muncul di tabel.])

*Hasil yang diharapkan.* Pesan sukses ("Pengaturan '&lt;kunci&gt;' diperbarui.") tampil dan baris baru muncul di tabel Runtime Settings.

*Perubahan status.* Pengaturan tidak ada/nilai lama → nilai baru tersimpan.

#belum_tersedia[
  *Tidak ada aksi hapus untuk Runtime Settings di antarmuka.* Setelah sebuah pengaturan disimpan, tidak ditemukan cara menghapusnya kembali melalui UI -- hanya tambah/ubah nilai yang tersedia. Berhati-hatilah saat menambahkan kunci pengaturan baru; pastikan penamaan kunci sudah benar sejak awal karena entri tidak dapat dibersihkan sendiri dari antarmuka.
]

=== Memvalidasi token Apify tingkat sistem

*Tujuan.* Menyimpan/menguji kredensial Apify tingkat sistem (berbeda dari token tenant pada Konsol Konfigurasi).

*Prasyarat.* Login sebagai Platform Super Admin.

*Langkah-langkah.*
1. Pada kartu *Kredensial Apify*, isi kolom token.
2. Klik tombol *Validasi & simpan*.

#screenshot("/testing-report/screenshots/devops_simpan-token-palsu_dewi-anjani_01_hasil.png", [Hasil validasi token Apify palsu -- ditolak dengan pesan error.])

*Hasil yang diharapkan.* Token divalidasi ke API Apify sungguhan sebelum disimpan; token yang tidak valid ditolak dengan pesan error.

*Perubahan status.* Tidak ada token aktif → token aktif tersimpan (jika valid).
