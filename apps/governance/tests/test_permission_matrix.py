from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.core.models import AnalystProfile, PagePermission, Tenant
from apps.core.seed import DEMO_USERNAME, seed_core
from apps.governance.models import AuditLogEntry

User = get_user_model()


class PermissionMatrixViewTest(TestCase):
    def setUp(self):
        self.tenant, _ = seed_core()
        self.super_admin = User.objects.get(username=DEMO_USERNAME)  # seeded super admin
        self.analyst = User.objects.create(username="analis.biasa")
        AnalystProfile.objects.update_or_create(
            user=self.analyst,
            defaults={"tenant": self.tenant, "role": AnalystProfile.ROLE_ANALYST},
        )

    def test_super_admin_can_open_matrix(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse("governance:permission_matrix"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Konfigurasi")  # a page label in the grid

    def test_analyst_forbidden_from_matrix(self):
        self.client.force_login(self.analyst)
        response = self.client.get(reverse("governance:permission_matrix"))
        self.assertEqual(response.status_code, 403)

    def test_toggle_updates_cell_and_writes_audit(self):
        self.client.force_login(self.super_admin)
        before = AuditLogEntry.objects.count()
        response = self.client.post(
            reverse("governance:toggle_permission"),
            {"role": AnalystProfile.ROLE_ANALYST, "page": "konfigurasi"},
        )
        self.assertRedirects(response, reverse("governance:permission_matrix"))
        row = PagePermission.objects.get(role=AnalystProfile.ROLE_ANALYST, page="konfigurasi")
        self.assertTrue(row.can_access)  # default was False, toggled to True
        self.assertEqual(AuditLogEntry.objects.count(), before + 1)

    def test_cannot_toggle_reserved_cell(self):
        self.client.force_login(self.super_admin)
        self.client.post(
            reverse("governance:toggle_permission"),
            {"role": AnalystProfile.ROLE_TENANT_ADMIN, "page": "runtime_settings"},
        )
        self.assertFalse(
            PagePermission.objects.filter(
                role=AnalystProfile.ROLE_TENANT_ADMIN, page="runtime_settings", can_access=True
            ).exists()
        )


class GatedToolPageTest(TestCase):
    def setUp(self):
        self.tenant, _ = seed_core()
        self.analyst = User.objects.create(username="analis.biasa2")
        AnalystProfile.objects.update_or_create(
            user=self.analyst,
            defaults={"tenant": self.tenant, "role": AnalystProfile.ROLE_ANALYST},
        )

    def test_analyst_denied_konfigurasi(self):
        self.client.force_login(self.analyst)
        response = self.client.get(reverse("governance:konfigurasi"))
        self.assertEqual(response.status_code, 403)

    def test_super_admin_allowed_konfigurasi(self):
        self.client.force_login(User.objects.get(username=DEMO_USERNAME))
        response = self.client.get(reverse("governance:konfigurasi"))
        self.assertEqual(response.status_code, 200)
