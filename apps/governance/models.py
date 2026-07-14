from django.conf import settings
from django.db import models

from apps.core.models import Platform, Tenant


class PlatformIntegration(models.Model):
    METHOD_APIFY = "apify"
    METHOD_INTERNAL = "internal"
    METHOD_CHOICES = [(METHOD_APIFY, "Apify"), (METHOD_INTERNAL, "Internal")]

    platform = models.OneToOneField(Platform, on_delete=models.CASCADE, related_name="integration")
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    actor_id = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    status_note = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.platform.display_name} ({'aktif' if self.is_active else 'nonaktif'})"


class ApifyCredential(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_INVALID = "invalid"
    STATUS_REVOKED = "revoked"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Aktif"),
        (STATUS_INVALID, "Tidak valid"),
        (STATUS_REVOKED, "Dicabut"),
    ]

    masked_token = models.CharField(max_length=100)
    token_encrypted = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    last_verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.masked_token} ({self.get_status_display()})"


class RuntimeSetting(models.Model):
    """Database-backed cross-service configuration (FR-2A.9-11). Secret values are
    stored encrypted and only ever displayed masked; a small set of reserved keys
    cannot be edited through the Configuration Console.
    """

    key = models.CharField(max_length=150, unique=True)
    value = models.TextField(blank=True)
    is_secret = models.BooleanField(default=False)
    scope = models.CharField(max_length=50, default="platform")
    updated_by = models.CharField(max_length=150, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return self.key


class MonitoredDomain(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_NEEDS_REVIEW = "needs_review"
    STATUS_INACTIVE = "inactive"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Aktif"),
        (STATUS_NEEDS_REVIEW, "Perlu tinjauan"),
        (STATUS_INACTIVE, "Nonaktif"),
    ]

    domain = models.CharField(max_length=200, unique=True)
    adapter = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    last_tested_at = models.DateTimeField(null=True, blank=True)
    feed_url = models.URLField(max_length=500, blank=True)

    def __str__(self):
        return self.domain


class MonitoringKeyword(models.Model):
    keyword = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)
    match_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=150, blank=True)

    class Meta:
        ordering = ["keyword"]

    def __str__(self):
        return self.keyword


class PoliticalMonitoringPermission(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="political_monitoring_permissions",
    )
    approved_by = models.CharField(max_length=150)
    approved_at = models.DateTimeField()
    active = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} — {'aktif' if self.active else 'dicabut'}"


class AuditLogEntry(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    actor_label = models.CharField(max_length=150)
    action = models.CharField(max_length=255)
    target = models.CharField(max_length=150)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.actor_label}: {self.action}"


class RegulatoryDocument(models.Model):
    """A curated law, regulation, or internal SOP backing the regulatory grounding
    corpus (FR-31.1). Kept separate from the mention content index and managed by a
    Compliance Officer or Super Admin through the console (FR-31.5)."""

    title = models.CharField(max_length=300)
    source_ref = models.CharField(max_length=200)
    body = models.TextField()
    indexed_at = models.DateTimeField(auto_now=True)
    retired_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["title"]

    @property
    def is_active(self):
        return self.retired_at is None

    def __str__(self):
        return self.title


class CollectionRun(models.Model):
    """One collection cycle for a single source (Apify platform or news), with a
    status claim that lets the orchestrator skip overlapping runs (REQ-SC-05) and
    a per-run cost estimate for usage metering (REQ-DC-04)."""

    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_SKIPPED = "skipped"
    STATUS_CHOICES = [
        (STATUS_RUNNING, "Berjalan"),
        (STATUS_COMPLETED, "Selesai"),
        (STATUS_FAILED, "Gagal"),
        (STATUS_SKIPPED, "Dilewati"),
    ]

    source = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_RUNNING)
    keywords_count = models.PositiveIntegerField(default=0)
    items_found = models.PositiveIntegerField(default=0)
    cost_estimate = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    error = models.CharField(max_length=500, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.source} — {self.get_status_display()} ({self.items_found})"


class PolicyAcknowledgment(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="policy_acknowledgments")
    approved_by = models.CharField(max_length=150)
    approved_at = models.DateTimeField()
    next_review_at = models.DateTimeField()

    def __str__(self):
        return f"{self.tenant} — {self.approved_at:%Y-%m-%d}"
