"""Assign alert rules and alerts to projects (FR-1.2, FR-12).

Legacy rules were global. To preserve their behaviour without retaining cross-tenant
evaluation, each rule is copied to every existing project. Existing alerts follow
their political issue's project when that relationship is available.
"""
from django.db import migrations, models
import django.db.models.deletion


RULE_FIELDS = (
    "name",
    "condition_summary",
    "channel",
    "condition_type",
    "threshold",
    "window_minutes",
    "is_active",
)


def assign_projects(apps, schema_editor):
    Alert = apps.get_model("analytics", "Alert")
    AlertRule = apps.get_model("analytics", "AlertRule")
    Project = apps.get_model("core", "Project")

    projects = list(Project.objects.order_by("pk"))
    if not projects:
        if AlertRule.objects.exists() or Alert.objects.exists():
            raise RuntimeError("Cannot project-scope legacy alerts because no project exists.")
        return

    primary_project = projects[0]
    for original in list(AlertRule.objects.order_by("pk")):
        rules_by_project = {primary_project.pk: original}
        original.project_id = primary_project.pk
        original.save(update_fields=["project"])

        values = {field: getattr(original, field) for field in RULE_FIELDS}
        for project in projects[1:]:
            rules_by_project[project.pk] = AlertRule.objects.create(
                project_id=project.pk, **values
            )

        for alert in Alert.objects.filter(rule_id=original.pk).select_related("issue"):
            project_id = (
                alert.issue.project_id
                if alert.issue_id and alert.issue.project_id in rules_by_project
                else primary_project.pk
            )
            alert.project_id = project_id
            alert.rule_id = rules_by_project[project_id].pk
            alert.save(update_fields=["project", "rule"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_remove_analystprofile_has_political_monitoring_permission"),
        ("analytics", "0011_politicalissue_project"),
    ]

    operations = [
        migrations.AddField(
            model_name="alertrule",
            name="project",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="alert_rules",
                to="core.project",
            ),
        ),
        migrations.AddField(
            model_name="alert",
            name="project",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="alerts",
                to="core.project",
            ),
        ),
        migrations.RunPython(assign_projects, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="alertrule",
            name="project",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="alert_rules",
                to="core.project",
            ),
        ),
        migrations.AlterField(
            model_name="alert",
            name="project",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="alerts",
                to="core.project",
            ),
        ),
    ]
