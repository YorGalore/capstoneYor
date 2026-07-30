"""Configurable page-level permission matrix (FR-1A).

Access is governed by a database-backed matrix of (role × page) → allowed/denied,
with secure defaults and a small set of permanently reserved combinations that
cannot be edited away:

* The Platform Super Admin is always fully permitted (FR-1A.3).
* The Dev/Operations settings page and the permission-matrix editor are reserved
  to the Super Admin and can never be granted to another role via the matrix.
"""
from functools import wraps

from django.core.exceptions import PermissionDenied

from .models import AnalystProfile, PagePermission

R = AnalystProfile

# Registry of gate-able pages: (slug, human label).
PAGES = [
    ("ringkasan", "Ringkasan"),
    ("feed", "Umpan Sebutan"),
    ("narasi", "Narasi Politik"),
    ("war_room", "War Room"),
    ("insiden", "Insiden"),
    ("koordinasi", "Deteksi Koordinasi"),
    ("regional", "Regional"),
    ("sosiograf", "Sosiograf"),
    ("laporan", "Laporan"),
    ("konfigurasi", "Konfigurasi"),
    ("pengawasan", "Pengawasan"),
    ("brief", "Sorotan"),
    ("taxonomy", "Taksonomi Isu"),
    ("drivers", "Alasan Keluhan"),
    ("export", "Ekspor Data"),
    ("permission_matrix", "Matriks Izin Halaman"),
    ("runtime_settings", "Pengaturan Dev/Ops"),
    ("onboarding_requests", "Permintaan Demo"),
]
PAGE_LABELS = dict(PAGES)

DEV_OPS_PAGE = "runtime_settings"
# Pages reserved to the Super Admin only — never grantable to another role.
SUPER_ADMIN_ONLY_PAGES = {DEV_OPS_PAGE, "permission_matrix", "onboarding_requests"}

# The Daily Brief is written for the Spokesperson/Pimpinan persona and reviewed by
# Analysts (FR-30.3), so both roles reach it by default — unlike the operational
# "tool" pages, which stay denied by default (FR-1A.1). "feed" also defaults in:
# sentiment correction (FR-5.3) is core Analyst work, not an opt-in extra an admin
# has to remember to grant.
DASHBOARD_PAGES = {
    "ringkasan", "narasi", "war_room", "koordinasi", "regional", "brief",
    "sosiograf", "laporan", "insiden", "feed",
}
ROLES = [R.ROLE_SUPER_ADMIN, R.ROLE_TENANT_ADMIN, R.ROLE_ANALYST, R.ROLE_VIEWER]


def is_reserved(role, page):
    """A reserved cell is fixed by policy and not editable through the matrix."""
    if role == R.ROLE_SUPER_ADMIN:
        return True
    if page in SUPER_ADMIN_ONLY_PAGES:
        return True
    return False


def default_can_access(role, page):
    """Secure default for a cell when no explicit matrix row exists."""
    if role == R.ROLE_SUPER_ADMIN:
        return True
    if page in SUPER_ADMIN_ONLY_PAGES:
        return False
    if role == R.ROLE_TENANT_ADMIN:
        return True
    if role == R.ROLE_ANALYST:
        return page in DASHBOARD_PAGES or page == "export"
    if role == R.ROLE_VIEWER:
        return page in DASHBOARD_PAGES
    return False


def can_access(role, page):
    if role == R.ROLE_SUPER_ADMIN:
        return True
    if page in SUPER_ADMIN_ONLY_PAGES:
        return False
    row = PagePermission.objects.filter(role=role, page=page).first()
    if row is not None:
        return row.can_access
    return default_can_access(role, page)


def user_can_access(user, page):
    profile = getattr(user, "analyst_profile", None)
    if profile is None:
        return False
    return can_access(profile.role, page)


def seed_permission_matrix():
    """Idempotently materialize the editable cells with their secure defaults."""
    for role in ROLES:
        for page, _label in PAGES:
            if is_reserved(role, page):
                continue
            PagePermission.objects.get_or_create(
                role=role, page=page, defaults={"can_access": default_can_access(role, page)}
            )


def require_page(page):
    """View decorator gating access to ``page`` via the permission matrix."""

    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not user_can_access(request.user, page):
                raise PermissionDenied(f"Akses ditolak untuk halaman: {page}")
            return view(request, *args, **kwargs)

        return wrapped

    return decorator


def require_writer_role(view):
    """Restrict a write action to roles above Peninjau (viewer), independent of the
    page-level read gate.

    Several DASHBOARD_PAGES entries (war_room, brief, insiden) intentionally grant
    Peninjau default *read* access, since viewing is exactly what a read-only role
    is for. But that same page-level grant would also cover a mutating POST view
    decorated only with @require_page, letting a viewer write into an auditable
    timeline it can only legitimately observe. This decorator closes that gap for
    the write action specifically, leaving the page's read access untouched.
    """

    @wraps(view)
    def wrapped(request, *args, **kwargs):
        profile = getattr(request.user, "analyst_profile", None)
        if profile is None or profile.role == AnalystProfile.ROLE_VIEWER:
            raise PermissionDenied("Peran Peninjau tidak memiliki akses tulis pada halaman ini.")
        return view(request, *args, **kwargs)

    return wrapped


def require_role_at_least(*roles):
    """Restrict a view to an explicit set of roles, stricter than require_writer_role.

    Used for actions that only make sense for Tenant Admin / Super Admin even though
    Analyst can otherwise write to the same page (e.g. reopening a finalized brief).
    """

    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            profile = getattr(request.user, "analyst_profile", None)
            if profile is None or profile.role not in roles:
                raise PermissionDenied("Peran Anda tidak memiliki akses untuk aksi ini.")
            return view(request, *args, **kwargs)

        return wrapped

    return decorator
