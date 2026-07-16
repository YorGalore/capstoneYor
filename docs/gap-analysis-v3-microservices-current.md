# Current Gap Analysis — SRS v3 Microservices vs Current Codebase

**Audit date:** 2026-07-14  
**SRS reviewed:** `SRS_Government_Political_Narrative_Platform_v3_microservices.pdf` (42 pages)  
**Code reviewed:** current working tree, including uncommitted landing/onboarding work  
**Validation:** 383 Django tests pass after the critical-remediation tranche; system checks pass; no missing migrations

Legend: ✅ implemented · 🟡 partial / prototype-depth · ❌ missing

## Executive conclusion

The current system is a credible **modular-monolith pilot**, but it is **not yet conformant with the v3 SRS**. It has good server-rendered dashboard coverage, a working Apify happy path, RSS ingestion, scheduling, a pluggable enrichment interface, governance models, a CIB scoring prototype, and strong automated unit/integration coverage.

The largest gap is structural: the SRS requires independently deployable microservices, database-per-service boundaries, Kafka/event contracts, an API gateway/BFF, Elasticsearch, Redis, raw object storage, distributed tracing, and Kubernetes scaling. The repository is one Django deployment sharing one relational database, with a second container running Django management jobs. Section 3.5 permits temporarily coarser services in Phase 1, but the current design has no deployable service boundaries or event contracts from which to evolve yet.

The second-largest gap is production completeness. Several screens still demonstrate analytics over seeded data rather than end-to-end collected/enriched data. The 2026-07-14 remediation tranche closed the identified configuration/alert tenant-isolation defects, mutation authorization bypass, false-success Apify handling, disconnected political/program tagging, and application-layer audit mutation paths. Production infrastructure and the remaining functional modules are still substantial work.

### Release readiness

| SRS release | Current assessment | Main reason |
|---|---|---|
| Phase 1 — MVP | 🟡 Partial | Core UI, RBAC, project-scoped configuration, Apify collection, feed, scheduling and CSV/XLSX exist; custom X scraper, full unified schema, raw lake, and service/search isolation do not. |
| Phase 2 — Core Analytics | 🟡 Early/partial | Sentiment fallback, alert evaluation, geo views and political models exist; real AI, notification delivery, usage caps, arbitrary comparison, and connected actor/program workflows are incomplete. |
| Phase 3 — Advanced | 🟡 Prototype slices | War Room and CIB have meaningful slices; OCEAN, demographics, sociographs, command center, CRM, reports and full oversight are absent or shallow. |
| Target architecture / production NFRs | ❌ Not implemented | No microservice deployments, queue, search cluster, cache, object store, API contracts, tracing, autoscaling, HA or performance evidence. |

## Critical-remediation status

### 1. Configuration ownership — ✅ Fixed

`PlatformIntegration`, `ApifyCredential`, `MonitoredDomain`, `MonitoringKeyword`, and `CollectionRun` now require a project. Per-project uniqueness, UI/query scoping, forms, health, scheduler/command credential lookup, and a legacy-data migration are implemented. Cross-project mutation and credential isolation have regression tests.

### 2. Configuration mutation authorization — ✅ Fixed

Every configuration mutation endpoint now enforces `@require_page("konfigurasi")`, and object lookup includes the active project. Viewer denial and guessed cross-project IDs are covered by tests.

### 3. Collection ledger attribution — ✅ Fixed

`CollectionRun` now requires a project. Overlap detection, history, estimated cost, health, and admin visibility are project-scoped. Actual provider-billed cost and the full FR-23 usage ledger remain future work.

### 4. Political actor/program enrichment — ✅ Fixed at ingestion

Live ingestion now invokes `tag_mention()` and `tag_program()` after normalization/taxonomy. Tests cover matching configured public actors/programs and excluding unregistered private individuals. The Narrative UI still needs migration from legacy `Coalition` to `PoliticalActor`/`Camp`.

### 5. Alert ownership — ✅ Fixed; delivery remains missing

`AlertRule` and `Alert` now require a project. Evaluation, deduplication, issue validation, dashboard retrieval, admin and seeds are project-scoped, with a migration that preserves legacy semantics. Email, push and signed-webhook delivery, triggering-mention links, and War Room distribution lists remain missing.

### 6. Apify false-success handling — ✅ Fixed

Transport, HTTP, OS, malformed JSON, and unexpected-payload failures now raise `ApifyCollectionError`, allowing the orchestrator to record a failed run and the scheduler to back off. A genuine empty dataset remains a successful empty run.

### 7. Audit mutation paths — 🟡 Hardened

Admin edits were already disabled. Model and queryset update/delete operations now raise `ValidationError`, with regression tests. A database-native append-only trigger or external write-once audit store is still required to defend against privileged SQL access and fully satisfy the target architecture.

## Requirement gap map

### Architecture, deployment and observability (§3)

| Requirement area | Status | Current evidence / gap |
|---|---|---|
| Independently deployable service catalog | ❌ | One Django image/application and one scheduler process share code and DB. |
| Database per service | ❌ | Single Django `DATABASES["default"]`; SQLite locally and one PostgreSQL service in Compose. |
| API Gateway + BFF | ❌ | No gateway or dashboard API service. |
| Kafka asynchronous event pipeline | ❌ | Direct in-process calls; no broker, schemas, DLQ or idempotent consumers. |
| Elasticsearch/OpenSearch mention search | ❌ | Django ORM queries and relational indexes only. |
| Redis cache/rate counters | ❌ | No cache service/dependency/configuration. |
| Immutable S3/GCS raw lake | ❌ | Raw payload/HTML is not stored and mentions have no `raw_payload_ref`. |
| Independent containers/CI/scaling | ❌ | Web and scheduler reuse one image; no per-domain images, K8s, HPA or IaC. |
| Resilience patterns | 🟡 | Scheduler has failure backoff and overlap control; no service-boundary circuit breakers, Kafka retry/DLQ, or general idempotency contract. |
| Observability (§3.6) | ❌ | Console logging and `/healthz` exist; no OpenTelemetry trace IDs, Prometheus metrics, centralized log metadata, or per-service probes. |

### Tenant, access and configuration (FR-1, FR-2, FR-2A)

| Requirement | Status | Notes |
|---|---|---|
| FR-1.1 multi-tenant projects | 🟡 | Models and active-project context exist; no tenant/project management UI or API. |
| FR-1.2 strict isolation | 🟡 (strong) | Analytics, configuration, credentials, collection runs and alerts are project-scoped with regression tests; no database row-level security or search-index isolation. |
| FR-1.3 RBAC roles | 🟡 (strong) | Four roles, page matrix and configuration endpoint enforcement exist; a full API-layer authorization model awaits the API. |
| FR-1.4 tenant user invite/remove/role assignment | ❌ | Internal RBAC helpers and Django admin exist, but no tenant-admin workflow constrained to its tenant. |
| FR-2.1 boolean/phrase/exclusion queries | ❌ | One unique plain keyword string with substring-style matching. |
| FR-2.2 platform-scoped query | ❌ | Keywords have no project/platform relationships. |
| FR-2.3 match-volume preview | ❌ | Stored `match_count` is not a pre-save estimate/preview. |
| FR-2.4 runtime CRUD | 🟡 (strong) | Project-scoped keyword/domain CRUD works; boolean/platform query semantics are still missing. |
| FR-2A.1 project platform toggles | ✅ | Platform integrations are unique and enabled/disabled per project. |
| FR-2A.2 domain/adapter management | 🟡 | Project-scoped CRUD exists; only RSS behavior is real and adapter is free text. |
| FR-2A.3 credential lifecycle | 🟡 (strong) | Project-scoped encrypted/masked/test/rotate/revoke works; a separate platform-wide fallback hierarchy is not modeled. |
| FR-2A.4 live token validation | ✅ | Save path tests the Apify token before activation. |
| FR-2A.5 actor selection/version pinning | ❌ | Actor IDs are hard-coded in `ACTOR_CONFIG`; model `actor_id` is not used by the crawler. |
| FR-2A.6 per-source frequency/concurrency/rate | ❌ | Cadence is per project/job type, not source; no concurrency/rate-limit controls. |
| FR-2A.7 configuration audit | 🟡 (strong) | Console writes are logged and application ORM mutation/deletion is blocked; before/after structured values and a DB-native write-once store remain missing. |
| FR-2A.8 limited test run | 🟡 | Token/domain tests and a full manual scan exist; no isolated limited source job with unified result. |

### Collection, scheduling and legal controls (§4)

| Requirement area | Status | Notes |
|---|---|---|
| REQ-DC-01 trigger Apify with managed secrets | 🟡 (strong) | Working synchronous REST path with project-scoped encrypted credentials; no dedicated external secrets manager. |
| REQ-DC-02 webhook + polling fallback | ❌ | Uses only `run-sync-get-dataset-items`. |
| REQ-DC-03 queue dataset items | ❌ | Items are passed directly into Django ingestion; no message queue. |
| REQ-DC-04 cost attribution | 🟡 | Estimated cost and runs are project-owned; actual Apify compute/pay-per-result billing data is not retrieved. |
| REQ-DC-05 per-keyword inputs | ❌ | Fixed code-generated input; no stored per-keyword date/range/limit configuration. |
| REQ-DC-06 version pin/deprecation/schema alert | ❌ | Hard-coded actor IDs; no versions or alerts. |
| REQ-DC-07 retry/backoff/rate-limit handling | 🟡 | Upstream failures are explicit and scheduled jobs back off; actor-specific rate-limit parsing, durable retry queue and admin alert delivery remain missing. |
| REQ-DC-08 runtime credential | 🟡 (strong) | Project-scoped encrypted create/view/test/rotate/revoke works; no platform-default fallback hierarchy. |
| REQ-CS-01-02 isolated headless workers/proxies | ❌ | No Playwright/Puppeteer, worker pool, network isolation or proxy rotation. |
| REQ-CS-03 site adapters | 🟡 | Config has an adapter label, but implementation is one generic RSS parser. |
| REQ-CS-04-06 pacing/circuit breaker/robots | ❌ | Not implemented. |
| REQ-CS-07 health | 🟡 | Source freshness/status exists; no success/block/latency metrics and alerts. |
| REQ-CS-08 raw versioned payload | ❌ | Not stored. |
| REQ-CS-09 CAPTCHA queue | ❌ | Not implemented. |
| REQ-CS-10 runtime domains | 🟡 | Project-scoped CRUD works; arbitrary site adapters are not implemented. |
| REQ-SC-01 cadence | 🟡 | Per-project collection cadence exists, not per tracked keyword. |
| REQ-SC-02 priority queue | ❌ | Fixed database polling order; no priority job queue. |
| REQ-SC-03 unified orchestration/status | 🟡 | Apify runs and health are project-scoped; RSS scan follows a separate execution/status path. |
| REQ-SC-04 date-range backfill | ❌ | Management/manual collection exists but accepts no keyword/date backfill range. |
| Unified mention schema (§4.4) | 🟡 | Core content/author/sentiment fields exist; media, language, collection method+version, structured engagement, emotion scores, geo object, raw reference and true source publish time are incomplete. |
| REQ-LC-01-07 compliance controls | 🟡 | Kill switch and retention purge exist. Missing per-source legal approval, robots enforcement, PII minimization/redaction, DSAR/opt-out workflow, method/version audit per mention, and source-specific immediate kill switches. |

### Analytics and delivery (FR-3 through FR-23)

| Module | Status | Main remaining gap |
|---|---|---|
| Mention feed (FR-3) | 🟡 | Platform/sentiment/author filters, dedup and author link work; documented date filter is not applied, and “raw” source payload is unavailable. |
| Summary (FR-4) | 🟡 | Totals, sentiment, daily timeline and source share work; no period-over-period indicators, hourly/monthly selector, gender view, or consistent global filters. |
| Sentiment (FR-5) | 🟡 | Pluggable interface, confidence and ID/EN lexicon fallback exist; no actual LLM/IndoBERT provider and ingestion language is not detected/stored. |
| Emotion (FR-6) | 🟡 | Eight multi-label names exist; no per-label scores and no complete project/date aggregate module. |
| OCEAN (FR-7) | ❌ | No model, aggregate workflow, consent control or UI. |
| Demographics (FR-8) | ❌ | No aggregate gender/demographic model or UI. |
| Author/influencer (FR-9) | 🟡 | Author model and unique-author count exist; influence is not computed end to end and no author propagation graph. |
| Keyword sociograph (FR-10) | ❌ | No co-occurrence graph or drill-through. |
| Buzzer/KOL campaigns (FR-11) | ❌ | No campaign/tracked-account data model or report. |
| Alerts (FR-12) | 🟡 | Project-scoped evaluation, persistence and dashboard retrieval exist; no rule-management UI, delivery, triggering-mention links, or notification audit. |
| Geo (FR-13) | 🟡 | Province/regency aggregation and trend exist; location enrichment is absent and the UI is not a geographic map. |
| Comparison (FR-14) | 🟡 | Legacy two-coalition narrative comparison exists; no arbitrary keyword comparison or saved/shareable views. |
| Digital Health Index (FR-15) | 🟡 | Current summary computes a score; no documented persisted formula/version or history. |
| Infographic builder (FR-16) | ❌ | Missing PNG/PDF generation and tenant branding controls. |
| Command Center (FR-17) | ❌ | War Room is fixed; no 20-widget library, layout editor or per-user persistence. |
| CRM integration (FR-18) | ❌ | No connector, case/status model, inbound sync or extension contract. |
| Correction/tagging (FR-19) | 🟡 | Sentiment correction history and issue taxonomy labeling exist; no emotion correction UI and no author merge. |
| Export (FR-20) | 🟡 | Mention CSV/XLSX works; no chart/report PDF or scheduled recurring email export. |
| Interaction summary (FR-21) | 🟡 | Aggregate engagement is displayed; the schema collapses metrics and does not provide the required per-platform likes/comments/shares/views breakdown. |
| Profile/topic analysis (FR-22) | ❌ / future | Correctly future-scoped by the SRS. |
| Billing/usage (FR-23) | ❌ | A rough per-run Apify estimate exists; no tenant ledger, scraper/AI cost, quotas, hard stops or tenant dashboard. |

### Government-specific modules (FR-24 through FR-29)

| Module | Status | Main remaining gap |
|---|---|---|
| Political actors/camps (FR-24) | 🟡 | Models, matching and ingestion tagging work; no tenant UI or actor/camp trend UI using the new model. |
| Comparative narrative/SoV (FR-25) | 🟡 | Legacy symmetric UI exists; themes are seeded/simple fields rather than topic clustering, new camp service is disconnected, and neutral brief export is absent. |
| CIB detection (FR-26) | 🟡 | Near-duplicate, timing and shared-URL proxy scoring plus human review exist; no account-age/history signal, full amplification network/timeline, or explicit logged external-report workflow. |
| Program/policy tracking (FR-27) | 🟡 | First-class model, ingestion tagging and summary helper exist; no UI, negative-spike/camp correlation or program sub-topic workflow. |
| War Room (FR-28) | 🟡 (strong) | Real summary, 60-second refresh, response log and kiosk styling exist; missing 1-5 minute configurable cadence, designated distribution list and delivered escalation alerts. |
| Governance/neutrality (FR-29) | 🟡 | Explicit permission gate, private-actor allowlist, oversight page, notice, policy record and election freeze exist. Co-approval is not modeled/enforced, permission revoke is not an immediate oversight workflow, audit is not immutable/tenant-scoped, and annual acknowledgment is not enforced as a module-enable precondition. |

### Interfaces and non-functional requirements (§7-8)

| Area | Status | Gap |
|---|---|---|
| REST/GraphQL API | ❌ | Server-rendered web endpoints only; no documented client API/auth/rate limits. |
| WebSocket real-time updates | ❌ | War Room uses full-page 60-second refresh. |
| Signed outbound webhooks | ❌ | No sender/signing/retry implementation. |
| Performance targets | ❌ | No load/latency/throughput tests or evidence for 2s p95, 5-minute ingestion, 2-minute alerts, or 500 mentions/sec. |
| Availability/backups | ❌ | Health endpoint and container restarts exist; no uptime architecture, PITR backup config/runbook, RPO/RTO validation or raw replay. |
| Security | 🟡 | Django security headers, CSRF, TLS-aware settings, RBAC enforcement, project isolation, encrypted runtime secrets and application-immutable audit operations exist. Missing DB-native write-once audit, data-at-rest controls beyond DB assumptions, dedicated secrets manager, vulnerability CI and penetration-test evidence. |
| Compliance/UU PDP | 🟡 | Retention and neutrality concepts exist; no DSAR/breach workflow, legal-basis records, per-source quarterly review, data residency control, tenant compliance acceptance enforcement, or misuse incident process. |
| Maintainability | 🟡 | NLP interface is swappable and Django apps are modular; data-source adapter and independently deployable/versioned service contracts are absent. |
| Accessibility | 🟡 / unverified | Semantic templates and styling exist, but no WCAG 2.1 AA audit or automated accessibility tests. |
| Localization | ❌ | UI strings are hard-coded Indonesian; `USE_I18N` alone does not provide Indonesian/English translation or a language switch. |

## What is genuinely implemented and worth preserving

- A useful dashboard shell with Summary, Feed, Taxonomy, War Room, Narrative, Regional, Coordination, Brief, Configuration and Oversight screens.
- Tenant-scoped mention selectors and automated cross-tenant tests on several analytics paths.
- Four-role profile model, page permission matrix, inactive-user helper and last-admin safeguards.
- Encrypted/masked runtime secret storage and live Apify token validation.
- Working synchronous Apify collection for five platforms with explicit failure semantics, normalization, author linking and deduplication.
- Database-backed scheduling with concurrency claims and failure backoff.
- CSV/XLSX mention exports, retention purge and global collection kill switch.
- Pluggable NLP provider contract, deterministic ID/EN sentiment fallback, confidence, eight emotion labels, taxonomy and correction history.
- CIB scoring with human-only review, War Room response-action logging and alert condition evaluation.
- Political actor/camp/program models, live ingestion tagging, neutrality notice, election freeze and a permission-gated narrative view.
- Strong regression baseline: 383 passing tests.

## Recommended closure sequence

1. **Continue the completed isolation baseline.** Configuration, credentials, runs and alerts are now project-owned and console mutations are guarded. Extend the same invariant to future APIs/search indexes and add database row-level defense where appropriate.
2. **Make Phase 1 collection replayable.** Explicit Apify failures and scheduler backoff are complete; next store source publish time and collection method/version, add raw object storage/durable retry, and provide per-source kill switches.
3. **Finish the SRS configuration contract.** Boolean query AST, platform scoping, preview, per-keyword cadence/input, allow-listed actor/version selection, per-tenant credentials and test jobs.
4. **Finish connecting domain services.** Actor/program tagging and alert project scoping are complete; replace the legacy coalition UI path and connect alert delivery plus notification audit.
5. **Close core product holes before more screens.** Real NLP provider, demographics/OCEAN governance decision, author/keyword graphs, usage quotas, CRM, PDF/scheduled export and configurable command center.
6. **Create an evolutionary service boundary.** Introduce versioned events and a broker for collection → normalization → enrichment → indexing, plus raw storage and OpenSearch. Split deployables only after contracts and observability exist.
7. **Prove non-functionals.** Load tests, accessibility scan, backup/restore drill, vulnerability scanning, DSAR/incident runbooks, trace/metric dashboards and formal SRS acceptance tests keyed by requirement ID.

## Audit limitations

- This is a static code/configuration audit plus the existing automated test suite; no live Apify token, browser accessibility scan, load test, container deployment, backup restore, or penetration test was executed.
- “Partial” means code evidence covers only part of the acceptance condition; it does not imply production readiness.
- The uncommitted landing/onboarding work was included in the current-tree inventory but does not materially close the monitoring SRS gaps above.
