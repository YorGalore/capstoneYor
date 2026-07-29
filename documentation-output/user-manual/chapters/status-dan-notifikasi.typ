#import "/_shared/style.typ": *

= Status dan Notifikasi

Bab ini merangkum label status/lencana (badge) yang akan Anda temui di berbagai modul PANTAU, beserta arti dan sumber teksnya sebagaimana teramati langsung dari aplikasi.

== Sorotan Eksekutif (Brief)

- *Draf* -- brief baru dibuat/dihasilkan, isu-isunya masih perlu ditinjau dan disetujui. Watermark diagonal "DRAF" tampil di versi cetak.
- *Final — terkunci* -- seluruh isu telah disetujui dan brief telah difinalisasi. Tidak dapat disunting lagi, dan tidak ada jalur resmi untuk kembali ke Draf (lihat Bab 7.4).
- Pada tingkat isu (bukan brief keseluruhan): *Belum ditinjau* → *Disetujui* setelah Anda mengklik "Setujui isu ini".
- Chip *Risiko* pada kartu isu idealnya menampilkan satu label ("Risiko: Rendah/Sedang/Tinggi"); pada pengujian, chip ini kadang menampilkan teks mentah yang tidak rapi -- lihat Bab 7.4 dan Bab 10 untuk detail.

== Insiden

- Ringkasan jumlah pada papan Insiden ditampilkan per kategori: *Terkonfirmasi*, *Kandidat*, *Kritis*, *Terbuka*.
- Status detail insiden ditampilkan sebagai gabungan tiga informasi dipisah tanda "·", contoh: *"Kritis · Ditangani · Kulon Progo"* (tingkat keparahan · status penanganan · wilayah/OPD terkait). Status penanganan yang teramati pada pengujian termasuk *Ditangani* dan *Selesai*.

== Deteksi Perilaku Tidak Otentik Terkoordinasi (Koordinasi)

- *Ditandai* -- status awal klaster yang terdeteksi, menunggu tinjauan.
- *Ditinjau — Organik* -- klaster telah ditinjau dan dinyatakan bukan aktivitas tidak otentik (false positive).
- Eskalasi ke tinjauan analis senior *tidak* mengubah badge status yang tampil di halaman (tetap "Ditandai") -- lihat catatan pada Bab 7.6.

== Konsol Konfigurasi

- Status Platform Terpantau: *● Aktif* / *● Nonaktif*.
- Status domain pantauan: *Aktif* / *Perlu tinjauan*, diperbarui setelah "Uji koneksi" dijalankan.
- Status kartu Koleksi Data (kill switch): *berjalan* / *dihentikan*.
- Status kartu Trigger Koleksi Manual (live, via polling): *Siap* → *Dalam antrean* atau *Diproses* → *selesai* atau *Gagal*.
- Status Kredensial Apify: "Belum ada token aktif untuk tenant ini" ketika belum ada token tersimpan/valid.

== Umpan Sebutan

- Label sentimen: *Positif* / *Negatif* / *Netral* -- dapat dikoreksi manual oleh Tenant Admin/Super Admin (lihat Bab 7.1).
- Kondisi kosong pencarian: "Belum ada mention yang cocok."

== Kontrol akses (403 Forbidden)

Ketika Anda mencoba mengakses sebuah halaman atau menjalankan aksi yang tidak diizinkan untuk peran Anda, PANTAU menampilkan halaman error "403 Forbidden" standar. Ini adalah perilaku yang benar dan disengaja, bukan tanda aplikasi rusak -- lihat Bab 6 (Panduan per Peran) untuk mengetahui halaman mana yang seharusnya dapat Anda akses.

Pesan login yang gagal juga bersifat generik dengan sengaja: "Nama pengguna atau kata sandi salah." ditampilkan baik untuk kata sandi yang salah maupun nama pengguna yang tidak terdaftar, agar tidak membocorkan keberadaan sebuah akun kepada pihak yang tidak berwenang.
