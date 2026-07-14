"""Coordinated Inauthentic Behavior detection (FR-26.1).

Computes coordination signals over a set of mentions — near-duplicate text,
abnormally synchronized posting times, and shared authorship patterns — into a
composite score, and flags clusters above a configurable threshold **for human
analyst review only**. The engine never takes automated action against any
account (FR-26.2): it writes a flagged cluster and stops there.

The scoring method is intentionally transparent and inspectable, since a false
positive here can unfairly discredit genuine grassroots activity.
"""
import re
from decimal import Decimal
from statistics import median

from django.utils import timezone

from apps.analytics.models import Mention

from .models import ClusterAccount, CoordinationCluster, CoordinationSignal, DuplicateTextSample

WORD_RE = re.compile(r"\w+", re.UNICODE)

# A pair of posts is "near-duplicate" above this Jaccard similarity.
NEAR_DUPLICATE_THRESHOLD = 0.6
# Posts within this many seconds of each other count as synchronized.
SYNC_WINDOW_SECONDS = 300
DEFAULT_THRESHOLD = 0.6

SIGNAL_WEIGHTS = {
    CoordinationSignal.SIGNAL_TEXT_SIMILARITY: Decimal("0.45"),
    CoordinationSignal.SIGNAL_TIME_SYNC: Decimal("0.35"),
    CoordinationSignal.SIGNAL_SHARED_MEDIA: Decimal("0.20"),
}


def _tokens(text):
    return set(WORD_RE.findall((text or "").lower()))


def text_similarity(a, b):
    """Jaccard similarity between two texts (0.0–1.0)."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def time_sync_score(timestamps):
    """How tightly a set of posts clusters in time (0.0–1.0). Needs >= 2 posts."""
    if len(timestamps) < 2:
        return 0.0
    ordered = sorted(timestamps)
    gaps = [
        (ordered[i + 1] - ordered[i]).total_seconds() for i in range(len(ordered) - 1)
    ]
    typical_gap = median(gaps)
    if typical_gap >= SYNC_WINDOW_SECONDS:
        return 0.0
    return round(1.0 - (typical_gap / SYNC_WINDOW_SECONDS), 3)


def _group_near_duplicates(mentions):
    """Group mentions into buckets of mutually near-duplicate text."""
    groups = []
    for mention in mentions:
        for group in groups:
            if text_similarity(mention.content_snippet, group[0].content_snippet) >= NEAR_DUPLICATE_THRESHOLD:
                group.append(mention)
                break
        else:
            groups.append([mention])
    return groups


def _next_cluster_code():
    existing = CoordinationCluster.objects.count() + 1
    return f"Klaster-{existing:02d}"


def detect(project, issue, threshold=DEFAULT_THRESHOLD, since=None):
    """Score mentions on an issue and persist any cluster above ``threshold`` as
    flagged-for-review. Returns the list of created clusters."""
    qs = Mention.objects.filter(project=project, issue=issue).select_related("author")
    if since is not None:
        qs = qs.filter(posted_at__gte=since)

    clusters = []
    for group in _group_near_duplicates(list(qs.order_by("posted_at"))):
        handles = {m.author_handle for m in group}
        # Coordination is a property of multiple accounts acting together; a single
        # account repeating itself is not a network (FR-26.1).
        if len(handles) < 2:
            continue

        similarity = _mean_pairwise_similarity(group)
        sync = time_sync_score([m.posted_at for m in group])
        shared_media = _shared_media_score(group)

        scores = {
            CoordinationSignal.SIGNAL_TEXT_SIMILARITY: Decimal(str(round(similarity, 2))),
            CoordinationSignal.SIGNAL_TIME_SYNC: Decimal(str(round(sync, 2))),
            CoordinationSignal.SIGNAL_SHARED_MEDIA: Decimal(str(round(shared_media, 2))),
        }
        composite = sum(scores[k] * w for k, w in SIGNAL_WEIGHTS.items())
        composite = composite.quantize(Decimal("0.01"))
        if composite < Decimal(str(threshold)):
            continue

        clusters.append(_persist(issue, group, handles, scores, composite))
    return clusters


def _mean_pairwise_similarity(group):
    pairs = [
        text_similarity(group[i].content_snippet, group[j].content_snippet)
        for i in range(len(group))
        for j in range(i + 1, len(group))
    ]
    return sum(pairs) / len(pairs) if pairs else 0.0


def _shared_media_score(group):
    """Proxy for shared media assets: repeated identical source URLs across accounts."""
    urls = [m.source_url for m in group if m.source_url]
    if len(urls) < 2:
        return 0.0
    return 1.0 - (len(set(urls)) / len(urls))


def _persist(issue, group, handles, scores, composite):
    cluster = CoordinationCluster.objects.create(
        issue=issue,
        cluster_code=_next_cluster_code(),
        score=composite,
        status=CoordinationCluster.STATUS_FLAGGED,  # human review only (FR-26.2)
        account_count=len(handles),
        detected_at=timezone.now(),
        note=f"{len(handles)} akun · {len(group)} unggahan nyaris identik",
    )
    for signal_type, value in scores.items():
        CoordinationSignal.objects.create(
            cluster=cluster, signal_type=signal_type, score=value
        )

    for handle in sorted(handles):
        posts = [m for m in group if m.author_handle == handle]
        cluster.accounts.create(
            handle=handle,
            role=ClusterAccount.ROLE_AMPLIFIER,
            reach=max((m.reach_estimate for m in posts), default=0),
            post_count=len(posts),
        )

    for mention in group[:5]:
        DuplicateTextSample.objects.create(
            cluster=cluster,
            account_handle=mention.author_handle,
            posted_at=mention.posted_at,
            text=mention.content_snippet,
            highlighted_phrase=_shared_phrase(group),
        )
    return cluster


def _shared_phrase(group, max_words=8):
    common = set.intersection(*[_tokens(m.content_snippet) for m in group]) if group else set()
    if not common:
        return ""
    first = _tokens(group[0].content_snippet)
    ordered = [w for w in WORD_RE.findall(group[0].content_snippet.lower()) if w in common]
    return " ".join(ordered[:max_words])
