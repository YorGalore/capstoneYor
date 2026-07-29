from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("governance", "0010_alter_scheduledjob_job_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="manualcollectionrequest",
            name="history_start_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="manualcollectionrequest",
            name="history_end_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="manualcollectionrequest",
            name="max_results_per_platform",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
