"""Governance, neutrality & oversight controls (FR-29, SRS §8.5).

These are mandatory, not optional. Because this Platform monitors political
conversation on behalf of a government body, these controls exist to prevent it
being used to target, profile, or suppress individual citizens or political
opponents:

* FR-29.1 — political-actor tracking and camp comparison require an explicit
  Political Monitoring permission, separate from standard Analyst access.
* FR-29.2 — every political query is written to the immutable audit trail.
* FR-29.3 — the data model refuses to create a profile on a private individual;
  only parties, coalitions, public officials/candidates, and organizational
  accounts may be registered as trackable actors.
* FR-29.5 — a persistent purpose/prohibited-use notice is shown on political views.
* §8.5 — an "election period" mode freezes political-actor configuration.
"""
from functools import wraps

from django.core.exceptions import PermissionDenied, ValidationError

from apps.analytics.models import PoliticalActor

from .models import PoliticalMonitoringPermission
from .runtime import get_setting, set_setting
from .services import record_audit_entry

ELECTION_MODE_KEY = "governance.election_period_mode"

# The only actor types that may ever be profiled (FR-29.3). A private citizen's
# personal account is deliberately absent and cannot be added through config.
PUBLIC_ACTOR_TYPES = {
    PoliticalActor.TYPE_PARTY,
    PoliticalActor.TYPE_COALITION,
    PoliticalActor.TYPE_OFFICIAL,
    PoliticalActor.TYPE_ORGANIZATION,
}

NEUTRALITY_NOTICE = (
    "Platform ini digunakan untuk pemantauan opini publik dan pelaporan netral "
    "berbasis bukti. Dilarang digunakan untuk menargetkan, menekan, atau memprofilkan "
    "individu warga negara maupun lawan politik."
)


class ElectionPeriodFrozen(Exception):
    """Raised when political configuration is changed during an election period."""


def has_political_monitoring_permission(user):
    if not user.is_authenticated:
        return False
    return PoliticalMonitoringPermission.objects.filter(user=user, active=True).exists()


def require_political_monitoring(query_label):
    """Gate a political-narrative view on the Political Monitoring permission
    (FR-29.1) and record the access in the audit trail (FR-29.2)."""

    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not has_political_monitoring_permission(request.user):
                raise PermissionDenied(
                    "Akses pemantauan politik memerlukan izin Pemantauan Politik "
                    "yang disetujui Pejabat Kepatuhan."
                )
            record_audit_entry(
                actor_label=request.user.get_full_name() or request.user.username,
                action=f"Kueri pemantauan politik — {query_label}",
                target=request.get_full_path()[:150],
            )
            return view(request, *args, **kwargs)

        return wrapped

    return decorator


def is_private_individual(handle, project):
    """True unless the handle belongs to a registered public/organizational actor.
    Private citizens' personal accounts are never political-actor tagged (FR-29.3)."""
    normalized = (handle or "").lower().lstrip("@")
    for actor in PoliticalActor.objects.filter(project=project, is_active=True):
        if any(h.lower().lstrip("@") == normalized for h in (actor.handles or []) if h):
            return False
    return True


def election_mode_active():
    return get_setting(ELECTION_MODE_KEY) == "on"


def set_election_mode(enabled, updated_by):
    set_setting(ELECTION_MODE_KEY, "on" if enabled else "off", updated_by=updated_by)
    record_audit_entry(
        actor_label=updated_by,
        action="Mengaktifkan mode periode pemilu" if enabled else "Menonaktifkan mode periode pemilu",
        target="Konfigurasi pemantauan politik",
    )


def create_political_actor(project, name, actor_type, camp=None, keywords=None, handles=None):
    """Create a trackable political actor, enforcing the FR-29.3 allowlist and the
    §8.5 election-period configuration freeze."""
    if election_mode_active():
        raise ElectionPeriodFrozen(
            "Konfigurasi aktor politik dibekukan selama periode pemilu. "
            "Perubahan memerlukan tinjauan Pejabat Kepatuhan."
        )
    if actor_type not in PUBLIC_ACTOR_TYPES:
        raise ValidationError(
            "Hanya partai, koalisi, pejabat/kandidat publik, dan organisasi yang boleh "
            "didaftarkan sebagai aktor politik. Individu privat tidak boleh diprofilkan (FR-29.3)."
        )
    return PoliticalActor.objects.create(
        project=project,
        name=name,
        actor_type=actor_type,
        camp=camp,
        keywords=keywords or [],
        handles=handles or [],
    )
