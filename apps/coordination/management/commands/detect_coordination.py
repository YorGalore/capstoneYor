"""Run the CIB detection engine over active issues (FR-26.1). Flags clusters for
human review; never takes automated action against any account (FR-26.2).
"""
from django.core.management.base import BaseCommand

from apps.analytics.models import PoliticalIssue
from apps.core.models import Project
from apps.coordination import detection


class Command(BaseCommand):
    help = "Score mentions for coordinated inauthentic behavior and flag clusters for review."

    def add_arguments(self, parser):
        parser.add_argument("--threshold", type=float, default=detection.DEFAULT_THRESHOLD)

    def handle(self, *args, **options):
        project = Project.objects.first()
        if project is None:
            self.stderr.write("Tidak ada proyek.")
            return

        total = 0
        for issue in PoliticalIssue.objects.filter(
            project=project, status=PoliticalIssue.STATUS_ACTIVE
        ):
            clusters = detection.detect(project, issue, threshold=options["threshold"])
            for cluster in clusters:
                self.stdout.write(
                    f"{cluster.cluster_code}: skor {cluster.score} · {cluster.account_count} akun "
                    f"— ditandai untuk tinjauan manusia"
                )
            total += len(clusters)
        self.stdout.write(self.style.SUCCESS(f"Deteksi selesai: {total} klaster ditandai."))
