"""Public social-comment collection through dedicated Apify actors.

Search actors discover relevant public posts. Comment actors then receive a small,
bounded set of those post URLs and return comment bodies as first-class Mention
records. The feature is deliberately opt-in because comment collection has a
separate cost and a materially larger privacy/retention footprint.
"""
import hashlib
from datetime import datetime, timezone as datetime_timezone

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.analytics.models import Mention

from .apify_crawler import _external_id, _first, _run_and_fetch_items


COMMENT_ACTORS = {
    "x": {
        "actor_id": "clappi~x-twitter-comments-scraper",
        "input": lambda urls, maximum: {
            "postUrls": urls, "maxCommentsPerPost": maximum,
        },
    },
    "facebook": {
        "actor_id": "unseenuser~fb-comments",
        "input": lambda urls, maximum: {
            "postUrls": urls,
            "maxComments": maximum,
            "fetchReplies": False,
            "excludeAuthorGender": True,
        },
    },
    "instagram": {
        "actor_id": "futurizerush~instagram-comment-scraper",
        "input": lambda urls, maximum: {
            "postUrls": urls, "maxComments": maximum, "includeReplies": False,
        },
    },
    "tiktok": {
        "actor_id": "kawsar~tiktok-comments-scraper",
        "input": lambda urls, maximum: {
            "postUrls": urls,
            "maxCommentsPerPost": maximum,
            "includeReplies": False,
        },
    },
    "youtube": {
        "actor_id": "scrapesmith~youtube-comment-scraper",
        "input": lambda urls, maximum: {
            "videoIds": urls, "maxComments": maximum, "sortBy": "newest",
        },
    },
}


def supported_platforms():
    return list(COMMENT_ACTORS)


def _timestamp(item):
    value = _first(
        item,
        "createdAt",
        "created_at",
        "publishedAt",
        "timestamp",
        "createTime",
        default=None,
    )
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=datetime_timezone.utc)
    parsed = parse_datetime(str(value))
    if parsed is None:
        return None
    return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed


def _comment_payload(item):
    nested = item.get("comment")
    return nested if isinstance(nested, dict) else item


def _parent_url(platform, item, payload):
    if platform == "x":
        return _first(item, "post_url", "postUrl", default="")
    if platform == "facebook":
        return _first(item, "postUrl", default="")
    if platform == "instagram":
        return _first(item, "postUrl", default="")
    if platform == "tiktok":
        return _first(
            item, "searchQuery", "videoWebUrl", "submittedVideoUrl", "input", default=""
        )
    if platform == "youtube":
        return _first(item, "videoUrl", "url", default="")
    return _first(item, "postUrl", "parentUrl", default="")


def _comment_text(payload):
    return _first(
        payload, "text", "commentText", "comment", "content", "message", default=""
    )


def _comment_author(payload):
    author = payload.get("author")
    if isinstance(author, dict):
        return _first(
            author, "username", "userName", "name", "displayName", default=""
        )
    return _first(
        payload,
        "username",
        "uniqueId",
        "authorName",
        "nickname",
        "author",
        default="",
    ) or ""


def _comment_identifier(payload):
    return str(_first(
        payload,
        "commentId",
        "comment_id",
        "cid",
        "id",
        default="",
    ) or "")


def _comment_engagement(payload):
    likes = _first(
        payload, "likeCount", "likes", "commentLikeCount", "diggCount", default=0
    )
    replies = _first(
        payload, "replyCount", "repliesCount", "reply_comment_total", default=0
    )
    return {
        "likes": int(likes or 0),
        "comments": int(replies or 0),
    }


def extract_comment(platform, item, matched_keyword=""):
    """Normalize one comment-actor row into an ingestion item."""
    if platform not in COMMENT_ACTORS:
        raise ValueError(f"Platform komentar tidak didukung: {platform}")
    payload = _comment_payload(item)
    text = _comment_text(payload)
    parent_url = _parent_url(platform, item, payload)
    if not text or not parent_url:
        return None

    author = _comment_author(payload)
    identifier = _comment_identifier(payload)
    digest_seed = f"{platform}|{parent_url}|{identifier}|{author}|{text}"
    digest = hashlib.sha256(digest_seed.encode("utf-8")).hexdigest()[:20]
    comment_url = _first(
        payload, "commentUrl", "comment_url", "url", default=""
    )
    # Multiple comments commonly share the parent URL. Mention.source_url is
    # unique, so a stable fragment preserves clickability without collisions.
    source_url = (
        comment_url
        if comment_url and comment_url != parent_url
        else f"{parent_url}#pantau-comment-{identifier or digest}"
    )
    engagement = _comment_engagement(payload)
    return {
        "external_id": f"cm-{platform}-{identifier or digest}",
        "parent_external_id": _external_id(platform, parent_url),
        "url": source_url,
        "content": text,
        "author": author,
        "posted_at": _timestamp(payload),
        "engagement": engagement,
        "engagement_count": engagement["likes"] + engagement["comments"],
        "reach": 0,
        "platform": platform,
        "matched_keyword": matched_keyword,
        "content_type": Mention.CONTENT_COMMENT,
    }


def _flatten(items):
    for item in items:
        yield item
        replies = item.get("replies")
        if isinstance(replies, list):
            for reply in replies:
                if isinstance(reply, dict):
                    merged = dict(reply)
                    for key in (
                        "post_url", "postUrl", "videoUrl", "searchQuery",
                        "videoWebUrl", "submittedVideoUrl", "input",
                    ):
                        if key in item and key not in merged:
                            merged[key] = item[key]
                    yield merged


def collect(
    platform,
    parent_items,
    token,
    max_comments_per_post=25,
    *,
    start_date=None,
    end_date=None,
):
    """Collect comments for normalized parent post items.

    ``parent_items`` is bounded by the orchestrator before this call. Only public
    post URLs are sent to the actor; private/closed discussions remain out of scope.
    """
    if platform not in COMMENT_ACTORS:
        return []
    urls = list(dict.fromkeys(
        item.get("url") for item in parent_items if item.get("url")
    ))
    if not urls:
        return []
    cfg = COMMENT_ACTORS[platform]
    raw_items = _run_and_fetch_items(
        cfg["actor_id"],
        cfg["input"](urls, max_comments_per_post),
        token,
        max_items=len(urls) * max_comments_per_post,
    )
    keyword_by_parent = {
        item.get("url"): item.get("matched_keyword", "") for item in parent_items
    }
    normalized = []
    for raw in _flatten(raw_items):
        parent = _parent_url(platform, raw, _comment_payload(raw))
        record = extract_comment(
            platform, raw, matched_keyword=keyword_by_parent.get(parent, "")
        )
        if record is None:
            continue
        if start_date or end_date:
            posted_at = record.get("posted_at")
            if posted_at is None:
                continue
            local_day = timezone.localtime(posted_at).date()
            if start_date and local_day < start_date:
                continue
            if end_date and local_day > end_date:
                continue
        normalized.append(record)
    return normalized
