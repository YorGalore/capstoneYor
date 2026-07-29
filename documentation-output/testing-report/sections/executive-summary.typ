#import "../../_shared/style.typ": *

== Lingkup dan Tujuan Pengujian

Pengujian ini dilakukan terhadap seluruh 24 halaman/rute yang teridentifikasi pada PANTAU, mencakup empat modul aplikasi (Analitik, Koordinasi, Tata Kelola/Governance, dan halaman publik/onboarding), dijalankan bergantian dengan empat akun uji yang mewakili keempat peran RBAC aplikasi: Platform Super Admin, Tenant Admin, Analis, dan Peninjau. Untuk setiap halaman dan alur kerja, pengujian memverifikasi tiga hal sekaligus: (1) apakah fungsi inti bekerja sesuai deskripsi produk, (2) apakah kontrol akses berbasis peran benar-benar ditegakkan di sisi server (bukan hanya disembunyikan di UI), dan (3) apakah tampilan tetap dapat digunakan pada tiga lebar layar (1440x900 desktop, 834x1112 tablet, 390x844 mobile).

== Temuan Kritis yang Perlu Perhatian Segera <sec-exec-summary>

#block(fill: rgb("#eaf5f0"), stroke: (left: 3pt + rgb("#178a5c")), inset: 8pt, radius: 2pt, width: 100%)[
  #text(size: 9pt)[*Status terkini:* seluruh temuan pada bagian ini (ISS-FW-002, ISS-KOORDINASI-003, RBAC-ISSUE-001, ISS-BTX-002) telah *diperbaiki dan diverifikasi ulang* terhadap kode sumber terbaru -- lihat @sec-reverification. Narasi di bawah menggambarkan kondisi *saat ditemukan pertama kali*, dipertahankan apa adanya sebagai catatan pengujian asli.]
]

Dua temuan berikut membuktikan bahwa mekanisme kontrol akses inti PANTAU -- matriks izin halaman berbasis basis data yang secara eksplisit dijual sebagai fitur keamanan (FR-1A) -- dapat dilewati sepenuhnya pada dua modul yang menyimpan jejak audit resmi institusi.

+ *War Room mencatat aksi tanpa pengecekan izin apa pun (ISS-FW-002, Critical).* Endpoint `POST /war-room/<issue_id>/aksi/` (fungsi `log_response`) hanya didekorasi `@require_POST`, tanpa `@require_page` maupun pengecekan peran. Akun uji peran Peninjau (`qa.peninjau`) berhasil menulis entri baru ke linimasa respons War Room -- linimasa yang menurut FR-28.2 adalah catatan auditable resmi atas respons institusi terhadap krisis narasi. Bukti: `warroom_probe-otorisasi_peninjau_02_setelah-submit.png`.
+ *Matriks izin "Tolak" untuk Deteksi Koordinasi tidak berefek sama sekali (ISS-KOORDINASI-003, Critical).* View `koordinasi` di `apps/coordination/views.py` tidak dibungkus `@require_page('koordinasi')`, berbeda dari seluruh view `apps/governance/views.py` yang konsisten memakainya. Diuji langsung: sel matriks Deteksi Koordinasi x Peninjau diubah menjadi "Tolak" di `/konfigurasi/izin/`, disimpan, dan diverifikasi persisten -- namun akun `qa.peninjau` tetap berhasil memuat `/koordinasi/` dengan status 200. Bukti: `izin_uji-celah-decorator_dewi-anjani_01_deny-set.png` dan `koordinasi_matriks-izin-efek_qa-peninjau_08_akses-setelah-tolak.png`.

Pola kegagalan yang sama meluas ke tingkat *High*: view `ringkasan`, `war_room`, `narasi`, dan `regional` di `apps/analytics/views.py` juga tidak memiliki `@require_page`, sehingga menoggle sel-sel ini di editor matriks izin -- yang secara eksplisit dijelaskan UI sebagai "sel terkunci dilindungi kebijakan" -- tidak berefek apa pun pada empat halaman analitik tersebut (RBAC-ISSUE-001, dibuktikan langsung dengan mendenda Regional x Peninjau lalu tetap memuat `/regional/` dengan status 200). Ini adalah rasa aman yang keliru (false sense of security) pada fitur yang namanya sendiri menjanjikan kontrol akses. Selain itu, peran Peninjau dapat membuat draf Daily Brief melalui `POST /brief/buat/` langsung meskipun UI tidak pernah menampilkan aksi tersebut ke peran itu (ISS-BTX-002, High).

Rincian penuh, evidence, dampak, dan rekomendasi setiap temuan ada pada @sec-issues dan @sec-recommendations.

== Yang Berjalan Baik

Di luar celah RBAC di atas, cakupan fungsional PANTAU cukup solid: dari #box[154] kasus uji, *126 berstatus Complete* dan *18 Complete with Friction* (berhasil namun dengan catatan kecil) -- lebih dari 93% alur kerja yang diuji berfungsi sesuai ekspektasi. Modul Konsol Konfigurasi (36 kasus uji: kata kunci, domain, kubu, aktor, program, aturan peringatan, penjadwalan) berjalan mulus termasuk validasi negatif (field kosong, duplikat, nilai di luar rentang). Alur Daily Brief (draft -> tinjau -> setujui -> finalisasi -> cetak), Taksonomi Isu (label, gabung isu, unmerge), dan Insiden (catat, ubah status) semuanya berhasil end-to-end untuk peran yang berwenang. Otorisasi berbasis matriks izin bekerja benar untuk 13 dari 16 halaman yang terdaftar di registry (Umpan Sebutan, Taksonomi, Laporan, Sosiograf, Ekspor, Sorotan, Insiden, Konfigurasi, Pengawasan, Matriks Izin, Dev-Ops -- seluruhnya menegakkan 403 Forbidden dengan benar saat peran ditolak).
