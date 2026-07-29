# Parity Audit — `Analisis 27Juli2026.pdf`

**Reference period:** 21–27 July 2026
**Audit intent:** compare the analytical method and output structure in the reference PDF with PANTAU, then identify the source, actor, topic, keyword, comment, evidence, and PDF-generation capabilities needed to reproduce it inside the platform.

## Executive conclusion

PANTAU now has the application features required to generate the same *class* of report inside the platform:

- inclusive custom date ranges;
- sentiment split by Media Online, Media Sosial, and combined corpus;
- comments analyzed from comment text, not inferred from comment counters;
- actor/organization-specific sentiment;
- dominant issue ranking and source evidence;
- methodology, limitations, quality coverage, and communication recommendations;
- source inventory and configuration gaps;
- candidate keywords derived from actors, programs, and topics;
- server-side downloadable PDF generated from the same calculations as the Laporan UI.

This is capability parity, not automatic historical-data parity. The current Kulon Progo demo corpus does not contain all 21–27 July reference articles or their comment bodies/URLs. A PDF generated before collecting that material will honestly show incomplete source/comment coverage rather than fabricate the reference percentages.

### Live backfill update — 29 July 2026

Historical social collection is now available from the Konfigurasi page and
management command. The bounded 21–27 July run used the deployment `.env`
credential fallback and produced verifiable Instagram/YouTube posts plus 37
Instagram comments from five parent posts inside the report window. X and
Facebook returned no public search results for the bounded queries; TikTok
returned `SEARCH_QUERY_NOT_FOUND`. Those zeroes are source-availability results,
not evidence that discussion did not exist. The project still contains demo
fixtures, so the report now discloses collected-versus-fixture counts and must
not be finalized as a production record until those corpora are separated.

## Gap matrix

| Reference capability | Before this work | Current platform status | Remaining operational dependency |
|---|---|---|---|
| Fixed reporting window | Rolling 7/30/90 days | Implemented: arbitrary inclusive `from`/`to` range | None |
| Online vs social sentiment | Platform volume only | Implemented with explicit platform channel classification | Platforms must be classified correctly |
| Combined sentiment | Basic overall calculation | Implemented and reused by UI/PDF | Sufficient corpus |
| Comment analysis | Comment counters only | Implemented: comment text is a linked first-class mention | Enable per project; valid Apify token; public comments available |
| Actor comparison | Actor tags; one global mention sentiment | Implemented: per mention–actor assessment and manual correction | Actor aliases/handles must be configured |
| Dominant issues | Top free-text themes | Implemented: taxonomy-first issue table, sentiment, chronology, actors, evidence | Taxonomy review coverage |
| Source evidence | URL stored but not synthesized | Implemented: URL/domain inventory, evidence examples, coverage percentage | Crawler must retain canonical URLs |
| Methodology/limitations | Not in periodic report | Implemented in UI and PDF | Analyst review |
| Communication recommendations | Daily-brief fragments | Implemented as measured, basis-labelled report recommendations | Analyst approval |
| Generated PDF | Browser print only | Implemented: real server-side PDF download | `reportlab` dependency installed by deployment |
| Report immutability/version approval | Daily brief only | Not implemented for periodic PDFs | Add snapshot/finalization workflow if PDF becomes an official record |
| Publication date vs event date | One `posted_at` timestamp | Not implemented | Add a separately extracted event date for formal chronology |
| Claim-level contradiction resolution | Not structured | Not implemented | Add claim extraction and source-attributed adjudication |

## Comment-analysis finding

The earlier social collectors stored fields such as `commentCount`, `replyCount`, or `comments`, but those were engagement counters. They did not prove what commenters said. This was not parity with the reference report’s discussion of warganet and parents.

The new comment layer:

1. discovers relevant public posts through the existing keyword collectors;
2. takes a bounded number of high-engagement post URLs;
3. uses dedicated comment actors per supported social platform;
4. stores every returned public comment as a `Mention(content_type="comment")`;
5. links it to its parent post;
6. applies sentiment, topic, actor, and program tagging;
7. reports how many eligible parent posts actually received a comment sample.

Dedicated public comment actors exist for [X/Twitter](https://apify.com/clappi/x-twitter-comments-scraper), [Facebook](https://apify.com/unseenuser/fb-comments), [Instagram](https://apify.com/futurizerush/instagram-comment-scraper), [TikTok](https://apify.com/kawsar/tiktok-comments-scraper), and [YouTube](https://apify.com/scrapesmith/youtube-comment-scraper). These are separate paid/community services; availability, pricing, terms, and output schemas must be rechecked before production procurement.

Comment collection is opt-in per project because it increases cost, retention volume, and privacy risk. Private groups, deleted comments, and access-controlled discussions remain out of scope.

## Source check

### Evidence consistency

The reference PDF combines source claims that are not perfectly consistent:

- [Detik reported 150 symptomatic students](https://www.detik.com/jogja/berita/d-8584008/150-siswa-smpn-3-wates-mual-muntah-diduga-keracunan-mbg/amp).
- [Radar Jogja reported 115 students](https://radarjogja.jawapos.com/amp/kulonprogo/2607210012/lagi-lagi-terjadi-ratusan-siswa-smpn-3-wates-kulon-progo-diduga-keracunan-mbg).
- [IDN Times reported 27 students receiving care](https://jogja.idntimes.com/news/jogja/siswa-di-wates-alami-gejala-keracunan-mbg-c1c2-01-32lq5-8nj7ht/amp).
- [RRI later repeated 115 symptomatic students and 27 referrals](https://rri.co.id/yogyakarta/regional/2600128/dprd-kulon-progo-desak-investasi-menyeluruh-terkait-dugaan-keracunan-smp-3-wates).

These figures can describe different concepts or reporting cutoffs, but a generated report must not collapse them into one unattributed “105–115 victims” statement. PANTAU currently preserves source rows and URLs; claim-level reconciliation remains a future capability.

The positive Sermo Run source also requires date discipline. [ANTARA’s Sermo Run article was published on 22 May 2026](https://jogja.antaranews.com/berita/830421/dispar-kulon-progo-selenggarakan-sermo-run), while the event was scheduled for 19 July. A publication-period report should distinguish an article’s publication timestamp from the event date.

### Source coverage configuration

The Kulon Progo fixture now includes:

- Tribun Jogja;
- Harian Jogja / Espos;
- ANTARA Yogyakarta;
- Proliman News;
- RRI;
- Detik Jogja;
- Kominfo Kulon Progo;
- Kompas Yogyakarta;
- IDN Times Jogja;
- Radar Jogja / JawaPos;
- Bisnis.com;
- Espos.id;
- official Kulon Progo portal.

Configured does not mean collectible. PANTAU honors `robots.txt`, and a source that blocks the crawler must be marked “needs review” or collected through an authorized API/provider. A flat chart from a stale/blocked collector must never be interpreted as calm public opinion.

## Recommended monitoring objects

### Primary report subjects

| Actor/object | Type | High-value aliases |
|---|---|---|
| Pemerintah Kabupaten Kulon Progo | Organization | `Pemkab Kulon Progo`, `Pemerintah Kabupaten Kulon Progo`, `@pemkabkulonprogo` |
| Agung Setyawan | Public official | `Agung Setyawan`, `Bupati Kulon Progo`, `Bupati Agung` |
| Ambar Purwoko | Public official | `Ambar Purwoko`, `Wakil Bupati Kulon Progo`, `Wabup Ambar` |

### Supporting public/organizational actors

- Badan Gizi Nasional / BGN;
- Dinas Kesehatan Kulon Progo / Dinkes Kulon Progo;
- DPRD Kulon Progo / Ketua DPRD Kulon Progo;
- SPPG Karangwuni / dapur MBG Karangwuni;
- KPPG Sleman;
- SMPN 3 Wates;
- Puskesmas Wates;
- Komnas HAM;
- Dinas Pariwisata Kulon Progo;
- SMKN 1 Pengasih;
- SMK Ma’arif 1 Nanggulan.

The platform’s political-actor model permits public officials and organizations, not private citizens. Parents and students may appear as anonymized/ordinary authors in content evidence but must not be registered as tracked political actors.

## Recommended topic taxonomy

| Category | Topic | Core aliases |
|---|---|---|
| Health & food safety | Suspected MBG poisoning at SMPN 3 Wates | `keracunan MBG`, `SMPN 3 Wates`, `SPPG Karangwuni`, `KLB MBG`, `uji laboratorium MBG` |
| Program governance | MBG authority and oversight | `BGN`, `kewenangan pusat`, `Satgas MBG`, `audit SOP dapur` |
| Crisis response | Medical handling and cost coverage | `Puskesmas Wates`, `biaya penanganan`, `klaim BGN`, `Dinkes Kulon Progo` |
| Youth safety | Declaration against student delinquency | `cegah kenakalan pelajar`, `kejahatan jalanan`, `deklarasi pelajar` |
| Tourism & sport | Sermo Run 2026 | `Sermo Run`, `Waduk Sermo`, `sport tourism`, `5K`, `17K` |
| Regional finance | BUKP customer funds | `BUKP`, `dana nasabah BUKP`, `simpanan nasabah` |

## Recommended search queries

Prefer location-qualified phrases over broad national tokens:

- `("MBG" OR "Makan Bergizi Gratis") AND "Kulon Progo"`
- `"keracunan MBG" AND ("Wates" OR "Kulon Progo")`
- `"SMPN 3 Wates"`
- `"SPPG Karangwuni"`
- `("BGN" OR "Badan Gizi Nasional") AND "Kulon Progo"`
- `("Dinkes" OR "Dinas Kesehatan") AND "Kulon Progo"`
- `"DPRD Kulon Progo" AND (MBG OR keracunan)`
- `("Agung Setyawan" OR "Bupati Kulon Progo")`
- `("Ambar Purwoko" OR "Wakil Bupati Kulon Progo")`
- `("Sermo Run" OR "Sermorun") AND "Kulon Progo"`
- `("kenakalan pelajar" OR "kejahatan jalanan") AND "Kulon Progo"`
- `"BUKP" AND "Kulon Progo"`

The current keyword manager stores phrases, not Boolean query trees. The phrase variants above are therefore seeded individually. A Boolean query builder remains a useful future enhancement for precision/recall control.

## Operational acceptance criteria

A generated weekly PDF should not be finalized unless:

- both Media Online and at least one Media Sosial source have healthy collection in the period;
- comment coverage is displayed and is nonzero when the report makes claims about commenters;
- source URL coverage and taxonomy coverage are visible;
- every material factual claim has at least one clickable source;
- actor sentiment for high-impact multi-actor items has been manually reviewed;
- conflicting quantities are source-attributed;
- methodology and limitations remain in the PDF;
- an authorized analyst approves the report.
