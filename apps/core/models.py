from django.conf import settings
from django.db import models


class Tenant(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Project(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Platform(models.Model):
    METHOD_APIFY = "apify"
    METHOD_INTERNAL = "internal"
    METHOD_CHOICES = [(METHOD_APIFY, "Apify"), (METHOD_INTERNAL, "Internal")]

    slug = models.SlugField(unique=True)
    display_name = models.CharField(max_length=100)
    brand_color = models.CharField(max_length=7, default="#0E7C86")
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default=METHOD_INTERNAL)

    def __str__(self):
        return self.display_name


class Province(models.Model):
    name = models.CharField(max_length=100, unique=True)
    population_online = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name


class Regency(models.Model):
    province = models.ForeignKey(Province, on_delete=models.CASCADE, related_name="regencies")
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "regencies"
        unique_together = ("province", "name")

    def __str__(self):
        return f"{self.name}, {self.province.name}"


class PagePermission(models.Model):
    """One cell of the runtime-editable role × page access matrix (FR-1A)."""

    role = models.CharField(max_length=20)
    page = models.CharField(max_length=50)
    can_access = models.BooleanField(default=False)
    updated_by = models.CharField(max_length=150, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("role", "page")
        ordering = ["page", "role"]

    def __str__(self):
        return f"{self.role} × {self.page} = {'izin' if self.can_access else 'tolak'}"


class AnalystProfile(models.Model):
    ROLE_SUPER_ADMIN = "super_admin"
    ROLE_TENANT_ADMIN = "tenant_admin"
    ROLE_ANALYST = "analyst"
    ROLE_VIEWER = "viewer"
    ROLE_CHOICES = [
        (ROLE_SUPER_ADMIN, "Platform Super Admin"),
        (ROLE_TENANT_ADMIN, "Tenant Admin"),
        (ROLE_ANALYST, "Analis"),
        (ROLE_VIEWER, "Peninjau"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="analyst_profile"
    )
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="analysts")
    role_label = models.CharField(max_length=100, default="Analis Humas")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_ANALYST)
    has_political_monitoring_permission = models.BooleanField(default=False)

    @property
    def is_super_admin(self):
        return self.role == self.ROLE_SUPER_ADMIN

    @property
    def is_tenant_admin(self):
        return self.role == self.ROLE_TENANT_ADMIN

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.role_label})"
