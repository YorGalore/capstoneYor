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
    masked_token = models.CharField(max_length=100)
    last_verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.masked_token


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

    def __str__(self):
        return self.domain


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


class PolicyAcknowledgment(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="policy_acknowledgments")
    approved_by = models.CharField(max_length=150)
    approved_at = models.DateTimeField()
    next_review_at = models.DateTimeField()

    def __str__(self):
        return f"{self.tenant} — {self.approved_at:%Y-%m-%d}"
