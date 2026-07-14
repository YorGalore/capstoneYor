from django.shortcuts import render

from .models import AnalystProfile


def profile(request):
    analyst_profile = (
        AnalystProfile.objects.select_related("tenant", "user").filter(user=request.user).first()
    )
    return render(request, "core/profile.html", {
        "active_nav": "profile",
        "profile": analyst_profile,
    })
