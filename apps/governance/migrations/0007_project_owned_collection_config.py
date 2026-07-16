from django.db import migrations, models
import django.db.models.deletion


def assign_legacy_rows(apps, schema_editor):
    """Attach formerly global rows to the deterministic legacy/default project.

    Historical rows contain no tenant discriminator, so inventing a mapping would be
    unsafe.  Keeping them with the first project preserves the application's prior
    effective owner while all new writes carry explicit ownership.
    """
    Project = apps.get_model("core", "Project")
    project = Project.objects.order_by("pk").first()
    if project is None:
        orphan_count = sum(
            apps.get_model("governance", model_name).objects.filter(project__isnull=True).count()
            for model_name in (
                "PlatformIntegration", "ApifyCredential", "MonitoredDomain",
                "MonitoringKeyword", "CollectionRun",
            )
        )
        if orphan_count:
            raise RuntimeError(
                "Cannot migrate global governance configuration: no Project exists to own it."
            )
        return
    for model_name in (
        "PlatformIntegration",
        "ApifyCredential",
        "MonitoredDomain",
        "MonitoringKeyword",
        "CollectionRun",
    ):
        apps.get_model("governance", model_name).objects.filter(project__isnull=True).update(
            project=project
        )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_remove_analystprofile_has_political_monitoring_permission"),
        ("governance", "0006_scheduledjob"),
    ]

    operations = [
        migrations.AlterField(
            model_name="platformintegration",
            name="platform",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="integrations",
                to="core.platform",
            ),
        ),
        migrations.AlterField(
            model_name="monitoreddomain",
            name="domain",
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name="monitoringkeyword",
            name="keyword",
            field=models.CharField(max_length=150),
        ),
        *[
            migrations.AddField(
                model_name=model_name,
                name="project",
                field=models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    to="core.project",
                ),
            )
            for model_name in (
                "platformintegration",
                "apifycredential",
                "monitoreddomain",
                "monitoringkeyword",
                "collectionrun",
            )
        ],
        migrations.RunPython(assign_legacy_rows, migrations.RunPython.noop),
        *[
            migrations.AlterField(
                model_name=model_name,
                name="project",
                field=models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to="core.project",
                ),
            )
            for model_name in (
                "platformintegration",
                "apifycredential",
                "monitoreddomain",
                "monitoringkeyword",
                "collectionrun",
            )
        ],
        migrations.AddConstraint(
            model_name="platformintegration",
            constraint=models.UniqueConstraint(
                fields=("project", "platform"),
                name="uniq_governance_integration_project_platform",
            ),
        ),
        migrations.AddConstraint(
            model_name="monitoreddomain",
            constraint=models.UniqueConstraint(
                fields=("project", "domain"), name="uniq_governance_domain_project"
            ),
        ),
        migrations.AddConstraint(
            model_name="monitoringkeyword",
            constraint=models.UniqueConstraint(
                fields=("project", "keyword"), name="uniq_governance_keyword_project"
            ),
        ),
    ]
