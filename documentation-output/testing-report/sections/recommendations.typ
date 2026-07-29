#import "../../_shared/style.typ": *

= Rekomendasi <sec-recommendations>

Rendering langsung dari `recommendations.csv` (20 baris), diurutkan berdasarkan prioritas. Setiap rekomendasi berbasis satu isu spesifik pada @sec-issues (kolom "Berdasarkan Isu").

#let recs = read_register("/registers/recommendations.csv")
#let prio_order = ("Critical", "High", "Medium", "Low", "Enhancement")

#for p in prio_order [
  == Prioritas #p
  #let rows = recs.filter(r => r.priority == p)
  #table(
    columns: (auto, auto, 1fr),
    stroke: 0.5pt + rgb("#cccccc"),
    table.header[*ID*][*Modul*][*Rekomendasi*],
    ..rows.map(r => (
      text(size: 8.5pt)[#r.rec_id \ (#r.based_on_issue)],
      text(size: 8.5pt)[#r.module],
      text(size: 9pt)[#r.recommendation],
    )).flatten(),
  )
]
