"""The evidence contract: a metric that cannot show its work is not shippable.

Every KPI this platform reports to a government decision-maker has to survive the
question "where does that number come from?". A bare integer in a template cannot,
so selectors return a :class:`Metric` instead — the value plus the method that
produced it, the rows behind it, the model's aggregate confidence, and an
:class:`EvidenceRef` that reproduces the exact supporting mentions.

Nothing here is cached. A stored aggregate can silently disagree with the feed
after an analyst corrects a label; recomputing from the same queryset the
drill-down uses means the number and its evidence cannot drift apart.

``resolve_evidence`` is the single chokepoint every drill-down routes through.
That is deliberate: it makes "no black-box analytics" a property the test suite
can actually enforce, rather than a claim in a slide.
"""
from dataclasses import dataclass, field
from urllib.parse import urlencode

from django.db.models import Q

# Below this, a model's label is weak enough that a reviewer should look before
# acting on it. Surfaced per metric as `low_confidence_pct`, never used to hide
# rows: suppressing uncertain evidence would misrepresent the confidence itself.
LOW_CONFIDENCE = 0.5


@dataclass(frozen=True)
class EvidenceRef:
    """A reproducible pointer to the mentions behind a number.

    ``kind`` selects the resolver; ``params`` are querystring-safe scalars so a
    reference survives a round trip through a URL and back into a queryset.
    """

    kind: str
    params: dict = field(default_factory=dict)

    def to_query(self):
        """Render as a querystring fragment the feed can parse back."""
        items = [("bukti", self.kind)]
        items += [(k, v) for k, v in sorted(self.params.items()) if v not in (None, "")]
        return urlencode(items)

    @classmethod
    def from_params(cls, params):
        """Rebuild from request.GET. Returns None when no evidence ref is present."""
        kind = (params.get("bukti") or "").strip()
        if kind not in RESOLVERS:
            return None
        allowed = RESOLVERS[kind].params
        return cls(
            kind=kind,
            params={k: v for k, v in params.items() if k in allowed and v not in (None, "")},
        )


@dataclass(frozen=True)
class Metric:
    """A number that carries its own justification."""

    value: float
    unit: str = "count"          # "count" | "percent" | "score" | "points"
    label: str = ""
    method: str = ""             # human-readable formula, shown in the disclosure
    evidence: "EvidenceRef | None" = None
    contributing: int = 0        # rows behind the number
    confidence: float = 0.0      # mean model confidence over contributing rows
    low_confidence_pct: int = 0  # share of those rows below LOW_CONFIDENCE

    @property
    def evidence_query(self):
        return self.evidence.to_query() if self.evidence else ""

    @property
    def confidence_band(self):
        """Coarse band for the UI. Deliberately three-valued: a decimal confidence
        invites false precision from a reader who cannot calibrate it."""
        if not self.contributing:
            return "tidak tersedia"
        if self.confidence >= 0.75 and self.low_confidence_pct <= 20:
            return "tinggi"
        if self.confidence >= 0.55:
            return "sedang"
        return "rendah"

    @property
    def display_value(self):
        if self.unit == "percent":
            return f"{round(self.value)}%"
        if self.unit == "points":
            return f"{'+' if self.value > 0 else ''}{round(self.value)} poin"
        if self.unit == "score":
            return str(round(self.value))
        return f"{round(self.value):,}".replace(",", ".")


def confidence_stats(confidences):
    """Mean confidence and the share below LOW_CONFIDENCE, over one metric's rows."""
    values = [c for c in confidences if c is not None]
    if not values:
        return 0.0, 0
    mean = sum(values) / len(values)
    weak = sum(1 for c in values if c < LOW_CONFIDENCE)
    return round(mean, 3), round((weak / len(values)) * 100)


@dataclass(frozen=True)
class Resolver:
    """How one kind of evidence reference turns back into mentions."""

    params: tuple
    fn: object


def _resolve_mention(project, params):
    from .models import Mention

    qs = Mention.objects.filter(project=project)
    if params.get("sentiment"):
        qs = qs.filter(sentiment=params["sentiment"])
    if params.get("content_type"):
        qs = qs.filter(content_type=params["content_type"])
    if params.get("issue"):
        qs = qs.filter(issue_label__issue_id=params["issue"])
    return qs


def _resolve_attribution(project, params):
    from .models import Mention

    qs = Mention.objects.filter(project=project, attributions__isnull=False)
    if params.get("target"):
        qs = qs.filter(attributions__target_id=params["target"])
    if params.get("level"):
        qs = qs.filter(attributions__target__level=params["level"])
    if params.get("own_government"):
        qs = qs.filter(own_government_q())
    if params.get("sentiment"):
        qs = qs.filter(attributions__sentiment=params["sentiment"])
    return qs.distinct()


def own_government_q(prefix="attributions"):
    """Filter for attributions landing on the tenant's own government.

    Depth is capped at two by AttributionTarget, so "our node, or a child of it"
    is the complete expansion — a complaint about Dinas PUPR is a complaint about
    the Pemkab that runs it, and there is no third level to recurse into.

    ``prefix`` is the path to the attribution rows: the default suits a Mention
    queryset, and ``prefix=""`` a MentionAttribution one.
    """
    base = f"{prefix}__" if prefix else ""
    return Q(**{f"{base}target__is_own_government": True}) | Q(
        **{f"{base}target__parent__is_own_government": True}
    )


def _resolve_driver(project, params):
    from .models import Mention

    qs = Mention.objects.filter(project=project, drivers__isnull=False)
    if params.get("driver"):
        qs = qs.filter(drivers__driver_id=params["driver"])
    if params.get("sentiment"):
        qs = qs.filter(sentiment=params["sentiment"])
    return qs.distinct()


def _resolve_thread(project, params):
    """A thread's evidence is its comments — the discussion, not the post that
    started it, since every thread metric is computed from the replies."""
    from .models import Mention

    qs = Mention.objects.filter(
        project=project, content_type__in=Mention.REACTIVE_CONTENT_TYPES
    )
    if params.get("root"):
        qs = qs.filter(parent_id=params["root"])
    if params.get("toxic"):
        qs = qs.filter(toxicity_label=Mention.TOXICITY_TOXIC)
    if params.get("stance"):
        qs = qs.filter(stance=params["stance"])
    return qs


RESOLVERS = {
    "mention": Resolver(
        params=("sentiment", "content_type", "issue"), fn=_resolve_mention
    ),
    "attribution": Resolver(
        params=("target", "level", "sentiment", "own_government"),
        fn=_resolve_attribution,
    ),
    "driver": Resolver(params=("driver", "sentiment"), fn=_resolve_driver),
    "thread": Resolver(params=("root", "toxic", "stance"), fn=_resolve_thread),
}


def register_resolver(kind, params, fn):
    """Register an evidence kind. Slices B, C and D call this at import time so
    every metric they introduce is drillable through the same chokepoint."""
    RESOLVERS[kind] = Resolver(params=tuple(params), fn=fn)


def resolve_evidence(project, ref):
    """Replay an evidence reference into the mentions behind a metric.

    Returns an empty queryset for an unknown kind rather than raising: a stale
    bookmarked URL should show "no evidence", not a 500.
    """
    from .models import Mention

    if ref is None or ref.kind not in RESOLVERS:
        return Mention.objects.none()
    return RESOLVERS[ref.kind].fn(project, ref.params)
