from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.analytics.models import Camp, PoliticalActor
from apps.core.models import AnalystProfile, Tenant, Project
from apps.core.seed import DEMO_USERNAME, seed_core
from apps.governance import neutrality
from apps.governance.models import PoliticalMonitoringPermission

User = get_user_model()


class PoliticalMonitoringGateTest(TestCase):
    """FR-29.1: political-actor tracking and camp comparison require an explicit
    Political Monitoring permission, separate from standard Analyst access."""

    def setUp(self):
        self.tenant, self.project = seed_core()
        self.analyst = User.objects.create(username="analis.polos")
        AnalystProfile.objects.update_or_create(
            user=self.analyst,
            defaults={"tenant": self.tenant, "role": AnalystProfile.ROLE_ANALYST},
        )

    def test_analyst_without_permission_denied_narasi(self):
        self.client.force_login(self.analyst)
        response = self.client.get(reverse("analytics:narasi"))
        self.assertEqual(response.status_code, 403)

    def test_analyst_with_active_permission_allowed(self):
        PoliticalMonitoringPermission.objects.create(
            user=self.analyst, approved_by="R. Hartono (Kepatuhan)",
            approved_at=timezone.now(), active=True,
        )
        self.client.force_login(self.analyst)
        response = self.client.get(reverse("analytics:narasi"))
        self.assertEqual(response.status_code, 200)

    def test_revoked_permission_denies_access_again(self):
        PoliticalMonitoringPermission.objects.create(
            user=self.analyst, approved_by="R. Hartono (Kepatuhan)",
            approved_at=timezone.now(), active=False, revoked_at=timezone.now(),
        )
        self.client.force_login(self.analyst)
        self.assertEqual(self.client.get(reverse("analytics:narasi")).status_code, 403)

    def test_political_query_is_audited(self):
        from apps.governance.models import AuditLogEntry

        PoliticalMonitoringPermission.objects.create(
            user=self.analyst, approved_by="Kepatuhan", approved_at=timezone.now(), active=True,
        )
        self.client.force_login(self.analyst)
        before = AuditLogEntry.objects.filter(action__icontains="kueri").count()

        self.client.get(reverse("analytics:narasi"))

        after = AuditLogEntry.objects.filter(action__icontains="kueri").count()
        self.assertEqual(after, before + 1)  # FR-29.2

    def test_neutrality_notice_shown_on_political_view(self):
        PoliticalMonitoringPermission.objects.create(
            user=self.analyst, approved_by="Kepatuhan", approved_at=timezone.now(), active=True,
        )
        self.client.force_login(self.analyst)
        response = self.client.get(reverse("analytics:narasi"))
        # FR-29.5: persistent purpose/prohibited-use notice
        self.assertContains(response, "pemantauan opini publik")


class PrivateIndividualProhibitionTest(TestCase):
    """FR-29.3: the data model must refuse to profile private individuals."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        self.camp = Camp.objects.create(project=self.project, name="Koalisi A")

    def test_rejects_actor_type_outside_public_allowlist(self):
        with self.assertRaises(ValidationError):
            neutrality.create_political_actor(
                project=self.project, name="Warga Biasa", actor_type="private_citizen",
                camp=self.camp,
            )

    def test_allows_public_official(self):
        actor = neutrality.create_political_actor(
            project=self.project, name="Menteri X", actor_type=PoliticalActor.TYPE_OFFICIAL,
            camp=self.camp,
        )
        self.assertEqual(actor.actor_type, PoliticalActor.TYPE_OFFICIAL)

    def test_private_handle_is_excluded_from_actor_tagging(self):
        # A personal account not registered as a public actor must never be tagged.
        self.assertTrue(neutrality.is_private_individual("@warga_pribadi_01", self.project))
        neutrality.create_political_actor(
            project=self.project, name="Partai Alfa", actor_type=PoliticalActor.TYPE_PARTY,
            camp=self.camp, handles=["@partaialfa"],
        )
        self.assertFalse(neutrality.is_private_individual("@partaialfa", self.project))


class ElectionModeTest(TestCase):
    """SRS 8.5: during an official campaign period, political-actor configuration is
    frozen and subject to heightened Compliance review."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        self.camp = Camp.objects.create(project=self.project, name="Koalisi A")

    def test_config_frozen_when_election_mode_on(self):
        neutrality.set_election_mode(True, updated_by="Kepatuhan")
        self.assertTrue(neutrality.election_mode_active())
        with self.assertRaises(neutrality.ElectionPeriodFrozen):
            neutrality.create_political_actor(
                project=self.project, name="Partai Baru",
                actor_type=PoliticalActor.TYPE_PARTY, camp=self.camp,
            )

    def test_config_allowed_when_election_mode_off(self):
        neutrality.set_election_mode(False, updated_by="Kepatuhan")
        self.assertFalse(neutrality.election_mode_active())
        actor = neutrality.create_political_actor(
            project=self.project, name="Partai Baru",
            actor_type=PoliticalActor.TYPE_PARTY, camp=self.camp,
        )
        self.assertTrue(actor.pk)
