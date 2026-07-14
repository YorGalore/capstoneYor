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
import urllib.error
import urllib.request
from datetime import timedelta

from django.utils import timezone

# platform slug → actor config (doc §4). "x" is this project's slug for Twitter/X.
ACTOR_CONFIG = {
    "x": {"actor_id": "CJdippxWmn9uRfooo", "input_key": "searchTerms", "default_max": 1000, "prefix": "tw"},
    "facebook": {"actor_id": "Ew2lyICEnHMcqRo6T", "input_key": "query", "default_max": 20, "prefix": "fb"},
    "youtube": {"actor_id": "nfyn3ecod9uCDaoVH", "input_key": "query", "default_max": 100, "prefix": "yt"},
    "tiktok": {"actor_id": "wVJo1lJBw0WIxslPI", "input_key": "keyword", "default_max": 100, "prefix": "tt"},
    "instagram": {"actor_id": "culc72xb7MP3EbaeX", "input_key": "search", "default_max": 100, "prefix": "ig"},
}

APIFY_RUN_URL = "https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items"
RUN_TIMEOUT_SECONDS = 300


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


def build_actor_input(platform, keywords, max_results):
    """Build the actor run input for a platform (doc §4.1-4.5)."""
    now = timezone.now()
    if platform == "x":
        since = (now - timedelta(hours=3)).strftime("%Y-%m-%d_%H:%M:%S_UTC")
        until = now.strftime("%Y-%m-%d_%H:%M:%S_UTC")
        return {
            "searchTerms": [f"{kw} lang:in since:{since} until:{until}" for kw in keywords],
            "maxItems": max_results,
            "lang": "in",
            "filter:has_engagement": True,
            "filter:safe": True,
            "queryType": "Top",
        }
    if platform == "youtube":
        return {
            "query": keywords[0],
            "maxResults": max(20, max_results),
            "lang": "id", "geo": "ID", "sortBy": "views",
            "type": "shorts", "uploadDate": "today",
            "scrapeAllResults": False,
        }
    if platform == "instagram":
        return {
            "startUrls": [
                f"https://www.instagram.com/explore/tags/{kw.replace(' ', '')}" for kw in keywords
            ],
            "maxItems": max_results,
            "until": now.strftime("%Y-%m-%d"),
        }
    if platform == "tiktok":
        return {
            "keyword": keywords[0],
            "maxResults": max_results,
            "datePosted": "yesterday", "region": "ID",
            "scrapeMode": "keyword", "sortBy": "latest",
        }
    if platform == "facebook":
        today = now.strftime("%Y-%m-%d")
        return {
            "query": keywords[0],
            "maxResults": max_results,
            "start_date": today, "end_date": today,
            "location_uid": "ID", "recent_posts": True,
        }
    cfg = ACTOR_CONFIG[platform]
    return {cfg["input_key"]: keywords, "maxItems": max_results * len(keywords)}


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
            "likes": _first(item, "likes", "likeCount", default=0),
            "comments": _first(item, "comments", "commentCount", default=0),
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
            "likes": _first(item, "reactions", "likes", default=0),
            "shares": _first(item, "reshares", "shares", default=0),
            "comments": _first(item, "comments", default=0),
        }
    return {}


def _author(platform, item):
    author = item.get("author")
    if isinstance(author, dict):
        return _first(author, "userName", "username", "name", "handle", default="")
    meta = item.get("authorMeta")
    if isinstance(meta, dict):
        return _first(meta, "name", "nickName", "uniqueId", default="")
    return _first(item, "ownerUsername", "channelName", "author", default="") or ""


def extract_platform_content(platform, item):
    """Map one Apify dataset item into normalized fields (doc §5). Returns None
    for items without a usable URL (silently dropped upstream)."""
    url = _first(item, "url", "webVideoUrl", "postUrl", "link", "videoUrl")
    if not url:
        return None
    engagement = _engagement(platform, item)
    engagement_count = (
        engagement.get("likes", 0) + engagement.get("shares", 0) + engagement.get("comments", 0)
    )
    return {
        "external_id": _external_id(platform, url),
        "url": url,
        "content": _first(item, "text", "caption", "desc", "title", "content", default=""),
        "author": _author(platform, item),
        "engagement": engagement,
        "engagement_count": engagement_count,
        "reach": engagement.get("views", 0) or 0,
    }


def _run_and_fetch_items(actor_id, run_input, token):
    """Sole network boundary: trigger the actor run and return dataset items.
    Stubbed in tests."""
    url = f"{APIFY_RUN_URL.format(actor_id=actor_id)}?token={token}"
    payload = json.dumps(run_input).encode("utf-8")
    request = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "PantauSocialCrawler/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=RUN_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError):
        return []


def collect(platform, keywords, token, max_results=None):
    """Run the platform's actor for the given keywords and return a list of
    normalized item dicts (each tagged with platform + matched keyword)."""
    if platform not in ACTOR_CONFIG:
        raise ValueError(f"Platform tidak didukung untuk Apify: {platform}")
    if not keywords:
        return []
    if max_results is None:
        max_results = default_max_results(platform)

    cfg = ACTOR_CONFIG[platform]
    run_input = build_actor_input(platform, keywords, max_results)
    items = _run_and_fetch_items(cfg["actor_id"], run_input, token)

    normalized = []
    for item in items:
        try:
            record = extract_platform_content(platform, item)
        except Exception:
            continue
        if record is None:
            continue
        record["platform"] = platform
        record["matched_keyword"] = keywords[0]
        normalized.append(record)
    return normalized
