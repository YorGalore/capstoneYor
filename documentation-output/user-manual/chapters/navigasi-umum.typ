#import "/_shared/style.typ": *

= Pola Navigasi Umum

Beberapa pola interaksi berulang di banyak modul PANTAU. Bab ini merangkumnya satu kali agar tidak perlu diulang pada setiap prosedur.

== Filter

Halaman yang menampilkan daftar data (mis. Umpan Sebutan) menyediakan kontrol filter berbentuk dropdown dan/atau kolom teks di bagian atas tabel, diikuti tombol *Saring*. Setelah filter diterapkan, pilihan filter tercermin pada parameter URL (query string) dan tetap terisi pada kontrolnya sendiri, sehingga Anda bisa menyalin/membagikan tautan hasil filter tersebut.

== Pencarian

Kolom pencarian bertindak sebagai filter teks bebas (mis. mencari berdasarkan nama penulis pada Umpan Sebutan). Jika tidak ada data yang cocok, halaman menampilkan pesan kondisi kosong yang jelas (mis. "Belum ada mention yang cocok.") alih-alih tabel kosong tanpa penjelasan.

== Paginasi

Untuk daftar panjang, kontrol paginasi ("Sebelumnya"/"Berikutnya") muncul otomatis ketika jumlah baris melebihi batas per halaman (25 baris). Jika data pada tenant/proyek Anda tidak melebihi batas ini, kontrol paginasi tidak akan terlihat -- ini normal, bukan tanda error.

#belum_tersedia[
  *Pengurutan (sort) kolom* belum tersedia di halaman Umpan Sebutan (dan kemungkinan besar juga di halaman daftar lain yang belum diuji terpisah). Tabel selalu terurut tetap berdasarkan waktu terbaru di sisi server, tanpa opsi untuk mengubah urutan dari antarmuka.
]

== Pola simpan-dan-muat-ulang (Post/Redirect/Get)

Ketika Anda mengirimkan sebuah formulir (menambah kata kunci, mengoreksi sentimen, mencatat aksi, dan sebagainya), aplikasi mengarahkan Anda kembali ke halaman yang sama setelah proses selesai (pola Post/Redirect/Get). Ini berarti:

- Pesan sukses/error muncul sekali setelah aksi, lalu hilang saat halaman dimuat ulang secara manual.
- Menekan tombol "kembali" (back) pada peramban setelah submit yang berhasil *tidak* akan memicu pengiriman ulang data secara tidak sengaja.
- Untuk memverifikasi bahwa perubahan Anda benar-benar tersimpan, muat ulang (refresh) halaman dan periksa datanya secara langsung, bukan hanya mengandalkan pesan sukses sesaat.

== Validasi formulir

PANTAU menerapkan validasi berlapis pada sebagian besar formulir: validasi bawaan peramban (kolom bertanda wajib akan mencegah pengiriman formulir kosong) dan validasi di sisi server (pesan error spesifik, mis. "Kata kunci ini sudah ada dalam proyek aktif."). Karena keduanya ada, mengosongkan kolom wajib pada kebanyakan formulir akan dicegah sebelum data terkirim; namun validasi server tetap menjadi lapisan penentu jika validasi peramban dilewati.

== Konfirmasi hasil aksi

Setelah aksi tambah/ubah/hapus, PANTAU menampilkan pesan hasil (flash message) berwarna di bagian atas halaman. Pesan ini hanya tampil sekali pada pemuatan halaman berikutnya setelah aksi -- jika Anda memuat ulang halaman lagi setelahnya, pesan tersebut akan hilang meski perubahan tetap tersimpan.
