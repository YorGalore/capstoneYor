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

    class Meta:
        indexes = [
            models.Index(fields=["posted_at"]),
            models.Index(fields=["sentiment"]),
            models.Index(fields=["is_political"]),
        ]

    def __str__(self):
        return f"{self.author_handle} ({self.platform.slug}, {self.sentiment})"


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

    name = models.CharField(max_length=150)
    condition_summary = models.CharField(max_length=255)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)

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
