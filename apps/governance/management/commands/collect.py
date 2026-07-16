"""Manual on-demand collection for online news and configured social sources."""

from django.core.management.base import BaseCommand

from apps.core.models import Project
from apps.governance import apify, orchestrator


class Command(BaseCommand):
    help = "Run online-news crawlers and available Apify social collectors."

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

        runs = orchestrator.run_news_collection(project)
        token = apify.get_active_token(project)
        if token:
            runs += orchestrator.run_apify_collection(project, token)
        else:
            self.stderr.write(
                "Tidak ada token Apify aktif — koleksi berita tetap dijalankan; "
                "sumber sosial dilewati."
            )

        if not runs:
            self.stdout.write("Tidak ada sumber/kata kunci aktif untuk dikumpulkan.")
            return
        for run in runs:
            self.stdout.write(
                f"{run.source}: {run.status} - {run.items_found} item "
                f"(~${run.cost_estimate})"
            )
        self.stdout.write(self.style.SUCCESS("Siklus koleksi selesai."))
