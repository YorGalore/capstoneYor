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


class AnalystProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="analyst_profile"
    )
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="analysts")
    role_label = models.CharField(max_length=100, default="Analis Humas")
    has_political_monitoring_permission = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.role_label})"
