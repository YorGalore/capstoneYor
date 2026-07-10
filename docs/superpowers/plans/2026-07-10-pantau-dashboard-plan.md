# PANTAU Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Django app implementing the 7 PANTAU dashboard screens (Ringkasan, War Room, Perbandingan Narasi, Deteksi Koordinasi, Regional, Konsol Konfigurasi, Pengawasan) against real Django models populated with seeded fictional data.

**Architecture:** Django project `pantau` with four apps — `apps.core` (tenant/reference data, shared chrome, demo auth), `apps.analytics` (Mention fact table + Ringkasan/War Room/Narasi/Regional views), `apps.coordination` (coordination cluster detection), `apps.governance` (platform config + oversight/audit). Server-rendered templates, no JS framework, inline SVG charts computed in Python selectors and interpolated into templates.

**Tech Stack:** Django 5.x, SQLite (dev), vanilla CSS ported from the design doc's Archivo/IBM Plex Sans/Mono system, no DRF/frontend framework.

## Global Constraints

- All UI copy is in Bahasa Indonesia, matching `docs/design/pantau/screen_*.html` and `docs/superpowers/specs/2026-07-10-pantau-dashboard-design.md`.
- Neutrality/audit-logging banner text (FR-29.5, FR-26.2/26.4, etc.) must be reproduced verbatim from the design reference files where a screen includes one.
- No live ingestion, no login screen, no REST API — per the spec's "Out of scope" section.
- Every app that writes data must also be covered by a test that runs the write and asserts the resulting state (no untested mutations).
- Seed functions must be idempotent (`get_or_create` / existence checks) — `seed_demo_data` must be safe to run multiple times.
- Design reference markup lives at `docs/design/pantau/screen_1a.html` .. `screen_1g.html` and `docs/design/pantau/shared_style.css` — port structure/colors from these into templates/CSS; hardcoded numbers in the reference files are illustrative only and must be replaced with template variables bound to real querysets.

---

### Task 1: Project scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `manage.py`
- Create: `pantau/__init__.py`
- Create: `pantau/settings.py`
- Create: `pantau/urls.py`
- Create: `pantau/wsgi.py`
- Create: `pantau/asgi.py`
- Create: `apps/__init__.py`
- Create: `apps/core/__init__.py`
- Create: `apps/core/apps.py`
- Create: `apps/core/models.py` (empty for now)
- Create: `apps/core/middleware.py` (pass-through stub)
- Create: `apps/core/context_processors.py` (stub)
- Create: `apps/core/migrations/__init__.py`
- Create: `apps/core/tests/__init__.py`
- Create: `apps/analytics/__init__.py`, `apps/analytics/apps.py`, `apps/analytics/models.py` (empty), `apps/analytics/migrations/__init__.py`
- Create: `apps/coordination/__init__.py`, `apps/coordination/apps.py`, `apps/coordination/models.py` (empty), `apps/coordination/migrations/__init__.py`
- Create: `apps/governance/__init__.py`, `apps/governance/apps.py`, `apps/governance/models.py` (empty), `apps/governance/migrations/__init__.py`
- Test: `apps/core/tests/test_scaffolding.py`

**Interfaces:**
- Produces: `apps.core.middleware.DemoUserMiddleware` (pass-through stub, real logic in Task 3), `apps.core.context_processors.tenant_context(request) -> dict` (stub returning `{}`, real logic in Task 3), bootable settings module `pantau.settings`.

- [ ] **Step 1: Create `requirements.txt` and install**

```
Django>=5.0,<6.0
```

Run:
```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
```

- [ ] **Step 2: Create the Django project files**

`manage.py`:
```python
#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pantau.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

`pantau/__init__.py`: empty file.

`pantau/settings.py`:
```python
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "dev-only-secret-key-change-before-production"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.core",
    "apps.analytics",
    "apps.coordination",
    "apps.governance",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.middleware.DemoUserMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "pantau.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.tenant_context",
            ],
        },
    },
]

WSGI_APPLICATION = "pantau.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "id"
TIME_ZONE = "Asia/Jakarta"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

`pantau/urls.py`:
```python
from django.contrib import admin
from django.urls import path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(url="/admin/", permanent=False)),
]
```

`pantau/wsgi.py`:
```python
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pantau.settings")

application = get_wsgi_application()
```

`pantau/asgi.py`:
```python
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pantau.settings")

application = get_asgi_application()
```

- [ ] **Step 3: Write the failing smoke test**

`apps/core/tests/test_scaffolding.py`:
```python
from django.test import TestCase


class ScaffoldingSmokeTest(TestCase):
    def test_admin_login_page_loads(self):
        response = self.client.get("/admin/login/")
        self.assertEqual(response.status_code, 200)
```

- [ ] **Step 4: Run the test, verify it fails**

Run: `python manage.py test apps.core.tests.test_scaffolding -v 2`
Expected: FAIL with `ModuleNotFoundError: No module named 'apps'`

- [ ] **Step 5: Create the four app packages**

`apps/__init__.py`: empty file.

`apps/core/__init__.py`: empty file.
`apps/core/apps.py`:
```python
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
```
`apps/core/models.py`: empty file (no models yet).
`apps/core/middleware.py`:
```python
class DemoUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)
```
`apps/core/context_processors.py`:
```python
def tenant_context(request):
    return {}
```
`apps/core/migrations/__init__.py`: empty file.
`apps/core/tests/__init__.py`: empty file.

`apps/analytics/__init__.py`: empty file.
`apps/analytics/apps.py`:
```python
from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.analytics"
```
`apps/analytics/models.py`: empty file.
`apps/analytics/migrations/__init__.py`: empty file.

`apps/coordination/__init__.py`: empty file.
`apps/coordination/apps.py`:
```python
from django.apps import AppConfig


class CoordinationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.coordination"
```
`apps/coordination/models.py`: empty file.
`apps/coordination/migrations/__init__.py`: empty file.

`apps/governance/__init__.py`: empty file.
`apps/governance/apps.py`:
```python
from django.apps import AppConfig


class GovernanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.governance"
```
`apps/governance/models.py`: empty file.
`apps/governance/migrations/__init__.py`: empty file.

- [ ] **Step 6: Migrate and run the test again**

Run:
```bash
python manage.py migrate
python manage.py test apps.core.tests.test_scaffolding -v 2
```
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add requirements.txt manage.py pantau apps
git commit -m "Scaffold Django project with four empty apps"
```

---

### Task 2: Core reference-data models

**Files:**
- Modify: `apps/core/models.py`
- Create: `apps/core/admin.py`
- Create: `apps/core/migrations/0001_initial.py` (via `makemigrations`)
- Test: `apps/core/tests/test_models.py`

**Interfaces:**
- Consumes: nothing new (uses `django.contrib.auth` `User` from Task 1's `INSTALLED_APPS`).
- Produces: `apps.core.models.Tenant`, `Project`, `Platform` (with `METHOD_APIFY`/`METHOD_INTERNAL` constants), `Province`, `Regency`, `AnalystProfile` (fields: `user` 1:1, `tenant` FK, `role_label`, `has_political_monitoring_permission`).

- [ ] **Step 1: Write the failing test**

`apps/core/tests/test_models.py`:
```python
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.core.models import AnalystProfile, Platform, Province, Regency, Project, Tenant


class CoreModelsTest(TestCase):
    def test_tenant_project_str(self):
        tenant = Tenant.objects.create(name="Kemenko PMK")
        project = Project.objects.create(tenant=tenant, name="Program Pangan Rakyat")
        self.assertEqual(str(tenant), "Kemenko PMK")
        self.assertEqual(str(project), "Program Pangan Rakyat")

    def test_platform_str(self):
        platform = Platform.objects.create(
            slug="x", display_name="X (Twitter)", method=Platform.METHOD_INTERNAL
        )
        self.assertEqual(str(platform), "X (Twitter)")

    def test_province_and_regency(self):
        province = Province.objects.create(name="Maluku", population_online=800000)
        regency = Regency.objects.create(province=province, name="Kota Ambon")
        self.assertEqual(str(regency), "Kota Ambon, Maluku")

    def test_analyst_profile(self):
        tenant = Tenant.objects.create(name="Kemenko PMK")
        user = get_user_model().objects.create_user(
            username="dewi.anjani", first_name="Dewi", last_name="Anjani"
        )
        profile = AnalystProfile.objects.create(
            user=user, tenant=tenant, role_label="Analis Humas",
            has_political_monitoring_permission=True,
        )
        self.assertIn("Analis Humas", str(profile))
```

- [ ] **Step 2: Run the test, verify it fails**

Run: `python manage.py test apps.core.tests.test_models -v 2`
Expected: FAIL with `ImportError: cannot import name 'Tenant'`

- [ ] **Step 3: Write the models**

`apps/core/models.py`:
```python
from django.conf import settings
from django.db import models


class Tenant(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Project(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Platform(models.Model):
    METHOD_APIFY = "apify"
    METHOD_INTERNAL = "internal"
    METHOD_CHOICES = [(METHOD_APIFY, "Apify"), (METHOD_INTERNAL, "Internal")]

    slug = models.SlugField(unique=True)
    display_name = models.CharField(max_length=100)
    brand_color = models.CharField(max_length=7, default="#0E7C86")
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default=METHOD_INTERNAL)

    def __str__(self):
        return self.display_name


class Province(models.Model):
    name = models.CharField(max_length=100, unique=True)
    population_online = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name


class Regency(models.Model):
    province = models.ForeignKey(Province, on_delete=models.CASCADE, related_name="regencies")
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "regencies"
        unique_together = ("province", "name")

    def __str__(self):
        return f"{self.name}, {self.province.name}"


class AnalystProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="analyst_profile"
    )
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="analysts")
    role_label = models.CharField(max_length=100, default="Analis Humas")
    has_political_monitoring_permission = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.role_label})"
```

- [ ] **Step 4: Generate and apply the migration**

Run:
```bash
python manage.py makemigrations core
python manage.py migrate
```
Expected: `apps/core/migrations/0001_initial.py` created; migration applies cleanly.

- [ ] **Step 5: Register admin**

`apps/core/admin.py`:
```python
from django.contrib import admin

from .models import AnalystProfile, Platform, Province, Regency, Project, Tenant

admin.site.register(Tenant)
admin.site.register(Project)
admin.site.register(Platform)
admin.site.register(Province)
admin.site.register(Regency)
admin.site.register(AnalystProfile)
```

- [ ] **Step 6: Run the test, verify it passes**

Run: `python manage.py test apps.core.tests.test_models -v 2`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add apps/core/models.py apps/core/admin.py apps/core/migrations apps/core/tests/test_models.py
git commit -m "Add core reference-data models: Tenant, Project, Platform, Province, Regency, AnalystProfile"
```

---

### Task 3: Demo-auth middleware, tenant context processor, core seed, and `get_active_project` selector

**Files:**
- Modify: `apps/core/middleware.py`
- Modify: `apps/core/context_processors.py`
- Create: `apps/core/seed.py`
- Create: `apps/core/selectors.py`
- Test: `apps/core/tests/test_middleware.py`
- Test: `apps/core/tests/test_seed.py`
- Test: `apps/core/tests/test_selectors.py`

**Interfaces:**
- Consumes: `apps.core.models.{Tenant,Project,Platform,Province,Regency,AnalystProfile}` (Task 2).
- Produces: `apps.core.seed.seed_core() -> (Tenant, Project)` and `apps.core.seed.DEMO_USERNAME = "dewi.anjani"`; `apps.core.selectors.get_active_project(request) -> Project | None`. Every later app's views call `get_active_project(request)` to scope queries to the demo tenant's project.

- [ ] **Step 1: Write the failing tests**

`apps/core/tests/test_seed.py`:
```python
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.core.models import AnalystProfile, Platform, Province, Regency
from apps.core.seed import seed_core


class SeedCoreTest(TestCase):
    def test_seed_core_creates_reference_data(self):
        tenant, project = seed_core()
        self.assertEqual(tenant.name, "Kemenko PMK")
        self.assertEqual(project.tenant, tenant)
        self.assertEqual(Platform.objects.count(), 7)
        self.assertGreaterEqual(Province.objects.count(), 10)
        self.assertTrue(Regency.objects.filter(province__name="Maluku").exists())
        demo_user = get_user_model().objects.get(username="dewi.anjani")
        profile = AnalystProfile.objects.get(user=demo_user)
        self.assertTrue(profile.has_political_monitoring_permission)

    def test_seed_core_is_idempotent(self):
        seed_core()
        seed_core()
        self.assertEqual(Platform.objects.count(), 7)
```

`apps/core/tests/test_middleware.py`:
```python
from django.test import TestCase

from apps.core.seed import seed_core


class DemoUserMiddlewareTest(TestCase):
    def test_requests_are_auto_authenticated_as_demo_user(self):
        seed_core()
        response = self.client.get("/admin/")
        self.assertEqual(response.wsgi_request.user.username, "dewi.anjani")
```

`apps/core/tests/test_selectors.py`:
```python
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from apps.core.seed import seed_core
from apps.core.selectors import get_active_project


class GetActiveProjectTest(TestCase):
    def test_returns_none_for_anonymous_user(self):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        self.assertIsNone(get_active_project(request))

    def test_returns_project_for_demo_user(self):
        tenant, project = seed_core()
        demo_user = get_user_model().objects.get(username="dewi.anjani")
        request = RequestFactory().get("/")
        request.user = demo_user
        self.assertEqual(get_active_project(request), project)
```

- [ ] **Step 2: Run the tests, verify they fail**

Run: `python manage.py test apps.core.tests.test_seed apps.core.tests.test_middleware apps.core.tests.test_selectors -v 2`
Expected: FAIL — `ImportError: cannot import name 'seed_core'` / `get_active_project`

- [ ] **Step 3: Write `apps/core/seed.py`**

```python
from django.contrib.auth import get_user_model

from .models import AnalystProfile, Platform, Province, Regency, Project, Tenant

DEMO_USERNAME = "dewi.anjani"

PLATFORMS = [
    ("x", "X (Twitter)", "#0B1F33", Platform.METHOD_INTERNAL),
    ("instagram", "Instagram", "#DD2A7B", Platform.METHOD_APIFY),
    ("tiktok", "TikTok", "#0B1F33", Platform.METHOD_APIFY),
    ("youtube", "YouTube", "#FF0000", Platform.METHOD_APIFY),
    ("facebook", "Facebook", "#0866FF", Platform.METHOD_APIFY),
    ("berita", "Berita Daring", "#0E7C86", Platform.METHOD_INTERNAL),
    ("forum", "Forum/Blog", "#7C8A99", Platform.METHOD_INTERNAL),
]

PROVINCES = [
    ("DKI Jakarta", 9_000_000),
    ("Jawa Barat", 11_000_000),
    ("Jawa Tengah", 8_500_000),
    ("Jawa Timur", 9_800_000),
    ("Banten", 3_200_000),
    ("Sumatera Utara", 3_600_000),
    ("Sulawesi Selatan", 2_500_000),
    ("Kalimantan Timur", 1_900_000),
    ("Maluku", 420_000),
    ("Papua", 690_000),
    ("Sulawesi Tengah", 780_000),
    ("Nusa Tenggara Timur", 810_000),
]

REGENCIES = {
    "Maluku": ["Kota Ambon", "Maluku Tengah", "Kota Tual", "Buru", "Seram Bagian Barat"],
    "Papua": ["Kota Jayapura", "Jayapura", "Mimika", "Nabire"],
}


def seed_core():
    tenant, _ = Tenant.objects.get_or_create(name="Kemenko PMK")
    project, _ = Project.objects.get_or_create(tenant=tenant, name="Program Pangan Rakyat")

    for slug, display_name, brand_color, method in PLATFORMS:
        Platform.objects.get_or_create(
            slug=slug,
            defaults={"display_name": display_name, "brand_color": brand_color, "method": method},
        )

    for name, population_online in PROVINCES:
        province, _ = Province.objects.get_or_create(
            name=name, defaults={"population_online": population_online}
        )
        for regency_name in REGENCIES.get(name, []):
            Regency.objects.get_or_create(province=province, name=regency_name)

    User = get_user_model()
    demo_user, _ = User.objects.get_or_create(
        username=DEMO_USERNAME,
        defaults={"first_name": "Dewi", "last_name": "Anjani", "is_staff": True},
    )
    AnalystProfile.objects.get_or_create(
        user=demo_user,
        defaults={
            "tenant": tenant,
            "role_label": "Analis Humas",
            "has_political_monitoring_permission": True,
        },
    )
    return tenant, project
```

- [ ] **Step 4: Write `apps/core/selectors.py`**

```python
from .models import AnalystProfile


def get_active_project(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return None
    profile = AnalystProfile.objects.select_related("tenant").filter(user=user).first()
    if profile is None:
        return None
    return profile.tenant.projects.first()
```

- [ ] **Step 5: Implement the real middleware**

`apps/core/middleware.py`:
```python
from django.contrib.auth import get_user_model, login
from django.contrib.auth.models import AnonymousUser

from .seed import DEMO_USERNAME


class DemoUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if isinstance(request.user, AnonymousUser):
            User = get_user_model()
            demo_user = User.objects.filter(username=DEMO_USERNAME).first()
            if demo_user is not None:
                request.user = demo_user
                login(request, demo_user, backend="django.contrib.auth.backends.ModelBackend")
        return self.get_response(request)
```

- [ ] **Step 6: Implement the real context processor**

`apps/core/context_processors.py`:
```python
from .models import AnalystProfile


def tenant_context(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"instansi": "", "proyek": "", "analyst_profile": None}
    profile = AnalystProfile.objects.select_related("tenant").filter(user=user).first()
    if profile is None:
        return {"instansi": "", "proyek": "", "analyst_profile": None}
    project = profile.tenant.projects.first()
    return {
        "instansi": profile.tenant.name,
        "proyek": project.name if project else "",
        "analyst_profile": profile,
    }
```

- [ ] **Step 7: Run the tests, verify they pass**

Run: `python manage.py test apps.core.tests.test_seed apps.core.tests.test_middleware apps.core.tests.test_selectors -v 2`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add apps/core/seed.py apps/core/selectors.py apps/core/middleware.py apps/core/context_processors.py apps/core/tests
git commit -m "Add demo-auth middleware, tenant context processor, core seed, and get_active_project selector"
```

---

### Task 4: Base templates, shared CSS, and placeholder routes for all 7 screens

Every sidebar link must resolve from this task onward, even though most views are still placeholders — later tasks replace each placeholder view body in place without touching `urls.py` again.

**Files:**
- Create: `apps/analytics/views.py`, `apps/analytics/urls.py`
- Create: `apps/coordination/views.py`, `apps/coordination/urls.py`
- Create: `apps/governance/views.py`, `apps/governance/urls.py`
- Modify: `pantau/urls.py`
- Create: `templates/core/base_dashboard.html`, `templates/core/base_warroom.html`, `templates/core/_sidebar.html`, `templates/core/_topbar.html`
- Create: `static/core/css/base.css`
- Test: `apps/core/tests/test_navigation.py`

**Interfaces:**
- Produces: named URLs `analytics:ringkasan`, `analytics:war_room`, `analytics:narasi`, `analytics:regional`, `coordination:koordinasi`, `governance:konfigurasi`, `governance:pengawasan` — every later task reuses these names, never renames them.
- Produces: template blocks `content` and `topbar_actions` on `core/base_dashboard.html`; `content` on `core/base_warroom.html`.

- [ ] **Step 1: Write the failing test**

`apps/core/tests/test_navigation.py`:
```python
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase

from apps.core.seed import seed_core


class NavigationSmokeTest(TestCase):
    def test_sidebar_and_topbar_render_without_error(self):
        request = RequestFactory().get("/ringkasan/")
        html = render_to_string(
            "core/_sidebar.html", {"active_nav": "ringkasan"}, request=request
        )
        self.assertIn("PANTAU", html)
        self.assertIn("Ringkasan", html)

        topbar_html = render_to_string(
            "core/_topbar.html",
            {"instansi": "Kemenko PMK", "proyek": "Program Pangan Rakyat"},
            request=request,
        )
        self.assertIn("Kemenko PMK", topbar_html)

    def test_root_redirects_to_ringkasan(self):
        seed_core()
        response = self.client.get("/")
        self.assertRedirects(response, "/ringkasan/", fetch_redirect_response=False)

    def test_all_screen_routes_resolve(self):
        seed_core()
        for path in [
            "/ringkasan/", "/war-room/", "/narasi/", "/regional/",
            "/koordinasi/", "/konfigurasi/", "/pengawasan/",
        ]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
```

- [ ] **Step 2: Run the test, verify it fails**

Run: `python manage.py test apps.core.tests.test_navigation -v 2`
Expected: FAIL — `TemplateDoesNotExist: core/_sidebar.html`

- [ ] **Step 3: Create placeholder views and urls for `analytics`**

`apps/analytics/views.py`:
```python
from django.http import HttpResponse


def ringkasan(request):
    return HttpResponse("Ringkasan — coming soon")


def war_room(request):
    return HttpResponse("War Room — coming soon")


def narasi(request):
    return HttpResponse("Perbandingan Narasi — coming soon")


def regional(request):
    return HttpResponse("Regional — coming soon")
```

`apps/analytics/urls.py`:
```python
from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("ringkasan/", views.ringkasan, name="ringkasan"),
    path("war-room/", views.war_room, name="war_room"),
    path("narasi/", views.narasi, name="narasi"),
    path("regional/", views.regional, name="regional"),
]
```

- [ ] **Step 4: Create placeholder views and urls for `coordination`**

`apps/coordination/views.py`:
```python
from django.http import HttpResponse


def koordinasi(request):
    return HttpResponse("Deteksi Koordinasi — coming soon")
```

`apps/coordination/urls.py`:
```python
from django.urls import path

from . import views

app_name = "coordination"

urlpatterns = [
    path("koordinasi/", views.koordinasi, name="koordinasi"),
]
```

- [ ] **Step 5: Create placeholder views and urls for `governance`**

`apps/governance/views.py`:
```python
from django.http import HttpResponse


def konfigurasi(request):
    return HttpResponse("Konsol Konfigurasi — coming soon")


def pengawasan(request):
    return HttpResponse("Dasbor Pengawasan — coming soon")
```

`apps/governance/urls.py`:
```python
from django.urls import path

from . import views

app_name = "governance"

urlpatterns = [
    path("konfigurasi/", views.konfigurasi, name="konfigurasi"),
    path("pengawasan/", views.pengawasan, name="pengawasan"),
]
```

- [ ] **Step 6: Wire the root urlconf**

`pantau/urls.py` (replace the Task 1 version):
```python
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(pattern_name="analytics:ringkasan", permanent=False)),
    path("", include("apps.analytics.urls")),
    path("", include("apps.coordination.urls")),
    path("", include("apps.governance.urls")),
]
```

- [ ] **Step 7: Create the shared chrome templates**

`templates/core/base_dashboard.html`:
```html
{% load static %}
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{% static 'core/css/base.css' %}">
  <title>{% block title %}Ringkasan{% endblock %} — PANTAU</title>
</head>
<body>
  <div class="pantau-shell">
    {% include "core/_sidebar.html" %}
    <div class="pantau-main">
      {% include "core/_topbar.html" %}
      <div class="pantau-content">
        {% block content %}{% endblock %}
      </div>
    </div>
  </div>
</body>
</html>
```

`templates/core/_sidebar.html`:
```html
<div class="pantau-sidebar">
  <div class="pantau-brand">
    <div class="pantau-logo">P</div>
    <div>
      <div class="pantau-brand-name">PANTAU</div>
      <div class="pantau-brand-sub">NARASI &amp; OPINI</div>
    </div>
  </div>
  <nav class="pantau-nav">
    <a class="pantau-nav-item{% if active_nav == 'ringkasan' %} active{% endif %}" href="{% url 'analytics:ringkasan' %}">Ringkasan</a>
    <span class="pantau-nav-item disabled" title="Segera hadir">Umpan Sebutan</span>
    <span class="pantau-nav-item disabled" title="Segera hadir">Analitik AI</span>
    <a class="pantau-nav-item{% if active_nav == 'narasi' %} active{% endif %}" href="{% url 'analytics:narasi' %}">Narasi Politik</a>
    <a class="pantau-nav-item{% if active_nav == 'war_room' %} active{% endif %}" href="{% url 'analytics:war_room' %}">War Room</a>
    <a class="pantau-nav-item{% if active_nav == 'koordinasi' %} active{% endif %}" href="{% url 'coordination:koordinasi' %}">Deteksi Koordinasi</a>
    <a class="pantau-nav-item{% if active_nav == 'regional' %} active{% endif %}" href="{% url 'analytics:regional' %}">Regional</a>
    <span class="pantau-nav-item disabled" title="Segera hadir">Sosiograf</span>
    <span class="pantau-nav-item disabled" title="Segera hadir">Laporan</span>
  </nav>
  <div class="pantau-nav-footer">
    <a class="pantau-nav-item{% if active_nav == 'konfigurasi' %} active{% endif %}" href="{% url 'governance:konfigurasi' %}">Konfigurasi</a>
    <a class="pantau-nav-item{% if active_nav == 'pengawasan' %} active{% endif %}" href="{% url 'governance:pengawasan' %}">Pengawasan</a>
    {% if analyst_profile %}
    <div class="pantau-user">
      <div class="pantau-user-avatar">{{ analyst_profile.user.first_name|slice:":1" }}{{ analyst_profile.user.last_name|slice:":1" }}</div>
      <div>
        <div class="pantau-user-name">{{ analyst_profile.user.get_full_name }}</div>
        <div class="pantau-user-role">{{ analyst_profile.role_label }}</div>
      </div>
    </div>
    {% endif %}
  </div>
</div>
```

`templates/core/_topbar.html`:
```html
<div class="pantau-topbar">
  <div class="pantau-project-pill"><span class="dot"></span>{{ proyek }}</div>
  <div class="pantau-instansi">{{ instansi }}</div>
  <div class="pantau-topbar-actions">{% block topbar_actions %}{% endblock %}</div>
</div>
```

`templates/core/base_warroom.html` (standalone dark "kiosk" shell — no sidebar, per the design doc's own War Room layout):
```html
{% load static %}
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{% static 'core/css/base.css' %}">
  {% block extra_css %}{% endblock %}
  <meta http-equiv="refresh" content="60">
  <title>War Room — PANTAU</title>
</head>
<body class="pantau-warroom-body">
  {% block content %}{% endblock %}
</body>
</html>
```

- [ ] **Step 8: Create the shared stylesheet**

`static/core/css/base.css` — port the color system and card patterns common to every screen (ported from `docs/design/pantau/shared_style.css`, extended with layout classes for the sidebar/topbar chrome):
```css
:root {
  --navy: #0B1F33;
  --navy-2: #16283B;
  --teal: #0E7C86;
  --teal-light: #2FD4C4;
  --bg: #EBEEF1;
  --content-bg: #F3F5F7;
  --border: #E2E8EE;
  --text-muted: #64748B;
  --text-faint: #8A97A6;
  --positive: #178A5C;
  --negative: #C6483F;
  --neutral: #AEBBC7;
  --warning: #B07818;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--bg);
  font-family: 'IBM Plex Sans', system-ui, sans-serif;
  color: var(--navy-2);
}

a { color: var(--teal); text-decoration: none; }
a:hover { color: #0A5C64; text-decoration: underline; }

.pantau-shell {
  display: grid;
  grid-template-columns: 208px 1fr;
  min-height: 100vh;
}

.pantau-sidebar {
  background: var(--navy);
  display: flex;
  flex-direction: column;
}

.pantau-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 18px 18px;
  border-bottom: 1px solid rgba(255,255,255,.08);
}

.pantau-logo {
  width: 30px; height: 30px; border-radius: 8px;
  background: linear-gradient(135deg, var(--teal), var(--teal-light));
  display: grid; place-items: center;
  font: 700 13px Archivo, sans-serif; color: #fff;
}

.pantau-brand-name { font: 700 14px Archivo, sans-serif; color: #fff; letter-spacing: .04em; }
.pantau-brand-sub { font: 400 9px 'IBM Plex Mono', monospace; color: #5F7A93; letter-spacing: .04em; }

.pantau-nav { padding: 14px 10px; display: flex; flex-direction: column; gap: 2px; }
.pantau-nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px; border-radius: 7px;
  color: #8FA3B8; font: 500 12.5px 'IBM Plex Sans', sans-serif;
  cursor: pointer;
}
.pantau-nav-item.active { background: rgba(47,212,196,.14); color: var(--teal-light); font-weight: 600; }
.pantau-nav-item.disabled { opacity: .45; cursor: default; }
.pantau-nav-footer { margin-top: auto; padding: 14px 10px; border-top: 1px solid rgba(255,255,255,.08); display: flex; flex-direction: column; gap: 2px; }

.pantau-user { display: flex; align-items: center; gap: 10px; padding: 12px 10px 4px; }
.pantau-user-avatar {
  width: 28px; height: 28px; border-radius: 50%; background: #1E3A55;
  display: grid; place-items: center; font: 600 11px Archivo, sans-serif; color: #7FD1C8;
}
.pantau-user-name { font: 600 11.5px 'IBM Plex Sans', sans-serif; color: #D7E3F0; }
.pantau-user-role { font: 400 10px 'IBM Plex Sans', sans-serif; color: #5F7A93; }

.pantau-main { display: flex; flex-direction: column; background: var(--content-bg); }

.pantau-topbar {
  display: flex; align-items: center; gap: 14px;
  padding: 14px 24px; background: #fff; border-bottom: 1px solid var(--border);
}
.pantau-project-pill {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 12px; border: 1px solid var(--border); border-radius: 8px; background: #F8FAFB;
  font: 600 12.5px 'IBM Plex Sans', sans-serif; color: var(--navy-2);
}
.pantau-project-pill .dot { width: 8px; height: 8px; border-radius: 3px; background: var(--teal); }
.pantau-instansi { font: 400 11.5px 'IBM Plex Sans', sans-serif; color: var(--text-muted); }
.pantau-topbar-actions { margin-left: auto; display: flex; align-items: center; gap: 8px; }

.pantau-content { padding: 22px 24px; display: flex; flex-direction: column; gap: 16px; }

.pantau-card {
  background: #fff; border: 1px solid var(--border); border-radius: 10px; padding: 16px 18px;
}

.pantau-badge {
  display: inline-block; padding: 3px 9px; border-radius: 20px;
  font: 600 10.5px 'IBM Plex Sans', sans-serif;
}
.pantau-badge-positive { background: #EAF5F0; color: var(--positive); }
.pantau-badge-negative { background: #FBEDEC; color: var(--negative); }
.pantau-badge-warning { background: #FDF3E3; color: #9A6B14; }
.pantau-badge-neutral { background: #EEF2F5; color: var(--text-muted); }

.pantau-neutrality-notice {
  padding: 7px 24px; background: #FDFAF3; border-bottom: 1px solid #F0E4CC;
  font: 400 10.5px 'IBM Plex Sans', sans-serif; color: #8A7A52;
}

@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: .35; } }
```

- [ ] **Step 9: Run the test, verify it passes**

Run: `python manage.py test apps.core.tests.test_navigation -v 2`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add apps/analytics/views.py apps/analytics/urls.py apps/coordination/views.py apps/coordination/urls.py apps/governance/views.py apps/governance/urls.py pantau/urls.py templates static apps/core/tests/test_navigation.py
git commit -m "Add shared dashboard chrome, base templates, and placeholder routes for all 7 screens"
```

---

### Task 5: Analytics models — Mention, Coalition, PoliticalIssue, AlertRule, Alert

**Files:**
- Modify: `apps/analytics/models.py`
- Create: `apps/analytics/admin.py`
- Create: `apps/analytics/migrations/0001_initial.py` (via `makemigrations`)
- Create: `apps/analytics/tests/__init__.py`
- Test: `apps/analytics/tests/test_models.py`

**Interfaces:**
- Consumes: `apps.core.models.{Platform,Project,Province,Regency}` (Task 2).
- Produces: `apps.analytics.models.Mention` (fields: `project`, `platform`, `province`, `regency`, `author_handle`, `content_snippet`, `sentiment`, `emotion`, `posted_at`, `engagement_count`, `reach_estimate`, `is_political`, `coalition`, `issue`; constants `SENTIMENT_POSITIVE/NEUTRAL/NEGATIVE`, `EMOTION_TRUST/ANTICIPATION/JOY/ANGER/SADNESS`), `Coalition` (`name`, `slug`, `stance`, `color`; constants `STANCE_PETAHANA/PENANTANG`), `PoliticalIssue` (`title`, `status`, `opened_at`, `owner_label`; constants `STATUS_ACTIVE/CLOSED`), `AlertRule` (`name`, `condition_summary`, `channel`), `Alert` (`rule`, `issue`, `severity`, `title`, `detail`, `triggered_at`, `status`, ordered `-triggered_at`).

- [ ] **Step 1: Write the failing test**

`apps/analytics/tests/test_models.py`:
```python
from django.test import TestCase
from django.utils import timezone

from apps.core.models import Platform, Project, Tenant
from apps.analytics.models import Alert, AlertRule, Coalition, Mention, PoliticalIssue


class AnalyticsModelsTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Kemenko PMK")
        self.project = Project.objects.create(tenant=self.tenant, name="Program Pangan Rakyat")
        self.platform = Platform.objects.create(
            slug="x", display_name="X (Twitter)", method=Platform.METHOD_INTERNAL
        )

    def test_mention_str_and_defaults(self):
        mention = Mention.objects.create(
            project=self.project,
            platform=self.platform,
            author_handle="@warga_peduli21",
            content_snippet="Contoh sebutan",
            sentiment=Mention.SENTIMENT_NEGATIVE,
            emotion=Mention.EMOTION_ANGER,
            posted_at=timezone.now(),
        )
        self.assertIn("@warga_peduli21", str(mention))
        self.assertFalse(mention.is_political)

    def test_coalition_and_issue(self):
        coalition = Coalition.objects.create(
            name="Koalisi Nusantara Raya", slug="nusantara-raya",
            stance=Coalition.STANCE_PETAHANA, color="#4656C9",
        )
        issue = PoliticalIssue.objects.create(
            title="Distribusi Pangan Wilayah Timur", opened_at=timezone.now(),
            owner_label="Tim Respons Cepat",
        )
        mention = Mention.objects.create(
            project=self.project,
            platform=self.platform,
            author_handle="@gerakmaju_net",
            content_snippet="Isu politik",
            sentiment=Mention.SENTIMENT_NEUTRAL,
            emotion=Mention.EMOTION_TRUST,
            posted_at=timezone.now(),
            is_political=True,
            coalition=coalition,
            issue=issue,
        )
        self.assertEqual(mention.coalition, coalition)
        self.assertEqual(mention.issue, issue)

    def test_alert_ordering_is_most_recent_first(self):
        rule = AlertRule.objects.create(
            name="Rasio-Neg-3J", condition_summary="Negatif > 55% dalam 3 jam",
            channel=AlertRule.CHANNEL_WEBHOOK,
        )
        older = Alert.objects.create(
            rule=rule, severity=Alert.SEVERITY_WARNING, title="Lama", detail="...",
            triggered_at=timezone.now() - timezone.timedelta(hours=2),
        )
        newer = Alert.objects.create(
            rule=rule, severity=Alert.SEVERITY_CRITICAL, title="Baru", detail="...",
            triggered_at=timezone.now(),
        )
        self.assertEqual(list(Alert.objects.all()), [newer, older])
```

- [ ] **Step 2: Run the test, verify it fails**

Run: `python manage.py test apps.analytics.tests.test_models -v 2`
Expected: FAIL — `ImportError: cannot import name 'Mention'`

- [ ] **Step 3: Write the models**

`apps/analytics/models.py`:
```python
from django.db import models

from apps.core.models import Platform, Project, Province, Regency


class Coalition(models.Model):
    STANCE_PETAHANA = "petahana"
    STANCE_PENANTANG = "penantang"
    STANCE_CHOICES = [(STANCE_PETAHANA, "Petahana"), (STANCE_PENANTANG, "Penantang")]

    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    stance = models.CharField(max_length=20, choices=STANCE_CHOICES)
    color = models.CharField(max_length=7)

    def __str__(self):
        return self.name


class PoliticalIssue(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [(STATUS_ACTIVE, "Aktif"), (STATUS_CLOSED, "Ditutup")]

    title = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    opened_at = models.DateTimeField()
    owner_label = models.CharField(max_length=150)

    def __str__(self):
        return self.title


class Mention(models.Model):
    SENTIMENT_POSITIVE = "positive"
    SENTIMENT_NEUTRAL = "neutral"
    SENTIMENT_NEGATIVE = "negative"
    SENTIMENT_CHOICES = [
        (SENTIMENT_POSITIVE, "Positif"),
        (SENTIMENT_NEUTRAL, "Netral"),
        (SENTIMENT_NEGATIVE, "Negatif"),
    ]

    EMOTION_TRUST = "trust"
    EMOTION_ANTICIPATION = "anticipation"
    EMOTION_JOY = "joy"
    EMOTION_ANGER = "anger"
    EMOTION_SADNESS = "sadness"
    EMOTION_CHOICES = [
        (EMOTION_TRUST, "Kepercayaan"),
        (EMOTION_ANTICIPATION, "Antisipasi"),
        (EMOTION_JOY, "Kegembiraan"),
        (EMOTION_ANGER, "Kemarahan"),
        (EMOTION_SADNESS, "Kesedihan"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="mentions")
    platform = models.ForeignKey(Platform, on_delete=models.PROTECT, related_name="mentions")
    province = models.ForeignKey(
        Province, on_delete=models.SET_NULL, null=True, blank=True, related_name="mentions"
    )
    regency = models.ForeignKey(
        Regency, on_delete=models.SET_NULL, null=True, blank=True, related_name="mentions"
    )
    author_handle = models.CharField(max_length=150)
    content_snippet = models.TextField()
    sentiment = models.CharField(max_length=20, choices=SENTIMENT_CHOICES)
    emotion = models.CharField(max_length=20, choices=EMOTION_CHOICES)
    posted_at = models.DateTimeField()
    engagement_count = models.PositiveIntegerField(default=0)
    reach_estimate = models.PositiveIntegerField(default=0)
    is_political = models.BooleanField(default=False)
    coalition = models.ForeignKey(
        Coalition, on_delete=models.SET_NULL, null=True, blank=True, related_name="mentions"
    )
    issue = models.ForeignKey(
        PoliticalIssue, on_delete=models.SET_NULL, null=True, blank=True, related_name="mentions"
    )

    class Meta:
        indexes = [
            models.Index(fields=["posted_at"]),
            models.Index(fields=["sentiment"]),
            models.Index(fields=["is_political"]),
        ]

    def __str__(self):
        return f"{self.author_handle} ({self.platform.slug}, {self.sentiment})"


class AlertRule(models.Model):
    CHANNEL_EMAIL = "email"
    CHANNEL_PUSH = "push"
    CHANNEL_WEBHOOK = "webhook"
    CHANNEL_CHOICES = [
        (CHANNEL_EMAIL, "Email"), (CHANNEL_PUSH, "Push"), (CHANNEL_WEBHOOK, "Webhook"),
    ]

    name = models.CharField(max_length=150)
    condition_summary = models.CharField(max_length=255)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)

    def __str__(self):
        return self.name


class Alert(models.Model):
    SEVERITY_INFO = "info"
    SEVERITY_WARNING = "warning"
    SEVERITY_CRITICAL = "critical"
    SEVERITY_CHOICES = [
        (SEVERITY_INFO, "Info"),
        (SEVERITY_WARNING, "Peringatan"),
        (SEVERITY_CRITICAL, "Kritis"),
    ]
    STATUS_ACTIVE = "active"
    STATUS_RESOLVED = "resolved"
    STATUS_CHOICES = [(STATUS_ACTIVE, "Aktif"), (STATUS_RESOLVED, "Teratasi")]

    rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name="alerts")
    issue = models.ForeignKey(
        PoliticalIssue, on_delete=models.SET_NULL, null=True, blank=True, related_name="alerts"
    )
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    title = models.CharField(max_length=255)
    detail = models.CharField(max_length=500)
    triggered_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)

    class Meta:
        ordering = ["-triggered_at"]

    def __str__(self):
        return self.title
```

- [ ] **Step 4: Generate and apply the migration**

Run:
```bash
python manage.py makemigrations analytics
python manage.py migrate
```

- [ ] **Step 5: Register admin**

`apps/analytics/admin.py`:
```python
from django.contrib import admin

from .models import Alert, AlertRule, Coalition, Mention, PoliticalIssue

admin.site.register(Coalition)
admin.site.register(PoliticalIssue)
admin.site.register(Mention)
admin.site.register(AlertRule)
admin.site.register(Alert)
```

- [ ] **Step 6: Run the test, verify it passes**

Run: `python manage.py test apps.analytics.tests.test_models -v 2`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add apps/analytics/models.py apps/analytics/admin.py apps/analytics/migrations apps/analytics/tests
git commit -m "Add analytics models: Mention, Coalition, PoliticalIssue, AlertRule, Alert"
```

---

### Task 6: Analytics seed data

**Files:**
- Create: `apps/analytics/seed.py`
- Test: `apps/analytics/tests/test_seed.py`

**Interfaces:**
- Consumes: `apps.core.seed.seed_core` (Task 3), `apps.analytics.models.*` (Task 5).
- Produces: `apps.analytics.seed.seed_analytics(project, mention_count=4000) -> None`. Idempotent — no-ops if `Mention` rows already exist for `project`. Always creates exactly one `PoliticalIssue` titled "Distribusi Pangan Wilayah Timur" with 2 `Coalition` rows and 1400 political `Mention` rows (700 per coalition) regardless of `mention_count`, plus 5 `Alert` rows.

- [ ] **Step 1: Write the failing test**

`apps/analytics/tests/test_seed.py`:
```python
from django.test import TestCase

from apps.core.seed import seed_core
from apps.analytics.models import Alert, Coalition, Mention, PoliticalIssue
from apps.analytics.seed import seed_analytics


class SeedAnalyticsTest(TestCase):
    def test_seed_analytics_creates_mentions_and_political_data(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=200)

        self.assertEqual(Mention.objects.filter(project=project).count(), 200 + 1400)
        self.assertTrue(Mention.objects.filter(is_political=True).exists())
        self.assertEqual(Coalition.objects.count(), 2)
        self.assertTrue(
            PoliticalIssue.objects.filter(title="Distribusi Pangan Wilayah Timur").exists()
        )
        self.assertEqual(Alert.objects.count(), 5)

    def test_seed_analytics_is_idempotent(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=200)
        seed_analytics(project, mention_count=200)
        self.assertEqual(Mention.objects.filter(project=project).count(), 200 + 1400)
```

- [ ] **Step 2: Run the test, verify it fails**

Run: `python manage.py test apps.analytics.tests.test_seed -v 2`
Expected: FAIL — `ImportError: cannot import name 'seed_analytics'`

- [ ] **Step 3: Write `apps/analytics/seed.py`**

```python
import random
from datetime import timedelta

from django.utils import timezone

from apps.core.models import Platform, Province

from .models import Alert, AlertRule, Coalition, Mention, PoliticalIssue

RNG_SEED = 20260710

PLATFORM_WEIGHTS = {
    "x": 0.34, "tiktok": 0.24, "instagram": 0.17, "berita": 0.13,
    "youtube": 0.06, "facebook": 0.04, "forum": 0.02,
}

SENTIMENT_WEIGHTS = [
    (Mention.SENTIMENT_POSITIVE, 0.46),
    (Mention.SENTIMENT_NEUTRAL, 0.33),
    (Mention.SENTIMENT_NEGATIVE, 0.21),
]
EMOTION_CHOICES = [c[0] for c in Mention.EMOTION_CHOICES]

SAMPLE_HANDLES = [
    "@warga_peduli21", "@nusantara_bgkt", "@kabarnusantara", "@suara_timur88",
    "@wartadesa_id", "@analisis_pangan", "@gerakmaju_net", "@ibu_rumahtangga",
    "@petani_muda", "@relawan_pangan",
]

SNIPPET_TEMPLATES = [
    "Program distribusi pangan tahap ini terasa membantu di lingkungan kami.",
    "Kapan bantuan sampai ke wilayah kami? Sudah ditunggu sejak minggu lalu.",
    "Terima kasih atas transparansi data yang dibagikan pemerintah.",
    "Ada laporan keterlambatan distribusi di beberapa titik.",
    "Testimoni penerima manfaat cukup positif di daerah kami.",
    "Perlu evaluasi lebih lanjut soal ketepatan sasaran program ini.",
]


def _weighted_choice(rng, weighted_options):
    total = sum(weight for _, weight in weighted_options)
    pick = rng.uniform(0, total)
    upto = 0
    for option, weight in weighted_options:
        upto += weight
        if pick <= upto:
            return option
    return weighted_options[-1][0]


def seed_analytics(project, mention_count=4000):
    if Mention.objects.filter(project=project).exists():
        return

    rng = random.Random(RNG_SEED)
    platforms = {p.slug: p for p in Platform.objects.all()}
    provinces = list(Province.objects.all())
    now = timezone.now()

    mentions = []
    for _ in range(mention_count):
        platform_slug = _weighted_choice(rng, list(PLATFORM_WEIGHTS.items()))
        sentiment = _weighted_choice(rng, SENTIMENT_WEIGHTS)
        province = rng.choice(provinces)
        regency = rng.choice(list(province.regencies.all())) if province.regencies.exists() else None
        posted_at = now - timedelta(days=rng.uniform(0, 30), hours=rng.uniform(0, 24))
        mentions.append(Mention(
            project=project,
            platform=platforms[platform_slug],
            province=province,
            regency=regency,
            author_handle=rng.choice(SAMPLE_HANDLES),
            content_snippet=rng.choice(SNIPPET_TEMPLATES),
            sentiment=sentiment,
            emotion=rng.choice(EMOTION_CHOICES),
            posted_at=posted_at,
            engagement_count=rng.randint(5, 4000),
            reach_estimate=rng.randint(200, 500000),
        ))
    Mention.objects.bulk_create(mentions)

    _seed_political_issue(project, rng, now)
    _seed_alerts(now)


def _seed_political_issue(project, rng, now):
    issue, _ = PoliticalIssue.objects.get_or_create(
        title="Distribusi Pangan Wilayah Timur",
        defaults={
            "status": PoliticalIssue.STATUS_ACTIVE,
            "opened_at": now - timedelta(days=16),
            "owner_label": "Tim Respons Cepat",
        },
    )
    coalition_a, _ = Coalition.objects.get_or_create(
        slug="nusantara-raya",
        defaults={
            "name": "Koalisi Nusantara Raya",
            "stance": Coalition.STANCE_PETAHANA,
            "color": "#4656C9",
        },
    )
    coalition_b, _ = Coalition.objects.get_or_create(
        slug="perubahan-bersatu",
        defaults={
            "name": "Koalisi Perubahan Bersatu",
            "stance": Coalition.STANCE_PENANTANG,
            "color": "#B07818",
        },
    )

    platforms = {p.slug: p for p in Platform.objects.all()}
    provinces = list(Province.objects.all())
    political_mentions = []
    coalition_sentiment_weights = (
        (coalition_a, [
            (Mention.SENTIMENT_POSITIVE, 0.58),
            (Mention.SENTIMENT_NEUTRAL, 0.29),
            (Mention.SENTIMENT_NEGATIVE, 0.13),
        ]),
        (coalition_b, [
            (Mention.SENTIMENT_POSITIVE, 0.21),
            (Mention.SENTIMENT_NEUTRAL, 0.33),
            (Mention.SENTIMENT_NEGATIVE, 0.46),
        ]),
    )
    for coalition, sentiment_weights in coalition_sentiment_weights:
        for _ in range(700):
            sentiment = _weighted_choice(rng, sentiment_weights)
            political_mentions.append(Mention(
                project=project,
                platform=platforms[_weighted_choice(rng, list(PLATFORM_WEIGHTS.items()))],
                province=rng.choice(provinces),
                author_handle=rng.choice(SAMPLE_HANDLES),
                content_snippet=rng.choice(SNIPPET_TEMPLATES),
                sentiment=sentiment,
                emotion=rng.choice(EMOTION_CHOICES),
                posted_at=now - timedelta(days=rng.uniform(0, 16), hours=rng.uniform(0, 24)),
                engagement_count=rng.randint(5, 4000),
                reach_estimate=rng.randint(200, 500000),
                is_political=True,
                coalition=coalition,
                issue=issue,
            ))
    Mention.objects.bulk_create(political_mentions)


def _seed_alerts(now):
    rule_spike, _ = AlertRule.objects.get_or_create(
        name="Rasio-Neg-3J",
        defaults={
            "condition_summary": "Volume negatif naik >150% dalam 3 jam",
            "channel": AlertRule.CHANNEL_WEBHOOK,
        },
    )
    rule_influencer, _ = AlertRule.objects.get_or_create(
        name="Akun-Berpengaruh",
        defaults={
            "condition_summary": "Sebutan dari akun >1 juta pengikut",
            "channel": AlertRule.CHANNEL_PUSH,
        },
    )
    issue = PoliticalIssue.objects.filter(title="Distribusi Pangan Wilayah Timur").first()

    Alert.objects.get_or_create(
        title="Lonjakan sentimen negatif — distribusi wilayah timur",
        defaults={
            "rule": rule_spike, "issue": issue, "severity": Alert.SEVERITY_CRITICAL,
            "detail": "Volume negatif +212% dalam 3 jam",
            "triggered_at": now - timedelta(hours=2), "status": Alert.STATUS_ACTIVE,
        },
    )
    Alert.objects.get_or_create(
        title="Sebutan dari akun berpengaruh tinggi",
        defaults={
            "rule": rule_influencer, "issue": issue, "severity": Alert.SEVERITY_WARNING,
            "detail": "@kabarnusantara (2,4 jt pengikut) mengunggah utas kritik",
            "triggered_at": now - timedelta(hours=4), "status": Alert.STATUS_ACTIVE,
        },
    )
    Alert.objects.get_or_create(
        title="Ambang volume harian tercapai — teratasi",
        defaults={
            "rule": rule_spike, "issue": None, "severity": Alert.SEVERITY_INFO,
            "detail": "Dikonfirmasi analis, dikirim ke webhook CRM",
            "triggered_at": now - timedelta(days=1), "status": Alert.STATUS_RESOLVED,
        },
    )
    Alert.objects.get_or_create(
        title="Klaster amplifikasi baru terdeteksi",
        defaults={
            "rule": rule_spike, "issue": issue, "severity": Alert.SEVERITY_WARNING,
            "detail": "Klaster-09 melewati ambang skor koordinasi 0,75",
            "triggered_at": now - timedelta(hours=30), "status": Alert.STATUS_ACTIVE,
        },
    )
    Alert.objects.get_or_create(
        title="Sentimen positif melampaui rata-rata mingguan",
        defaults={
            "rule": rule_spike, "issue": None, "severity": Alert.SEVERITY_INFO,
            "detail": "Testimoni penerima manfaat tahap 2 mendominasi linimasa",
            "triggered_at": now - timedelta(days=2), "status": Alert.STATUS_RESOLVED,
        },
    )
```

- [ ] **Step 4: Run the test, verify it passes**

Run: `python manage.py test apps.analytics.tests.test_seed -v 2`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/analytics/seed.py apps/analytics/tests/test_seed.py
git commit -m "Add analytics seed data: mentions, political issue, coalitions, alerts"
```

---

### Task 7: Governance models — platform config + oversight/audit

Built before `coordination`'s review actions (Task 15) and before `analytics`'s War Room (Task 12), both of which depend on `AuditLogEntry`/cluster status — no, War Room depends on `coordination` models, not governance; `coordination`'s review actions depend on `AuditLogEntry` here.

**Files:**
- Modify: `apps/governance/models.py`
- Create: `apps/governance/admin.py`
- Create: `apps/governance/services.py`
- Create: `apps/governance/migrations/0001_initial.py` (via `makemigrations`)
- Create: `apps/governance/tests/__init__.py`
- Test: `apps/governance/tests/test_models.py`

**Interfaces:**
- Consumes: `apps.core.models.{Platform,Tenant}` (Task 2), `django.contrib.auth` `User`.
- Produces: `apps.governance.models.PlatformIntegration`, `ApifyCredential`, `MonitoredDomain` (constants `STATUS_ACTIVE/NEEDS_REVIEW/INACTIVE`), `PoliticalMonitoringPermission`, `AuditLogEntry` (ordered `-timestamp`), `PolicyAcknowledgment`. Produces `apps.governance.services.record_audit_entry(actor_label, action, target) -> AuditLogEntry` — the only way any app should write an audit entry (used by `coordination`'s review actions in Task 15).

- [ ] **Step 1: Write the failing test**

`apps/governance/tests/test_models.py`:
```python
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.core.models import Platform, Tenant
from apps.governance.models import (
    AuditLogEntry, MonitoredDomain, PlatformIntegration,
    PoliticalMonitoringPermission, PolicyAcknowledgment,
)


class GovernanceModelsTest(TestCase):
    def test_platform_integration_str(self):
        platform = Platform.objects.create(
            slug="facebook", display_name="Facebook", method=Platform.METHOD_APIFY
        )
        integration = PlatformIntegration.objects.create(
            platform=platform, method=PlatformIntegration.METHOD_APIFY, is_active=False
        )
        self.assertIn("nonaktif", str(integration))

    def test_monitored_domain_default_status(self):
        domain = MonitoredDomain.objects.create(domain="kompas.com", adapter="generik-berita")
        self.assertEqual(domain.status, MonitoredDomain.STATUS_ACTIVE)

    def test_audit_log_orders_most_recent_first(self):
        first = AuditLogEntry.objects.create(actor_label="Sistem", action="A", target="X")
        second = AuditLogEntry.objects.create(actor_label="Sistem", action="B", target="Y")
        self.assertEqual(list(AuditLogEntry.objects.all()), [second, first])

    def test_policy_acknowledgment(self):
        tenant = Tenant.objects.create(name="Kemenko PMK")
        ack = PolicyAcknowledgment.objects.create(
            tenant=tenant, approved_by="Tenant Admin",
            approved_at=timezone.now(), next_review_at=timezone.now() + timezone.timedelta(days=365),
        )
        self.assertEqual(ack.tenant, tenant)

    def test_political_monitoring_permission(self):
        user = get_user_model().objects.create_user(username="siti.rahmawati")
        permission = PoliticalMonitoringPermission.objects.create(
            user=user, approved_by="R. Hartono (Kepatuhan)", approved_at=timezone.now(),
        )
        self.assertTrue(permission.active)
```

- [ ] **Step 2: Run the test, verify it fails**

Run: `python manage.py test apps.governance.tests.test_models -v 2`
Expected: FAIL — `ImportError: cannot import name 'PlatformIntegration'`

- [ ] **Step 3: Write the models**

`apps/governance/models.py`:
```python
from django.conf import settings
from django.db import models

from apps.core.models import Platform, Tenant


class PlatformIntegration(models.Model):
    METHOD_APIFY = "apify"
    METHOD_INTERNAL = "internal"
    METHOD_CHOICES = [(METHOD_APIFY, "Apify"), (METHOD_INTERNAL, "Internal")]

    platform = models.OneToOneField(Platform, on_delete=models.CASCADE, related_name="integration")
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    actor_id = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    status_note = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.platform.display_name} ({'aktif' if self.is_active else 'nonaktif'})"


class ApifyCredential(models.Model):
    masked_token = models.CharField(max_length=100)
    last_verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.masked_token


class MonitoredDomain(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_NEEDS_REVIEW = "needs_review"
    STATUS_INACTIVE = "inactive"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Aktif"),
        (STATUS_NEEDS_REVIEW, "Perlu tinjauan"),
        (STATUS_INACTIVE, "Nonaktif"),
    ]

    domain = models.CharField(max_length=200, unique=True)
    adapter = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    last_tested_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.domain


class PoliticalMonitoringPermission(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="political_monitoring_permissions",
    )
    approved_by = models.CharField(max_length=150)
    approved_at = models.DateTimeField()
    active = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} — {'aktif' if self.active else 'dicabut'}"


class AuditLogEntry(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    actor_label = models.CharField(max_length=150)
    action = models.CharField(max_length=255)
    target = models.CharField(max_length=150)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.actor_label}: {self.action}"


class PolicyAcknowledgment(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="policy_acknowledgments")
    approved_by = models.CharField(max_length=150)
    approved_at = models.DateTimeField()
    next_review_at = models.DateTimeField()

    def __str__(self):
        return f"{self.tenant} — {self.approved_at:%Y-%m-%d}"
```

- [ ] **Step 4: Generate and apply the migration**

Run:
```bash
python manage.py makemigrations governance
python manage.py migrate
```

- [ ] **Step 5: Register admin and write the audit-entry service**

`apps/governance/admin.py`:
```python
from django.contrib import admin

from .models import (
    ApifyCredential, AuditLogEntry, MonitoredDomain, PlatformIntegration,
    PoliticalMonitoringPermission, PolicyAcknowledgment,
)

admin.site.register(PlatformIntegration)
admin.site.register(ApifyCredential)
admin.site.register(MonitoredDomain)
admin.site.register(PoliticalMonitoringPermission)
admin.site.register(AuditLogEntry)
admin.site.register(PolicyAcknowledgment)
```

`apps/governance/services.py`:
```python
from .models import AuditLogEntry


def record_audit_entry(actor_label, action, target):
    return AuditLogEntry.objects.create(actor_label=actor_label, action=action, target=target)
```

- [ ] **Step 6: Run the test, verify it passes**

Run: `python manage.py test apps.governance.tests.test_models -v 2`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add apps/governance/models.py apps/governance/admin.py apps/governance/services.py apps/governance/migrations apps/governance/tests
git commit -m "Add governance models: PlatformIntegration, ApifyCredential, MonitoredDomain, PoliticalMonitoringPermission, AuditLogEntry, PolicyAcknowledgment"
```

---

### Task 8: Governance seed data

**Files:**
- Create: `apps/governance/seed.py`
- Test: `apps/governance/tests/test_seed.py`

**Interfaces:**
- Consumes: `apps.core.seed.seed_core` (Task 3), `apps.governance.models.*` (Task 7).
- Produces: `apps.governance.seed.seed_governance(tenant) -> None`. Idempotent — no-ops if any `PlatformIntegration` rows already exist. Creates one `PlatformIntegration` per social-media `Platform` — X, Instagram, TikTok, YouTube, Facebook; the `berita`/`forum` platforms are web-scraping sources handled by `MonitoredDomain` instead, matching the design doc's screen 1f which shows only 5 rows in "Platform Terpantau" — (Facebook inactive with a deprecation note, all others active), one `ApifyCredential`, 4 `MonitoredDomain` rows, 3 `PoliticalMonitoringPermission` rows (including the demo user), 10 `AuditLogEntry` rows (2 of which record auto-rejected individual profiles — read by the Pengawasan KPI in Task 17), and 1 `PolicyAcknowledgment`.

- [ ] **Step 1: Write the failing test**

`apps/governance/tests/test_seed.py`:
```python
from django.test import TestCase

from apps.core.seed import seed_core
from apps.governance.models import (
    AuditLogEntry, MonitoredDomain, PlatformIntegration, PoliticalMonitoringPermission,
)
from apps.governance.seed import seed_governance


class SeedGovernanceTest(TestCase):
    def test_seed_governance_creates_expected_rows(self):
        tenant, project = seed_core()
        seed_governance(tenant)

        self.assertEqual(PlatformIntegration.objects.count(), 5)
        self.assertFalse(PlatformIntegration.objects.get(platform__slug="facebook").is_active)
        self.assertEqual(MonitoredDomain.objects.count(), 4)
        self.assertGreaterEqual(
            PoliticalMonitoringPermission.objects.filter(active=True).count(), 3
        )
        self.assertEqual(AuditLogEntry.objects.count(), 10)
        self.assertEqual(
            AuditLogEntry.objects.filter(action__icontains="dikecualikan").count(), 2
        )

    def test_seed_governance_is_idempotent(self):
        tenant, project = seed_core()
        seed_governance(tenant)
        seed_governance(tenant)
        self.assertEqual(PlatformIntegration.objects.count(), 5)
```

- [ ] **Step 2: Run the test, verify it fails**

Run: `python manage.py test apps.governance.tests.test_seed -v 2`
Expected: FAIL — `ImportError: cannot import name 'seed_governance'`

- [ ] **Step 3: Write `apps/governance/seed.py`**

```python
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.models import Platform

from .models import (
    ApifyCredential, AuditLogEntry, MonitoredDomain, PlatformIntegration,
    PoliticalMonitoringPermission, PolicyAcknowledgment,
)

DOMAINS = [
    ("kompas.com", "generik-berita", MonitoredDomain.STATUS_ACTIVE),
    ("detik.com", "generik-berita", MonitoredDomain.STATUS_ACTIVE),
    ("forum.kaskus.co.id", "adapter khusus", MonitoredDomain.STATUS_NEEDS_REVIEW),
    ("tribunnews.com", "generik-berita", MonitoredDomain.STATUS_INACTIVE),
]

PERMISSION_USERS = [
    ("bagus.prakoso", "Bagus Prakoso"),
    ("siti.rahmawati", "Siti Rahmawati"),
]

AUDIT_ENTRIES = [
    ("D. Anjani", "Ekspor brief perbandingan narasi", "Isu #PGN-118"),
    ("B. Prakoso", "Kueri tren aktor politik", "Koalisi Nusantara Raya"),
    ("Sistem", "Klaster koordinasi ditandai untuk tinjauan", "Klaster-07"),
    ("R. Hartono", "Menyetujui izin Pemantauan Politik", "S. Rahmawati"),
    ("D. Anjani", "Mencatat aksi War Room", "Distribusi Pangan Timur"),
    ("Sistem", "Profil individu dikecualikan dari penandaan aktor otomatis", "@warga_pribadi_01"),
    ("Sistem", "Profil individu dikecualikan dari penandaan aktor otomatis", "@akun_pribadi_44"),
    ("B. Prakoso", "Kueri sebaran regional isu politik", "Maluku"),
    ("S. Rahmawati", "Ekspor log audit", "7 hari terakhir"),
    ("R. Hartono", "Menyetujui izin Pemantauan Politik", "B. Prakoso"),
]

ACTOR_IDS = {
    "instagram": "apify/instagram-scraper",
    "tiktok": "clockworks/tiktok-scraper",
    "youtube": "streamers/youtube-scraper",
    "facebook": "apify/facebook-posts-scraper",
    "x": "scraper internal v2.4.1",
}


def seed_governance(tenant):
    if PlatformIntegration.objects.exists():
        return

    now = timezone.now()
    social_platforms = Platform.objects.exclude(slug__in=["berita", "forum"])
    for platform in social_platforms:
        PlatformIntegration.objects.get_or_create(
            platform=platform,
            defaults={
                "method": platform.method,
                "actor_id": ACTOR_IDS.get(platform.slug, ""),
                "is_active": platform.slug != "facebook",
                "status_note": "deprecation notice" if platform.slug == "facebook" else "",
            },
        )

    ApifyCredential.objects.get_or_create(
        masked_token="apify_••••••••••••••••••3f9a",
        defaults={"last_verified_at": now - timezone.timedelta(hours=2)},
    )

    for domain, adapter, status in DOMAINS:
        MonitoredDomain.objects.get_or_create(
            domain=domain,
            defaults={
                "adapter": adapter, "status": status,
                "last_tested_at": now - timezone.timedelta(hours=2),
            },
        )

    User = get_user_model()
    demo_user = User.objects.filter(username="dewi.anjani").first()
    if demo_user is not None:
        PoliticalMonitoringPermission.objects.get_or_create(
            user=demo_user,
            defaults={"approved_by": "R. Hartono (Kepatuhan)", "approved_at": now - timezone.timedelta(days=120)},
        )
    for username, first_name in PERMISSION_USERS:
        user, _ = User.objects.get_or_create(username=username, defaults={"first_name": first_name})
        PoliticalMonitoringPermission.objects.get_or_create(
            user=user,
            defaults={"approved_by": "R. Hartono (Kepatuhan)", "approved_at": now - timezone.timedelta(days=90)},
        )

    for actor_label, action, target in AUDIT_ENTRIES:
        AuditLogEntry.objects.create(actor_label=actor_label, action=action, target=target)

    PolicyAcknowledgment.objects.get_or_create(
        tenant=tenant,
        defaults={
            "approved_by": "Tenant Admin",
            "approved_at": now - timezone.timedelta(days=190),
            "next_review_at": now + timezone.timedelta(days=175),
        },
    )
```

- [ ] **Step 4: Run the test, verify it passes**

Run: `python manage.py test apps.governance.tests.test_seed -v 2`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/governance/seed.py apps/governance/tests/test_seed.py
git commit -m "Add governance seed data: integrations, credentials, domains, permissions, audit log"
```

---

### Task 9: Coordination models — cluster detection

**Files:**
- Modify: `apps/coordination/models.py`
- Create: `apps/coordination/admin.py`
- Create: `apps/coordination/migrations/0001_initial.py` (via `makemigrations`)
- Create: `apps/coordination/tests/__init__.py`
- Test: `apps/coordination/tests/test_models.py`

**Interfaces:**
- Consumes: `apps.analytics.models.PoliticalIssue` (Task 5).
- Produces: `apps.coordination.models.CoordinationCluster` (fields: `issue`, `cluster_code` unique, `score`, `status`, `account_count`, `detected_at`, `note`; constants `STATUS_FLAGGED/REVIEWED_ORGANIC/IGNORED`; ordered `-score`), `ClusterAccount` (`cluster`, `handle`, `role`, `reach`, `post_count`; constants `ROLE_HUB/AMPLIFIER/SATELLITE`), `CoordinationSignal` (`cluster`, `signal_type`, `score`; constants `SIGNAL_TEXT_SIMILARITY/TIME_SYNC/ACCOUNT_AGE/SHARED_MEDIA`), `DuplicateTextSample` (`cluster`, `account_handle`, `posted_at`, `text`, `highlighted_phrase`). Reverse relations: `cluster.accounts`, `cluster.signals`, `cluster.duplicate_samples`.

- [ ] **Step 1: Write the failing test**

`apps/coordination/tests/test_models.py`:
```python
from django.test import TestCase
from django.utils import timezone

from apps.analytics.models import PoliticalIssue
from apps.coordination.models import (
    ClusterAccount, CoordinationCluster, CoordinationSignal, DuplicateTextSample,
)


class CoordinationModelsTest(TestCase):
    def setUp(self):
        self.issue = PoliticalIssue.objects.create(
            title="Distribusi Pangan Wilayah Timur", opened_at=timezone.now(),
            owner_label="Tim Respons Cepat",
        )

    def test_cluster_ordering_by_score_desc(self):
        low = CoordinationCluster.objects.create(
            issue=self.issue, cluster_code="Klaster-03", score="0.68", detected_at=timezone.now(),
        )
        high = CoordinationCluster.objects.create(
            issue=self.issue, cluster_code="Klaster-07", score="0.91", detected_at=timezone.now(),
        )
        self.assertEqual(list(CoordinationCluster.objects.all()), [high, low])

    def test_cluster_relations(self):
        cluster = CoordinationCluster.objects.create(
            issue=self.issue, cluster_code="Klaster-07", score="0.91",
            detected_at=timezone.now(), account_count=62,
        )
        ClusterAccount.objects.create(
            cluster=cluster, handle="@suara_timur88", role=ClusterAccount.ROLE_HUB,
            reach=640000, post_count=31,
        )
        CoordinationSignal.objects.create(
            cluster=cluster, signal_type=CoordinationSignal.SIGNAL_TIME_SYNC, score="0.91",
        )
        DuplicateTextSample.objects.create(
            cluster=cluster, account_handle="@suara_timur88", posted_at=timezone.now(),
            text="sample", highlighted_phrase="rakyat timur",
        )
        self.assertEqual(cluster.accounts.count(), 1)
        self.assertEqual(cluster.signals.count(), 1)
        self.assertEqual(cluster.duplicate_samples.count(), 1)
```

- [ ] **Step 2: Run the test, verify it fails**

Run: `python manage.py test apps.coordination.tests.test_models -v 2`
Expected: FAIL — `ImportError: cannot import name 'CoordinationCluster'`

- [ ] **Step 3: Write the models**

`apps/coordination/models.py`:
```python
from django.db import models

from apps.analytics.models import PoliticalIssue


class CoordinationCluster(models.Model):
    STATUS_FLAGGED = "flagged"
    STATUS_REVIEWED_ORGANIC = "reviewed_organic"
    STATUS_IGNORED = "ignored"
    STATUS_CHOICES = [
        (STATUS_FLAGGED, "Ditandai"),
        (STATUS_REVIEWED_ORGANIC, "Ditinjau — Organik"),
        (STATUS_IGNORED, "Diabaikan"),
    ]

    issue = models.ForeignKey(PoliticalIssue, on_delete=models.CASCADE, related_name="coordination_clusters")
    cluster_code = models.CharField(max_length=30, unique=True)
    score = models.DecimalField(max_digits=3, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_FLAGGED)
    account_count = models.PositiveIntegerField(default=0)
    detected_at = models.DateTimeField()
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-score"]

    def __str__(self):
        return self.cluster_code


class ClusterAccount(models.Model):
    ROLE_HUB = "hub"
    ROLE_AMPLIFIER = "amplifier"
    ROLE_SATELLITE = "satellite"
    ROLE_CHOICES = [
        (ROLE_HUB, "Pusat penyebaran"),
        (ROLE_AMPLIFIER, "Amplifier inti"),
        (ROLE_SATELLITE, "Akun satelit"),
    ]

    cluster = models.ForeignKey(CoordinationCluster, on_delete=models.CASCADE, related_name="accounts")
    handle = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    reach = models.PositiveIntegerField(default=0)
    post_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.handle


class CoordinationSignal(models.Model):
    SIGNAL_TEXT_SIMILARITY = "text_similarity"
    SIGNAL_TIME_SYNC = "time_sync"
    SIGNAL_ACCOUNT_AGE = "account_age"
    SIGNAL_SHARED_MEDIA = "shared_media"
    SIGNAL_CHOICES = [
        (SIGNAL_TEXT_SIMILARITY, "Teks nyaris identik"),
        (SIGNAL_TIME_SYNC, "Sinkronisasi waktu unggah"),
        (SIGNAL_ACCOUNT_AGE, "Akun baru / riwayat minim"),
        (SIGNAL_SHARED_MEDIA, "Aset media bersama"),
    ]

    cluster = models.ForeignKey(CoordinationCluster, on_delete=models.CASCADE, related_name="signals")
    signal_type = models.CharField(max_length=30, choices=SIGNAL_CHOICES)
    score = models.DecimalField(max_digits=3, decimal_places=2)

    def __str__(self):
        return f"{self.cluster.cluster_code} — {self.get_signal_type_display()}"


class DuplicateTextSample(models.Model):
    cluster = models.ForeignKey(CoordinationCluster, on_delete=models.CASCADE, related_name="duplicate_samples")
    account_handle = models.CharField(max_length=150)
    posted_at = models.DateTimeField()
    text = models.TextField()
    highlighted_phrase = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.account_handle} @ {self.posted_at:%H:%M}"
```

- [ ] **Step 4: Generate and apply the migration**

Run:
```bash
python manage.py makemigrations coordination
python manage.py migrate
```

- [ ] **Step 5: Register admin**

`apps/coordination/admin.py`:
```python
from django.contrib import admin

from .models import ClusterAccount, CoordinationCluster, CoordinationSignal, DuplicateTextSample


class ClusterAccountInline(admin.TabularInline):
    model = ClusterAccount
    extra = 0


class CoordinationSignalInline(admin.TabularInline):
    model = CoordinationSignal
    extra = 0


class DuplicateTextSampleInline(admin.TabularInline):
    model = DuplicateTextSample
    extra = 0


@admin.register(CoordinationCluster)
class CoordinationClusterAdmin(admin.ModelAdmin):
    list_display = ("cluster_code", "score", "status", "account_count")
    inlines = [ClusterAccountInline, CoordinationSignalInline, DuplicateTextSampleInline]
```

- [ ] **Step 6: Run the test, verify it passes**

Run: `python manage.py test apps.coordination.tests.test_models -v 2`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add apps/coordination/models.py apps/coordination/admin.py apps/coordination/migrations apps/coordination/tests
git commit -m "Add coordination models: CoordinationCluster, ClusterAccount, CoordinationSignal, DuplicateTextSample"
```

---

### Task 10: Coordination seed data

**Files:**
- Create: `apps/coordination/seed.py`
- Test: `apps/coordination/tests/test_seed.py`

**Interfaces:**
- Consumes: `apps.analytics.models.PoliticalIssue` (Task 5), `apps.coordination.models.*` (Task 9). Requires `apps.analytics.seed.seed_analytics` (Task 6) to have run first so the "Distribusi Pangan Wilayah Timur" issue exists — no-ops silently otherwise.
- Produces: `apps.coordination.seed.seed_coordination() -> None`. Idempotent — no-ops if any `CoordinationCluster` rows exist. Creates 4 clusters (Klaster-07 flagged score 0.91 with 3 accounts/4 signals/3 duplicate samples, Klaster-09 flagged score 0.79, Klaster-05 reviewed-organic score 0.76, Klaster-03 ignored score 0.68).

- [ ] **Step 1: Write the failing test**

`apps/coordination/tests/test_seed.py`:
```python
from django.test import TestCase

from apps.core.seed import seed_core
from apps.analytics.seed import seed_analytics
from apps.coordination.models import CoordinationCluster
from apps.coordination.seed import seed_coordination


class SeedCoordinationTest(TestCase):
    def test_seed_coordination_creates_clusters(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=100)
        seed_coordination()

        self.assertEqual(CoordinationCluster.objects.count(), 4)
        flagged = CoordinationCluster.objects.filter(status=CoordinationCluster.STATUS_FLAGGED)
        self.assertEqual(flagged.count(), 2)
        top = CoordinationCluster.objects.first()
        self.assertEqual(top.cluster_code, "Klaster-07")
        self.assertEqual(top.accounts.count(), 3)

    def test_seed_coordination_is_idempotent(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=100)
        seed_coordination()
        seed_coordination()
        self.assertEqual(CoordinationCluster.objects.count(), 4)

    def test_seed_coordination_noop_without_issue(self):
        seed_coordination()
        self.assertEqual(CoordinationCluster.objects.count(), 0)
```

- [ ] **Step 2: Run the test, verify it fails**

Run: `python manage.py test apps.coordination.tests.test_seed -v 2`
Expected: FAIL — `ImportError: cannot import name 'seed_coordination'`

- [ ] **Step 3: Write `apps/coordination/seed.py`**

```python
from django.utils import timezone

from apps.analytics.models import PoliticalIssue

from .models import ClusterAccount, CoordinationCluster, CoordinationSignal, DuplicateTextSample

CLUSTER_DEFS = [
    {
        "cluster_code": "Klaster-07", "score": "0.91", "status": CoordinationCluster.STATUS_FLAGGED,
        "account_count": 62, "note": "62 akun · isu distribusi pangan · aktif sejak 24 Jun",
        "accounts": [
            ("@suara_timur88", ClusterAccount.ROLE_HUB, 640000, 31),
            ("@nusantara_bgkt", ClusterAccount.ROLE_AMPLIFIER, 120000, 14),
            ("@warga_peduli21", ClusterAccount.ROLE_AMPLIFIER, 98000, 9),
        ],
        "signals": [
            (CoordinationSignal.SIGNAL_TEXT_SIMILARITY, "0.86"),
            (CoordinationSignal.SIGNAL_TIME_SYNC, "0.91"),
            (CoordinationSignal.SIGNAL_ACCOUNT_AGE, "0.62"),
            (CoordinationSignal.SIGNAL_SHARED_MEDIA, "0.74"),
        ],
        "samples": [
            ("@suara_timur88", "Bantuan tak kunjung sampai, rakyat timur kembali jadi penonton. Sampai kapan? #PanganUntukSiapa", "rakyat timur kembali jadi penonton"),
            ("@warga_peduli21", "Bantuan tidak kunjung sampai, rakyat timur kembali jadi penonton!! Sampai kapan #PanganUntukSiapa", "rakyat timur kembali jadi penonton"),
            ("@nusantara_bgkt", "bantuan tak kunjung sampai... rakyat timur kembali jadi penonton — sampai kapan? #PanganUntukSiapa", "rakyat timur kembali jadi penonton"),
        ],
    },
    {
        "cluster_code": "Klaster-09", "score": "0.79", "status": CoordinationCluster.STATUS_FLAGGED,
        "account_count": 28, "note": "28 akun · amplifikasi tagar #GantiSkema · sejak 27 Jun",
        "accounts": [("@gerakmaju_net", ClusterAccount.ROLE_HUB, 296000, 22)],
        "signals": [
            (CoordinationSignal.SIGNAL_TIME_SYNC, "0.79"),
            (CoordinationSignal.SIGNAL_TEXT_SIMILARITY, "0.71"),
        ],
        "samples": [],
    },
    {
        "cluster_code": "Klaster-05", "score": "0.76", "status": CoordinationCluster.STATUS_REVIEWED_ORGANIC,
        "account_count": 19, "note": "Komunitas relawan asli — diputuskan analis 28 Jun (false positive)",
        "accounts": [], "signals": [], "samples": [],
    },
    {
        "cluster_code": "Klaster-03", "score": "0.68", "status": CoordinationCluster.STATUS_IGNORED,
        "account_count": 11, "note": "Jaringan giveaway komersial — tidak relevan dgn isu politik",
        "accounts": [], "signals": [], "samples": [],
    },
]


def seed_coordination():
    if CoordinationCluster.objects.exists():
        return

    issue = PoliticalIssue.objects.filter(title="Distribusi Pangan Wilayah Timur").first()
    if issue is None:
        return

    now = timezone.now()
    for definition in CLUSTER_DEFS:
        cluster = CoordinationCluster.objects.create(
            issue=issue,
            cluster_code=definition["cluster_code"],
            score=definition["score"],
            status=definition["status"],
            account_count=definition["account_count"],
            detected_at=now - timezone.timedelta(days=6),
            note=definition["note"],
        )
        for handle, role, reach, post_count in definition["accounts"]:
            ClusterAccount.objects.create(
                cluster=cluster, handle=handle, role=role, reach=reach, post_count=post_count
            )
        for signal_type, score in definition["signals"]:
            CoordinationSignal.objects.create(cluster=cluster, signal_type=signal_type, score=score)
        for handle, text, phrase in definition["samples"]:
            DuplicateTextSample.objects.create(
                cluster=cluster, account_handle=handle,
                posted_at=now - timezone.timedelta(days=6, minutes=2),
                text=text, highlighted_phrase=phrase,
            )
```

- [ ] **Step 4: Run the test, verify it passes**

Run: `python manage.py test apps.coordination.tests.test_seed -v 2`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/coordination/seed.py apps/coordination/tests/test_seed.py
git commit -m "Add coordination seed data: 4 clusters with accounts, signals, duplicate samples"
```

---

### Task 11: Ringkasan (main dashboard) view

Replaces the Task 4 placeholder for `analytics:ringkasan` in place — the URL name and route are unchanged.

**Files:**
- Create: `apps/analytics/selectors.py`
- Modify: `apps/analytics/views.py`
- Create: `templates/analytics/ringkasan.html`
- Modify: `static/core/css/base.css`
- Create: `apps/analytics/tests/test_selectors.py`
- Modify: `apps/analytics/tests/test_views.py` (create if absent)

**Interfaces:**
- Consumes: `apps.core.selectors.get_active_project` (Task 3), `apps.analytics.models.{Mention,Alert}` (Task 5).
- Produces: `apps.analytics.selectors.ringkasan_summary(project, days=30) -> dict` (keys: `total_mentions`, `total_interactions`, `unique_authors`, `sentiment_breakdown`, `source_breakdown`, `emotion_breakdown`, `timeline_chart`, `health_index`, `positive_pct`), `apps.analytics.selectors.recent_alerts(limit=5) -> list[Alert]`, `apps.analytics.selectors.timeline_chart(timeline, width, height) -> dict` (keys: `positive_points`, `neutral_points`, `negative_points`, `width`, `height` — SVG polyline point strings, reused by Task 12's War Room chart).

- [ ] **Step 1: Write the failing selector test**

`apps/analytics/tests/test_selectors.py`:
```python
from django.test import TestCase
from django.utils import timezone

from apps.core.models import Platform, Project, Tenant
from apps.analytics.models import Mention
from apps.analytics import selectors


class RingkasanSummaryTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Kemenko PMK")
        self.project = Project.objects.create(tenant=self.tenant, name="Program Pangan Rakyat")
        self.platform = Platform.objects.create(
            slug="x", display_name="X (Twitter)", method=Platform.METHOD_INTERNAL
        )

    def test_summary_counts_and_breakdowns(self):
        now = timezone.now()
        Mention.objects.create(
            project=self.project, platform=self.platform, author_handle="@a",
            content_snippet="s", sentiment=Mention.SENTIMENT_POSITIVE, emotion=Mention.EMOTION_TRUST,
            posted_at=now, engagement_count=10,
        )
        Mention.objects.create(
            project=self.project, platform=self.platform, author_handle="@b",
            content_snippet="s", sentiment=Mention.SENTIMENT_NEGATIVE, emotion=Mention.EMOTION_ANGER,
            posted_at=now, engagement_count=5,
        )
        summary = selectors.ringkasan_summary(self.project)
        self.assertEqual(summary["total_mentions"], 2)
        self.assertEqual(summary["total_interactions"], 15)
        self.assertEqual(summary["unique_authors"], 2)
        positive = next(s for s in summary["sentiment_breakdown"] if s["key"] == Mention.SENTIMENT_POSITIVE)
        self.assertEqual(positive["count"], 1)
        self.assertEqual(positive["pct"], 50)

    def test_summary_excludes_political_mentions(self):
        now = timezone.now()
        Mention.objects.create(
            project=self.project, platform=self.platform, author_handle="@political",
            content_snippet="s", sentiment=Mention.SENTIMENT_NEUTRAL, emotion=Mention.EMOTION_TRUST,
            posted_at=now, is_political=True,
        )
        summary = selectors.ringkasan_summary(self.project)
        self.assertEqual(summary["total_mentions"], 0)
```

- [ ] **Step 2: Run the test, verify it fails**

Run: `python manage.py test apps.analytics.tests.test_selectors -v 2`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.analytics.selectors'`

- [ ] **Step 3: Write `apps/analytics/selectors.py`**

```python
from collections import OrderedDict

from django.db.models import Count, Sum
from django.utils import timezone

from .models import Alert, Mention

SENTIMENT_LABELS = OrderedDict([
    (Mention.SENTIMENT_POSITIVE, "Positif"),
    (Mention.SENTIMENT_NEUTRAL, "Netral"),
    (Mention.SENTIMENT_NEGATIVE, "Negatif"),
])

EMOTION_LABELS = dict(Mention.EMOTION_CHOICES)


def ringkasan_summary(project, days=30):
    since = timezone.now() - timezone.timedelta(days=days)
    qs = Mention.objects.filter(project=project, posted_at__gte=since, is_political=False)

    total_mentions = qs.count()
    total_interactions = qs.aggregate(total=Sum("engagement_count"))["total"] or 0
    unique_authors = qs.values("author_handle").distinct().count()

    sentiment_counts = {row["sentiment"]: row["n"] for row in qs.values("sentiment").annotate(n=Count("id"))}
    sentiment_breakdown = []
    for key, label in SENTIMENT_LABELS.items():
        count = sentiment_counts.get(key, 0)
        pct = round((count / total_mentions) * 100) if total_mentions else 0
        sentiment_breakdown.append({"key": key, "label": label, "count": count, "pct": pct})

    source_breakdown = []
    for row in qs.values("platform__display_name").annotate(n=Count("id")).order_by("-n"):
        source_breakdown.append({
            "name": row["platform__display_name"],
            "count": row["n"],
            "pct": round((row["n"] / total_mentions) * 100) if total_mentions else 0,
        })

    emotion_counts = {row["emotion"]: row["n"] for row in qs.values("emotion").annotate(n=Count("id"))}
    emotion_breakdown = []
    for key, label in EMOTION_LABELS.items():
        count = emotion_counts.get(key, 0)
        pct = round((count / total_mentions) * 100) if total_mentions else 0
        emotion_breakdown.append({"key": key, "label": label, "count": count, "pct": pct})
    emotion_breakdown.sort(key=lambda item: item["count"], reverse=True)

    timeline = _daily_timeline(qs, since, days)
    positive_pct = next(
        (s["pct"] for s in sentiment_breakdown if s["key"] == Mention.SENTIMENT_POSITIVE), 0
    )
    health_index = round((positive_pct * 0.7) + (min(total_mentions, 5000) / 5000 * 30))

    return {
        "total_mentions": total_mentions,
        "total_interactions": total_interactions,
        "unique_authors": unique_authors,
        "sentiment_breakdown": sentiment_breakdown,
        "source_breakdown": source_breakdown,
        "emotion_breakdown": emotion_breakdown,
        "timeline_chart": timeline_chart(timeline),
        "health_index": health_index,
        "positive_pct": positive_pct,
    }


def _daily_timeline(qs, since, days):
    buckets = OrderedDict()
    for offset in range(days):
        day = (since + timezone.timedelta(days=offset)).date()
        buckets[day] = {"positive": 0, "neutral": 0, "negative": 0}

    for mention in qs.only("posted_at", "sentiment"):
        day = mention.posted_at.date()
        if day in buckets:
            buckets[day][mention.sentiment] += 1

    return list(buckets.values())


def _scale_points(values, width, height, max_value):
    if not values:
        return ""
    step = width / max(len(values) - 1, 1)
    points = []
    for index, value in enumerate(values):
        x = round(index * step, 1)
        y = round(height - (value / max_value * height), 1) if max_value else height
        points.append(f"{x},{y}")
    return " ".join(points)


def timeline_chart(timeline, width=760, height=230):
    max_value = max(
        [max(day["positive"], day["neutral"], day["negative"]) for day in timeline] or [0]
    ) or 1
    return {
        "positive_points": _scale_points([d["positive"] for d in timeline], width, height, max_value),
        "neutral_points": _scale_points([d["neutral"] for d in timeline], width, height, max_value),
        "negative_points": _scale_points([d["negative"] for d in timeline], width, height, max_value),
        "width": width,
        "height": height,
    }


def recent_alerts(limit=5):
    return list(Alert.objects.select_related("rule").order_by("-triggered_at")[:limit])
```

- [ ] **Step 4: Run the selector test, verify it passes**

Run: `python manage.py test apps.analytics.tests.test_selectors -v 2`
Expected: PASS

- [ ] **Step 5: Write the failing view test**

`apps/analytics/tests/test_views.py`:
```python
from django.test import TestCase

from apps.core.seed import seed_core
from apps.analytics.seed import seed_analytics


class RingkasanViewTest(TestCase):
    def test_ringkasan_renders_kpis(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=200)
        response = self.client.get("/ringkasan/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Total Sebutan")
        self.assertContains(response, "Komposisi Sentimen")
```

- [ ] **Step 6: Run the test, verify it fails**

Run: `python manage.py test apps.analytics.tests.test_views -v 2`
Expected: FAIL — response body is `"Ringkasan — coming soon"`, does not contain "Total Sebutan"

- [ ] **Step 7: Replace the placeholder view**

`apps/analytics/views.py` — replace the `ringkasan` function only, leave the other three placeholders untouched:
```python
from django.shortcuts import render

from apps.core.selectors import get_active_project
from . import selectors


def ringkasan(request):
    project = get_active_project(request)
    summary = selectors.ringkasan_summary(project) if project else None
    alerts = selectors.recent_alerts()
    return render(request, "analytics/ringkasan.html", {
        "active_nav": "ringkasan",
        "summary": summary,
        "alerts": alerts,
    })


def war_room(request):
    from django.http import HttpResponse
    return HttpResponse("War Room — coming soon")


def narasi(request):
    from django.http import HttpResponse
    return HttpResponse("Perbandingan Narasi — coming soon")


def regional(request):
    from django.http import HttpResponse
    return HttpResponse("Regional — coming soon")
```

- [ ] **Step 8: Write the template**

`templates/analytics/ringkasan.html`:
```html
{% extends "core/base_dashboard.html" %}
{% block title %}Ringkasan{% endblock %}
{% block topbar_actions %}
  <div class="pantau-topbar-filter">Semua Platform ▾</div>
  <div class="pantau-topbar-filter mono">30 hari terakhir</div>
  <div class="pantau-btn-primary">Ekspor</div>
{% endblock %}
{% block content %}
<div class="pantau-kpi-row">
  <div class="pantau-card">
    <div class="pantau-kpi-label">Total Sebutan</div>
    <div class="pantau-kpi-value">{{ summary.total_mentions }}</div>
  </div>
  <div class="pantau-card">
    <div class="pantau-kpi-label">Total Interaksi</div>
    <div class="pantau-kpi-value">{{ summary.total_interactions }}</div>
  </div>
  <div class="pantau-card">
    <div class="pantau-kpi-label">Penulis Unik</div>
    <div class="pantau-kpi-value">{{ summary.unique_authors }}</div>
  </div>
  <div class="pantau-card pantau-card-dark">
    <div class="pantau-health-gauge" style="--pct: {{ summary.health_index }}"><span>{{ summary.health_index }}</span></div>
    <div>
      <div class="pantau-kpi-label light">Indeks Kesehatan Digital</div>
      <div class="pantau-health-status">Sentimen {{ summary.positive_pct }}% positif</div>
    </div>
  </div>
</div>

<div class="pantau-card">
  <div class="pantau-card-header">
    <div class="pantau-card-title">Komposisi Sentimen</div>
    <div>
      {% for item in summary.sentiment_breakdown %}
        <span class="pantau-legend-item pantau-dot-{{ item.key }}">{{ item.label }} {{ item.count }} ({{ item.pct }}%)</span>
      {% endfor %}
    </div>
  </div>
  <div class="pantau-sentiment-bar">
    {% for item in summary.sentiment_breakdown %}
      <div class="pantau-bg-{{ item.key }}" style="width: {{ item.pct }}%"></div>
    {% endfor %}
  </div>
</div>

<div class="pantau-grid-2-1">
  <div class="pantau-card">
    <div class="pantau-card-title">Linimasa Sebutan</div>
    <svg width="100%" height="{{ summary.timeline_chart.height }}" viewBox="0 0 {{ summary.timeline_chart.width }} {{ summary.timeline_chart.height }}" preserveAspectRatio="none">
      <polyline points="{{ summary.timeline_chart.positive_points }}" fill="none" stroke="#178A5C" stroke-width="2.5"></polyline>
      <polyline points="{{ summary.timeline_chart.neutral_points }}" fill="none" stroke="#AEBBC7" stroke-width="2" stroke-dasharray="5 4"></polyline>
      <polyline points="{{ summary.timeline_chart.negative_points }}" fill="none" stroke="#C6483F" stroke-width="2.5"></polyline>
    </svg>
  </div>
  <div class="pantau-card">
    <div class="pantau-card-title">Sumber Sebutan</div>
    {% for source in summary.source_breakdown %}
      <div class="pantau-source-row">
        <span>{{ source.name }}</span>
        <div class="pantau-progress"><div class="pantau-progress-fill" style="width: {{ source.pct }}%"></div></div>
        <span class="mono">{{ source.count }}</span>
      </div>
    {% endfor %}
  </div>
</div>

<div class="pantau-grid-2">
  <div class="pantau-card">
    <div class="pantau-card-title">Emosi Dominan — Roda Plutchik</div>
    {% for item in summary.emotion_breakdown %}
      <div class="pantau-source-row">
        <span>{{ item.label }}</span>
        <div class="pantau-progress"><div class="pantau-progress-fill" style="width: {{ item.pct }}%"></div></div>
        <span class="mono">{{ item.pct }}%</span>
      </div>
    {% endfor %}
  </div>
  <div class="pantau-card">
    <div class="pantau-card-header">
      <div class="pantau-card-title">Peringatan Terbaru</div>
      <span class="pantau-badge pantau-badge-negative">{{ alerts|length }} terbaru</span>
    </div>
    {% for alert in alerts %}
      <div class="pantau-alert-row pantau-alert-{{ alert.severity }}">
        <div>
          <div class="pantau-alert-title">{{ alert.title }}</div>
          <div class="pantau-alert-detail">{{ alert.detail }}</div>
        </div>
        <span class="mono">{{ alert.triggered_at|date:"H:i" }}</span>
      </div>
    {% endfor %}
  </div>
</div>
{% endblock %}
```

- [ ] **Step 9: Extend the shared stylesheet**

Append to `static/core/css/base.css`:
```css
.pantau-kpi-row { display: grid; grid-template-columns: 1fr 1fr 1fr 1.2fr; gap: 14px; }
.pantau-card-dark {
  background: linear-gradient(135deg, var(--navy), #123A52);
  border-color: var(--navy);
  display: flex; align-items: center; gap: 16px;
}
.pantau-kpi-label {
  font: 600 10.5px 'IBM Plex Sans', sans-serif; color: var(--text-muted);
  letter-spacing: .07em; text-transform: uppercase;
}
.pantau-kpi-label.light { color: #7FA0B8; }
.pantau-kpi-value { font: 600 30px Archivo, sans-serif; color: var(--navy); margin: 8px 0 4px; }

.pantau-health-gauge {
  --pct: 0;
  width: 64px; height: 64px; border-radius: 50%; flex: none;
  background: conic-gradient(#2FD4C4 calc(var(--pct) * 1%), #1E3A55 0);
  display: grid; place-items: center;
  font: 700 18px Archivo, sans-serif; color: #fff;
}
.pantau-health-status { font: 600 15px Archivo, sans-serif; color: var(--teal-light); margin: 5px 0 3px; }

.pantau-card-header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 12px; }
.pantau-card-title { font: 600 13px 'IBM Plex Sans', sans-serif; color: var(--navy-2); margin-bottom: 12px; }
.pantau-legend-item { font: 400 11px 'IBM Plex Sans', sans-serif; color: var(--text-muted); margin-right: 16px; }
.pantau-legend-item::before { content: ""; display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 5px; }
.pantau-dot-positive::before { background: var(--positive); }
.pantau-dot-neutral::before { background: var(--neutral); }
.pantau-dot-negative::before { background: var(--negative); }

.pantau-sentiment-bar { display: flex; height: 14px; border-radius: 7px; overflow: hidden; gap: 2px; }
.pantau-bg-positive { background: var(--positive); }
.pantau-bg-neutral { background: var(--neutral); }
.pantau-bg-negative { background: var(--negative); }

.pantau-grid-2-1 { display: grid; grid-template-columns: 2fr 1fr; gap: 14px; }
.pantau-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }

.pantau-source-row { display: grid; grid-template-columns: 96px 1fr 70px; align-items: center; gap: 10px; margin-bottom: 9px; font: 500 11.5px 'IBM Plex Sans', sans-serif; color: #334155; }
.pantau-progress { height: 8px; border-radius: 4px; background: #EEF2F5; }
.pantau-progress-fill { height: 8px; border-radius: 4px; background: var(--teal); }
.mono { font-family: 'IBM Plex Mono', monospace; text-align: right; color: var(--text-muted); }

.pantau-alert-row { display: flex; justify-content: space-between; gap: 12px; padding: 10px 12px; border-radius: 8px; border: 1px solid #EEF2F5; margin-bottom: 8px; }
.pantau-alert-critical { border-color: #F2D8D6; background: #FDF7F6; }
.pantau-alert-warning { border-color: #F0E4CC; background: #FDFAF3; }
.pantau-alert-title { font: 600 12px 'IBM Plex Sans', sans-serif; color: var(--navy-2); }
.pantau-alert-detail { font: 400 10.5px 'IBM Plex Sans', sans-serif; color: var(--text-faint); margin-top: 2px; }

.pantau-topbar-filter { padding: 7px 12px; border: 1px solid var(--border); border-radius: 8px; background: #fff; font: 500 11.5px 'IBM Plex Sans', sans-serif; color: #334155; }
.pantau-topbar-filter.mono { font-family: 'IBM Plex Mono', monospace; }
.pantau-btn-primary { padding: 7px 14px; border-radius: 8px; background: var(--teal); font: 600 11.5px 'IBM Plex Sans', sans-serif; color: #fff; cursor: pointer; }
```

- [ ] **Step 10: Run the test, verify it passes**

Run: `python manage.py test apps.analytics.tests.test_views -v 2`
Expected: PASS

- [ ] **Step 11: Commit**

```bash
git add apps/analytics/selectors.py apps/analytics/views.py templates/analytics/ringkasan.html static/core/css/base.css apps/analytics/tests
git commit -m "Implement Ringkasan view: KPIs, sentiment split, timeline, sources, emotions, alerts"
```

---

### Task 12: War Room view

Replaces the Task 4 placeholder for `analytics:war_room` in place.

**Files:**
- Modify: `apps/analytics/selectors.py`
- Modify: `apps/analytics/views.py`
- Create: `templates/analytics/war_room.html`
- Create: `static/analytics/css/war_room.css`
- Modify: `apps/analytics/tests/test_selectors.py`
- Modify: `apps/analytics/tests/test_views.py`

**Interfaces:**
- Consumes: `apps.analytics.selectors.timeline_chart` (Task 11), `apps.coordination.models.{CoordinationCluster,ClusterAccount}` (Task 9/10).
- Produces: `apps.analytics.selectors.war_room_summary(issue) -> dict` (keys: `issue`, `mentions_last_hour`, `negative_ratio`, `hourly_change_pct`, `cumulative_reach`, `coordinated_cluster_count`, `timeline_chart`, `top_spreaders`, `hotspots`).

- [ ] **Step 1: Write the failing selector test**

Append to `apps/analytics/tests/test_selectors.py`:
```python
from apps.analytics.models import PoliticalIssue
from apps.coordination.seed import seed_coordination
from apps.core.seed import seed_core
from apps.analytics.seed import seed_analytics


class WarRoomSummaryTest(TestCase):
    def test_war_room_summary_shape(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=100)
        seed_coordination()
        issue = PoliticalIssue.objects.get(title="Distribusi Pangan Wilayah Timur")

        summary = selectors.war_room_summary(issue)
        self.assertEqual(summary["issue"], issue)
        self.assertGreaterEqual(summary["coordinated_cluster_count"], 0)
        self.assertIn("negative_points", summary["timeline_chart"])
        self.assertIsInstance(summary["hotspots"], list)
```

- [ ] **Step 2: Run the test, verify it fails**

Run: `python manage.py test apps.analytics.tests.test_selectors -v 2`
Expected: FAIL — `AttributeError: module 'apps.analytics.selectors' has no attribute 'war_room_summary'`

- [ ] **Step 3: Add `war_room_summary` to `apps/analytics/selectors.py`**

Append (add `Count` and `Sum` are already imported; add this below `recent_alerts`):
```python
def war_room_summary(issue):
    now = timezone.now()
    last_hour = Mention.objects.filter(issue=issue, posted_at__gte=now - timezone.timedelta(hours=1))
    prev_window = Mention.objects.filter(
        issue=issue,
        posted_at__gte=now - timezone.timedelta(hours=4),
        posted_at__lt=now - timezone.timedelta(hours=1),
    )

    mentions_last_hour = last_hour.count()
    negative_last_hour = last_hour.filter(sentiment=Mention.SENTIMENT_NEGATIVE).count()
    negative_ratio = round((negative_last_hour / mentions_last_hour) * 100) if mentions_last_hour else 0

    prev_hourly_avg = (prev_window.count() / 3) or 1
    hourly_change_pct = round(((mentions_last_hour - prev_hourly_avg) / prev_hourly_avg) * 100)

    cumulative_reach = Mention.objects.filter(issue=issue).aggregate(total=Sum("reach_estimate"))["total"] or 0

    from apps.coordination.models import ClusterAccount, CoordinationCluster
    coordinated_cluster_count = CoordinationCluster.objects.filter(
        issue=issue, status=CoordinationCluster.STATUS_FLAGGED
    ).count()
    top_spreaders = list(
        ClusterAccount.objects.filter(cluster__issue=issue)
        .select_related("cluster")
        .order_by("-reach")[:5]
    )

    timeline = _hourly_timeline(issue, now)
    hotspots = _geo_hotspots(issue)

    return {
        "issue": issue,
        "mentions_last_hour": mentions_last_hour,
        "negative_ratio": negative_ratio,
        "hourly_change_pct": hourly_change_pct,
        "cumulative_reach": cumulative_reach,
        "coordinated_cluster_count": coordinated_cluster_count,
        "timeline_chart": timeline_chart(timeline, width=800, height=210),
        "top_spreaders": top_spreaders,
        "hotspots": hotspots,
    }


def _hourly_timeline(issue, now, hours=12, bucket_minutes=5):
    since = now - timezone.timedelta(hours=hours)
    bucket_count = hours * 60 // bucket_minutes
    buckets = [{"positive": 0, "neutral": 0, "negative": 0} for _ in range(bucket_count)]
    for mention in Mention.objects.filter(issue=issue, posted_at__gte=since).only("posted_at", "sentiment"):
        elapsed_minutes = (mention.posted_at - since).total_seconds() / 60
        index = min(int(elapsed_minutes // bucket_minutes), bucket_count - 1)
        buckets[index][mention.sentiment] += 1
    return buckets


def _geo_hotspots(issue, limit=6):
    rows = (
        Mention.objects.filter(issue=issue, province__isnull=False)
        .values("province__name")
        .annotate(n=Count("id"))
        .order_by("-n")[:limit]
    )
    rows = list(rows)
    max_count = rows[0]["n"] if rows else 1
    return [
        {"name": row["province__name"], "count": row["n"], "pct": round((row["n"] / max_count) * 100)}
        for row in rows
    ]
```

- [ ] **Step 4: Run the selector test, verify it passes**

Run: `python manage.py test apps.analytics.tests.test_selectors -v 2`
Expected: PASS

- [ ] **Step 5: Write the failing view test**

Append to `apps/analytics/tests/test_views.py`:
```python
from apps.coordination.seed import seed_coordination


class WarRoomViewTest(TestCase):
    def test_war_room_renders(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=100)
        seed_coordination()
        response = self.client.get("/war-room/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WAR ROOM NARASI")
```

- [ ] **Step 6: Run the test, verify it fails**

Run: `python manage.py test apps.analytics.tests.test_views -v 2`
Expected: FAIL — response body is `"War Room — coming soon"`

- [ ] **Step 7: Replace the placeholder view**

`apps/analytics/views.py` — replace only the `war_room` function:
```python
def war_room(request):
    from apps.analytics.models import PoliticalIssue

    project = get_active_project(request)
    issue = PoliticalIssue.objects.filter(status=PoliticalIssue.STATUS_ACTIVE).first() if project else None
    summary = selectors.war_room_summary(issue) if issue else None
    return render(request, "analytics/war_room.html", {"active_nav": "war_room", "summary": summary})
```

- [ ] **Step 8: Write the war-room base template and stylesheet**

`templates/core/base_warroom.html` already exists (Task 4) with an `extra_css` block — no change needed.

`static/analytics/css/war_room.css`:
```css
.pantau-warroom-body { margin: 0; background: #0A1626; font-family: 'IBM Plex Sans', system-ui, sans-serif; color: #D7E3F0; }

.wr-header { display: flex; align-items: center; gap: 16px; padding: 16px 26px; border-bottom: 1px solid #1E3A55; }
.wr-title-row { display: flex; align-items: center; gap: 10px; }
.wr-title { font: 700 16px Archivo, sans-serif; color: #fff; }
.wr-live-badge { display: flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 20px; background: rgba(214,69,56,.16); border: 1px solid rgba(214,69,56,.4); font: 700 10px 'IBM Plex Mono', monospace; color: #FF8A80; letter-spacing: .1em; }
.wr-live-dot { width: 7px; height: 7px; border-radius: 50%; background: #FF6B5E; animation: pulse 1.4s infinite; }
.wr-subtitle { font: 400 11.5px 'IBM Plex Sans', sans-serif; color: #7A90A8; margin-top: 2px; }
.wr-header-actions { margin-left: auto; display: flex; align-items: center; gap: 10px; }
.wr-pill { padding: 6px 12px; border: 1px solid #1E3A55; border-radius: 8px; font: 500 11px 'IBM Plex Mono', monospace; color: #7FD1C8; }
.wr-btn-escalate { padding: 6px 14px; border-radius: 8px; background: #C6483F; font: 600 11.5px 'IBM Plex Sans', sans-serif; color: #fff; cursor: pointer; }

.wr-notice { padding: 7px 26px; background: rgba(47,212,196,.06); border-bottom: 1px solid #1E3A55; font: 400 10.5px 'IBM Plex Sans', sans-serif; color: #6E8AA3; }

.wr-body { display: grid; grid-template-columns: 1fr; gap: 16px; padding: 20px 26px; }
.wr-left { display: flex; flex-direction: column; gap: 16px; }

.wr-kpi-strip { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.wr-kpi-card { background: #10233A; border: 1px solid #1E3A55; border-radius: 10px; padding: 14px 16px; }
.wr-kpi-label { font: 600 10px 'IBM Plex Sans', sans-serif; color: #6E8AA3; letter-spacing: .08em; text-transform: uppercase; }
.wr-kpi-value { font: 600 26px Archivo, sans-serif; color: #fff; margin: 6px 0 2px; }
.wr-kpi-value.wr-negative { color: #FF8A80; }
.wr-kpi-value.wr-warning { color: #F0B14E; }
.wr-kpi-delta { font: 600 10.5px 'IBM Plex Mono', monospace; color: #7A90A8; }

.wr-card { background: #10233A; border: 1px solid #1E3A55; border-radius: 10px; padding: 16px 18px; }
.wr-card-title { font: 600 13px 'IBM Plex Sans', sans-serif; color: #D7E3F0; margin-bottom: 12px; }

.wr-grid-2 { display: grid; grid-template-columns: 1.3fr 1fr; gap: 16px; }
.wr-spreader-row { display: grid; grid-template-columns: 1fr 90px 70px 86px; align-items: center; gap: 8px; padding: 9px 0; border-bottom: 1px solid #16304C; }
.wr-hotspot-row { display: grid; grid-template-columns: 110px 1fr 44px; align-items: center; gap: 10px; padding: 9px 0; }
.mono-light { font: 500 11px 'IBM Plex Mono', monospace; color: #AFC3D6; }
.wr-cluster-tag { font: 600 10px 'IBM Plex Sans', sans-serif; color: #F0B14E; background: rgba(240,177,78,.14); border-radius: 4px; padding: 3px 7px; text-align: center; }
.wr-progress { height: 8px; border-radius: 4px; background: #16304C; }
.wr-progress-fill { height: 8px; border-radius: 4px; background: #FF6B5E; }
```

- [ ] **Step 9: Write the template**

`templates/analytics/war_room.html`:
```html
{% extends "core/base_warroom.html" %}
{% block extra_css %}<link rel="stylesheet" href="{% static 'analytics/css/war_room.css' %}">{% endblock %}
{% load static %}
{% block content %}
<div class="wr-header">
  <div class="pantau-logo">P</div>
  <div>
    <div class="wr-title-row">
      <span class="wr-title">WAR ROOM NARASI</span>
      <span class="wr-live-badge"><span class="wr-live-dot"></span>LANGSUNG</span>
    </div>
    <div class="wr-subtitle">Isu aktif: <strong>{{ summary.issue.title }}</strong> · dibuka {{ summary.issue.opened_at|date:"d M Y H:i" }} WIB · pemilik: {{ summary.issue.owner_label }}</div>
  </div>
  <div class="wr-header-actions">
    <div class="wr-pill">Segarkan: 60 dtk</div>
    <div class="wr-pill">Layar penuh (kiosk)</div>
    <div class="wr-btn-escalate">Eskalasi</div>
  </div>
</div>
<div class="wr-notice">⚖ Tampilan narasi politik — hanya untuk kesadaran sentimen publik &amp; pelaporan netral. Dilarang untuk penargetan, penekanan, atau pemrofilan individu (FR-29.5). Seluruh kueri tercatat dalam log audit.</div>
<div class="wr-body">
  <div class="wr-left">
    <div class="wr-kpi-strip">
      <div class="wr-kpi-card">
        <div class="wr-kpi-label">Sebutan / Jam</div>
        <div class="wr-kpi-value">{{ summary.mentions_last_hour }}</div>
        <div class="wr-kpi-delta">{{ summary.hourly_change_pct }}% vs 3 jam lalu</div>
      </div>
      <div class="wr-kpi-card">
        <div class="wr-kpi-label">Rasio Negatif (1 jam)</div>
        <div class="wr-kpi-value wr-negative">{{ summary.negative_ratio }}%</div>
      </div>
      <div class="wr-kpi-card">
        <div class="wr-kpi-label">Jangkauan Kumulatif</div>
        <div class="wr-kpi-value">{{ summary.cumulative_reach }}</div>
      </div>
      <div class="wr-kpi-card">
        <div class="wr-kpi-label">Klaster Terkoordinasi</div>
        <div class="wr-kpi-value wr-warning">{{ summary.coordinated_cluster_count }}</div>
        <div class="wr-kpi-delta">menunggu tinjauan analis</div>
      </div>
    </div>
    <div class="wr-card">
      <div class="wr-card-title">Volume Waktu-Nyata — interval 5 menit</div>
      <svg width="100%" height="{{ summary.timeline_chart.height }}" viewBox="0 0 {{ summary.timeline_chart.width }} {{ summary.timeline_chart.height }}" preserveAspectRatio="none">
        <polyline points="{{ summary.timeline_chart.negative_points }}" fill="none" stroke="#FF6B5E" stroke-width="2.5"></polyline>
        <polyline points="{{ summary.timeline_chart.positive_points }}" fill="none" stroke="#2FD4C4" stroke-width="2"></polyline>
        <polyline points="{{ summary.timeline_chart.neutral_points }}" fill="none" stroke="#41597A" stroke-width="2" stroke-dasharray="4 4"></polyline>
      </svg>
    </div>
    <div class="wr-grid-2">
      <div class="wr-card">
        <div class="wr-card-title">Akun Penyebar Teratas</div>
        {% for account in summary.top_spreaders %}
          <div class="wr-spreader-row">
            <span class="mono-light">{{ account.handle }}</span>
            <span class="mono-light">{{ account.reach }}</span>
            <span class="mono-light">{{ account.post_count }}</span>
            <span class="wr-cluster-tag">{{ account.cluster.cluster_code }}</span>
          </div>
        {% endfor %}
      </div>
      <div class="wr-card">
        <div class="wr-card-title">Titik Panas Geografis</div>
        {% for hotspot in summary.hotspots %}
          <div class="wr-hotspot-row">
            <span>{{ hotspot.name }}</span>
            <div class="wr-progress"><div class="wr-progress-fill" style="width: {{ hotspot.pct }}%"></div></div>
            <span class="mono-light">{{ hotspot.count }}</span>
          </div>
        {% endfor %}
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 10: Run the test, verify it passes**

Run: `python manage.py test apps.analytics.tests.test_views -v 2`
Expected: PASS

- [ ] **Step 11: Commit**

```bash
git add apps/analytics/selectors.py apps/analytics/views.py templates/analytics/war_room.html static/analytics/css/war_room.css apps/analytics/tests
git commit -m "Implement War Room view: live KPI strip, realtime chart, spreaders, geo hotspots"
```

---

### Task 13: Perbandingan Narasi (coalition comparison) view

Replaces the Task 4 placeholder for `analytics:narasi` in place.

**Files:**
- Modify: `apps/analytics/selectors.py`
- Modify: `apps/analytics/views.py`
- Create: `apps/analytics/templatetags/__init__.py`, `apps/analytics/templatetags/analytics_extras.py`
- Create: `templates/analytics/narasi.html`
- Modify: `static/core/css/base.css`
- Modify: `apps/analytics/tests/test_selectors.py`
- Modify: `apps/analytics/tests/test_views.py`

**Interfaces:**
- Consumes: `apps.analytics.selectors._scale_points` (Task 11, private helper reused here), `apps.analytics.models.Coalition` (Task 5).
- Produces: `apps.analytics.templatetags.analytics_extras.get_item` template filter (`{% load analytics_extras %}`) — a general dict-lookup-by-variable-key filter, reusable by any later template that needs it.
- Produces: `apps.analytics.selectors.narasi_summary(issue) -> dict` (keys: `issue`, `total_attributed`, `unattributed_pct`, `coalitions` — list of dicts with `coalition`, `count`, `share_pct`, `sentiment_breakdown`, `trend_chart` —, `overlay_chart`).

- [ ] **Step 1: Write the failing selector test**

Append to `apps/analytics/tests/test_selectors.py`:
```python
class NarasiSummaryTest(TestCase):
    def test_narasi_summary_splits_by_coalition(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=100)
        issue = PoliticalIssue.objects.get(title="Distribusi Pangan Wilayah Timur")

        summary = selectors.narasi_summary(issue)
        self.assertEqual(summary["issue"], issue)
        self.assertEqual(len(summary["coalitions"]), 2)
        total_share = sum(c["share_pct"] for c in summary["coalitions"])
        self.assertGreater(total_share, 0)
        self.assertIn("series", summary["overlay_chart"])
```

- [ ] **Step 2: Run the test, verify it fails**

Run: `python manage.py test apps.analytics.tests.test_selectors -v 2`
Expected: FAIL — `AttributeError: module 'apps.analytics.selectors' has no attribute 'narasi_summary'`

- [ ] **Step 3: Add `narasi_summary` to `apps/analytics/selectors.py`**

Append (add `from .models import Coalition` alongside the existing `from .models import Alert, Mention` import):
```python
def narasi_summary(issue):
    coalitions = Coalition.objects.all()
    total_political = Mention.objects.filter(issue=issue, is_political=True).count()
    total_attributed = Mention.objects.filter(issue=issue, coalition__isnull=False).count()
    unattributed_pct = (
        round(((total_political - total_attributed) / total_political) * 100)
        if total_political else 0
    )

    coalition_data = []
    for coalition in coalitions:
        qs = Mention.objects.filter(issue=issue, coalition=coalition)
        count = qs.count()
        share_pct = round((count / total_attributed) * 100) if total_attributed else 0
        sentiment_counts = {row["sentiment"]: row["n"] for row in qs.values("sentiment").annotate(n=Count("id"))}
        sentiment_breakdown = []
        for key, label in SENTIMENT_LABELS.items():
            c = sentiment_counts.get(key, 0)
            pct = round((c / count) * 100) if count else 0
            sentiment_breakdown.append({"key": key, "label": label, "pct": pct})
        coalition_data.append({
            "coalition": coalition,
            "count": count,
            "share_pct": share_pct,
            "sentiment_breakdown": sentiment_breakdown,
            "trend_chart": _coalition_trend(qs),
        })

    return {
        "issue": issue,
        "total_attributed": total_attributed,
        "unattributed_pct": unattributed_pct,
        "coalitions": coalition_data,
        "overlay_chart": _overlay_trend(coalitions, issue),
    }


def _coalition_trend(qs, days=30, width=560, height=90):
    since = timezone.now() - timezone.timedelta(days=days)
    daily = [0] * days
    for mention in qs.filter(posted_at__gte=since).only("posted_at"):
        offset = (mention.posted_at - since).days
        if 0 <= offset < days:
            daily[offset] += 1
    max_value = max(daily) or 1
    return {"points": _scale_points(daily, width, height, max_value), "width": width, "height": height}


def _overlay_trend(coalitions, issue, days=30, width=1160, height=150):
    since = timezone.now() - timezone.timedelta(days=days)
    series = {}
    for coalition in coalitions:
        daily = [0] * days
        for mention in Mention.objects.filter(
            issue=issue, coalition=coalition, posted_at__gte=since
        ).only("posted_at"):
            offset = (mention.posted_at - since).days
            if 0 <= offset < days:
                daily[offset] += 1
        max_value = max(daily) or 1
        series[coalition.slug] = _scale_points(daily, width, height, max_value)
    return {"series": series, "width": width, "height": height}
```

- [ ] **Step 4: Run the selector test, verify it passes**

Run: `python manage.py test apps.analytics.tests.test_selectors -v 2`
Expected: PASS

- [ ] **Step 5: Write the failing view test**

Append to `apps/analytics/tests/test_views.py`:
```python
class NarasiViewTest(TestCase):
    def test_narasi_renders_both_coalitions(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=100)
        response = self.client.get("/narasi/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Koalisi Nusantara Raya")
        self.assertContains(response, "Koalisi Perubahan Bersatu")
```

- [ ] **Step 6: Run the test, verify it fails**

Run: `python manage.py test apps.analytics.tests.test_views -v 2`
Expected: FAIL — response body is `"Perbandingan Narasi — coming soon"`

- [ ] **Step 7: Replace the placeholder view**

`apps/analytics/views.py` — replace only the `narasi` function:
```python
def narasi(request):
    from apps.analytics.models import PoliticalIssue

    project = get_active_project(request)
    issue = PoliticalIssue.objects.filter(status=PoliticalIssue.STATUS_ACTIVE).first() if project else None
    summary = selectors.narasi_summary(issue) if issue else None
    return render(request, "analytics/narasi.html", {"active_nav": "narasi", "summary": summary})
```

- [ ] **Step 8: Write a template filter for dict lookup by loop variable**

Django templates cannot subscript a dict by a variable key (`{{ dict.key }}` only works when `key` is a literal) — `summary.overlay_chart.series` is keyed by `coalition.slug`, which is only known inside the `{% for %}` loop, so a small filter is needed.

`apps/analytics/templatetags/__init__.py`: empty file.
`apps/analytics/templatetags/analytics_extras.py`:
```python
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, "")
```

- [ ] **Step 9: Write the template**

`templates/analytics/narasi.html`:
```html
{% extends "core/base_dashboard.html" %}
{% load analytics_extras %}
{% block title %}Perbandingan Narasi{% endblock %}
{% block content %}
<div class="pantau-neutrality-notice">⚖ Modul pemantauan politik — akses memerlukan izin khusus dengan persetujuan Petugas Pengawas (FR-29.1). Tampilan simetris; tidak ada penilaian atas kebenaran narasi. Kueri ini tercatat di log audit.</div>

<div class="pantau-card">
  <div class="pantau-card-header">
    <div class="pantau-card-title">Pangsa Suara (SoV) pada isu ini</div>
    <div class="mono-muted">total {{ summary.total_attributed }} sebutan teratribusi · {{ summary.unattributed_pct }}% tidak teratribusi ke kubu manapun</div>
  </div>
  <div class="narasi-sov-row">
    {% for item in summary.coalitions %}
      <div class="narasi-sov-side" style="color: {{ item.coalition.color }}">
        <div class="narasi-sov-name">{{ item.coalition.name }}</div>
        <div class="narasi-sov-pct">{{ item.share_pct }}%</div>
      </div>
    {% endfor %}
  </div>
</div>

<div class="pantau-grid-2">
  {% for item in summary.coalitions %}
    <div class="pantau-card narasi-coalition-card" style="border-top: 3px solid {{ item.coalition.color }}">
      <div class="pantau-card-header">
        <div class="pantau-card-title">{{ item.coalition.name }}</div>
        <span class="mono-muted">{{ item.count }} sebutan</span>
      </div>
      <div class="pantau-sentiment-bar">
        {% for s in item.sentiment_breakdown %}
          <div class="pantau-bg-{{ s.key }}" style="width: {{ s.pct }}%"></div>
        {% endfor %}
      </div>
      <svg width="100%" height="{{ item.trend_chart.height }}" viewBox="0 0 {{ item.trend_chart.width }} {{ item.trend_chart.height }}" preserveAspectRatio="none">
        <polyline points="{{ item.trend_chart.points }}" fill="none" stroke="{{ item.coalition.color }}" stroke-width="2.5"></polyline>
      </svg>
    </div>
  {% endfor %}
</div>

<div class="pantau-card">
  <div class="pantau-card-title">SoV Harian — kedua kubu pada skala yang sama</div>
  <svg width="100%" height="{{ summary.overlay_chart.height }}" viewBox="0 0 {{ summary.overlay_chart.width }} {{ summary.overlay_chart.height }}" preserveAspectRatio="none">
    {% for item in summary.coalitions %}
      <polyline points="{{ summary.overlay_chart.series|get_item:item.coalition.slug }}" fill="none" stroke="{{ item.coalition.color }}" stroke-width="2.5"></polyline>
    {% endfor %}
  </svg>
</div>
{% endblock %}
```

- [ ] **Step 10: Extend the shared stylesheet**

Append to `static/core/css/base.css`:
```css
.mono-muted { font: 400 11px 'IBM Plex Sans', sans-serif; color: var(--text-faint); }
.narasi-sov-row { display: flex; justify-content: space-around; align-items: baseline; padding: 8px 0; }
.narasi-sov-name { font: 600 13px 'IBM Plex Sans', sans-serif; }
.narasi-sov-pct { font: 600 34px Archivo, sans-serif; margin-top: 4px; }
.narasi-coalition-card { display: flex; flex-direction: column; gap: 12px; }
```

- [ ] **Step 11: Run the test, verify it passes**

Run: `python manage.py test apps.analytics.tests.test_views -v 2`
Expected: PASS

- [ ] **Step 12: Commit**

```bash
git add apps/analytics/selectors.py apps/analytics/views.py apps/analytics/templatetags templates/analytics/narasi.html static/core/css/base.css apps/analytics/tests
git commit -m "Implement Perbandingan Narasi view: symmetric coalition SoV, sentiment, trend overlay"
```

---

### Task 14: Regional view

Replaces the Task 4 placeholder for `analytics:regional` in place.

**Files:**
- Modify: `apps/analytics/selectors.py`
- Modify: `apps/analytics/views.py`
- Create: `templates/analytics/regional.html`
- Modify: `static/core/css/base.css`
- Modify: `apps/analytics/tests/test_selectors.py`
- Modify: `apps/analytics/tests/test_views.py`

**Interfaces:**
- Consumes: `apps.core.models.{Province,Regency}` (Task 2).
- Produces: `apps.analytics.selectors.regional_summary(project, selected_province=None) -> dict` (keys: `province_rows` — top 10, each with `id`, `name`, `count`, `positive_pct`, `neutral_pct`, `negative_pct`, `flagged` —, `selected` — the drilled-down province plus `regencies`, or `None` if no data).

- [ ] **Step 1: Write the failing selector test**

Append to `apps/analytics/tests/test_selectors.py`:
```python
class RegionalSummaryTest(TestCase):
    def test_regional_summary_ranks_and_drills_down(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=300)

        summary = selectors.regional_summary(project)
        self.assertLessEqual(len(summary["province_rows"]), 10)
        self.assertIsNotNone(summary["selected"])
        self.assertIn("regencies", summary["selected"])

    def test_regional_summary_respects_selected_province(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=300)

        summary = selectors.regional_summary(project, selected_province="Maluku")
        self.assertEqual(summary["selected"]["name"], "Maluku")
```

- [ ] **Step 2: Run the test, verify it fails**

Run: `python manage.py test apps.analytics.tests.test_selectors -v 2`
Expected: FAIL — `AttributeError: module 'apps.analytics.selectors' has no attribute 'regional_summary'`

- [ ] **Step 3: Add `regional_summary` to `apps/analytics/selectors.py`**

Append (add `Q` to the existing `from django.db.models import Count, Sum` import, and `from apps.core.models import Province`):
```python
def regional_summary(project, selected_province=None):
    rows = (
        Mention.objects.filter(project=project, is_political=False, province__isnull=False)
        .values("province__name")
        .annotate(
            n=Count("id"),
            positive=Count("id", filter=Q(sentiment=Mention.SENTIMENT_POSITIVE)),
            neutral=Count("id", filter=Q(sentiment=Mention.SENTIMENT_NEUTRAL)),
            negative=Count("id", filter=Q(sentiment=Mention.SENTIMENT_NEGATIVE)),
        )
        .order_by("-n")
    )
    province_rows = []
    for row in rows:
        total = row["n"] or 1
        negative_pct = round((row["negative"] / total) * 100)
        province_rows.append({
            "name": row["province__name"],
            "count": row["n"],
            "positive_pct": round((row["positive"] / total) * 100),
            "neutral_pct": round((row["neutral"] / total) * 100),
            "negative_pct": negative_pct,
            "flagged": negative_pct > 50,
        })

    selected = None
    if province_rows:
        target_name = selected_province or max(province_rows, key=lambda r: r["negative_pct"])["name"]
        selected_row = next((r for r in province_rows if r["name"] == target_name), province_rows[0])
        province = Province.objects.filter(name=selected_row["name"]).first()
        regency_rows = (
            Mention.objects.filter(project=project, province=province, regency__isnull=False)
            .values("regency__name")
            .annotate(n=Count("id"))
            .order_by("-n")[:6]
        )
        regency_rows = list(regency_rows)
        max_regency = regency_rows[0]["n"] if regency_rows else 1
        selected = {
            **selected_row,
            "regencies": [
                {"name": r["regency__name"], "count": r["n"], "pct": round((r["n"] / max_regency) * 100)}
                for r in regency_rows
            ],
        }

    return {"province_rows": province_rows[:10], "selected": selected}
```

- [ ] **Step 4: Run the selector test, verify it passes**

Run: `python manage.py test apps.analytics.tests.test_selectors -v 2`
Expected: PASS

- [ ] **Step 5: Write the failing view test**

Append to `apps/analytics/tests/test_views.py`:
```python
class RegionalViewTest(TestCase):
    def test_regional_view_renders_and_drill_down(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=300)
        response = self.client.get("/regional/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Distribusi Narasi Regional")

        province_name = response.context["summary"]["province_rows"][0]["name"]
        drill_response = self.client.get(f"/regional/?provinsi={province_name}")
        self.assertEqual(drill_response.context["summary"]["selected"]["name"], province_name)
```

- [ ] **Step 6: Run the test, verify it fails**

Run: `python manage.py test apps.analytics.tests.test_views -v 2`
Expected: FAIL — response body is `"Regional — coming soon"`

- [ ] **Step 7: Replace the placeholder view**

`apps/analytics/views.py` — replace only the `regional` function:
```python
def regional(request):
    project = get_active_project(request)
    selected_province = request.GET.get("provinsi") or None
    summary = selectors.regional_summary(project, selected_province) if project else None
    return render(request, "analytics/regional.html", {"active_nav": "regional", "summary": summary})
```

- [ ] **Step 8: Write the template**

`templates/analytics/regional.html`:
```html
{% extends "core/base_dashboard.html" %}
{% block title %}Regional{% endblock %}
{% block content %}
<div class="pantau-grid-regional">
  <div class="pantau-card">
    <div class="pantau-card-title">10 Provinsi Teratas — volume &amp; komposisi sentimen</div>
    {% for row in summary.province_rows %}
      <a class="pantau-region-row{% if row.flagged %} pantau-region-flagged{% endif %}" href="?provinsi={{ row.name|urlencode }}">
        <span>{{ row.name }}{% if row.flagged %} ⚠{% endif %}</span>
        <div class="pantau-sentiment-bar">
          <div class="pantau-bg-positive" style="width: {{ row.positive_pct }}%"></div>
          <div class="pantau-bg-neutral" style="width: {{ row.neutral_pct }}%"></div>
          <div class="pantau-bg-negative" style="width: {{ row.negative_pct }}%"></div>
        </div>
        <span class="mono">{{ row.count }}</span>
      </a>
    {% endfor %}
  </div>
  <div class="pantau-card pantau-card-dark pantau-region-selected">
    <div>
      <div class="pantau-kpi-label light">Provinsi terpilih</div>
      <div class="pantau-region-name">{{ summary.selected.name }}</div>
    </div>
    <span class="pantau-badge pantau-badge-negative">{{ summary.selected.negative_pct }}% negatif</span>
    <div class="pantau-region-kpis">
      <div><div class="pantau-kpi-value light">{{ summary.selected.count }}</div><div class="pantau-kpi-label light">sebutan</div></div>
    </div>
  </div>
  <div class="pantau-card">
    <div class="pantau-card-title">Kabupaten/Kota — {{ summary.selected.name }}</div>
    {% for regency in summary.selected.regencies %}
      <div class="pantau-source-row">
        <span>{{ regency.name }}</span>
        <div class="pantau-progress"><div class="pantau-progress-fill" style="width: {{ regency.pct }}%"></div></div>
        <span class="mono">{{ regency.count }}</span>
      </div>
    {% endfor %}
  </div>
</div>
{% endblock %}
```

- [ ] **Step 9: Extend the shared stylesheet**

Append to `static/core/css/base.css`:
```css
.pantau-grid-regional { display: grid; grid-template-columns: 1fr 420px; gap: 16px; }
.pantau-region-row { display: grid; grid-template-columns: 96px 1fr 58px; align-items: center; gap: 12px; padding: 8px 0; color: inherit; text-decoration: none; }
.pantau-region-row:hover { text-decoration: none; background: #F8FAFB; }
.pantau-region-flagged { color: var(--negative); font-weight: 600; }
.pantau-region-selected { flex-direction: column; align-items: flex-start; gap: 10px; }
.pantau-region-name { font: 700 20px Archivo, sans-serif; color: #fff; margin-top: 4px; }
.pantau-region-kpis { display: flex; gap: 16px; }
.pantau-kpi-value.light { color: #fff; font: 600 18px Archivo, sans-serif; }
```

- [ ] **Step 10: Run the test, verify it passes**

Run: `python manage.py test apps.analytics.tests.test_views -v 2`
Expected: PASS

- [ ] **Step 11: Commit**

```bash
git add apps/analytics/selectors.py apps/analytics/views.py templates/analytics/regional.html static/core/css/base.css apps/analytics/tests
git commit -m "Implement Regional view: province heat ranking and regency drill-down"
```

---

### Task 15: Deteksi Koordinasi view + human-review actions

Replaces the Task 4 placeholder for `coordination:koordinasi` in place, and adds two new POST-only routes.

**Files:**
- Modify: `apps/coordination/views.py`
- Modify: `apps/coordination/urls.py`
- Create: `templates/coordination/koordinasi.html`
- Modify: `static/core/css/base.css`
- Create: `apps/coordination/tests/test_views.py`

**Interfaces:**
- Consumes: `apps.governance.services.record_audit_entry` (Task 7), `apps.coordination.models.CoordinationCluster` (Task 9).
- Produces: routes `coordination:escalate_cluster` and `coordination:mark_cluster_organic` (both POST-only, redirect back to `?cluster=<code>`). Escalation never changes `CoordinationCluster.status` (per FR-26.2/26.4 — no auto-action); marking organic sets `status=STATUS_REVIEWED_ORGANIC`. Both write exactly one `AuditLogEntry`.

- [ ] **Step 1: Write the failing test**

`apps/coordination/tests/test_views.py`:
```python
from django.test import TestCase

from apps.core.seed import seed_core
from apps.analytics.seed import seed_analytics
from apps.coordination.models import CoordinationCluster
from apps.coordination.seed import seed_coordination
from apps.governance.models import AuditLogEntry


class CoordinationViewsTest(TestCase):
    def setUp(self):
        tenant, project = seed_core()
        seed_analytics(project, mention_count=100)
        seed_coordination()

    def test_koordinasi_view_renders(self):
        response = self.client.get("/koordinasi/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Klaster-07")

    def test_mark_cluster_organic_updates_status_and_logs_audit(self):
        response = self.client.post("/koordinasi/Klaster-07/tandai-organik/")
        self.assertRedirects(response, "/koordinasi/?cluster=Klaster-07")
        cluster = CoordinationCluster.objects.get(cluster_code="Klaster-07")
        self.assertEqual(cluster.status, CoordinationCluster.STATUS_REVIEWED_ORGANIC)
        self.assertTrue(AuditLogEntry.objects.filter(target="Klaster-07").exists())

    def test_escalate_cluster_logs_audit_without_changing_status(self):
        self.client.post("/koordinasi/Klaster-07/eskalasi/")
        cluster = CoordinationCluster.objects.get(cluster_code="Klaster-07")
        self.assertEqual(cluster.status, CoordinationCluster.STATUS_FLAGGED)
        self.assertTrue(
            AuditLogEntry.objects.filter(action__icontains="tinjauan analis senior").exists()
        )
```

- [ ] **Step 2: Run the test, verify it fails**

Run: `python manage.py test apps.coordination.tests.test_views -v 2`
Expected: FAIL — response body is `"Deteksi Koordinasi — coming soon"`, `/koordinasi/Klaster-07/tandai-organik/` is a 404

- [ ] **Step 3: Write the views**

`apps/coordination/views.py`:
```python
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from apps.governance.services import record_audit_entry

from .models import CoordinationCluster


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


@transaction.atomic
def escalate_cluster(request, cluster_code):
    cluster = get_object_or_404(CoordinationCluster, cluster_code=cluster_code)
    actor_label = request.user.get_full_name() or request.user.username
    record_audit_entry(
        actor_label=actor_label,
        action="Mengirim klaster ke tinjauan analis senior",
        target=cluster.cluster_code,
    )
    messages.success(request, f"{cluster.cluster_code} dikirim ke tinjauan analis senior.")
    return redirect(f"/koordinasi/?cluster={cluster_code}")


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
```

- [ ] **Step 4: Wire the new routes**

`apps/coordination/urls.py` (replace the Task 4 version):
```python
from django.urls import path

from . import views

app_name = "coordination"

urlpatterns = [
    path("koordinasi/", views.koordinasi, name="koordinasi"),
    path("koordinasi/<str:cluster_code>/eskalasi/", views.escalate_cluster, name="escalate_cluster"),
    path("koordinasi/<str:cluster_code>/tandai-organik/", views.mark_cluster_organic, name="mark_cluster_organic"),
]
```

- [ ] **Step 5: Write the template**

`templates/coordination/koordinasi.html`:
```html
{% extends "core/base_dashboard.html" %}
{% block title %}Deteksi Koordinasi{% endblock %}
{% block content %}
<div class="pantau-neutrality-notice">⚖ Temuan bersifat indikatif, bukan bukti. Wajib tinjauan manusia sebelum tindak lanjut; sistem tidak pernah melapor/memblokir akun secara otomatis (FR-26.2, FR-26.4).</div>
<div class="pantau-grid-koordinasi">
  <div class="pantau-cluster-list">
    {% for cluster in clusters %}
      <a class="pantau-card pantau-cluster-card{% if cluster == selected %} pantau-cluster-selected{% endif %}" href="?cluster={{ cluster.cluster_code }}">
        <div class="pantau-card-header">
          <span class="mono-strong">{{ cluster.cluster_code }}</span>
          <span class="pantau-badge pantau-badge-{% if cluster.status == 'flagged' %}warning{% elif cluster.status == 'reviewed_organic' %}positive{% else %}neutral{% endif %}">{{ cluster.get_status_display }}</span>
        </div>
        <div class="pantau-cluster-score">{{ cluster.score }}</div>
        <div class="mono-muted">{{ cluster.note }}</div>
      </a>
    {% endfor %}
  </div>
  {% if selected %}
  <div class="pantau-cluster-detail">
    <div class="pantau-grid-2">
      <div class="pantau-card">
        <div class="pantau-card-title">{{ selected.cluster_code }} — Jaringan Amplifikasi</div>
        {% for account in selected.accounts.all %}
          <div class="pantau-source-row">
            <span>{{ account.handle }}</span>
            <span class="mono">{{ account.get_role_display }}</span>
            <span class="mono">{{ account.reach }}</span>
          </div>
        {% endfor %}
      </div>
      <div class="pantau-card">
        <div class="pantau-card-title">Sinyal Koordinasi</div>
        {% for signal in selected.signals.all %}
          <div class="pantau-source-row">
            <span>{{ signal.get_signal_type_display }}</span>
            <div class="pantau-progress"><div class="pantau-progress-fill" style="width: {{ signal.score|floatformat:0 }}0%"></div></div>
            <span class="mono">{{ signal.score }}</span>
          </div>
        {% endfor %}
      </div>
    </div>
    <div class="pantau-card">
      <div class="pantau-card-title">Sampel Teks Terduplikasi</div>
      <div class="pantau-grid-3">
        {% for sample in selected.duplicate_samples.all %}
          <div class="pantau-sample-card">
            <div class="mono-muted">{{ sample.account_handle }} · {{ sample.posted_at|date:"H:i" }}</div>
            <div>{{ sample.text }}</div>
          </div>
        {% endfor %}
      </div>
      <div class="pantau-cluster-actions">
        <form method="post" action="{% url 'coordination:escalate_cluster' selected.cluster_code %}">
          {% csrf_token %}
          <button type="submit" class="pantau-btn-dark">Kirim ke tinjauan analis senior</button>
        </form>
        <form method="post" action="{% url 'coordination:mark_cluster_organic' selected.cluster_code %}">
          {% csrf_token %}
          <button type="submit" class="pantau-btn-outline">Tandai organik (false positive)</button>
        </form>
        <span class="mono-muted">Pelaporan eksternal hanya manual oleh pengguna berwenang &amp; tercatat (FR-26.4)</span>
      </div>
    </div>
  </div>
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 6: Extend the shared stylesheet**

Append to `static/core/css/base.css`:
```css
.pantau-grid-koordinasi { display: grid; grid-template-columns: 330px 1fr; gap: 16px; }
.pantau-cluster-list { display: flex; flex-direction: column; gap: 10px; }
.pantau-cluster-card { display: block; text-decoration: none; color: inherit; }
.pantau-cluster-selected { border-color: var(--warning); border-width: 2px; }
.pantau-cluster-score { font: 600 26px Archivo, sans-serif; color: var(--warning); margin: 6px 0; }
.mono-strong { font: 700 13px 'IBM Plex Mono', monospace; color: var(--navy-2); }
.pantau-cluster-detail { display: flex; flex-direction: column; gap: 16px; }
.pantau-grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }
.pantau-sample-card { padding: 12px 14px; border: 1px solid #EEF2F5; border-radius: 8px; background: #FBFCFD; font-size: 11.5px; line-height: 1.55; }
.pantau-cluster-actions { display: flex; align-items: center; gap: 10px; margin-top: 14px; padding-top: 14px; border-top: 1px solid #EEF2F5; }
.pantau-btn-dark { padding: 8px 16px; border-radius: 8px; background: var(--navy); border: none; font: 600 12px 'IBM Plex Sans', sans-serif; color: #fff; cursor: pointer; }
.pantau-btn-outline { padding: 8px 16px; border-radius: 8px; border: 1px solid var(--border); background: #fff; font: 600 12px 'IBM Plex Sans', sans-serif; color: #334155; cursor: pointer; }
```

- [ ] **Step 7: Run the test, verify it passes**

Run: `python manage.py test apps.coordination.tests.test_views -v 2`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add apps/coordination/views.py apps/coordination/urls.py templates/coordination/koordinasi.html static/core/css/base.css apps/coordination/tests/test_views.py
git commit -m "Implement Deteksi Koordinasi view with escalate / mark-organic review actions"
```

---

### Task 16: Konsol Konfigurasi view

Replaces the Task 4 placeholder for `governance:konfigurasi` in place. Read-only for this phase — toggles are visual only, no POST routes (per spec: "Apify/scraper toggles are UI-only, no live API calls").

**Files:**
- Modify: `apps/governance/views.py`
- Create: `templates/governance/konfigurasi.html`
- Modify: `static/core/css/base.css`
- Create: `apps/governance/tests/test_views.py`

**Interfaces:**
- Consumes: `apps.governance.models.{PlatformIntegration,ApifyCredential,MonitoredDomain}` (Task 7).

- [ ] **Step 1: Write the failing test**

`apps/governance/tests/test_views.py`:
```python
from django.test import TestCase

from apps.core.seed import seed_core
from apps.governance.seed import seed_governance


class KonfigurasiViewTest(TestCase):
    def test_konfigurasi_view_renders(self):
        tenant, project = seed_core()
        seed_governance(tenant)
        response = self.client.get("/konfigurasi/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Konsol Konfigurasi")
        self.assertContains(response, "kompas.com")
        self.assertContains(response, "Nonaktif")
```

- [ ] **Step 2: Run the test, verify it fails**

Run: `python manage.py test apps.governance.tests.test_views -v 2`
Expected: FAIL — response body is `"Konsol Konfigurasi — coming soon"`

- [ ] **Step 3: Replace the placeholder view**

`apps/governance/views.py` — replace only the `konfigurasi` function:
```python
from django.shortcuts import render

from .models import ApifyCredential, MonitoredDomain, PlatformIntegration


def konfigurasi(request):
    integrations = PlatformIntegration.objects.select_related("platform").order_by("platform__display_name")
    credential = ApifyCredential.objects.order_by("-last_verified_at").first()
    domains = MonitoredDomain.objects.order_by("domain")
    return render(request, "governance/konfigurasi.html", {
        "active_nav": "konfigurasi",
        "integrations": integrations,
        "credential": credential,
        "domains": domains,
    })


def pengawasan(request):
    from django.http import HttpResponse
    return HttpResponse("Dasbor Pengawasan — coming soon")
```

- [ ] **Step 4: Write the template**

`templates/governance/konfigurasi.html`:
```html
{% extends "core/base_dashboard.html" %}
{% block title %}Konsol Konfigurasi{% endblock %}
{% block content %}
<div class="pantau-card">
  <div class="pantau-card-title">Platform Terpantau</div>
  {% for integration in integrations %}
    <div class="pantau-source-row">
      <span>{{ integration.platform.display_name }}</span>
      <span class="mono-muted">{{ integration.actor_id }}{% if integration.status_note %} ⚠ {{ integration.status_note }}{% endif %}</span>
      <span class="{% if integration.is_active %}pantau-status-active{% else %}pantau-status-inactive{% endif %}">
        {% if integration.is_active %}● Aktif{% else %}● Nonaktif{% endif %}
      </span>
    </div>
  {% endfor %}
</div>

<div class="pantau-grid-2">
  <div class="pantau-card">
    <div class="pantau-card-title">Kredensial Apify</div>
    <div class="mono-muted">TOKEN API (TINGKAT TENANT)</div>
    <div class="pantau-credential-box">{{ credential.masked_token }}</div>
    <div class="pantau-credential-status">✓ Terverifikasi {{ credential.last_verified_at|timesince }} lalu</div>
    <div class="pantau-hint">Nilai penuh disimpan terenkripsi di secrets manager; tidak pernah dikirim utuh ke browser (FR-2A.3).</div>
  </div>
  <div class="pantau-card">
    <div class="pantau-card-title">Pemilihan Aktor per Platform</div>
    {% for integration in integrations %}
      {% if integration.method == 'apify' %}
        <div class="pantau-source-row">
          <span>{{ integration.platform.display_name }}</span>
          <span class="mono">{{ integration.actor_id }} ▾</span>
        </div>
      {% endif %}
    {% endfor %}
  </div>
</div>

<div class="pantau-card">
  <div class="pantau-card-header">
    <div class="pantau-card-title">Situs &amp; Domain Pantauan</div>
    <div class="pantau-btn-dark">+ Tambah domain</div>
  </div>
  {% for domain in domains %}
    <div class="pantau-domain-row">
      <span class="mono-strong">{{ domain.domain }}</span>
      <span class="mono-muted">{{ domain.adapter }}</span>
      <span>{{ domain.get_status_display }}</span>
      <span class="mono-muted">{% if domain.last_tested_at %}{{ domain.last_tested_at|timesince }} lalu{% else %}—{% endif %}</span>
    </div>
  {% endfor %}
</div>
<div class="pantau-hint pantau-hint-highlight">Setiap perubahan pada konsol ini tercatat ke log audit — siapa, kapan, nilai sebelum/sesudah (FR-2A.7).</div>
{% endblock %}
```

- [ ] **Step 5: Extend the shared stylesheet**

Append to `static/core/css/base.css`:
```css
.pantau-status-active { color: var(--positive); font: 500 11px 'IBM Plex Sans', sans-serif; }
.pantau-status-inactive { color: var(--text-faint); font: 500 11px 'IBM Plex Sans', sans-serif; }
.pantau-credential-box { padding: 9px 12px; border: 1px solid var(--border); border-radius: 8px; background: #F8FAFB; font: 500 12.5px 'IBM Plex Mono', monospace; color: #334155; margin: 6px 0; }
.pantau-credential-status { font: 600 11.5px 'IBM Plex Sans', sans-serif; color: var(--positive); margin-bottom: 10px; }
.pantau-hint { padding: 10px 12px; border-radius: 8px; background: #F8FAFB; border: 1px solid #EEF2F5; font: 400 10.5px 'IBM Plex Sans', sans-serif; color: var(--text-faint); }
.pantau-hint-highlight { background: #EAF4F5; border-color: #D3E8EA; color: var(--teal); }
.pantau-domain-row { display: grid; grid-template-columns: 1.6fr 1fr 110px 110px; gap: 10px; align-items: center; padding: 10px 0; border-bottom: 1px solid #F5F7F8; font: 500 12px 'IBM Plex Sans', sans-serif; }
```

- [ ] **Step 6: Run the test, verify it passes**

Run: `python manage.py test apps.governance.tests.test_views -v 2`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add apps/governance/views.py templates/governance/konfigurasi.html static/core/css/base.css apps/governance/tests/test_views.py
git commit -m "Implement Konsol Konfigurasi view: platform integrations, Apify credential, monitored domains"
```

---

### Task 17: Dasbor Pengawasan view

Replaces the Task 4 placeholder for `governance:pengawasan` in place — the final screen.

**Files:**
- Modify: `apps/governance/views.py`
- Create: `templates/governance/pengawasan.html`
- Modify: `static/core/css/base.css`
- Modify: `apps/governance/tests/test_views.py`

**Interfaces:**
- Consumes: `apps.core.models.AnalystProfile`, `apps.governance.models.{PoliticalMonitoringPermission,AuditLogEntry,PolicyAcknowledgment}` (Task 7).

- [ ] **Step 1: Write the failing test**

Append to `apps/governance/tests/test_views.py`:
```python
class PengawasanViewTest(TestCase):
    def test_pengawasan_view_renders(self):
        tenant, project = seed_core()
        seed_governance(tenant)
        response = self.client.get("/pengawasan/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dasbor Pengawasan")
        self.assertContains(response, "dilarang keras")
```

- [ ] **Step 2: Run the test, verify it fails**

Run: `python manage.py test apps.governance.tests.test_views -v 2`
Expected: FAIL — response body is `"Dasbor Pengawasan — coming soon"`

- [ ] **Step 3: Replace the placeholder view**

`apps/governance/views.py` — replace only the `pengawasan` function:
```python
def pengawasan(request):
    from apps.core.models import AnalystProfile

    permissions = PoliticalMonitoringPermission.objects.filter(active=True).select_related("user")
    total_users = AnalystProfile.objects.count()
    political_query_count = AuditLogEntry.objects.filter(action__icontains="kueri").count()
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
```

Add the two new imports at the top of `apps/governance/views.py` alongside the existing ones:
```python
from .models import (
    ApifyCredential, AuditLogEntry, MonitoredDomain, PlatformIntegration,
    PoliticalMonitoringPermission, PolicyAcknowledgment,
)
```

- [ ] **Step 4: Write the template**

`templates/governance/pengawasan.html`:
```html
{% extends "core/base_dashboard.html" %}
{% block title %}Pengawasan{% endblock %}
{% block topbar_actions %}<div class="pantau-btn-dark">Ekspor log audit</div>{% endblock %}
{% block content %}
<div class="pantau-purpose-banner">
  <strong>Pernyataan tujuan (FR-29.5):</strong> Platform ini adalah alat pemantauan sentimen publik &amp; pelaporan naratif netral. Penggunaan untuk menargetkan, menekan, atau memprofilkan individu — termasuk warga sipil, jurnalis, atau lawan politik — dilarang keras dan melanggar kebijakan penggunaan.
</div>

<div class="pantau-kpi-row-4">
  <div class="pantau-card">
    <div class="pantau-kpi-label">Pengguna dgn Izin Pemantauan Politik</div>
    <div class="pantau-kpi-value">{{ permission_count }}</div>
    <div class="mono-muted">dari {{ total_users }} pengguna total</div>
  </div>
  <div class="pantau-card">
    <div class="pantau-kpi-label">Kueri Aktor/Kubu Politik</div>
    <div class="pantau-kpi-value">{{ political_query_count }}</div>
    <div class="mono-muted">seluruhnya tercatat immutable (FR-29.2)</div>
  </div>
  <div class="pantau-card">
    <div class="pantau-kpi-label">Profil Individu Ditolak Otomatis</div>
    <div class="pantau-kpi-value pantau-kpi-positive">{{ excluded_profile_count }}</div>
    <div class="mono-muted">dikecualikan dari penandaan aktor (FR-29.3)</div>
  </div>
  <div class="pantau-card">
    <div class="pantau-kpi-label">Mode Periode Pemilu</div>
    <div class="pantau-election-toggle">Nonaktif</div>
    <div class="mono-muted">saat aktif: konfigurasi aktor dibekukan (§8.5)</div>
  </div>
</div>

<div class="pantau-card">
  <div class="pantau-card-title">Pengguna dengan Izin Pemantauan Politik</div>
  {% for permission in permissions %}
    <div class="pantau-permission-row">
      <span>{{ permission.user.get_full_name|default:permission.user.username }}</span>
      <span class="mono-muted">{{ permission.approved_by }}</span>
      <span class="mono">{{ permission.approved_at|date:"d M y" }}</span>
    </div>
  {% endfor %}
</div>

<div class="pantau-card">
  <div class="pantau-card-title">Log Audit — Aktivitas Pemantauan Politik (append-only)</div>
  {% for entry in audit_entries %}
    <div class="pantau-audit-row">
      <span class="mono">{{ entry.timestamp|date:"d M H:i" }}</span>
      <span>{{ entry.actor_label }}</span>
      <span>{{ entry.action }}</span>
      <span class="mono-strong">{{ entry.target }}</span>
    </div>
  {% endfor %}
</div>

<div class="pantau-card pantau-policy-ack">
  <div>
    <div class="pantau-card-title">Kebijakan Penggunaan &amp; Persetujuan Tahunan (FR-29.6)</div>
    <div class="mono-muted">disetujui oleh {{ policy_ack.approved_by }} pada {{ policy_ack.approved_at|date:"d M Y" }} · tinjauan berikutnya jatuh tempo {{ policy_ack.next_review_at|date:"d M Y" }}</div>
  </div>
  <span class="pantau-badge pantau-badge-positive">✓ Berlaku</span>
</div>
{% endblock %}
```

- [ ] **Step 5: Extend the shared stylesheet**

Append to `static/core/css/base.css`:
```css
.pantau-purpose-banner { padding: 10px 24px; background: #EAF4F5; border-bottom: 1px solid #D3E8EA; font: 400 11px/1.6 'IBM Plex Sans', sans-serif; color: #0B4A52; }
.pantau-kpi-row-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.pantau-kpi-positive { color: var(--positive); }
.pantau-election-toggle { font: 600 13px 'IBM Plex Sans', sans-serif; color: var(--text-muted); margin: 10px 0 2px; }
.pantau-permission-row, .pantau-audit-row { display: grid; grid-template-columns: 1.4fr 1fr 1fr; gap: 10px; align-items: center; padding: 10px 0; border-bottom: 1px solid #F5F7F8; font: 500 12px 'IBM Plex Sans', sans-serif; }
.pantau-audit-row { grid-template-columns: 120px 1fr 1.3fr 110px; }
.pantau-policy-ack { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
```

- [ ] **Step 6: Run the test, verify it passes**

Run: `python manage.py test apps.governance.tests.test_views -v 2`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add apps/governance/views.py templates/governance/pengawasan.html static/core/css/base.css apps/governance/tests/test_views.py
git commit -m "Implement Dasbor Pengawasan view: permission roster, audit log, policy acknowledgment"
```

---

### Task 18: `seed_demo_data` orchestration command

**Files:**
- Create: `apps/core/management/__init__.py`
- Create: `apps/core/management/commands/__init__.py`
- Create: `apps/core/management/commands/seed_demo_data.py`
- Create: `apps/core/tests/test_seed_demo_data.py`

**Interfaces:**
- Consumes: `apps.core.seed.seed_core` (Task 3), `apps.analytics.seed.seed_analytics` (Task 6), `apps.coordination.seed.seed_coordination` (Task 10), `apps.governance.seed.seed_governance` (Task 8).
- Produces: `python manage.py seed_demo_data` — idempotent, safe to re-run.

- [ ] **Step 1: Write the failing test**

`apps/core/tests/test_seed_demo_data.py`:
```python
from django.core.management import call_command
from django.test import TestCase

from apps.analytics.models import Mention
from apps.coordination.models import CoordinationCluster
from apps.governance.models import AuditLogEntry


class SeedDemoDataCommandTest(TestCase):
    def test_command_populates_all_apps(self):
        call_command("seed_demo_data")
        self.assertGreater(Mention.objects.count(), 1000)
        self.assertEqual(CoordinationCluster.objects.count(), 4)
        self.assertGreater(AuditLogEntry.objects.count(), 0)

    def test_command_is_idempotent(self):
        call_command("seed_demo_data")
        first_count = Mention.objects.count()
        call_command("seed_demo_data")
        self.assertEqual(Mention.objects.count(), first_count)
```

- [ ] **Step 2: Run the test, verify it fails**

Run: `python manage.py test apps.core.tests.test_seed_demo_data -v 2`
Expected: FAIL — `django.core.management.base.CommandError: Unknown command: 'seed_demo_data'`

- [ ] **Step 3: Write the command**

`apps/core/management/__init__.py`: empty file.
`apps/core/management/commands/__init__.py`: empty file.
`apps/core/management/commands/seed_demo_data.py`:
```python
from django.core.management.base import BaseCommand

from apps.analytics.seed import seed_analytics
from apps.coordination.seed import seed_coordination
from apps.core.seed import seed_core
from apps.governance.seed import seed_governance


class Command(BaseCommand):
    help = "Populate the database with fictional demo data for the PANTAU dashboard."

    def handle(self, *args, **options):
        tenant, project = seed_core()
        self.stdout.write(self.style.SUCCESS(f"Core reference data ready ({tenant.name} / {project.name})"))

        seed_analytics(project)
        self.stdout.write(self.style.SUCCESS("Analytics mentions, coalitions, issue, and alerts seeded"))

        seed_coordination()
        self.stdout.write(self.style.SUCCESS("Coordination clusters seeded"))

        seed_governance(tenant)
        self.stdout.write(self.style.SUCCESS("Governance integrations, permissions, and audit log seeded"))

        self.stdout.write(self.style.SUCCESS("seed_demo_data complete."))
```

- [ ] **Step 4: Run the test, verify it passes**

Run: `python manage.py test apps.core.tests.test_seed_demo_data -v 2`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/core/management apps/core/tests/test_seed_demo_data.py
git commit -m "Add seed_demo_data management command orchestrating all four apps' seeders"
```

---

### Task 19: Final nav verification and full-suite smoke test

**Files:**
- Create: `apps/core/tests/test_full_flow.py`

**Interfaces:**
- Consumes: everything from Tasks 1–18. No production code changes — this task only adds an end-to-end regression test and runs the full suite.

- [ ] **Step 1: Write the full-flow test**

`apps/core/tests/test_full_flow.py`:
```python
from django.core.management import call_command
from django.test import TestCase


class FullFlowSmokeTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo_data")

    def test_all_seven_screens_render_with_seeded_data(self):
        checks = [
            ("/ringkasan/", "Total Sebutan"),
            ("/war-room/", "WAR ROOM NARASI"),
            ("/narasi/", "Pangsa Suara"),
            ("/regional/", "Distribusi Narasi Regional"),
            ("/koordinasi/", "Deteksi Perilaku"),
            ("/konfigurasi/", "Konsol Konfigurasi"),
            ("/pengawasan/", "Dasbor Pengawasan"),
        ]
        for path, expected_text in checks:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertContains(response, expected_text, msg_prefix=path)

    def test_disabled_nav_items_have_no_route(self):
        response = self.client.get("/ringkasan/")
        content = response.content.decode()
        self.assertIn("Umpan Sebutan", content)
        self.assertNotIn('href="/umpan-sebutan/"', content)
```

- [ ] **Step 2: Run the new test, verify it passes**

Run: `python manage.py test apps.core.tests.test_full_flow -v 2`
Expected: PASS. If any screen 404s or is missing its expected text, the regression is in whichever task built that screen — go back and fix it there, not here.

- [ ] **Step 3: Run the entire test suite**

Run: `python manage.py test`
Expected: All tests across `apps.core`, `apps.analytics`, `apps.coordination`, `apps.governance` PASS.

- [ ] **Step 4: Manual verification**

Run:
```bash
python manage.py seed_demo_data
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` and confirm it redirects to Ringkasan, the sidebar highlights the active screen, all 7 links work, War Room renders the dark kiosk layout without the sidebar, and Deteksi Koordinasi's "Tandai organik" button visibly updates the cluster's badge after a page reload.

- [ ] **Step 5: Commit**

```bash
git add apps/core/tests/test_full_flow.py
git commit -m "Add end-to-end smoke test covering all 7 screens against seeded data"
```

---

## Execution Notes

- Tasks 1–4 must run in order (each depends on the previous). Tasks 5–6 (analytics), 7–8 (governance) can run in either order relative to each other, but both must complete before Task 9 (coordination models depend on `analytics.PoliticalIssue`; coordination's later review actions in Task 15 depend on `governance.services.record_audit_entry`). Task 10 (coordination seed) depends on Task 6 (analytics seed) having created the political issue. Tasks 11–17 (the seven screen views) each depend only on their respective app's models/seed being done, but Task 12 (War Room) additionally depends on Task 9/10 (coordination) for cluster counts and spreader data. Tasks 18–19 depend on everything before them.
- Every `seed_*` function takes the pattern "no-op if data already exists" — this is what makes `seed_demo_data` safe to re-run and what the idempotency tests check. Don't break this pattern when extending seed data later.
- `docs/design/pantau/screen_1a.html` .. `screen_1g.html` are the visual source of truth for spacing, colors, and copy in each template — when a template step above says "port the structure," open the corresponding reference file rather than guessing at values.
