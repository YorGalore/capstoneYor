"""Manual on-demand collection for online news and configured social sources."""

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date

from apps.core.models import Project
from apps.governance import apify, orchestrator


class Command(BaseCommand):
    help = "Run online-news crawlers and available Apify social collectors."

    def add_arguments(self, parser):
        parser.add_argument("--project-id", type=int, default=None)
        parser.add_argument("--history-from", default=None)
        parser.add_argument("--history-to", default=None)
        parser.add_argument("--max-results", type=int, default=100)
        parser.add_argument(
            "--platform",
            action="append",
            choices=orchestrator.apify_crawler.supported_platforms(),
            help="Limit social collection to one or more platform slugs.",
        )
        parser.add_argument(
            "--social-only",
            action="store_true",
            help="Skip online-news collection.",
        )

    def handle(self, *args, **options):
        project = (
            Project.objects.filter(id=options["project_id"]).first()
            if options["project_id"]
            else Project.objects.first()
        )
        if project is None:
            self.stderr.write("Tidak ada proyek. Jalankan seed_demo_data dulu.")
            return

        start_date = parse_date(options["history_from"] or "")
        end_date = parse_date(options["history_to"] or "")
        if bool(start_date) != bool(end_date):
            self.stderr.write(
                self.style.ERROR("--history-from dan --history-to harus dipakai bersama.")
            )
            return
        if start_date and start_date > end_date:
            self.stderr.write(self.style.ERROR("Rentang tanggal historis tidak valid."))
            return
        if start_date and (end_date - start_date).days >= 31:
            self.stderr.write(self.style.ERROR("Backfill dibatasi maksimal 31 hari."))
            return

        runs = [] if options["social_only"] else orchestrator.run_news_collection(project)
        token = apify.get_active_token(project)
        if token:
            runs += orchestrator.run_apify_collection(
                project,
                token,
                platforms=options["platform"] or None,
                start_date=start_date,
                end_date=end_date,
                max_results=(
                    min(max(options["max_results"], 1), 500)
                    if start_date else None
                ),
            )
        else:
            self.stderr.write(
                "Tidak ada token Apify proyek atau fallback environment — "
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
