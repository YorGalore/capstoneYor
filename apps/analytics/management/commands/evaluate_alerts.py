"""Evaluate alert rules against the current mention window (FR-12)."""
from django.core.management.base import BaseCommand

from apps.analytics import alerting
from apps.core.models import Project


class Command(BaseCommand):
    help = "Evaluate active alert rules and raise alerts on threshold breach."

    def handle(self, *args, **options):
        project = Project.objects.first()
        if project is None:
            self.stderr.write("Tidak ada proyek.")
            return
        triggered = alerting.evaluate_rules(project)
        for alert in triggered:
            self.stdout.write(f"[{alert.severity}] {alert.title}: {alert.detail}")
        self.stdout.write(self.style.SUCCESS(f"{len(triggered)} peringatan baru dipicu."))
