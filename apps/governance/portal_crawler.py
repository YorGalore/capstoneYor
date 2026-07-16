"""Respectful custom discovery and article extraction for configured news portals.

Discovery prefers publisher-owned RSS and Google News sitemaps.  Listing pages are
used only where no feed is published.  Every URL is checked against robots.txt;
search/API/tag endpoints are never used, and only links whose visible title already
matches a monitoring keyword are opened as articles.
"""

import json
import re
import threading
import time
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser

from django.utils import timezone


BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
ROBOTS_AGENT = "PantauNewsBot"
REQUEST_TIMEOUT = 20
MAX_RESPONSE_BYTES = 3_000_000
MAX_DISCOVERED = 60
MAX_MATCHES_PER_SOURCE = 20
MAX_CRAWL_DELAY_SECONDS = 10

_crawl_delays = {}
_last_request_at = {}
_rate_lock = threading.Lock()


@dataclass(frozen=True)
class PortalSpec:
    strategy: str
    start_url: str
    article_prefixes: tuple[str, ...]


PORTALS = {
    "jogja.tribunnews.com": PortalSpec(
        "listing", "https://jogja.tribunnews.com/",
        ("https://jogja.tribunnews.com/",),
    ),
    "jogjapolitan.harianjogja.com": PortalSpec(
        "sitemap", "https://www.harianjogja.com/sitemap-news-jogjapolitan.xml",
        ("https://jogjapolitan.harianjogja.com/",),
    ),
    "jogja.antaranews.com": PortalSpec(
        "rss", "https://jogja.antaranews.com/rss/jogja-terkini.xml",
        ("https://jogja.antaranews.com/",),
    ),
    "www.prolimannews.id": PortalSpec(
        "rss", "https://www.prolimannews.id/feed/",
        ("https://www.prolimannews.id/", "http://www.prolimannews.id/"),
    ),
    "rri.co.id": PortalSpec(
        "rss", "https://rri.co.id/rss",
        ("https://rri.co.id/", "https://www.rri.co.id/"),
    ),
    "jogja.viva.co.id": PortalSpec(
        "listing", "https://jogja.viva.co.id/warta",
        ("https://jogja.viva.co.id/",),
    ),
    "www.detik.com": PortalSpec(
        "listing", "https://www.detik.com/jogja/berita",
        ("https://www.detik.com/jogja/",),
    ),
    "www.purworejo24.com": PortalSpec(
        "rss", "https://www.purworejo24.com/feed/",
        ("https://www.purworejo24.com/",),
    ),
    "kominfo.kulonprogokab.go.id": PortalSpec(
        "listing", "https://kominfo.kulonprogokab.go.id/publikasi/berita",
        ("https://kominfo.kulonprogokab.go.id/publikasi/detail/",),
    ),
}


class PortalCrawlError(RuntimeError):
    pass


def _get(url):
    host = urllib.parse.urlparse(url).netloc.lower()
    with _rate_lock:
        delay = _crawl_delays.get(host, 0)
        elapsed = time.monotonic() - _last_request_at.get(host, 0)
        wait_for = max(0, delay - elapsed)
    if wait_for:
        time.sleep(wait_for)

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "text/html,application/rss+xml,application/xml,text/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "id-ID,id;q=0.9,en;q=0.5",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            content_type = response.headers.get("Content-Type", "")
            payload = response.read(MAX_RESPONSE_BYTES + 1)
            if len(payload) > MAX_RESPONSE_BYTES:
                raise PortalCrawlError(f"respons terlalu besar: {url}")
            with _rate_lock:
                _last_request_at[host] = time.monotonic()
            return payload, content_type, response.geturl()
    except PortalCrawlError:
        raise
    except Exception as exc:
        raise PortalCrawlError(f"gagal membuka {url}: {exc}") from exc


def _robots_allows(url):
    parsed = urllib.parse.urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        raw, _content_type, _final_url = _get(robots_url)
    except PortalCrawlError as exc:
        # RFC 9309: a 4xx response means no robots file is available. ANTARA,
        # for example, publishes a public RSS directory but returns 404 here.
        if "HTTP Error 404" in str(exc):
            return True
        # Fail closed: a portal that does not expose a readable robots policy must
        # be reviewed by an operator instead of silently crawled on network/5xx errors.
        return False
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)
    parser.parse(raw.decode("utf-8", "replace").splitlines())
    delay = parser.crawl_delay(ROBOTS_AGENT)
    if delay is None:
        delay = parser.crawl_delay("*")
    if delay is not None:
        with _rate_lock:
            _crawl_delays[parsed.netloc.lower()] = min(float(delay), MAX_CRAWL_DELAY_SECONDS)
    return parser.can_fetch(ROBOTS_AGENT, url)


def check_reachable(domain):
    """Probe a starter through the same robots and request path used by crawl()."""
    spec = PORTALS.get(domain.domain)
    if spec is None:
        return False
    start_url = domain.feed_url or spec.start_url
    if not _robots_allows(start_url):
        return False
    try:
        _get(start_url)
    except PortalCrawlError:
        return False
    return True


def _text(raw, content_type=""):
    match = re.search(r"charset=([\w-]+)", content_type, re.I)
    encoding = match.group(1) if match else "utf-8"
    try:
        return raw.decode(encoding, "replace")
    except LookupError:
        return raw.decode("utf-8", "replace")


def _strip_html(value):
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", value or "")).split())


def _parse_date(value):
    if not value:
        return timezone.now()
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return timezone.now()
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_default_timezone())
    return parsed


def _child_text(node, local_name):
    for child in node.iter():
        if child.tag.rsplit("}", 1)[-1] == local_name and child.text:
            return child.text.strip()
    return ""


def parse_rss(raw):
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise PortalCrawlError(f"RSS/XML tidak valid: {exc}") from exc
    items = []
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] not in {"item", "entry"}:
            continue
        link = _child_text(node, "link")
        if not link:
            for child in node:
                if child.tag.rsplit("}", 1)[-1] == "link" and child.attrib.get("href"):
                    link = child.attrib["href"]
                    break
        body = _child_text(node, "encoded") or _child_text(node, "content")
        description = _child_text(node, "description") or _child_text(node, "summary")
        items.append({
            "title": _child_text(node, "title"),
            "link": link,
            "description": _strip_html(description),
            "body": _strip_html(body),
            "posted_at": _parse_date(
                _child_text(node, "pubDate")
                or _child_text(node, "published")
                or _child_text(node, "updated")
            ),
        })
    return items[:MAX_DISCOVERED]


def parse_sitemap(raw):
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise PortalCrawlError(f"sitemap tidak valid: {exc}") from exc
    items = []
    for node in root:
        local = node.tag.rsplit("}", 1)[-1]
        if local != "url":
            continue
        items.append({
            "title": _child_text(node, "title"),
            "link": _child_text(node, "loc"),
            "description": "",
            "body": "",
            "posted_at": _parse_date(
                _child_text(node, "publication_date") or _child_text(node, "lastmod")
            ),
        })
    return items[:MAX_DISCOVERED]


class _ListingParser(HTMLParser):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.current_href = None
        self.current_text = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.current_href = dict(attrs).get("href")
            self.current_text = []

    def handle_data(self, data):
        if self.current_href is not None:
            self.current_text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.current_href is not None:
            title = " ".join("".join(self.current_text).split())
            url = urllib.parse.urljoin(self.base_url, self.current_href)
            if title:
                self.links.append((title, url))
            self.current_href = None


def parse_listing(raw, base_url, content_type=""):
    parser = _ListingParser(base_url)
    parser.feed(_text(raw, content_type))
    seen = set()
    items = []
    for title, link in parser.links:
        canonical = link.split("#", 1)[0]
        if canonical in seen:
            continue
        seen.add(canonical)
        items.append({
            "title": title, "link": canonical, "description": "", "body": "",
            "posted_at": timezone.now(),
        })
    return items[:MAX_DISCOVERED]


def _jsonld_nodes(value):
    if isinstance(value, list):
        for item in value:
            yield from _jsonld_nodes(item)
    elif isinstance(value, dict):
        yield value
        if "@graph" in value:
            yield from _jsonld_nodes(value["@graph"])


class _ArticleParser(HTMLParser):
    CONTENT_TOKENS = ("article", "content", "read__content", "detail-body", "post-content")

    def __init__(self):
        super().__init__()
        self.meta = {}
        self.h1 = []
        self.in_h1 = False
        self.capture_depth = 0
        self.paragraph_depth = 0
        self.paragraph = []
        self.paragraphs = []
        self.in_jsonld = False
        self.jsonld = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            key = attrs.get("property") or attrs.get("name")
            if key and attrs.get("content"):
                self.meta[key.lower()] = attrs["content"]
        if tag == "h1":
            self.in_h1 = True
        if tag == "script" and "ld+json" in attrs.get("type", "").lower():
            self.in_jsonld = True
            self.jsonld = []
        marker = f"{attrs.get('id', '')} {attrs.get('class', '')}".lower()
        if tag == "article" or any(token in marker for token in self.CONTENT_TOKENS):
            self.capture_depth += 1
        elif self.capture_depth:
            self.capture_depth += 1
        if tag == "p" and self.capture_depth:
            self.paragraph_depth = 1
            self.paragraph = []

    def handle_data(self, data):
        if self.in_h1:
            self.h1.append(data)
        if self.in_jsonld:
            self.jsonld.append(data)
        if self.paragraph_depth:
            self.paragraph.append(data)

    def handle_endtag(self, tag):
        if tag == "h1":
            self.in_h1 = False
        if tag == "script" and self.in_jsonld:
            self.in_jsonld = False
            try:
                value = json.loads("".join(self.jsonld))
            except (json.JSONDecodeError, TypeError):
                value = None
            if value is not None:
                for node in _jsonld_nodes(value):
                    node_type = node.get("@type", "")
                    types = node_type if isinstance(node_type, list) else [node_type]
                    if any(t in {"Article", "NewsArticle", "ReportageNewsArticle"} for t in types):
                        for source, target in [
                            ("headline", "jsonld:title"),
                            ("description", "jsonld:description"),
                            ("articleBody", "jsonld:body"),
                            ("datePublished", "jsonld:date"),
                        ]:
                            if node.get(source):
                                self.meta[target] = str(node[source])
        if tag == "p" and self.paragraph_depth:
            text = " ".join("".join(self.paragraph).split())
            if len(text) >= 30:
                self.paragraphs.append(text)
            self.paragraph_depth = 0
        if self.capture_depth:
            self.capture_depth -= 1


def parse_article(raw, content_type=""):
    parser = _ArticleParser()
    parser.feed(_text(raw, content_type))
    title = (
        parser.meta.get("jsonld:title")
        or parser.meta.get("og:title")
        or " ".join("".join(parser.h1).split())
    )
    body = parser.meta.get("jsonld:body") or "\n".join(parser.paragraphs)
    description = parser.meta.get("jsonld:description") or parser.meta.get("description", "")
    posted_at = _parse_date(
        parser.meta.get("jsonld:date")
        or parser.meta.get("article:published_time")
        or parser.meta.get("datepublished")
    )
    return {"title": title, "description": description, "body": body, "posted_at": posted_at}


def _matches_prefix(url, prefixes):
    return any(url.startswith(prefix) for prefix in prefixes)


def _matched_keyword(item, keywords):
    haystack = f"{item.get('title', '')} {item.get('description', '')} {item.get('body', '')}".lower()
    return next((keyword for keyword in keywords if keyword.lower() in haystack), "")


def crawl(domain, keywords):
    """Discover and extract keyword-matching articles for one configured domain."""
    spec = PORTALS.get(domain.domain)
    if spec is None:
        raise PortalCrawlError(f"belum ada adapter khusus untuk {domain.domain}")
    start_url = domain.feed_url or spec.start_url
    if not _robots_allows(start_url):
        raise PortalCrawlError(f"robots.txt tidak mengizinkan starter {start_url}")

    raw, content_type, final_url = _get(start_url)
    if spec.strategy == "rss":
        discovered = parse_rss(raw)
    elif spec.strategy == "sitemap":
        discovered = parse_sitemap(raw)
    else:
        discovered = parse_listing(raw, final_url, content_type)

    results = []
    for item in discovered:
        link = item.get("link", "")
        if not link or not _matches_prefix(link, spec.article_prefixes):
            continue
        keyword = _matched_keyword(item, keywords)
        if not keyword:
            continue
        if not item.get("body") and _robots_allows(link):
            article_raw, article_type, _article_url = _get(link)
            details = parse_article(article_raw, article_type)
            for key in ("title", "description", "body", "posted_at"):
                if details.get(key):
                    item[key] = details[key]
        item["matched_keyword"] = keyword
        results.append(item)
        if len(results) >= MAX_MATCHES_PER_SOURCE:
            break
    return results
