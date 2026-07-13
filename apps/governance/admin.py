from django.contrib import admin

from .models import (
    ApifyCredential, AuditLogEntry, MonitoredDomain, PlatformIntegration,
    PoliticalMonitoringPermission, PolicyAcknowledgment,
)

admin.site.register(PlatformIntegration)
admin.site.register(ApifyCredential)
admin.site.register(MonitoredDomain)
admin.site.register(PoliticalMonitoringPermission)
admin.site.register(AuditLogEntry)
admin.site.register(PolicyAcknowledgment)
