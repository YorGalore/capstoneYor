"""Generate the daily executive brief for H-1 (FR-30.1/30.6).

Safe to run on a schedule: the DB-level status claim means a scheduled run and a
manual run arriving together cannot produce duplicate output.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.analytics import briefs
from apps.core.models import Project


class Command(BaseCommand):
    help = "Generate the H-1 daily executive brief as a draft pending human review."

    def add_arguments(self, parser):
        parser.add_argument("--date", type=str, default=None, help="YYYY-MM-DD (default: yesterday)")

    def handle(self, *args, **options):
        project = Project.objects.first()
        if project is None:
            self.stderr.write("Tidak ada proyek.")
            return

        brief_date = (
            parse_date(options["date"]) if options["date"]
            else (timezone.now() - timezone.timedelta(days=1)).date()
        )
        try:
            brief = briefs.generate(project, brief_date, triggered_by="terjadwal")
        except briefs.BriefAlreadyGenerating:
            self.stdout.write("Pembuatan untuk tanggal ini sedang berjalan — dilewati.")
            return
        except briefs.BriefLocked:
            self.stdout.write("Brief sudah final — tidak dibuat ulang.")
            return

        for item in brief.issues.all():
            self.stdout.write(
                f"  [{item.risk_level}] {item.title} — {item.mention_count} sebutan, "
                f"{item.negative_pct}% negatif, {len(item.regulatory_context)} rujukan regulasi"
            )
        self.stdout.write(self.style.SUCCESS(
            f"Draf brief {brief_date}: {brief.issues.count()} isu — MENUNGGU TINJAUAN MANUSIA."
        ))
