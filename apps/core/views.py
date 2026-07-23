from django.contrib.auth.decorators import login_not_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone

from .articles import ARTICLES, get_article
from .forms import OnboardingRequestForm
from .models import AnalystProfile, OnboardingRequest
from .permissions import require_page

# A second submission with the same email + organization within this window is
# almost certainly the same lead re-submitting (double-click, browser back, retry
# after a network hiccup), not a genuinely new request — so we don't create a
# duplicate row, but we also don't tell the public form that (avoids leaking
# whether a given organization/email has already contacted us).
DUPLICATE_WINDOW_DAYS = 7


@login_not_required
def landing(request):
    # The public page is for the public. Someone already signed in who lands here — from a
    # bookmark of the root, or the logo on the way back — should go to work, not be shown
    # a "Masuk" button and a demo booking form they have no use for.
    if request.user.is_authenticated:
        return redirect("analytics:ringkasan")
    return render(request, "core/landing.html", {"articles": ARTICLES})


@login_not_required
def onboarding(request):
    initial_type = request.GET.get("type", "brand")
    if initial_type not in {"brand", "government"}:
        initial_type = "brand"
    if request.method == "POST":
        form = OnboardingRequestForm(request.POST)
        if form.is_valid():
            cutoff = timezone.now() - timezone.timedelta(days=DUPLICATE_WINDOW_DAYS)
            duplicate = OnboardingRequest.objects.filter(
                work_email__iexact=form.cleaned_data["work_email"],
                organization_name__iexact=form.cleaned_data["organization_name"],
                created_at__gte=cutoff,
            ).exists()
            if not duplicate:
                form.save()
            request.session["onboarding_submitted"] = True
            return redirect("core:onboarding_success")
    else:
        form = OnboardingRequestForm(initial={"organization_type": initial_type})
    return render(request, "core/onboarding.html", {"form": form})


@login_not_required
def onboarding_success(request):
    if not request.session.pop("onboarding_submitted", False):
        return redirect("core:onboarding")
    return render(request, "core/onboarding_success.html")


@login_not_required
def article_detail(request, slug):
    article = get_article(slug)
    if article is None:
        raise Http404("Artikel tidak ditemukan")
    related = [a for a in ARTICLES if a["slug"] != slug][:5]
    return render(request, "core/artikel_detail.html", {"article": article, "related": related})


def profile(request):
    analyst_profile = (
        AnalystProfile.objects.select_related("tenant", "user").filter(user=request.user).first()
    )
    return render(request, "core/profile.html", {
        "active_nav": "profile",
        "profile": analyst_profile,
    })


@require_page("onboarding_requests")
def onboarding_requests(request):
    """First-party list of public demo requests (OnboardingRequest), so a Platform
    Super Admin can verify submissions without needing Django-admin staff/model
    permissions — AnalystProfile.role is intentionally not wired into is_staff."""
    return render(request, "core/onboarding_requests.html", {
        "active_nav": "onboarding_requests",
        "requests": OnboardingRequest.objects.all()[:200],
    })
