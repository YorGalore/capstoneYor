"""Tests for the cadence scheduler (REQ-SC-01, REQ-SC-02, REQ-SC-05).

The platform is deployed but nothing runs on its own: collection, alerting, brief
generation and CIB detection all wait for a human to type a management command. This
module is what makes the monitoring platform actually monitor.
"""
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from apps.core.models import Platform, Project, Tenant
from apps.governance import scheduling
from apps.governance.models import ScheduledJob


def minutes_ago(n):
    return timezone.now() - timezone.timedelta(minutes=n)


class DueJobTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")

    def _job(self, **kwargs):
        defaults = {
            "project": self.project,
            "job_type": ScheduledJob.JOB_EVALUATE_ALERTS,
            "cadence_minutes": 15,
            "enabled": True,
            "next_run_at": minutes_ago(1),
        }
        defaults.update(kwargs)
        return ScheduledJob.objects.create(**defaults)

    def test_a_job_whose_time_has_come_is_due(self):
        job = self._job(next_run_at=minutes_ago(1))
        self.assertIn(job, list(scheduling.due_jobs()))

    def test_a_job_scheduled_for_the_future_is_not_due(self):
        self._job(next_run_at=timezone.now() + timezone.timedelta(minutes=10))
        self.assertEqual(list(scheduling.due_jobs()), [])

    def test_a_disabled_job_is_never_due(self):
        # Disabling is the operator's off switch; it has to actually stop the work.
        self._job(enabled=False, next_run_at=minutes_ago(60))
        self.assertEqual(list(scheduling.due_jobs()), [])


class RunDueTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        self.job = ScheduledJob.objects.create(
            project=self.project,
            job_type=ScheduledJob.JOB_EVALUATE_ALERTS,
            cadence_minutes=15,
            next_run_at=minutes_ago(1),
        )

    def test_running_a_due_job_invokes_its_handler(self):
        handler = mock.Mock(return_value="2 peringatan")
        with mock.patch.dict(scheduling.HANDLERS, {ScheduledJob.JOB_EVALUATE_ALERTS: handler}):
            results = scheduling.run_due()
        handler.assert_called_once_with(self.project)
        self.assertEqual(len(results), 1)

    def test_a_successful_run_is_recorded_and_rescheduled(self):
        with mock.patch.dict(
            scheduling.HANDLERS, {ScheduledJob.JOB_EVALUATE_ALERTS: mock.Mock(return_value="ok")}
        ):
            scheduling.run_due()
        self.job.refresh_from_db()
        self.assertEqual(self.job.last_status, ScheduledJob.STATUS_OK)
        self.assertIsNotNone(self.job.last_run_at)
        self.assertGreater(self.job.next_run_at, timezone.now())
        self.assertEqual(self.job.consecutive_failures, 0)

    def test_a_failing_job_records_the_error_and_keeps_running_later(self):
        # A handler that raises must not kill the scheduler loop, and must not silently
        # disappear: the failure has to be visible on the job itself.
        handler = mock.Mock(side_effect=RuntimeError("apify ditolak"))
        with mock.patch.dict(scheduling.HANDLERS, {ScheduledJob.JOB_EVALUATE_ALERTS: handler}):
            scheduling.run_due()
        self.job.refresh_from_db()
        self.assertEqual(self.job.last_status, ScheduledJob.STATUS_FAILED)
        self.assertIn("apify ditolak", self.job.last_error)
        self.assertEqual(self.job.consecutive_failures, 1)

    def test_one_failing_job_does_not_stop_the_others(self):
        other = ScheduledJob.objects.create(
            project=self.project,
            job_type=ScheduledJob.JOB_DETECT_COORDINATION,
            cadence_minutes=30,
            next_run_at=minutes_ago(1),
        )
        good = mock.Mock(return_value="ok")
        with mock.patch.dict(
            scheduling.HANDLERS,
            {
                ScheduledJob.JOB_EVALUATE_ALERTS: mock.Mock(side_effect=RuntimeError("boom")),
                ScheduledJob.JOB_DETECT_COORDINATION: good,
            },
        ):
            scheduling.run_due()
        good.assert_called_once()
        other.refresh_from_db()
        self.assertEqual(other.last_status, ScheduledJob.STATUS_OK)

    def test_repeated_failures_back_off_instead_of_hammering(self):
        """A dead upstream (expired Apify token, network down) must not be retried every
        cadence forever — that burns quota and floods the log while fixing nothing."""
        handler = mock.Mock(side_effect=RuntimeError("upstream mati"))
        with mock.patch.dict(scheduling.HANDLERS, {ScheduledJob.JOB_EVALUATE_ALERTS: handler}):
            scheduling.run_due()
            first = ScheduledJob.objects.get(pk=self.job.pk).next_run_at

            ScheduledJob.objects.filter(pk=self.job.pk).update(next_run_at=minutes_ago(1))
            scheduling.run_due()
            second = ScheduledJob.objects.get(pk=self.job.pk).next_run_at

        job = ScheduledJob.objects.get(pk=self.job.pk)
        self.assertEqual(job.consecutive_failures, 2)
        # The second backoff must be further out than the first.
        self.assertGreater(
            second - timezone.now(), first - self.job.next_run_at
        )

    def test_a_missed_window_runs_once_rather_than_replaying_every_slot(self):
        """If the scheduler was down for a day, a 15-minute job is 96 windows overdue.
        Catching up would fire 96 collection runs at once — a self-inflicted stampede
        against Apify, and 96 duplicate briefs. The correct behavior is to run now and
        resume the normal cadence.
        """
        self.job.next_run_at = minutes_ago(24 * 60)
        self.job.save()
        handler = mock.Mock(return_value="ok")
        with mock.patch.dict(scheduling.HANDLERS, {ScheduledJob.JOB_EVALUATE_ALERTS: handler}):
            scheduling.run_due()
        self.assertEqual(handler.call_count, 1)
        self.job.refresh_from_db()
        self.assertGreater(self.job.next_run_at, timezone.now())

    def test_an_unknown_job_type_fails_the_job_rather_than_the_loop(self):
        ScheduledJob.objects.filter(pk=self.job.pk).update(job_type="tidak_dikenal")
        results = scheduling.run_due()
        self.assertEqual(len(results), 1)
        self.job.refresh_from_db()
        self.assertEqual(self.job.last_status, ScheduledJob.STATUS_FAILED)


class KillSwitchTest(TestCase):
    """REQ-LC-03: a fast, platform-wide stop on collection.

    The point of a kill switch is that it works when someone is panicking. It is checked
    at the moment work is about to happen, not when it was scheduled.
    """

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Instansi A")
        self.project = Project.objects.create(tenant=self.tenant, name="Proyek A")
        Platform.objects.create(slug="x", display_name="X", method=Platform.METHOD_APIFY)

    def test_collection_is_enabled_by_default(self):
        self.assertTrue(scheduling.collection_enabled())

    def test_disabling_collection_skips_a_due_collect_job(self):
        scheduling.set_collection_enabled(False, actor="Super Admin")
        job = ScheduledJob.objects.create(
            project=self.project,
            job_type=ScheduledJob.JOB_COLLECT,
            cadence_minutes=30,
            next_run_at=minutes_ago(1),
        )
        handler = mock.Mock()
        with mock.patch.dict(scheduling.HANDLERS, {ScheduledJob.JOB_COLLECT: handler}):
            scheduling.run_due()

        handler.assert_not_called()
        job.refresh_from_db()
        self.assertEqual(job.last_status, ScheduledJob.STATUS_SKIPPED)

    def test_the_kill_switch_does_not_stop_non_collection_work(self):
        # Stopping collection must not also blind the analysts: alerting and briefs run
        # over data already held, and that is exactly what people need during an incident.
        scheduling.set_collection_enabled(False, actor="Super Admin")
        ScheduledJob.objects.create(
            project=self.project,
            job_type=ScheduledJob.JOB_EVALUATE_ALERTS,
            cadence_minutes=15,
            next_run_at=minutes_ago(1),
        )
        handler = mock.Mock(return_value="ok")
        with mock.patch.dict(scheduling.HANDLERS, {ScheduledJob.JOB_EVALUATE_ALERTS: handler}):
            scheduling.run_due()
        handler.assert_called_once()

    def test_toggling_the_kill_switch_is_audited(self):
        # Halting collection for an entire institution is exactly the kind of act that
        # must have a name and a timestamp against it.
        from apps.governance.models import AuditLogEntry

        scheduling.set_collection_enabled(False, actor="Dewi Anjani")
        entry = AuditLogEntry.objects.first()
        self.assertIn("Dewi Anjani", entry.actor_label)
        self.assertIn("koleksi", entry.action.lower())

    def test_re_enabling_restores_collection(self):
        scheduling.set_collection_enabled(False, actor="a")
        scheduling.set_collection_enabled(True, actor="a")
        self.assertTrue(scheduling.collection_enabled())

    def test_the_kill_switch_also_stops_a_manual_collection_run(self):
        """A kill switch that only the scheduler honors is not a kill switch.

        `manage.py collect` and the console's "Pindai" button both call the orchestrator
        directly. If the halt is only enforced in the scheduler, the very next person to
        press the button restarts the collection the institution just decided to stop.
        """
        from apps.governance import orchestrator
        from apps.governance.models import MonitoringKeyword, PlatformIntegration

        platform = Platform.objects.get(slug="x")
        PlatformIntegration.objects.create(
            project=self.project, platform=platform,
            method=PlatformIntegration.METHOD_APIFY, is_active=True
        )
        MonitoringKeyword.objects.create(project=self.project, keyword="pangan", is_active=True)
        scheduling.set_collection_enabled(False, actor="Super Admin")

        with mock.patch.object(orchestrator.apify_crawler, "collect") as collect:
            runs = orchestrator.run_apify_collection(self.project, token="tok")

        collect.assert_not_called()
        self.assertEqual(runs, [])
