# Landing page articles — design

## Goal
Make the case for media monitoring, and for PANTAU specifically, directly on the public
landing page via a visible "Artikel" section linking to 6 real article pages (Bahasa Indonesia).

## Content
`apps/core/articles.py`: a module-level list `ARTICLES` of dicts, no DB model, no migration.

Fields per article: `slug`, `title`, `excerpt` (1-2 sentences for card + meta description),
`category` (short label e.g. "Reputasi", "Pemerintahan"), `read_minutes` (int), `body`
(list of `("h", text)` / `("p", text)` tuples rendered in order — simple enough to avoid
a markdown dependency).

Topics (final, approved):
1. Kenapa organisasi perlu memantau percakapan publik secara real-time
2. Mendeteksi krisis reputasi sebelum membesar
3. Media monitoring untuk pemerintah: mendengar aspirasi, merancang kebijakan berbasis data
4. Dari data mentah ke keputusan: memahami sentimen & narasi publik
5. Mengenali disinformasi dan aktivitas terkoordinasi (buzzer/bot) di ruang digital
6. Dari mendengar ke bertindak: membangun war room komunikasi krisis yang efektif

Each article body explains the general importance of the topic, then closes with a short
paragraph connecting it to a concrete PANTAU capability (features already listed on the
landing page), so the article both educates and sells.

## Routing
`apps/core/urls.py`: add `path("artikel/<slug:slug>/", views.article_detail, name="artikel_detail")`.

`apps/core/views.py`: add `article_detail(request, slug)` — `@login_not_required`, looks up
the slug in `ARTICLES`, `Http404` if not found, renders `core/artikel_detail.html` with the
article and a `related` list (other 5, capped) in context.

## Templates
- `templates/core/landing.html`: new `<section id="artikel">` inserted between `#solusi` and
  `#cara-kerja`. Section head follows the existing `.section-kicker` + `h2` + intro-paragraph
  pattern. Grid of 6 cards (category tag, title, excerpt, "N menit baca"), each linking to
  `core:artikel_detail`. Add `<a href="#artikel">Artikel</a>` to `.navlinks` for direct nav
  visibility.
- `templates/core/artikel_detail.html`: reuses the same `<head>`/nav/footer/research-banner
  markup as landing.html for visual continuity. Body: category + read time + title, then
  rendered body blocks, then a "Artikel lainnya" list of the other articles, then the existing
  final-cta block (same copy/markup as landing.html's final CTA) so every article ends with an
  onboarding path.

## Styling
Extend `static/core/css/landing.css`:
- `.articles` section + `.article-grid` (3-column, collapsing to 1 column under 800px like
  `.feature-grid`) + `.article-card` styled consistently with `.feature`/`.solution-grid`
  (teal category tag, Archivo heading, muted excerpt).
- `.article-detail` page styles: constrained reading width (~680px), spacing for `h2`/`p`
  blocks, "Artikel lainnya" list styled like small nav links.

## Out of scope
No CMS/admin editing, no pagination, no tags/filtering, no comments, no JS — matches the
existing zero-JS, static-content pattern of the rest of the public site.
