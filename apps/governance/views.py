from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.models import AnalystProfile, PagePermission, Platform
from apps.core.permissions import (
    PAGE_LABELS,
    PAGES,
    ROLES,
    can_access,
    default_can_access,
    is_reserved,
    require_page,
)

from . import apify, runtime, scraping
from .forms import MonitoredDomainForm, MonitoringKeywordForm
from .models import (
    ApifyCredential, AuditLogEntry, CollectionRun, MonitoredDomain, MonitoringKeyword,
    PlatformIntegration, PoliticalMonitoringPermission, PolicyAcknowledgment, RuntimeSetting,
)
from .services import record_audit_entry


def _actor_label(request):
    return request.user.get_full_name() or request.user.username


def _current_project(request):
    profile = AnalystProfile.objects.select_related("tenant").filter(user=request.user).first()
    if profile is None:
        return None
    return profile.tenant.projects.first()


@require_page("konfigurasi")
def konfigurasi(request):
    integrations = PlatformIntegration.objects.select_related("platform").order_by("platform__display_name")
    credential = ApifyCredential.objects.order_by("-last_verified_at").first()
    domains = MonitoredDomain.objects.order_by("domain")
    keywords = MonitoringKeyword.objects.all()
    recent_runs = CollectionRun.objects.all()[:10]
    return render(request, "governance/konfigurasi.html", {
        "active_nav": "konfigurasi",
        "integrations": integrations,
        "credential": credential,
        "domains": domains,
        "keywords": keywords,
        "recent_runs": recent_runs,
        "domain_form": MonitoredDomainForm(),
        "keyword_form": MonitoringKeywordForm(),
    })


@require_POST
@transaction.atomic
def add_keyword(request):
    form = MonitoringKeywordForm(request.POST)
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


@require_POST
@transaction.atomic
def toggle_keyword(request, pk):
    keyword = get_object_or_404(MonitoringKeyword, pk=pk)
    keyword.is_active = not keyword.is_active
    keyword.save(update_fields=["is_active"])
    record_audit_entry(
        actor_label=_actor_label(request),
        action="Mengaktifkan kata kunci pemantauan" if keyword.is_active else "Menonaktifkan kata kunci pemantauan",
        target=keyword.keyword,
    )
    return redirect("governance:konfigurasi")


@require_POST
@transaction.atomic
def delete_keyword(request, pk):
    keyword = get_object_or_404(MonitoringKeyword, pk=pk)
    label = keyword.keyword
    keyword.delete()
    record_audit_entry(
        actor_label=_actor_label(request), action="Menghapus kata kunci pemantauan", target=label,
    )
    messages.success(request, f'Kata kunci "{label}" dihapus.')
    return redirect("governance:konfigurasi")


@require_POST
@transaction.atomic
def add_domain(request):
    form = MonitoredDomainForm(request.POST)
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


@require_POST
@transaction.atomic
def delete_domain(request, pk):
    domain = get_object_or_404(MonitoredDomain, pk=pk)
    label = domain.domain
    domain.delete()
    record_audit_entry(
        actor_label=_actor_label(request), action="Menghapus domain pantauan", target=label,
    )
    messages.success(request, f'Domain "{label}" dihapus.')
    return redirect("governance:konfigurasi")


@require_POST
@transaction.atomic
def test_domain_connection(request, pk):
    domain = get_object_or_404(MonitoredDomain, pk=pk)
    probe_url = domain.feed_url or f"https://{domain.domain}"
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


@require_POST
@transaction.atomic
def run_scan(request):
    keywords = list(MonitoringKeyword.objects.filter(is_active=True))
    if not keywords:
        messages.error(request, "Tambahkan minimal satu kata kunci aktif sebelum menjalankan pemindaian.")
        return redirect("governance:konfigurasi")

    domains = list(MonitoredDomain.objects.exclude(feed_url=""))
    if not domains:
        messages.error(request, "Tambahkan minimal satu domain dengan URL feed RSS sebelum menjalankan pemindaian.")
        return redirect("governance:konfigurasi")

    project = _current_project(request)
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


@require_POST
@transaction.atomic
def toggle_integration(request, pk):
    integration = get_object_or_404(PlatformIntegration, pk=pk)
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
    active_credential = ApifyCredential.objects.filter(
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
        cred = apify.store_token(token, updated_by=_actor_label(request))
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
    apify.revoke(updated_by=_actor_label(request))
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
