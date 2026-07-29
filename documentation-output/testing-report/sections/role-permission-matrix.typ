#import "../../_shared/style.typ": *

= Matriks Peran dan Izin Akses <sec-rbac>

Tabel berikut adalah rendering langsung dari `role-permission-matrix.csv` (68 baris), hasil probe langsung terhadap perilaku HTTP nyata setiap kombinasi peran x halaman -- bukan hanya pembacaan konfigurasi. Baris dengan `match = tidak` (akses aktual berbeda dari akses yang diharapkan berdasarkan `default_can_access` murni) ditandai merah; keduanya terjadi pada halaman Narasi dan *bukan* bug matriks peran, melainkan efek gerbang izin terpisah "Pemantauan Politik" (FR-29.1) yang belum diberikan ke akun `qa.analis`/`qa.peninjau`, sehingga sebenarnya sesuai desain.

Perlu dicatat secara terpisah (tidak tertangkap oleh kolom `match` karena keduanya membandingkan terhadap `default_can_access`, bukan terhadap perilaku matriks izin saat sel diubah secara aktif): halaman *ringkasan*, *war_room*, *narasi*, dan *regional* diberi catatan eksplisit pada register "Tidak ada `@require_page` pada view ini" untuk peran Analis dan Peninjau. Ini berarti kolom `actual_access` pada baris-baris tersebut mencerminkan perilaku *default* (yang kebetulan sesuai harapan), bukan bukti bahwa toggle matriks izin benar-benar berfungsi -- pengujian aktif men-deny sel Regional x Peninjau membuktikan toggle tersebut tidak berefek (lihat catatan pada baris terkait dan @sec-gap).

#let perm_matrix = read_register("/registers/role-permission-matrix.csv")
#let pages_order = perm_matrix.map(r => r.page).dedup()

#for p in pages_order [
  == #p
  #table(
    columns: (auto, auto, auto, auto, auto, 1fr),
    stroke: 0.5pt + rgb("#cccccc"),
    table.header[*Peran*][*Diharapkan*][*Aktual*][*Cocok*][*Reserved*][*Catatan*],
    ..perm_matrix.filter(r => r.page == p).map(r => (
      r.role,
      r.expected_access,
      r.actual_access,
      if r.match == "no" {
        text(fill: rgb("#7a0d1a"), weight: "bold")[TIDAK]
      } else [ya],
      if r.reserved == "yes" [ya] else [tidak],
      text(size: 8.5pt)[#r.notes],
    )).flatten(),
  )
]
