from .models import AnalystProfile, Project


def _active_profile(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return None
    return AnalystProfile.objects.select_related("tenant").filter(user=user).first()


def get_active_tenant(request):
    """The tenant the requesting user belongs to (FR-1.2)."""
    profile = _active_profile(request)
    return profile.tenant if profile else None


def get_active_project(request):
    profile = _active_profile(request)
    if profile is None:
        return None
    return profile.tenant.projects.first()


def visible_projects(request):
    """Projects the requesting user is allowed to see — only their own tenant's."""
    tenant = get_active_tenant(request)
    if tenant is None:
        return Project.objects.none()
    return Project.objects.filter(tenant=tenant)


def scope_to_tenant(queryset, request, project_path="project"):
    """Restrict ``queryset`` to rows owned by the active tenant, closing any
    cross-tenant leak (FR-1.2). ``project_path`` is the lookup from the model to
    its Project (default ``project`` → filters ``project__tenant``).
    """
    tenant = get_active_tenant(request)
    if tenant is None:
        return queryset.none()
    return queryset.filter(**{f"{project_path}__tenant": tenant})
