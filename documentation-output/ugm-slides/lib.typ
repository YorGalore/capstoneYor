// =============================================================================
// ugm-slides — Universitas Gadjah Mada presentation theme for Typst
// Brand-matched to the official UGM PowerPoint template, with heading-driven
// authoring and a top section-navigation bar inspired by `diatypst`.
// =============================================================================

// ---- Brand palette ----------------------------------------------------------
#let ugm-navy = rgb("#01416B") // primary
#let ugm-gold = rgb("#FDD402") // accent
#let ugm-lightblue = rgb("#7FA8C9") // secondary motif blue
#let ugm-paleblue = rgb("#C9DCEC") // secondary motif blue (pale)
#let ugm-ink = rgb("#1B2A38") // body text

// ---- Fonts ------------------------------------------------------------------
#let ugm-sans = "Gama-Sans"
#let ugm-serif = "Gama-Serif"

// ---- Decorative lotus-petal motif -------------------------------------------
// A single teardrop/petal, growing upward from its base point (0,0) to (0,-h).
#let _petal(w, h, fill) = curve(
  fill: fill,
  stroke: none,
  curve.move((0pt, 0pt)),
  curve.cubic((w, -h * 0.15), (w * 0.9, -h * 0.85), (0pt, -h)),
  curve.cubic((-w * 0.9, -h * 0.85), (-w, -h * 0.15), (0pt, 0pt)),
  curve.close(),
)

// A cluster of petals fanning out of the bottom-right corner.
#let _petal-cluster(scale: 1.0, opacity: 100%) = {
  let u = 1cm * scale
  box(width: 7 * u, height: 6 * u)[
    #place(
      bottom + right,
      dx: 1.2 * u,
      dy: 1.2 * u,
      rotate(
        -18deg,
        origin: bottom + center,
        _petal(2.6 * u, 6.6 * u, ugm-paleblue.transparentize(100% - opacity)),
      ),
    )
    #place(
      bottom + right,
      dx: 0.8 * u,
      dy: 1.2 * u,
      rotate(
        -48deg,
        origin: bottom + center,
        _petal(2.4 * u, 5.6 * u, ugm-lightblue.transparentize(100% - opacity)),
      ),
    )
    #place(
      bottom + right,
      dx: 1.0 * u,
      dy: 1.1 * u,
      rotate(
        -78deg,
        origin: bottom + center,
        _petal(2.0 * u, 4.4 * u, ugm-navy.transparentize(100% - opacity)),
      ),
    )
    #place(
      bottom + right,
      dx: 1.6 * u,
      dy: 0.4 * u,
      rotate(
        -10deg,
        origin: bottom + center,
        _petal(1.7 * u, 3.4 * u, ugm-gold.transparentize(100% - opacity)),
      ),
    )
  ]
}

// ---- Section navigation bar (the diatypst-inspired part) --------------------
// Renders the list of level-1 sections across the top; the active one (the last
// section whose page <= the current page) is a filled gold pill.
#let _navbar(current-page) = {
  let sections = query(heading.where(level: 1))
  if sections.len() == 0 { return }

  let current = 0
  for (i, s) in sections.enumerate() {
    if s.location().page() <= current-page { current = i + 1 }
  }

  set text(size: 0.62em, font: ugm-sans)
  let items = sections
    .enumerate()
    .map(((i, s)) => {
      let active = (i + 1 == current)
      box(
        inset: (x: 7pt, y: 3pt),
        radius: 4pt,
        fill: if active { ugm-gold } else { none },
        text(
          fill: if active { ugm-navy } else { ugm-navy.lighten(35%) },
          weight: if active { "bold" } else { "regular" },
          [#(i + 1). #s.body],
        ),
      )
    })
  items.join(box(width: 3pt))
}

// ---- Slide title bar --------------------------------------------------------
#let _title-bar(body) = {
  block(width: 100%, above: 6pt, below: 0pt)[
    #grid(
      columns: (auto, 1fr),
      gutter: 9pt,
      align: horizon,
      rect(width: 5pt, height: 1.05em, fill: ugm-gold, stroke: none),
      text(font: ugm-serif, weight: "bold", size: 1.4em, fill: ugm-navy, body),
    )
    #v(3pt)
    #line(length: 100%, stroke: 0.8pt + ugm-navy.lighten(55%))
  ]
}

// =============================================================================
// Main theme
// =============================================================================
#let ugm-theme(
  title: none,
  subtitle: none,
  author: none,
  date: none,
  faculty: none,
  ratio: 16 / 9,
  height: 7.5in, // real PowerPoint 16:9 canvas — keeps 18pt body at a comfortable size

  footer-tagline: "Locally Rooted, Globally Respected",
  url: "ugm.ac.id",
  toc: false,
  show-nav: true,
  body,
) = {
  let width = ratio * height
  let space = 1.55cm

  set document(title: if title != none { title } else { "" }, author: if author != none { author } else { () })
  set text(font: ugm-sans, fill: ugm-ink, size: 20pt, lang: "id")
  show heading: set text(font: ugm-serif, fill: ugm-navy)
  set list(marker: (
    text(fill: ugm-gold)[▪],
    text(fill: ugm-navy)[‣],
    text(fill: ugm-navy.lighten(30%))[–],
  ))
  set enum(numbering: n => text(fill: ugm-navy, weight: "bold")[#n.])

  // strong = navy, emphasized keywords pop on brand
  show strong: set text(fill: ugm-navy)

  // Links underlined in gold
  show link: it => {
    if type(it.dest) == str { underline(stroke: 0.6pt + ugm-gold, it) } else { it }
  }

  // Global content-slide page: gold left rail + subtle petal motif behind,
  // nav bar + slide title in the header, brand footer.
  set page(
    width: width,
    height: height,
    fill: white,
    margin: (left: 0.9 * space, right: 0.7 * space, top: 1.5cm, bottom: 1.6cm),
    background: {
      // gold left rail
      place(left + top, rect(width: 0.16cm, height: 100%, fill: ugm-gold))
      // petal motif, bottom-right, subtle
      place(bottom + right, _petal-cluster(scale: 0.82, opacity: 22%))
    },
    header: none,
    footer: context {
      set text(size: 0.6em, font: ugm-sans, fill: ugm-navy)
      line(length: 100%, stroke: 0.8pt + ugm-navy.lighten(55%))
      v(1pt)
      grid(
        columns: (1fr, auto, 1fr),
        align: (left + horizon, center + horizon, right + horizon),
        text(weight: "bold", url),
        smallcaps(text(tracking: 0.6pt, footer-tagline)),
        [#here().page() / #counter(page).final().first()],
      )
    },
    footer-descent: 0.45cm,
  )

  // ---- Section divider (level-1 headings) -----------------------------------
  show heading.where(level: 1): it => {
    // its own full-bleed navy page
    set page(
      fill: ugm-navy,
      margin: 0cm,
      header: none,
      footer: none,
      background: none,
    )
    counter("ugm-section").step()
    block(width: 100%, height: 100%, inset: (x: 1.5cm, y: 1.3cm))[
      // white emblem + wordmark, top-left
      #grid(
        columns: (auto, auto),
        column-gutter: 10pt,
        align: horizon,
        image("assets/logos/ugm-emblem-white.png", height: 1.2cm),
        text(font: ugm-serif, fill: white, size: 0.72em, weight: "regular")[
          UNIVERSITAS \ GADJAH MADA
        ],
      )
      #v(1.5fr)
      // big section number
      #context {
        let n = counter("ugm-section").get().first()
        text(font: ugm-serif, size: 2.0em, fill: ugm-gold, weight: "bold")[
          #numbering("01", n)
        ]
      }
      #v(-0.1em)
      #text(font: ugm-serif, size: 2.0em, fill: white, weight: "bold", it.body)
      #v(0.35em)
      #rect(width: 3cm, height: 4pt, fill: ugm-gold, stroke: none)
      #v(1fr)
    ]
  }

  // ---- Content slide break (level-2 headings) -------------------------------
  show heading.where(level: 2): it => {
    pagebreak(weak: true)
    // Horizontal section navigation, aligned to the top-right.
    if show-nav { align(right, context _navbar(here().page())) }
    _title-bar(it.body)
    v(0.25cm)
  }
  show heading.where(level: 3): set text(size: 1.05em, fill: ugm-navy)

  // Nice term lists
  show terms.item: it => stack(
    block(width: 100%, inset: 6pt, fill: ugm-navy, radius: (top: 4pt), text(fill: white, weight: "bold", it.term)),
    block(width: 100%, inset: 6pt, fill: ugm-navy.lighten(90%), radius: (bottom: 4pt), it.description),
  )

  // Code
  show raw.where(block: true): it => block(
    width: 100%, inset: 10pt, radius: 5pt, fill: ugm-navy.lighten(93%), it,
  )
  show raw.where(block: false): it => box(
    inset: (x: 2pt), radius: 2pt, fill: ugm-navy.lighten(90%), it,
  )

  // Tables
  set table(stroke: (x, y) => (bottom: 0.6pt + ugm-navy.lighten(40%), top: if y == 0 { 1pt + ugm-navy } else { 0pt }))
  show table.cell.where(y: 0): set text(fill: ugm-navy, weight: "bold")

  // Quotes
  set quote(block: true)
  show quote.where(block: true): it => block(
    width: 100%, inset: 10pt, radius: 3pt, fill: ugm-navy.lighten(92%),
    stroke: (left: 3pt + ugm-gold), it,
  )

  set outline(indent: auto)
  show outline: set heading(level: 2)

  // =========================== TITLE SLIDE ===================================
  if title != none {
    set page(
      fill: white,
      margin: 0cm,
      header: none,
      footer: none,
      background: {
        place(left + top, rect(width: 0.55cm, height: 100%, fill: ugm-gold))
        place(bottom + right, _petal-cluster(scale: 1.15, opacity: 100%))
      },
    )
    block(width: 100%, height: 100%, inset: (left: 1.9cm, right: 1.5cm, top: 1.15cm, bottom: 1.25cm))[
      // top row: faculty (left) + logo (right), no overlap
      #grid(
        columns: (1fr, auto),
        column-gutter: 1cm,
        align: (left + horizon, right + horizon),
        if faculty != none {
          text(font: ugm-sans, size: 0.66em, fill: ugm-navy, weight: "bold", tracking: 1pt, upper(faculty))
        } else [],
        image("assets/logos/ugm-logo-navy.png", height: 1.35cm),
      )
      #v(1fr)
      // ---- title group (vertically centred) ----
      #text(font: ugm-serif, size: 1.9em, fill: ugm-navy, weight: "bold", title)
      #if subtitle != none {
        v(0.25em)
        text(font: ugm-serif, size: 1.0em, fill: ugm-navy.lighten(15%), subtitle)
      }
      #v(0.55em)
      #rect(width: 3.5cm, height: 4pt, fill: ugm-gold, stroke: none)
      #v(1fr)
      // ---- bottom group ----
      #{
        set text(font: ugm-sans, size: 0.72em, fill: ugm-ink)
        if author != none { text(weight: "bold", author) }
        if author != none and date != none [ #h(0.6em) · #h(0.6em) ]
        if date != none { date }
      }
      #v(0.5em)
      #text(font: ugm-sans, size: 0.62em, fill: ugm-navy, weight: "bold")[
        #smallcaps(text(tracking: 1pt, footer-tagline)) #h(0.8em) · #h(0.8em) #url
      ]
    ]
  }

  if toc {
    pagebreak(weak: true)
    heading(level: 2)[Daftar Isi]
    outline(title: none, target: heading.where(level: 1))
  }

  body
}

// =============================================================================
// Helper slides
// =============================================================================

// Full-bleed navy emphasis slide (a quote, a key number, a transition).
#let focus-slide(body) = {
  pagebreak(weak: true)
  set page(fill: ugm-navy, margin: 1.4cm, header: none, footer: none, background: {
    place(bottom + right, _petal-cluster(scale: 0.9, opacity: 30%))
  })
  set text(fill: white, font: ugm-serif)
  show strong: set text(fill: ugm-gold)
  set align(horizon + center)
  block(width: 100%)[
    #text(size: 1.8em, weight: "bold", body)
  ]
}

// Two/three column content convenience: #columns-slide(a, b, ..)
#let columns-slide(..cols) = {
  let items = cols.pos()
  grid(
    columns: items.map(_ => 1fr),
    column-gutter: 1cm,
    ..items,
  )
}
