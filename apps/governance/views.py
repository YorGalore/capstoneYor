from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.models import AnalystProfile, PagePermission, Platform
from apps.core.selectors import get_active_project
from apps.core.permissions import (
    PAGE_LABELS,
    PAGES,
    ROLES,
    can_access,
    default_can_access,
    is_reserved,
    require_page,
)

from apps.analytics.models import AlertRule, Camp, GovernmentProgram, PoliticalActor

from . import apify, health, neutrality, portal_crawler, runtime, scheduling, scraping
from .forms import (
    AlertRuleForm, CampForm, GovernmentProgramForm, MonitoredDomainForm,
    MonitoringKeywordForm, PoliticalActorForm,
)
from .models import (
    ApifyCredential, AuditLogEntry, CollectionRun, ManualCollectionRequest, MonitoredDomain, MonitoringKeyword,
    PlatformIntegration, PoliticalMonitoringPermission, PolicyAcknowledgment, RuntimeSetting,
    ScheduledJob,
)
from .services import record_audit_entry


def _actor_label(request):
    return request.user.get_full_name() or request.user.username


def _current_project(request):
    return get_active_project(request)


@require_page("konfigurasi")
def konfigurasi(request):
    project = _current_project(request)
    integrations = PlatformIntegration.objects.filter(project=project).select_related("platform").order_by("platform__display_name")
    credential = ApifyCredential.objects.filter(
        project=project,
        status=ApifyCredential.STATUS_ACTIVE,
    ).exclude(token_encrypted="").order_by("-last_verified_at").first()
    domains = MonitoredDomain.objects.filter(project=project).order_by("domain")
    keywords = MonitoringKeyword.objects.filter(project=project)
    recent_runs = CollectionRun.objects.filter(project=project)[:10]
    return render(request, "governance/konfigurasi.html", {
        "active_nav": "konfigurasi",
        "integrations": integrations,
        "credential": credential,
        "domains": domains,
        "keywords": keywords,
        "recent_runs": recent_runs,
        "manual_requests": ManualCollectionRequest.objects.filter(project=project)[:10],
        "domain_form": MonitoredDomainForm(project=project),
        "keyword_form": MonitoringKeywordForm(project=project),
        "schedules": ScheduledJob.objects.filter(project=project).select_related("project"),
        "collector_health": health.collection_health(project=project),
        "health_labels": health.STATUS_LABELS,
        "collection_enabled": scheduling.collection_enabled(),
        "alert_rules": AlertRule.objects.filter(project=project).order_by("name"),
        "alert_rule_form": AlertRuleForm(project=project),
        "camps": Camp.objects.filter(project=project),
        "camp_form": CampForm(project=project),
        "actors": PoliticalActor.objects.filter(project=project).select_related("camp"),
        "actor_form": PoliticalActorForm(project=project),
        "programs": GovernmentProgram.objects.filter(project=project),
        "program_form": GovernmentProgramForm(project=project),
        "election_mode": neutrality.election_mode_active(),
    })


def _form_errors(form):
    return "; ".join(f"{field}: {', '.join(errors)}" for field, errors in form.errors.items())


@require_page("konfigurasi")
@require_POST
@transaction.atomic
def add_alert_rule(request):
    form = AlertRuleForm(request.POST, project=_current_project(request))
    if form.is_valid():
        rule = form.save()
        record_audit_entry(
            actor_label=_actor_label(request), action="Menambahkan aturan peringatan",
            target=rule.name,
        )
        messages.success(request, f'Aturan peringatan "{rule.name}" ditambahkan.')
    else:
        messages.error(request, f"Gagal menambahkan aturan peringatan. {_form_errors(form)}")
    return redirect("governance:konfigurasi")


@require_page("konfigurasi")
@require_POST
@transaction.atomic
def toggle_alert_rule(request, pk):
    rule = get_object_or_404(AlertRule, pk=pk, project=_current_project(request))
    rule.is_active = not rule.is_active
    rule.save(update_fields=["is_active"])
    record_audit_entry(
        actor_label=_actor_label(request),
        action="Mengaktifkan aturan peringatan" if rule.is_active else "Menonaktifkan aturan peringatan",
        target=rule.name,
    )
    return redirect("governance:konfigurasi")


@require_page("konfigurasi")
@require_POST
@transaction.atomic
def delete_alert_rule(request, pk):
    rule = get_object_or_404(AlertRule, pk=pk, project=_current_project(request))
    label = rule.name
    rule.delete()
    record_audit_entry(
        actor_label=_actor_label(request), action="Menghapus aturan peringatan", target=label,
    )
    messages.success(request, f'Aturan peringatan "{label}" dihapus.')
    return redirect("governance:konfigurasi")


@require_page("konfigurasi")
@require_POST
@transaction.atomic
def add_camp(request):
    if neutrality.election_mode_active():
        messages.error(request, "Konfigurasi politik dibekukan selama periode pemilu (§8.5).")
        return redirect("governance:konfigurasi")
    form = CampForm(request.POST, project=_current_project(request))
    if form.is_valid():
        camp = form.save()
        record_audit_entry(
            actor_label=_actor_label(request), action="Menambahkan kubu politik", target=camp.name,
        )
        messages.success(request, f'Kubu "{camp.name}" ditambahkan.')
    else:
        messages.error(request, f"Gagal menambahkan kubu. {_form_errors(form)}")
    return redirect("governance:konfigurasi")


@require_page("konfigurasi")
@require_POST
@transaction.atomic
def delete_camp(request, pk):
    if neutrality.election_mode_active():
        messages.error(request, "Konfigurasi politik dibekukan selama periode pemilu (§8.5).")
        return redirect("governance:konfigurasi")
    camp = get_object_or_404(Camp, pk=pk, project=_current_project(request))
    label = camp.name
    camp.delete()
    record_audit_entry(
        actor_label=_actor_label(request), action="Menghapus kubu politik", target=label,
    )
    messages.success(request, f'Kubu "{label}" dihapus.')
    return redirect("governance:konfigurasi")


@require_page("konfigurasi")
@require_POST
@transaction.atomic
def add_actor(request):
    project = _current_project(request)
    form = PoliticalActorForm(request.POST, project=project)
    if not form.is_valid():
        messages.error(request, f"Gagal menambahkan aktor politik. {_form_errors(form)}")
        return redirect("governance:konfigurasi")
    try:
        # Routed through the neutrality service so the FR-29.3 public-actor
        # allowlist and the §8.5 election-period freeze cannot be bypassed.
        actor = neutrality.create_political_actor(
            project,
            name=form.cleaned_data["name"],
            actor_type=form.cleaned_data["actor_type"],
            camp=form.cleaned_data.get("camp"),
            keywords=form.cleaned_data["keywords"],
            handles=form.cleaned_data["handles"],
        )
    except neutrality.ElectionPeriodFrozen as exc:
        messages.error(request, str(exc))
        return redirect("governance:konfigurasi")
    record_audit_entry(
        actor_label=_actor_label(request), action="Mendaftarkan aktor politik publik",
        target=actor.name,
    )
    messages.success(request, f'Aktor politik "{actor.name}" didaftarkan.')
    return redirect("governance:konfigurasi")


@require_page("konfigurasi")
@require_POST
@transaction.atomic
def toggle_actor(request, pk):
    if neutrality.election_mode_active():
        messages.error(request, "Konfigurasi politik dibekukan selama periode pemilu (§8.5).")
        return redirect("governance:konfigurasi")
    actor = get_object_or_404(PoliticalActor, pk=pk, project=_current_project(request))
    actor.is_active = not actor.is_active
    actor.save(update_fields=["is_active"])
    record_audit_entry(
        actor_label=_actor_label(request),
        action="Mengaktifkan aktor politik" if actor.is_active else "Menonaktifkan aktor politik",
        target=actor.name,
    )
    return redirect("governance:konfigurasi")


@require_page("konfigurasi")
@require_POST
@transaction.atomic
def delete_actor(request, pk):
    if neutrality.election_mode_active():
        messages.error(request, "Konfigurasi politik dibekukan selama periode pemilu (§8.5).")
        return redirect("governance:konfigurasi")
    actor = get_object_or_404(PoliticalActor, pk=pk, project=_current_project(request))
    label = actor.name
    actor.delete()
    record_audit_entry(
        actor_label=_actor_label(request), action="Menghapus aktor politik", target=label,
    )
    messages.success(request, f'Aktor politik "{label}" dihapus.')
    return redirect("governance:konfigurasi")


@require_page("konfigurasi")
@require_POST
@transaction.atomic
def add_program(request):
    form = GovernmentProgramForm(request.POST, project=_current_project(request))
    if form.is_valid():
        program = form.save()
        record_audit_entry(
            actor_label=_actor_label(request), action="Menambahkan program pemerintah terlacak",
            target=program.name,
        )
        messages.success(request, f'Program "{program.name}" ditambahkan.')
    else:
        messages.error(request, f"Gagal menambahkan program. {_form_errors(form)}")
    return redirect("governance:konfigurasi")


@require_page("konfigurasi")
@require_POST
@transaction.atomic
def delete_program(request, pk):
    program = get_object_or_404(GovernmentProgram, pk=pk, project=_current_project(request))
    label = program.name
    program.delete()
    record_audit_entry(
        actor_label=_actor_label(request), action="Menghapus program pemerintah terlacak", target=label,
    )
    messages.success(request, f'Program "{label}" dihapus.')
    return redirect("governance:konfigurasi")


@require_page("konfigurasi")
@require_POST
@transaction.atomic
def save_project_apify_token(request):
    """Let a tenant administrator manage only the active project's Apify token."""
    token = request.POST.get("token", "").strip()
    if not token:
        messages.error(request, "Token tidak boleh kosong.")
        return redirect("governance:konfigurasi")
    try:
        credential = apify.store_token(
            token,
            updated_by=_actor_label(request),
            project=_current_project(request),
        )
    except apify.ApifyTokenInvalid:
        messages.error(request, "Token Apify tidak valid — validasi API langsung gagal.")
        record_audit_entry(
            actor_label=_actor_label(request),
            action="Percobaan menyimpan token Apify tenant gagal validasi",
            target="Apify",
        )
        return redirect("governance:konfigurasi")
    record_audit_entry(
        actor_label=_actor_label(request),
        action="Menyimpan/merotasi token Apify tenant",
        target=credential.masked_token,
    )
    messages.success(request, "Token Apify tenant tervalidasi dan tersimpan terenkripsi.")
    return redirect("governance:konfigurasi")


@require_page("konfigurasi")
@require_POST
@transaction.atomic
def revoke_project_apify_token(request):
    project = _current_project(request)
    apify.revoke(updated_by=_actor_label(request), project=project)
    record_audit_entry(
        actor_label=_actor_label(request),
        action="Mencabut token Apify tenant",
        target=project.name,
    )
    messages.success(request, "Token Apify tenant dicabut.")
    return redirect("governance:konfigurasi")


@require_page("konfigurasi")
@require_POST
def update_schedule(request, job_id):
    """Change a job's cadence or switch it off (REQ-SC-01)."""
    job = get_object_or_404(ScheduledJob, pk=job_id, project=_current_project(request))
    try:
        cadence = int(request.POST.get("cadence_minutes", job.cadence_minutes))
    except ValueError:
        cadence = 0

    if cadence < 1:
        # A zero cadence would make the job due again the instant it finished, spending
        # Apify credits as fast as the scheduler can turn. Refuse rather than accept a
        # value that quietly becomes a runaway bill.
        messages.error(request, "Kadensi harus minimal 1 menit.")
        return redirect("governance:konfigurasi")

    job.cadence_minutes = cadence
    job.enabled = request.POST.get("enabled") == "on"
    job.save(update_fields=["cadence_minutes", "enabled"])

    record_audit_entry(
        actor_label=_actor_label(request),
        action=(
            f"Mengubah jadwal {job.get_job_type_display()}: tiap {cadence} menit, "
            f"{'aktif' if job.enabled else 'nonaktif'}"
        ),
        target=f"scheduled_job:{job.pk}",
    )
    messages.success(request, f"Jadwal {job.get_job_type_display()} diperbarui.")
    return redirect("governance:konfigurasi")


@require_page("konfigurasi")
@require_POST
def toggle_collection(request):
    """The collection kill switch (REQ-LC-03) — halts or resumes all collection."""
    enabled = request.POST.get("enabled") == "1"
    scheduling.set_collection_enabled(enabled, actor=_actor_label(request))
    if enabled:
        messages.success(request, "Koleksi data diaktifkan kembali.")
    else:
        messages.warning(
            request, "Koleksi data dihentikan. Tidak ada data baru yang akan masuk."
        )
    return redirect("governance:konfigurasi")


@require_page("konfigurasi")
@require_POST
@transaction.atomic
def add_keyword(request):
    project = _current_project(request)
    form = MonitoringKeywordForm(request.POST, project=project)
    if form.is_valid():
        keyword = form.save(commit=False)
        keyword.created_by = _actor_label(request)
        keyword.save()
        record_audit_entry(
            actor_label=_actor_label(request),
            action="Menambahkan kata kunci pemantauan",
            target=keyword.keyword,
        )
        messages.success(request, f'Kata kunci "{keyword.keyword}" ditambahkan.')
    else:
        errors = "; ".join(f"{f}: {', '.join(e)}" for f, e in form.errors.items())
        messages.error(request, f"Gagal menambahkan kata kunci. {errors}")
    return redirect("governance:konfigurasi")


@require_page("konfigurasi")
@require_POST
@transaction.atomic
def toggle_keyword(request, pk):
    keyword = get_object_or_404(MonitoringKeyword, pk=pk, project=_current_project(request))
    keyword.is_active = not keyword.is_active
    keyword.save(update_fields=["is_active"])
    record_audit_entry(
        actor_label=_actor_label(request),
        action="Mengaktifkan kata kunci pemantauan" if keyword.is_active else "Menonaktifkan kata kunci pemantauan",
        target=keyword.keyword,
    )
    return redirect("governance:konfigurasi")


@require_page("konfigurasi")
@require_POST
@transaction.atomic
def delete_keyword(request, pk):
    keyword = get_object_or_404(MonitoringKeyword, pk=pk, project=_current_project(request))
    label = keyword.keyword
    keyword.delete()
    record_audit_entry(
        actor_label=_actor_label(request), action="Menghapus kata kunci pemantauan", target=label,
    )
    messages.success(request, f'Kata kunci "{label}" dihapus.')
    return redirect("governance:konfigurasi")


@require_page("konfigurasi")
@require_POST
@transaction.atomic
def add_domain(request):
    form = MonitoredDomainForm(request.POST, project=_current_project(request))
    if form.is_valid():
        domain = form.save()
        record_audit_entry(
            actor_label=_actor_label(request), action="Menambahkan domain pantauan", target=domain.domain,
        )
        messages.success(request, f'Domain "{domain.domain}" ditambahkan.')
    else:
        errors = "; ".join(f"{f}: {', '.join(e)}" for f, e in form.errors.items())
        messages.error(request, f"Gagal menambahkan domain. {errors}")
    return redirect("governance:konfigurasi")


@require_page("konfigurasi")
@require_POST
@transaction.atomic
def delete_domain(request, pk):
    domain = get_object_or_404(MonitoredDomain, pk=pk, project=_current_project(request))
    label = domain.domain
    domain.delete()
    record_audit_entry(
        actor_label=_actor_label(request), action="Menghapus domain pantauan", target=label,
    )
    messages.success(request, f'Domain "{label}" dihapus.')
    return redirect("governance:konfigurasi")


@require_page("konfigurasi")
@require_POST
@transaction.atomic
def test_domain_connection(request, pk):
    domain = get_object_or_404(MonitoredDomain, pk=pk, project=_current_project(request))
    probe_url = domain.feed_url or f"https://{domain.domain}"
    if domain.domain in portal_crawler.PORTALS:
        reachable = portal_crawler.check_reachable(domain)
    else:
        reachable = scraping.check_reachable(probe_url)
    domain.status = MonitoredDomain.STATUS_ACTIVE if reachable else MonitoredDomain.STATUS_NEEDS_REVIEW
    domain.last_tested_at = timezone.now()
    domain.save(update_fields=["status", "last_tested_at"])
    record_audit_entry(
        actor_label=_actor_label(request), action="Menguji koneksi domain pantauan", target=domain.domain,
    )
    if reachable:
        messages.success(request, f'Koneksi ke "{domain.domain}" berhasil.')
    else:
        messages.error(request, f'Tidak dapat menjangkau "{domain.domain}". Status ditandai perlu tinjauan.')
    return redirect("governance:konfigurasi")


def _manual_request_payload(collection_request):
    return {
        "id": collection_request.pk,
        "type": collection_request.collection_type,
        "type_label": collection_request.get_collection_type_display(),
        "status": collection_request.status,
        "status_label": collection_request.get_status_display(),
        "items_found": collection_request.items_found,
        "sources_processed": collection_request.sources_processed,
        "detail": collection_request.detail,
        "requested_at": collection_request.requested_at.isoformat(),
        "started_at": collection_request.started_at.isoformat() if collection_request.started_at else None,
        "finished_at": collection_request.finished_at.isoformat() if collection_request.finished_at else None,
        "terminal": collection_request.status in {
            ManualCollectionRequest.STATUS_COMPLETED,
            ManualCollectionRequest.STATUS_FAILED,
            ManualCollectionRequest.STATUS_SKIPPED,
        },
    }


def _enqueue_collection(request, collection_type):
    project = _current_project(request)
    wants_json = request.headers.get("x-requested-with") == "XMLHttpRequest"

    def reject(message):
        if wants_json:
            return JsonResponse({"ok": False, "message": message}, status=400)
        messages.error(request, message)
        return redirect("governance:konfigurasi")

    if project is None:
        return reject("Tidak ada proyek aktif untuk menyimpan hasil koleksi.")
    if not scheduling.collection_enabled():
        return reject("Koleksi sedang dihentikan. Aktifkan kembali sebelum menjalankan trigger manual.")
    if not MonitoringKeyword.objects.filter(project=project, is_active=True).exists():
        return reject("Tambahkan minimal satu kata kunci aktif sebelum menjalankan koleksi.")

    if collection_type == ManualCollectionRequest.TYPE_NEWS:
        available = MonitoredDomain.objects.filter(project=project).exclude(
            status=MonitoredDomain.STATUS_INACTIVE
        ).exclude(feed_url="").exists()
        if not available:
            return reject("Tambahkan minimal satu domain berita aktif dengan URL starter.")
    else:
        has_token = ApifyCredential.objects.filter(
            project=project, status=ApifyCredential.STATUS_ACTIVE
        ).exclude(token_encrypted="").exists()
        if not has_token:
            return reject("Simpan token Apify aktif sebelum menjalankan koleksi social media.")
        if not PlatformIntegration.objects.filter(
            project=project, method=PlatformIntegration.METHOD_APIFY, is_active=True,
        ).exists():
            return reject("Aktifkan minimal satu integrasi social media berbasis Apify.")

    active_request = ManualCollectionRequest.objects.filter(
        project=project,
        collection_type=collection_type,
        status__in=[ManualCollectionRequest.STATUS_QUEUED, ManualCollectionRequest.STATUS_RUNNING],
    ).first()
    if active_request:
        message = f"Koleksi {active_request.get_collection_type_display()} sudah {active_request.get_status_display().lower()}."
        if wants_json:
            return JsonResponse({"ok": True, "message": message, "request": _manual_request_payload(active_request)}, status=202)
        messages.info(request, message)
        return redirect("governance:konfigurasi")

    collection_request = ManualCollectionRequest.objects.create(
        project=project, collection_type=collection_type, requested_by=_actor_label(request),
    )
    record_audit_entry(
        actor_label=_actor_label(request),
        action=f"Mengantrekan koleksi manual {collection_request.get_collection_type_display()}",
        target=f"manual_collection:{collection_request.pk}",
    )
    message = f"Koleksi {collection_request.get_collection_type_display()} masuk antrean worker."
    if wants_json:
        return JsonResponse({"ok": True, "message": message, "request": _manual_request_payload(collection_request)}, status=202)
    messages.success(request, message)
    return redirect("governance:konfigurasi")


@require_page("konfigurasi")
@require_POST
def queue_news_collection(request):
    return _enqueue_collection(request, ManualCollectionRequest.TYPE_NEWS)


@require_page("konfigurasi")
@require_POST
def queue_social_collection(request):
    return _enqueue_collection(request, ManualCollectionRequest.TYPE_SOCIAL)


@require_page("konfigurasi")
def collection_request_status(request, pk):
    collection_request = get_object_or_404(
        ManualCollectionRequest, pk=pk, project=_current_project(request)
    )
    return JsonResponse({"ok": True, "request": _manual_request_payload(collection_request)})


@require_page("konfigurasi")
@require_POST
@transaction.atomic
def _legacy_synchronous_run_scan(request):
    project = _current_project(request)
    keywords = list(MonitoringKeyword.objects.filter(project=project, is_active=True))
    if not keywords:
        messages.error(request, "Tambahkan minimal satu kata kunci aktif sebelum menjalankan pemindaian.")
        return redirect("governance:konfigurasi")

    domains = list(MonitoredDomain.objects.filter(project=project).exclude(feed_url=""))
    if not domains:
        messages.error(request, "Tambahkan minimal satu domain dengan URL starter sebelum menjalankan pemindaian.")
        return redirect("governance:konfigurasi")

    if project is None:
        messages.error(request, "Tidak ada proyek aktif untuk menyimpan hasil pemindaian.")
        return redirect("governance:konfigurasi")

    platform, _ = Platform.objects.get_or_create(
        slug="berita", defaults={"display_name": "Berita Daring", "brand_color": "#0E7C86"},
    )

    result = scraping.run_scan(project=project, platform=platform, domains=domains, keywords=keywords)

    record_audit_entry(
        actor_label=_actor_label(request),
        action="Menjalankan pemindaian berita langsung",
        target=f"{result['new_mentions']} mention baru dari {result['sources_scanned']} sumber",
    )

    if result["new_mentions"]:
        messages.success(
            request,
            f"Pemindaian selesai: {result['new_mentions']} mention baru dari "
            f"{result['sources_scanned']} sumber.",
        )
    else:
        messages.info(
            request,
            f"Pemindaian selesai: tidak ada artikel baru yang cocok dari {result['sources_scanned']} sumber.",
        )
    for error in result["errors"]:
        messages.warning(request, f"Sumber gagal dipindai — {error}")

    return redirect("governance:konfigurasi")


@require_page("konfigurasi")
@require_POST
@transaction.atomic
def toggle_integration(request, pk):
    integration = get_object_or_404(
        PlatformIntegration, pk=pk, project=_current_project(request)
    )
    integration.is_active = not integration.is_active
    integration.save(update_fields=["is_active"])
    record_audit_entry(
        actor_label=_actor_label(request),
        action="Mengaktifkan integrasi platform" if integration.is_active else "Menonaktifkan integrasi platform",
        target=integration.platform.display_name,
    )
    return redirect("governance:konfigurasi")


@require_page("pengawasan")
def pengawasan(request):
    permissions = PoliticalMonitoringPermission.objects.filter(active=True).select_related("user")
    total_users = AnalystProfile.objects.count()
    political_query_count = AuditLogEntry.objects.filter(
        action__icontains="kueri", timestamp__gte=timezone.now() - timezone.timedelta(days=30)
    ).count()
    excluded_profile_count = AuditLogEntry.objects.filter(action__icontains="dikecualikan").count()
    audit_entries = AuditLogEntry.objects.all()[:20]
    policy_ack = PolicyAcknowledgment.objects.order_by("-approved_at").first()

    return render(request, "governance/pengawasan.html", {
        "active_nav": "pengawasan",
        "permissions": permissions,
        "permission_count": permissions.count(),
        "total_users": total_users,
        "political_query_count": political_query_count,
        "excluded_profile_count": excluded_profile_count,
        "audit_entries": audit_entries,
        "policy_ack": policy_ack,
    })


@require_page("permission_matrix")
def permission_matrix(request):
    """Super-Admin-only editor for the role × page access matrix (FR-1A)."""
    rows = []
    for page_slug, page_label in PAGES:
        cells = []
        for role in ROLES:
            cells.append({
                "role": role,
                "allowed": can_access(role, page_slug),
                "reserved": is_reserved(role, page_slug),
            })
        rows.append({"page": page_slug, "label": page_label, "cells": cells})

    role_labels = dict(AnalystProfile.ROLE_CHOICES)
    return render(request, "governance/permission_matrix.html", {
        "active_nav": "permission_matrix",
        "rows": rows,
        "roles": [{"key": r, "label": role_labels.get(r, r)} for r in ROLES],
    })


@require_page("permission_matrix")
@require_POST
@transaction.atomic
def toggle_permission(request):
    role = request.POST.get("role", "")
    page = request.POST.get("page", "")
    if role not in ROLES or page not in PAGE_LABELS:
        messages.error(request, "Kombinasi peran/halaman tidak dikenal.")
        return redirect("governance:permission_matrix")
    if is_reserved(role, page):
        messages.error(request, "Sel ini dilindungi dan tidak dapat diubah.")
        return redirect("governance:permission_matrix")

    row, _ = PagePermission.objects.get_or_create(
        role=role, page=page, defaults={"can_access": default_can_access(role, page)}
    )
    row.can_access = not row.can_access
    row.updated_by = _actor_label(request)
    row.save(update_fields=["can_access", "updated_by", "updated_at"])

    record_audit_entry(
        actor_label=_actor_label(request),
        action=f"Mengubah izin halaman menjadi {'izin' if row.can_access else 'tolak'}",
        target=f"{role} × {page}",
    )
    messages.success(request, f"Izin {role} untuk {PAGE_LABELS[page]} diperbarui.")
    return redirect("governance:permission_matrix")


@require_page("runtime_settings")
def runtime_settings(request):
    """Dev/Ops settings page (Super-Admin only, FR-1A.3): Runtime Settings list
    and Apify credential management (FR-2A.3/2A.9-11)."""
    settings_rows = [
        {
            "key": row.key,
            "value": runtime.masked_value(row),
            "is_secret": row.is_secret,
            "updated_by": row.updated_by,
            "updated_at": row.updated_at,
        }
        for row in RuntimeSetting.objects.all()
    ]
    project = _current_project(request)
    active_credential = ApifyCredential.objects.filter(
        project=project,
        status=ApifyCredential.STATUS_ACTIVE
    ).order_by("-id").first()
    return render(request, "governance/runtime_settings.html", {
        "active_nav": "runtime_settings",
        "settings_rows": settings_rows,
        "reserved_keys": sorted(runtime.RESERVED_KEYS),
        "active_credential": active_credential,
    })


@require_page("runtime_settings")
@require_POST
@transaction.atomic
def save_apify_token(request):
    token = request.POST.get("token", "").strip()
    if not token:
        messages.error(request, "Token tidak boleh kosong.")
        return redirect("governance:runtime_settings")
    try:
        cred = apify.store_token(
            token, updated_by=_actor_label(request), project=_current_project(request)
        )
    except apify.ApifyTokenInvalid:
        messages.error(request, "Token Apify tidak valid — validasi API langsung gagal.")
        record_audit_entry(
            actor_label=_actor_label(request),
            action="Percobaan menyimpan token Apify gagal validasi",
            target="Apify",
        )
        return redirect("governance:runtime_settings")
    record_audit_entry(
        actor_label=_actor_label(request),
        action="Menyimpan/merotasi token Apify",
        target=cred.masked_token,
    )
    messages.success(request, "Token Apify tervalidasi dan tersimpan (terenkripsi).")
    return redirect("governance:runtime_settings")


@require_page("runtime_settings")
@require_POST
@transaction.atomic
def revoke_apify_token(request):
    apify.revoke(updated_by=_actor_label(request), project=_current_project(request))
    record_audit_entry(
        actor_label=_actor_label(request), action="Mencabut token Apify", target="Apify",
    )
    messages.success(request, "Token Apify dicabut.")
    return redirect("governance:runtime_settings")


@require_page("runtime_settings")
@require_POST
@transaction.atomic
def save_runtime_setting(request):
    key = request.POST.get("key", "").strip()
    value = request.POST.get("value", "")
    is_secret = bool(request.POST.get("is_secret"))
    if not key:
        messages.error(request, "Kunci pengaturan wajib diisi.")
        return redirect("governance:runtime_settings")
    try:
        runtime.set_setting(key, value, updated_by=_actor_label(request), is_secret=is_secret)
    except runtime.RuntimeSettingReserved as exc:
        messages.error(request, str(exc))
        return redirect("governance:runtime_settings")
    record_audit_entry(
        actor_label=_actor_label(request), action="Memperbarui Runtime Setting", target=key,
    )
    messages.success(request, f'Pengaturan "{key}" diperbarui.')
    return redirect("governance:runtime_settings")
