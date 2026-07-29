#import "../_shared/style.typ": *

#set document(title: "Laporan Pengujian Web dan Analisis Kesenjangan - PANTAU", author: "Tim QA PANTAU")
#set text(lang: "id", size: 10.5pt, font: "New Computer Modern")
#set page(numbering: "1", margin: (x: 2.2cm, y: 2.2cm))
#set heading(numbering: "1.1.1")
#set par(justify: true)

#cover(
  "Laporan Pengujian Web dan Analisis Kesenjangan",
  "Platform PANTAU -- Sistem Pemantauan Media Sosial dan Narasi Politik Multi-Tenant",
  "Disusun berdasarkan pengujian fungsional, kontrol akses (RBAC), dan tampilan responsif yang dijalankan langsung terhadap salinan basis data pengembangan berisi data uji Kabupaten Kulon Progo",
  "21 Juli 2026",
)

= Ringkasan Eksekutif

== Statistik Pengujian

Seluruh angka pada bagian ini dihitung langsung dari register CSV sumber (`documentation-output/registers/`), bukan diketik ulang secara manual, sehingga tidak dapat menyimpang dari data mentah.

#let pages = read_register("/registers/page-inventory.csv")
#let perm_matrix = read_register("/registers/role-permission-matrix.csv")
#let workflows = read_register("/registers/workflow-matrix.csv")
#let testcases = read_register("/registers/test-cases.csv")
#let issues = read_register("/registers/issue-register.csv")
#let recs = read_register("/registers/recommendations.csv")

#let count_by(rows, key) = {
  let counts = (:)
  for r in rows {
    let k = r.at(key)
    if k in counts { counts.insert(k, counts.at(k) + 1) } else { counts.insert(k, 1) }
  }
  counts
}

#let tc_status = count_by(testcases, "status")
#let issue_sev = count_by(issues, "severity")
#let perm_mismatch = perm_matrix.filter(r => r.match == "no").len()

#grid(
  columns: (1fr, 1fr, 1fr, 1fr),
  gutter: 8pt,
  block(fill: rgb("#eef3fb"), inset: 10pt, radius: 3pt, width: 100%)[
    #text(size: 20pt, weight: "bold")[#pages.len()] \
    #text(size: 9pt)[Halaman/rute terinventarisasi]
  ],
  block(fill: rgb("#eef3fb"), inset: 10pt, radius: 3pt, width: 100%)[
    #text(size: 20pt, weight: "bold")[4] \
    #text(size: 9pt)[Peran diuji (Super Admin, Tenant Admin, Analis, Peninjau)]
  ],
  block(fill: rgb("#eef3fb"), inset: 10pt, radius: 3pt, width: 100%)[
    #text(size: 20pt, weight: "bold")[#workflows.len()] \
    #text(size: 9pt)[Baris alur kerja diuji lintas peran]
  ],
  block(fill: rgb("#eef3fb"), inset: 10pt, radius: 3pt, width: 100%)[
    #text(size: 20pt, weight: "bold")[#testcases.len()] \
    #text(size: 9pt)[Kasus uji tercatat]
  ],
)

#v(6pt)

=== Ringkasan Status Kasus Uji

#let status_order = ("Complete", "Complete with Friction", "Partially Complete", "Blocked", "Not Available", "Not Testable")
#table(
  columns: (auto, auto, 1fr),
  stroke: 0.5pt + rgb("#cccccc"),
  table.header[*Status*][*Jumlah*][*Keterangan*],
  ..status_order.map(s => (
    status_badge(s),
    str(tc_status.at(s, default: 0)),
    if s == "Complete" [ Berjalan sesuai ekspektasi tanpa catatan. ]
    else if s == "Complete with Friction" [ Berhasil namun disertai catatan gangguan/kejanggalan yang perlu diperbaiki. ]
    else if s == "Partially Complete" [ Sebagian perilaku sesuai ekspektasi, sebagian tidak. ]
    else if s == "Blocked" [ Tidak dapat dijalankan sampai selesai karena hambatan (izin, data, atau desain). ]
    else if s == "Not Available" [ Fitur yang diuji memang tidak tersedia di aplikasi (bukan bug). ]
    else [ Tidak dapat diuji pada kondisi data/sesi yang tersedia. ]
  )).flatten(),
)

=== Ringkasan Isu berdasarkan Tingkat Keparahan

#let sev_order = ("Critical", "High", "Medium", "Low", "Enhancement")
#table(
  columns: (auto, auto, 1fr),
  stroke: 0.5pt + rgb("#cccccc"),
  table.header[*Tingkat*][*Jumlah*][*Modul terdampak*],
  ..sev_order.map(s => (
    severity_badge(s),
    str(issue_sev.at(s, default: 0)),
    issues.filter(i => i.severity == s).map(i => i.module).dedup().join(", "),
  )).flatten(),
)

#v(6pt)
Dari #perm_matrix.len() sel matriks peran x halaman yang diverifikasi langsung terhadap perilaku HTTP nyata (bukan hanya dibaca dari UI), #perm_mismatch sel menunjukkan perbedaan antara akses yang diharapkan berdasarkan desain matriks izin murni dan akses aktual -- keduanya untuk halaman Narasi, dan keduanya *bukan* bug matriks peran melainkan efek gerbang izin terpisah (Pemantauan Politik, FR-29.1) yang belum diberikan ke akun uji terkait. Lihat @sec-rbac untuk rincian penuh.

== Verdict Kelayakan Rilis

#block(fill: rgb("#eaf5f0"), stroke: (left: 3pt + rgb("#178a5c")), inset: 10pt, radius: 2pt, width: 100%)[
  #text(weight: "bold", fill: rgb("#178a5c"))[LAYAK RILIS -- ke-18 dari 20 isu telah diperbaiki dan diverifikasi ulang langsung terhadap kode sumber yang telah diperbaiki (@sec-reverification).]

  Kedua temuan *Critical* yang semula membuktikan bahwa mekanisme kontrol akses inti PANTAU (matriks izin halaman berbasis basis data, FR-1A) dapat dilewati sepenuhnya pada War Room dan modul Koordinasi -- kini terkonfirmasi *diperbaiki*: dekorator `@require_page`/pengecekan peran-tulis yang hilang telah ditambahkan pada seluruh view yang terdampak, dan setiap perbaikan diuji ulang langsung dengan mengulang skenario reproduksi asli terhadap server hidup. Kelima temuan *High* yang memperluas pola kegagalan yang sama juga terkonfirmasi diperbaiki. Dua isu tetap terbuka secara sadar: *ISS-BTX-006* (sidebar belum responsif di mobile, High, di luar cakupan paket perbaikan ini) dan *ISS-BTX-003* (ekspor belum mengikuti filter, Enhancement, sengaja ditangguhkan). Lihat @sec-conclusion untuk penilaian lengkap dan syarat sebelum go-live berikutnya.
]

#include "sections/executive-summary.typ"
#include "sections/system-overview.typ"
#include "sections/scope-environment.typ"
#include "sections/sitemap.typ"
#include "sections/role-permission-matrix.typ"
#include "sections/workflow-results.typ"
#include "sections/functional-findings.typ"
#include "sections/ui-ux-findings.typ"
#include "sections/accessibility-responsive.typ"
#include "sections/gap-analysis.typ"
#include "sections/issue-register.typ"
#include "sections/reverification.typ"
#include "sections/recommendations.typ"
#include "sections/proposed-workflows.typ"
#include "sections/conclusion.typ"
