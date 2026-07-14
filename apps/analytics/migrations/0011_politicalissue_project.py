"""Give PoliticalIssue a project (FR-1.2 tenant isolation).

Done in three steps rather than one so existing rows are backfilled from the data itself:
an issue belongs to whichever project its mentions are in. Letting Django prompt for a
single one-off default would have shoved every tenant's issues into one project.
"""
from django.db import migrations, models
import django.db.models.deletion


def assign_project(apps, schema_editor):
    PoliticalIssue = apps.get_model("analytics", "PoliticalIssue")
    Mention = apps.get_model("analytics", "Mention")
    Project = apps.get_model("core", "Project")

    fallback = Project.objects.order_by("pk").first()

    for issue in PoliticalIssue.objects.all():
        # The mentions already carry the project, so they are the ground truth for which
        # tenant this issue actually belongs to.
        mention = Mention.objects.filter(issue=issue).first()
        project = mention.project if mention else fallback
        if project is None:
            # No projects exist at all, so no issue can meaningfully belong to one.
            continue
        issue.project = project
        issue.save(update_fields=["project"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_remove_analystprofile_has_political_monitoring_permission"),
        ("analytics", "0010_dailybrief_dailybriefissue_dailybriefrun"),
    ]

    operations = [
        migrations.AddField(
            model_name="politicalissue",
            name="project",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="political_issues",
                to="core.project",
            ),
        ),
        migrations.RunPython(assign_project, noop),
        migrations.AlterField(
            model_name="politicalissue",
            name="project",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="political_issues",
                to="core.project",
            ),
        ),
    ]
