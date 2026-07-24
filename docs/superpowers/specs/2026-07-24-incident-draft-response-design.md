# Draf Tanggapan Insiden — Desain

**Tanggal:** 2026-07-24
**Halaman:** `/insiden/<id>/` (detail insiden)
**Terkait:** FR-31 (grounding regulasi, anti-halusinasi), FR-31.4 (label draf, sumber terlihat)

## Masalah

Halaman detail insiden sudah menampilkan empat blok narasi AI (Ringkasan, Dugaan
Penyebab, Dampak, Rekomendasi), tetapi tidak ada satupun yang berlandaskan
regulasi, dan tidak ada artefak **tanggapan** — teks respons resmi yang bisa
dikeluarkan OPD/Pemda ke publik.

Brief harian (`apps/analytics/briefs.py`) sudah membuktikan pola yang benar:
setiap isu memanggil `regulatory.retrieve()` terhadap korpus `RegulatoryDocument`
(UU/Perda/SOP), menyimpan `regulatory_context`, dan menampilkan blok "Dasar
regulasi" berisi `source_ref` + `passage` verbatim, selalu berlabel draf. Insiden
belum memakai mesin ini.

Permintaan: saat menyusun draf tanggapan di halaman insiden, teks harus
**berlandaskan data via RAG** sehingga ada **rujukan ke undang-undang / regulasi**.

## Prinsip

- Komposer **deterministik + RAG**, mengikuti pola proyek. Tanpa layanan
  eksternal; tidak bisa mengarang kutipan.
- Setiap kutipan regulasi selalu **terlihat** beserta sumbernya (FR-31.4).
- Teks selalu **berlabel Draf** — tidak pernah terbit tanpa tinjauan manusia.
- `compose_incident_response()` adalah **seam** tempat LLM ter-host bisa
  menggantikan komposer di masa depan tanpa mengubah pemanggil.

## 1. Model

### `Incident` (apps/analytics/models.py) — migrasi baru

```python
draft_response = models.TextField(blank=True)
# [{source_ref, passage, score}, ...] — sama seperti DailyBriefIssue.regulatory_context
response_regulatory_context = models.JSONField(default=list, blank=True)
response_generated_at = models.DateTimeField(null=True, blank=True)
```

- `draft_response` kosong / `response_generated_at is None` → belum ada draf.
- Suntingan manusia menimpa `draft_response`; `response_regulatory_context`
  tidak berubah oleh suntingan (grounding tetap dapat ditelusuri).

### `IncidentEvent` — tambah satu kind

```python
KIND_RESPONSE_DRAFTED = "response_drafted"  # label: "Tanggapan disusun"
```

Dipakai untuk pembuatan maupun penyuntingan draf; deskripsi event yang
membedakan ("Draf tanggapan disusun." / "Draf tanggapan disunting.").

## 2. Komposer (apps/analytics/incidents.py)

### `_response_grounding_query(incident) -> str`

Meniru `briefs._grounding_query`: rakit query dari `incident.title` +
keyword `incident.issue.keywords` + kutipan `content_snippet` dari
`incident.mentions` teratas (urut `-engagement_count`, ambil ~10). Alasan sama
seperti brief: label isu dan judul regulasi sering tak berbagi kosakata;
percakapan warga-lah yang menjembatani.

### `compose_incident_response(incident) -> dict`

Kontrak: terima `incident`, kembalikan `{"text": str, "regulatory_context": list}`.

1. `hits = regulatory.retrieve(_response_grounding_query(incident), limit=3)`
2. Susun `text` (Markdown) secara deterministik:
   - `DRAFT_BANNER`
   - **Pembuka**: mengakui keresahan warga di `{lokasi}` terkait `"{judul}"`,
     menyebut `{mention_count}` sebutan dengan `{negative_pct}%` negatif.
   - **Dasar regulasi**: untuk tiap hit → `- **{source_ref}** — "{passage}"`
     (verbatim). Bila `hits` kosong → satu baris eksplisit: tidak ditemukan
     rujukan regulasi pada korpus, **jangan mengarang kutipan**, tambahkan
     dokumen ke korpus bila perlu.
   - **Langkah tindak lanjut**: menyebut `{assigned_opd}` bila ada; bila belum
     ditugaskan, kalimat netral bahwa penanganan akan ditugaskan ke OPD
     berwenang.
   - **Penutup**: pernyataan bahwa ini draf, menunggu persetujuan pejabat
     berwenang sebelum dikeluarkan ke publik.
3. `regulatory_context = [{"source_ref", "passage", "score"} for h in hits]`

## 3. Service (apps/analytics/incidents.py)

### `generate_response(incident, by) -> Incident`

- `result = compose_incident_response(incident)`
- Simpan `draft_response`, `response_regulatory_context`,
  `response_generated_at = timezone.now()` (`update_fields`).
- `IncidentEvent(kind=KIND_RESPONSE_DRAFTED, description="Draf tanggapan disusun.", logged_by=by)`
- Regenerasi menimpa draf lama (tidak menambah versi).

### `edit_response(incident, text, by) -> Incident`

- Simpan `draft_response = text` (`update_fields`); `regulatory_context` tetap.
- `IncidentEvent(kind=KIND_RESPONSE_DRAFTED, description="Draf tanggapan disunting.", logged_by=by)`

## 4. Views + URLs (apps/analytics/views.py, urls.py)

Pola identik dengan `insiden_note`: `@require_page("insiden")`,
`@require_writer_role`, `@require_POST`, tenant-scoped via `_get_incident`,
aktor via `_actor`, `record_audit_entry`, redirect ke `insiden_detail`.

| URL | View | Aksi |
|-----|------|------|
| `insiden/<int:incident_id>/tanggapan/susun/` | `insiden_response_generate` | `incidents.generate_response` |
| `insiden/<int:incident_id>/tanggapan/simpan/` | `insiden_response_save` | `incidents.edit_response` (tolak teks kosong) |

## 5. Template (templates/analytics/insiden_detail.html)

Blok baru pada kolom narasi utama, setelah "Rekomendasi", sebelum "Lini Masa".

- **Belum ada draf** (`response_generated_at` None): tombol POST
  **"Susun draf tanggapan"** → `insiden_response_generate`.
- **Ada draf**:
  - banner draf + judul blok "Draf Tanggapan" + tag Draf
  - teks via filter `incident_body` (Markdown → HTML, seperti blok lain)
  - blok **Dasar regulasi**: loop `incident.response_regulatory_context`,
    `source_ref` tebal + `passage` (visual sama seperti brief)
  - `<form>` dengan `<textarea>` berisi `draft_response` → tombol **Simpan**
    (`insiden_response_save`)
  - tombol **Susun ulang** → `insiden_response_generate`
  - baris jejak: "Disusun {{ response_generated_at }}"

## 6. Tests

**Komposer** (`test_incidents.py`)
- Mengutip `passage` yang diambil secara verbatim beserta `source_ref`.
- `retrieve` kosong → memuat baris anti-karang, bukan kutipan palsu.
- Teks membawa `DRAFT_BANNER`.
- Teks memuat angka insiden (mention_count, negative_pct) dan lokasi.
- `regulatory_context` cocok dengan hits.

**Service**
- `generate_response` menyimpan tiga field + mencatat `IncidentEvent`
  `response_drafted`.
- `edit_response` menimpa teks, **mempertahankan** `regulatory_context`,
  mencatat event.
- Regenerasi menimpa draf sebelumnya.

**View** (`test_incident_views.py`)
- Butuh writer role (viewer ditolak).
- Tenant scoping: tidak bisa menyusun tanggapan untuk insiden tenant lain (404).
- `record_audit_entry` terpanggil.
- Teks kosong pada simpan → pesan error, draf tak berubah.

## Di luar cakupan (YAGNI)

- Integrasi LLM ter-host (seam disiapkan, tapi tidak diimplementasi).
- Versioning / riwayat draf.
- Alur approval terpisah — draf tetap draf sampai manusia menyalin/mengeluarkan.
- Indeks vektor — `regulatory.retrieve()` leksikal tetap dipakai.
