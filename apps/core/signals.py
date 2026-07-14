from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import AnalystProfile, Tenant


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_analyst_profile(sender, instance, created, **kwargs):
    if not created or AnalystProfile.objects.filter(user=instance).exists():
        return
    tenant = Tenant.objects.first()
    if tenant is not None:
        AnalystProfile.objects.create(user=instance, tenant=tenant)
