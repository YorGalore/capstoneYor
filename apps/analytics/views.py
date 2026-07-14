from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.models import Platform
from apps.core.permissions import require_page, user_can_access
from apps.core.selectors import get_active_project, scope_to_tenant
from . import exports, selectors, taxonomy
from .models import Issue, IssueMergeHistory, LabelCorrection, Mention


def _export_max_rows():
    """Resolve the configurable export cap (FR-20.3) from Runtime Settings, with
    a safe default. Imported lazily to avoid an app-level import cycle."""
    try:
        from apps.governance.runtime import get_setting

        value = get_setting("export.max_rows")
        return int(value) if value else exports.MAX_ROWS_DEFAULT
    except (ImportError, ValueError, TypeError):
        return exports.MAX_ROWS_DEFAULT


@require_page("export")
def export_mentions(request):
    fmt = request.GET.get("format", "csv").lower()
    queryset = scope_to_tenant(
        Mention.objects.select_related("platform"), request
    )
    rows = exports.iter_export_rows(queryset, max_rows=_export_max_rows())
    stamp = timezone.now().strftime("%Y%m%d-%H%M")

    if fmt == "xlsx":
        content = exports.rows_to_xlsx(rows)
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="mentions-{stamp}.xlsx"'
        return response

    response = StreamingHttpResponse(exports.rows_to_csv(rows), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="mentions-{stamp}.csv"'
    return response


@require_page("feed")
def feed(request):
    """Raw mention feed, filterable by platform/sentiment/author/date (FR-3.1),
    tenant-scoped (FR-1.2)."""
    mentions = scope_to_tenant(
        Mention.objects.select_related("platform", "author"), request
    ).order_by("-posted_at")

    platform = request.GET.get("platform") or ""
    sentiment = request.GET.get("sentiment") or ""
    author = request.GET.get("author") or ""
    if platform:
        mentions = mentions.filter(platform__slug=platform)
    if sentiment:
        mentions = mentions.filter(sentiment=sentiment)
    if author:
        mentions = mentions.filter(author_handle__icontains=author)

    paginator = Paginator(mentions, 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "analytics/feed.html", {
        "active_nav": "feed",
        "page_obj": page,
        "platforms": Platform.objects.order_by("display_name"),
        "sentiment_choices": Mention.SENTIMENT_CHOICES,
        "filters": {"platform": platform, "sentiment": sentiment, "author": author},
    })


@require_page("feed")
@require_POST
def correct_sentiment(request, mention_id):
    """Manually override a mention's sentiment (FR-5.3), recording the change as
    correction history / model-tuning feedback (FR-19.2)."""
    mention = get_object_or_404(
        scope_to_tenant(Mention.objects.all(), request), pk=mention_id
    )
    new_value = request.POST.get("sentiment", "")
    valid = {key for key, _label in Mention.SENTIMENT_CHOICES}
    if new_value not in valid:
        messages.error(request, "Nilai sentimen tidak valid.")
        return redirect("analytics:feed")

    if new_value != mention.sentiment:
        LabelCorrection.objects.create(
            mention=mention, field="sentiment", old_value=mention.sentiment,
            new_value=new_value, corrected_by=request.user.get_full_name() or request.user.username,
        )
        mention.sentiment = new_value
        mention.sentiment_model = "manual"
        mention.save(update_fields=["sentiment", "sentiment_model"])
        messages.success(request, "Sentimen diperbarui dan dicatat sebagai koreksi manual.")
    return redirect("analytics:feed")


def ringkasan(request):
    project = get_active_project(request)
    summary = selectors.ringkasan_summary(project) if project else None
    alerts = selectors.recent_alerts()
    return render(request, "analytics/ringkasan.html", {
        "active_nav": "ringkasan",
        "summary": summary,
        "alerts": alerts,
        "can_export": user_can_access(request.user, "export"),
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


@require_page("taxonomy")
def taxonomy_view(request):
    """Issue Taxonomy tool page (FR-3A): manual review queue for unlabeled content,
    plus issue merge/unmerge management."""
    project = get_active_project(request)
    queue = (
        taxonomy.review_queue(project).select_related("platform").order_by("-posted_at")[:25]
        if project else []
    )
    issues = Issue.objects.filter(is_active=True).select_related("subcategory__category")
    return render(request, "analytics/taxonomy.html", {
        "active_nav": "taxonomy",
        "queue": queue,
        "issues": issues,
        "merges": IssueMergeHistory.objects.filter(reversed_at__isnull=True)[:10],
    })


@require_page("taxonomy")
@require_POST
def assign_issue(request, mention_id):
    mention = get_object_or_404(scope_to_tenant(Mention.objects.all(), request), pk=mention_id)
    issue = get_object_or_404(Issue, pk=request.POST.get("issue"), is_active=True)
    taxonomy.assign_issue(
        mention, issue, by=request.user.get_full_name() or request.user.username
    )
    messages.success(request, f'Konten dilabeli ke isu "{issue.name}".')
    return redirect("analytics:taxonomy")


@require_page("taxonomy")
@require_POST
def merge_issues(request):
    source_ids = [int(v) for v in request.POST.getlist("source") if v]
    target_id = request.POST.get("target")
    if not source_ids or not target_id:
        messages.error(request, "Pilih minimal satu isu sumber dan satu isu tujuan.")
        return redirect("analytics:taxonomy")

    taxonomy.merge_issues(
        source_ids, int(target_id),
        performed_by=request.user.get_full_name() or request.user.username,
    )
    messages.success(request, "Isu digabungkan. Aksi ini dapat dibatalkan (unmerge).")
    return redirect("analytics:taxonomy")


@require_page("taxonomy")
@require_POST
def unmerge_issues(request, history_id):
    history = get_object_or_404(IssueMergeHistory, pk=history_id)
    taxonomy.unmerge(history)
    messages.success(request, "Penggabungan isu dibatalkan.")
    return redirect("analytics:taxonomy")
