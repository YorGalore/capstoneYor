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


class Mention(models.Model):
    SENTIMENT_POSITIVE = "positive"
    SENTIMENT_NEUTRAL = "neutral"
    SENTIMENT_NEGATIVE = "negative"
    SENTIMENT_CHOICES = [
        (SENTIMENT_POSITIVE, "Positif"),
        (SENTIMENT_NEUTRAL, "Netral"),
        (SENTIMENT_NEGATIVE, "Negatif"),
    ]

    EMOTION_TRUST = "trust"
    EMOTION_ANTICIPATION = "anticipation"
    EMOTION_JOY = "joy"
    EMOTION_ANGER = "anger"
    EMOTION_SADNESS = "sadness"
    EMOTION_CHOICES = [
        (EMOTION_TRUST, "Kepercayaan"),
        (EMOTION_ANTICIPATION, "Antisipasi"),
        (EMOTION_JOY, "Kegembiraan"),
        (EMOTION_ANGER, "Kemarahan"),
        (EMOTION_SADNESS, "Kesedihan"),
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
    content_snippet = models.TextField()
    theme = models.CharField(max_length=100, blank=True)
    sentiment = models.CharField(max_length=20, choices=SENTIMENT_CHOICES)
    emotion = models.CharField(max_length=20, choices=EMOTION_CHOICES)
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

    class Meta:
        indexes = [
            models.Index(fields=["posted_at"]),
            models.Index(fields=["sentiment"]),
            models.Index(fields=["is_political"]),
        ]

    def __str__(self):
        return f"{self.author_handle} ({self.platform.slug}, {self.sentiment})"


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
