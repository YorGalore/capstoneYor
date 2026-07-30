"""Migration 0012 must leave every Apify integration addressable.

Runs the real migration against a database migrated back to 0011, because the whole
point of the change is what happens to rows that already exist in a deployment.
"""
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from apps.core.models import Platform, Project, Tenant

APP = "governance"
BEFORE = "0011_manualcollectionrequest_history_window"
AFTER = "0012_repair_apify_actor_references"


class RepairApifyActorReferencesTest(TransactionTestCase):
    def _migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate([(APP, target)])
        return executor

    def tearDown(self):
        self._migrate(AFTER)

    def test_unusable_references_are_replaced_and_valid_ones_kept(self):
        executor = self._migrate(BEFORE)
        # Only `governance` is rolled back, so `core` rows are created through the
        # real models; the historical registry supplies the integration itself.
        apps = executor.loader.project_state((APP, BEFORE)).apps
        PlatformIntegration = apps.get_model(APP, "PlatformIntegration")

        tenant = Tenant.objects.create(name="Instansi A")
        project = Project.objects.create(tenant=tenant, name="Proyek A")
        rows = {
            # slug, method, stored actor_id
            "instagram": ("apify", "culc72xb7MP3EbaeX"),      # stale object ID
            "tiktok": ("apify", "clockworks/tiktok-scraper"),  # console path
            "youtube": ("apify", "streamers~youtube-scraper"),  # already correct
            "facebook": ("apify", "myteam/private-fb-scraper"),  # tenant's own Actor
            "x": ("internal", "scraper internal v2.4.1"),      # not an Actor at all
        }
        for slug, (method, actor_id) in rows.items():
            platform = Platform.objects.create(
                slug=slug, display_name=slug, method=method
            )
            PlatformIntegration.objects.create(
                project_id=project.pk, platform_id=platform.pk,
                method=method, actor_id=actor_id,
            )

        self._migrate(AFTER)

        stored = dict(
            PlatformIntegration.objects.values_list("platform__slug", "actor_id")
        )
        self.assertEqual(stored["instagram"], "apify~instagram-scraper")
        self.assertEqual(stored["tiktok"], "clockworks~tiktok-scraper")
        self.assertEqual(stored["youtube"], "streamers~youtube-scraper")
        self.assertEqual(stored["facebook"], "myteam~private-fb-scraper")
        self.assertEqual(stored["x"], "scraper internal v2.4.1")
