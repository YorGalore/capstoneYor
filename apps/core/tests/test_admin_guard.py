from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.core.models import AnalystProfile, Tenant

User = get_user_model()


class UserAdminLockoutTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.admin = User.objects.create_superuser(username="root", password="rootpass")
        AnalystProfile.objects.update_or_create(
            user=self.admin,
            defaults={"tenant": self.tenant, "role": AnalystProfile.ROLE_SUPER_ADMIN},
        )
        self.client.force_login(self.admin)

    def test_admin_cannot_deactivate_last_super_admin(self):
        change_url = reverse("admin:auth_user_change", args=[self.admin.pk])
        response = self.client.post(
            change_url,
            {
                "username": "root",
                "is_active": "",  # unchecked -> deactivate
                "is_staff": "on",
                "is_superuser": "on",
                "date_joined_0": "2026-01-01",
                "date_joined_1": "00:00:00",
                "last_login_0": "",
                "last_login_1": "",
                "initial-date_joined_0": "2026-01-01",
                "initial-date_joined_1": "00:00:00",
                "_continue": "Save and continue editing",
            },
            follow=True,
        )
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active, "last super admin must stay active")

    def test_admin_cannot_delete_last_super_admin(self):
        delete_url = reverse("admin:auth_user_delete", args=[self.admin.pk])
        self.client.post(delete_url, {"post": "yes"}, follow=True)
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())
