from django.contrib import messages
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from apps.core.models import AnalystProfile, Platform
from apps.core.permissions import (
    require_page, require_role_at_least, require_writer_role, user_can_access,
)
from apps.core.selectors import get_active_project, scope_to_tenant
from apps.governance import regulatory
from apps.governance.neutrality import NEUTRALITY_NOTICE, require_political_monitoring
from apps.governance.services import record_audit_entry
from . import briefs, exports, incidents, media_report_pdf, selectors, taxonomy
from .models import (
    ActorSentimentAssessment, DailyBrief, DailyBriefIssue, Issue, IssueMergeHistory,
    LabelCorrection, Mention, PoliticalIssue, ResponseAction,
)


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
        Mention.objects.select_related("platform", "author", "parent")
        .prefetch_related("actor_sentiments__actor"),
        request,
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
@require_writer_role
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


@require_page("feed")
@require_writer_role
@require_POST
def correct_actor_sentiment(request, mention_id, assessment_id):
    mention = get_object_or_404(
        scope_to_tenant(Mention.objects.all(), request), pk=mention_id
    )
    assessment = get_object_or_404(
        ActorSentimentAssessment.objects.select_related("actor"),
        pk=assessment_id,
        mention=mention,
    )
    new_value = request.POST.get("sentiment", "")
    valid = {key for key, _label in Mention.SENTIMENT_CHOICES}
    if new_value not in valid:
        messages.error(request, "Nilai sentimen aktor tidak valid.")
        return redirect("analytics:feed")
    if new_value != assessment.sentiment:
        assessment.sentiment = new_value
        assessment.source = ActorSentimentAssessment.SOURCE_MANUAL
        assessment.reviewed_by = request.user.get_full_name() or request.user.username
        assessment.save(update_fields=["sentiment", "source", "reviewed_by", "updated_at"])
        record_audit_entry(
            actor_label=assessment.reviewed_by,
            action="Mengoreksi sentimen per aktor",
            target=f"{assessment.actor.name} / mention {mention.id}: {new_value}",
        )
        messages.success(
            request, f"Sentimen terhadap {assessment.actor.name} diperbarui."
        )
    return redirect("analytics:feed")


@require_page("ringkasan")
def ringkasan(request):
    project = get_active_project(request)
    summary = selectors.ringkasan_summary(project) if project else None
    alerts = selectors.recent_alerts(project) if project else []
    return render(request, "analytics/ringkasan.html", {
        "active_nav": "ringkasan",
        "summary": summary,
        "alerts": alerts,
        "can_export": user_can_access(request.user, "export"),
    })


@require_page("war_room")
def war_room(request):
    project = get_active_project(request)
    issue = (
        PoliticalIssue.objects.filter(
            project=project, status=PoliticalIssue.STATUS_ACTIVE
        ).first()
        if project else None
    )
    summary = selectors.war_room_summary(issue) if issue else None
    return render(request, "analytics/war_room.html", {
        "active_nav": "war_room",
        "summary": summary,
        "issue": issue,
        "response_actions": (
            ResponseAction.objects.filter(issue=issue)[:10] if issue else []
        ),
        "action_choices": ResponseAction.ACTION_CHOICES,
    })


@require_page("narasi")
@require_political_monitoring("Narasi & perbandingan kubu")
def narasi(request):
    project = get_active_project(request)
    issue = (
        PoliticalIssue.objects.filter(
            project=project, status=PoliticalIssue.STATUS_ACTIVE
        ).first()
        if project else None
    )
    summary = selectors.narasi_summary(issue) if issue else None
    return render(request, "analytics/narasi.html", {
        "active_nav": "narasi",
        "summary": summary,
        "neutrality_notice": NEUTRALITY_NOTICE,
    })


@require_page("sosiograf")
def sosiograf(request):
    """Interaction sociograph: influential accounts as a server-rendered graph,
    with coordination-flagged accounts highlighted."""
    project = get_active_project(request)
    summary = selectors.sosiograf_summary(project) if project else None
    return render(request, "analytics/sosiograf.html", {
        "active_nav": "sosiograf",
        "summary": summary,
    })


@require_page("laporan")
def laporan(request):
    """Report center: archive of finalized daily briefs plus a periodic recap of
    the reporting window, with links to the raw-data exports."""
    project = get_active_project(request)
    start_date, end_date, days = _laporan_period(request)
    summary = (
        selectors.laporan_summary(
            project, days=days, start_date=start_date, end_date=end_date
        )
        if project else None
    )
    return render(request, "analytics/laporan.html", {
        "active_nav": "laporan",
        "summary": summary,
        "can_export": user_can_access(request.user, "export"),
    })


def _laporan_period(request):
    try:
        days = min(max(int(request.GET.get("periode", 30)), 1), 366)
    except (TypeError, ValueError):
        days = 30
    end_date = parse_date(request.GET.get("to") or "") or timezone.localdate()
    start_date = parse_date(request.GET.get("from") or "")
    if start_date is None:
        start_date = end_date - timezone.timedelta(days=days - 1)
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    if (end_date - start_date).days >= 366:
        start_date = end_date - timezone.timedelta(days=365)
    return start_date, end_date, (end_date - start_date).days + 1


@require_page("laporan")
def laporan_pdf(request):
    """Generate the reviewed date range as a real PDF inside PANTAU."""
    project = get_active_project(request)
    if project is None:
        raise Http404("Proyek aktif tidak ditemukan.")
    start_date, end_date, days = _laporan_period(request)
    summary = selectors.laporan_summary(
        project, days=days, start_date=start_date, end_date=end_date
    )
    actor = request.user.get_full_name() or request.user.username
    content = media_report_pdf.build(
        summary,
        institution=project.tenant.name,
        project_name=project.name,
        generated_by=actor,
    )
    record_audit_entry(
        actor_label=actor,
        action="Menghasilkan PDF analisis media",
        target=f"{project.name}: {start_date} s.d. {end_date}",
    )
    filename = f"analisis-media-{start_date:%Y%m%d}-{end_date:%Y%m%d}.pdf"
    response = HttpResponse(content, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Content-Length"] = len(content)
    return response


@require_page("regional")
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


@require_page("war_room")
@require_writer_role
@require_POST
def log_response(request, issue_id):
    """Log a response action against the War Room timeline (FR-28.2), creating a
    single auditable record of the narrative event and the institution's response."""
    # Scoped to the caller's project, not looked up by bare id: without the project in the
    # lookup, any analyst could write into another tenant's War Room timeline by guessing
    # an integer (FR-1.2).
    project = get_active_project(request)
    issue = get_object_or_404(PoliticalIssue, pk=issue_id, project=project)
    description = (request.POST.get("description") or "").strip()
    action_type = request.POST.get("action_type", "")
    valid = {key for key, _label in ResponseAction.ACTION_CHOICES}

    if not description or action_type not in valid:
        messages.error(request, "Jenis aksi dan deskripsi wajib diisi.")
        return redirect("analytics:war_room")

    ResponseAction.objects.create(
        issue=issue,
        action_type=action_type,
        description=description,
        logged_by=request.user.get_full_name() or request.user.username,
        occurred_at=timezone.now(),
    )
    record_audit_entry(
        actor_label=request.user.get_full_name() or request.user.username,
        action="Mencatat aksi respons War Room",
        target=issue.title,
    )
    messages.success(request, "Aksi respons dicatat pada linimasa War Room.")
    return redirect("analytics:war_room")


@require_page("brief")
def brief_view(request):
    """Daily Executive Brief (FR-30): draft review workspace for the Analyst /
    Spokesperson — edit, approve, reorder, then finalize (which locks it)."""
    project = get_active_project(request)
    brief_date = request.GET.get("tanggal")
    if brief_date:
        parsed = parse_date(brief_date)
    else:
        parsed = timezone.localdate() - timezone.timedelta(days=1)

    brief = (
        DailyBrief.objects.filter(project=project, brief_date=parsed).first()
        if project else None
    )
    profile = getattr(request.user, "analyst_profile", None)
    can_reopen_brief = profile is not None and profile.role in (
        AnalystProfile.ROLE_TENANT_ADMIN, AnalystProfile.ROLE_SUPER_ADMIN,
    )
    return render(request, "analytics/brief.html", {
        "active_nav": "brief",
        "brief": brief,
        "brief_date": parsed,
        "risk_labels": regulatory.RISK_LABELS,
        "recent": DailyBrief.objects.filter(project=project)[:7] if project else [],
        "can_reopen_brief": can_reopen_brief,
    })


@require_page("brief")
def brief_print(request, brief_id):
    """Standalone print-ready rendering of a brief (save as PDF via the browser's
    print dialog). Drafts carry a watermark — only a final brief speaks for the
    institution (FR-30.2)."""
    project = get_active_project(request)
    brief = get_object_or_404(DailyBrief, pk=brief_id, project=project)
    record_audit_entry(
        actor_label=request.user.get_full_name() or request.user.username,
        action="Membuka brief versi cetak",
        target=str(brief.brief_date),
    )
    return render(request, "analytics/brief_print.html", {
        "brief": brief,
        "instansi": project.tenant.name,
        "proyek": project.name,
        "risk_labels": regulatory.RISK_LABELS,
    })


@require_page("brief")
@require_writer_role
@require_POST
def generate_brief(request):
    project = get_active_project(request)
    parsed = parse_date(request.POST.get("tanggal") or "") or (
        timezone.localdate() - timezone.timedelta(days=1)
    )
    actor = request.user.get_full_name() or request.user.username
    try:
        brief = briefs.generate(project, parsed, triggered_by=actor)
    except briefs.BriefAlreadyGenerating:
        messages.warning(request, "Pembuatan brief untuk tanggal ini sedang berjalan.")
        return redirect(f"{reverse('analytics:brief')}?tanggal={parsed}")
    except briefs.BriefLocked:
        messages.error(request, "Brief sudah final dan tidak dapat dibuat ulang.")
        return redirect(f"{reverse('analytics:brief')}?tanggal={parsed}")

    record_audit_entry(
        actor_label=actor, action="Membuat draf sorotan", target=str(parsed),
    )
    messages.success(
        request,
        f"Draf brief dibuat: {brief.issues.count()} isu. Semua konten AI wajib ditinjau manusia.",
    )
    return redirect(f"{reverse('analytics:brief')}?tanggal={parsed}")


@require_page("brief")
@require_writer_role
@require_POST
def review_brief_issue(request, issue_id):
    item = get_object_or_404(DailyBriefIssue, pk=issue_id)
    actor = request.user.get_full_name() or request.user.username
    action = request.POST.get("action")
    try:
        if action == "save":
            briefs.edit_issue(item, content=request.POST.get("content", ""), edited_by=actor)
            messages.success(request, "Suntingan disimpan.")
        elif action == "approve":
            briefs.approve_issue(item, approved_by=actor)
            messages.success(request, f'Isu "{item.title}" disetujui.')
    except briefs.BriefLocked as exc:
        messages.error(request, str(exc))
    return redirect(f"{reverse('analytics:brief')}?tanggal={item.brief.brief_date}")


@require_page("brief")
@require_writer_role
@require_POST
def finalize_brief(request, brief_id):
    brief = get_object_or_404(DailyBrief, pk=brief_id)
    actor = request.user.get_full_name() or request.user.username
    try:
        briefs.finalize(brief, finalized_by=actor)
    except briefs.BriefNotReviewed as exc:
        messages.error(request, str(exc))
        return redirect(f"{reverse('analytics:brief')}?tanggal={brief.brief_date}")
    except briefs.BriefLocked as exc:
        messages.error(request, str(exc))
        return redirect(f"{reverse('analytics:brief')}?tanggal={brief.brief_date}")

    record_audit_entry(
        actor_label=actor, action="Memfinalisasi sorotan", target=str(brief.brief_date),
    )
    messages.success(request, "Brief difinalisasi dan dikunci.")
    return redirect(f"{reverse('analytics:brief')}?tanggal={brief.brief_date}")


@require_page("brief")
@require_role_at_least(AnalystProfile.ROLE_TENANT_ADMIN, AnalystProfile.ROLE_SUPER_ADMIN)
@require_POST
def reopen_brief(request, brief_id):
    """Emergency correction path (ISS-BTX-001): return a finalized brief to Draft
    so a substantive error (e.g. a misquoted regulation) can be fixed without a
    direct database edit. Restricted to Tenant Admin / Super Admin and recorded
    in the audit log, same as finalize itself."""
    brief = get_object_or_404(DailyBrief, pk=brief_id)
    actor = request.user.get_full_name() or request.user.username
    try:
        briefs.reopen(brief, actor=actor)
    except briefs.BriefNotFinal as exc:
        messages.error(request, str(exc))
        return redirect(f"{reverse('analytics:brief')}?tanggal={brief.brief_date}")

    record_audit_entry(
        actor_label=actor, action="Membuka kembali sorotan untuk revisi", target=str(brief.brief_date),
    )
    messages.success(request, "Brief dibuka kembali sebagai draf.")
    return redirect(f"{reverse('analytics:brief')}?tanggal={brief.brief_date}")


def _actor(request):
    """The human to record against an action — never 'sistem' for a user action."""
    return request.user.get_full_name() or request.user.username


def _get_incident(request, incident_id):
    """Fetch a tenant-scoped incident or 404. Never trust the id alone (FR-1.2)."""
    from .models import Incident

    return get_object_or_404(
        scope_to_tenant(Incident.objects.all(), request), pk=incident_id
    )


@require_page("insiden")
def insiden(request):
    """Incident board: candidates and confirmed incidents as cards."""
    board = selectors.incident_board(
        request,
        window=request.GET.get("periode", "7"),
        opd_slug=request.GET.get("opd", ""),
        severity=request.GET.get("severity", ""),
    )
    from .models import Incident

    return render(request, "analytics/insiden.html", {
        "active_nav": "insiden",
        "board": board,
        "severity_choices": Incident.SEVERITY_CHOICES,
        "filters": {
            "periode": request.GET.get("periode", "7"),
            "opd": request.GET.get("opd", ""),
            "severity": request.GET.get("severity", ""),
        },
    })


@require_page("insiden")
def insiden_detail(request, incident_id):
    incident = selectors.incident_detail(request, incident_id)
    if incident is None:
        raise Http404("Insiden tidak ditemukan.")

    from .models import Incident, OPD

    # Only offer transitions the engine will actually accept (FR: no skipped
    # lifecycle stages). This is a UI convenience — set_status() still enforces
    # the same rule server-side as defence in depth.
    allowed_statuses = incidents.ALLOWED_TRANSITIONS.get(incident.status, set())
    allowed_status_choices = [
        (value, label) for value, label in Incident.STATUS_CHOICES if value in allowed_statuses
    ]

    return render(request, "analytics/insiden_detail.html", {
        "active_nav": "insiden",
        "incident": incident,
        "events": incident.events.all(),
        "related_mentions": incident.mentions.all()[:20],
        "opds": OPD.objects.filter(project=incident.project, is_active=True),
        "status_choices": Incident.STATUS_CHOICES,
        "allowed_status_choices": allowed_status_choices,
    })


@require_page("insiden")
@require_writer_role
@require_POST
def insiden_promote(request, incident_id):
    incident = _get_incident(request, incident_id)
    incidents.promote(incident, by=_actor(request))
    messages.success(request, "Kandidat dikonfirmasi sebagai insiden.")
    return redirect("analytics:insiden_detail", incident_id=incident.pk)


@require_page("insiden")
@require_writer_role
@require_POST
def insiden_assign(request, incident_id):
    from .models import OPD

    incident = _get_incident(request, incident_id)
    opd = get_object_or_404(
        OPD.objects.filter(project=incident.project), pk=request.POST.get("opd")
    )
    incidents.assign(incident, opd, by=_actor(request))
    messages.success(request, f"Insiden ditugaskan ke {opd}.")
    return redirect("analytics:insiden_detail", incident_id=incident.pk)


@require_page("insiden")
@require_writer_role
@require_POST
def insiden_status(request, incident_id):
    incident = _get_incident(request, incident_id)
    try:
        incidents.set_status(incident, request.POST.get("status", ""), by=_actor(request))
        messages.success(request, "Status insiden diperbarui.")
    except incidents.InvalidTransition as exc:
        messages.error(request, str(exc))
    return redirect("analytics:insiden_detail", incident_id=incident.pk)


@require_page("insiden")
@require_writer_role
@require_POST
def insiden_note(request, incident_id):
    incident = _get_incident(request, incident_id)
    description = (request.POST.get("description") or "").strip()
    if not description:
        messages.error(request, "Catatan tidak boleh kosong.")
    else:
        incidents.log_note(incident, description, by=_actor(request))
        messages.success(request, "Catatan ditambahkan ke lini masa.")
    return redirect("analytics:insiden_detail", incident_id=incident.pk)


@require_page("insiden")
@require_writer_role
@require_POST
def insiden_response_generate(request, incident_id):
    incident = _get_incident(request, incident_id)
    actor = _actor(request)
    incidents.generate_response(incident, by=actor)
    record_audit_entry(
        actor_label=actor,
        action="Menyusun draf tanggapan insiden",
        target=incident.title,
    )
    messages.success(
        request,
        "Draf tanggapan disusun. Wajib ditinjau manusia sebelum dikeluarkan ke publik.",
    )
    return redirect("analytics:insiden_detail", incident_id=incident.pk)


@require_page("insiden")
@require_writer_role
@require_POST
def insiden_response_save(request, incident_id):
    incident = _get_incident(request, incident_id)
    text = (request.POST.get("draft_response") or "").strip()
    if not text:
        messages.error(request, "Teks tanggapan tidak boleh kosong.")
    else:
        actor = _actor(request)
        incidents.edit_response(incident, text, by=actor)
        record_audit_entry(
            actor_label=actor,
            action="Menyunting draf tanggapan insiden",
            target=incident.title,
        )
        messages.success(request, "Suntingan tanggapan disimpan.")
    return redirect("analytics:insiden_detail", incident_id=incident.pk)


@require_page("insiden")
@require_writer_role
@require_POST
def insiden_refresh(request):
    project = get_active_project(request)
    if project is None:
        messages.error(request, "Tidak ada proyek aktif.")
    else:
        touched = incidents.refresh_candidates(project)
        messages.success(request, f"{len(touched)} kandidat insiden diperbarui.")
    return redirect("analytics:insiden")
