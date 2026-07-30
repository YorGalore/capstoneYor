"""Ingestion & normalization (§4.4, FR-3.2/3.3): persist normalized crawler items
as Mention rows, deduplicated by external_id and linked to a normalized Author.

Interim sentiment/emotion come from the lexicon scorer in `scraping` until the
NLP Analytics service lands (Workstream C); the classifier is swappable behind
this boundary.
"""
import logging

from django.db import transaction

from apps.analytics import actors, attribution, comment_intel, drivers, taxonomy
from apps.analytics.models import Author, Mention
from apps.analytics.nlp import default_pipeline

logger = logging.getLogger(__name__)


def _author_for(platform, handle):
    handle = (handle or "").strip() or "tidak_dikenal"
    author, _ = Author.objects.get_or_create(
        platform=platform, handle=handle, defaults={"display_name": handle}
    )
    return author


@transaction.atomic
def ingest_items(project, platform, items):
    """Persist a batch of normalized items. Returns a summary dict."""
    created = 0
    duplicates = 0
    classifier = default_pipeline()
    # Built once per batch: each pipeline construction re-reads runtime settings
    # and would otherwise repeat that work for every item ingested.
    attributor = attribution.default_pipeline()
    driver_pipeline = drivers.default_pipeline()
    comment_pipeline = comment_intel.default_pipeline()
    for item in items:
        external_id = item.get("external_id")
        if external_id and Mention.objects.filter(external_id=external_id).exists():
            duplicates += 1
            continue

        content = item.get("content", "") or ""
        result = classifier.classify(content)
        author = _author_for(platform, item.get("author"))
        parent = None
        parent_external_id = item.get("parent_external_id")
        if parent_external_id:
            parent = Mention.objects.filter(
                project=project, external_id=parent_external_id
            ).first()
        mention = Mention.objects.create(
            project=project,
            platform=platform,
            external_id=external_id,
            author=author,
            author_handle=author.handle,
            content_snippet=content[:500],
            sentiment=result.sentiment,
            sentiment_confidence=result.confidence,
            sentiment_model=result.model_version,
            emotion=result.emotions[0] if result.emotions else Mention.EMOTION_TRUST,
            emotion_labels=result.emotions,
            posted_at=item.get("posted_at") or _now(),
            engagement_count=item.get("engagement_count", 0) or 0,
            reach_estimate=item.get("reach", 0) or 0,
            source_url=item.get("url") or None,
            matched_keyword=item.get("matched_keyword", ""),
            is_scraped=True,
            content_type=item.get("content_type", Mention.CONTENT_POST),
            parent=parent,
            reported_comment_count=(
                (item.get("engagement") or {}).get("comments", 0) or 0
            ),
        )
        # Auto-assign to the Issue Taxonomy where the content confidently matches;
        # anything unmatched surfaces in the manual review queue (FR-3A.2/3A.3).
        taxonomy.auto_label(mention)
        # Apply only tenant-configured public/organizational actor rules, plus
        # configured government-program rules, while the mention is ingested.
        actors.tag_mention(mention)
        actors.tag_program(mention)
        # Decide who the sentiment is aimed at. Enrichment failure must never
        # cost us the mention itself — a post that lands with sentiment but no
        # attribution is recoverable by backfill; one that never lands is not.
        try:
            attribution.attribute(mention, pipeline=attributor)
        except Exception:
            logger.exception("Attribution failed for mention %s", mention.pk)
        # Drivers run after attribution: a post can be negative toward one entity
        # while positive overall, and that still needs a reason attached.
        try:
            drivers.label(mention, pipeline=driver_pipeline)
        except Exception:
            logger.exception("Driver labeling failed for mention %s", mention.pk)
        try:
            comment_intel.enrich(mention, pipeline=comment_pipeline)
        except Exception:
            logger.exception("Comment enrichment failed for mention %s", mention.pk)
        created += 1
    return {"created": created, "duplicates": duplicates}


def _now():
    from django.utils import timezone

    return timezone.now()
