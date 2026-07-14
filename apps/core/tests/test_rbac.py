from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.core.models import AnalystProfile, Tenant
from apps.core.rbac import (
    AdminLockoutError,
    activate_user,
    assert_can_deactivate_user,
    assert_can_delete_user,
    create_pending_user,
)

User = get_user_model()


def set_profile(user, tenant, role):
    """Set a user's profile role, tolerating the profile the post_save signal
    may already have created."""
    profile, _ = AnalystProfile.objects.update_or_create(
        user=user, defaults={"tenant": tenant, "role": role}
    )
    return profile


class RoleModelTest(TestCase):
    def test_new_profile_defaults_to_analyst_role(self):
        tenant = Tenant.objects.create(name="Instansi A")
        user = User.objects.create(username="analis1")
        profile = set_profile(user, tenant, AnalystProfile.ROLE_ANALYST)
        self.assertEqual(profile.role, AnalystProfile.ROLE_ANALYST)
        self.assertFalse(profile.is_super_admin)
        self.assertFalse(profile.is_tenant_admin)

    def test_super_admin_helpers(self):
        tenant = Tenant.objects.create(name="Instansi A")
        user = User.objects.create(username="super1")
        profile = set_profile(user, tenant, AnalystProfile.ROLE_SUPER_ADMIN)
        self.assertTrue(profile.is_super_admin)


class ActivationTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")

    def test_create_pending_user_is_inactive(self):
        user = create_pending_user(
            username="pending1", tenant=self.tenant, role=AnalystProfile.ROLE_ANALYST
        )
        self.assertFalse(user.is_active)
        profile = AnalystProfile.objects.get(user=user)
        self.assertEqual(profile.tenant, self.tenant)
        self.assertEqual(profile.role, AnalystProfile.ROLE_ANALYST)

    def test_pending_user_cannot_log_in_until_activated(self):
        user = create_pending_user(
            username="pending2", tenant=self.tenant, password="secret-123"
        )
        self.assertFalse(self.client.login(username="pending2", password="secret-123"))

        activator = User.objects.create(username="admin1")
        set_profile(activator, self.tenant, AnalystProfile.ROLE_TENANT_ADMIN)
        activate_user(user, activated_by=activator)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(self.client.login(username="pending2", password="secret-123"))


class LastAdminGuardTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")

    def _make(self, username, role, is_active=True):
        user = User.objects.create(username=username, is_active=is_active)
        set_profile(user, self.tenant, role)
        return user

    def test_cannot_delete_own_account(self):
        user = self._make("selfadmin", AnalystProfile.ROLE_SUPER_ADMIN)
        # even with another super admin present, you cannot delete yourself
        self._make("other_super", AnalystProfile.ROLE_SUPER_ADMIN)
        with self.assertRaises(AdminLockoutError):
            assert_can_delete_user(user, acting_user=user)

    def test_cannot_delete_last_super_admin(self):
        only_super = self._make("only_super", AnalystProfile.ROLE_SUPER_ADMIN)
        actor = self._make("actor", AnalystProfile.ROLE_TENANT_ADMIN)
        with self.assertRaises(AdminLockoutError):
            assert_can_delete_user(only_super, acting_user=actor)

    def test_can_delete_super_admin_when_another_exists(self):
        target = self._make("super_a", AnalystProfile.ROLE_SUPER_ADMIN)
        actor = self._make("super_b", AnalystProfile.ROLE_SUPER_ADMIN)
        # should not raise
        assert_can_delete_user(target, acting_user=actor)

    def test_cannot_deactivate_last_super_admin(self):
        only_super = self._make("only_super2", AnalystProfile.ROLE_SUPER_ADMIN)
        actor = self._make("actor2", AnalystProfile.ROLE_SUPER_ADMIN)
        # deactivating the actor themselves would leave only_super, that's fine;
        # deactivating only_super while actor stays is also fine (two supers).
        # Remove actor first to make only_super the last one.
        actor_profile = actor.analyst_profile
        actor_profile.delete()
        actor.delete()
        with self.assertRaises(AdminLockoutError):
            assert_can_deactivate_user(only_super, acting_user=only_super)

    def test_cannot_delete_last_tenant_admin_when_no_super_admin(self):
        target = self._make("t_admin", AnalystProfile.ROLE_TENANT_ADMIN)
        self._make("an_analyst", AnalystProfile.ROLE_ANALYST)
        with self.assertRaises(AdminLockoutError):
            assert_can_delete_user(target, acting_user=self._make("actor3", AnalystProfile.ROLE_ANALYST))

    def test_can_delete_tenant_admin_when_super_admin_exists(self):
        target = self._make("t_admin2", AnalystProfile.ROLE_TENANT_ADMIN)
        self._make("platform_super", AnalystProfile.ROLE_SUPER_ADMIN)
        actor = self._make("actor4", AnalystProfile.ROLE_SUPER_ADMIN)
        assert_can_delete_user(target, acting_user=actor)
