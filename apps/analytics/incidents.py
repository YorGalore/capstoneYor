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
from .briefs import DRAFT_BANNER
from .models import Incident

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
