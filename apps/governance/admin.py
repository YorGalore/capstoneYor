from django.contrib import admin

from .models import (
    ApifyCredential, AuditLogEntry, MonitoredDomain, PlatformIntegration,
    PoliticalMonitoringPermission, PolicyAcknowledgment,
)

admin.site.register(PlatformIntegration)
admin.site.register(ApifyCredential)
admin.site.register(MonitoredDomain)
admin.site.register(PoliticalMonitoringPermission)


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
