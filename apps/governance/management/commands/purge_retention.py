"""Apply the data retention policy (REQ-LC-01, REQ-LC-02).

Defaults to a dry run. This is the only command in the platform that destroys data, and
it is unrecoverable, so deleting has to be the thing you explicitly asked for.
"""
from django.core.management.base import BaseCommand

from apps.core.models import Project
from apps.governance import retention


class Command(BaseCommand):
    help = "Delete mentions past the retention window. Dry run unless --apply is given."

    def add_arguments(self, parser):
        parser.add_argument("--project-id", type=int, default=None)
        parser.add_argument(
            "--apply", action="store_true", help="Actually delete. Without this, only reports."
        )
        parser.add_argument("--actor", default="CLI")

    def handle(self, *args, **options):
        days = retention.retention_days()
        if days == retention.RETENTION_DISABLED:
            self.stdout.write(
                "Tidak ada kebijakan retensi (retention.days belum diatur) — tidak ada yang dihapus."
            )
            return

        projects = (
            Project.objects.filter(id=options["project_id"])
            if options["project_id"]
            else Project.objects.all()
        )

        dry_run = not options["apply"]
        for project in projects:
            result = retention.purge(
                project, dry_run=dry_run, actor=options["actor"]
            )
            verb = "akan dihapus" if dry_run else "dihapus"
            self.stdout.write(
                f"{project.name}: {result['deleted']} sebutan {verb}, "
                f"{result['protected']} dilindungi (investigasi terbuka) "
                f"— batas {result['cutoff']:%Y-%m-%d}"
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run. Jalankan dengan --apply untuk menghapus."))
        else:
            self.stdout.write(self.style.SUCCESS("Purge retensi selesai."))
