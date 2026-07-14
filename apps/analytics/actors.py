"""Political actor & camp tagging and government-program tracking (FR-24, FR-27).

Symmetric and non-partisan by construction: the platform tags whichever actors the
tenant configured and reports the same metrics for every camp side by side. No camp
is hard-coded or defaulted (FR-24.3), and tagging is restricted to registered
public/organizational actors — private individuals are never profiled (FR-29.3).
"""
from django.db.models import Count, Q

from .models import Camp, GovernmentProgram, Mention, PoliticalActor


def _matches(actor, text, handle):
    handle = (handle or "").lower().lstrip("@")
    if any(h.lower().lstrip("@") == handle for h in (actor.handles or []) if h):
        return True
    return any(kw.lower() in text for kw in (actor.keywords or []) if kw)


def tag_mention(mention):
    """Tag a mention with zero, one, or more matching political actors (FR-24.2).
    Returns the list of matched actors."""
    text = (mention.content_snippet or "").lower()
    matched = [
        actor
        for actor in PoliticalActor.objects.filter(project=mention.project, is_active=True)
        if _matches(actor, text, mention.author_handle)
    ]
    if not matched:
        return []

    mention.political_actors.set(matched)
    if not mention.is_political:
        mention.is_political = True
        mention.save(update_fields=["is_political"])
    return matched


def tag_program(mention):
    """Attribute a mention to a tracked government program (FR-27.1)."""
    text = (mention.content_snippet or "").lower()
    for program in GovernmentProgram.objects.filter(project=mention.project, is_active=True):
        if any(kw.lower() in text for kw in (program.keywords or []) if kw):
            mention.program = program
            mention.save(update_fields=["program"])
            return program
    return None


def share_of_voice(project):
    """Share of Voice per camp (FR-25.1), reported symmetrically for every camp."""
    camps = list(Camp.objects.filter(project=project))
    counts = {
        camp.id: Mention.objects.filter(
            project=project, political_actors__camp=camp
        ).distinct().count()
        for camp in camps
    }
    total = sum(counts.values())
    return [
        {
            "camp": camp,
            "count": counts[camp.id],
            "share_pct": round((counts[camp.id] / total) * 100) if total else 0,
        }
        for camp in camps
    ]


def program_summary(program):
    """Volume and sentiment breakdown for a tracked program (FR-27.1)."""
    qs = Mention.objects.filter(program=program)
    total = qs.count()
    row = qs.aggregate(
        positive=Count("id", filter=Q(sentiment=Mention.SENTIMENT_POSITIVE)),
        neutral=Count("id", filter=Q(sentiment=Mention.SENTIMENT_NEUTRAL)),
        negative=Count("id", filter=Q(sentiment=Mention.SENTIMENT_NEGATIVE)),
    )
    return {
        "program": program,
        "total": total,
        "positive_pct": round((row["positive"] / total) * 100) if total else 0,
        "neutral_pct": round((row["neutral"] / total) * 100) if total else 0,
        "negative_pct": round((row["negative"] / total) * 100) if total else 0,
    }
