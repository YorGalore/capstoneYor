#import "/_shared/style.typ": *

= Pemecahan Masalah

Bab ini mengumpulkan gejala umum yang mungkin Anda temui saat memakai PANTAU, disusun berdasarkan gejala, beserta penjelasan dan langkah yang disarankan. Semua gejala di sini teramati langsung selama pengujian aplikasi.

== "Saya tidak bisa membuka halaman tertentu (403 Forbidden)"

Ini hampir selalu berarti peran Anda memang tidak diberi akses ke halaman tersebut, dan sistem bekerja dengan benar menolaknya. Periksa Bab 6 (Panduan per Peran) untuk memastikan halaman tersebut memang seharusnya dapat Anda akses. Kasus yang sering membingungkan:

- *Umpan Sebutan* untuk peran Analis -- tidak termasuk akses bawaan Analis; hanya Tenant Admin/Super Admin. Lihat Bab 7.1.
- *Narasi (Perbandingan Narasi)* untuk Analis/Peninjau -- memerlukan izin tambahan "Pemantauan Politik" yang terpisah dari izin halaman biasa. Lihat Bab 7.8.
- *Konfigurasi* dan *Pengawasan* untuk Analis/Peninjau -- tautannya masih tampil aktif di sidebar meskipun peran Anda akan ditolak jika mengkliknya; ini keterbatasan tampilan sidebar yang diketahui, bukan indikasi Anda seharusnya memiliki akses. Lihat Bab 4.
- Jika Anda seorang administrator dan sudah mengatur Matriks Izin Halaman untuk mencabut akses suatu peran tapi peran itu ternyata masih bisa masuk -- lihat gejala berikutnya.

== "Saya mengatur Matriks Izin Halaman ke 'Tolak' tapi peran itu masih bisa mengakses halamannya"

Ini dikonfirmasi terjadi pada lima halaman: *Ringkasan*, *War Room*, *Perbandingan Narasi*, *Regional*, dan *Deteksi Perilaku Tidak Otentik Terkoordinasi*. Penegakan matriks izin untuk kelima halaman ini belum sepenuhnya berfungsi -- perbaikan sedang berjalan. Untuk halaman lain di matriks (Umpan Sebutan, Sosiograf, Laporan, Ekspor Data, Sorotan Eksekutif, Taksonomi Isu, Insiden, Konsol Konfigurasi, Dasbor Pengawasan, Matriks Izin Halaman, Pengaturan Dev/Ops), pengaturan "Tolak" bekerja dengan benar. Lihat Bab 7.7.

== "Peran Peninjau (read-only) saya ternyata bisa mengirim/mengubah data"

Diketahui terjadi pada tiga aksi: mencatat aksi respons War Room, menambah catatan pada Insiden, dan mengeskalasi/menandai organik klaster Deteksi Koordinasi. Tombol-tombol ini secara teknis masih dapat digunakan oleh akun Peninjau meski seharusnya hanya-baca. Bila Anda berperan Peninjau, hindari menggunakan tombol aksi tulis ini meski tampak aktif, demi menjaga integritas linimasa audit. Lihat Bab 7.2, 7.3, dan 7.6.

== "Data yang saya kirim melalui formulir tampak tidak tersimpan"

- Pesan sukses kadang tidak selalu tampak jelas di layar meskipun data sesungguhnya tersimpan (teramati pada Log Aksi Respons War Room). *Selalu muat ulang halaman* dan periksa langsung datanya, jangan hanya mengandalkan pesan sukses sesaat.
- Pada Taksonomi Isu, antrean tinjauan manual dibatasi menampilkan 25 baris teratas -- jumlah baris yang tampak sama setelah Anda melabeli satu konten *bukan* berarti label gagal tersimpan; baris lain otomatis mengisi slot yang kosong.
- Pesan hasil aksi (flash message) hanya tampil satu kali pada pemuatan halaman berikutnya setelah aksi, lalu hilang saat Anda memuat ulang lagi. Ini normal.

== "Tampilan berantakan/terpotong di ponsel"

Sidebar navigasi belum menyusut secara otomatis pada lebar layar ponsel (390px) di halaman-halaman dasbor, sehingga menyisakan ruang sempit untuk konten utama. Dampak paling terasa pada *Taksonomi Isu* (kolom Konten dan tombol Labeli bisa tidak terlihat) dan *Sorotan Eksekutif* (teks isu terpotong-potong). Untuk pekerjaan yang melibatkan tabel data, gunakan layar tablet (834px) ke atas atau desktop. Lihat Bab 2.

== "Chip risiko atau teks pada Sorotan Eksekutif tampak aneh/tidak rapi"

Diketahui: chip label "Risiko" pada kartu isu brief kadang menampilkan teks mentah alih-alih label tunggal yang rapi, baik pada draf maupun versi cetak (kadang muncul sebagai kode bahasa Inggris seperti "RISIKO: MEDIUM" pada versi cetak). Selain itu, teks isu pada brief final yang dicetak dapat masih memuat kalimat pengingat draf yang sedianya sudah tidak relevan setelah brief dikunci. Nilai data yang sesungguhnya (risiko, isi isu) tetap benar tersimpan -- ini murni masalah tampilan. Lihat Bab 7.4.

== "Saya (Super Admin) tidak bisa memverifikasi data melalui Django Admin (/admin/)"

Peran "Platform Super Admin" pada aplikasi PANTAU tidak otomatis memberi izin staf Django (`is_staff`/model permissions). Login ke `/admin/` mungkin berhasil secara autentikasi, tetapi Anda dapat menerima pesan "Anda tidak memiliki izin untuk melihat atau mengedit apa pun" atau 403 saat membuka model tertentu (mis. `OnboardingRequest`). Gunakan halaman PANTAU yang relevan (mis. Dasbor Pengawasan) untuk verifikasi operasional, atau hubungi administrator platform untuk akses Django Admin yang tepat bila benar-benar diperlukan.

== "Domain/kata kunci/kubu yang saya tambahkan sepertinya tidak divalidasi formatnya"

Untuk kartu *Situs & Domain Pantauan*, sistem saat ini hanya memvalidasi keunikan domain dalam proyek, *bukan* format domain (nilai yang mengandung spasi atau tanpa titik dapat tersimpan tanpa penolakan). Periksa ejaan domain secara manual sebelum menyimpan. Untuk kartu lain (Kata Kunci, Aturan Peringatan, Kubu, Aktor Politik, Program), validasi field wajib dan duplikat sudah berfungsi dengan baik.

== "Saya tidak bisa menghapus entri Aktor Politik yang salah"

Kartu Aktor Politik Publik hanya menyediakan toggle Aktif/Nonaktif, tanpa tombol hapus permanen (berbeda dari kartu Kubu/Kata Kunci/Domain/Program yang semuanya memiliki aksi hapus). Nonaktifkan entri yang salah sebagai solusi sementara; entri akan tetap ada dalam daftar (berstatus nonaktif). Lihat Bab 7.7.
