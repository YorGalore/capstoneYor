from django.contrib import admin

from .models import (
    ApifyCredential, AuditLogEntry, CollectionRun, MonitoredDomain, MonitoringKeyword,
    PlatformIntegration, PoliticalMonitoringPermission, PolicyAcknowledgment, RegulatoryDocument,
    RuntimeSetting, ScheduledJob,
)

@admin.register(PlatformIntegration)
class PlatformIntegrationAdmin(admin.ModelAdmin):
    list_display = ("platform", "project", "method", "is_active")
    list_filter = ("project", "method", "is_active")


@admin.register(ApifyCredential)
class ApifyCredentialAdmin(admin.ModelAdmin):
    list_display = ("masked_token", "project", "status", "last_verified_at")
    list_filter = ("project", "status")


@admin.register(MonitoredDomain)
class MonitoredDomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "project", "adapter", "status")
    list_filter = ("project", "status")


@admin.register(MonitoringKeyword)
class MonitoringKeywordAdmin(admin.ModelAdmin):
    list_display = ("keyword", "project", "is_active", "match_count")
    list_filter = ("project", "is_active")
admin.site.register(PoliticalMonitoringPermission)
@admin.register(CollectionRun)
class CollectionRunAdmin(admin.ModelAdmin):
    list_display = ("source", "project", "status", "items_found", "cost_estimate", "started_at")
    list_filter = ("project", "source", "status")


@admin.register(AuditLogEntry)
class AuditLogEntryAdmin(admin.ModelAdmin):
    """Audit log is append-only — no add/change/delete via admin (FR governance constraint)."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(PolicyAcknowledgment)

admin.site.register(RuntimeSetting)


@admin.register(ScheduledJob)
class ScheduledJobAdmin(admin.ModelAdmin):
    """Per-project cadence for the recurring jobs (REQ-SC-01)."""

    list_display = (
        "job_type", "project", "cadence_minutes", "enabled",
        "next_run_at", "last_status", "consecutive_failures",
    )
    list_filter = ("job_type", "enabled", "last_status")
    # Outcome fields are written by the scheduler; editing them by hand would falsify the
    # record of what actually ran.
    readonly_fields = (
        "last_run_at", "last_status", "last_error", "last_detail", "consecutive_failures",
    )


@admin.register(RegulatoryDocument)
class RegulatoryDocumentAdmin(admin.ModelAdmin):
    """Corpus management for the Compliance Officer / Super Admin (FR-31.5)."""

    list_display = ("title", "source_ref", "indexed_at", "retired_at")
    search_fields = ("title", "source_ref", "body")
