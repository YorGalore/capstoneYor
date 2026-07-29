# Apify Integration — Social Crawler (Team 1)

**Service:** `team1-crawler/services/social-crawler/`
**SDK:** `apify-client==1.8.0` (+ `apify-shared==1.3.0`)
**Purpose:** Crawl TikTok, YouTube (Shorts), Instagram, Twitter/X, and Facebook for a set of keywords, normalize the results, and hand them off to the enrichment/ingestion stages of the KPM pipeline. News/media-online sources are **not** handled here — those go through `crawl4ai` in the separate News Crawler service.

> **Django platform implementation (29 July 2026):** the live connector in
> `apps/governance/apify_crawler.py` supersedes the legacy Actor table below for
> this repository. It supports inclusive historical windows of at most 31 days,
> per-platform result caps, API-level `maxItems` and `maxTotalChargeUsd` guards,
> publication-time filtering, and linked comment collection. Credential
> precedence is project-encrypted token → `APIFY_API_TOKEN` → `APIFY_KEY`; the
> environment fallback is never copied into the database or shown in the UI.
> Current configured post Actors are `apidojo/tweet-scraper`,
> `apify/instagram-scraper`, `clockworks/tiktok-scraper`,
> `streamers/youtube-scraper`, and `scraper_one/facebook-posts-search`.
> The legacy microservice analysis remains below as historical architecture
> documentation.

---

## 1. Where it sits in the pipeline

```
Orchestrator (Celery task, tasks.py)
   │
   ├─ POST NEWS_CRAWLER_URL/crawl        (media_online only)
   └─ POST SOCIAL_CRAWLER_URL/crawl      (all non-media_online platforms)
            │
            ▼
   Social Crawler service (FastAPI, this doc)
            │  for each platform × keyword:
            │    ApifyClient.actor(actor_id).call(run_input=...)
            │    ApifyClient.dataset(datasetId).iterate_items()
            │
            ├─ download media (image/audio URLs found in results)
            ├─ upload media   → MinIO bucket `media`
            └─ upload batch   → MinIO bucket `raw-data` (one JSON file per run)
            │
            ▼
   AI Service (enrichment) → Ingestion Service → PostgreSQL (kpm_crawler)
```

The Orchestrator dispatches both crawlers **concurrently** (`asyncio.gather`) with a 10800s (3h) timeout per call, and merges the returned `minio_paths` from each (`team1-crawler/services/orchestrator/app/tasks.py:299-324`).

---

## 2. Service's own HTTP API

`team1-crawler/services/social-crawler/app/main.py`

| Method | Path | Request body | Response | Notes |
|---|---|---|---|---|
| `GET` | `/health` | — | `{service, status, version}` | Standard health probe |
| `POST` | `/crawl` | `CrawlRequest` | `CrawlResponse` | Main entrypoint, called by the Orchestrator |

**`CrawlRequest`** (`shared/schemas.py`):
```python
keywords: list[str]                          # required, from orchestrator/keyword manager
batch_id: str | None                         # auto-generated if omitted: "social-<unix_ts>"
platforms: list[PlatformType]                # empty → defaults to all 5 platforms
max_results_per_keyword: int | None           # 1–100 if set via API; unset → per-platform default (see §4)
```
If `platforms` is empty, `main.py` defaults to `[TIKTOK, YOUTUBE, INSTAGRAM, TWITTER, FACEBOOK]`.

**`CrawlResponse`**:
```python
batch_id: str
status: str            # "completed" | "error"
message: str
items_found: int
minio_paths: list[str] # e.g. ["raw-data/social-172xxxx-social.json"]
```

If `APIFY_API_TOKEN` isn't configured, the call short-circuits and returns `status="error"` immediately (`engine.py:42-43`) — no exception, no partial crawl.

---

## 3. Apify client usage

`team1-crawler/services/social-crawler/app/engine.py`

```python
from apify_client import ApifyClient

client = ApifyClient(runtime.apify_api_token)
run = client.actor(cfg["actor_id"]).call(run_input=actor_input, timeout_secs=300)
items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
```

- One **synchronous actor run** per `(platform, keyword)` pair — the loop is sequential per platform (not parallelized across keywords), each capped at `timeout_secs=300` (5 min).
- Failures are caught per-call (`try/except Exception`) and logged; a failed actor run for one keyword does **not** abort the rest of the batch (`engine.py:68-73`).
- The Apify token itself is **not** read from `.env` directly at call time — it comes from `get_runtime_service_settings()`, which:
  1. Tries a cached value (TTL `RUNTIME_SETTINGS_TTL`, default 300s).
  2. On miss, calls the backend's internal endpoint `GET /v1/internal/team1/runtime-settings` (Bearer `BACKEND_INTERNAL_API_TOKEN`) to pull `APIFY_API_TOKEN` from the `app_runtime_settings` DB table (Dev Settings UI source of truth).
  3. Falls back to the local `.env` value (`shared/config.py` `APIFY_API_TOKEN`) if the backend call fails or returns nothing, with a stale-cache fallback in between.

This means the Apify token can be rotated live from the **Dev Settings** page without redeploying the crawler.

---

## 4. Actor configuration per platform

`team1-crawler/services/social-crawler/app/platforms.py` — `ACTOR_CONFIG`

| Platform | Actor ID | Input key | Default max results/keyword* |
|---|---|---|---|
| Twitter/X | `CJdippxWmn9uRfooo` | `searchTerms` | 1000 |
| Facebook | `Ew2lyICEnHMcqRo6T` | `query` | 20 |
| YouTube | `nfyn3ecod9uCDaoVH` | `query` | 100 |
| TikTok | `wVJo1lJBw0WIxslPI` | `keyword` | 100 |
| Instagram | `culc72xb7MP3EbaeX` | `search` | 100 |

\* Applied only when the caller doesn't pass `max_results_per_keyword` explicitly (`engine.py get_platform_limit`). `media_online` is explicitly skipped in this service even if included in the request.

### 4.1 Twitter/X actor input
```python
since, until = last 3 hours, formatted "%Y-%m-%d_%H:%M:%S_UTC"
{
  "searchTerms": [f"{kw} lang:in since:{since} until:{until}" for kw in keywords],
  "maxItems": max_results,
  "lang": "in",
  "filter:has_engagement": True,
  "filter:images": True,
  "filter:media": True,
  "filter:news": True,
  "filter:twimg": True,
  "filter:safe": True,
  "queryType": "Top",
}
```
Rolling 3-hour recency window baked into the query string itself — matches the "partial pipeline every 3 hours" crawl schedule.

### 4.2 YouTube actor input
```python
{
  "query": keywords[0],           # only the first keyword is used
  "maxResults": max(20, max_results),
  "lang": "id", "geo": "ID",
  "sortBy": "views",
  "type": "shorts",               # Shorts only
  "uploadDate": "today",
  "features": {"subtitles": True},
  "videoDepthDetails": "detailed",
  "scrapeAllResults": False,
  "local": False,
}
```

### 4.3 Instagram actor input
```python
{
  "startUrls": [f"https://www.instagram.com/explore/tags/{kw_no_spaces}" for kw in keywords],
  "maxItems": max_results,
  "until": today (YYYY-MM-DD),
  "customMapFunction": "(object) => { return {...object} }",
}
```
Crawls hashtag "explore" pages rather than a keyword search — keywords are converted to hashtags by stripping spaces.

### 4.4 TikTok actor input
```python
{
  "keyword": keywords[0],          # only the first keyword is used
  "maxResults": max_results,
  "datePosted": "yesterday",
  "region": "ID",
  "scrapeMode": "keyword",
  "sortBy": "latest",
}
```

### 4.5 Facebook actor input
```python
{
  "query": keywords[0],            # only the first keyword is used
  "maxResults": max_results,
  "start_date": today, "end_date": today,
  "location_uid": "ID",
  "recent_posts": True,
}
```

### 4.6 Fallback (any platform not special-cased)
```python
{cfg["input_key"]: keywords, "maxItems": max_results * len(keywords)}
```
(Not reachable today since all 5 configured platforms have dedicated branches above — kept as a defensive default.)

---

## 5. Result extraction & normalization

`extract_platform_content(platform, item)` maps each Apify dataset item into a common dict, which is then wrapped into a `RawContent` model (`shared/schemas.py`). Common fields produced for every platform:

- `external_id` — `"<platform-prefix>-<md5(url)[:12]>"` (e.g. `tt-...`, `yt-...`, `ig-...`, `tw-...`, `fb-...`)
- `url`, `title`, `content`, `author`, `published_at`
- `metadata.engagement` — platform-specific counters (see below)
- `metadata.media` / `media_raw` — extracted image/audio URLs, used for the media download step (§6)

Any item missing a usable `url` is dropped (returns `None`). Extraction is wrapped in try/except; a malformed item logs an error and is skipped rather than failing the whole batch.

| Platform | Engagement fields captured | Media captured |
|---|---|---|
| TikTok | views (`playCount`), likes (`diggCount`), shares (`shareCount`), comments (`commentCount`), saves (`collectCount`) | cover image (`covers.default` / `videoMeta.coverUrl`), audio (`musicMeta.playUrl`), `duration_sec` |
| YouTube | views, likes, comments | best-resolution thumbnail |
| Instagram | likes, comments | post image; also captures post `type` |
| Twitter/X | retweets, replies, likes, quotes, views, bookmarks | first media item's `media_url_https` if present |
| Facebook | comments, reactions, reshares | photo (`image.uri`) or first `album_preview` image |

Content text is passed through `clean_social_text()` (`app/cleaning.py`) before being stored.

---

## 6. Media download & storage

For every non-empty `image`/`audio` URL found in `media_raw`:
1. `download_media_file(media_url)` (`shared/utils.py`) fetches the raw bytes.
2. File is named `"<external_id>-<image|audio>.<jpg|mp3>"`.
3. Uploaded to MinIO via `upload_media(client, batch_id, fname, bytes, subfolder=media_key, ct=...)` → stored at `media/<batch_id>/<image|audio>/<filename>`, content-type `image/jpg` or `audio/mpeg`.
4. The resulting MinIO path is written back into `metadata.media[f"{media_key}_path"]` so downstream (AI enrichment / vision-caption / audio-transcription services) can locate the file.

This download step runs **inline, per item, sequentially** — it's not batched or parallelized, which is a real throughput consideration at high `max_results` volumes (e.g. Twitter's 1000/keyword default).

---

## 7. Batch output

All extracted+downloaded records across all platforms/keywords in one `/crawl` call are collected into a single list and uploaded once as a JSON array:

```python
minio_path = await upload_batch_raw_json(minio, f"{batch_id}-social.json", all_records)
```
→ stored at `raw-data/<batch_id>-social.json` (bucket `MINIO_BUCKET_RAW`, default `raw-data`).

This path is returned in `CrawlResponse.minio_paths` and is what the Orchestrator collects and forwards to the AI Service for enrichment.

---

## 8. Configuration reference

| Setting | Source | Default | Notes |
|---|---|---|---|
| `APIFY_API_TOKEN` | `app_runtime_settings` (scope `team1`) → `.env` fallback | `""` | Required; missing token = immediate error response, no crawl attempted |
| Per-actor `timeout_secs` | hardcoded in `engine.py` | `300` | Per `(platform, keyword)` actor call |
| Orchestrator→Social Crawler HTTP timeout | hardcoded in `orchestrator/app/tasks.py` | `10800` (3h) | Covers the whole `/crawl` batch across all platforms/keywords |
| `max_results_per_keyword` | request param or per-platform default | Twitter 1000 / YouTube 100 / TikTok 100 / Instagram 100 / Facebook 20 | API-level `CrawlRequest.max_results_per_keyword` is constrained 1–100 when explicitly provided; the higher defaults (e.g. Twitter 1000) only apply when the field is omitted entirely |

---

## 9. Known limitations (observed in code, not assumptions)

- **Single-keyword actors**: YouTube, TikTok, and Facebook actor inputs only use `keywords[0]` — if the orchestrator passes multiple keywords per platform call, only the first is actually searched for those three platforms (Twitter and Instagram do use the full keyword list).
- **No cross-keyword/platform parallelism**: actor calls loop sequentially per keyword within a platform; only the platform-level dispatch to News vs Social crawler is concurrent.
- **No retry logic**: a failed Apify actor call (`client.actor(...).call(...)` raising) is logged and skipped — there's no retry/backoff before moving to the next keyword.
- **Media download is sequential and unbounded**: no concurrency limit or size cap observed on `download_media_file`, which could be slow for large batches with many images (e.g. Twitter at 1000 items/keyword).
- **Facebook capped much lower** (20 vs 100+ elsewhere) — likely a deliberate cost/reliability constraint on that specific actor, not documented elsewhere in code.
