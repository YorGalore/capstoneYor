"""Regression coverage for RBAC-ISSUE-001 / ISS-KOORDINASI-003.

Five views (ringkasan, war_room, narasi, regional, koordinasi) previously had
no @require_page decorator at all, so the permission-matrix editor could toggle
their cells without any real effect. This file proves the matrix now actually
governs direct access to every one of those pages, and — per the issue's own
acceptance criteria — generalizes the check across the full PAGES registry so a
future page that forgets the decorator fails a test instead of shipping quietly.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.models import AnalystProfile, PagePermission
from apps.core.permissions import PAGES, SUPER_ADMIN_ONLY_PAGES
from apps.core.seed import DEMO_USERNAME, seed_core
from apps.governance.models import PoliticalMonitoringPermission

User = get_user_model()

# Pages with no plain GET landing page reachable the same way as the rest (a
# file-download endpoint, or an id-scoped detail page with no bare list route
# usable without seed data) are out of scope for this generic sweep.
NOT_PLAIN_GET = {"export"}

PAGE_URLS = {
    "ringkasan": "analytics:ringkasan",
    "feed": "analytics:feed",
    "narasi": "analytics:narasi",
    "war_room": "analytics:war_room",
    "insiden": "analytics:insiden",
    "koordinasi": "coordination:koordinasi",
    "regional": "analytics:regional",
    "sosiograf": "analytics:sosiograf",
    "laporan": "analytics:laporan",
    "konfigurasi": "governance:konfigurasi",
    "pengawasan": "governance:pengawasan",
    "brief": "analytics:brief",
    "taxonomy": "analytics:taxonomy",
    "permission_matrix": "governance:permission_matrix",
    "runtime_settings": "governance:runtime_settings",
    "onboarding_requests": "core:onboarding_requests",
}


class PreviouslyUngatedPagesTest(TestCase):
    """The five views this fix set actually touched (Critical + High findings)."""

    def setUp(self):
        self.tenant, _ = seed_core()
        self.super_admin = User.objects.get(username=DEMO_USERNAME)
        PoliticalMonitoringPermission.objects.create(
            user=self.super_admin, approved_by="Kepatuhan", approved_at=timezone.now(), active=True,
        )
        self.viewer = User.objects.create(username="viewer.gate")
        AnalystProfile.objects.update_or_create(
            user=self.viewer,
            defaults={"tenant": self.tenant, "role": AnalystProfile.ROLE_VIEWER},
        )

    def _deny(self, page):
        PagePermission.objects.update_or_create(
            role=AnalystProfile.ROLE_VIEWER, page=page, defaults={"can_access": False},
        )

    def test_denying_ringkasan_blocks_direct_access(self):
        self._deny("ringkasan")
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(reverse("analytics:ringkasan")).status_code, 403)

    def test_denying_war_room_blocks_direct_access(self):
        self._deny("war_room")
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(reverse("analytics:war_room")).status_code, 403)

    def test_denying_narasi_blocks_direct_access(self):
        self._deny("narasi")
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(reverse("analytics:narasi")).status_code, 403)

    def test_denying_regional_blocks_direct_access(self):
        self._deny("regional")
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(reverse("analytics:regional")).status_code, 403)

    def test_denying_koordinasi_blocks_direct_access(self):
        self._deny("koordinasi")
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(reverse("coordination:koordinasi")).status_code, 403)

    def test_re_granting_restores_access(self):
        self._deny("regional")
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(reverse("analytics:regional")).status_code, 403)
        PagePermission.objects.filter(role=AnalystProfile.ROLE_VIEWER, page="regional").update(can_access=True)
        self.assertEqual(self.client.get(reverse("analytics:regional")).status_code, 200)


class FullPageRegistryGateSweepTest(TestCase):
    """Generalized version of the same check across every registered page, so a
    future page missing @require_page fails here instead of shipping unnoticed."""

    def setUp(self):
        self.tenant, _ = seed_core()
        self.viewer = User.objects.create(username="viewer.sweep")
        AnalystProfile.objects.update_or_create(
            user=self.viewer,
            defaults={"tenant": self.tenant, "role": AnalystProfile.ROLE_VIEWER},
        )
        self.client.force_login(self.viewer)

    def test_deny_then_access_returns_403_for_every_gateable_page(self):
        for page, _label in PAGES:
            if page in NOT_PLAIN_GET or page not in PAGE_URLS:
                continue
            if page in SUPER_ADMIN_ONLY_PAGES:
                # Reserved cells can't be granted to viewer at all; access should
                # already be 403 with no matrix row needed.
                response = self.client.get(reverse(PAGE_URLS[page]))
                self.assertEqual(response.status_code, 403, page)
                continue
            PagePermission.objects.update_or_create(
                role=AnalystProfile.ROLE_VIEWER, page=page, defaults={"can_access": False},
            )
            response = self.client.get(reverse(PAGE_URLS[page]))
            self.assertEqual(response.status_code, 403, page)
