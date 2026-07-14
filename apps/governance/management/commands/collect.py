"""Manual, on-demand collection cycle (REQ-SC-04). Resolves the active Apify token
and the first project, then runs the Apify orchestrator across enabled platforms.
"""
from django.core.management.base import BaseCommand

from apps.core.models import Project
from apps.governance import apify, orchestrator


class Command(BaseCommand):
    help = "Run an Apify collection cycle across enabled platforms for active keywords."

    def add_arguments(self, parser):
        parser.add_argument("--project-id", type=int, default=None)

    def handle(self, *args, **options):
        project = (
            Project.objects.filter(id=options["project_id"]).first()
            if options["project_id"]
            else Project.objects.first()
        )
        if project is None:
            self.stderr.write("Tidak ada proyek. Jalankan seed_demo_data dulu.")
            return

        token = apify.get_active_token()
        if not token:
            self.stderr.write("Tidak ada token Apify aktif — atur di halaman Dev/Ops.")
            return

        runs = orchestrator.run_apify_collection(project, token)
        if not runs:
            self.stdout.write("Tidak ada platform/kata kunci aktif untuk dikumpulkan.")
            return
        for run in runs:
            self.stdout.write(
                f"{run.source}: {run.status} — {run.items_found} item "
                f"(≈${run.cost_estimate})"
            )
        self.stdout.write(self.style.SUCCESS("Siklus koleksi selesai."))
