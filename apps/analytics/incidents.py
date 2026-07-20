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
    """
    escalating = volume_change_pct >= SURGE_PCT or coordinated

    if negative_pct >= CRITICAL_NEGATIVE_PCT:
        return Incident.SEVERITY_CRITICAL if escalating else Incident.SEVERITY_HIGH
    if negative_pct >= HIGH_NEGATIVE_PCT:
        return Incident.SEVERITY_HIGH if escalating else Incident.SEVERITY_MEDIUM
    if negative_pct >= MEDIUM_NEGATIVE_PCT or coordinated:
        return Incident.SEVERITY_MEDIUM
    return Incident.SEVERITY_LOW


def _location(candidate):
    return candidate.get("regency_name") or "wilayah yang belum teridentifikasi"


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

    if snippets:
        root_cause = (
            f"{DRAFT_BANNER}\n\n"
            "Penyebab belum diverifikasi. Indikasi awal berdasarkan kutipan warga "
            "di atas perlu dikonfirmasi melalui pemeriksaan lapangan oleh OPD terkait."
        )
    else:
        root_cause = (
            f"{DRAFT_BANNER}\n\n"
            "Penyebab belum dapat disimpulkan: tidak tersedia kutipan percakapan "
            "yang memadai. Jangan mengarang penyebab; lakukan verifikasi lapangan."
        )

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


# How far back detection looks when no explicit window is given.
DEFAULT_WINDOW_DAYS = 7


def shortlist_candidates(project, since=None, window_days=DEFAULT_WINDOW_DAYS):
    """Group recent labeled conversation into candidate incidents.

    Clusters on (taxonomy Issue x Regency): the same complaint in two different
    kecamatan is two incidents, because they are assigned and resolved separately.
    """
    if since is None:
        since = timezone.now() - timedelta(days=window_days)

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
        candidates.append({
            "title": row["issue__name"],
            "issue_id": row["issue__id"],
            "regency_id": row["mention__regency__id"],
            "regency_name": row["mention__regency__name"] or "",
            "total": total,
            "negative_pct": negative_pct,
            "snippets": [snippet for _id, snippet in mentions[:MAX_SNIPPETS]],
            "mention_ids": [mention_id for mention_id, _snippet in mentions],
        })
    return candidates


@transaction.atomic
def refresh_candidates(project, since=None, window_days=DEFAULT_WINDOW_DAYS):
    """Upsert candidate incidents for a project, returning the touched incidents.

    A confirmed incident is left alone entirely: once an operator has promoted and
    edited it, re-running detection must not clobber their judgement with a fresh
    machine composition.
    """
    touched = []
    for candidate in shortlist_candidates(project, since=since, window_days=window_days):
        incident = Incident.objects.filter(
            project=project,
            issue_id=candidate["issue_id"],
            regency_id=candidate["regency_id"],
        ).first()

        if incident is not None and incident.is_confirmed:
            continue

        narrative = compose_incident_narrative(candidate)
        severity = severity_for(negative_pct=candidate["negative_pct"])

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
