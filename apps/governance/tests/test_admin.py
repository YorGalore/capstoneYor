from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.core.seed import seed_core
from apps.governance.models import AuditLogEntry
from apps.governance.seed import seed_governance


class AuditLogEntryAdminTest(TestCase):
    def setUp(self):
        tenant, project = seed_core()
        seed_governance(tenant)
        self.entry = AuditLogEntry.objects.first()
        User = get_user_model()
        self.superuser = User.objects.create_superuser(
            username="admin.super", email="admin.super@example.com", password="s3cret-pass"
        )
        self.client.force_login(self.superuser)

    def test_add_view_is_forbidden(self):
        response = self.client.get("/admin/governance/auditlogentry/add/")
        self.assertEqual(response.status_code, 403)

    def test_change_view_is_read_only(self):
        # Django's admin grants superusers implicit view permission, so the
        # change view renders as a read-only detail page (200) instead of a
        # 403 — but crucially with no save control, so the entry cannot be
        # edited through it.
        response = self.client.get(f"/admin/governance/auditlogentry/{self.entry.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="_save"')

    def test_change_view_post_does_not_modify_entry(self):
        original_action = self.entry.action
        response = self.client.post(
            f"/admin/governance/auditlogentry/{self.entry.pk}/change/",
            {"actor_label": "Tampered", "action": "Tampered action", "target": "Tampered"},
        )
        self.assertEqual(response.status_code, 403)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.action, original_action)

    def test_delete_view_is_forbidden(self):
        response = self.client.get(f"/admin/governance/auditlogentry/{self.entry.pk}/delete/")
        self.assertEqual(response.status_code, 403)

    def test_changelist_view_is_still_viewable(self):
        response = self.client.get("/admin/governance/auditlogentry/")
        self.assertEqual(response.status_code, 200)

    def test_model_update_and_delete_are_rejected(self):
        self.entry.action = "Tampered outside admin"
        with self.assertRaises(ValidationError):
            self.entry.save()
        with self.assertRaises(ValidationError):
            self.entry.delete()

    def test_queryset_update_and_delete_are_rejected(self):
        queryset = AuditLogEntry.objects.filter(pk=self.entry.pk)
        with self.assertRaises(ValidationError):
            queryset.update(action="Tampered in bulk")
        with self.assertRaises(ValidationError):
            queryset.delete()
