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
    from apps.analytics.models import PoliticalIssue

    project = get_active_project(request)
    issue = PoliticalIssue.objects.filter(status=PoliticalIssue.STATUS_ACTIVE).first() if project else None
    summary = selectors.war_room_summary(issue) if issue else None
    return render(request, "analytics/war_room.html", {"active_nav": "war_room", "summary": summary})


def narasi(request):
    from apps.analytics.models import PoliticalIssue

    project = get_active_project(request)
    issue = PoliticalIssue.objects.filter(status=PoliticalIssue.STATUS_ACTIVE).first() if project else None
    summary = selectors.narasi_summary(issue) if issue else None
    return render(request, "analytics/narasi.html", {"active_nav": "narasi", "summary": summary})


def regional(request):
    project = get_active_project(request)
    selected_province = request.GET.get("provinsi") or None
    summary = selectors.regional_summary(project, selected_province) if project else None
    return render(request, "analytics/regional.html", {"active_nav": "regional", "summary": summary})
