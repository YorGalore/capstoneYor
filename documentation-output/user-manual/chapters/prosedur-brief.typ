#import "/_shared/style.typ": *

= Prosedur: Sorotan Eksekutif (Brief)

Sorotan Eksekutif (`/brief/`) adalah ringkasan eksekutif harian yang dihasilkan otomatis oleh sistem berbasis isu-isu terkini, untuk ditinjau dan difinalisasi oleh tim sebelum dibagikan ke pimpinan/juru bicara.

== Membuat draf Sorotan Eksekutif

*Tujuan.* Menghasilkan draf Sorotan Eksekutif untuk tanggal tertentu sebagai titik awal peninjauan.

*Peran yang berlaku.* Tenant Admin, Platform Super Admin.

*Prasyarat.* Anda memiliki akses ke halaman Sorotan Eksekutif.

*Langkah-langkah.*
1. Buka halaman *Sorotan Eksekutif* (`/brief/`).
2. Isi tanggal brief yang ingin dibuat (jika dikosongkan, sistem menggunakan tanggal H-1 secara otomatis).
3. Klik tombol *Buat / perbarui draf*.

#screenshot("/testing-report/screenshots/brief_alur_admin_02_draf-dibuat.png", [Draf Sorotan Eksekutif setelah dibuat, berisi kartu-kartu isu untuk ditinjau.])

*Hasil yang diharapkan.* Draf brief terbentuk dengan daftar kartu isu berstatus "Belum ditinjau".

*Perubahan status.* Brief berada pada status *Draf*.

*Pemecahan masalah.*
- *Tanggal dikosongkan:* sistem menangani ini dengan aman menggunakan tanggal H-1 sebagai bawaan, tidak menimbulkan error.
- *Membuat ulang draf untuk tanggal yang briefnya sudah Final:* ditolak oleh sistem (brief final terkunci permanen) -- lihat bagian "Perjalanan status" di bawah.

== Meninjau, menyunting, dan menyetujui isu

*Tujuan.* Memverifikasi dan bila perlu menyunting teks setiap isu sebelum brief difinalisasi.

*Peran yang berlaku.* Tenant Admin, Platform Super Admin.

*Prasyarat.* Draf brief sudah terbentuk dan berisi isu yang belum ditinjau.

*Langkah-langkah.*
1. Pada draf brief, ubah teks isu pada kolom teks (textarea) bila diperlukan.
2. Klik tombol *Simpan suntingan*.
3. Klik tombol *Setujui isu ini* pada kartu isu setelah ditinjau.
4. Ulangi untuk setiap kartu isu hingga semuanya berstatus "Disetujui".

#screenshot("/testing-report/screenshots/brief_tinjau_admin_05_semua-disetujui.png", [Seluruh isu pada draf brief berstatus Disetujui.])

*Hasil yang diharapkan.* Perubahan teks tersimpan dan tercermin saat halaman dimuat ulang; setiap isu yang disetujui tidak lagi berlabel "Belum ditinjau".

*Perubahan status.* Status masing-masing isu berubah dari "Belum ditinjau" menjadi "Disetujui". Status brief secara keseluruhan tetap *Draf* sampai difinalisasi.

*Pemecahan masalah.*
- Chip label "Risiko" pada tiap kartu isu menampilkan label Indonesia tunggal (mis. "Risiko: Sedang").

== Memfinalisasi brief

*Tujuan.* Mengunci brief menjadi versi final yang siap dibagikan/dicetak, setelah seluruh isu ditinjau.

*Peran yang berlaku.* Tenant Admin, Platform Super Admin.

*Prasyarat.* Seluruh isu pada draf brief sudah berstatus "Disetujui".

*Langkah-langkah.*
1. Pada draf brief yang seluruh isunya sudah disetujui, klik tombol *Finalisasi & kunci brief*.

#screenshot("/testing-report/screenshots/brief_finalisasi_reverifikasi_diperbaiki.png", [Brief berhasil difinalisasi; chip "Final — terkunci" tampil, isu tidak lagi dapat disunting, dan tombol "Buka kembali untuk revisi" tersedia.])

*Hasil yang diharapkan.* Brief berpindah ke status Final: chip "Final — terkunci" tampil, dan formulir edit isu digantikan tampilan baca-saja.

*Perubahan status.* Draf → Final (satu arah, lihat penjelasan di bawah).

*Pemecahan masalah.*
- *Mencoba finalisasi sebelum semua isu ditinjau:* ditolak oleh sistem dengan pesan error; brief tetap berstatus Draf.
- *Mencoba finalisasi dua kali (mis. lewat tombol "kembali" lalu submit ulang):* percobaan kedua tidak menimbulkan efek samping -- brief tetap konsisten pada status Final yang sama.

=== Perjalanan status (state machine)

Status Sorotan Eksekutif bergerak: *pending → generating → draf → final*, dengan satu jalur kembali resmi dari Final ke Draf untuk koreksi darurat (lihat "Membuka kembali brief final" di bawah). Membuat draf baru untuk tanggal yang sama akan ditolak selama brief tanggal tersebut masih berstatus Final.

== Membuka kembali brief final untuk revisi

*Tujuan.* Mengembalikan brief yang sudah Final ke status Draf, untuk kasus koreksi darurat (mis. kutipan regulasi yang keliru ditemukan setelah finalisasi).

*Peran yang berlaku.* Tenant Admin, Platform Super Admin. (Analis tidak dapat melakukan aksi ini meskipun dapat menyunting/menyetujui/memfinalisasi brief -- membuka kembali dokumen resmi yang sudah final dibatasi lebih ketat.)

*Prasyarat.* Brief untuk tanggal terkait berstatus Final.

*Langkah-langkah.*
1. Buka halaman *Sorotan Eksekutif* (`/brief/`) untuk tanggal brief final yang perlu direvisi.
2. Klik tombol *Buka kembali untuk revisi*.
3. Konfirmasi pada dialog konfirmasi peramban yang muncul.

#screenshot("/testing-report/screenshots/ISS-BTX-001_reverifikasi_diperbaiki.png", [Tombol "Buka kembali untuk revisi" pada brief final, dan hasilnya setelah disubmit -- status kembali ke Draf.])

*Hasil yang diharapkan.* Chip status brief berubah dari "Final — terkunci" kembali menjadi "Draf — menunggu tinjauan"; tombol edit/setujui/finalisasi muncul kembali pada setiap kartu isu.

*Perubahan status.* Final → Draf. Aksi ini tercatat pada log audit; `finalized_by`/`finalized_at` brief direset.

*Pemecahan masalah.*
- *Mencoba membuka kembali brief yang belum Final:* ditolak, tidak ada perubahan status.
- Gunakan aksi ini secukupnya -- ini adalah jalur koreksi darurat, bukan alur revisi rutin.

== Melihat dan mencetak versi cetak brief final

*Tujuan.* Memperoleh versi cetak (untuk dicetak atau disimpan sebagai PDF via dialog cetak peramban) dari brief yang sudah final.

*Peran yang berlaku.* Tenant Admin, Platform Super Admin.

*Prasyarat.* Brief untuk tanggal terkait sudah berstatus Final.

*Langkah-langkah.*
1. Buka `/brief/<id>/cetak/` untuk brief final terkait (atau klik tautan "Cetak" dari halaman Laporan, lihat Bab 8).
2. Gunakan fungsi cetak peramban (Ctrl+P / Cmd+P) bila ingin menyimpan sebagai PDF.

#screenshot("/testing-report/screenshots/brief_cetak_admin_07_versi-cetak.png", [Versi cetak Sorotan Eksekutif final.])

*Hasil yang diharapkan.* Halaman versi cetak dimuat tanpa watermark diagonal "DRAF" (watermark ini hanya muncul pada draf, dan sudah benar hilang pada versi final).

*Perubahan status.* Tidak ada; ini murni tampilan baca-saja.

*Pemecahan masalah.*
- Chip label risiko pada versi cetak menampilkan label Indonesia yang sama dengan halaman brief utama (mis. "Risiko: Sedang"), dan teks isu pada brief final tidak lagi memuat kalimat pengingat draf "\[DRAF - DIHASILKAN AI, MENUNGGU TINJAUAN MANUSIA\]" -- kalimat itu dihapus otomatis saat brief difinalisasi. Aman dibagikan ke pihak eksternal tanpa penjelasan tambahan.
