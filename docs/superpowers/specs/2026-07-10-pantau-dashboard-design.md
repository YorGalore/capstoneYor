# PANTAU Dashboard — Design Spec

Date: 2026-07-10
Source design: Claude Design project "Government political narrative platform",
file `PANTAU Dashboard.dc.html` (7 screens, turn `t1`).
Source spec: `SRS_Government_Political_Narrative_Platform_v3_microservices.pdf/docx` (local, project root).

## Summary

PANTAU (Pusat Analitik Narasi & Opini Publik) is a multi-tenant government
communications dashboard for monitoring public sentiment and political
narrative online. This spec covers implementing the 7 key screens from the
design doc as a real Django application with seeded fixture data — not a
static mockup and not wired to live ingestion.

All content in the app is in Indonesian (Bahasa Indonesia), matching the
design doc. All monitored data (mentions, coalitions, programs) is fictional;
provinces/regencies are real. The design doc's own neutrality banners
(FR-29.5) and audit-logging language must be preserved verbatim where they
appear in the UI.

## Screens in scope

1. **Ringkasan** (`/ringkasan/`) — main dashboard: KPI cards (total mentions,
   interactions, unique authors), digital health index gauge, sentiment
   composition bar, mentions timeline (daily/hourly/monthly toggle — daily
   wired first), source breakdown by platform, Plutchik emotion bars, recent
   alerts panel.
2. **War Room Narasi** (`/war-room/`) — dark "control room" mode for an
   active political issue: live KPI strip (mentions/hour, negative ratio,
   cumulative reach, coordinated cluster count), realtime volume chart
   (negative/positive/neutral overlay), top spreader accounts table,
   geographic hotspots, neutrality/audit notice banner, 60s poll refresh.
3. **Perbandingan Narasi & Pangsa Suara** (`/narasi/`) — symmetric two-coalition
   comparison for a political issue: share-of-voice bar, per-coalition
   sentiment/dominant-themes/30-day trend, permission-gated access notice
   (FR-29.1), overlay SoV trend chart.
4. **Deteksi Perilaku Terkoordinasi** (`/koordinasi/`) — coordination cluster
   list (flagged/reviewed-organic/ignored), network graph (hub/amplifier/
   satellite accounts), coordination signal scores, upload-time heatmap,
   duplicate text sample comparison, human-review actions (escalate / mark
   organic — no auto-report/auto-block per FR-26.2/26.4).
5. **Distribusi Narasi Regional** (`/regional/`) — province heat grid,
   top-10 province ranking with sentiment composition, drill-down to a
   selected province's regency breakdown + dominant sub-issues + 30-day trend.
6. **Konsol Konfigurasi** (`/konfigurasi/`) — platform integration toggles
   (Apify actor / internal scraper status), masked Apify credential + test
   connection, per-platform actor selection, monitored domains table with
   adapter/status/last-tested, audit-logging notice (FR-2A.7).
7. **Dasbor Pengawasan & Netralitas** (`/pengawasan/`) — purpose statement
   banner (FR-29.5), summary KPIs (users with political-monitoring
   permission, 30-day political queries, auto-rejected individual profiles,
   election-period mode toggle), permission roster table, append-only audit
   log table, annual policy acknowledgment status.

**Out of scope / nav-disabled placeholders**: Umpan Sebutan, Analitik AI,
Sosiograf, Laporan — these appear in the design doc's sidebar but have no
mockup; render as disabled sidebar entries (no route, "segera hadir" affordance).

## Architecture

- **Backend**: Django, server-rendered templates (no DRF/API layer for this
  phase). SQLite for dev.
- **Frontend**: no JS framework. Port the design doc's own CSS (Archivo +
  IBM Plex Sans/Mono, teal `#0E7C86`/navy `#0B1F33` system, card patterns,
  inline SVG charts) into a shared base template + per-screen templates.
  Charts are hand-built inline SVG (as in the source mockup), not a charting
  library — keeps parity with the design doc and avoids a new dependency.
- **Auth**: real `django.contrib.auth` User model. No login screen this
  phase — a middleware auto-authenticates a seeded demo user ("Dewi Anjani",
  role "Analis Humas") on every request. Built so a real login view can be
  added later without model changes.
- **Realtime**: War Room's "Segarkan: 60 dtk" is implemented as client-side
  JS polling (`fetch` re-render or meta-refresh) against the same view.
  There is no WebSocket/push layer and no live ingestion — displayed values
  only change when the underlying seeded data changes.

## Django apps

### `core`
Reference/shared data and chrome.
- `Tenant` (instansi) — name
- `Project` (proyek) — tenant FK, name
- `Platform` — slug, display_name, brand_color, method (apify/internal)
- `Province` — name, population_online (for heat-map normalization)
- `Regency` — province FK, name
- `AnalystProfile` — user FK (1:1), tenant FK, role_label, has_political_monitoring_permission
- Shared base template (sidebar nav, header project/date/platform filters, `{{ instansi }}`/`{{ proyek }}` context)
- Demo-auth middleware

### `analytics`
The central fact table and everything aggregated from it.
- `Mention` — tenant/project FK, platform FK, province FK (nullable), regency
  FK (nullable), author_handle, content_snippet, sentiment
  (positive/neutral/negative), emotion (trust/anticipation/joy/anger/sadness/
  fear/surprise/disgust — Plutchik), posted_at, engagement_count,
  reach_estimate, is_political (bool), coalition FK (nullable), issue FK
  (nullable, only set when is_political)
- `Coalition` — name, slug, stance (petahana/penantang), color
- `PoliticalIssue` — title, status (active/closed), opened_at, owner_label
- `AlertRule` — name, condition_summary, channel (email/push/webhook)
- `Alert` — rule FK, issue FK (nullable), severity, title, detail,
  triggered_at, status (active/resolved)

Powers: Ringkasan, War Room, Perbandingan Narasi, Regional — each is a
different aggregation/filter over `Mention` (+ `Alert` for Ringkasan/War Room,
+ `Coalition`/`PoliticalIssue` for Perbandingan Narasi/War Room).

### `coordination`
- `CoordinationCluster` — issue FK, cluster_code, score (0-1), status
  (flagged/reviewed_organic/ignored), account_count, detected_at, note
- `ClusterAccount` — cluster FK, handle, role (hub/amplifier/satellite),
  reach, post_count
- `CoordinationSignal` — cluster FK, signal_type (text_similarity/time_sync/
  account_age/shared_media), score
- `DuplicateTextSample` — cluster FK, account_handle, posted_at, text,
  highlighted_phrase

Powers: Deteksi Koordinasi directly; War Room's "Klaster Terkoordinasi" count
and spreader table read from here too.

### `governance`
- `PlatformIntegration` — platform FK, actor_id, is_active, status_note
- `ApifyCredential` — masked_token, last_verified_at
- `MonitoredDomain` — domain, adapter, status (active/needs_review/inactive),
  last_tested_at
- `PoliticalMonitoringPermission` — user FK, approved_by, approved_at,
  active, revoked_at
- `AuditLogEntry` — timestamp, actor_label, action, target — append-only,
  no update/delete views exposed anywhere
- `PolicyAcknowledgment` — tenant FK, approved_by, approved_at, next_review_at

Powers: Konsol Konfigurasi, Dasbor Pengawasan.

## Seed data

One `seed_demo_data` management command (idempotent — safe to re-run) creates:
- 1 tenant ("Kemenko PMK"), 1 project ("Program Pangan Rakyat")
- 7 platforms (X, TikTok, Instagram, YouTube, Facebook, Berita Daring, Forum/Blog)
- Provinces/regencies actually referenced by the design doc (Maluku + its
  regencies, Papua, Sulawesi Tengah, NTT, DKI Jakarta, Jabar, Jateng, Jatim,
  Sumut, Banten, Sulsel, Kaltim, + a handful more for the heat grid)
- 3,000–5,000 `Mention` rows spread across a 30-day window with realistic
  platform/sentiment/province distribution
- 1 `PoliticalIssue` ("Distribusi Pangan Wilayah Timur") with 2 `Coalition`
  rows ("Koalisi Nusantara Raya", "Koalisi Perubahan Bersatu") and their own
  political `Mention` split (is_political=True, coalition set)
- 4 `CoordinationCluster` rows (2 flagged, 1 reviewed-organic, 1 ignored)
  with accounts, signals, and duplicate text samples
- 5–8 `Alert` rows across a couple of `AlertRule`s
- 5 `PlatformIntegration` rows, 1 `ApifyCredential`, 4 `MonitoredDomain` rows
- 3 users with `PoliticalMonitoringPermission` (including the demo user)
- 10–20 `AuditLogEntry` rows, 1 `PolicyAcknowledgment`

Displayed KPI numbers will be real aggregates over this seeded data and will
not match the design doc's illustrative figures exactly.

## Error handling & testing

- Views are read-mostly; the only writes in this phase are the two
  human-review actions on Deteksi Koordinasi (escalate / mark organic), which
  update `CoordinationCluster.status` and append an `AuditLogEntry` — wrapped
  in a transaction so both succeed or neither does.
- Django's standard 404/500 handling; no custom error UX needed for this phase.
- Testing: one Django test per app covering (a) `seed_demo_data` runs
  cleanly and produces non-empty querysets, (b) each of the 7 views returns
  200 and renders its key template blocks, (c) the two coordination actions
  correctly mutate cluster status and write an audit entry.

## Out of scope (explicitly deferred)

- Real ingestion/scraping — Apify/scraper toggles are UI-only, no live API calls
- Login screen / multi-tenant access control
- Umpan Sebutan, Analitik AI, Sosiograf, Laporan screens
- WebSocket/live push (polling only)
- REST API layer
