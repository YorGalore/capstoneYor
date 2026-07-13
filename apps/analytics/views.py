from django.http import HttpResponse
from django.shortcuts import render

from apps.core.selectors import get_active_project
from . import selectors


def ringkasan(request):
    project = get_active_project(request)
    summary = selectors.ringkasan_summary(project) if project else None
    alerts = selectors.recent_alerts()
    return render(request, "analytics/ringkasan.html", {
        "active_nav": "ringkasan",
        "summary": summary,
        "alerts": alerts,
    })


def war_room(request):
    return HttpResponse("War Room — coming soon")


def narasi(request):
    return HttpResponse("Perbandingan Narasi — coming soon")


def regional(request):
    return HttpResponse("Regional — coming soon")
