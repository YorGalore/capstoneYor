from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import AnalystProfile, OnboardingRequest, Platform, Province, Regency, Project, Tenant
from .rbac import AdminLockoutError, assert_can_deactivate_user, assert_can_delete_user

User = get_user_model()


class GuardedUserAdmin(DjangoUserAdmin):
    """Enforces the last-admin lockout rules (FR-1.6) on the user admin: a
    Super/Tenant Admin cannot be deactivated or deleted if doing so would leave
    the platform or a tenant with no administrator, and no one may delete their
    own account.
    """

    def save_model(self, request, obj, form, change):
        if change and "is_active" in form.changed_data and not obj.is_active:
            try:
                assert_can_deactivate_user(obj, acting_user=request.user)
            except AdminLockoutError as exc:
                self.message_user(request, str(exc), level=messages.ERROR)
                obj.is_active = True
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        try:
            assert_can_delete_user(obj, acting_user=request.user)
        except AdminLockoutError as exc:
            self.message_user(request, str(exc), level=messages.ERROR)
            return
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            try:
                assert_can_delete_user(obj, acting_user=request.user)
            except AdminLockoutError as exc:
                self.message_user(request, str(exc), level=messages.ERROR)
                continue
            super(GuardedUserAdmin, self).delete_model(request, obj)


admin.site.unregister(User)
admin.site.register(User, GuardedUserAdmin)

admin.site.register(Tenant)
admin.site.register(Project)
admin.site.register(Platform)
admin.site.register(Province)
admin.site.register(Regency)
admin.site.register(AnalystProfile)


@admin.register(OnboardingRequest)
class OnboardingRequestAdmin(admin.ModelAdmin):
    list_display = ("organization_name", "organization_type", "contact_name", "work_email", "status", "created_at")
    list_filter = ("organization_type", "status", "created_at")
    search_fields = ("organization_name", "contact_name", "work_email")
