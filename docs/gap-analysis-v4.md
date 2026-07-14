# Implementation Gap Analysis — SRS v4 (KPM-inspired) vs. Current Codebase

**Date:** 2026-07-14
**SRS:** `SRS_Government_Political_Narrative_Platform_v4_KPM_inspired.docx` (v1.1, PANTAU)
**Codebase:** Django monolith (`pantau/`, 4 apps), SQLite, seeded demo data + one live RSS scraper

Legend: ✅ implemented · 🟡 partial (UI/demo/shallow) · ❌ missing

---

## 1. Executive summary

The current codebase is a **UI-complete prototype of 7 dashboard screens** driven by seeded demo data plus **one real data-collection slice** (RSS news scraping with a naive keyword/lexicon pipeline). It demonstrates the *shape* of the product convincingly and covers meaningful slices of Phase 1–3 functionality at the presentation layer.

Against the full SRS, however, the bulk of the system is not yet built:

- **Architecture:** SRS targets ~20 independently-deployable microservices (Kafka, Elasticsearch, Redis, K8s, secrets manager, RAG vector index). Current is a single Django app on SQLite with no message bus, search index, or cache. *(SRS §3.5 explicitly permits a coarser-grained Phase-1 deployment, so a monolith is defensible for MVP — but the target architecture is a large future lift.)*
- **Data collection:** Apify integration is absent; the "custom scraper" is RSS-only. No orchestrator/scheduler, no proxy layer, no raw data lake, no X/Instagram/TikTok/YouTube/Facebook collection.
- **AI/NLP:** No real classifier — sentiment is a Bahasa-Indonesia word-list; emotion/OCEAN/demographics are seeded or absent.
- **Governance depth, security, non-functionals:** Foundational models exist; enforcement, encryption, secrets, audit immutability, RBAC matrix, exports, APIs, and i18n are largely missing.

**Bottom line:** roughly **Phase 1 partially demoed + selected Phase 2/3 screens mocked**, with the real collection/AI/infra substrate and the security/governance enforcement still to build.

---

## 2. What exists today

| App | Screens (views) | Models |
|-----|-----------------|--------|
| `core` | `profile` | Tenant, Project, Platform, Province, Regency, AnalystProfile |
| `analytics` | `ringkasan` (Summary), `war_room`, `narasi` (SoV), `regional` | Coalition, PoliticalIssue, Mention, AlertRule, Alert |
| `coordination` | `koordinasi` (CIB) | CoordinationCluster, ClusterAccount, CoordinationSignal, DuplicateTextSample |
| `governance` | `konfigurasi` (Config Console), `pengawasan` (Oversight) | PlatformIntegration, ApifyCredential, MonitoredDomain, MonitoringKeyword, PoliticalMonitoringPermission, AuditLogEntry, PolicyAcknowledgment |

**Real (non-mocked) behavior:** `governance/scraping.py` fetches live RSS feeds, matches active keywords, scores sentiment via a positive/negative word list, and persists `Mention` rows; `konfigurasi` "Uji Koneksi"/"Pindai" buttons drive it. Everything else renders computed analytics over seeded data.

---

## 3. Requirement-by-requirement gap map

### Foundation — Tenant, RBAC, Permissions (§5.1, §5.1A)
| Req | Status | Notes |
|-----|--------|-------|
| FR-1.1 multi-tenant projects | 🟡 | Tenant/Project models + active-project context; single seeded tenant |
| FR-1.2 strict DB/index isolation | 🟡 | `project` FK on Mention; no enforced query-scoping guard, no search index |
| FR-1.3 roles (Admin/Analyst/Viewer/SuperAdmin) | 🟡 | `AnalystProfile.role_label` is free text; no real role model/enforcement |
| FR-1.4 tenant-scoped user mgmt | ❌ | No invite/role-assignment flow |
| FR-1.5 inactive-by-default registration | ❌ | Django auth only; registration templates just added |
| FR-1.6 last-admin lockout protection | ❌ | — |
| FR-1A.1–1A.4 page-permission matrix | ❌ | No `PagePermission` model/UI/audit |

### Configuration Console (§5.2, §5.2A)
| Req | Status | Notes |
|-----|--------|-------|
| FR-2.1 boolean keyword queries | ❌ | Keywords are plain strings, substring match only |
| FR-2.2 per-platform keyword scoping | ❌ | — |
| FR-2.3 match-volume preview | ❌ | — |
| FR-2.4 runtime add/edit/disable | 🟡 | Keywords/domains CRUD works; takes effect on manual scan |
| FR-2A.1 platform enable/disable | 🟡 | `PlatformIntegration` toggle; not per-project |
| FR-2A.2 domain + adapter mgmt | 🟡 | Add/remove/test domains; single generic RSS adapter |
| FR-2A.3–2A.5 Apify key entry/test/rotate/actor select | ❌ | `ApifyCredential` is a masked string only; no encryption/test/rotate/actor dropdown |
| FR-2A.6 polling/concurrency/rate config | ❌ | — |
| FR-2A.7 audit config changes | 🟡 | `record_audit_entry()` exists; not wired to every change |
| FR-2A.8 test-run action | 🟡 | Manual "Pindai" runs full scan, not a single limited test |
| FR-2A.9–2A.11 Runtime Settings (DB-backed, masked, reserved) | ❌ | No `RuntimeSetting` model |

### Data Collection Layer (§4)
| Req | Status | Notes |
|-----|--------|-------|
| REQ-DC-01–09 Apify integration | ❌ | No Apify API client, cost tracking, actor versioning, or Google Trends |
| REQ-CS-01,02,04,05 Playwright/proxy/rate-limit/backoff | ❌ | Plain `urllib` RSS fetch only |
| REQ-CS-03,10 site adapters + runtime domain list | 🟡 | One generic RSS adapter; domains configurable |
| REQ-CS-06,09 robots.txt / CAPTCHA | ❌ | — |
| REQ-CS-07 scraper health dashboard | ❌ | Per-domain status field only |
| REQ-CS-08 raw payload data lake + versioning | ❌ | No raw storage; only normalized Mention |
| REQ-SC-01–05 scheduling/orchestration | ❌ | Manual button; no scheduler, priorities, or cadence |
| §4.4 unified schema | 🟡 | Mention ≈ subset; no `raw_payload_ref`, media, collection_method version |
| REQ-LC-01–07 retention/kill-switch/PII/method-audit | 🟡 | `is_scraped` + integration toggle; no retention purge, PII minimization, or fast platform-wide kill-switch |

### Mention Feed & Issue Taxonomy (§5.3, §5.3A)
| Req | Status | Notes |
|-----|--------|-------|
| FR-3.1–3.3 raw mention feed + dedup + author link | ❌ | No feed screen; dedup only via unique `source_url`; no Author entity |
| FR-3A.1–3A.6 taxonomy, auto/manual labeling, merge/unmerge | ❌ | No Category/SubCategory/Issue taxonomy or labeling queue |

### Core Analytics (§5.4–5.23)
| Req | Status | Notes |
|-----|--------|-------|
| FR-4 Summary dashboard | 🟡 (strong) | `ringkasan` has totals, sentiment, timeline, source split, health index. Missing: period-over-period %, gender-by-channel, global date-range filter |
| FR-5 AI sentiment | 🟡 | Word-list scorer / seeded; no LLM/NLP, confidence, or manual override |
| FR-6 emotion (Plutchik) | 🟡 | 5 of 8 emotions, seeded; aggregate viz only |
| FR-7 OCEAN | ❌ | — |
| FR-8 demographics/gender | ❌ | — |
| FR-9 author/influencer analytics | 🟡 | Unique-author count only; no influence rank or sociograph |
| FR-10 sociograph — keyword | ❌ | — |
| FR-11 buzzer/KOL campaign tracking | ❌ | No `BuzzerCampaign` |
| FR-12 alerts & notifications | 🟡 | Alert/AlertRule models + display; no rule engine or delivery |
| FR-13 geo mapping | 🟡 (strong) | `regional` heat tiles + regency drill + trend; tile heatmap, not a geo map |
| FR-14 comparison / saved views | ❌ | Camp comparison exists (narasi) but not arbitrary keyword comparison |
| FR-15 Digital Health Index | 🟡 | Ad-hoc formula on Summary; no historical trend |
| FR-16 infographic report builder | ❌ | — |
| FR-17 Command Center widgets | ❌ | — |
| FR-18 CRM integration | ❌ | — |
| FR-19 manual correction & tagging | ❌ | — |
| FR-20 export CSV/XLSX/PDF | ❌ | — |
| FR-21 interaction summary | 🟡 | Total engagement shown; not per-platform breakdown |
| FR-22 profile/topic analysis | ❌ | Phase 4 (out of scope) |
| FR-23 billing/usage metering | ❌ | — |

### Political Narrative Intelligence (§5A)
| Req | Status | Notes |
|-----|--------|-------|
| FR-24 actor/party rivalry | 🟡 | Coalition (petahana/penantang) + camp trends; no `PoliticalActor` entity or detection rules |
| FR-25 comparative narrative / SoV | 🟡 (strong) | `narasi` computes SoV, sentiment, dominant themes, symmetric overlay. Missing neutral-brief export, real topic clustering |
| FR-26 CIB / buzzer-network detection | 🟡 | `koordinasi` full UI + review workflow (escalate/mark-organic); scores seeded, no detection engine |
| FR-27 program/policy sentiment | ❌ | No `GovernmentProgram` entity |
| FR-28 War Room | 🟡 | Real-time volume/sentiment/spreaders/hotspots. Missing response-action logging (FR-28.2), accelerated refresh, escalation alerts |
| FR-29 governance/neutrality | 🟡 | `pengawasan` + permission/audit/policy models; admin made view-only. Missing co-approval (29.1), private-individual prohibition (29.3), persistent notice (29.5), immutable-log enforcement |
| FR-30 Daily Executive Brief Engine | ❌ | — |
| FR-31 Regulatory RAG grounding | ❌ | — |

### External Interfaces & Non-Functional (§7, §8)
| Area | Status | Notes |
|------|--------|-------|
| REST/GraphQL API, WebSocket, webhooks | ❌ | Server-rendered Django only |
| i18n (Bahasa + English) | ❌ | Indonesian hardcoded in templates |
| Encryption at rest, secrets manager | ❌ | Plaintext SQLite; masked-string credential |
| Search index (Elasticsearch) | ❌ | ORM aggregation over SQLite |
| Observability (tracing/metrics/logs) | ❌ | — |
| Backups / HA / model fallback chain | ❌ | — |
| CSRF, audit immutability | 🟡 | CSRF enabled; AuditLogEntry admin view-only (recent commit) |

---

## 4. Recommended plan to close the gap

Framing: keep the **Django monolith** for Phases 1–2 (SRS §3.5 permits this), defer the microservices split, and prioritize **real data + real enforcement** over more mocked screens. Work is grouped into value-ordered workstreams.

### Workstream A — Make Phase-1 "Must" real (foundation) — ✅ DONE (2026-07-14)
Implemented TDD; +53 tests (89 → 142 passing). Details:
1. ✅ **RBAC + activation model** (FR-1.3/1.5/1.6): `AnalystProfile.role` enum (super_admin/tenant_admin/analyst/viewer), `apps/core/rbac.py` with `create_pending_user` (inactive-by-default), `activate_user`, and last-admin lockout guard enforced in the Django user admin.
2. ✅ **Page-permission matrix** (FR-1A): `PagePermission` model + `apps/core/permissions.py` (`can_access`, `require_page`, reserved super-admin/dev-ops combos), Super-Admin editor UI at `governance:permission_matrix` with audit on every toggle. Tool pages (konfigurasi, pengawasan) now gated.
3. ✅ **Runtime Settings + real Apify credential** (FR-2A.3/2A.9-11, REQ-DC-01/08): `RuntimeSetting` (Fernet-encrypted secrets, masked display, reserved keys) + `apps/governance/apify.py` (live token validation, encrypted store, rotate, revoke). Dev/Ops page at `governance:runtime_settings` (super-admin only).
4. ✅ **Tenant isolation guard** (FR-1.2): `scope_to_tenant`/`visible_projects`/`get_active_tenant` in `apps/core/selectors.py`, proven by two-tenant isolation tests; used by the export path.
5. ✅ **Export** (FR-20): `apps/analytics/exports.py` CSV (streaming) + XLSX, configurable row cap (default 10k via `export.max_rows` Runtime Setting), 100-row server-side batching; `analytics:export_mentions` gated by the `export` page permission. *(PDF export still pending.)*

### Workstream B — Real collection breadth — 🟢 IN PROGRESS (2026-07-14)
Grounded in `docs/APIFY_INTEGRATION.md`. Implemented TDD; +28 tests (142 → 170 passing). Uses Apify's REST `run-sync-get-dataset-items` endpoint via stdlib (no `apify-client` dependency), consistent with `apify.py`.
6. ✅ **Apify connector** (REQ-DC-01/03/05): `apps/governance/apify_crawler.py` — `ACTOR_CONFIG` (actor IDs + per-platform input builders from doc §4), `collect()` via REST (network boundary `_run_and_fetch_items` is stubbable), `extract_platform_content` normalization (doc §5).
7. ✅ **Orchestrator + ledger + cost** (REQ-SC-05, REQ-DC-04): `apps/governance/orchestrator.py` fans active keywords across enabled Apify platforms, `CollectionRun` ledger with overlap-skip claim and per-run cost estimate; `manage.py collect` command (REQ-SC-04); unified run history on Konfigurasi (REQ-SC-03).
8. ✅ **Ingestion + Author + dedup** (§4.4, FR-3.2/3.3): `apps/governance/ingestion.py` persists normalized items as Mentions, dedup by `Mention.external_id`, links normalized `Author`. Interim sentiment via lexicon scorer (swappable for NLP in Workstream C).
9. ✅ **Mention feed** (FR-3.1): `analytics:feed` screen filterable by platform/sentiment/author, tenant-scoped, gated by the `feed` page permission (a "raw mention review" tool page → denied by default for analyst/viewer per FR-1A.1).
10. ⏳ **Remaining:** boolean query engine + volume preview (FR-2.1/2.3), raw data-lake payload persistence + collection_method version (REQ-CS-08), Apify webhook/poll + published_at parsing, per-tenant scheduling cadence UI (REQ-SC-01).

### Workstream C — Real AI/NLP — 🟢 MOSTLY DONE (2026-07-14)
Implemented TDD; +27 tests (170 → 197 passing). Backfilled 5,405 seeded mentions through the real pipeline (`manage.py enrich --all`) → 869 auto-labeled onto the taxonomy.
11. ✅ **Pluggable NLP layer** (FR-5.1/5.2, §8.3/8.6): `apps/analytics/nlp/` — `Provider` interface + `Classification` (sentiment, **confidence**, emotions, model_version); `LexiconProvider` (id+en); `DummyProvider` (deterministic degraded mode, no external call); `Pipeline` **tiered fallback chain** that always terminates in a valid result. A real LLM provider plugs in as the primary tier without changing callers. `Mention.sentiment_confidence`/`sentiment_model` persisted.
12. ✅ **Full Plutchik emotion, multi-label** (FR-6.1): all 8 primary emotions; `Mention.emotion_labels` (JSON, multi-label) alongside the legacy single `emotion` field.
13. ✅ **Manual correction + history** (FR-5.3, FR-19.2): `LabelCorrection` model (old→new, who, when) as the model-tuning feedback signal; inline correction control on the feed; admin-read-only.
14. ✅ **Issue Taxonomy + auto/manual labeling + merge** (FR-3A): `Category → SubCategory → Issue` + `IssueLabel` (auto|manual); auto-labeling on ingest **and** on backfill; manual review queue for unmatched content; **manual labels never overwritten by an auto pass** (FR-3A.3); merge/unmerge with reversible `IssueMergeHistory` (FR-3A.5); top-content preview (FR-3A.6). New `taxonomy` tool page, denied by default to analyst/viewer.
15. ⏳ **Remaining:** OCEAN (FR-7), demographics/gender (FR-8), real LLM provider wired as primary tier (the `analyze` API contract in `docs/api-example-analyze-*.json` is the intended enrichment interface), unresolved-raw-label queue (FR-3A.4).

### Workstream D — Political/governance modules — 🟢 MOSTLY DONE (2026-07-14)
Implemented TDD; +47 tests (197 → 244 passing).
14. ✅ **PoliticalActor + camps + program/policy** (FR-24, FR-27): `PoliticalActor` (party/coalition/official/organization) with keywords+handles, **user-defined `Camp`** (no camp is hard-coded or defaulted, FR-24.3), multi-actor tagging per mention, symmetric Share-of-Voice, and `GovernmentProgram` as a first-class tracked entity with its own sentiment breakdown. *(Service + admin layer; no dedicated actor-management UI yet — `narasi` still renders off the legacy `Coalition` model.)*
15. ✅ **CIB detection engine** (FR-26.1/26.2): real coordination scoring in `apps/coordination/detection.py` — near-duplicate text (Jaccard), synchronized posting times, shared-media proxy → weighted composite score; clusters above a configurable threshold are **flagged for human review only, never auto-actioned**. `manage.py detect_coordination`.
16. ✅ **War Room response log + alert engine** (FR-28.2, FR-12): `ResponseAction` logged against the live issue timeline (auditable record of the institution's response); `apps/analytics/alerting.py` evaluates machine-readable rules (negative-ratio, volume-spike) over a rolling window, raises deduplicated Alerts with the numbers that caused them. `manage.py evaluate_alerts`.
17. ✅ **Governance enforcement** (FR-29, §8.5) — `apps/governance/neutrality.py`: political views gated on the **Political Monitoring permission** (FR-29.1) with every political query written to the audit trail (FR-29.2); **data-model prohibition on profiling private individuals** (FR-29.3 — only parties/coalitions/public officials/organizations may be registered); persistent neutrality notice (FR-29.5); **election-period mode** freezing political-actor configuration (§8.5).
    - Also removed a duplicate source of truth: `AnalystProfile.has_political_monitoring_permission` was a stored bool that the profile page displayed but nothing enforced — it could read "Diizinkan" while access was denied. It is now a **derived property** of the governance grant, so it cannot drift.
18. ⏳ **Remaining:** Daily Brief Engine (FR-30) + Regulatory RAG (FR-31) — the largest Phase-3 items; actor-management UI; wiring `narasi` onto `PoliticalActor`/`Camp` in place of legacy `Coalition`.

**Demo-data caveat:** the seeded corpus never names a party, so actor tagging matches nothing and Share-of-Voice renders 0%/0% until real collected data (or an enriched seed) is present. Program tagging does work on the seed (134 mentions → "Program Pangan Rakyat").

### Workstream E — Daily Brief + Regulatory RAG — 🟢 DONE (2026-07-14)
Implemented TDD; +41 tests (244 → 285 passing). Closes the two largest remaining Phase-3 items.
19. ✅ **Daily Executive Brief Engine** (FR-30): `DailyBrief`/`DailyBriefIssue`/`DailyBriefRun`; H-1 per-issue generation shortlisted by negative sentiment or unusual volume; output is **always a draft requiring human review** (FR-30.2) and generated text carries an explicit draft banner (FR-31.4); edit/approve/reorder workflow (FR-30.3); **finalize locks the brief** so the record of what leadership read cannot be rewritten (FR-30.4); **DB-level status claim** means a scheduled and a manual run arriving together cannot duplicate or corrupt output (FR-30.6). `manage.py generate_brief`.
20. ✅ **Regulatory & policy grounding** (FR-31): `RegulatoryDocument` corpus kept separate from the mention index (FR-31.1); lexical retrieval with a light **Indonesian stemmer** (agglutinative affixes — `disalurkan`/`penyaluran` → `salur`); every hit returns its **source passage alongside the citation** so a reviewer can verify it independently (FR-31.2/31.4); **risk classification** Rendah/Sedang/Tinggi (FR-31.3); corpus managed in the console (FR-31.5). Returns *nothing* rather than a weak match — better no citation than a fabricated-sounding one.
    - **Retrieval defect found by running it, not by testing it:** a food-price issue cited the *fuel-subsidy* Perpres first, because the taxonomy keyword "harga bahan" incidentally overlapped "bahan bakar" and the shorter doc won on term frequency. A wrong top-ranked citation is exactly the risk FR-31.4 exists to mitigate. Fixed by weighting title matches (a regulation's title states its subject): the food regulation now ranks 1.042 vs 0.106.

### Workstream G — Scheduling & operations — 🟢 DONE (2026-07-14)
Implemented TDD; +41 tests (313 → 354 passing). Prompted by deployment: the platform ran
in production but **nothing ran on a cadence** — collection, alerting, briefs and CIB
detection all waited for a human to type a management command.
21. ✅ **Cadence scheduler** (REQ-SC-01/02): `ScheduledJob` (per-project cadence) +
    `apps/governance/scheduling.py` + a `scheduler` container running `manage.py
    run_scheduler`. Deliberately a DB-backed loop, not Celery/Redis: the job set is small
    and fixed, and Postgres already provides the one primitive a scheduler needs —
    `SELECT … FOR UPDATE SKIP LOCKED` — so two replicas cannot run the same job twice
    (and cannot pay Apify twice for it). A broker would add an operational component and
    a failure mode without adding a capability.
    - **Missed windows do not replay.** If the scheduler is down for a day, a 15-minute
      job is 96 windows overdue; catching up would fire 96 collection runs at once — a
      self-inflicted stampede against Apify and 96 duplicate briefs. It runs once and
      resumes cadence.
    - Repeated failures back off geometrically (capped at 60m) rather than hammering a
      dead upstream every cycle; one failing job never stops the others.
    - The scheduler runs in its own container, so a four-minute collection cannot occupy
      a gunicorn worker that should be answering an analyst.
22. ✅ **Collection kill switch** (REQ-LC-03): halts all collection platform-wide, from
    the console, effective immediately. **Enforced at the collection boundary, not in the
    scheduler** — `manage.py collect` and the console's "Pindai" button call the
    orchestrator directly, so a halt only the scheduler honored would be undone by the
    next person to press the button. It does *not* stop alerting or briefs: those run over
    data already held, which is exactly what people need during the incident that made
    someone hit the switch. Toggling is audited.
23. ✅ **Collector health** (REQ-CS-07): per-source status on the console. Explicitly
    models the failure that hides — a collector that reports success and simply *stops
    producing* is reported `stale`, not green, because a flat trend line read as calm
    public opinion is the most dangerous thing this platform can show. Overlap-skips are
    not counted as failures.
24. ✅ **Retention purge** (REQ-LC-01/02/04): `apps/governance/retention.py` +
    `manage.py purge_retention` (dry-run by default). Two rules, both load-bearing:
    **no policy means no deletion** (the platform must never start deleting a ministry's
    archive on its own), and **an open coordination investigation is never purged** — a
    flagged cluster is a case a human is still reviewing, and deleting the posts under it
    on a date boundary would destroy the evidence and leave the cluster pointing at
    nothing. Purges are audited; dry runs are not.

**Bug found by driving a real browser, not by the tests:** the schedule form silently
submitted nothing. Django's `{# … #}` comment is *single-line only*, so a multi-line
`{# … #}` explaining an HTML pitfall was emitted verbatim into the page — and because it
contained the literal text `<form>`, the browser parsed it as a real form start tag inside
`<tbody>`, foster-parented it out, and then (nested-form rule) stripped the `id` and
`action` off every real schedule form. The comment caused the exact bug it described. The
Django test client never parses HTML, so all 9 view tests passed against a page that was
broken in every real browser.

### Workstream F — Platform/non-functional (deferred)
25. REST/GraphQL API + WebSocket (§7), i18n framework (§8.8), observability (§3.6), search index, OCEAN (FR-7) + demographics (FR-8), real LLM provider as primary NLP tier, PDF/DOCX brief export (FR-30.5), then the microservices decomposition (§3.3) once load/team justify it.

### Known gap surfaced while building Workstream G
- **`PoliticalIssue` has no `project` FK** — issues are global, shared across every tenant.
  This contradicts FR-1.2 (strict tenant isolation). `detect()` and the retention purge both
  scope the *mentions* they read to a project, so nothing leaks today, but the issue list
  itself is not tenant-scoped and should be.

### Suggested near-term sequencing
- **Sprint 1–2:** A1–A5 (RBAC, permission matrix, runtime settings/Apify cred, tenant guard, export) — turns the demo into a governable Phase-1 base.
- **Sprint 3–4:** B6–B10 (Apify + orchestrator + real ingestion + feed) — real multi-platform data.
- **Sprint 5–6:** C11–C13 (real NLP + taxonomy) — replaces the word-list pipeline.
- **Sprint 7+:** D + E per Phase-2/3 priority.
