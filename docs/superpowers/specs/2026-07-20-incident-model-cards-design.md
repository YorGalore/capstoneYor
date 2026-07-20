# Incident Model + Cards — Design

**Date:** 2026-07-20
**Status:** Approved (pending spec review)
**Slice:** 1 of a larger "Command Center + AI Copilot" vision

## Context

PANTAU today answers "what is being said?" through mention-level pages (Umpan, Taksonomi,
Regional, Sosiograf) and two aggregate surfaces (Ringkasan, Brief Harian). It does not answer
the three questions a Bupati or Kepala Dinas actually has:

1. What is happening?
2. How serious is it?
3. What should I do?

The gap is a missing object. Conversation is currently modeled either as individual `Mention`s
or as a `PoliticalIssue` (a political-narrative war-room event). Neither is a *decision object*
for a citizen-service problem. This slice introduces one: the **Incident**.

### Scope of the larger vision

The full vision spans roughly eight subsystems: Executive Dashboard, Incident model, incident
cards + detail, interactive kabupaten map, event timeline, AI Copilot chat, notification/crisis
center, and persona dashboards including a Sekda KPI board. Specifying all of it at once would
produce a plan too large to execute well. Each subsystem gets its own spec → plan → build cycle.

**This spec covers the Incident model and cards only.** It is first because incident data is
what the cards, detail view, timeline, Copilot, and KPI board all read from; without it the
remaining surfaces are cosmetic.

## Concept and boundaries

An **Incident** is a citizen-service problem surfaced by social conversation (jalan rusak,
sampah, banjir) that leadership must decide on and act on. It aggregates mentions into one
object carrying urgency, location, composed narrative, an assigned OPD, and a lifecycle.

It is deliberately distinct from the two existing issue types, both of which remain unchanged:

| Type | Meaning | Relationship to Incident |
|------|---------|--------------------------|
| `PoliticalIssue` | Political-narrative war-room event, neutrality-gated | Untouched. Separate concern. |
| taxonomy `Issue` | Classification leaf applied to individual mentions | **Reused** as the clustering key |

Incidents cluster on (taxonomy `Issue` × `Regency`) — the same geo unit `Mention` uses.

## Data model

New models in `apps/analytics/models.py`.

### `OPD`

A per-project organizational unit (Dinas).

- `project` FK → `Project`
- `name`, `slug`, `abbr` (e.g. "PU", "DLH", "Dishub", "Dinkes")
- `is_active`

Seeded for the demo tenants (Sleman / Kulon Progo). Introduced in this slice so the later
Sekda KPI-per-OPD board is unblocked, but **no KPI view is built here**.

### `Incident`

- `project` FK, `title`
- `issue` FK → taxonomy `Issue`, nullable
- `regency` FK → `Regency`, nullable (location)
- `severity`: `critical | high | medium | low`
- `status`: `open | assigned | in_progress | resolved | closed`
- `assigned_opd` FK → `OPD`, nullable
- `mention_count`, `negative_pct` — denormalized snapshot, refreshed on recompute
- `ai_summary`, `root_cause`, `impact`, `recommendation` — composed text, draft-labeled
- `is_confirmed` — a candidate becomes a real incident when an operator promotes it
- `mentions` — plain `ManyToManyField` to `Mention`
- `created_at`, `updated_at`, `first_seen_at`, `closed_at`

Tenant isolation is mandatory: every incident is project-scoped, and all querysets go through
`scope_to_tenant`. This mirrors the fix applied to `PoliticalIssue` in commit `1ad5abf`.

### `IncidentEvent`

The timeline. Shape mirrors the existing `ResponseAction`.

- `incident` FK
- `kind`: `detected | volume_update | assigned | status_change | action_logged | note`
- `description`, `occurred_at`, `logged_by`

Auto-appended on detection, assignment, and status change; also manually loggable.

### Resolved design questions

Three sub-questions were raised at design review and resolved to the recommended defaults.
They are recorded here so they can be revisited at spec review:

1. **Related posts use a plain M2M**, not a through-table. The clustering rule already explains
   membership, so a `linked_at` / reason column earns nothing yet. Revisit if incidents ever
   need manual add/remove of individual mentions with provenance.
2. **Lifecycle is the full five states** (`open → assigned → in_progress → resolved → closed`)
   rather than a simplified three. Assignment and resolution are distinct real-world moments,
   and the Sekda KPI board will need to distinguish "assigned but untouched" from "being worked".
3. **Candidates and confirmed incidents share one board**, visually separated, rather than
   living in a separate operator-only review queue. Simpler to build and keeps the operator's
   work visible in context. If leadership personas later need a candidate-free view, that is a
   filter, not a second page.

## Detection and composition

New module `apps/analytics/incidents.py`, structured to mirror `briefs.py`.

- `shortlist_candidates(project, window)` — groups `IssueLabel` × `Regency` over a time window,
  applies volume and negativity thresholds, returns candidate dicts. Threshold constants follow
  the `MIN_MENTIONS` / `MIN_NEGATIVE_PCT` pattern already established in `briefs.py`.
- `compose_incident_narrative(candidate) -> dict` — the **swappable seam**. Returns
  `{ai_summary, root_cause, impact, recommendation}`.
- `_compose(candidate)` — the default deterministic implementation behind that seam.
- `severity_for(negative_pct, volume, coordinated)` — reuses `regulatory.classify_risk`.
- `refresh_candidates(project)` — upserts unconfirmed candidate incidents. **Never overwrites
  operator edits on confirmed incidents.**
- `promote(incident, by)`, `assign(incident, opd, by)`, `set_status(incident, status, by)` —
  each appends an `IncidentEvent`.

### Generation posture

Composition is **deterministic and grounded**, matching the existing Daily Brief engine. It
states measured values (mention count, negative percentage, location, time window) and quotes
the highest-engagement snippets verbatim rather than inventing narrative.

All four composed fields carry the mandatory draft banner already used by `briefs.py`:

```
**[DRAF — DIHASILKAN AI, MENUNGGU TINJAUAN MANUSIA]**
```

This preserves the platform's current posture: no hosted LLM dependency, nothing auto-published
without human review. A hosted LLM may later replace `compose_incident_narrative` behind the
same signature; the draft banner and visible source data are required either way (FR-31.4).

**Recommendations are advisory, never automated action.** The system proposes assigning an OPD;
a human performs the assignment.

## Views and URLs

New page slug `insiden`, added to `apps/core/permissions.py` `PAGES` and included in
`DASHBOARD_PAGES` so Analyst and Viewer roles reach it by default.

| Route | Purpose |
|-------|---------|
| `insiden/` | Incident board — cards grouped by severity |
| `insiden/<id>/` | Incident detail |
| `insiden/<id>/promote/` | POST — promote candidate to confirmed |
| `insiden/<id>/tugaskan/` | POST — assign OPD |
| `insiden/<id>/status/` | POST — change status |
| `insiden/<id>/catat/` | POST — log a timeline event |
| `insiden/hitung-ulang/` | POST — recompute candidates |

Board filters, kept deliberately few: time window (Hari ini / 7 hari / 30 hari), OPD, severity.

Detail page order reflects the drill-down principle — composed narrative first, related raw
posts last and collapsed, because only operators need them.

Selectors go in `apps/analytics/selectors.py`. All querysets tenant-scoped.

## UI

Follows existing PANTAU conventions: templates modeled on `war_room.html` and `regional.html`,
styling extending `static/core/css/base.css`.

- `templates/analytics/insiden.html`
- `templates/analytics/insiden_detail.html`
- Nav item "Insiden" in `templates/core/_sidebar.html`, permission-gated like existing entries
- Incident-card CSS: icon, title, severity chip, location, mention count, negative %, assigned OPD

## Testing

Following the existing test style in `apps/analytics/tests/`.

`test_incidents.py`
- Detection respects volume and negativity thresholds
- `refresh_candidates` is idempotent and does not overwrite confirmed incidents
- `promote` / `assign` / `set_status` each append the correct `IncidentEvent`
- Invalid status transitions are rejected
- Composed fields carry the draft banner
- Tenant isolation: one project's incidents are invisible to another

`test_incident_views.py`
- Permission gating honours the matrix
- Board renders candidates and confirmed incidents distinctly
- Each POST action performs its change and redirects
- POST actions reject cross-tenant incident IDs

## Out of scope

Deferred to later slices, each with its own spec:

- Executive Dashboard shell ("situasi daerah hari ini")
- Interactive kabupaten choropleth map
- AI Copilot chat
- Persona role mapping (Bupati / Sekda / Kepala Dinas / Operator)
- Sekda KPI-per-OPD board
- Notification / crisis center UI

## Success criteria

1. An operator can see auto-detected incident candidates without reading the mention feed.
2. An operator can promote a candidate, assign it to an OPD, and move it through its lifecycle.
3. Every incident carries a grounded, draft-labeled narrative answering what/how serious/what to do.
4. Every state change is recorded on an auditable timeline.
5. No incident leaks across tenants.
