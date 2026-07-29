#import "/_shared/style.typ": *

= Laporan dan Ekspor Data

== Melihat halaman Laporan

*Tujuan.* Meninjau pusat laporan analitik: rekap periode, tren, komposisi sentimen, sebaran platform, tema dominan, dan arsip Sorotan Eksekutif.

*Peran yang berlaku.* Tenant Admin, Platform Super Admin, Analis, Peninjau.

*Prasyarat.* Login dengan akun yang memiliki akses ke halaman Laporan.

*Langkah-langkah.*
1. Buka halaman *Laporan* (`/laporan/`).
2. Tinjau ringkasan rekap, tren, komposisi sentimen, sebaran platform, dan tema dominan.

#screenshot("/testing-report/screenshots/laporan_lihat_admin_01_halaman-awal.png", [Halaman Laporan dengan rekap periode dan tombol unduh/cetak.])

*Hasil yang diharapkan.* Halaman termuat lengkap dengan seluruh bagian rekap.

*Perubahan status.* Tidak ada; murni tampilan.

== Memfilter rentang periode rekap

*Tujuan.* Melihat rekap untuk rentang waktu yang berbeda (7, 30, atau 90 hari terakhir).

*Peran yang berlaku.* Tenant Admin, Platform Super Admin, Analis, Peninjau.

*Prasyarat.* Anda berada di halaman Laporan.

*Langkah-langkah.*
1. Pada dropdown *Periode rekap*, pilih rentang yang diinginkan (7 hari / 30 hari / 90 hari).

*Hasil yang diharapkan.* Halaman otomatis memuat ulang (auto-submit) begitu pilihan diubah, dan seluruh data rekap menyesuaikan rentang yang dipilih.

#screenshot("/testing-report/screenshots/laporan_filter_admin_02_periode-90hari.png", [Rekap periode menyesuaikan setelah memilih 90 hari terakhir.])

*Perubahan status.* Tidak ada; ini murni penyaringan tampilan.

*Pemecahan masalah.*
- Tidak tersedia pencarian teks bebas atau filter tanggal kustom (dari/sampai) di halaman ini -- hanya tiga pilihan periode preset (7/30/90 hari).

== Mengunduh data mention (Ekspor)

*Tujuan.* Mengunduh seluruh data mention tenant Anda sebagai berkas CSV atau XLSX untuk dianalisis lebih lanjut di luar aplikasi.

*Peran yang berlaku.* Tenant Admin, Platform Super Admin, Analis. (Peninjau ditolak -- lihat catatan di bawah.)

*Prasyarat.* Login dengan akun yang memiliki akses ekspor.

*Langkah-langkah.*
1. Buka halaman *Laporan* (`/laporan/`).
2. Klik tombol *Unduh Data (CSV)* atau *Unduh Data (XLSX)*.

*Hasil yang diharapkan.* Berkas terunduh langsung (bukan berupa halaman HTML) berisi seluruh baris data mention tenant Anda, dengan kolom: `mention_id, platform, author, sentiment, emotion, posted_at, engagement, matched_keyword, source_url, content`.

*Perubahan status.* Tidak ada; ini murni pengambilan data baca.

*Pemecahan masalah.*
- *Peran Peninjau tidak dapat mengunduh data ekspor:* percobaan akses menghasilkan 403 Forbidden. Halaman ekspor tidak termasuk akses bawaan Peninjau (berbeda dengan halaman Laporan itu sendiri, yang tetap dapat dilihat Peninjau).

#belum_tersedia[
  *Ekspor belum dapat mengikuti filter yang sedang aktif.* Tombol unduh CSV/XLSX pada halaman Laporan (dan tidak ada tombol ekspor sama sekali di halaman Umpan Sebutan) selalu mengekspor *seluruh* data mention tenant, tanpa opsi untuk membatasi hanya pada filter platform/sentimen/rentang tanggal yang sedang Anda gunakan. Jika Anda hanya memerlukan data untuk rentang/filter tertentu, unduh data lengkap lalu saring secara manual di luar aplikasi (mis. di Excel/spreadsheet).
]

== Mencetak brief dari Arsip Sorotan

*Tujuan.* Membuka versi cetak sebuah Sorotan Eksekutif yang telah difinalisasi, langsung dari halaman Laporan.

*Peran yang berlaku.* Tenant Admin, Platform Super Admin.

*Prasyarat.* Terdapat entri pada Arsip Sorotan di halaman Laporan.

*Langkah-langkah.*
1. Buka halaman *Laporan* (`/laporan/`).
2. Pada bagian Arsip Sorotan, klik tautan *Cetak* pada baris brief yang diinginkan.

*Hasil yang diharapkan.* Tab baru terbuka menampilkan versi cetak brief terkait (halaman `/brief/<id>/cetak/` yang sama dengan yang dijelaskan pada Bab 7.4).

*Perubahan status.* Tidak ada; ini murni navigasi ke halaman baca-saja.
