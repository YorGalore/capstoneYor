from django.contrib.auth.decorators import login_not_required
from django.shortcuts import redirect, render

from .forms import OnboardingRequestForm
from .models import AnalystProfile


@login_not_required
def landing(request):
    # The public page is for the public. Someone already signed in who lands here — from a
    # bookmark of the root, or the logo on the way back — should go to work, not be shown
    # a "Masuk" button and a demo booking form they have no use for.
    if request.user.is_authenticated:
        return redirect("analytics:ringkasan")
    return render(request, "core/landing.html")


@login_not_required
def onboarding(request):
    initial_type = request.GET.get("type", "brand")
    if initial_type not in {"brand", "government"}:
        initial_type = "brand"
    if request.method == "POST":
        form = OnboardingRequestForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("core:onboarding_success")
    else:
        form = OnboardingRequestForm(initial={"organization_type": initial_type})
    return render(request, "core/onboarding.html", {"form": form})


@login_not_required
def onboarding_success(request):
    return render(request, "core/onboarding_success.html")


def profile(request):
    analyst_profile = (
        AnalystProfile.objects.select_related("tenant", "user").filter(user=request.user).first()
    )
    return render(request, "core/profile.html", {
        "active_nav": "profile",
        "profile": analyst_profile,
    })
