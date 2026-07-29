#import "/_shared/style.typ": *

= Pertanyaan yang Sering Diajukan (FAQ)

*T: Mengapa saya (Analis) tidak bisa membuka Umpan Sebutan?*

J: Berdasarkan matriks izin bawaan, halaman Umpan Sebutan hanya diberikan secara bawaan kepada Tenant Admin dan Platform Super Admin. Analis tidak termasuk dalam akses bawaan ini meskipun secara fungsional bertanggung jawab atas koreksi sentimen. Mintalah Tenant Admin/Super Admin di tenant Anda mengaktifkan akses ini lewat Matriks Izin Halaman, atau delegasikan tugas koreksi sentimen kepada Tenant Admin. Lihat Bab 6.3 dan 7.1.

*T: Mengapa halaman Narasi menolak akun saya padahal peran saya seharusnya bisa melihatnya?*

J: Halaman Narasi digerbangi dua lapisan izin: izin halaman biasa (yang mungkin sudah Anda miliki) dan izin "Pemantauan Politik" per-pengguna yang terpisah. Jika Anda belum diberi izin Pemantauan Politik secara eksplisit oleh administrator, Anda akan tetap ditolak walau peran Anda seharusnya bisa mengakses halaman ini. Lihat Bab 7.8.

*T: Saya berperan Peninjau (read-only) tapi tombol "Catat aksi"/"Eskalasi" masih tampak bisa saya klik -- apa yang terjadi jika saya klik?*

J: Saat ini tombol tersebut memang masih dapat digunakan oleh akun Peninjau pada beberapa modul (War Room, Insiden, Deteksi Koordinasi) karena pembatasan aksi tulis belum sepenuhnya terpisah dari izin melihat halaman. Klik tersebut akan benar-benar tersimpan sebagai data (bukan ditolak diam-diam). Sebaiknya hindari menggunakan tombol ini meski aktif, agar linimasa audit tetap mencerminkan tindakan yang benar-benar berwenang. Lihat Bab 10.

*T: Bagaimana cara membatalkan finalisasi Sorotan Eksekutif yang sudah Final?*

J: Saat ini tidak ada jalur resmi di antarmuka untuk mengembalikan brief Final ke Draft atau merevisinya. Status brief bergerak satu arah (draf → final) dan terkunci permanen setelah difinalisasi. Jika ditemukan kesalahan substantif, hubungi administrator platform Anda. Lihat Bab 7.4.

*T: Mengapa chip "Risiko" pada Sorotan Eksekutif kadang menampilkan teks yang aneh?*

J: Ini masalah tampilan yang diketahui pada template halaman brief -- chip terkadang menampilkan representasi data mentah alih-alih label tunggal yang rapi (mis. "Sedang"). Nilai risiko sesungguhnya tetap benar tersimpan dan tidak memengaruhi analisis Anda. Lihat Bab 9 dan 10.

*T: Saya sudah mengatur Matriks Izin Halaman untuk menolak akses suatu peran, tapi peran itu masih bisa masuk. Kenapa?*

J: Untuk lima halaman tertentu (Ringkasan, War Room, Narasi, Regional, Deteksi Koordinasi), penegakan matriks izin belum sepenuhnya berfungsi -- perbaikan sedang berjalan. Untuk halaman lain di luar kelima itu, pengaturan "Tolak" pada matriks sudah bekerja dengan benar. Lihat Bab 7.7 dan Bab 10.

*T: Bagaimana cara mengekspor hanya data yang sudah saya filter di Umpan Sebutan atau Laporan?*

J: Saat ini belum tersedia. Tombol unduh CSV/XLSX pada halaman Laporan selalu mengekspor seluruh data mention tenant Anda, tanpa mengikuti filter platform/sentimen/periode yang sedang aktif. Unduh data lengkap lalu saring secara manual di luar aplikasi. Lihat Bab 8.

*T: Apakah saya bisa mengedit profil saya sendiri (nama, email) dari dalam aplikasi?*

J: Tidak. Halaman Profil (`/profil/`) bersifat murni tampilan (read-only) untuk semua peran -- tidak ada formulir edit di halaman ini. Perubahan data profil perlu dilakukan oleh administrator.

*T: Kenapa halaman Konfigurasi dan Pengawasan masih tampil sebagai tautan aktif di sidebar saya padahal saya (Analis/Peninjau) akan ditolak jika mengkliknya?*

J: Ini keterbatasan tampilan sidebar yang diketahui -- untuk kedua halaman ini, sidebar belum menerapkan pola non-aktif otomatis seperti yang sudah diterapkan pada Umpan Sebutan dan Taksonomi Isu. Server tetap menolak akses dengan benar (403), jadi tidak ada risiko keamanan; hanya berpotensi membingungkan secara tampilan. Lihat Bab 4.

*T: Apakah aman menggunakan PANTAU dari ponsel?*

J: Untuk memantau ringkasan dan War Room, umumnya masih dapat digunakan meski sidebar memakan banyak ruang layar. Untuk pekerjaan entri data yang melibatkan tabel (Taksonomi Isu, Konsol Konfigurasi), sebaiknya gunakan layar tablet ke atas karena beberapa elemen tabel dapat sulit dijangkau pada lebar 390px. Lihat Bab 2.

*T: Mengapa saya menerima pesan error umum "Nama pengguna atau kata sandi salah" -- apakah ini berarti akun saya tidak terdaftar?*

J: Pesan ini sengaja dibuat generik dan identik baik untuk kata sandi yang salah maupun nama pengguna yang tidak terdaftar, sebagai praktik keamanan agar tidak membocorkan informasi keberadaan akun. Periksa kembali ejaan Anda, atau hubungi administrator untuk verifikasi akun.

*T: Saya Tenant Admin dan sudah menambahkan token Apify tenant, tapi trigger koleksi Social Media masih gagal. Kenapa?*

J: Periksa kembali apakah token yang Anda simpan benar-benar valid (tervalidasi ke API Apify saat disimpan). Jika token belum tersimpan/aktif, sistem akan menolak trigger koleksi Social Media dengan pesan yang meminta Anda menyimpan token aktif terlebih dahulu -- ini perilaku yang benar sesuai desain. Lihat Bab 7.7.
