"""Daily Executive Brief Engine (FR-30).

Generates a per-issue briefing on the previous day's (H-1) conversation for the
Spokesperson/Pimpinan persona, shortlisting issues by dominant negative sentiment
or unusual volume. Two properties matter more than the generation itself:

* The output is always a **draft requiring human review** — never auto-published
  (FR-30.2/30.3), and generated text is explicitly labeled as such (FR-31.4).
* Once finalized the brief is **locked and snapshotted** (FR-30.4), so the record
  of what leadership actually read cannot be rewritten afterwards.

Concurrency (FR-30.6) is handled with a database-level status claim rather than
request timing: a brief already in `generating` refuses a second concurrent
request for the same date, so a scheduled run and a manual run arriving together
cannot produce duplicate or corrupted output.
"""
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.governance import regulatory

from .models import DailyBrief, DailyBriefIssue, DailyBriefRun, IssueLabel, Mention

# An issue is only worth a leadership brief if it carries real signal.
MIN_MENTIONS = 3
MIN_NEGATIVE_PCT = 40
MAX_ISSUES_PER_BRIEF = 8

DRAFT_BANNER = (
    "**[DRAF — DIHASILKAN AI, MENUNGGU TINJAUAN MANUSIA]** "
    "Teks ini belum diverifikasi. Kutipan regulasi di bawah wajib diperiksa "
    "terhadap sumber aslinya sebelum dikutip publik."
)


class BriefAlreadyGenerating(Exception):
    """A generation for this date is already in flight (FR-30.6)."""


class BriefLocked(Exception):
    """The brief is finalized and can no longer be changed (FR-30.4)."""


class BriefNotReviewed(Exception):
    """All issues must be approved by a human before finalizing (FR-30.3)."""


def _shortlist(project, brief_date):
    """Pick the issues worth briefing leadership on, by negative sentiment or volume."""
    rows = (
        IssueLabel.objects.filter(
            mention__project=project, mention__posted_at__date=brief_date
        )
        .values("issue__id", "issue__name")
        .annotate(
            total=Count("mention__id"),
            negative=Count("mention__id", filter=Q(mention__sentiment=Mention.SENTIMENT_NEGATIVE)),
        )
        .order_by("-negative", "-total")
    )

    shortlisted = []
    for row in rows:
        total = row["total"]
        negative_pct = round((row["negative"] / total) * 100) if total else 0
        if total < MIN_MENTIONS and negative_pct < MIN_NEGATIVE_PCT:
            continue
        if negative_pct < MIN_NEGATIVE_PCT and total < MIN_MENTIONS * 3:
            continue
        shortlisted.append({
            "issue_id": row["issue__id"],
            "title": row["issue__name"],
            "total": total,
            "negative_pct": negative_pct,
        })
    return shortlisted[:MAX_ISSUES_PER_BRIEF]


def _grounding_query(project, brief_date, item):
    """Build the regulatory-retrieval query from what people actually said, not just
    the issue label. An issue named "Distribusi Bansos" shares no vocabulary with a
    regulation titled "Penyaluran Bantuan Sosial"; the underlying conversation does.
    """
    snippets = list(
        Mention.objects.filter(
            project=project,
            posted_at__date=brief_date,
            issue_label__issue_id=item["issue_id"],
        )
        .order_by("-engagement_count")
        .values_list("content_snippet", flat=True)[:10]
    )
    from apps.analytics.models import Issue

    issue = Issue.objects.filter(id=item["issue_id"]).first()
    keywords = " ".join(issue.keywords or []) if issue else ""
    return " ".join([item["title"], keywords, *snippets])


def _compose(item, hits, risk_level):
    """Compose the briefing text for one issue.

    Deterministic and grounded: it states the measured numbers and attaches the
    retrieved regulatory passages verbatim. A hosted LLM can replace this composer
    behind the same signature; the draft banner and the visible source passages are
    required either way (FR-31.4).
    """
    lines = [
        DRAFT_BANNER,
        "",
        f"## {item['title']}",
        "",
        f"- Volume percakapan (H-1): **{item['total']}** sebutan",
        f"- Sentimen negatif: **{item['negative_pct']}%**",
        f"- Tingkat risiko: **{regulatory.RISK_LABELS[risk_level]}**",
        "",
    ]
    if hits:
        lines.append("### Dasar regulasi (terambil, perlu verifikasi)")
        for hit in hits:
            lines.append(f"- **{hit['source_ref']}** — \"{hit['passage']}\"")
    else:
        lines.append(
            "### Dasar regulasi\n"
            "- Tidak ditemukan rujukan regulasi yang relevan pada korpus. "
            "Jangan mengarang kutipan; tambahkan dokumen ke korpus bila diperlukan."
        )
    return "\n".join(lines)


def _preview(item, risk_level):
    return (
        f"{item['title']}: {item['total']} sebutan dengan {item['negative_pct']}% "
        f"sentimen negatif — risiko {regulatory.RISK_LABELS[risk_level]}."
    )


@transaction.atomic
def _claim(project, brief_date):
    """Atomically claim the brief for generation, or refuse (FR-30.6)."""
    brief, _ = DailyBrief.objects.select_for_update().get_or_create(
        project=project, brief_date=brief_date,
        defaults={"status": DailyBrief.STATUS_PENDING},
    )
    if brief.status == DailyBrief.STATUS_FINAL:
        raise BriefLocked("Brief sudah final dan tidak dapat dibuat ulang.")
    if brief.status == DailyBrief.STATUS_GENERATING:
        raise BriefAlreadyGenerating(
            "Pembuatan brief untuk tanggal ini sedang berjalan."
        )
    brief.status = DailyBrief.STATUS_GENERATING
    brief.save(update_fields=["status"])
    return brief


def generate(project, brief_date, triggered_by):
    """Generate (or regenerate) the daily brief as a reviewable draft."""
    brief = _claim(project, brief_date)
    run = DailyBriefRun.objects.create(brief=brief, triggered_by=triggered_by)

    try:
        with transaction.atomic():
            # Regeneration replaces the prior draft rather than appending to it.
            brief.issues.all().delete()

            for order, item in enumerate(_shortlist(project, brief_date)):
                hits = regulatory.retrieve(
                    _grounding_query(project, brief_date, item), limit=2
                )
                risk_level = regulatory.classify_risk(
                    negative_ratio=item["negative_pct"] / 100,
                    volume_change_pct=0,
                    coordinated=False,
                )
                DailyBriefIssue.objects.create(
                    brief=brief,
                    title=item["title"],
                    content=_compose(item, hits, risk_level),
                    preview_summary=_preview(item, risk_level),
                    risk_level=risk_level,
                    order=order,
                    mention_count=item["total"],
                    negative_pct=item["negative_pct"],
                    regulatory_context=[
                        {"source_ref": h["source_ref"], "passage": h["passage"], "score": h["score"]}
                        for h in hits
                    ],
                )

            brief.status = DailyBrief.STATUS_DRAFT
            brief.save(update_fields=["status"])
    except Exception as exc:
        brief.status = DailyBrief.STATUS_FAILED
        brief.save(update_fields=["status"])
        run.detail = str(exc)[:300]
        run.completed_at = timezone.now()
        run.save(update_fields=["detail", "completed_at"])
        raise

    run.succeeded = True
    run.completed_at = timezone.now()
    run.detail = f"{brief.issues.count()} isu diprioritaskan"
    run.save(update_fields=["succeeded", "completed_at", "detail"])
    return brief


def _assert_editable(brief):
    if brief.is_locked:
        raise BriefLocked("Brief sudah final dan terkunci (FR-30.4).")


def edit_issue(item, content, edited_by):
    _assert_editable(item.brief)
    item.content = content
    item.edited_by = edited_by
    item.save(update_fields=["content", "edited_by"])
    return item


def approve_issue(item, approved_by):
    _assert_editable(item.brief)
    item.approved = True
    item.edited_by = item.edited_by or approved_by
    item.save(update_fields=["approved", "edited_by"])
    return item


@transaction.atomic
def reorder(brief, ordered_issue_ids):
    """Reorder issues within a brief (FR-30.3)."""
    _assert_editable(brief)
    for order, issue_id in enumerate(ordered_issue_ids):
        DailyBriefIssue.objects.filter(brief=brief, id=issue_id).update(order=order)
    return brief


def finalize(brief, finalized_by):
    """Lock the brief. Every issue must have been reviewed first (FR-30.3/30.4)."""
    _assert_editable(brief)
    if brief.issues.filter(approved=False).exists():
        raise BriefNotReviewed(
            "Setiap isu harus ditinjau dan disetujui sebelum brief difinalisasi."
        )
    brief.status = DailyBrief.STATUS_FINAL
    brief.finalized_by = finalized_by
    brief.finalized_at = timezone.now()
    brief.save(update_fields=["status", "finalized_by", "finalized_at"])
    return brief
