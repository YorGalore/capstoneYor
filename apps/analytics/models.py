from urllib.parse import urlsplit

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
    CONTENT_CHOICES = [
        (CONTENT_POST, "Posting/Artikel"),
        (CONTENT_COMMENT, "Komentar/Balasan"),
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
