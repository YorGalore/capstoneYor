from .models import AuditLogEntry


def record_audit_entry(actor_label, action, target):
    return AuditLogEntry.objects.create(actor_label=actor_label, action=action, target=target)
