#import "../../_shared/style.typ": *

#let verification_badge(status) = {
  let (bg, fg, label) = if status == "FIXED" {
    (rgb("#eaf5f0"), rgb("#178a5c"), "DIPERBAIKI, terverifikasi ulang")
  } else if status == "STILL_BROKEN" {
    (rgb("#fdeaea"), rgb("#b3001b"), "MASIH TERBUKA")
  } else if status == "DEFERRED" {
    (rgb("#fff4e5"), rgb("#b35900"), "DITANGGUHKAN (disepakati)")
  } else {
    (rgb("#eef2f5"), rgb("#64748b"), "Belum diverifikasi ulang")
  }
  box(fill: bg, inset: (x: 5pt, y: 3pt), radius: 2pt)[
    #text(fill: fg, size: 8.5pt, weight: "bold")[#label]
  ]
}

= Daftar Isu <sec-issues>

Rendering langsung dari `issue-register.csv` (20 baris), dikelompokkan per tingkat keparahan dari yang paling kritis. Kolom "Bukti" merujuk pada berkas tangkapan layar di `testing-report/screenshots/`.

Setiap isu telah melalui *verifikasi ulang* (@sec-reverification) terhadap kode sumber yang telah diperbaiki, dijalankan langsung pada server hidup -- bukan diasumsikan dari catatan commit. Status verifikasi ulang ditampilkan sebagai lencana di bawah setiap isu.

#let issues = read_register("/registers/issue-register.csv")
#let sev_order = ("Critical", "High", "Medium", "Low", "Enhancement")

#for s in sev_order [
  == Tingkat #s
  #let rows = issues.filter(i => i.severity == s)
  #for i in rows [
    === #i.issue_id -- #i.module #h(1fr) #severity_badge(i.severity)

    #verification_badge(i.at("verification_status", default: ""))

    *Peran:* #i.role

    *Diharapkan:* #i.expected

    *Aktual (saat pengujian awal):* #i.actual

    *Dampak:* #i.impact

    *Rekomendasi:* #i.recommendation

    *Kriteria Penerimaan:* #i.acceptance_criteria

    *Bukti (pengujian awal):* #text(size: 8.5pt, style: "italic")[#i.evidence]

    #if i.at("verification_note", default: "") != "" [
      *Hasil verifikasi ulang:* #i.verification_note
    ]

    #v(4pt)
  ]
]
