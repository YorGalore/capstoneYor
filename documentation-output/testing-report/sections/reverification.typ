#import "../../_shared/style.typ": *

= Verifikasi Ulang Perbaikan <sec-reverification>

Setelah 20 isu pada @sec-issues diperbaiki langsung pada kode sumber (bukan pada salinan basis data uji), setiap perbaikan diverifikasi ulang dengan menjalankan kembali *langkah reproduksi asli yang sama persis* yang menemukan bug tersebut -- terhadap server hidup yang menjalankan kode terbaru, memakai salinan basis data uji baru. Ini bukan pengujian ulang menyeluruh dari awal, melainkan pengujian regresi bertarget: membuktikan bahwa perilaku yang salah pada @sec-issues kini menghasilkan perilaku yang benar, tanpa mengasumsikan perbaikan kode otomatis berarti perbaikan perilaku nyata.

== Ringkasan Hasil

#let issues = read_register("/registers/issue-register.csv")
#let ver_counts = (:)
#for i in issues {
  let s = i.at("verification_status", default: "NOT_RECHECKED")
  ver_counts.insert(s, ver_counts.at(s, default: 0) + 1)
}

#table(
  columns: (auto, auto, 1fr),
  stroke: 0.5pt + rgb("#cccccc"),
  table.header[*Status Verifikasi Ulang*][*Jumlah*][*Keterangan*],
  [DIPERBAIKI], [#str(ver_counts.at("FIXED", default: 0))], [Perilaku yang salah pada pengujian awal kini terkonfirmasi benar, diuji langsung terhadap server hidup.],
  [MASIH TERBUKA], [#str(ver_counts.at("STILL_BROKEN", default: 0))], [Belum termasuk dalam paket perbaikan ini -- perilaku yang salah masih terjadi persis seperti temuan awal.],
  [DITANGGUHKAN], [#str(ver_counts.at("DEFERRED", default: 0))], [Sengaja tidak dikerjakan pada paket ini (disepakati bersama pemilik produk) -- bukan kegagalan perbaikan.],
)

18 dari 20 isu (90%) terkonfirmasi *diperbaiki* dan diverifikasi ulang secara langsung. Rincian per isu ada di @sec-issues (lencana status di setiap entri) dan ringkasan naratif di bawah.

== Catatan Metodologi Penting: Satu False Negative karena Data Uji Basi

Pengujian ulang awal untuk *ISS-FW-001* (akses baca Analis ke Umpan Sebutan) sempat melaporkan "masih rusak" -- `GET /umpan/` sebagai peran Analis tetap mengembalikan 403. Investigasi lebih lanjut menemukan bahwa perbaikan kode *sudah benar* (`apps/core/permissions.py` kini memasukkan `"feed"` ke `DASHBOARD_PAGES`, memberi akses baca-baku ke Analis dan Peninjau), tetapi tabel `PagePermission` pada basis data uji masih menyimpan baris penolakan eksplisit dari sesi pengujian *sebelum* perbaikan diterapkan -- baris eksplisit lama ini menutupi nilai baku kode yang baru, sesuai desain matriks izin itu sendiri (baris eksplisit selalu didahulukan atas `default_can_access`).

Setelah baris basi tersebut dihapus dari basis data uji, `GET /umpan/` sebagai peran Analis dikonfirmasi ulang secara langsung: *200 OK*. Isu ini kini berstatus DIPERBAIKI. Kesalahan ini murni artefak riwayat pengujian pada satu basis data uji tertentu, bukan kegagalan perbaikan kode -- dicatat di sini secara transparan karena inilah persis jenis kesalahan yang dapat menyesatkan sebuah laporan QA jika hasil pengujian pertama diterima begitu saja tanpa investigasi akar masalah.

== Dua Isu yang Belum Selesai (dan Mengapa)

#belum_tersedia[
  *ISS-BTX-006 (Tinggi) -- Sidebar tidak responsif di lebar mobile* tetap terbuka. Diverifikasi ulang pada viewport 390#sym.times 844: sidebar masih menempati kolom tetap 208px tanpa mode hamburger/off-canvas pada `/brief/` maupun `/taksonomi/`, sehingga kolom Konten dan tombol Labeli pada Taksonomi Isu tetap sulit dijangkau. Isu ini *tidak termasuk* dalam ke-20 isu yang dikerjakan pada paket perbaikan ini -- perlu pekerjaan front-end terpisah (pola sidebar off-canvas standar) sebagai tindak lanjut.
]

#belum_tersedia[
  *ISS-BTX-003 (Enhancement) -- Ekspor mention tidak mengikuti filter aktif* tetap seperti semula, sesuai kesepakatan eksplisit sebelum paket perbaikan dimulai. Diverifikasi ulang: tidak ada tombol ekspor sama sekali di halaman Umpan Sebutan; tautan ekspor di Ringkasan/Laporan tetap statis (`?format=csv`/`?format=xlsx`) tanpa parameter filter apa pun, dan `export_mentions` pada `apps/analytics/views.py` dikonfirmasi tidak membaca parameter GET seperti sentimen/platform/penulis. Direkomendasikan sebagai paket kerja terpisah, bukan kegagalan pada paket ini.
]

== Bukti Visual Verifikasi Ulang

Setiap isu yang diverifikasi ulang memiliki satu tangkapan layar baru (nama berkas berpola `<issue_id>_reverifikasi_<hasil>.png`) yang menunjukkan kondisi *setelah* perbaikan, terpisah dari tangkapan layar pengujian awal yang menunjukkan kondisi *sebelum* perbaikan pada @sec-issues. Tiga contoh representatif:

#grid(
  columns: (1fr, 1fr),
  gutter: 10pt,
  screenshot("/testing-report/screenshots/ISS-KOORDINASI-003_reverifikasi_diperbaiki.png", [Akses `/koordinasi/` sebagai Peninjau kini 403 setelah sel matriks izin diatur ke "Tolak" -- dibandingkan dengan temuan awal yang menunjukkan akses tetap berhasil.]),
  screenshot("/testing-report/screenshots/ISS-BTX-001_reverifikasi_diperbaiki.png", [Tombol "Buka kembali untuk revisi" pada brief final kini tersedia dan berfungsi, mengembalikan status ke Draf.]),
)

#grid(
  columns: (1fr, 1fr),
  gutter: 10pt,
  screenshot("/testing-report/screenshots/ISS-BTX-006_reverifikasi_belum-diperbaiki.png", [Sidebar pada viewport 390#sym.times 844 masih menempati kolom tetap -- dikonfirmasi tetap sesuai dugaan, belum termasuk paket perbaikan ini.]),
  screenshot("/testing-report/screenshots/ISS-KONFIGURASI-005_reverifikasi_diperbaiki.png", [Tombol "Hapus" kini tersedia pada baris Aktor Politik Publik, konsisten dengan kartu Kubu/Kata Kunci/Domain/Program.]),
)
