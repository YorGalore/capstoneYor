// =============================================================================
// ugm-slides / clean — a second UGM presentation theme for Typst.
// Faithful to "(NEW) Template Presentasi UGM 5.pptx": white canvas, the
// Balairung UGM line-art, gold + navy edge accents, and the template's own
// (smaller) type scale — 30pt titles, 14pt body. Chrome (logo, footer bar,
// building) is baked into authentic backgrounds exported from the PPTX.
//
// This theme is independent of `lib.typ`; import whichever you need.
// =============================================================================

// ---- Brand palette ----------------------------------------------------------
#let ugm-navy = rgb("#01416B")
#let ugm-gold = rgb("#FDD402")

// ---- Fonts ------------------------------------------------------------------
#let ugm-sans = "Gama-Sans"
#let ugm-serif = "Gama-Serif"

// ---- Canvas (13.333in x 7.5in = PowerPoint 16:9 widescreen) ------------------
#let _pw = 13.333in
#let _ph = 7.5in

// Full-bleed background image helper.
#let _bg(name) = place(
  top + left,
  image("assets/backgrounds/" + name, width: 100%, height: 100%),
)

// =============================================================================
// Main theme
// =============================================================================
#let ugm-clean-theme(
  title: none,
  subtitle: none,
  author: none,
  date: none,
  brand-mark: none,
  body,
) = {
  set document(
    title: if title != none { title } else { "" },
    author: if author != none { author } else { () },
  )
  set text(font: ugm-sans, fill: ugm-navy, size: 18pt, lang: "id")

  // Lists / enums in the brand palette.
  set list(marker: (
    text(fill: ugm-gold)[▪],
    text(fill: ugm-navy.lighten(20%))[‣],
    text(fill: ugm-navy.lighten(45%))[–],
  ))
  set enum(numbering: n => text(fill: ugm-navy, weight: "bold")[#n.])
  show strong: set text(fill: ugm-navy, weight: "bold")
  show link: it => if type(it.dest) == str {
    underline(stroke: 0.6pt + ugm-gold, it)
  } else { it }

  // Code, tables, quotes — light, matching the clean aesthetic.
  show raw.where(block: true): it => block(
    width: 100%, inset: 9pt, radius: 4pt, fill: ugm-navy.lighten(94%), it,
  )
  show raw.where(block: false): it => box(
    inset: (x: 2pt), radius: 2pt, fill: ugm-navy.lighten(92%), it,
  )
  set table(stroke: (x, y) => (
    bottom: 0.6pt + ugm-navy.lighten(45%),
    top: if y == 0 { 1pt + ugm-navy } else { 0pt },
  ))
  show table.cell.where(y: 0): set text(fill: ugm-navy, weight: "bold")
  set terms(separator: [: ], hanging-indent: 0pt)

  // -------- Global CONTENT-slide page ---------------------------------------
  // Background = white + logo (top-right) + navy footer bar, all baked in.
  // The slide title is drawn inline (see the level-2 show rule) so the top
  // margin controls its spacing directly.
  set page(
    width: _pw,
    height: _ph,
    fill: white,
    margin: (left: 0.95in, right: 0.95in, top: 0.8in, bottom: 0.95in),
    background: _bg("bg-content.png"),
    header: none,
    footer: none,
  )

  // -------- Section divider (level-1 heading) -------------------------------
  // Clean white canvas (small corner logo + navy footer), with the section
  // number, gold rule, and title as the hero. No competing building line-art.
  show heading.where(level: 1): it => {
    set page(
      background: _bg("bg-content.png"),
      margin: (left: 0.95in, right: 0.95in, top: 0.8in, bottom: 0.95in),
      header: none,
      footer: none,
    )
    counter("ugm-clean-section").step()
    block(width: 100%, height: 100%)[
      #if brand-mark != none { brand-mark }
      #v(1fr)
      #context {
        let n = counter("ugm-clean-section").get().first()
        text(font: ugm-serif, size: 66pt, weight: "bold", fill: ugm-gold, numbering("01", n))
      }
      #v(4pt)
      #rect(width: 2.6cm, height: 5pt, fill: ugm-gold, stroke: none)
      #v(16pt)
      #block(width: 72%, text(size: 40pt, weight: "bold", fill: ugm-navy, it.body))
      #v(1.25fr)
    ]
  }

  // -------- Content slide break (level-2 heading) ---------------------------
  // New content slide, with the title drawn inline at top-left (gold tick +
  // navy). Width is capped so a long title never runs under the baked logo.
  show heading.where(level: 2): it => {
    pagebreak(weak: true)
    block(above: 0pt, below: 16pt, width: 8.6in)[
      #grid(
        columns: (auto, 1fr),
        column-gutter: 10pt,
        align: (horizon + left, horizon + left),
        rect(width: 6pt, height: 1.0em, fill: ugm-gold, stroke: none),
        text(size: 22pt, weight: "bold", fill: ugm-navy, it.body),
      )
    ]
  }
  show heading.where(level: 3): set text(size: 19pt, weight: "bold", fill: ugm-navy)

  set outline(indent: auto)
  show outline: set heading(level: 2)

  // ============================ TITLE SLIDE =================================
  // Overlaid onto bg-title at the PPTX's own anchor points.
  if title != none {
    set page(
      background: _bg("bg-title.png"),
      margin: 0pt,
      header: none,
      footer: none,
    )
    // PANTAU (or other product) brand lockup — sits just above the title so
    // the product identity leads, distinct from the UGM chrome baked into bg.
    if brand-mark != none {
      place(top + left, dx: 55.0% * _pw, dy: 12.0% * _ph, brand-mark)
    }
    // Title block — anchored at 54.9% / 19.1% (matches the PPTX title box).
    place(top + left, dx: 54.9% * _pw, dy: 19.1% * _ph, block(width: 40% * _pw)[
      #set par(leading: 6pt)
      #text(font: ugm-sans, size: 30pt, weight: "bold", fill: ugm-navy, title)
    ])
    // Subtitle — anchored at 55.3% / 59.3% (below the baked gold tick).
    if subtitle != none {
      place(top + left, dx: 55.3% * _pw, dy: 59.3% * _ph, block(width: 30% * _pw)[
        #set par(leading: 5pt)
        #text(font: ugm-sans, size: 14pt, fill: ugm-navy, subtitle)
      ])
    }
    // Optional author · date, just under the subtitle area.
    if author != none or date != none {
      place(top + left, dx: 55.3% * _pw, dy: 79% * _ph, block(width: 40% * _pw)[
        #set text(font: ugm-sans, size: 12pt, fill: ugm-navy)
        #if author != none { strong(author) }
        #if author != none and date != none [ #h(0.5em) · #h(0.5em) ]
        #if date != none { date }
      ])
    }
    pagebreak(weak: true)
  }

  body
}

// =============================================================================
// Helper slides
// =============================================================================

// Quote / closing slide — clean white canvas with a big navy light-italic
// quote as the hero, opened by an oversized gold quotation glyph. An optional
// `mark` (e.g. a product brand lockup) leads at the top-left.
#let quote-slide(body, mark: none) = {
  pagebreak(weak: true)
  set page(
    background: _bg("bg-content.png"),
    margin: (left: 0.95in, right: 0.95in, top: 0.8in, bottom: 0.95in),
    header: none, footer: none,
  )
  show strong: set text(fill: ugm-navy)
  block(width: 100%, height: 100%)[
    #if mark != none { mark }
    #v(1fr)
    #text(font: ugm-serif, size: 78pt, weight: "bold", fill: ugm-gold)[\u{201C}]
    #v(-54pt)
    #block(width: 80%)[
      #set par(leading: 12pt)
      #text(font: ugm-sans, size: 30pt, weight: "light", style: "italic", fill: ugm-navy, body)
    ]
    #v(1.35fr)
  ]
}

// Equal-width multi-column content: #columns-slide(a, b, ..)
#let columns-slide(..cols) = {
  let items = cols.pos()
  grid(columns: items.map(_ => 1fr), column-gutter: 0.9cm, ..items)
}
