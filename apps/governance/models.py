from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.models import Platform, Project, Tenant


class ProjectOwnedModel(models.Model):
    """Configuration and collection records isolated by their owning project."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE)

    class Meta:
        abstract = True

class PlatformIntegration(ProjectOwnedModel):
    METHOD_APIFY = "apify"
    METHOD_INTERNAL = "internal"
    METHOD_CHOICES = [(METHOD_APIFY, "Apify"), (METHOD_INTERNAL, "Internal")]

    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, related_name="integrations")
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    actor_id = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    status_note = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "platform"], name="uniq_governance_integration_project_platform"
            )
        ]

    def __str__(self):
        return f"{self.platform.display_name} ({'aktif' if self.is_active else 'nonaktif'})"


class ApifyCredential(ProjectOwnedModel):
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


class MonitoredDomain(ProjectOwnedModel):
    STATUS_ACTIVE = "active"
    STATUS_NEEDS_REVIEW = "needs_review"
    STATUS_INACTIVE = "inactive"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Aktif"),
        (STATUS_NEEDS_REVIEW, "Perlu tinjauan"),
        (STATUS_INACTIVE, "Nonaktif"),
    ]

    domain = models.CharField(max_length=200)
    adapter = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    last_tested_at = models.DateTimeField(null=True, blank=True)
    feed_url = models.URLField(max_length=500, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "domain"], name="uniq_governance_domain_project"
            )
        ]

    def __str__(self):
        return self.domain


class MonitoringKeyword(ProjectOwnedModel):
    keyword = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)
    match_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=150, blank=True)

    class Meta:
        ordering = ["keyword"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "keyword"], name="uniq_governance_keyword_project"
            )
        ]

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


class ImmutableAuditLogQuerySet(models.QuerySet):
    """Refuse ORM bulk operations that could rewrite audit history."""

    def update(self, **kwargs):
        raise ValidationError("Audit log entries are immutable and cannot be updated.")

    def delete(self):
        raise ValidationError("Audit log entries are immutable and cannot be deleted.")


class AuditLogEntry(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    actor_label = models.CharField(max_length=150)
    action = models.CharField(max_length=255)
    target = models.CharField(max_length=150)

    objects = ImmutableAuditLogQuerySet.as_manager()

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.actor_label}: {self.action}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Audit log entries are immutable and cannot be updated.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit log entries are immutable and cannot be deleted.")


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


class CollectionRun(ProjectOwnedModel):
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


class ManualCollectionRequest(ProjectOwnedModel):
    """A user-triggered collection queued for the separate scheduler process.

    The HTTP request only creates this durable work item. Network crawling stays out
    of the web worker, and the UI can poll this row for an honest completion status.
    """

    TYPE_SOCIAL = "social"
    TYPE_NEWS = "news"
    TYPE_CHOICES = [
        (TYPE_SOCIAL, "Social Media"),
        (TYPE_NEWS, "Berita Daring"),
    ]

    STATUS_QUEUED = "queued"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_SKIPPED = "skipped"
    STATUS_CHOICES = [
        (STATUS_QUEUED, "Dalam antrean"),
        (STATUS_RUNNING, "Sedang berjalan"),
        (STATUS_COMPLETED, "Selesai"),
        (STATUS_FAILED, "Gagal"),
        (STATUS_SKIPPED, "Dilewati"),
    ]

    collection_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED, db_index=True
    )
    requested_by = models.CharField(max_length=150)
    requested_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    items_found = models.PositiveIntegerField(default=0)
    sources_processed = models.PositiveIntegerField(default=0)
    detail = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["status", "requested_at"], name="manual_collect_queue_idx")
        ]

    def __str__(self):
        return f"{self.get_collection_type_display()} — {self.get_status_display()}"


class ScheduledJob(models.Model):
    """A recurring job on a per-project cadence (REQ-SC-01, REQ-SC-02).

    Without this, the platform only monitors when somebody remembers to type a
    management command. Cadence is per project because a national program under active
    scrutiny and a dormant one should not cost the same in Apify credits.
    """

    JOB_COLLECT = "collect"
    JOB_EVALUATE_ALERTS = "evaluate_alerts"
    JOB_DETECT_COORDINATION = "detect_coordination"
    JOB_GENERATE_BRIEF = "generate_brief"
    JOB_PURGE_RETENTION = "purge_retention"
    JOB_CHOICES = [
        (JOB_COLLECT, "Koleksi data"),
        (JOB_EVALUATE_ALERTS, "Evaluasi peringatan"),
        (JOB_DETECT_COORDINATION, "Deteksi koordinasi"),
        (JOB_GENERATE_BRIEF, "Brief harian"),
        (JOB_PURGE_RETENTION, "Purge retensi"),
    ]

    STATUS_OK = "ok"
    STATUS_FAILED = "failed"
    STATUS_SKIPPED = "skipped"
    STATUS_CHOICES = [
        (STATUS_OK, "Berhasil"),
        (STATUS_FAILED, "Gagal"),
        (STATUS_SKIPPED, "Dilewati"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="scheduled_jobs")
    job_type = models.CharField(max_length=40, choices=JOB_CHOICES)
    cadence_minutes = models.PositiveIntegerField(default=60)
    enabled = models.BooleanField(default=True)

    next_run_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_status = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=True)
    last_error = models.CharField(max_length=500, blank=True)
    last_detail = models.CharField(max_length=255, blank=True)
    consecutive_failures = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("project", "job_type")
        ordering = ["project_id", "job_type"]

    def __str__(self):
        return f"{self.get_job_type_display()} — {self.project.name} (tiap {self.cadence_minutes}m)"


class PolicyAcknowledgment(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="policy_acknowledgments")
    approved_by = models.CharField(max_length=150)
    approved_at = models.DateTimeField()
    next_review_at = models.DateTimeField()

    def __str__(self):
        return f"{self.tenant} — {self.approved_at:%Y-%m-%d}"
