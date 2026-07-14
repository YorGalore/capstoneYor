"""Tests for the collection health view (REQ-CS-07).

A silently dead collector is the worst failure this platform has: the dashboards keep
rendering, the numbers keep looking plausible, and nobody notices that no new data has
arrived for a week. Health has to be legible without reading the run ledger by hand.
"""
from django.test import TestCase
from django.utils import timezone

from apps.governance import health
from apps.governance.models import CollectionRun


def run(source, status, minutes_ago=0, **kwargs):
    entry = CollectionRun.objects.create(source=source, status=status, **kwargs)
    when = timezone.now() - timezone.timedelta(minutes=minutes_ago)
    CollectionRun.objects.filter(pk=entry.pk).update(started_at=when, finished_at=when)
    return CollectionRun.objects.get(pk=entry.pk)


class CollectionHealthTest(TestCase):
    def test_a_source_with_recent_successes_is_healthy(self):
        run("x", CollectionRun.STATUS_COMPLETED, minutes_ago=5, items_found=40)
        run("x", CollectionRun.STATUS_COMPLETED, minutes_ago=35, items_found=32)

        report = {r["source"]: r for r in health.collection_health()}
        self.assertEqual(report["x"]["status"], health.HEALTHY)
        self.assertEqual(report["x"]["consecutive_failures"], 0)
        self.assertIsNotNone(report["x"]["last_success_at"])

    def test_consecutive_failures_since_the_last_success_are_counted(self):
        run("x", CollectionRun.STATUS_COMPLETED, minutes_ago=200)
        run("x", CollectionRun.STATUS_FAILED, minutes_ago=60, error="401")
        run("x", CollectionRun.STATUS_FAILED, minutes_ago=30, error="401")

        report = {r["source"]: r for r in health.collection_health()}
        self.assertEqual(report["x"]["consecutive_failures"], 2)
        self.assertEqual(report["x"]["last_error"], "401")

    def test_a_source_failing_repeatedly_is_reported_down(self):
        for i in range(health.DOWN_AFTER_FAILURES):
            run("x", CollectionRun.STATUS_FAILED, minutes_ago=10 * i, error="token kedaluwarsa")

        report = {r["source"]: r for r in health.collection_health()}
        self.assertEqual(report["x"]["status"], health.DOWN)

    def test_a_source_that_has_stopped_producing_is_not_reported_healthy(self):
        """The dangerous case: the last run "succeeded", so nothing looks broken — but it
        was days ago and no data has arrived since. A stale collector must not read as
        green just because it did not error.
        """
        run("x", CollectionRun.STATUS_COMPLETED, minutes_ago=int(health.STALE_AFTER_MINUTES) + 60)

        report = {r["source"]: r for r in health.collection_health()}
        self.assertEqual(report["x"]["status"], health.STALE)

    def test_a_skipped_run_is_not_treated_as_a_failure(self):
        # Overlap-skip is normal, healthy backpressure — not an error.
        run("x", CollectionRun.STATUS_COMPLETED, minutes_ago=20)
        run("x", CollectionRun.STATUS_SKIPPED, minutes_ago=5)

        report = {r["source"]: r for r in health.collection_health()}
        self.assertEqual(report["x"]["consecutive_failures"], 0)
        self.assertEqual(report["x"]["status"], health.HEALTHY)

    def test_sources_are_reported_independently(self):
        run("x", CollectionRun.STATUS_COMPLETED, minutes_ago=5)
        run("tiktok", CollectionRun.STATUS_FAILED, minutes_ago=5, error="rate limit")

        report = {r["source"]: r for r in health.collection_health()}
        self.assertEqual(report["x"]["status"], health.HEALTHY)
        self.assertNotEqual(report["tiktok"]["status"], health.HEALTHY)

    def test_a_source_that_never_ran_is_absent_rather_than_invented(self):
        self.assertEqual(health.collection_health(), [])
