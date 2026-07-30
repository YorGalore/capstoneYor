"""Escalation scoring: will this become a crisis if nobody acts?

Sentiment tells you how people feel now. It does not tell you whether an issue is
*accelerating* — and acceleration is what turns a complaint into a headline. This
engine combines eight signals into a 0–100 score and four explanations: why the
score, what happens if ignored, how confident we are, and what to do.

Three properties are non-negotiable here, because this number will be read by
people making public decisions:

* **Every signal shows its working.** Each carries its raw measure, its
  normalised value, its weight, its contribution, and a reference to the evidence
  behind it.
* **Missing data lowers confidence, not the score.** A project not collecting
  comments has no toxicity signal. Scoring that as zero would quietly understate
  risk on every issue. Instead the score is normalised over available weight and
  the confidence — and the UI — names what was missing.
* **The narrative is deterministic and draft-labelled**, following briefs.py and
  incidents.py. Nothing reaches leadership without human review.
"""
import logging
import math
from dataclasses import dataclass, field
from datetime import timedelta

from django.db.models import Count, Max, Q, Sum
from django.utils import timezone

from apps.governance import regulatory

from .briefs import DRAFT_BANNER
from .models import (
    EscalationAssessment, Incident, IncidentEvent, Mention, MentionAttribution,
)

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_DAYS = 7

# Starting calibration, front-loading the signals that distinguish a growing
# crisis from a merely loud day. Not a claim of empirical validity — these are
# runtime-tunable, and each assessment persists the weights it used so a
# historical score stays reproducible after retuning.
DEFAULT_WEIGHTS = {
    "velocity": 0.18,
    "sentiment_trend": 0.16,
    "engagement_growth": 0.14,
    "cross_platform": 0.13,
    "influencer": 0.12,
    "bot_activity": 0.11,
    "toxicity": 0.09,
    "emerging_narrative": 0.07,
}

SIGNAL_LABELS = {
    "velocity": "Kecepatan percakapan",
    "sentiment_trend": "Tren sentimen",
    "engagement_growth": "Pertumbuhan interaksi",
    "cross_platform": "Sebaran lintas platform",
    "influencer": "Keterlibatan akun berpengaruh",
    "bot_activity": "Indikasi aktivitas terkoordinasi",
    "toxicity": "Toksisitas diskusi",
    "emerging_narrative": "Narasi baru",
}

TIER_THRESHOLDS = [
    (75, EscalationAssessment.TIER_CRITICAL),
    (50, EscalationAssessment.TIER_HIGH),
    (25, EscalationAssessment.TIER_WATCH),
]

# An author at or above this follower percentile within the project's own author
# base counts as an influencer — floored by an absolute minimum so the biggest
# fish in a tiny pond does not qualify, and capped by the percentile so a
# regency-scale conversation can still register one.
INFLUENCER_PERCENTILE = 0.95
INFLUENCER_FLOOR = 10_000

# A platform carrying less than this share of volume is noise, not spread.
PLATFORM_SHARE_FLOOR = 0.05


@dataclass
class Signal:
    key: str
    raw: float = 0.0
    normalized: float = 0.0
    available: bool = False
    note: str = ""
    evidence_kind: str = ""
    evidence_params: dict = field(default_factory=dict)

    @property
    def label(self):
        return SIGNAL_LABELS.get(self.key, self.key)


def _ratio_to_score(ratio, ceiling=3.0):
    """Map a growth ratio onto 0–1, flattening above the ceiling.

    Tripling is already the top of the scale: the difference between 3x and 10x
    does not change what a government does next, and letting a single runaway
    ratio dominate the composite would drown the other seven signals.
    """
    if ratio <= 1:
        return 0.0
    return round(min(1.0, math.log(ratio) / math.log(ceiling)), 3)


def _window_bounds(since, until):
    span = until - since
    return since - span, since


def _velocity(current, previous, since, until):
    hours = max((until - since).total_seconds() / 3600, 1.0)
    now_rate = current.count() / hours
    prev_rate = previous.count() / hours
    if current.count() == 0:
        return Signal("velocity", note="Tidak ada sebutan pada jendela ini.")
    if prev_rate == 0:
        # No baseline. A burst from nothing is real, but "infinite growth" is not
        # a measurement — treat it as a strong-but-bounded reading.
        normalized = 0.7 if now_rate > 1 else 0.3
        return Signal(
            "velocity", raw=round(now_rate, 2), normalized=normalized, available=True,
            note=f"{round(now_rate, 2)} sebutan/jam tanpa aktivitas pembanding sebelumnya.",
            evidence_kind="mention", evidence_params={},
        )
    ratio = now_rate / prev_rate
    return Signal(
        "velocity", raw=round(ratio, 2), normalized=_ratio_to_score(ratio), available=True,
        note=(
            f"{round(now_rate, 2)} sebutan/jam vs {round(prev_rate, 2)} "
            "pada periode sebelumnya."
        ),
        evidence_kind="mention", evidence_params={},
    )


def _negative_pct(qs):
    total = qs.count()
    if not total:
        return 0
    return round(
        (qs.filter(sentiment=Mention.SENTIMENT_NEGATIVE).count() / total) * 100
    )


def _sentiment_trend(current, previous):
    if not current.exists():
        return Signal("sentiment_trend", note="Tidak ada sebutan pada jendela ini.")
    now_pct = _negative_pct(current)
    prev_pct = _negative_pct(previous)
    if not previous.exists():
        # Without a prior window, the level itself is the only honest reading.
        normalized = round(min(1.0, now_pct / 100), 3)
        return Signal(
            "sentiment_trend", raw=now_pct, normalized=normalized, available=True,
            note=f"{now_pct}% negatif; tidak ada periode pembanding.",
            evidence_kind="mention",
            evidence_params={"sentiment": Mention.SENTIMENT_NEGATIVE},
        )
    delta = now_pct - prev_pct
    # 40 points of movement in one window is a full-scale reading; beyond that the
    # distinction stops informing the decision.
    normalized = round(max(0.0, min(1.0, delta / 40)), 3)
    return Signal(
        "sentiment_trend", raw=delta, normalized=normalized, available=True,
        note=f"Negatif {prev_pct}% → {now_pct}% ({'+' if delta > 0 else ''}{delta} poin).",
        evidence_kind="mention",
        evidence_params={"sentiment": Mention.SENTIMENT_NEGATIVE},
    )


def _engagement_growth(current, previous):
    now_total = current.aggregate(t=Sum("engagement_count"))["t"] or 0
    prev_total = previous.aggregate(t=Sum("engagement_count"))["t"] or 0
    if now_total == 0:
        return Signal("engagement_growth", note="Belum ada interaksi tercatat.")
    if prev_total == 0:
        return Signal(
            "engagement_growth", raw=now_total, normalized=0.6, available=True,
            note=f"{now_total} interaksi tanpa pembanding periode sebelumnya.",
            evidence_kind="mention", evidence_params={},
        )
    ratio = now_total / prev_total
    return Signal(
        "engagement_growth", raw=round(ratio, 2), normalized=_ratio_to_score(ratio),
        available=True,
        note=f"{now_total} interaksi vs {prev_total} sebelumnya.",
        evidence_kind="mention", evidence_params={},
    )


def _influencer(current, project):
    from .models import Author

    followers = sorted(
        Author.objects.filter(mentions__project=project, follower_count__gt=0)
        .values_list("follower_count", flat=True).distinct()
    )
    if not followers:
        return Signal(
            "influencer",
            note="Data jumlah pengikut tidak tersedia untuk penulis mana pun.",
        )
    index = int(len(followers) * INFLUENCER_PERCENTILE)
    percentile_value = followers[min(index, len(followers) - 1)]
    threshold = max(percentile_value, INFLUENCER_FLOOR)

    participants = (
        current.filter(author__follower_count__gte=threshold)
        .values("author_id").distinct().count()
    )
    reach = current.aggregate(m=Max("author__follower_count"))["m"] or 0
    # Three or more influential participants is a full-scale reading: past that,
    # the issue has already left the niche.
    normalized = round(min(1.0, participants / 3), 3)
    return Signal(
        "influencer", raw=participants, normalized=normalized, available=True,
        note=(
            f"{participants} akun dengan ≥{threshold:,} pengikut ikut membahas "
            f"(jangkauan terbesar {reach:,})."
        ).replace(",", "."),
        evidence_kind="mention", evidence_params={},
    )


def _cross_platform(current):
    total = current.count()
    if not total:
        return Signal("cross_platform", note="Tidak ada sebutan pada jendela ini.")
    rows = current.values("platform__display_name").annotate(n=Count("id"))
    carrying = [r for r in rows if (r["n"] / total) >= PLATFORM_SHARE_FLOOR]
    if len(rows) <= 1:
        return Signal(
            "cross_platform", raw=1, normalized=0.0, available=True,
            note="Percakapan hanya terjadi pada satu platform.",
            evidence_kind="mention", evidence_params={},
        )
    # Normalised Shannon entropy: measures how evenly the conversation is spread,
    # not just how many platforms are involved. One platform with a token
    # presence elsewhere is not cross-platform spread.
    shares = [r["n"] / total for r in carrying]
    entropy = -sum(s * math.log(s) for s in shares if s > 0)
    max_entropy = math.log(len(shares)) if len(shares) > 1 else 1
    normalized = round(entropy / max_entropy, 3) if max_entropy else 0.0
    return Signal(
        "cross_platform", raw=len(carrying), normalized=normalized, available=True,
        note=f"{len(carrying)} platform masing-masing membawa ≥5% percakapan.",
        evidence_kind="mention", evidence_params={},
    )


def _toxicity(current):
    analysed = current.filter(
        content_type__in=Mention.REACTIVE_CONTENT_TYPES, toxicity_score__isnull=False
    )
    total = analysed.count()
    if not total:
        return Signal(
            "toxicity",
            note="Belum ada komentar yang dianalisis toksisitasnya pada jendela ini.",
        )
    toxic = analysed.filter(toxicity_label=Mention.TOXICITY_TOXIC).count()
    share = toxic / total
    # A quarter of comments turning abusive is a full-scale reading.
    normalized = round(min(1.0, share / 0.25), 3)
    return Signal(
        "toxicity", raw=round(share * 100), normalized=normalized, available=True,
        note=f"{round(share * 100)}% dari {total} komentar tergolong toksik.",
        evidence_kind="thread", evidence_params={"toxic": "1"},
    )


def _bot_activity(current, project):
    from apps.coordination.models import CoordinationCluster

    issue_ids = [
        i for i in current.values_list("issue_id", flat=True).distinct() if i
    ]
    if not issue_ids:
        return Signal(
            "bot_activity",
            note="Tidak ada isu war-room tertaut, sehingga deteksi koordinasi tidak berjalan.",
        )
    clusters = CoordinationCluster.objects.filter(issue_id__in=issue_ids)
    if not clusters.exists():
        return Signal(
            "bot_activity", raw=0, normalized=0.0, available=True,
            note="Tidak ditemukan klaster terkoordinasi pada isu ini.",
        )
    top = clusters.aggregate(m=Max("score"))["m"] or 0
    return Signal(
        "bot_activity", raw=float(top), normalized=round(min(1.0, float(top)), 3),
        available=True,
        note=f"Skor klaster terkoordinasi tertinggi {top} (perlu tinjauan analis).",
    )


def _emerging_narrative(project, since):
    from .models import DriverCandidate

    candidates = DriverCandidate.objects.filter(
        project=project, promoted_to__isnull=True, dismissed=False,
        last_seen_at__gte=since,
    )
    count = candidates.count()
    if not count:
        return Signal(
            "emerging_narrative", raw=0, normalized=0.0, available=True,
            note="Tidak ada alasan keluhan baru di luar taksonomi.",
        )
    top = candidates.order_by("-count").first()
    # Two or more unrecognised recurring complaints is a full-scale reading: the
    # conversation has moved somewhere the configured taxonomy does not cover.
    normalized = round(min(1.0, count / 2), 3)
    return Signal(
        "emerging_narrative", raw=count, normalized=normalized, available=True,
        note=f"{count} alasan baru terdeteksi, terbanyak \"{top.phrase}\".",
    )


def collect_signals(project, mentions, since, until):
    """Measure all eight signals over one window."""
    previous_since, previous_until = _window_bounds(since, until)
    current = mentions.filter(posted_at__gte=since, posted_at__lte=until)
    previous = mentions.filter(
        posted_at__gte=previous_since, posted_at__lt=previous_until
    )
    return [
        _velocity(current, previous, since, until),
        _sentiment_trend(current, previous),
        _engagement_growth(current, previous),
        _cross_platform(current),
        _influencer(current, project),
        _bot_activity(current, project),
        _toxicity(current),
        _emerging_narrative(project, since),
    ]


def score_signals(signals, weights=None):
    """Combine signals into a 0–100 score and a data-sufficiency confidence.

    Unavailable signals are excluded from both numerator and denominator. That is
    the whole point: treating "not measured" as "measured zero" would make every
    thinly-instrumented project look calm.
    """
    weights = weights or DEFAULT_WEIGHTS
    available = [s for s in signals if s.available]
    available_weight = sum(weights.get(s.key, 0) for s in available)
    if not available_weight:
        return 0, 0.0, []

    contributions = []
    total = 0.0
    for signal in signals:
        weight = weights.get(signal.key, 0)
        contribution = (
            (signal.normalized * weight / available_weight) if signal.available else 0.0
        )
        total += contribution
        contributions.append({
            "key": signal.key,
            "label": signal.label,
            "raw": signal.raw,
            "normalized": signal.normalized,
            "weight": weight,
            "contribution": round(contribution * 100, 1),
            "available": signal.available,
            "note": signal.note,
            "evidence_kind": signal.evidence_kind,
            "evidence_params": signal.evidence_params,
        })

    score = round(total * 100)
    # Confidence is the share of total weight that had data behind it.
    confidence = round(available_weight / sum(weights.values()), 3)
    return score, confidence, contributions


def tier_for(score):
    for threshold, tier in TIER_THRESHOLDS:
        if score >= threshold:
            return tier
    return EscalationAssessment.TIER_LOW


def compose_why(contributions, score, tier_display):
    """State which signals drove the score, largest contribution first."""
    drivers = sorted(
        [c for c in contributions if c["available"] and c["contribution"] > 0],
        key=lambda c: c["contribution"], reverse=True,
    )[:3]
    lines = [
        DRAFT_BANNER,
        "",
        f"Skor eskalasi **{score}/100** ({tier_display}).",
    ]
    if drivers:
        lines.append("")
        lines.append("Sinyal yang paling menentukan:")
        for item in drivers:
            lines.append(
                f"- **{item['label']}** — menyumbang {item['contribution']} poin. {item['note']}"
            )
    else:
        lines.append("")
        lines.append(
            "Tidak ada sinyal eskalasi yang aktif; skor rendah karena percakapan "
            "stabil, bukan karena data tidak tersedia."
        )

    missing = [c["label"] for c in contributions if not c["available"]]
    if missing:
        lines.append("")
        lines.append(
            "Sinyal tanpa data pada periode ini (tidak dihitung, dan menurunkan "
            f"tingkat keyakinan): {', '.join(missing)}."
        )
    return "\n".join(lines)


IMPACT_BY_TIER = {
    EscalationAssessment.TIER_CRITICAL: (
        "Bila dibiarkan, isu ini berpeluang besar menjadi pemberitaan luas dan "
        "menuntut penjelasan resmi pimpinan daerah dalam hitungan hari. Biaya "
        "komunikasi meningkat tajam setelah isu masuk media arus utama."
    ),
    EscalationAssessment.TIER_HIGH: (
        "Bila dibiarkan, isu ini berpeluang menarik perhatian media lokal dan "
        "memperluas ketidakpuasan ke kelompok warga yang belum terlibat. "
        "Penanganan pada tahap ini masih jauh lebih murah daripada setelah viral."
    ),
    EscalationAssessment.TIER_WATCH: (
        "Isu belum mengancam, tetapi menunjukkan pola awal pertumbuhan. Tanpa "
        "pemantauan, perubahan kecil pada volume atau sentimen dapat luput."
    ),
    EscalationAssessment.TIER_LOW: (
        "Tidak ada indikasi eskalasi. Dampak bila tidak ditangani segera "
        "diperkirakan terbatas pada keluhan individual."
    ),
}

RESPONSE_BY_TIER = {
    EscalationAssessment.TIER_CRITICAL: (
        "Siapkan pernyataan resmi dan satu pintu juru bicara dalam 24 jam, "
        "verifikasi lapangan segera oleh OPD berwenang, dan laporkan ke pimpinan "
        "daerah hari ini."
    ),
    EscalationAssessment.TIER_HIGH: (
        "Tugaskan OPD berwenang untuk verifikasi lapangan dalam 3 hari kerja dan "
        "siapkan bahan klarifikasi sebelum isu masuk media arus utama."
    ),
    EscalationAssessment.TIER_WATCH: (
        "Pantau perkembangan harian. Belum perlu pernyataan publik; cukup "
        "siapkan data dukung bila pertanyaan masuk."
    ),
    EscalationAssessment.TIER_LOW: (
        "Tangani melalui kanal pengaduan reguler. Tidak diperlukan tindakan "
        "komunikasi khusus."
    ),
}


def compose_impact(tier):
    return f"{DRAFT_BANNER}\n\n{IMPACT_BY_TIER[tier]}"


def compose_response(tier, contributions, incident=None, confidence=1.0):
    """Compose a recommended response, grounded in the regulatory corpus.

    Advisory only — the same rule the incident composer follows. The system
    proposes; a human with authority decides and signs.
    """
    lines = [DRAFT_BANNER, "", RESPONSE_BY_TIER[tier]]

    top = sorted(
        [c for c in contributions if c["available"]],
        key=lambda c: c["contribution"], reverse=True,
    )
    if top and top[0]["contribution"] > 0:
        lines.append("")
        lines.append(
            f"Fokus penanganan pada pendorong utama: {top[0]['label'].lower()}."
        )

    if incident is not None and incident.assigned_opd:
        lines.append("")
        lines.append(
            f"Penanganan saat ini berada pada **{incident.assigned_opd.name}**."
        )

    hits = []
    if incident is not None:
        query = " ".join(filter(None, [
            incident.title,
            " ".join((incident.issue.keywords or []) if incident.issue else []),
        ]))
        hits = regulatory.retrieve(query, limit=2) if query.strip() else []
        if hits:
            lines.append("")
            lines.append("### Dasar regulasi")
            for hit in hits:
                lines.append(f"- **{hit['source_ref']}** — \"{hit['passage']}\"")

    if confidence < 0.6:
        lines.append("")
        lines.append(
            "_Tingkat keyakinan rendah karena sebagian sinyal tidak memiliki data. "
            "Perlakukan rekomendasi ini sebagai indikasi awal, bukan dasar tunggal "
            "pengambilan keputusan._"
        )

    lines.append("")
    lines.append(
        "_Rekomendasi bersifat usulan. Keputusan dan penugasan tetap pada pejabat "
        "berwenang._"
    )
    return "\n".join(lines), [
        {"source_ref": h["source_ref"], "passage": h["passage"], "score": h["score"]}
        for h in hits
    ]


def assess_incident(incident, window_days=DEFAULT_WINDOW_DAYS, weights=None):
    """Score one incident and persist the assessment."""
    until = timezone.now()
    since = until - timedelta(days=window_days)
    mentions = Mention.objects.filter(incidents=incident)

    signals = collect_signals(incident.project, mentions, since, until)
    score, confidence, contributions = score_signals(signals, weights)
    tier = tier_for(score)
    tier_display = dict(EscalationAssessment.TIER_CHOICES)[tier]
    response, regulatory_context = compose_response(
        tier, contributions, incident=incident, confidence=confidence
    )

    assessment = EscalationAssessment.objects.create(
        incident=incident,
        project=incident.project,
        score=score,
        tier=tier,
        signals=contributions,
        confidence=confidence,
        available_signal_count=sum(1 for c in contributions if c["available"]),
        why=compose_why(contributions, score, tier_display),
        impact_if_ignored=compose_impact(tier),
        recommended_response=response,
        regulatory_context=regulatory_context,
        window_start=since,
        window_end=until,
        model="escalation-v1",
    )
    _apply_to_incident(incident, assessment)
    return assessment


def _apply_to_incident(incident, assessment):
    """Derive the incident's severity from the escalation tier.

    The board, its ordering, and its KPIs all read `Incident.severity`. Deriving
    it here rather than forking the ranking means escalation upgrades what is
    already there instead of adding a second, competing notion of urgency.
    """
    severity = assessment.severity
    if incident.severity == severity:
        return incident
    previous = incident.get_severity_display()
    incident.severity = severity
    incident.save(update_fields=["severity", "severity_rank", "updated_at"])
    IncidentEvent.objects.create(
        incident=incident,
        kind=IncidentEvent.KIND_VOLUME_UPDATE,
        description=(
            f"Skor eskalasi {assessment.score}/100 "
            f"({assessment.get_tier_display()}) — tingkat keparahan berubah dari "
            f"{previous} menjadi {incident.get_severity_display()}."
        ),
        logged_by="sistem",
    )
    return incident


def assess_project(project, window_days=DEFAULT_WINDOW_DAYS, weights=None):
    """Score every open incident in a project. Idempotent and re-runnable."""
    assessed = []
    for incident in Incident.objects.filter(project=project).exclude(
        status__in=[Incident.STATUS_RESOLVED, Incident.STATUS_CLOSED]
    ):
        try:
            assessed.append(assess_incident(incident, window_days, weights))
        except Exception as exc:
            logger.warning("Escalation failed for incident %s: %s", incident.pk, exc)
    return assessed


def latest_for(incident):
    return incident.escalations.order_by("-computed_at").first()
