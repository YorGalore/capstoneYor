from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.core.models import AnalystProfile, PagePermission, Tenant
from apps.core.permissions import (
    DEV_OPS_PAGE,
    PAGES,
    can_access,
    is_reserved,
    seed_permission_matrix,
)

User = get_user_model()
R = AnalystProfile


class DefaultMatrixTest(TestCase):
    def test_super_admin_can_access_every_page(self):
        for page, _label in PAGES:
            self.assertTrue(can_access(R.ROLE_SUPER_ADMIN, page), page)

    def test_analyst_denied_konfigurasi_by_default(self):
        self.assertFalse(can_access(R.ROLE_ANALYST, "konfigurasi"))

    def test_analyst_can_access_dashboard_by_default(self):
        self.assertTrue(can_access(R.ROLE_ANALYST, "ringkasan"))

    def test_viewer_denied_export_by_default(self):
        self.assertFalse(can_access(R.ROLE_VIEWER, "export"))

    def test_dev_ops_page_is_super_admin_only(self):
        self.assertFalse(can_access(R.ROLE_TENANT_ADMIN, DEV_OPS_PAGE))
        self.assertTrue(can_access(R.ROLE_SUPER_ADMIN, DEV_OPS_PAGE))

    def test_dev_ops_page_reserved_for_non_super_roles(self):
        self.assertTrue(is_reserved(R.ROLE_SUPER_ADMIN, "ringkasan"))
        self.assertTrue(is_reserved(R.ROLE_TENANT_ADMIN, DEV_OPS_PAGE))
        self.assertFalse(is_reserved(R.ROLE_TENANT_ADMIN, "konfigurasi"))


class MatrixOverrideTest(TestCase):
    def test_explicit_row_overrides_default(self):
        # By default analyst cannot access konfigurasi; grant it via the matrix.
        PagePermission.objects.create(
            role=R.ROLE_ANALYST, page="konfigurasi", can_access=True
        )
        self.assertTrue(can_access(R.ROLE_ANALYST, "konfigurasi"))

    def test_explicit_deny_row_overrides_default(self):
        PagePermission.objects.create(
            role=R.ROLE_ANALYST, page="ringkasan", can_access=False
        )
        self.assertFalse(can_access(R.ROLE_ANALYST, "ringkasan"))

    def test_reserved_dev_ops_cannot_be_granted_via_matrix(self):
        # Even with an explicit allow row, a non-super role never reaches dev/ops.
        PagePermission.objects.create(
            role=R.ROLE_TENANT_ADMIN, page=DEV_OPS_PAGE, can_access=True
        )
        self.assertFalse(can_access(R.ROLE_TENANT_ADMIN, DEV_OPS_PAGE))


class SeedMatrixTest(TestCase):
    def test_seed_is_idempotent_and_populates_editable_cells(self):
        seed_permission_matrix()
        first = PagePermission.objects.count()
        self.assertGreater(first, 0)
        seed_permission_matrix()
        self.assertEqual(PagePermission.objects.count(), first)
