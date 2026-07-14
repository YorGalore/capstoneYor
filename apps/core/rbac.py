"""Role-based access foundation: activation of new users and the last-admin
lockout guard (FR-1.3, FR-1.5, FR-1.6). Page-level access is handled separately
by the permission matrix (FR-1A).
"""
from django.contrib.auth import get_user_model
from django.db import transaction

from .models import AnalystProfile


class AdminLockoutError(Exception):
    """Raised when an action would remove the last administrator able to manage
    the platform or a tenant, or when a user tries to delete their own account.
    """


def create_pending_user(username, tenant, role=AnalystProfile.ROLE_ANALYST, password=None, **user_fields):
    """Create a new user in the inactive state (FR-1.5). The user cannot log in
    until a Tenant Admin or Super Admin activates them.
    """
    User = get_user_model()
    with transaction.atomic():
        user = User(username=username, is_active=False, **user_fields)
        if password:
            user.set_password(password)
        user.save()
        AnalystProfile.objects.update_or_create(
            user=user, defaults={"tenant": tenant, "role": role}
        )
    return user


def activate_user(user, activated_by):
    """Activate a pending user so they can log in (FR-1.5)."""
    if not user.is_active:
        user.is_active = True
        user.save(update_fields=["is_active"])
    return user


def _active_super_admin_count(exclude_user=None):
    qs = AnalystProfile.objects.filter(
        role=AnalystProfile.ROLE_SUPER_ADMIN, user__is_active=True
    )
    if exclude_user is not None:
        qs = qs.exclude(user=exclude_user)
    return qs.count()


def _active_tenant_admin_count(tenant, exclude_user=None):
    qs = AnalystProfile.objects.filter(
        tenant=tenant, role=AnalystProfile.ROLE_TENANT_ADMIN, user__is_active=True
    )
    if exclude_user is not None:
        qs = qs.exclude(user=exclude_user)
    return qs.count()


def _assert_not_last_admin(target):
    """Guard the FR-1.6 lockout rules for a user being removed or deactivated."""
    profile = AnalystProfile.objects.filter(user=target).first()
    if profile is None:
        return

    if profile.role == AnalystProfile.ROLE_SUPER_ADMIN:
        if _active_super_admin_count(exclude_user=target) == 0:
            raise AdminLockoutError(
                "Tidak dapat menghapus/menonaktifkan Platform Super Admin aktif terakhir."
            )

    if profile.role == AnalystProfile.ROLE_TENANT_ADMIN:
        others_in_tenant = _active_tenant_admin_count(profile.tenant, exclude_user=target)
        # A platform-wide Super Admin can always administer the tenant, so a
        # tenant is only "locked out" when there is neither another active
        # Tenant Admin in it nor any active Super Admin at all.
        if others_in_tenant == 0 and _active_super_admin_count(exclude_user=target) == 0:
            raise AdminLockoutError(
                "Tidak dapat menghapus/menonaktifkan Tenant Admin aktif terakhir tanpa Super Admin."
            )


def assert_can_delete_user(target, acting_user):
    """Raise AdminLockoutError if deleting ``target`` is not allowed (FR-1.6)."""
    if target.pk == acting_user.pk:
        raise AdminLockoutError("Pengguna tidak dapat menghapus akunnya sendiri.")
    _assert_not_last_admin(target)


def assert_can_deactivate_user(target, acting_user):
    """Raise AdminLockoutError if deactivating ``target`` is not allowed (FR-1.6)."""
    _assert_not_last_admin(target)
