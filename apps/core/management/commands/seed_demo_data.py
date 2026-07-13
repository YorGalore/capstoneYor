from django.core.management.base import BaseCommand

from apps.analytics.seed import seed_analytics
from apps.coordination.seed import seed_coordination
from apps.core.seed import seed_core
from apps.governance.seed import seed_governance


class Command(BaseCommand):
    help = "Populate the database with fictional demo data for the PANTAU dashboard."

    def handle(self, *args, **options):
        tenant, project = seed_core()
        self.stdout.write(self.style.SUCCESS(f"Core reference data ready ({tenant.name} / {project.name})"))

        seed_analytics(project)
        self.stdout.write(self.style.SUCCESS("Analytics mentions, coalitions, issue, and alerts seeded"))

        seed_coordination()
        self.stdout.write(self.style.SUCCESS("Coordination clusters seeded"))

        seed_governance(tenant)
        self.stdout.write(self.style.SUCCESS("Governance integrations, permissions, and audit log seeded"))

        self.stdout.write(self.style.SUCCESS("seed_demo_data complete."))
