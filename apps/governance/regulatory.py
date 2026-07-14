"""Regulatory & policy grounding (FR-31).

Grounds generated narrative analysis and daily briefs in a curated corpus of actual
laws, regulations, and SOPs rather than an unaided language model, and returns the
retrieved source passage alongside every hit so a reviewer can verify it
independently (FR-31.4). This is the mitigation for the risk the SRS calls out
explicitly: a model fabricating a plausible-sounding but incorrect regulatory
citation that leadership then acts on or repeats publicly.

Retrieval is lexical (TF-IDF-style scoring over the corpus) rather than a vector
index, so it runs without any external service. The interface is stable, so a real
embedding index can replace `retrieve()` without touching callers.
"""
import math
import re
from collections import Counter

from .models import RegulatoryDocument

WORD_RE = re.compile(r"\w+", re.UNICODE)

# Indonesian + English stopwords that would otherwise dominate lexical scoring.
STOPWORDS = {
    "yang", "dan", "atau", "di", "ke", "dari", "pada", "untuk", "dengan", "dalam",
    "adalah", "itu", "ini", "oleh", "akan", "tidak", "the", "a", "an", "of", "to",
    "in", "for", "and", "or", "is", "are",
}

RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"
RISK_LABELS = {RISK_LOW: "Rendah", RISK_MEDIUM: "Sedang", RISK_HIGH: "Tinggi"}

# A hit below this score is not a credible citation — return nothing rather than
# surface a weak match that reads as authoritative.
MIN_SCORE = 0.05
# How much a query term appearing in the regulation's *title* counts relative to
# the same term buried in its body.
TITLE_WEIGHT = 0.5


# Bahasa Indonesia is agglutinative: "penyaluran", "disalurkan", and "salurkan"
# all share the stem "salur", and "terlambat" shares "lambat". Without stripping
# affixes, exact-token matching misses citations that are plainly relevant, so a
# real regulation would fail to surface. This is a deliberately conservative
# stemmer — it strips only common, unambiguous affixes.
PREFIXES = ("keter", "peny", "peng", "pen", "pem", "per", "ber", "ter", "di", "ke", "se", "me")
SUFFIXES = ("kannya", "annya", "kan", "an", "i", "nya")
MIN_STEM = 4


def _stem(word):
    for prefix in PREFIXES:
        if word.startswith(prefix) and len(word) - len(prefix) >= MIN_STEM:
            word = word[len(prefix):]
            # "penyaluran" -> "aluran": restore the elided consonant of peny-/peng-/pem-.
            if prefix in ("peny", "meny"):
                word = "s" + word
            elif prefix in ("peng", "meng"):
                word = "k" + word if not word[0] in "aeiou" else word
            break
    for suffix in SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= MIN_STEM:
            word = word[: -len(suffix)]
            break
    return word


def _tokens(text):
    return [
        _stem(w)
        for w in WORD_RE.findall((text or "").lower())
        if w not in STOPWORDS
    ]


def _active_documents():
    return RegulatoryDocument.objects.filter(retired_at__isnull=True)


def _idf(documents):
    total = len(documents)
    counts = Counter()
    for doc_tokens in documents:
        counts.update(set(doc_tokens))
    return {
        term: math.log((total + 1) / (count + 1)) + 1.0
        for term, count in counts.items()
    }


def _best_passage(body, query_terms, window=2):
    """Return the sentence(s) in ``body`` most relevant to the query, so the
    reviewer sees the specific passage rather than a whole document."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body) if s.strip()]
    if not sentences:
        return body
    scored = [
        (sum(1 for t in _tokens(s) if t in query_terms), i)
        for i, s in enumerate(sentences)
    ]
    best_score, best_i = max(scored)
    if best_score == 0:
        return sentences[0]
    start = max(0, best_i - (window - 1))
    return " ".join(sentences[start:best_i + 1])


def retrieve(query, limit=3):
    """Retrieve the most relevant regulatory passages for a query (FR-31.2).

    Each hit carries the source passage and citation reference so the generated
    text can never be presented as a verbatim legal citation without the source
    being independently visible (FR-31.4).
    """
    query_terms = set(_tokens(query))
    if not query_terms:
        return []

    documents = list(_active_documents())
    if not documents:
        return []

    tokenized = [_tokens(f"{d.title} {d.body}") for d in documents]
    idf = _idf(tokenized)

    hits = []
    for doc, doc_tokens in zip(documents, tokenized):
        if not doc_tokens:
            continue
        counts = Counter(doc_tokens)
        length = len(doc_tokens)
        score = sum(
            (counts[term] / length) * idf.get(term, 0.0)
            for term in query_terms
            if term in counts
        )

        # A regulation's title states its subject, so a title hit is a far stronger
        # topical signal than an incidental body word. Without this, a food-price
        # query cites the fuel-subsidy regulation first purely because "harga bahan"
        # overlaps "bahan bakar" — a wrong top citation is exactly the risk FR-31.4
        # exists to mitigate.
        title_terms = set(_tokens(doc.title))
        matched_title_terms = query_terms & title_terms
        if matched_title_terms:
            title_boost = sum(idf.get(term, 0.0) for term in matched_title_terms)
            score += TITLE_WEIGHT * title_boost

        if score < MIN_SCORE:
            continue
        hits.append({
            "document": doc,
            "source_ref": doc.source_ref,
            "passage": _best_passage(doc.body, query_terms),
            "score": round(score, 4),
        })

    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits[:limit]


def classify_risk(negative_ratio, volume_change_pct, coordinated):
    """Assign Low/Medium/High (Rendah/Sedang/Tinggi) so leadership can triage which
    items need the fastest response (FR-31.3).

    Coordinated inauthentic activity on the same issue always lifts an item above
    Low, even when sentiment looks calm — that combination is precisely what a
    manufactured narrative looks like early on.
    """
    score = 0
    if negative_ratio >= 0.7:
        score += 2
    elif negative_ratio >= 0.5:
        score += 1

    if volume_change_pct >= 100:
        score += 2
    elif volume_change_pct >= 50:
        score += 1

    if coordinated:
        score += 2

    if score >= 4:
        return RISK_HIGH
    if score >= 1:
        return RISK_MEDIUM
    return RISK_LOW
