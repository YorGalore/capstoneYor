from django.http import HttpResponse
from django.shortcuts import render

from .models import ApifyCredential, MonitoredDomain, PlatformIntegration


def konfigurasi(request):
    integrations = PlatformIntegration.objects.select_related("platform").order_by("platform__display_name")
    credential = ApifyCredential.objects.order_by("-last_verified_at").first()
    domains = MonitoredDomain.objects.order_by("domain")
    return render(request, "governance/konfigurasi.html", {
        "active_nav": "konfigurasi",
        "integrations": integrations,
        "credential": credential,
        "domains": domains,
    })


def pengawasan(request):
    return HttpResponse("Dasbor Pengawasan — coming soon")
