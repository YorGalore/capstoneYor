#import "/_shared/style.typ": *

= Daftar Istilah (Glosarium)

/ *Tenant*: Satu entitas organisasi (mis. satu kabupaten/kementerian) yang menggunakan PANTAU sebagai batas isolasi data tertinggi. Setiap pengguna terhubung ke tepat satu tenant.

/ *Project*: Sub-unit di bawah Tenant yang menjadi batas isolasi data operasional (mis. kata kunci, domain, mention) untuk keperluan pemantauan tertentu.

/ *Mention (sebutan)*: Satu unit konten (unggahan media sosial atau artikel berita) yang terkumpul karena cocok dengan kata kunci/domain pemantauan.

/ *Sentimen*: Klasifikasi nada sebuah mention -- Positif, Negatif, atau Netral. Dapat dikoreksi manual oleh pengguna berwenang di halaman Umpan Sebutan.

/ *Umpan Sebutan (Feed)*: Halaman daftar mention yang terkumpul, dengan kemampuan filter, pencarian, dan koreksi sentimen.

/ *War Room*: Dasbor isu aktif untuk respons cepat terhadap krisis narasi, berisi KPI, grafik volume, dan linimasa auditable Log Aksi Respons yang mencatat tindakan resmi institusi.

/ *Insiden*: Lonjakan aktivitas/isu yang terdeteksi sistem sebagai potensi insiden yang memerlukan penanganan lintas OPD, dengan status (Terkonfirmasi/Kandidat), tingkat keparahan (mis. Kritis), dan status penanganan (mis. Ditangani/Selesai).

/ *Sorotan Eksekutif (Brief)*: Ringkasan eksekutif harian berbasis isu-isu terkini yang dihasilkan otomatis, kemudian ditinjau, disunting, disetujui, dan difinalisasi oleh tim sebelum dibagikan ke pimpinan/juru bicara. Statusnya bergerak satu arah: pending → generating → draf → final.

/ *Taksonomi Isu*: Struktur pengelompokan konten ke dalam isu-isu tertentu. Halaman Taksonomi Isu menyediakan antrean tinjauan manual untuk melabeli konten ke isu, serta fitur menggabungkan (merge) isu yang tumpang tindih.

/ *Deteksi Perilaku Tidak Otentik Terkoordinasi (Koordinasi/CIB)*: Modul deteksi klaster akun yang menunjukkan pola aktivitas terkoordinasi/tidak otentik (Coordinated Inauthentic Behavior), lengkap dengan bukti jaringan amplifikasi, sinyal koordinasi, dan sampel teks terduplikasi.

/ *Klaster*: Sekumpulan akun/konten yang terdeteksi menunjukkan pola koordinasi mencurigakan pada modul Deteksi Koordinasi. Status klaster bergerak dari "Ditandai" menjadi "Ditinjau — Organik" (jika ditandai false positive) atau dieskalasi ke tinjauan analis senior.

/ *Regional*: Halaman visualisasi distribusi narasi/sebutan berdasarkan wilayah.

/ *Sosiograf*: Halaman visualisasi jaringan interaksi antar aktor (analisis jaringan sosial).

/ *Perbandingan Narasi (Narasi)*: Halaman analisis perbandingan narasi/isu politik antar kubu/aktor, digerbangi izin tambahan "Pemantauan Politik" di luar izin halaman biasa.

/ *Pemantauan Politik*: Izin khusus per-pengguna (terpisah dari matriks izin peran x halaman) yang harus diberikan administrator agar seorang pengguna dapat mengakses halaman Perbandingan Narasi.

/ *Konsol Konfigurasi*: Halaman tunggal berisi seluruh pengaturan cakupan pemantauan tenant: Platform Terpantau, Kredensial Apify, Kata Kunci, Domain, Trigger Koleksi Manual, Aturan Peringatan, Kubu, Aktor Politik, Program Pemerintah, Kesehatan Kolektor, Penjadwalan, dan Riwayat Siklus Koleksi.

/ *Kubu*: Kelompok/faksi politik yang didaftarkan untuk keperluan analisis perbandingan narasi.

/ *Aktor Politik*: Tokoh publik yang didaftarkan untuk dilacak narasinya di media sosial/berita.

/ *Matriks Izin Halaman*: Halaman khusus Platform Super Admin (`/konfigurasi/izin/`) untuk mengatur kombinasi peran x halaman mana yang diizinkan atau ditolak.

/ *Pengaturan Dev/Ops*: Halaman khusus Platform Super Admin (`/dev-ops/`) berisi kredensial Apify tingkat sistem dan Runtime Settings.

/ *Dasbor Pengawasan*: Halaman pemantauan operasional (`/pengawasan/`) untuk Tenant Admin dan Platform Super Admin.

/ *Ekspor Data*: Fungsi unduhan seluruh data mention tenant dalam format CSV atau XLSX, diakses dari halaman Laporan.

/ *Peran (Role)*: Tingkat akses seorang pengguna -- Platform Super Admin, Tenant Admin, Analis, atau Peninjau -- yang menentukan halaman dan aksi mana yang dapat diaksesnya.

/ *Peninjau (Viewer)*: Peran yang dirancang hanya-baca (read-only), dimaksudkan untuk memantau dasbor tanpa mengubah data.
