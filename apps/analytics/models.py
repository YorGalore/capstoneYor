from urllib.parse import urlsplit

from django.conf import settings
from django.db import models

from apps.core.models import Platform, Project, Province, Regency


class Coalition(models.Model):
    STANCE_PETAHANA = "petahana"
    STANCE_PENANTANG = "penantang"
    STANCE_CHOICES = [(STANCE_PETAHANA, "Petahana"), (STANCE_PENANTANG, "Penantang")]

    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    stance = models.CharField(max_length=20, choices=STANCE_CHOICES)
    color = models.CharField(max_length=7)

    def __str__(self):
        return self.name


class PoliticalIssue(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [(STATUS_ACTIVE, "Aktif"), (STATUS_CLOSED, "Ditutup")]

    # Tenant isolation (FR-1.2). Without this the issue pool is global: every tenant's War
    # Room would surface whichever active issue happened to be created first, across all
    # institutions, and the response-log endpoint would accept any issue id.
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="political_issues")
    title = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    opened_at = models.DateTimeField()
    owner_label = models.CharField(max_length=150)

    def __str__(self):
        return self.title


class Author(models.Model):
    """Normalized social account a mention is attributed to (FR-3.3)."""

    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, related_name="authors")
    handle = models.CharField(max_length=150)
    display_name = models.CharField(max_length=200, blank=True)
    follower_count = models.PositiveIntegerField(default=0)
    influence_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    class Meta:
        unique_together = ("platform", "handle")

    def __str__(self):
        return f"{self.handle} ({self.platform.slug})"


class Mention(models.Model):
    CONTENT_POST = "post"
    CONTENT_COMMENT = "comment"
    CONTENT_QUOTE = "quote"
    CONTENT_CHOICES = [
        (CONTENT_POST, "Posting/Artikel"),
        (CONTENT_COMMENT, "Komentar/Balasan"),
        (CONTENT_QUOTE, "Kutipan/Quote post"),
    ]
    # Content that reacts to a parent, and so carries a stance toward it. A quote
    # post is a comment that happens to live on its author's own timeline.
    REACTIVE_CONTENT_TYPES = (CONTENT_COMMENT, CONTENT_QUOTE)

    TOXICITY_CLEAN = "bersih"
    TOXICITY_HARSH = "kasar"
    TOXICITY_TOXIC = "toksik"
    TOXICITY_CHOICES = [
        (TOXICITY_CLEAN, "Bersih"),
        (TOXICITY_HARSH, "Kasar"),
        (TOXICITY_TOXIC, "Toksik"),
    ]

    STANCE_AGREE = "setuju"
    STANCE_DISAGREE = "tidak_setuju"
    STANCE_NEUTRAL = "netral"
    STANCE_CHOICES = [
        (STANCE_AGREE, "Setuju"),
        (STANCE_DISAGREE, "Tidak setuju"),
        (STANCE_NEUTRAL, "Netral"),
    ]

    SENTIMENT_POSITIVE = "positive"
    SENTIMENT_NEUTRAL = "neutral"
    SENTIMENT_NEGATIVE = "negative"
    SENTIMENT_CHOICES = [
        (SENTIMENT_POSITIVE, "Positif"),
        (SENTIMENT_NEUTRAL, "Netral"),
        (SENTIMENT_NEGATIVE, "Negatif"),
    ]

    # Plutchik's eight primary emotions (FR-6.1).
    EMOTION_JOY = "joy"
    EMOTION_TRUST = "trust"
    EMOTION_FEAR = "fear"
    EMOTION_SURPRISE = "surprise"
    EMOTION_SADNESS = "sadness"
    EMOTION_DISGUST = "disgust"
    EMOTION_ANGER = "anger"
    EMOTION_ANTICIPATION = "anticipation"
    EMOTION_CHOICES = [
        (EMOTION_JOY, "Kegembiraan"),
        (EMOTION_TRUST, "Kepercayaan"),
        (EMOTION_FEAR, "Ketakutan"),
        (EMOTION_SURPRISE, "Keterkejutan"),
        (EMOTION_SADNESS, "Kesedihan"),
        (EMOTION_DISGUST, "Kejijikan"),
        (EMOTION_ANGER, "Kemarahan"),
        (EMOTION_ANTICIPATION, "Antisipasi"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="mentions")
    platform = models.ForeignKey(Platform, on_delete=models.PROTECT, related_name="mentions")
    province = models.ForeignKey(
        Province, on_delete=models.SET_NULL, null=True, blank=True, related_name="mentions"
    )
    regency = models.ForeignKey(
        Regency, on_delete=models.SET_NULL, null=True, blank=True, related_name="mentions"
    )
    author_handle = models.CharField(max_length=150)
    author = models.ForeignKey(
        "Author", on_delete=models.SET_NULL, null=True, blank=True, related_name="mentions"
    )
    external_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
    content_snippet = models.TextField()
    theme = models.CharField(max_length=100, blank=True)
    sentiment = models.CharField(max_length=20, choices=SENTIMENT_CHOICES)
    sentiment_confidence = models.FloatField(default=0.0)
    sentiment_model = models.CharField(max_length=50, blank=True)
    emotion = models.CharField(max_length=20, choices=EMOTION_CHOICES)
    emotion_labels = models.JSONField(default=list, blank=True)
    posted_at = models.DateTimeField()
    engagement_count = models.PositiveIntegerField(default=0)
    reach_estimate = models.PositiveIntegerField(default=0)
    is_political = models.BooleanField(default=False)
    coalition = models.ForeignKey(
        Coalition, on_delete=models.SET_NULL, null=True, blank=True, related_name="mentions"
    )
    issue = models.ForeignKey(
        PoliticalIssue, on_delete=models.SET_NULL, null=True, blank=True, related_name="mentions"
    )
    source_url = models.URLField(max_length=500, null=True, blank=True, unique=True)
    matched_keyword = models.CharField(max_length=150, blank=True)
    is_scraped = models.BooleanField(default=False)
    content_type = models.CharField(
        max_length=20, choices=CONTENT_CHOICES, default=CONTENT_POST
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="comments"
    )
    reported_comment_count = models.PositiveIntegerField(default=0)
    # Attribution enrichment provenance. Nullable because attribution runs as its
    # own stage after ingestion: a mention collected before the stage existed, or
    # while the provider was down, is legitimately un-attributed until backfilled.
    attributed_at = models.DateTimeField(null=True, blank=True)
    attribution_model = models.CharField(max_length=50, blank=True)
    # Comment intelligence. Null rather than 0.0 by default: "not analysed" and
    # "analysed and found clean" are different facts, and averaging the former as
    # zero would understate toxicity across a partially-enriched corpus.
    toxicity_score = models.FloatField(null=True, blank=True)
    toxicity_label = models.CharField(
        max_length=10, choices=TOXICITY_CHOICES, blank=True
    )
    stance = models.CharField(max_length=15, choices=STANCE_CHOICES, blank=True)
    stance_confidence = models.FloatField(default=0.0)
    comment_intel_model = models.CharField(max_length=50, blank=True)
    political_actors = models.ManyToManyField(
        "PoliticalActor", blank=True, related_name="mentions"
    )
    program = models.ForeignKey(
        "GovernmentProgram", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="mentions",
    )

    class Meta:
        indexes = [
            models.Index(fields=["posted_at"]),
            models.Index(fields=["sentiment"]),
            models.Index(fields=["is_political"]),
            models.Index(
                fields=["content_type"], name="analytics_m_content_6bf398_idx"
            ),
        ]

    def __str__(self):
        return f"{self.author_handle} ({self.platform.slug}, {self.sentiment})"

    @property
    def has_clickable_source(self):
        """Whether the UI may present source_url as a real external link."""
        if not self.source_url:
            return False
        return urlsplit(self.source_url).hostname != "demo.pantau.local"


class LabelCorrection(models.Model):
    """History of an analyst manually correcting an enrichment label (FR-5.3,
    FR-19.2). Doubles as the feedback signal for periodic model tuning."""

    mention = models.ForeignKey(Mention, on_delete=models.CASCADE, related_name="corrections")
    field = models.CharField(max_length=20)  # "sentiment" | "emotion"
    old_value = models.CharField(max_length=50)
    new_value = models.CharField(max_length=50)
    corrected_by = models.CharField(max_length=150)
    corrected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-corrected_at"]

    def __str__(self):
        return f"{self.field}: {self.old_value} → {self.new_value}"


class AlertRule(models.Model):
    CHANNEL_EMAIL = "email"
    CHANNEL_PUSH = "push"
    CHANNEL_WEBHOOK = "webhook"
    CHANNEL_CHOICES = [
        (CHANNEL_EMAIL, "Email"), (CHANNEL_PUSH, "Push"), (CHANNEL_WEBHOOK, "Webhook"),
    ]

    # Machine-evaluable conditions (FR-12.1).
    CONDITION_NEGATIVE_RATIO = "negative_ratio"
    CONDITION_VOLUME_SPIKE = "volume_spike"
    CONDITION_CHOICES = [
        (CONDITION_NEGATIVE_RATIO, "Rasio sentimen negatif melewati ambang"),
        (CONDITION_VOLUME_SPIKE, "Lonjakan volume sebutan"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="alert_rules")
    name = models.CharField(max_length=150)
    condition_summary = models.CharField(max_length=255)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    condition_type = models.CharField(
        max_length=30, choices=CONDITION_CHOICES, default=CONDITION_NEGATIVE_RATIO
    )
    threshold = models.FloatField(default=0.5)
    window_minutes = models.PositiveIntegerField(default=60)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Alert(models.Model):
    SEVERITY_INFO = "info"
    SEVERITY_WARNING = "warning"
    SEVERITY_CRITICAL = "critical"
    SEVERITY_CHOICES = [
        (SEVERITY_INFO, "Info"),
        (SEVERITY_WARNING, "Peringatan"),
        (SEVERITY_CRITICAL, "Kritis"),
    ]
    STATUS_ACTIVE = "active"
    STATUS_RESOLVED = "resolved"
    STATUS_CHOICES = [(STATUS_ACTIVE, "Aktif"), (STATUS_RESOLVED, "Teratasi")]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="alerts")
    rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name="alerts")
    issue = models.ForeignKey(
        PoliticalIssue, on_delete=models.SET_NULL, null=True, blank=True, related_name="alerts"
    )
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    title = models.CharField(max_length=255)
    detail = models.CharField(max_length=500)
    triggered_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)

    class Meta:
        ordering = ["-triggered_at"]

    def __str__(self):
        return self.title


class Category(models.Model):
    """Top level of the three-level Issue Taxonomy (FR-3A.1)."""

    name = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class SubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategories")
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "subcategories"
        unique_together = ("category", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.category.name} › {self.name}"


class Issue(models.Model):
    """Leaf of the Issue Taxonomy (FR-3A.1) — distinct from the free-text keywords
    (FR-2) and from PoliticalIssue (war-room event)."""

    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name="issues")
    name = models.CharField(max_length=200)
    keywords = models.JSONField(default=list, blank=True)  # terms that auto-map content here
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class IssueLabel(models.Model):
    """Assignment of a mention to a taxonomy Issue (FR-3A.2/3A.3)."""

    SOURCE_AUTO = "auto"
    SOURCE_MANUAL = "manual"
    SOURCE_CHOICES = [(SOURCE_AUTO, "Otomatis"), (SOURCE_MANUAL, "Manual")]

    mention = models.OneToOneField(Mention, on_delete=models.CASCADE, related_name="issue_label")
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="labels")
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=SOURCE_AUTO)
    decided_by = models.CharField(max_length=150, blank=True)
    decided_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.mention_id} → {self.issue.name} ({self.source})"


class IssueMergeHistory(models.Model):
    """Audit trail for issue merges, capturing enough state to support unmerge
    (FR-3A.5)."""

    source_issue_ids = models.JSONField(default=list)
    target_issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="merges_in")
    moved = models.JSONField(default=dict)  # {source_issue_id: [mention_id, ...]}
    performed_by = models.CharField(max_length=150)
    performed_at = models.DateTimeField(auto_now_add=True)
    reversed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-performed_at"]

    def __str__(self):
        return f"merge → {self.target_issue.name}"


class Camp(models.Model):
    """A user-defined grouping of political actors (FR-24.3). The Platform never
    hard-codes or defaults a camp — every camp is created by the tenant."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="camps")
    name = models.CharField(max_length=150)
    color = models.CharField(max_length=7, default="#7C8A99")
    is_user_defined = models.BooleanField(default=True, editable=False)

    class Meta:
        unique_together = ("project", "name")
        ordering = ["name"]

    def __str__(self):
        return self.name


class PoliticalActor(models.Model):
    """A trackable political entity (FR-24.1). Restricted by FR-29.3 to public
    officials, candidates, parties, coalitions, and organizational accounts —
    never private individuals."""

    TYPE_PARTY = "party"
    TYPE_COALITION = "coalition"
    TYPE_OFFICIAL = "official"
    TYPE_ORGANIZATION = "organization"
    TYPE_CHOICES = [
        (TYPE_PARTY, "Partai"),
        (TYPE_COALITION, "Koalisi"),
        (TYPE_OFFICIAL, "Pejabat/Kandidat"),
        (TYPE_ORGANIZATION, "Organisasi"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="political_actors")
    name = models.CharField(max_length=200)
    actor_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    camp = models.ForeignKey(
        Camp, on_delete=models.SET_NULL, null=True, blank=True, related_name="actors"
    )
    keywords = models.JSONField(default=list, blank=True)
    handles = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ActorSentimentAssessment(models.Model):
    """Sentiment toward one configured public/organizational actor within a mention.

    A single article can be negative toward the institution while neutral toward a
    quoted official. Keeping this separate from Mention.sentiment is required for
    defensible actor-by-actor comparisons in periodic reports.
    """

    SOURCE_AUTO = "auto"
    SOURCE_MANUAL = "manual"
    SOURCE_CHOICES = [(SOURCE_AUTO, "Otomatis"), (SOURCE_MANUAL, "Manual")]

    mention = models.ForeignKey(
        Mention, on_delete=models.CASCADE, related_name="actor_sentiments"
    )
    actor = models.ForeignKey(
        PoliticalActor, on_delete=models.CASCADE, related_name="sentiment_assessments"
    )
    sentiment = models.CharField(max_length=20, choices=Mention.SENTIMENT_CHOICES)
    confidence = models.FloatField(default=0.0)
    model = models.CharField(max_length=50, blank=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=SOURCE_AUTO)
    reviewed_by = models.CharField(max_length=150, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("mention", "actor")
        ordering = ["actor__name"]

    def __str__(self):
        return f"{self.mention_id} / {self.actor.name}: {self.sentiment}"


class AttributionTarget(models.Model):
    """Who criticism in a mention can be *directed at*, per project.

    Distinct from PoliticalActor, which answers a different question — "which
    tracked political actor appears in this text" — and lives behind the FR-29
    neutrality/political-monitoring gate. Attributing a pothole complaint to Dinas
    PUPR must not drag routine service monitoring into that regime, so the two
    registries stay separate and coexist on the same mention.

    The tree is deliberately capped at two levels (a catch-all level bucket, and
    concrete entities beneath it). That keeps "is this aimed at us?" a single
    parent hop rather than a recursive descent, and nothing downstream routes on
    sub-sub-agency precision.
    """

    LEVEL_PUSAT = "pusat"
    LEVEL_PROVINSI = "provinsi"
    LEVEL_KABUPATEN = "kabupaten"
    LEVEL_OPD = "opd"
    LEVEL_PEJABAT = "pejabat"
    LEVEL_NON_PEMERINTAH = "non_pemerintah"
    LEVEL_TIDAK_JELAS = "tidak_jelas"
    LEVEL_CHOICES = [
        (LEVEL_PUSAT, "Pemerintah Pusat"),
        (LEVEL_PROVINSI, "Pemerintah Provinsi"),
        (LEVEL_KABUPATEN, "Pemerintah Kabupaten/Kota"),
        (LEVEL_OPD, "Instansi/OPD"),
        (LEVEL_PEJABAT, "Pejabat publik"),
        (LEVEL_NON_PEMERINTAH, "Non-pemerintah"),
        (LEVEL_TIDAK_JELAS, "Tidak jelas"),
    ]

    # Display order for the attribution tree. Alphabetical ordering would scatter
    # the government levels; readers expect them ranked by tier of government.
    LEVEL_ORDER = {
        LEVEL_KABUPATEN: 0,
        LEVEL_OPD: 1,
        LEVEL_PEJABAT: 2,
        LEVEL_PROVINSI: 3,
        LEVEL_PUSAT: 4,
        LEVEL_NON_PEMERINTAH: 5,
        LEVEL_TIDAK_JELAS: 6,
    }

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="attribution_targets"
    )
    name = models.CharField(max_length=200)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    # String reference: OPD is declared further down this module.
    opd = models.ForeignKey(
        "OPD", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="attribution_targets",
    )
    keywords = models.JSONField(default=list, blank=True)
    handles = models.JSONField(default=list, blank=True)
    # A level-level bucket. Always offered as a candidate even when no entity name
    # matched, so implicit blame ("jalan ini udah 3 tahun dibiarin") can still be
    # attributed at level granularity instead of collapsing into Unknown.
    is_catch_all = models.BooleanField(default=False)
    # Marks the tenant's own government — the numerator of "only X% of negative
    # sentiment is actually directed at us".
    is_own_government = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("project", "name")
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def level_rank(self):
        return self.LEVEL_ORDER.get(self.level, 99)

    @property
    def counts_as_own_government(self):
        """Whether criticism of this target lands on the tenant.

        True for the tenant's own node and anything directly beneath it — a
        complaint about Dinas PUPR is a complaint about the Pemkab that runs it.
        """
        if self.is_own_government:
            return True
        return bool(self.parent and self.parent.is_own_government)


class MentionAttribution(models.Model):
    """The sentiment one mention expresses *toward* one target.

    A single post can praise the central government while blaming the regency, so
    a mention carries as many of these as it has targets. Every mention ends up
    with at least one — worst case the `tidak_jelas` catch-all — which is what
    keeps attribution shares summing to 100% with no silent unattributed
    remainder.
    """

    SOURCE_AUTO = "auto"
    SOURCE_MANUAL = "manual"
    SOURCE_CHOICES = [(SOURCE_AUTO, "Otomatis"), (SOURCE_MANUAL, "Manual")]

    mention = models.ForeignKey(
        Mention, on_delete=models.CASCADE, related_name="attributions"
    )
    target = models.ForeignKey(
        AttributionTarget, on_delete=models.CASCADE, related_name="attributions"
    )
    sentiment = models.CharField(max_length=20, choices=Mention.SENTIMENT_CHOICES)
    confidence = models.FloatField(default=0.0)
    # The verbatim substring that carries the attribution, so a reviewer can see
    # what the model actually read rather than taking the label on trust.
    evidence_span = models.CharField(max_length=300, blank=True)
    rationale = models.CharField(max_length=300, blank=True)
    model = models.CharField(max_length=50, blank=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=SOURCE_AUTO)
    reviewed_by = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("mention", "target")
        ordering = ["target__name"]
        indexes = [
            models.Index(fields=["sentiment"]),
        ]

    def __str__(self):
        return f"{self.mention_id} → {self.target.name}: {self.sentiment}"


class NegativeDriver(models.Model):
    """A *reason* behind negative sentiment, as opposed to a topic.

    The Issue taxonomy answers "what is this about"; a driver answers "why are
    they angry about it". Those diverge in practice — two posts both labelled
    "Jalan" can be about a pothole and about a procurement scandal, and they route
    to different responses.

    Per project, so a tenant governs its own reason vocabulary.
    """

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="negative_drivers"
    )
    name = models.CharField(max_length=150)
    slug = models.SlugField()
    keywords = models.JSONField(default=list, blank=True)
    color = models.CharField(max_length=7, default="#C6483F")
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("project", "slug")
        ordering = ["name"]

    def __str__(self):
        return self.name


class MentionDriver(models.Model):
    """One reason a mention is negative. A complaint can carry several — a flood
    post is often both `banjir` and `respons lambat`."""

    SOURCE_AUTO = "auto"
    SOURCE_MANUAL = "manual"
    SOURCE_CHOICES = [(SOURCE_AUTO, "Otomatis"), (SOURCE_MANUAL, "Manual")]

    mention = models.ForeignKey(
        Mention, on_delete=models.CASCADE, related_name="drivers"
    )
    driver = models.ForeignKey(
        NegativeDriver, on_delete=models.CASCADE, related_name="mention_links"
    )
    confidence = models.FloatField(default=0.0)
    evidence_span = models.CharField(max_length=300, blank=True)
    rationale = models.CharField(max_length=300, blank=True)
    model = models.CharField(max_length=50, blank=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=SOURCE_AUTO)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("mention", "driver")
        ordering = ["-confidence"]

    def __str__(self):
        return f"{self.mention_id} → {self.driver.name}"


class DriverCandidate(models.Model):
    """A recurring complaint that fits none of the configured drivers.

    This is how a narrative nobody anticipated surfaces without letting the model
    silently invent taxonomy. The model may only *propose* a phrase here; an
    analyst decides whether it becomes a real driver. That human gate is what
    keeps the reason vocabulary governed while still catching the new thing.
    """

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="driver_candidates"
    )
    phrase = models.CharField(max_length=120)
    count = models.PositiveIntegerField(default=0)
    sample_mention_ids = models.JSONField(default=list, blank=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    promoted_to = models.ForeignKey(
        NegativeDriver, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="promoted_from",
    )
    dismissed = models.BooleanField(default=False)

    class Meta:
        unique_together = ("project", "phrase")
        ordering = ["-count", "-last_seen_at"]

    @property
    def is_open(self):
        return self.promoted_to_id is None and not self.dismissed

    def __str__(self):
        return f"{self.phrase} ({self.count})"


class ThreadInsight(models.Model):
    """What a discussion did to the post that started it.

    A post-only dashboard misses the case that matters most: a calm official
    statement whose comment section is furious. Divergence is that case as a
    number, and opinion shift is the early-warning version of it — sentiment
    turning *within* a thread while it is still running.

    Recomputed on a schedule rather than per-comment: these are properties of a
    conversation, and a conversation is not finished when its first reply lands.
    """

    root_mention = models.OneToOneField(
        Mention, on_delete=models.CASCADE, related_name="thread_insight"
    )
    comment_count = models.PositiveIntegerField(default=0)
    reply_depth_max = models.PositiveSmallIntegerField(default=0)
    post_sentiment = models.CharField(max_length=20, choices=Mention.SENTIMENT_CHOICES)
    comment_negative_pct = models.PositiveSmallIntegerField(default=0)
    # Comment negativity minus the post's own, in percentage points. Positive means
    # the crowd is angrier than the post that provoked it.
    divergence_pp = models.SmallIntegerField(default=0)
    # Late-half minus early-half comment negativity, in points. Positive means
    # opinion turned against the subject while the thread ran.
    opinion_shift_pp = models.SmallIntegerField(default=0)
    toxicity_pct = models.PositiveSmallIntegerField(default=0)
    disagreement_pct = models.PositiveSmallIntegerField(default=0)
    # Comments per hour across the thread's active span.
    intensity = models.FloatField(default=0.0)
    # [{driver_id, name, count, sample_mention_ids}] — the complaints that recur
    # across this thread, reusing the driver taxonomy.
    recurring_complaints = models.JSONField(default=list, blank=True)
    analysed_comment_count = models.PositiveIntegerField(default=0)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-divergence_pp"]
        indexes = [models.Index(fields=["-divergence_pp"])]

    def __str__(self):
        return f"Thread {self.root_mention_id}: {self.comment_count} komentar"


class GovernmentProgram(models.Model):
    """A named government program/policy tracked as a first-class entity, distinct
    from general keywords (FR-27.1)."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="programs")
    name = models.CharField(max_length=200)
    agency = models.CharField(max_length=200, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ResponseAction(models.Model):
    """A response action logged by communications staff against a live narrative
    event (FR-28.2) — e.g. "clarification statement issued at 14:32". Together with
    the mention timeline this forms a single auditable record of the event and the
    institution's response to it."""

    ACTION_STATEMENT = "statement"
    ACTION_CLARIFICATION = "clarification"
    ACTION_BRIEFING = "briefing"
    ACTION_ESCALATION = "escalation"
    ACTION_OTHER = "other"
    ACTION_CHOICES = [
        (ACTION_STATEMENT, "Pernyataan resmi"),
        (ACTION_CLARIFICATION, "Klarifikasi"),
        (ACTION_BRIEFING, "Briefing pimpinan"),
        (ACTION_ESCALATION, "Eskalasi"),
        (ACTION_OTHER, "Lainnya"),
    ]

    issue = models.ForeignKey(
        PoliticalIssue, on_delete=models.CASCADE, related_name="response_actions"
    )
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES)
    description = models.CharField(max_length=500)
    logged_by = models.CharField(max_length=150)
    occurred_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at"]

    def __str__(self):
        return f"{self.get_action_type_display()} — {self.occurred_at:%d %b %H:%M}"


class DailyBrief(models.Model):
    """A per-day executive briefing document for leadership (FR-30).

    A brief is generated as a *draft* and must be reviewed by a human before it is
    finalized. Once finalized it is locked and snapshotted, so the record of what
    leadership actually read cannot change afterwards (FR-30.4).
    """

    STATUS_PENDING = "pending"
    STATUS_GENERATING = "generating"
    STATUS_DRAFT = "draft"
    STATUS_FINAL = "final"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Belum dibuat"),
        (STATUS_GENERATING, "Sedang dibuat"),
        (STATUS_DRAFT, "Draf — menunggu tinjauan"),
        (STATUS_FINAL, "Final (terkunci)"),
        (STATUS_FAILED, "Gagal"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="briefs")
    brief_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    finalized_by = models.CharField(max_length=150, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("project", "brief_date")
        ordering = ["-brief_date"]

    @property
    def is_locked(self):
        return self.status == self.STATUS_FINAL

    def __str__(self):
        return f"Brief {self.brief_date} ({self.get_status_display()})"


class DailyBriefIssue(models.Model):
    """One prioritized issue within a daily brief. Content is AI-generated and is
    always labeled a draft pending human review (FR-31.4); the regulatory passages
    used to ground it are stored alongside so a reviewer can verify them."""

    brief = models.ForeignKey(DailyBrief, on_delete=models.CASCADE, related_name="issues")
    title = models.CharField(max_length=250)
    content = models.TextField()
    preview_summary = models.CharField(max_length=500, blank=True)
    risk_level = models.CharField(max_length=10, default="low")
    order = models.PositiveIntegerField(default=0)
    approved = models.BooleanField(default=False)
    edited_by = models.CharField(max_length=150, blank=True)
    # Retrieved regulatory grounding: [{source_ref, passage, score}, ...] (FR-31.2)
    regulatory_context = models.JSONField(default=list, blank=True)
    mention_count = models.PositiveIntegerField(default=0)
    negative_pct = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class NotificationDelivery(models.Model):
    """A delivery attempt for an outbound notification (FR-12.2): a triggered
    alert or a finalized daily brief, over a concrete channel. Recorded whether
    it succeeded or not, so operators can audit what left the platform."""

    KIND_ALERT = "alert"
    KIND_BRIEF = "brief"
    KIND_CHOICES = [(KIND_ALERT, "Peringatan"), (KIND_BRIEF, "Sorotan")]

    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_SKIPPED = "skipped"
    STATUS_CHOICES = [
        (STATUS_SENT, "Terkirim"),
        (STATUS_FAILED, "Gagal"),
        (STATUS_SKIPPED, "Dilewati"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="notification_deliveries")
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    channel = models.CharField(max_length=20)
    subject = models.CharField(max_length=255)
    recipients = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    detail = models.CharField(max_length=500, blank=True)
    alert = models.ForeignKey(
        Alert, on_delete=models.CASCADE, null=True, blank=True, related_name="deliveries"
    )
    brief = models.ForeignKey(
        DailyBrief, on_delete=models.CASCADE, null=True, blank=True, related_name="deliveries"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_kind_display()} via {self.channel} ({self.get_status_display()})"


class BrowserPushSubscription(models.Model):
    """One browser endpoint that opted in to tenant-scoped Web Push alerts."""

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="push_subscriptions"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pantau_push_subscriptions",
    )
    endpoint = models.URLField(max_length=1000, unique=True)
    p256dh = models.TextField()
    auth = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    @property
    def subscription_info(self):
        return {
            "endpoint": self.endpoint,
            "keys": {"p256dh": self.p256dh, "auth": self.auth},
        }

    @property
    def masked_endpoint(self):
        return f"{self.endpoint[:45]}…" if len(self.endpoint) > 45 else self.endpoint

    def __str__(self):
        return f"{self.user} — {'aktif' if self.is_active else 'nonaktif'}"


class DailyBriefRun(models.Model):
    """One generation attempt for a brief. The DB-level status claim on DailyBrief
    is what prevents a scheduled run and a manual run arriving together from
    producing duplicate or corrupted output (FR-30.6)."""

    brief = models.ForeignKey(DailyBrief, on_delete=models.CASCADE, related_name="runs")
    triggered_by = models.CharField(max_length=150)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    succeeded = models.BooleanField(default=False)
    detail = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"run {self.brief.brief_date} oleh {self.triggered_by}"


class OPD(models.Model):
    """An organizational unit (Dinas) an incident can be assigned to.

    Scoped per project so each tenant defines its own structure. Introduced with
    the Incident board; also the grouping key for the later per-OPD KPI view.
    """

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="opds")
    name = models.CharField(max_length=200)
    slug = models.SlugField()
    abbr = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("project", "slug")
        ordering = ["name"]
        verbose_name = "OPD"
        verbose_name_plural = "OPD"

    def __str__(self):
        return self.abbr or self.name


class Incident(models.Model):
    """A citizen-service problem surfaced by social conversation, tracked as a
    decision object for leadership.

    Distinct from PoliticalIssue (a political-narrative war-room event, gated by
    neutrality controls) and from the taxonomy Issue (a classification leaf applied
    to individual mentions). An Incident *aggregates* mentions — clustered on
    taxonomy Issue x Regency — into something a Kepala Dinas can act on.

    Narrative fields are composed deterministically and always carry the draft
    banner: nothing here is published to leadership without human review.
    """

    SEVERITY_CRITICAL = "critical"
    SEVERITY_HIGH = "high"
    SEVERITY_MEDIUM = "medium"
    SEVERITY_LOW = "low"
    SEVERITY_CHOICES = [
        (SEVERITY_CRITICAL, "Kritis"),
        (SEVERITY_HIGH, "Tinggi"),
        (SEVERITY_MEDIUM, "Sedang"),
        (SEVERITY_LOW, "Rendah"),
    ]

    # Ordering by the severity *string* would sort alphabetically — medium, low,
    # high, critical — putting the most urgent incidents last on a board whose
    # whole purpose is surfacing them first. Rank numerically instead.
    SEVERITY_RANK = {
        SEVERITY_CRITICAL: 0,
        SEVERITY_HIGH: 1,
        SEVERITY_MEDIUM: 2,
        SEVERITY_LOW: 3,
    }

    STATUS_OPEN = "open"
    STATUS_ASSIGNED = "assigned"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_RESOLVED = "resolved"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Terbuka"),
        (STATUS_ASSIGNED, "Ditugaskan"),
        (STATUS_IN_PROGRESS, "Ditangani"),
        (STATUS_RESOLVED, "Selesai"),
        (STATUS_CLOSED, "Ditutup"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="incidents")
    title = models.CharField(max_length=250)
    issue = models.ForeignKey(
        Issue, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidents"
    )
    regency = models.ForeignKey(
        Regency, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidents"
    )
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default=SEVERITY_LOW)
    severity_rank = models.PositiveSmallIntegerField(default=3, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    assigned_opd = models.ForeignKey(
        OPD, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidents"
    )
    mentions = models.ManyToManyField(Mention, blank=True, related_name="incidents")
    mention_count = models.PositiveIntegerField(default=0)
    negative_pct = models.PositiveIntegerField(default=0)
    ai_summary = models.TextField(blank=True)
    root_cause = models.TextField(blank=True)
    impact = models.TextField(blank=True)
    recommendation = models.TextField(blank=True)
    draft_response = models.TextField(blank=True)
    # Retrieved regulatory grounding for the response: [{source_ref, passage, score}, ...]
    # Kept separately from the editable text so the retrieved sources stay visible
    # for verification even after a human edits the wording (FR-31.4).
    response_regulatory_context = models.JSONField(default=list, blank=True)
    response_generated_at = models.DateTimeField(null=True, blank=True)
    evidence_image_path = models.CharField(max_length=255, blank=True)
    evidence_caption = models.CharField(max_length=300, blank=True)
    evidence_is_simulated = models.BooleanField(default=False)
    is_confirmed = models.BooleanField(default=False)
    first_seen_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["severity_rank", "-mention_count"]
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["severity_rank"]),
        ]

    def save(self, *args, **kwargs):
        self.severity_rank = self.SEVERITY_RANK[self.severity]
        # A partial save that touches severity must persist the derived rank too,
        # or the board silently keeps ordering by the previous severity.
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "severity" in update_fields:
            kwargs["update_fields"] = list(update_fields) + ["severity_rank"]
        super().save(*args, **kwargs)

    @property
    def is_open(self):
        return self.status not in (self.STATUS_RESOLVED, self.STATUS_CLOSED)

    def __str__(self):
        return self.title


class EscalationAssessment(models.Model):
    """How likely an incident is to become a public crisis if left alone.

    Replaces a bare severity tier with a multi-signal score that shows its work:
    which signals fired, how much each contributed, and — critically — which
    signals had no data at all.

    ``confidence`` is data sufficiency, not model certainty. A project collecting
    one platform has no cross-platform signal; a project not collecting comments
    has no toxicity signal. Scoring those as zero would systematically understate
    risk, so the score is normalised over available weight only and confidence
    falls instead. A confident-looking number computed from three of eight signals
    is worse than no number.
    """

    TIER_LOW = "low"
    TIER_WATCH = "watch"
    TIER_HIGH = "high_risk"
    TIER_CRITICAL = "critical"
    TIER_CHOICES = [
        (TIER_LOW, "Rendah"),
        (TIER_WATCH, "Pantau"),
        (TIER_HIGH, "Risiko Tinggi"),
        (TIER_CRITICAL, "Kritis"),
    ]

    TIER_RANK = {TIER_CRITICAL: 0, TIER_HIGH: 1, TIER_WATCH: 2, TIER_LOW: 3}

    # How an escalation tier maps onto the incident severity the board already
    # orders by, so adding escalation does not fork the ranking.
    TIER_TO_SEVERITY = {
        TIER_CRITICAL: "critical",
        TIER_HIGH: "high",
        TIER_WATCH: "medium",
        TIER_LOW: "low",
    }

    incident = models.ForeignKey(
        Incident, on_delete=models.CASCADE, related_name="escalations",
        null=True, blank=True,
    )
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="escalations"
    )
    score = models.PositiveSmallIntegerField(default=0)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default=TIER_LOW)
    # [{key, label, raw, normalized, weight, contribution, available, note,
    #   evidence_kind, evidence_params}] — the full working, persisted so a past
    # score stays reproducible after weights are retuned.
    signals = models.JSONField(default=list, blank=True)
    confidence = models.FloatField(default=0.0)
    available_signal_count = models.PositiveSmallIntegerField(default=0)
    why = models.TextField(blank=True)
    impact_if_ignored = models.TextField(blank=True)
    recommended_response = models.TextField(blank=True)
    # Regulatory grounding for the recommendation, same contract as the incident
    # draft response: retrieved passages kept beside the text for verification.
    regulatory_context = models.JSONField(default=list, blank=True)
    window_start = models.DateTimeField()
    window_end = models.DateTimeField()
    model = models.CharField(max_length=50, blank=True)
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-computed_at"]
        indexes = [
            models.Index(fields=["project", "-computed_at"]),
            models.Index(fields=["-score"]),
        ]

    @property
    def severity(self):
        return self.TIER_TO_SEVERITY[self.tier]

    @property
    def tier_rank(self):
        return self.TIER_RANK[self.tier]

    @property
    def unavailable_signals(self):
        return [s["label"] for s in self.signals if not s.get("available")]

    @property
    def top_signals(self):
        return sorted(
            [s for s in self.signals if s.get("available")],
            key=lambda s: s.get("contribution", 0),
            reverse=True,
        )

    def __str__(self):
        return f"{self.get_tier_display()} ({self.score})"


class IncidentEvent(models.Model):
    """One entry on an incident's timeline (detection, assignment, status change,
    logged action). Together these form the auditable record of how the institution
    responded — the same role ResponseAction plays for a political narrative event.
    """

    KIND_DETECTED = "detected"
    KIND_VOLUME_UPDATE = "volume_update"
    KIND_ASSIGNED = "assigned"
    KIND_STATUS_CHANGE = "status_change"
    KIND_ACTION_LOGGED = "action_logged"
    KIND_NOTE = "note"
    KIND_RESPONSE_DRAFTED = "response_drafted"
    KIND_CHOICES = [
        (KIND_DETECTED, "Terdeteksi"),
        (KIND_VOLUME_UPDATE, "Perubahan volume"),
        (KIND_ASSIGNED, "Penugasan"),
        (KIND_STATUS_CHANGE, "Perubahan status"),
        (KIND_ACTION_LOGGED, "Tindakan dicatat"),
        (KIND_NOTE, "Catatan"),
        (KIND_RESPONSE_DRAFTED, "Tanggapan disusun"),
    ]

    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="events")
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    description = models.CharField(max_length=500)
    logged_by = models.CharField(max_length=150, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["occurred_at", "id"]

    def __str__(self):
        return f"{self.get_kind_display()} — {self.description[:40]}"
