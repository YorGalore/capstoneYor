from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class ProjectScopedAlertsMigrationTest(TransactionTestCase):
    migrate_from = [("analytics", "0011_politicalissue_project")]
    migrate_to = [("analytics", "0012_project_scoped_alerts")]

    def test_global_rules_are_copied_and_alerts_follow_their_issue_project(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        old_apps = executor.loader.project_state(self.migrate_from).apps

        Tenant = old_apps.get_model("core", "Tenant")
        Project = old_apps.get_model("core", "Project")
        AlertRule = old_apps.get_model("analytics", "AlertRule")
        Alert = old_apps.get_model("analytics", "Alert")
        PoliticalIssue = old_apps.get_model("analytics", "PoliticalIssue")

        tenant_a = Tenant.objects.create(name="Instansi A")
        tenant_b = Tenant.objects.create(name="Instansi B")
        project_a = Project.objects.create(tenant=tenant_a, name="Proyek A")
        project_b = Project.objects.create(tenant=tenant_b, name="Proyek B")
        rule = AlertRule.objects.create(
            name="Legacy global rule",
            condition_summary="Negative > 50%",
            channel="email",
            condition_type="negative_ratio",
            threshold=0.5,
            window_minutes=60,
            is_active=True,
        )
        issue_b = PoliticalIssue.objects.create(
            project=project_b,
            title="Issue B",
            opened_at=timezone.now(),
            owner_label="Humas B",
        )
        Alert.objects.create(
            rule=rule,
            issue=issue_b,
            severity="warning",
            title="Legacy alert",
            detail="breached",
            triggered_at=timezone.now(),
            status="active",
        )

        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        new_apps = executor.loader.project_state(self.migrate_to).apps
        NewAlertRule = new_apps.get_model("analytics", "AlertRule")
        NewAlert = new_apps.get_model("analytics", "Alert")

        self.assertEqual(
            set(NewAlertRule.objects.values_list("project_id", flat=True)),
            {project_a.pk, project_b.pk},
        )
        migrated_alert = NewAlert.objects.get(title="Legacy alert")
        self.assertEqual(migrated_alert.project_id, project_b.pk)
        self.assertEqual(migrated_alert.rule.project_id, project_b.pk)
