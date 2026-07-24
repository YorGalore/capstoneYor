from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("analytics", "0016_alter_notificationdelivery_kind"),
    ]

    operations = [
        migrations.AddField(
            model_name="incident",
            name="evidence_caption",
            field=models.CharField(blank=True, max_length=300),
        ),
        migrations.AddField(
            model_name="incident",
            name="evidence_image_path",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="incident",
            name="evidence_is_simulated",
            field=models.BooleanField(default=False),
        ),
    ]
