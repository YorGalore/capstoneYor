"""Incident detection and composition.

An Incident is a citizen-service problem (jalan rusak, sampah, banjir) aggregated
from conversation so leadership can answer three questions: what is happening, how
serious is it, and what should be done.

Two properties are inherited deliberately from the Daily Brief engine (briefs.py):

* Narrative is **deterministic and grounded** — it states measured numbers and
  quotes source snippets verbatim rather than inventing prose. A hosted LLM can
  replace ``compose_incident_narrative`` behind the same signature later.
* Output is always **draft-labeled**, pending human review (FR-31.4).

Recommendations are advisory. The composer proposes an OPD; a human assigns it.
"""
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.governance import regulatory
from .briefs import DRAFT_BANNER
from .models import Incident, IncidentEvent, IssueLabel, Mention

# A cluster is only worth raising to leadership if it carries real signal. Mirrors
# the thresholds the brief engine uses for the same judgement.
MIN_MENTIONS = 5
MIN_NEGATIVE_PCT = 40

# How many source snippets to quote in the summary.
MAX_SNIPPETS = 3

# Sentiment thresholds for each severity tier.
CRITICAL_NEGATIVE_PCT = 70
HIGH_NEGATIVE_PCT = 50
MEDIUM_NEGATIVE_PCT = 30
# A volume change this large is a surge rather than drift.
SURGE_PCT = 200
# A cluster with no prior activity has no measurable change, so it only counts as
# a surge once it is substantially bigger than the detection floor. Without this,
# every cluster on a first-ever run looks like a surge — which would mark the whole
# board Critical on day one and drain the tier of meaning.
NEW_CLUSTER_SURGE_MENTIONS = MIN_MENTIONS * 3


def severity_for(negative_pct, volume_change_pct=0, coordinated=False):
    """Map measured signal onto an incident severity.

    Deliberately *not* delegated to ``regulatory.classify_risk``. That classifier
    needs a combined score of 4 to reach High, and sentiment alone contributes at
    most 2 — so an incident detected from negativity could never exceed Medium and
    the board would be unable to distinguish a grumble from a crisis.

    Negativity therefore sets the tier, and a volume surge or coordinated activity
    escalates it. Coordinated inauthentic activity lifts an item above Low even
    when sentiment looks calm, matching the reasoning in ``classify_risk``: that
    combination is what a manufactured narrative looks like early on.

    In the Medium band specifically, only a genuine volume ``surge`` escalates to
    High. ``coordinated`` alone is *why* a calm cluster reaches this branch at all
    (see above) — folding it into the escalation trigger too would double-count
    it and push a merely-coordinated-but-calm cluster straight to High, which is
    a bigger jump than the signal (coordination without volume or negativity)
    warrants.
    """
    surge = volume_change_pct >= SURGE_PCT
    escalating = surge or coordinated

    if negative_pct >= CRITICAL_NEGATIVE_PCT:
        return Incident.SEVERITY_CRITICAL if escalating else Incident.SEVERITY_HIGH
    if negative_pct >= HIGH_NEGATIVE_PCT:
        return Incident.SEVERITY_HIGH if escalating else Incident.SEVERITY_MEDIUM
    if negative_pct >= MEDIUM_NEGATIVE_PCT or coordinated:
        return Incident.SEVERITY_HIGH if surge else Incident.SEVERITY_MEDIUM
    return Incident.SEVERITY_LOW


def _location(candidate):
    return candidate.get("regency_name") or "wilayah yang belum teridentifikasi"


# How many reasons to name before the list stops being a summary.
MAX_ROOT_CAUSE_DRIVERS = 3


def driver_breakdown(mention_ids, limit=MAX_ROOT_CAUSE_DRIVERS):
    """The dominant reasons behind a set of mentions, with their shares.

    Kept separate from the narrative composer so the escalation engine and the
    incident detail can both read the same measured breakdown rather than parsing
    it back out of prose.
    """
    from .models import MentionDriver

    if not mention_ids:
        return []
    rows = (
        MentionDriver.objects.filter(mention_id__in=mention_ids)
        .values("driver__name")
        .annotate(n=Count("mention_id", distinct=True))
        .order_by("-n")[:limit]
    )
    labelled = (
        MentionDriver.objects.filter(mention_id__in=mention_ids)
        .values("mention_id").distinct().count()
    )
    return [
        {
            "name": row["driver__name"],
            "count": row["n"],
            "pct": round((row["n"] / labelled) * 100) if labelled else 0,
        }
        for row in rows
    ]


def _compose_root_cause(candidate, snippets):
    """State the measured reasons behind an incident, or say plainly that none
    were measured.

    Previously this always emitted the same "penyebab belum diverifikasi"
    placeholder regardless of what the data showed. Now it reports the driver
    labels actually attached to the incident's mentions — while keeping the
    instruction to verify in the field, because a clustered complaint is evidence
    of what people *say* the cause is, not proof of the cause.
    """
    breakdown = driver_breakdown(candidate.get("mention_ids") or [])
    if breakdown:
        lines = [
            DRAFT_BANNER,
            "",
            "Alasan keluhan yang terukur dari percakapan warga:",
        ]
        for driver in breakdown:
            lines.append(
                f"- **{driver['name']}** — {driver['pct']}% dari keluhan berlabel "
                f"({driver['count']} sebutan)"
            )
        lines.append("")
        lines.append(
            "Angka di atas menggambarkan apa yang warga sampaikan, bukan hasil "
            "verifikasi teknis. Konfirmasi lapangan oleh OPD terkait tetap wajib "
            "sebelum penyebab dinyatakan resmi."
        )
        return "\n".join(lines)

    if snippets:
        return (
            f"{DRAFT_BANNER}\n\n"
            "Penyebab belum diverifikasi dan belum ada label alasan yang terukur. "
            "Indikasi awal berdasarkan kutipan warga di atas perlu dikonfirmasi "
            "melalui pemeriksaan lapangan oleh OPD terkait."
        )
    return (
        f"{DRAFT_BANNER}\n\n"
        "Penyebab belum dapat disimpulkan: tidak tersedia kutipan percakapan "
        "yang memadai. Jangan mengarang penyebab; lakukan verifikasi lapangan."
    )


def compose_incident_narrative(candidate):
    """Compose the four narrative fields for one incident candidate.

    This is the seam a hosted LLM would replace. Its contract: accept a candidate
    dict, return the four fields, each carrying the draft banner.
    """
    total = candidate["total"]
    negative_pct = candidate["negative_pct"]
    location = _location(candidate)
    snippets = candidate.get("snippets") or []

    summary_lines = [
        DRAFT_BANNER,
        "",
        f"Terdapat **{total}** sebutan terkait \"{candidate['title']}\" "
        f"di **{location}**, dengan **{negative_pct}%** bersentimen negatif.",
    ]
    if snippets:
        summary_lines.append("")
        summary_lines.append("Kutipan percakapan dengan keterlibatan tertinggi:")
        for snippet in snippets[:MAX_SNIPPETS]:
            summary_lines.append(f"- \"{snippet}\"")

    root_cause = _compose_root_cause(candidate, snippets)

    impact = (
        f"{DRAFT_BANNER}\n\n"
        f"Terpapar pada **{total}** percakapan publik di {location}. "
        f"Proporsi negatif **{negative_pct}%** menunjukkan tingkat ketidakpuasan "
        "warga yang perlu direspons."
    )

    recommendation = (
        f"{DRAFT_BANNER}\n\n"
        f"Disarankan menugaskan OPD yang membidangi \"{candidate['title']}\" untuk "
        f"verifikasi lapangan di {location}, lalu memperbarui status insiden ini "
        "setelah penanganan dimulai. Penugasan dilakukan oleh pejabat berwenang, "
        "bukan secara otomatis oleh sistem."
    )

    return {
        "ai_summary": "\n".join(summary_lines),
        "root_cause": root_cause,
        "impact": impact,
        "recommendation": recommendation,
    }


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
            f"Penanganan ditugaskan kepada **{incident.assigned_opd.name}** untuk "
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


# How far back detection looks when no explicit window is given.
DEFAULT_WINDOW_DAYS = 7


def shortlist_candidates(project, since=None, window_days=DEFAULT_WINDOW_DAYS):
    """Group recent labeled conversation into candidate incidents.

    Clusters on (taxonomy Issue x Regency): the same complaint in two different
    kecamatan is two incidents, because they are assigned and resolved separately.
    """
    if since is None:
        since = timezone.now() - timedelta(days=window_days)

    now = timezone.now()
    # The comparison window for volume_change_pct: the same length of time
    # immediately preceding `since`, so "current" and "previous" are apples to
    # apples regardless of what window_days the caller chose.
    window_length = now - since
    previous_since = since - window_length

    rows = (
        IssueLabel.objects.filter(
            mention__project=project, mention__posted_at__gte=since
        )
        .values("issue__id", "issue__name", "mention__regency__id", "mention__regency__name")
        .annotate(
            total=Count("mention__id"),
            negative=Count(
                "mention__id", filter=Q(mention__sentiment=Mention.SENTIMENT_NEGATIVE)
            ),
        )
        .order_by("-negative", "-total")
    )

    candidates = []
    for row in rows:
        total = row["total"]
        negative_pct = round((row["negative"] / total) * 100) if total else 0
        if total < MIN_MENTIONS or negative_pct < MIN_NEGATIVE_PCT:
            continue

        mentions = list(
            Mention.objects.filter(
                project=project,
                posted_at__gte=since,
                issue_label__issue_id=row["issue__id"],
                regency_id=row["mention__regency__id"],
            )
            .order_by("-engagement_count")
            .values_list("id", "content_snippet")
        )

        previous_total = IssueLabel.objects.filter(
            mention__project=project,
            mention__posted_at__gte=previous_since,
            mention__posted_at__lt=since,
            issue__id=row["issue__id"],
            mention__regency_id=row["mention__regency__id"],
        ).count()
        if previous_total > 0:
            volume_change_pct = ((total - previous_total) / previous_total) * 100
        elif total >= NEW_CLUSTER_SURGE_MENTIONS:
            # No prior window to divide by. A cluster this much larger than the
            # detection floor appearing from nothing is a genuine spike — a flood
            # that draws hundreds of posts within hours has no yesterday.
            volume_change_pct = float(SURGE_PCT)
        else:
            # A handful of posts from nothing is a new grievance, not a crisis. It
            # enters at the tier its sentiment earns and escalates only if it grows.
            volume_change_pct = 0.0

        candidates.append({
            "title": row["issue__name"],
            "issue_id": row["issue__id"],
            "regency_id": row["mention__regency__id"],
            "regency_name": row["mention__regency__name"] or "",
            "total": total,
            "negative_pct": negative_pct,
            "volume_change_pct": volume_change_pct,
            "snippets": [snippet for _id, snippet in mentions[:MAX_SNIPPETS]],
            "mention_ids": [mention_id for mention_id, _snippet in mentions],
        })
    return candidates


@transaction.atomic
def refresh_candidates(project, since=None, window_days=DEFAULT_WINDOW_DAYS):
    """Upsert candidate incidents for a project, returning the touched incidents.

    A confirmed incident is left alone entirely: once an operator has promoted and
    edited it, re-running detection must not clobber their judgement with a fresh
    machine composition. The same protection extends to any incident an operator
    has already acted on even before confirming it: `assign()` advances a
    still-unconfirmed incident to `assigned`, and the detail view lets an operator
    work a candidate (assign/status/note) ahead of confirmation. Skipping only
    `is_confirmed` would let a later refresh overwrite that work — title,
    severity, mention_count, negative_pct, narrative, and the mentions M2M — with
    a silent downgrade and no timeline event. So the guard is: skip when
    confirmed OR when the incident has moved out of `open`.
    """
    touched = []
    for candidate in shortlist_candidates(project, since=since, window_days=window_days):
        incident = Incident.objects.filter(
            project=project,
            issue_id=candidate["issue_id"],
            regency_id=candidate["regency_id"],
        ).first()

        if incident is not None and (
            incident.is_confirmed or incident.status != Incident.STATUS_OPEN
        ):
            continue

        narrative = compose_incident_narrative(candidate)
        severity = severity_for(
            negative_pct=candidate["negative_pct"],
            volume_change_pct=candidate["volume_change_pct"],
        )

        if incident is None:
            incident = Incident.objects.create(
                project=project,
                title=candidate["title"],
                issue_id=candidate["issue_id"],
                regency_id=candidate["regency_id"],
                severity=severity,
                mention_count=candidate["total"],
                negative_pct=candidate["negative_pct"],
                first_seen_at=timezone.now(),
                **narrative,
            )
            IncidentEvent.objects.create(
                incident=incident,
                kind=IncidentEvent.KIND_DETECTED,
                description=(
                    f"Terdeteksi otomatis: {candidate['total']} sebutan, "
                    f"{candidate['negative_pct']}% negatif."
                ),
                logged_by="sistem",
            )
        else:
            previous = incident.mention_count
            incident.title = candidate["title"]
            incident.severity = severity
            incident.mention_count = candidate["total"]
            incident.negative_pct = candidate["negative_pct"]
            for field, value in narrative.items():
                setattr(incident, field, value)
            incident.save()
            if candidate["total"] != previous:
                IncidentEvent.objects.create(
                    incident=incident,
                    kind=IncidentEvent.KIND_VOLUME_UPDATE,
                    description=f"Volume berubah dari {previous} menjadi {candidate['total']} sebutan.",
                    logged_by="sistem",
                )

        incident.mentions.set(candidate["mention_ids"])
        touched.append(incident)
    return touched


class InvalidTransition(Exception):
    """The requested status change is not permitted from the current status."""


# An incident may not skip stages: a resolution that was never assigned or worked
# leaves a KPI record that does not describe what actually happened. Closed is
# terminal — a recurrence is a new incident, not a reopened one.
ALLOWED_TRANSITIONS = {
    Incident.STATUS_OPEN: {Incident.STATUS_ASSIGNED, Incident.STATUS_CLOSED},
    Incident.STATUS_ASSIGNED: {Incident.STATUS_IN_PROGRESS, Incident.STATUS_CLOSED},
    Incident.STATUS_IN_PROGRESS: {Incident.STATUS_RESOLVED, Incident.STATUS_CLOSED},
    Incident.STATUS_RESOLVED: {Incident.STATUS_CLOSED},
    Incident.STATUS_CLOSED: set(),
}


def promote(incident, by):
    """Confirm a detected candidate as a real incident (FR: human gate)."""
    incident.is_confirmed = True
    incident.save(update_fields=["is_confirmed", "updated_at"])
    IncidentEvent.objects.create(
        incident=incident,
        kind=IncidentEvent.KIND_ACTION_LOGGED,
        description="Kandidat dikonfirmasi sebagai insiden.",
        logged_by=by,
    )
    return incident


def assign(incident, opd, by):
    """Assign an incident to an OPD, advancing it out of `open`."""
    incident.assigned_opd = opd
    fields = ["assigned_opd", "updated_at"]
    if incident.status == Incident.STATUS_OPEN:
        incident.status = Incident.STATUS_ASSIGNED
        fields.append("status")
    incident.save(update_fields=fields)
    IncidentEvent.objects.create(
        incident=incident,
        kind=IncidentEvent.KIND_ASSIGNED,
        description=f"Ditugaskan ke {opd}.",
        logged_by=by,
    )
    return incident


def set_status(incident, status, by):
    """Move an incident to ``status``, refusing transitions that skip the lifecycle."""
    if status not in ALLOWED_TRANSITIONS.get(incident.status, set()):
        raise InvalidTransition(
            f"Tidak dapat mengubah status dari "
            f"{incident.get_status_display()} ke {dict(Incident.STATUS_CHOICES).get(status, status)}."
        )

    previous_display = incident.get_status_display()
    incident.status = status
    fields = ["status", "updated_at"]
    if status == Incident.STATUS_CLOSED:
        incident.closed_at = timezone.now()
        fields.append("closed_at")
    incident.save(update_fields=fields)

    IncidentEvent.objects.create(
        incident=incident,
        kind=IncidentEvent.KIND_STATUS_CHANGE,
        description=f"Status berubah dari {previous_display} menjadi {incident.get_status_display()}.",
        logged_by=by,
    )
    return incident


def log_note(incident, description, by):
    """Append a free-text note to the timeline without changing status."""
    return IncidentEvent.objects.create(
        incident=incident,
        kind=IncidentEvent.KIND_NOTE,
        description=description,
        logged_by=by,
    )


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
