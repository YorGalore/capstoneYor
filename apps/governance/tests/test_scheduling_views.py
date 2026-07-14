"""Tests for the scheduling and health UI on the Configuration Console.

A scheduler nobody can see is its own hazard: work happens on a cadence, costs Apify
credits, and deletes data, and an operator needs to be able to look at it and stop it
without an engineer and a shell.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.models import AnalystProfile, Platform, Project, Tenant
from apps.governance import scheduling
from apps.governance.models import CollectionRun, ScheduledJob


class SchedulingViewTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        Platform.objects.create(slug="x", display_name="X", method=Platform.METHOD_APIFY)

        user = get_user_model().objects.create_user(username="admin", password="pw12345678")
        AnalystProfile.objects.update_or_create(
            user=user,
            defaults={
                "tenant": self.tenant,
                "role": AnalystProfile.ROLE_SUPER_ADMIN,
                "role_label": "Super Admin",
            },
        )
        self.client.force_login(user)

        self.job = ScheduledJob.objects.create(
            project=self.project,
            job_type=ScheduledJob.JOB_EVALUATE_ALERTS,
            cadence_minutes=15,
        )

    def test_console_lists_the_schedule(self):
        response = self.client.get(reverse("governance:konfigurasi"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Evaluasi peringatan")

    def test_console_shows_collector_health(self):
        CollectionRun.objects.create(
            source="x", status=CollectionRun.STATUS_FAILED, error="token kedaluwarsa"
        )
        response = self.client.get(reverse("governance:konfigurasi"))
        self.assertContains(response, "token kedaluwarsa")

    def test_cadence_can_be_changed(self):
        self.client.post(
            reverse("governance:update_schedule", args=[self.job.pk]),
            {"cadence_minutes": "45", "enabled": "on"},
        )
        self.job.refresh_from_db()
        self.assertEqual(self.job.cadence_minutes, 45)
        self.assertTrue(self.job.enabled)

    def test_a_job_can_be_disabled_from_the_console(self):
        self.client.post(
            reverse("governance:update_schedule", args=[self.job.pk]),
            {"cadence_minutes": "15"},  # checkbox absent => disabled
        )
        self.job.refresh_from_db()
        self.assertFalse(self.job.enabled)

    def test_a_zero_cadence_is_rejected_rather_than_creating_a_hot_loop(self):
        # cadence 0 would make the job due again the instant it finishes, spending Apify
        # credits as fast as the scheduler can turn.
        self.client.post(
            reverse("governance:update_schedule", args=[self.job.pk]),
            {"cadence_minutes": "0", "enabled": "on"},
        )
        self.job.refresh_from_db()
        self.assertEqual(self.job.cadence_minutes, 15)

    def test_changing_a_cadence_is_audited(self):
        from apps.governance.models import AuditLogEntry

        self.client.post(
            reverse("governance:update_schedule", args=[self.job.pk]),
            {"cadence_minutes": "45", "enabled": "on"},
        )
        self.assertTrue(AuditLogEntry.objects.filter(action__icontains="jadwal").exists())

    def test_the_kill_switch_can_be_thrown_from_the_console(self):
        self.client.post(reverse("governance:toggle_collection"), {"enabled": "0"})
        self.assertFalse(scheduling.collection_enabled())

    def test_the_kill_switch_can_be_released_from_the_console(self):
        scheduling.set_collection_enabled(False, actor="x")
        self.client.post(reverse("governance:toggle_collection"), {"enabled": "1"})
        self.assertTrue(scheduling.collection_enabled())

    def test_the_console_says_when_collection_is_halted(self):
        # If collection is stopped, that has to be impossible to miss — otherwise someone
        # reads a flat trend line as calm public opinion rather than as no data.
        scheduling.set_collection_enabled(False, actor="x")
        response = self.client.get(reverse("governance:konfigurasi"))
        self.assertContains(response, "dihentikan", status_code=200)
