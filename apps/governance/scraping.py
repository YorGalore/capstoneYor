"""Real, live news scraping: fetches RSS feeds over HTTP and turns matching
items into `analytics.Mention` rows. No mocked/simulated network calls —
only the automated test suite stubs `fetch_feed` at the network boundary.
"""
import http.client
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from django.db import models as django_models
from django.utils import timezone

from apps.analytics.models import Mention

USER_AGENT = "PantauNewsBot/1.0 (+https://pantau.local; monitoring console)"
FETCH_TIMEOUT_SECONDS = 10
MAX_ITEMS_PER_SOURCE = 40

TAG_RE = re.compile(r"<[^>]+>")
WORD_RE = re.compile(r"[a-zA-Z]+")

POSITIVE_WORDS = {
    "bagus", "baik", "berhasil", "sukses", "meningkat", "membaik", "positif",
    "apresiasi", "dukungan", "capaian", "prestasi", "unggul", "lancar",
    "manfaat", "optimis", "puas", "solusi", "efektif", "membantu", "naik",
}
NEGATIVE_WORDS = {
    "buruk", "gagal", "krisis", "turun", "menurun", "negatif", "korupsi",
    "kecewa", "protes", "tolak", "kritik", "masalah", "rusak", "bencana",
    "darurat", "kesulitan", "kerugian", "konflik", "ancaman", "marah",
}


class ScrapeError(Exception):
    pass


def _http_get(url):
    if not url.startswith(("http://", "https://")):
        raise ScrapeError(f"skema URL tidak didukung: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
            return response.read()
    except (urllib.error.URLError, http.client.HTTPException, OSError) as exc:
        raise ScrapeError(str(exc)) from exc


def check_reachable(url):
    """Real connectivity probe used by the "Uji Koneksi" button."""
    try:
        _http_get(url)
    except ScrapeError:
        return False
    return True


def _parse_pub_date(raw):
    if not raw:
        return timezone.now()
    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return timezone.now()
    if parsed is None:
        return timezone.now()
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_default_timezone())
    return parsed


def fetch_feed(feed_url):
    """Fetch and parse a real RSS 2.0 feed. Returns a list of item dicts."""
    raw = _http_get(feed_url)
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ScrapeError(f"gagal mengurai RSS: {exc}") from exc

    items = []
    for node in root.findall(".//item")[:MAX_ITEMS_PER_SOURCE]:
        title = (node.findtext("title") or "").strip()
        link = (node.findtext("link") or "").strip()
        description = TAG_RE.sub("", node.findtext("description") or "").strip()
        items.append({
            "title": title,
            "link": link,
            "description": description,
            "posted_at": _parse_pub_date(node.findtext("pubDate")),
        })
    return items


def score_sentiment(text):
    words = set(WORD_RE.findall(text.lower()))
    positive_hits = len(words & POSITIVE_WORDS)
    negative_hits = len(words & NEGATIVE_WORDS)
    if positive_hits > negative_hits:
        return Mention.SENTIMENT_POSITIVE
    if negative_hits > positive_hits:
        return Mention.SENTIMENT_NEGATIVE
    return Mention.SENTIMENT_NEUTRAL


def _emotion_for_sentiment(sentiment):
    return {
        Mention.SENTIMENT_POSITIVE: Mention.EMOTION_JOY,
        Mention.SENTIMENT_NEGATIVE: Mention.EMOTION_ANGER,
    }.get(sentiment, Mention.EMOTION_TRUST)


def run_scan(project, platform, domains, keywords):
    """Fetch every domain's RSS feed and persist real, keyword-matching
    articles as Mention rows. Returns a summary dict for the UI/audit log.
    """
    active_keywords = [k for k in keywords if k.is_active]
    new_mentions = 0
    sources_scanned = 0
    errors = []
    gained_matches = {}

    for domain in domains:
        if not domain.feed_url:
            continue
        sources_scanned += 1
        try:
            items = fetch_feed(domain.feed_url)
        except ScrapeError as exc:
            errors.append(f"{domain.domain}: {exc}")
            domain.status = domain.STATUS_NEEDS_REVIEW
            domain.last_tested_at = timezone.now()
            domain.save(update_fields=["status", "last_tested_at"])
            continue

        domain.status = domain.STATUS_ACTIVE
        domain.last_tested_at = timezone.now()
        domain.save(update_fields=["status", "last_tested_at"])

        for item in items:
            if not item["link"]:
                continue
            haystack = f"{item['title']} {item['description']}".lower()
            matched_keyword = next(
                (k for k in active_keywords if k.keyword.lower() in haystack), None
            )
            if matched_keyword is None:
                continue

            sentiment = score_sentiment(haystack)
            _, created = Mention.objects.get_or_create(
                source_url=item["link"],
                defaults={
                    "project": project,
                    "platform": platform,
                    "author_handle": domain.domain,
                    "content_snippet": item["title"][:500] or item["description"][:500],
                    "sentiment": sentiment,
                    "emotion": _emotion_for_sentiment(sentiment),
                    "posted_at": item["posted_at"],
                    "is_political": False,
                    "matched_keyword": matched_keyword.keyword,
                    "is_scraped": True,
                },
            )
            if created:
                new_mentions += 1
                gained_matches[matched_keyword.id] = gained_matches.get(matched_keyword.id, 0) + 1

    for keyword in active_keywords:
        gained = gained_matches.get(keyword.id, 0)
        if gained:
            keyword.match_count = django_models.F("match_count") + gained
            keyword.save(update_fields=["match_count"])

    return {
        "sources_scanned": sources_scanned,
        "new_mentions": new_mentions,
        "errors": errors,
    }
