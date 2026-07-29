"""Apify social crawler connector (REQ-DC-01/03/05).

Ports the actor configuration and normalization rules documented in
`docs/APIFY_INTEGRATION.md` (Team 1 social crawler) into this Django platform.
Rather than pulling in the `apify-client` SDK, actor runs are triggered through
Apify's REST ``run-sync-get-dataset-items`` endpoint using the stdlib, keeping the
service dependency-light and consistent with `apify.py`. `_run_and_fetch_items`
is the sole network boundary and is what tests stub.

Platform keys use this project's Platform.slug values ("x" for Twitter/X).
"""
import hashlib
import http.client
import json
import math
import urllib.error
import urllib.request
from collections import Counter
from urllib.parse import urlencode
from datetime import date, datetime, time, timedelta, timezone as datetime_timezone
from email.utils import parsedate_to_datetime

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

# Platform slug → currently available public Actor and normalization config.
# Actor names are accepted by Apify's API and remain readable in the console.
ACTOR_CONFIG = {
    "x": {
        "actor_id": "apidojo~tweet-scraper",
        "default_max": 100,
        "prefix": "tw",
    },
    "facebook": {
        "actor_id": "scraper_one~facebook-posts-search",
        "default_max": 50,
        "prefix": "fb",
    },
    "youtube": {
        "actor_id": "streamers~youtube-scraper",
        "default_max": 100,
        "prefix": "yt",
    },
    "tiktok": {
        "actor_id": "clockworks~tiktok-scraper",
        "default_max": 100,
        "prefix": "tt",
    },
    "instagram": {
        "actor_id": "apify~instagram-scraper",
        "default_max": 100,
        "prefix": "ig",
    },
}

APIFY_RUN_URL = "https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items"
RUN_TIMEOUT_SECONDS = 300
MAX_TOTAL_CHARGE_USD = 2


class ApifyCollectionError(RuntimeError):
    """Raised when an Apify actor run cannot return a trustworthy dataset."""


def supported_platforms():
    return list(ACTOR_CONFIG.keys())


def default_max_results(platform):
    return ACTOR_CONFIG[platform]["default_max"]


def _first(item, *keys, default=None):
    for key in keys:
        value = item.get(key)
        if value not in (None, "", [], {}):
            return value
    return default


def _count(value):
    if isinstance(value, dict):
        return sum(_count(item) for item in value.values())
    if isinstance(value, str):
        value = value.replace(",", "").strip()
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _per_query_limit(max_results, keywords):
    return max(1, math.ceil(max_results / max(len(keywords), 1)))


def _exclusive_end(end_date):
    return end_date + timedelta(days=1) if end_date else None


def _tiktok_history_filter(start_date, end_date):
    """Pick the narrowest search window supported by TikTok keyword search."""
    if not start_date:
        return "PAST_24_HOURS"
    reference = end_date or timezone.localdate()
    age_days = max((reference - start_date).days + 1, 1)
    if age_days <= 1:
        return "PAST_24_HOURS"
    if age_days <= 7:
        return "PAST_WEEK"
    if age_days <= 31:
        return "PAST_MONTH"
    if age_days <= 92:
        return "LAST_3_MONTHS"
    return "ALL_TIME"


def _compact_facebook_query(keywords, max_chars=100):
    """Prefer a repeated location phrase, then add uncovered exact phrases."""
    bigrams = Counter()
    for keyword in keywords:
        words = keyword.split()
        bigrams.update(
            " ".join(words[index:index + 2])
            for index in range(max(len(words) - 1, 0))
        )
    repeated = [
        phrase for phrase, count in bigrams.most_common()
        if count >= 2
    ]
    selected = repeated[:1] or keywords[:1]
    anchor = selected[0].casefold() if selected else ""
    for keyword in keywords:
        if anchor and anchor in keyword.casefold():
            continue
        candidate = " OR ".join(f'"{term}"' for term in [*selected, keyword])
        if len(candidate) > max_chars:
            continue
        selected.append(keyword)
    return " OR ".join(f'"{term}"' for term in selected)[:max_chars]


def build_actor_input(
    platform, keywords, max_results, *, start_date=None, end_date=None
):
    """Build a bounded current or historical Actor input for a platform."""
    now = timezone.now()
    per_query = _per_query_limit(max_results, keywords)
    if platform == "x":
        if start_date:
            since = start_date.strftime("%Y-%m-%d")
            until = _exclusive_end(end_date or timezone.localdate()).strftime("%Y-%m-%d")
        else:
            since = (now - timedelta(hours=3)).strftime("%Y-%m-%d_%H:%M:%S_UTC")
            until = now.strftime("%Y-%m-%d_%H:%M:%S_UTC")
        run_input = {
            "searchTerms": [f"{kw} lang:id since:{since} until:{until}" for kw in keywords],
            "maxItems": max_results,
            "tweetLanguage": "id",
            "includeSearchTerms": True,
        }
        if start_date:
            run_input["start"] = start_date.strftime("%Y-%m-%d")
        if end_date:
            run_input["end"] = _exclusive_end(end_date).strftime("%Y-%m-%d")
        return run_input
    if platform == "youtube":
        return {
            "searchQueries": keywords,
            "maxResults": per_query,
            "maxResultsShorts": 0,
            "maxResultStreams": 0,
            "oldestPostDate": (
                start_date.strftime("%Y-%m-%d") if start_date else "1 day"
            ),
            "sortVideosBy": "NEWEST",
        }
    if platform == "instagram":
        return {
            "directUrls": [
                f"https://www.instagram.com/explore/tags/{''.join(ch for ch in kw if ch.isalnum())}/"
                for kw in keywords
            ],
            "resultsType": "posts",
            "resultsLimit": per_query,
            "onlyPostsNewerThan": (
                start_date.strftime("%Y-%m-%d") if start_date else "1 day"
            ),
            "skipPinnedPosts": True,
        }
    if platform == "tiktok":
        return {
            "searchQueries": keywords,
            "resultsPerPage": per_query,
            "searchSection": "/video",
            "videoSearchSorting": "LATEST",
            "videoSearchDateFilter": _tiktok_history_filter(start_date, end_date),
            "shouldDownloadVideos": False,
            "commentsPerPost": 0,
        }
    if platform == "facebook":
        today = timezone.localdate()
        return {
            "query": _compact_facebook_query(keywords),
            "resultsCount": max_results,
            "searchType": "latest",
            "startDate": (start_date or today).strftime("%Y-%m-%d"),
            "endDate": (end_date or today).strftime("%Y-%m-%d"),
        }
    raise ValueError(f"Platform tidak didukung untuk input Apify: {platform}")


def _external_id(platform, url):
    prefix = ACTOR_CONFIG[platform]["prefix"]
    digest = hashlib.md5(url.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def _engagement(platform, item):
    if platform == "tiktok":
        return {
            "views": _first(item, "playCount", default=0),
            "likes": _first(item, "diggCount", default=0),
            "shares": _first(item, "shareCount", default=0),
            "comments": _first(item, "commentCount", default=0),
        }
    if platform == "youtube":
        return {
            "views": _first(item, "viewCount", "views", default=0),
            "likes": _first(item, "likes", "likeCount", "likesCount", default=0),
            "comments": _first(
                item, "comments", "commentCount", "commentsCount", default=0
            ),
        }
    if platform == "instagram":
        return {
            "likes": _first(item, "likesCount", "likeCount", default=0),
            "comments": _first(item, "commentsCount", "commentCount", default=0),
        }
    if platform == "x":
        return {
            "views": _first(item, "viewCount", "views", default=0),
            "likes": _first(item, "likeCount", "likes", default=0),
            "shares": _first(item, "retweetCount", default=0),
            "comments": _first(item, "replyCount", default=0),
        }
    if platform == "facebook":
        return {
            "likes": _first(
                item, "reactions_count", "reactionsCount", "reactions", "likes", default=0
            ),
            "shares": _first(
                item, "reshare_count", "reshares", "sharesCount", "shares", default=0
            ),
            "comments": _first(
                item, "comments_count", "commentsCount", "comments", default=0
            ),
        }
    return {}


def _author(platform, item):
    author = item.get("author")
    if isinstance(author, dict):
        return _first(author, "userName", "username", "name", "handle", default="")
    meta = item.get("authorMeta")
    if isinstance(meta, dict):
        return _first(meta, "name", "nickName", "uniqueId", default="")
    return _first(
        item,
        "ownerUsername",
        "channelName",
        "authorName",
        "pageName",
        "author",
        default="",
    ) or ""


def _timestamp(item):
    value = _first(
        item,
        "createdAt",
        "created_at",
        "createTimeISO",
        "createTime",
        "publishedAt",
        "published_at",
        "uploadDate",
        "date",
        "time",
        "timestamp",
        default=None,
    )
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        seconds = float(value)
        if seconds > 10_000_000_000:
            seconds /= 1000
        return datetime.fromtimestamp(seconds, tz=datetime_timezone.utc)

    raw = str(value).strip()
    if raw.isdigit():
        seconds = float(raw)
        if seconds > 10_000_000_000:
            seconds /= 1000
        return datetime.fromtimestamp(seconds, tz=datetime_timezone.utc)

    parsed = parse_datetime(raw)
    if parsed is None:
        parsed_day = parse_date(raw)
        if parsed_day is not None:
            parsed = datetime.combine(parsed_day, time.min)
    if parsed is None:
        try:
            parsed = parsedate_to_datetime(raw)
        except (TypeError, ValueError, OverflowError):
            return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, datetime_timezone.utc)
    return parsed


def _matched_keyword(item, keywords, content):
    reported = _first(
        item, "searchTerm", "searchQuery", "query", "input", default=""
    )
    if reported:
        reported_normalized = str(reported).casefold()
        for keyword in keywords:
            if keyword.casefold() in reported_normalized:
                return keyword
    content_normalized = (content or "").casefold()
    return next(
        (keyword for keyword in keywords if keyword.casefold() in content_normalized),
        keywords[0] if keywords else "",
    )


def extract_platform_content(platform, item):
    """Map one Apify dataset item into normalized fields (doc §5). Returns None
    for items without a usable URL (silently dropped upstream)."""
    url = _first(
        item, "url", "webVideoUrl", "postUrl", "facebookUrl", "link", "videoUrl"
    )
    if not url:
        return None
    engagement = {
        key: _count(value) for key, value in _engagement(platform, item).items()
    }
    engagement_count = (
        engagement.get("likes", 0) + engagement.get("shares", 0) + engagement.get("comments", 0)
    )
    content = _first(
        item,
        "text",
        "caption",
        "desc",
        "title",
        "content",
        "message",
        "postText",
        default="",
    )
    return {
        "external_id": _external_id(platform, url),
        "url": url,
        "content": content,
        "author": _author(platform, item),
        "posted_at": _timestamp(item),
        "engagement": engagement,
        "engagement_count": engagement_count,
        "reach": engagement.get("views", 0) or 0,
    }


def _run_and_fetch_items(
    actor_id,
    run_input,
    token,
    *,
    max_items=None,
    max_total_charge_usd=MAX_TOTAL_CHARGE_USD,
):
    """Sole network boundary: trigger the actor run and return dataset items.
    Stubbed in tests. Upstream failures are raised so callers cannot mistake an
    unavailable actor for a successful run with no results."""
    charge_limits = {"maxTotalChargeUsd": max_total_charge_usd}
    if max_items:
        charge_limits["maxItems"] = max_items
    url = f"{APIFY_RUN_URL.format(actor_id=actor_id)}?{urlencode(charge_limits)}"
    payload = json.dumps(run_input).encode("utf-8")
    request = urllib.request.Request(
        url, data=payload, method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "PantauSocialCrawler/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=RUN_TIMEOUT_SECONDS) as response:
            items = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except OSError:
            detail = ""
        detail = " ".join(detail.split())[:300]
        suffix = f": {detail}" if detail else ""
        raise ApifyCollectionError(
            f"Apify actor request failed with HTTP {exc.code}{suffix}"
        ) from exc
    except (urllib.error.URLError, http.client.HTTPException, OSError) as exc:
        raise ApifyCollectionError(f"Apify actor request failed: {exc}") from exc
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ApifyCollectionError("Apify returned an invalid JSON dataset") from exc

    if not isinstance(items, list):
        raise ApifyCollectionError("Apify returned an unexpected dataset payload")
    return items


def _within_period(posted_at, start_date, end_date):
    if not start_date and not end_date:
        return True
    if posted_at is None:
        return False
    local_day = timezone.localtime(posted_at).date()
    return (
        (start_date is None or local_day >= start_date)
        and (end_date is None or local_day <= end_date)
    )


def collect(
    platform,
    keywords,
    token,
    max_results=None,
    *,
    start_date=None,
    end_date=None,
    actor_id=None,
):
    """Run the platform's actor for the given keywords and return a list of
    normalized item dicts (each tagged with platform + matched keyword)."""
    if platform not in ACTOR_CONFIG:
        raise ValueError(f"Platform tidak didukung untuk Apify: {platform}")
    if not keywords:
        return []
    if max_results is None:
        max_results = default_max_results(platform)

    if start_date and end_date and start_date > end_date:
        raise ValueError("Tanggal awal koleksi historis melewati tanggal akhir.")

    cfg = ACTOR_CONFIG[platform]
    run_input = build_actor_input(
        platform,
        keywords,
        max_results,
        start_date=start_date,
        end_date=end_date,
    )
    items = _run_and_fetch_items(
        actor_id or cfg["actor_id"],
        run_input,
        token,
        max_items=max_results,
    )

    normalized = []
    seen_urls = set()
    for item in items:
        try:
            record = extract_platform_content(platform, item)
        except Exception:
            continue
        if record is None:
            continue
        if record["url"] in seen_urls:
            continue
        if not _within_period(record.get("posted_at"), start_date, end_date):
            continue
        seen_urls.add(record["url"])
        record["platform"] = platform
        record["matched_keyword"] = _matched_keyword(
            item, keywords, record.get("content", "")
        )
        normalized.append(record)
        if len(normalized) >= max_results:
            break
    return normalized
