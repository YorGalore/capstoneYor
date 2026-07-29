"""Collection orchestrator (REQ-SC-01..05, REQ-DC-04): fans active keywords out
across enabled Apify platforms, ingests the results, and records each cycle in a
CollectionRun ledger with overlap-skip and a per-run cost estimate.
"""
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone

from . import apify_crawler, comment_crawler
from .ingestion import ingest_items
from .models import CollectionRun, MonitoredDomain, MonitoringKeyword, PlatformIntegration

# Indicative pay-per-1000-result pricing (USD), doc Appendix A. Re-verify before
# locking budgets — used only for the usage/cost estimate.
PRICING_PER_1000 = {
    "x": Decimal("0.40"),
    "instagram": Decimal("1.50"),
    "tiktok": Decimal("1.70"),
    "facebook": Decimal("2.00"),
    "youtube": Decimal("2.40"),
}

COMMENT_PRICING_PER_1000 = {
    "x": Decimal("1.61"),
    "instagram": Decimal("1.00"),
    "tiktok": Decimal("0.20"),
    "facebook": Decimal("3.00"),
    "youtube": Decimal("1.50"),
}


def estimate_cost(platform, item_count, *, comments=False):
    pricing = COMMENT_PRICING_PER_1000 if comments else PRICING_PER_1000
    price = pricing.get(platform, Decimal("0"))
    cost = (Decimal(item_count) / Decimal(1000)) * price
    return cost.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _is_overlapping(project, source):
    return CollectionRun.objects.filter(
        project=project, source=source, status=CollectionRun.STATUS_RUNNING
    ).exists()


def collect_platform(
    project,
    platform,
    keywords,
    token,
    *,
    actor_id=None,
    start_date=None,
    end_date=None,
    max_results=None,
):
    """Run one Apify platform for the active keywords, skipping if a prior run for
    the same source is still in flight (REQ-SC-05)."""
    source = platform.slug
    if start_date or end_date:
        source = (
            f"{source}:history:"
            f"{start_date.strftime('%Y%m%d') if start_date else 'open'}-"
            f"{end_date.strftime('%Y%m%d') if end_date else 'open'}"
        )
    if _is_overlapping(project, source):
        return CollectionRun.objects.create(
            project=project, source=source, status=CollectionRun.STATUS_SKIPPED,
            keywords_count=len(keywords), finished_at=timezone.now(),
        )

    run = CollectionRun.objects.create(
        project=project, source=source, status=CollectionRun.STATUS_RUNNING,
        keywords_count=len(keywords)
    )
    try:
        items = apify_crawler.collect(
            platform.slug,
            [kw.keyword for kw in keywords],
            token=token,
            max_results=max_results,
            start_date=start_date,
            end_date=end_date,
            actor_id=actor_id,
        )
        ingest_items(project, platform, items)
        comments = []
        comment_error = ""
        if (
            project.collect_comments
            and platform.slug in comment_crawler.supported_platforms()
        ):
            max_posts = min(max(project.comment_posts_per_run, 1), 50)
            max_comments = min(max(project.comments_per_post, 1), 500)
            parent_items = sorted(
                items, key=lambda item: item.get("engagement_count", 0), reverse=True
            )[:max_posts]
            try:
                comments = comment_crawler.collect(
                    platform.slug,
                    parent_items,
                    token=token,
                    max_comments_per_post=max_comments,
                    start_date=start_date,
                    end_date=end_date,
                )
                ingest_items(project, platform, comments)
            except Exception as exc:
                # A dedicated comment Actor can be unavailable while post search is
                # healthy. Preserve the successfully collected posts and expose the
                # partial-coverage reason instead of misreporting the whole run as lost.
                comment_error = f"Koleksi komentar gagal: {exc}"[:500]

        run.items_found = len(items) + len(comments)
        run.cost_estimate = (
            estimate_cost(platform.slug, len(items))
            + estimate_cost(platform.slug, len(comments), comments=True)
        )
        run.status = CollectionRun.STATUS_COMPLETED
        run.error = comment_error
    except Exception as exc:  # a failed actor run must not abort the batch (doc §3)
        run.status = CollectionRun.STATUS_FAILED
        run.error = str(exc)[:500]
    run.finished_at = timezone.now()
    run.save()
    return run


def run_apify_collection(
    project,
    token,
    platforms=None,
    *,
    start_date=None,
    end_date=None,
    max_results=None,
):
    """Collect from every enabled Apify platform. Returns the CollectionRun list.
    Degrades gracefully (no runs) when there is no token or no active keyword."""
    # The kill switch is enforced here, at the collection boundary, rather than in the
    # scheduler — `manage.py collect` and the console's "Pindai" button also land here,
    # and a halt that only the scheduler honors would be undone by the next person to
    # press the button (REQ-LC-03).
    from .scheduling import collection_enabled

    if not collection_enabled():
        return []
    if not token:
        return []
    active_keywords = list(MonitoringKeyword.objects.filter(project=project, is_active=True))
    if not active_keywords:
        return []

    integrations = (
        PlatformIntegration.objects.filter(
            project=project,
            is_active=True,
            method=PlatformIntegration.METHOD_APIFY,
            platform__slug__in=apify_crawler.supported_platforms(),
        )
        .select_related("platform")
        .order_by("platform__slug")
    )
    if platforms is not None:
        integrations = integrations.filter(platform__slug__in=platforms)

    return [
        collect_platform(
            project,
            integ.platform,
            active_keywords,
            token,
            actor_id=integ.actor_id or None,
            start_date=start_date,
            end_date=end_date,
            max_results=max_results,
        )
        for integ in integrations
    ]


def collect_news_source(project, platform, domain, keywords):
    """Collect one publisher through its RSS/sitemap/listing adapter."""
    source = f"news:{domain.domain}"
    if _is_overlapping(project, source):
        return CollectionRun.objects.create(
            project=project, source=source, status=CollectionRun.STATUS_SKIPPED,
            keywords_count=len(keywords), finished_at=timezone.now(),
        )

    run = CollectionRun.objects.create(
        project=project, source=source, status=CollectionRun.STATUS_RUNNING,
        keywords_count=len(keywords),
    )
    try:
        from . import scraping

        result = scraping.run_scan(
            project=project, platform=platform, domains=[domain], keywords=keywords
        )
        run.items_found = result["new_mentions"]
        if result["errors"]:
            run.status = CollectionRun.STATUS_FAILED
            run.error = "; ".join(result["errors"])[:500]
        else:
            run.status = CollectionRun.STATUS_COMPLETED
    except Exception as exc:
        run.status = CollectionRun.STATUS_FAILED
        run.error = str(exc)[:500]
    run.finished_at = timezone.now()
    run.save()
    return run


def run_news_collection(project, domains=None):
    """Collect enabled online-news sources without requiring an Apify token."""
    from apps.core.models import Platform
    from .scheduling import collection_enabled

    if not collection_enabled():
        return []
    keywords = list(MonitoringKeyword.objects.filter(project=project, is_active=True))
    if not keywords:
        return []
    queryset = MonitoredDomain.objects.filter(project=project).exclude(
        status=MonitoredDomain.STATUS_INACTIVE
    ).exclude(feed_url="")
    if domains is not None:
        queryset = queryset.filter(domain__in=domains)
    platform, _ = Platform.objects.get_or_create(
        slug="berita",
        defaults={"display_name": "Berita Daring", "brand_color": "#0E7C86"},
    )
    return [
        collect_news_source(project, platform, domain, keywords)
        for domain in queryset.order_by("domain")
    ]
