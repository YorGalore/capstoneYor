#import "../../_shared/style.typ": *

= Analisis Kesenjangan <sec-gap>

Bagian ini mengelompokkan 20 isu pada `issue-register.csv` menjadi kategori kesenjangan yang berulang, agar pola sistemik terlihat jelas -- bukan hanya daftar bug satu-per-satu.

== Kategori 1: Kesenjangan Kontrol Akses (Access-Control Gap) -- Kategori Paling Menonjol

Ini adalah kategori paling serius dan paling sering muncul pada laporan ini: fungsi *penegakan* izin di sisi server tidak konsisten dengan *janji* yang ditampilkan UI matriks izin. Enam dari dua puluh isu (dua Critical, tiga High, termasuk RBAC-ISSUE-001 yang mencakup empat halaman sekaligus) berasal dari akar penyebab yang sama: view Django yang lupa dibungkus `@require_page`.

- *ISS-KOORDINASI-003* (Critical) -- `/koordinasi/` tidak digerbang sama sekali; "Tolak" di matriks izin tidak berefek.
- *ISS-FW-002* (Critical) -- `log_response` War Room tidak memiliki pengecekan peran; Peninjau dapat menulis ke audit trail resmi.
- *RBAC-ISSUE-001* (High) -- Ringkasan, War Room, Narasi, Regional tidak digerbang; toggle matriks izin untuk keempatnya adalah tampilan kosong (false sense of security).
- *ISS-KOORDINASI-002* (High) -- Aksi eskalasi klaster dan tandai-organik dapat dieksekusi peran mana pun yang login, termasuk Peninjau.
- *ISS-FW-003* (High) -- Penambahan catatan pada lini masa Insiden lolos untuk Peninjau karena `insiden` termasuk `DASHBOARD_PAGES` default-viewer, sehingga gerbang baca tidak cukup untuk membedakan dari gerbang tulis.
- *ISS-BTX-002* (High) -- `POST /brief/buat/` oleh Peninjau berhasil membuat draf brief walau UI tidak pernah mengekspos aksi itu ke peran tersebut.

Akar masalah bersama pada seluruh enam isu ini: *`@require_page` mengontrol akses baca ke sebuah halaman, tetapi tidak semua endpoint aksi tulis terkait halaman itu ikut digerbang oleh pemeriksaan yang sama atau lebih ketat.* Pada beberapa kasus (Koordinasi, War Room, Ringkasan/Narasi/Regional), decorator-nya bahkan tidak ada sama sekali.

== Kategori 2: Aksi yang Hilang (Missing Actions)

Beberapa entitas mendukung sebagian siklus hidup CRUD tetapi bukan siklus penuh, tidak konsisten dengan entitas serupa di modul yang sama:

- *ISS-KONFIGURASI-005* (Medium) -- Aktor Politik hanya bisa toggle aktif/nonaktif, tidak bisa dihapus permanen, berbeda dari Kubu/Kata Kunci/Domain/Program yang semuanya memiliki aksi hapus.
- *DEVOPS-003* (dicatat pada test-cases, bukan isu register formal) -- Runtime Settings tidak memiliki endpoint hapus, meninggalkan residu data uji permanen.

== Kategori 3: Transisi Status yang Tidak Lengkap

- *ISS-BTX-001* (Medium) -- Brief yang sudah Final terkunci permanen; tidak ada jalur "batalkan finalisasi"/revisi untuk koreksi darurat (mis. kutipan regulasi keliru).
- *ISS-KOORDINASI-001* (Medium) -- Eskalasi klaster koordinasi mencatat audit log tapi tidak mengubah status yang terlihat di UI mana pun pada modul itu -- klaster tetap tampil "Ditandai" seolah belum dieskalasi.

== Kategori 4: Jalan Buntu (Dead Ends) bagi Operator

- *ONB-ISSUE-003* (Medium) -- Peran aplikasi "Platform Super Admin" tidak dipetakan ke `is_staff`/izin model Django, sehingga tidak ada operator dengan jalur UI resmi untuk memverifikasi `OnboardingRequest` tanpa akses shell/database langsung -- termasuk menghambat pengujian QA itu sendiri (dicatat sebagai Blocked pada ONB-006).

== Kategori 5: Validasi dan Deduplikasi yang Longgar

- *ISS-KONFIGURASI-004* (Low) -- form domain tidak memvalidasi format (spasi, tanpa TLD lolos tersimpan).
- *ONB-ISSUE-002* (Low) -- submission onboarding duplikat (email + organisasi identik) tidak terdeteksi.

== Kategori 6: Kebocoran Detail Implementasi ke UI

- *ISS-BTX-004* dan *ISS-BTX-005* -- representasi dict Python mentah pada chip risiko brief (draf, final, dan versi cetak).
- *AUTH-ISSUE-001* -- label peran di sidebar berasal dari field jabatan bebas teks, bukan peran RBAC teknis.

== Kategori 7: Inkonsistensi Navigasi

- *UX-ISSUE-001* (Medium) -- tautan "Konfigurasi"/"Pengawasan" tetap aktif di sidebar untuk peran yang akan ditolak, berbeda dari pola yang benar sudah diterapkan pada "Umpan Sebutan"/"Taksonomi Isu".

#v(6pt)
Distribusi tujuh kategori di atas menunjukkan bahwa kesenjangan paling berdampak pada PANTAU bukan pada logika bisnis inti (yang sebagian besar solid, lihat @sec-functional) melainkan pada *lapisan penegakan otorisasi yang tidak diterapkan seragam di seluruh view* -- pola yang sama berulang pada lima halaman berbeda.
