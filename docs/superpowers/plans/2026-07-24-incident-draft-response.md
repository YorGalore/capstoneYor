# Draf Tanggapan Insiden Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a regulation-grounded, human-editable draft public response ("Draf Tanggapan") to the incident detail page, composed deterministically from the incident's numbers and passages retrieved from the regulatory corpus (RAG), always labeled Draf.

**Architecture:** Reuse the proven Daily-Brief grounding pattern. A new deterministic composer `compose_incident_response()` calls `regulatory.retrieve()`, weaves the retrieved `source_ref` + `passage` into an official-style response, and returns both the text and a machine-readable `regulatory_context`. Service functions persist it on the `Incident` and log an `IncidentEvent`. Views mirror the existing `insiden_note` flow. The composer is the single seam where a hosted LLM could later drop in behind the same signature.

**Tech Stack:** Django (Python), SQLite, Django templates, `pytest`/Django `TestCase`.

## Global Constraints

- All AI-composed text MUST carry `DRAFT_BANNER` and be labeled Draf (FR-31.4).
- Every regulatory citation MUST be a passage actually returned by `regulatory.retrieve()`, shown verbatim with its `source_ref` — never fabricated. When retrieval returns nothing, emit an explicit no-fabrication line instead of inventing a citation.
- All write views MUST be tenant-scoped via `_get_incident(request, incident_id)` (404 on foreign tenant), gated by `@require_writer_role`, `@require_POST`, `@require_page("insiden")`, and record the human actor via `_actor(request)` + `record_audit_entry(...)`.
- No external services, no new dependencies. Retrieval stays lexical (`regulatory.retrieve`).
- Follow existing code idiom: composer/service live in `apps/analytics/incidents.py`; `DRAFT_BANNER` is imported from `.briefs`.

---

### Task 1: Model fields + timeline event kind + migration

**Files:**
- Modify: `apps/analytics/models.py` (class `Incident` ~600-628; class `IncidentEvent` ~660-673)
- Create: `apps/analytics/migrations/0018_incident_draft_response.py` (generated)
- Test: `apps/analytics/tests/test_incidents.py`

**Interfaces:**
- Produces: `Incident.draft_response: str`, `Incident.response_regulatory_context: list`, `Incident.response_generated_at: datetime|None`; `IncidentEvent.KIND_RESPONSE_DRAFTED = "response_drafted"`.

- [ ] **Step 1: Write the failing test**

Add to `apps/analytics/tests/test_incidents.py`, in `IncidentModelTest`:

```python
    def test_incident_has_empty_draft_response_by_default(self):
        incident = Incident.objects.create(
            project=self.project, title="Jalan Rusak", severity=Incident.SEVERITY_HIGH,
        )
        self.assertEqual(incident.draft_response, "")
        self.assertEqual(incident.response_regulatory_context, [])
        self.assertIsNone(incident.response_generated_at)

    def test_incident_event_supports_response_drafted_kind(self):
        incident = Incident.objects.create(
            project=self.project, title="Sampah", severity=Incident.SEVERITY_MEDIUM,
        )
        event = IncidentEvent.objects.create(
            incident=incident, kind=IncidentEvent.KIND_RESPONSE_DRAFTED,
            description="Draf tanggapan disusun.", logged_by="Operator Satu",
        )
        self.assertEqual(event.get_kind_display(), "Tanggapan disusun")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test apps.analytics.tests.test_incidents.IncidentModelTest.test_incident_has_empty_draft_response_by_default -v 2`
Expected: FAIL — `AttributeError`/`FieldError` (field does not exist).

- [ ] **Step 3: Add the model fields**

In `apps/analytics/models.py`, `Incident` class, immediately after the `recommendation = models.TextField(blank=True)` line:

```python
    draft_response = models.TextField(blank=True)
    # Retrieved regulatory grounding for the response: [{source_ref, passage, score}, ...]
    # Kept separately from the editable text so the retrieved sources stay visible
    # for verification even after a human edits the wording (FR-31.4).
    response_regulatory_context = models.JSONField(default=list, blank=True)
    response_generated_at = models.DateTimeField(null=True, blank=True)
```

In the `IncidentEvent` class, add the new kind constant with the others and register it in `KIND_CHOICES`:

```python
    KIND_RESPONSE_DRAFTED = "response_drafted"
```

Add to `KIND_CHOICES` (after the `KIND_NOTE` entry):

```python
        (KIND_RESPONSE_DRAFTED, "Tanggapan disusun"),
```

- [ ] **Step 4: Generate the migration**

Run: `python manage.py makemigrations analytics`
Expected: creates `apps/analytics/migrations/0018_incident_draft_response.py` adding three fields and the `kind` choices update.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python manage.py test apps.analytics.tests.test_incidents.IncidentModelTest -v 2`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/analytics/models.py apps/analytics/migrations/0018_incident_draft_response.py apps/analytics/tests/test_incidents.py
git commit -m "Add draft-response fields and timeline kind to Incident"
```

---

### Task 2: Composer + grounding query

**Files:**
- Modify: `apps/analytics/incidents.py` (add functions after `compose_incident_narrative`, ~line 138)
- Test: `apps/analytics/tests/test_incidents.py`

**Interfaces:**
- Consumes: `regulatory.retrieve(query, limit)`, `DRAFT_BANNER`, `Incident.{title, regency, mention_count, negative_pct, assigned_opd, issue, mentions}`.
- Produces:
  - `_response_grounding_query(incident) -> str`
  - `compose_incident_response(incident) -> {"text": str, "regulatory_context": list[dict]}`

- [ ] **Step 1: Write the failing tests**

Add a new test class to `apps/analytics/tests/test_incidents.py`. Import `RegulatoryDocument` at the top of the file:

```python
from apps.governance.models import RegulatoryDocument
```

```python
class ComposeIncidentResponseTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        self.province = Province.objects.create(name="DI Yogyakarta")
        self.regency = Regency.objects.create(province=self.province, name="Sleman")

    def _incident(self, **kwargs):
        defaults = dict(
            project=self.project, title="Jalan Rusak Berlubang",
            regency=self.regency, severity=Incident.SEVERITY_HIGH,
            mention_count=312, negative_pct=95,
        )
        defaults.update(kwargs)
        return Incident.objects.create(**defaults)

    def test_response_cites_retrieved_passage_verbatim_with_source(self):
        RegulatoryDocument.objects.create(
            title="Standar Pelayanan Minimal Jalan",
            source_ref="Permen PU No. 1/2014",
            body="Jalan rusak berlubang yang membahayakan pengguna wajib "
                 "diperbaiki oleh penyelenggara jalan dalam tenggat yang ditetapkan.",
        )
        result = incidents.compose_incident_response(self._incident())
        self.assertIn("Permen PU No. 1/2014", result["text"])
        self.assertIn("wajib", result["text"])
        self.assertTrue(result["regulatory_context"])
        self.assertEqual(
            result["regulatory_context"][0]["source_ref"], "Permen PU No. 1/2014"
        )

    def test_response_carries_draft_banner_and_incident_numbers(self):
        result = incidents.compose_incident_response(self._incident())
        self.assertIn(incidents.DRAFT_BANNER, result["text"])
        self.assertIn("312", result["text"])
        self.assertIn("95", result["text"])
        self.assertIn("Sleman", result["text"])

    def test_response_refuses_to_fabricate_a_citation_when_corpus_is_empty(self):
        result = incidents.compose_incident_response(self._incident())
        self.assertEqual(result["regulatory_context"], [])
        self.assertIn("Tidak ditemukan rujukan regulasi", result["text"])
        self.assertIn("Jangan mengarang", result["text"])

    def test_response_names_assigned_opd_when_present(self):
        opd = OPD.objects.create(
            project=self.project, name="Dinas PU", slug="pu", abbr="PU"
        )
        result = incidents.compose_incident_response(self._incident(assigned_opd=opd))
        self.assertIn("Dinas PU", result["text"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test apps.analytics.tests.test_incidents.ComposeIncidentResponseTest -v 2`
Expected: FAIL — `AttributeError: module 'apps.analytics.incidents' has no attribute 'compose_incident_response'`.

- [ ] **Step 3: Add the import and the composer**

In `apps/analytics/incidents.py`, add near the other imports (after `from .briefs import DRAFT_BANNER`):

```python
from apps.governance import regulatory
```

Add these functions immediately after `compose_incident_narrative` (after its `return {...}` block, ~line 138):

```python
def _response_grounding_query(incident):
    """Build the regulatory-retrieval query from what people actually said, not just
    the incident label — mirrors ``briefs._grounding_query``. An incident titled
    "Jalan Rusak" shares little vocabulary with "Standar Pelayanan Minimal Jalan";
    the underlying conversation and the issue keywords bridge them.
    """
    snippets = list(
        incident.mentions.order_by("-engagement_count")
        .values_list("content_snippet", flat=True)[:10]
    )
    keywords = " ".join(incident.issue.keywords or []) if incident.issue else ""
    return " ".join([incident.title, keywords, *snippets])


def compose_incident_response(incident):
    """Compose a regulation-grounded draft public response for an incident.

    The seam a hosted LLM would replace: accept an incident, return
    ``{"text", "regulatory_context"}``. Deterministic and grounded — every
    regulatory citation is a passage actually retrieved from the corpus, shown
    verbatim with its source, and the whole text carries the draft banner (FR-31.4).
    """
    hits = regulatory.retrieve(_response_grounding_query(incident), limit=3)
    location = incident.regency.name if incident.regency else "wilayah terkait"

    lines = [
        DRAFT_BANNER,
        "",
        f"Menanggapi keresahan warga di **{location}** terkait "
        f"\"{incident.title}\", kami mencatat **{incident.mention_count}** sebutan "
        f"di ruang publik dengan **{incident.negative_pct}%** bersentimen negatif. "
        "Keluhan ini menjadi perhatian kami dan akan ditindaklanjuti.",
        "",
        "### Dasar regulasi",
    ]
    if hits:
        for hit in hits:
            lines.append(f"- **{hit['source_ref']}** — \"{hit['passage']}\"")
    else:
        lines.append(
            "- Tidak ditemukan rujukan regulasi yang relevan pada korpus. "
            "Jangan mengarang kutipan; tambahkan dokumen ke korpus bila diperlukan."
        )

    lines.append("")
    lines.append("### Langkah tindak lanjut")
    if incident.assigned_opd:
        lines.append(
            f"Penanganan ditugaskan kepada **{incident.assigned_opd}** untuk "
            f"verifikasi lapangan di {location} dan perbaikan sesuai kewenangan."
        )
    else:
        lines.append(
            "Penanganan akan ditugaskan kepada OPD yang berwenang untuk verifikasi "
            f"lapangan di {location}."
        )
    lines.append("")
    lines.append(
        "_Draf ini menunggu persetujuan pejabat berwenang sebelum dikeluarkan ke publik._"
    )

    return {
        "text": "\n".join(lines),
        "regulatory_context": [
            {"source_ref": h["source_ref"], "passage": h["passage"], "score": h["score"]}
            for h in hits
        ],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test apps.analytics.tests.test_incidents.ComposeIncidentResponseTest -v 2`
Expected: PASS (all four).

- [ ] **Step 5: Commit**

```bash
git add apps/analytics/incidents.py apps/analytics/tests/test_incidents.py
git commit -m "Compose regulation-grounded incident draft response"
```

---

### Task 3: Service functions (generate / edit)

**Files:**
- Modify: `apps/analytics/incidents.py` (add after `log_note`, ~line 381)
- Test: `apps/analytics/tests/test_incidents.py`

**Interfaces:**
- Consumes: `compose_incident_response(incident)`, `IncidentEvent.KIND_RESPONSE_DRAFTED`, `timezone`.
- Produces:
  - `generate_response(incident, by) -> Incident`
  - `edit_response(incident, text, by) -> Incident`

- [ ] **Step 1: Write the failing tests**

Add a test class to `apps/analytics/tests/test_incidents.py`:

```python
class IncidentResponseServiceTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        self.province = Province.objects.create(name="DI Yogyakarta")
        self.regency = Regency.objects.create(province=self.province, name="Sleman")
        RegulatoryDocument.objects.create(
            title="Standar Pelayanan Minimal Jalan",
            source_ref="Permen PU No. 1/2014",
            body="Jalan rusak berlubang wajib diperbaiki oleh penyelenggara jalan.",
        )
        self.incident = Incident.objects.create(
            project=self.project, title="Jalan Rusak Berlubang", regency=self.regency,
            severity=Incident.SEVERITY_HIGH, mention_count=312, negative_pct=95,
        )

    def test_generate_stores_text_context_and_logs_event(self):
        incidents.generate_response(self.incident, by="Operator Satu")
        self.incident.refresh_from_db()
        self.assertIn("Permen PU No. 1/2014", self.incident.draft_response)
        self.assertTrue(self.incident.response_regulatory_context)
        self.assertIsNotNone(self.incident.response_generated_at)
        event = self.incident.events.filter(
            kind=IncidentEvent.KIND_RESPONSE_DRAFTED
        ).last()
        self.assertEqual(event.logged_by, "Operator Satu")
        self.assertEqual(event.description, "Draf tanggapan disusun.")

    def test_edit_overwrites_text_but_keeps_regulatory_context(self):
        incidents.generate_response(self.incident, by="Operator Satu")
        self.incident.refresh_from_db()
        original_context = self.incident.response_regulatory_context
        incidents.edit_response(self.incident, "Teks suntingan manusia.", by="Operator Satu")
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.draft_response, "Teks suntingan manusia.")
        self.assertEqual(self.incident.response_regulatory_context, original_context)
        self.assertEqual(
            self.incident.events.filter(kind=IncidentEvent.KIND_RESPONSE_DRAFTED).count(),
            2,
        )

    def test_regenerate_overwrites_the_previous_draft(self):
        incidents.edit_response(self.incident, "Draf lama.", by="Operator Satu")
        incidents.generate_response(self.incident, by="Operator Satu")
        self.incident.refresh_from_db()
        self.assertNotEqual(self.incident.draft_response, "Draf lama.")
        self.assertIn("Permen PU No. 1/2014", self.incident.draft_response)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test apps.analytics.tests.test_incidents.IncidentResponseServiceTest -v 2`
Expected: FAIL — `AttributeError: module 'apps.analytics.incidents' has no attribute 'generate_response'`.

- [ ] **Step 3: Add the service functions**

In `apps/analytics/incidents.py`, add after `log_note` (~line 381):

```python
def generate_response(incident, by):
    """Compose and persist a fresh regulation-grounded draft response, replacing any
    prior draft, and log it to the timeline (FR-31.4)."""
    result = compose_incident_response(incident)
    incident.draft_response = result["text"]
    incident.response_regulatory_context = result["regulatory_context"]
    incident.response_generated_at = timezone.now()
    incident.save(update_fields=[
        "draft_response", "response_regulatory_context",
        "response_generated_at", "updated_at",
    ])
    IncidentEvent.objects.create(
        incident=incident,
        kind=IncidentEvent.KIND_RESPONSE_DRAFTED,
        description="Draf tanggapan disusun.",
        logged_by=by,
    )
    return incident


def edit_response(incident, text, by):
    """Persist a human edit to the draft response text. The retrieved regulatory
    context is left untouched so the original sources stay auditable."""
    incident.draft_response = text
    incident.save(update_fields=["draft_response", "updated_at"])
    IncidentEvent.objects.create(
        incident=incident,
        kind=IncidentEvent.KIND_RESPONSE_DRAFTED,
        description="Draf tanggapan disunting.",
        logged_by=by,
    )
    return incident
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test apps.analytics.tests.test_incidents.IncidentResponseServiceTest -v 2`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/analytics/incidents.py apps/analytics/tests/test_incidents.py
git commit -m "Persist and log incident draft-response generate/edit"
```

---

### Task 4: Views + URLs

**Files:**
- Modify: `apps/analytics/views.py` (add after `insiden_note`, ~line 550)
- Modify: `apps/analytics/urls.py` (after the `insiden/.../catat/` line, ~line 34)
- Test: `apps/analytics/tests/test_incident_views.py`

**Interfaces:**
- Consumes: `incidents.generate_response`, `incidents.edit_response`, `_get_incident`, `_actor`, `record_audit_entry`, decorators `require_page`, `require_writer_role`, `require_POST`.
- Produces: URL names `analytics:insiden_response_generate`, `analytics:insiden_response_save`.

- [ ] **Step 1: Write the failing tests**

Add to `apps/analytics/tests/test_incident_views.py`. In `IncidentActionTest` (writer-role class, ~line 95) add:

```python
    def test_generate_response_creates_draft_and_logs_event(self):
        from apps.governance.models import RegulatoryDocument
        RegulatoryDocument.objects.create(
            title="Standar Pelayanan Minimal Jalan",
            source_ref="Permen PU No. 1/2014",
            body="Jalan rusak berlubang wajib diperbaiki oleh penyelenggara jalan.",
        )
        response = self.client.post(
            reverse("analytics:insiden_response_generate", args=[self.incident.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.incident.refresh_from_db()
        self.assertIn("Permen PU No. 1/2014", self.incident.draft_response)
        event = self.incident.events.filter(
            kind=IncidentEvent.KIND_RESPONSE_DRAFTED
        ).last()
        self.assertEqual(event.logged_by, "Operator Satu")

    def test_save_response_persists_edited_text(self):
        response = self.client.post(
            reverse("analytics:insiden_response_save", args=[self.incident.pk]),
            {"draft_response": "Tanggapan resmi hasil suntingan."},
        )
        self.assertEqual(response.status_code, 302)
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.draft_response, "Tanggapan resmi hasil suntingan.")

    def test_save_response_rejects_empty_text(self):
        self.client.post(
            reverse("analytics:insiden_response_save", args=[self.incident.pk]),
            {"draft_response": "   "},
        )
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.draft_response, "")

    def test_generate_response_rejects_another_tenants_incident(self):
        other = Tenant.objects.create(name="Instansi B")
        other_project = Project.objects.create(tenant=other, name="Proyek B")
        foreign = Incident.objects.create(
            project=other_project, title="Milik Tetangga", severity=Incident.SEVERITY_LOW,
        )
        response = self.client.post(
            reverse("analytics:insiden_response_generate", args=[foreign.pk])
        )
        self.assertEqual(response.status_code, 404)
```

In `IncidentWriteAccessTest` (viewer-role class, ~line 185) add:

```python
    def test_viewer_cannot_generate_response(self):
        response = self.client.post(
            reverse("analytics:insiden_response_generate", args=[self.incident.pk])
        )
        self.assertEqual(response.status_code, 403)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test apps.analytics.tests.test_incident_views -v 2`
Expected: FAIL — `NoReverseMatch: Reverse for 'insiden_response_generate' not found`.

- [ ] **Step 3: Add the URLs**

In `apps/analytics/urls.py`, after the `insiden/<int:incident_id>/catat/` path (~line 34):

```python
    path("insiden/<int:incident_id>/tanggapan/susun/", views.insiden_response_generate, name="insiden_response_generate"),
    path("insiden/<int:incident_id>/tanggapan/simpan/", views.insiden_response_save, name="insiden_response_save"),
```

- [ ] **Step 4: Add the views**

In `apps/analytics/views.py`, after `insiden_note` (~line 550):

```python
@require_page("insiden")
@require_writer_role
@require_POST
def insiden_response_generate(request, incident_id):
    incident = _get_incident(request, incident_id)
    actor = _actor(request)
    incidents.generate_response(incident, by=actor)
    record_audit_entry(
        actor_label=actor,
        action="Menyusun draf tanggapan insiden",
        target=incident.title,
    )
    messages.success(
        request,
        "Draf tanggapan disusun. Wajib ditinjau manusia sebelum dikeluarkan ke publik.",
    )
    return redirect("analytics:insiden_detail", incident_id=incident.pk)


@require_page("insiden")
@require_writer_role
@require_POST
def insiden_response_save(request, incident_id):
    incident = _get_incident(request, incident_id)
    text = (request.POST.get("draft_response") or "").strip()
    if not text:
        messages.error(request, "Teks tanggapan tidak boleh kosong.")
    else:
        actor = _actor(request)
        incidents.edit_response(incident, text, by=actor)
        record_audit_entry(
            actor_label=actor,
            action="Menyunting draf tanggapan insiden",
            target=incident.title,
        )
        messages.success(request, "Suntingan tanggapan disimpan.")
    return redirect("analytics:insiden_detail", incident_id=incident.pk)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python manage.py test apps.analytics.tests.test_incident_views -v 2`
Expected: PASS (all new tests + existing suite green).

- [ ] **Step 6: Commit**

```bash
git add apps/analytics/views.py apps/analytics/urls.py apps/analytics/tests/test_incident_views.py
git commit -m "Add incident draft-response generate/save views and routes"
```

---

### Task 5: Template block on incident detail

**Files:**
- Modify: `templates/analytics/insiden_detail.html` (insert after the "Rekomendasi" block ending at line 74, before the "Lini Masa" block at line 76)
- Test: `apps/analytics/tests/test_incident_views.py`

**Interfaces:**
- Consumes: template context `incident` (with `draft_response`, `response_regulatory_context`, `response_generated_at`); URL names `analytics:insiden_response_generate`, `analytics:insiden_response_save`; filter `incident_body` (already loaded via `{% load analytics_extras static %}`).

- [ ] **Step 1: Write the failing tests**

Add to `apps/analytics/tests/test_incident_views.py`, in `IncidentActionTest`:

```python
    def test_detail_shows_compose_button_when_no_draft_response(self):
        url = reverse("analytics:insiden_detail", args=[self.incident.pk])
        response = self.client.get(url)
        self.assertContains(response, "Susun draf tanggapan")

    def test_detail_renders_existing_draft_response_and_sources(self):
        from apps.governance.models import RegulatoryDocument
        RegulatoryDocument.objects.create(
            title="Standar Pelayanan Minimal Jalan",
            source_ref="Permen PU No. 1/2014",
            body="Jalan rusak berlubang wajib diperbaiki oleh penyelenggara jalan.",
        )
        incidents.generate_response(self.incident, by="Operator Satu")
        url = reverse("analytics:insiden_detail", args=[self.incident.pk])
        response = self.client.get(url)
        self.assertContains(response, "Draf Tanggapan")
        self.assertContains(response, "Permen PU No. 1/2014")
        self.assertContains(response, "Susun ulang")
```

Ensure `from apps.analytics import incidents` is imported at the top of the test module (add it if absent).

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test apps.analytics.tests.test_incident_views.IncidentActionTest.test_detail_shows_compose_button_when_no_draft_response apps.analytics.tests.test_incident_views.IncidentActionTest.test_detail_renders_existing_draft_response_and_sources -v 2`
Expected: FAIL — `assertContains` cannot find "Susun draf tanggapan" / "Draf Tanggapan".

- [ ] **Step 3: Add the template block**

In `templates/analytics/insiden_detail.html`, insert between the closing `</div>` of the Rekomendasi block (line 74) and the "Lini Masa" block (line 76):

```html
    <div class="incident-narrative-block incident-response-block">
      <div class="incident-narrative-head"><h3>Draf Tanggapan</h3>{% if incident.response_generated_at %}<span class="incident-draft-tag">Draf</span>{% endif %}</div>
      {% if incident.response_generated_at %}
        <div class="incident-draft-banner">
          <span class="icon">⚠️</span>
          <span class="incident-draft-banner-text"><strong>Draf — dihasilkan AI, menunggu tinjauan manusia.</strong> Kutipan regulasi harus diverifikasi terhadap sumber aslinya sebelum tanggapan dikeluarkan ke publik.</span>
        </div>
        <form method="post" action="{% url 'analytics:insiden_response_save' incident.pk %}" class="incident-response-form">
          {% csrf_token %}
          <textarea name="draft_response" rows="12" class="incident-response-textarea">{{ incident.draft_response }}</textarea>
          <div class="incident-response-actions">
            <button type="submit" class="pantau-btn-dark">Simpan suntingan</button>
          </div>
        </form>
        {% if incident.response_regulatory_context %}
        <div class="incident-response-sources">
          <h4>Rujukan terambil (verifikasi terhadap sumber asli)</h4>
          <ul>
            {% for ref in incident.response_regulatory_context %}
              <li><strong>{{ ref.source_ref }}</strong> — “{{ ref.passage }}”</li>
            {% endfor %}
          </ul>
        </div>
        {% endif %}
        <form method="post" action="{% url 'analytics:insiden_response_generate' incident.pk %}" class="incident-response-regenerate">
          {% csrf_token %}
          <button type="submit" class="pantau-btn-outline">Susun ulang</button>
          <span class="incident-action-note">Disusun {{ incident.response_generated_at|date:"d M Y · H:i" }} WIB</span>
        </form>
      {% else %}
        <p class="incident-action-note">Belum ada draf tanggapan. Sistem akan menyusun tanggapan berdasar data insiden dan rujukan regulasi terambil; hasilnya wajib ditinjau manusia.</p>
        <form method="post" action="{% url 'analytics:insiden_response_generate' incident.pk %}">
          {% csrf_token %}
          <button type="submit" class="pantau-btn-dark">Susun draf tanggapan</button>
        </form>
      {% endif %}
    </div>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test apps.analytics.tests.test_incident_views -v 2`
Expected: PASS.

- [ ] **Step 5: Full regression run**

Run: `python manage.py test apps.analytics -v 1`
Expected: entire analytics suite green.

- [ ] **Step 6: Commit**

```bash
git add templates/analytics/insiden_detail.html apps/analytics/tests/test_incident_views.py
git commit -m "Render incident draft-response with sources and edit form"
```

---

## Notes for the implementer

- **Why store `response_regulatory_context` separately from the text** even though the composed text already embeds a "Dasar regulasi" section: the text is human-editable and an editor can remove or reword a citation. The separate JSON is the immutable record of what retrieval actually returned, rendered under "Rujukan terambil" so the sources stay independently verifiable (FR-31.4) — the same reason `DailyBriefIssue` keeps `regulatory_context` alongside its composed `content`.
- **`incident_body` filter** already renders the Markdown-ish `**bold**`, `### headings`, and `- lists` the composer emits; no new template filter is needed. The editable `<textarea>` intentionally shows the raw Markdown source so an editor edits the same text the composer produced.
- **Styling** (`incident-response-*` classes) is optional polish; the tasks above pass without new CSS. If adding CSS, put it in `static/core/css/base.css` next to the existing `incident-narrative-*` rules — not required by any test.
```
