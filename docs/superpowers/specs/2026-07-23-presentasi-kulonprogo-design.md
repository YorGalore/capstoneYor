# Presentasi Kulonprogo — "Satu Pekan di Kulon Progo" — Design

**Date:** 2026-07-23
**Status:** Approved in conversation
**Deliverable:** UGM-branded Typst slide deck pitching PANTAU to Pemkab Kulon Progo

## Goal

A ~16-slide, ~20-minute, Bahasa Indonesia deck for pimpinan daerah (Bupati / Sekda /
Kepala OPD level) that tells one continuous story on real seeded data, ends with a
pilot-program ask, and can be followed by a live demo of the same data.

## Decisions (locked)

| Decision | Choice |
|----------|--------|
| Story frame | "Satu Pekan di Kulon Progo" — day-by-day journey of the Jalan Wates–Sentolo complaint surge |
| Audience / length | Pimpinan daerah, ~20 min, ~16 slides, benefit-led, no architecture diagrams |
| Theme | `ugm-clean-theme` (official "Template Presentasi UGM 5" look) from `documentation-output/ugm-slides.zip` |
| Visuals | Real screenshots captured from the locally running app with the seeded Kulon Progo demo tenant |
| Closing | Pilot ajakan: 3 bulan, 2 OPD, UGM mendampingi |
| Presenter | Dr.techn. Guntur Budi Herwanto, M.Cs. — DIKE FMIPA UGM |
| Language | Bahasa Indonesia |

## Story spine

The deck answers the three leadership questions (from the incident-model spec):
*Apa yang terjadi? Seberapa serius? Apa yang harus dilakukan?*

| # | Slide | Content |
|---|-------|---------|
| 1 | Judul | PANTAU — Sistem Pemantauan Aspirasi Publik & Media Sosial |
| 2 | Pembuka | Warga sudah bicara setiap hari — di media sosial, bukan di kotak saran |
| 3 | Tiga pertanyaan pimpinan | Apa yang terjadi / seberapa serius / apa yang harus dilakukan |
| 4 | Perkenalan PANTAU | Alur: Kumpulkan → Pahami → Prioritaskan → Tindak lanjuti |
| 5 | Setup cerita | Timeline Senin→Jumat |
| 6 | Senin–Selasa | Keluhan warga soal Jalan Wates–Sentolo (screenshot Umpan) |
| 7 | Rabu pagi | Insiden Kritis terdeteksi: 22 sebutan, 86% negatif (screenshot papan Insiden) |
| 8 | Detail insiden | Ringkasan/akar masalah/dampak/rekomendasi, berlabel DRAF (screenshot detail) |
| 9 | Rabu siang | Ditugaskan ke OPD PU; timeline audit |
| 10 | Kamis pagi | Bupati membaca Brief Harian (screenshot Brief) |
| 11 | Bukan hanya satu isu | Air PDAM (Tinggi), Sampah Pasar (Sedang) — papan prioritas |
| 12 | Perlindungan ekstra | Deteksi akun terkoordinasi (CIB) |
| 13 | Prinsip kepercayaan | Human-in-the-loop, netral, dapat diaudit |
| 14 | Mulai dari mana | Operator Kominfo, daftar OPD, sumber data |
| 15 | Ajakan pilot | 3 bulan, 2 OPD, UGM mendampingi |
| 16 | Terima kasih | Kontak |

## Data grounding

All numbers on slides come from `apps/core/demo_kulon_progo.py` seed:

- **Jalan Rusak Wates–Sentolo** — 22 mentions, 86% negative → severity **Kritis**
- **Air PDAM Mati Berhari-hari** — 9 mentions, 78% negative → **Tinggi**
- **Sampah Menumpuk di Pasar** — 7 mentions, 57% negative → **Sedang**
- OPD list, Kapanewon-level news items, coordination clusters as seeded

Seed is re-run fresh before screenshotting so relative dates read as the current week
(presentation date 23 Juli 2026).

## Build steps

1. **Data + screenshots**
   - `python manage.py migrate && python manage.py seed_demo_data` (fresh relative dates)
   - `python manage.py runserver`, log in as the demo user
   - Playwright script (scratchpad) captures: Umpan (filtered to jalan complaints),
     papan Insiden, detail Insiden Jalan Wates–Sentolo, Brief Harian, Sosiograf/CIB
   - Screenshots saved to `documentation-output/presentasi-kulonprogo/figs/`
2. **Deck**
   - Working dir `documentation-output/presentasi-kulonprogo/` reusing the extracted
     `../ugm-slides/` theme (`clean.typ`, assets) — no copy of fonts/logos
   - `presentasi-kulonprogo.typ` written per the story spine
   - Compile: `typst compile --font-path ../ugm-slides/assets/fonts presentasi-kulonprogo.typ`
3. **Verify**
   - PDF compiles without warnings that matter; screenshots legible at slide scale;
     every claim on a slide matches the seeded data

## Out of scope

- No changes to application code
- No architecture/deployment slides (leadership audience)
- No English version
