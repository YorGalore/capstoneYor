#import "../../_shared/style.typ": *

= Hasil Pengujian Alur Kerja

Tabel berikut adalah rendering langsung dari `workflow-matrix.csv` (140 baris), dikelompokkan per modul. Setiap baris merepresentasikan satu alur kerja spesifik dan status keseluruhannya (`overall_status`) setelah dijalankan pada peran yang relevan.

#let wf = read_register("/registers/workflow-matrix.csv")
#let modules_order = wf.map(r => r.module).dedup()

#for m in modules_order [
  == #m
  #table(
    columns: (1fr, auto),
    stroke: 0.5pt + rgb("#cccccc"),
    table.header[*Alur Kerja*][*Status Keseluruhan*],
    ..wf.filter(r => r.module == m).map(r => (
      text(size: 9pt)[#r.workflow],
      status_badge(r.overall_status),
    )).flatten(),
  )
]
