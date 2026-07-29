// Shared Typst helpers for the PANTAU QA testing report and user manual.
// Mirrors the house style used in docs/documentation.typ (title-page layout,
// heading numbering, monospace-break helper for long identifiers) so the two
// PANTAU documentation deliverables read as one family.

#let zws = "\u{200B}"
#let brk(s) = {
  let out = ""
  let first = true
  for c in s {
    if not first and c == upper(c) and c != lower(c) {
      out += zws
    }
    out += c
    if c == "_" or c == "/" or c == "." {
      out += zws
    }
    first = false
  }
  out
}
#let mcell(s) = raw(brk(s))

#let cover(title, subtitle, tagline, date) = {
  align(center)[
    #v(3cm)
    #text(size: 24pt, weight: "bold")[#title]
    #v(0.3cm)
    #text(size: 18pt)[Platform PANTAU]
    #v(0.1cm)
    #text(size: 13pt, style: "italic")[#subtitle]
    #v(2cm)
    #text(size: 11pt)[#tagline]
    #v(0.2cm)
    #text(size: 11pt)[#date]
  ]
  pagebreak()
  outline(indent: auto)
  pagebreak()
}

// Status badge used throughout the testing report's workflow tables.
#let status_color(s) = {
  if s == "Complete" { rgb("#1b7a3d") }
  else if s == "Complete with Friction" { rgb("#8a6d00") }
  else if s == "Partially Complete" { rgb("#b35900") }
  else if s == "Blocked" { rgb("#b3001b") }
  else if s == "Not Available" { rgb("#6b6b6b") }
  else if s == "Not Testable" { rgb("#6b6b6b") }
  else { rgb("#333333") }
}

#let status_badge(s) = {
  box(fill: status_color(s).lighten(85%), inset: (x: 4pt, y: 2pt), radius: 2pt)[
    #text(fill: status_color(s), size: 8.5pt, weight: "bold")[#s]
  ]
}

#let severity_color(s) = {
  if s == "Critical" { rgb("#7a0d1a") }
  else if s == "High" { rgb("#b3001b") }
  else if s == "Medium" { rgb("#b35900") }
  else if s == "Low" { rgb("#8a6d00") }
  else if s == "Enhancement" { rgb("#0e5c8a") }
  else { rgb("#333333") }
}

#let severity_badge(s) = {
  box(fill: severity_color(s).lighten(85%), inset: (x: 4pt, y: 2pt), radius: 2pt)[
    #text(fill: severity_color(s), size: 8.5pt, weight: "bold")[#s]
  ]
}

// Screenshot figure with a consistent frame, matching docs/documentation.typ's
// `diagram()` helper.
#let screenshot(path, caption) = figure(
  block(
    width: 100%,
    fill: rgb("#f5f5f7"),
    inset: 8pt,
    radius: 3pt,
    align(center, image(path, width: 95%))
  ),
  caption: caption,
  supplement: "Gambar"
)

// "Belum tersedia" callout for user-manual procedures that couldn't be
// verified as working end-to-end during testing.
#let belum_tersedia(text_body) = block(
  fill: rgb("#fff4e5"),
  stroke: (left: 3pt + rgb("#b35900")),
  inset: 10pt,
  radius: 2pt,
  width: 100%,
)[
  #text(weight: "bold", fill: rgb("#b35900"))[Belum tersedia / belum terverifikasi]
  #linebreak()
  #text_body
]

// Read a CSV register and return rows as an array of dictionaries keyed by
// header. Registers live under documentation-output/registers/.
#let read_register(path) = {
  let raw = csv(path)
  let header = raw.at(0)
  raw.slice(1).map(row => {
    let d = (:)
    for (i, key) in header.enumerate() {
      d.insert(key, row.at(i))
    }
    d
  })
}
