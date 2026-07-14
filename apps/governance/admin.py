from django.contrib import admin

from .models import (
    ApifyCredential, AuditLogEntry, CollectionRun, MonitoredDomain, MonitoringKeyword,
    PlatformIntegration, PoliticalMonitoringPermission, PolicyAcknowledgment, RegulatoryDocument,
    RuntimeSetting,
)

admin.site.register(PlatformIntegration)
admin.site.register(ApifyCredential)
admin.site.register(MonitoredDomain)
admin.site.register(MonitoringKeyword)
admin.site.register(PoliticalMonitoringPermission)
admin.site.register(CollectionRun)


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


@admin.register(RegulatoryDocument)
class RegulatoryDocumentAdmin(admin.ModelAdmin):
    """Corpus management for the Compliance Officer / Super Admin (FR-31.5)."""

    list_display = ("title", "source_ref", "indexed_at", "retired_at")
    search_fields = ("title", "source_ref", "body")
