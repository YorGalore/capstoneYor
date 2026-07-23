from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.permissions import require_page, require_writer_role
from apps.governance.services import record_audit_entry

from .models import CoordinationCluster


@require_page("koordinasi")
def koordinasi(request):
    clusters = CoordinationCluster.objects.select_related("issue").prefetch_related(
        "accounts", "signals", "duplicate_samples"
    )
    selected_code = request.GET.get("cluster")
    selected = clusters.filter(cluster_code=selected_code).first() if selected_code else clusters.first()

    return render(request, "coordination/koordinasi.html", {
        "active_nav": "koordinasi",
        "clusters": clusters,
        "selected": selected,
    })


@require_page("koordinasi")
@require_writer_role
@require_POST
@transaction.atomic
def escalate_cluster(request, cluster_code):
    cluster = get_object_or_404(CoordinationCluster, cluster_code=cluster_code)
    cluster.status = CoordinationCluster.STATUS_ESCALATED
    cluster.save(update_fields=["status"])
    actor_label = request.user.get_full_name() or request.user.username
    record_audit_entry(
        actor_label=actor_label,
        action="Mengirim klaster ke tinjauan analis senior",
        target=cluster.cluster_code,
    )
    messages.success(request, f"{cluster.cluster_code} dikirim ke tinjauan analis senior.")
    return redirect(f"/koordinasi/?cluster={cluster_code}")


@require_page("koordinasi")
@require_writer_role
@require_POST
@transaction.atomic
def mark_cluster_organic(request, cluster_code):
    cluster = get_object_or_404(CoordinationCluster, cluster_code=cluster_code)
    cluster.status = CoordinationCluster.STATUS_REVIEWED_ORGANIC
    cluster.save(update_fields=["status"])
    actor_label = request.user.get_full_name() or request.user.username
    record_audit_entry(
        actor_label=actor_label,
        action="Menandai klaster sebagai organik (false positive)",
        target=cluster.cluster_code,
    )
    messages.success(request, f"{cluster.cluster_code} ditandai sebagai organik.")
    return redirect(f"/koordinasi/?cluster={cluster_code}")
