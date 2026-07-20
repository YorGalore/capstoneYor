"""Author normalization and influence scoring (FR-3.3).

Collection stores only the raw ``author_handle`` string on each mention. This
step turns those strings into normalized Author rows — one per (platform,
handle) — links the mentions to them, and computes a rough influence score so
ranking authors does not depend on raw reach alone.

Influence is a log-scaled blend of cumulative reach and engagement: log scaling
because audience size is power-law distributed, and a linear score would make
one viral account flatten every other node in the sociograph.
"""
import math

from django.db.models import Count, Sum

from .models import Author, Mention

# Weights chosen so a pure-reach account and a high-engagement account can rank
# comparably: reach is easy to inflate, engagement is behaviour.
REACH_WEIGHT = 12.0
ENGAGEMENT_WEIGHT = 8.0
MENTION_WEIGHT = 2.0


def influence_score(reach, engagement, mention_count):
    return round(
        REACH_WEIGHT * math.log10(1 + max(reach, 0))
        + ENGAGEMENT_WEIGHT * math.log10(1 + max(engagement, 0))
        + MENTION_WEIGHT * math.log10(1 + max(mention_count, 0)),
        2,
    )


def link_authors(project):
    """Create/attach an Author row for every mention still carrying only the raw
    handle string. Returns the number of mentions linked."""
    pending = (
        Mention.objects.filter(project=project, author__isnull=True)
        .exclude(author_handle="")
        .select_related("platform")
    )
    linked = 0
    cache = {}
    for mention in pending:
        key = (mention.platform_id, mention.author_handle)
        author = cache.get(key)
        if author is None:
            author, _ = Author.objects.get_or_create(
                platform=mention.platform,
                handle=mention.author_handle,
                defaults={"display_name": mention.author_handle},
            )
            cache[key] = author
        mention.author = author
        mention.save(update_fields=["author"])
        linked += 1
    return linked


def recompute_influence(project):
    """Recompute influence for every author with mentions in the project.
    Returns the number of authors scored."""
    rows = (
        Mention.objects.filter(project=project, author__isnull=False)
        .values("author_id")
        .annotate(
            n=Count("id"),
            reach=Sum("reach_estimate"),
            engagement=Sum("engagement_count"),
        )
    )
    scored = 0
    for row in rows:
        score = influence_score(row["reach"] or 0, row["engagement"] or 0, row["n"])
        Author.objects.filter(pk=row["author_id"]).update(influence_score=score)
        scored += 1
    return scored


def enrich(project):
    """The scheduled entry point: link, then score."""
    linked = link_authors(project)
    scored = recompute_influence(project)
    return {"linked": linked, "scored": scored}
