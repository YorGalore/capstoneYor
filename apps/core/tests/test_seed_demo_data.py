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
