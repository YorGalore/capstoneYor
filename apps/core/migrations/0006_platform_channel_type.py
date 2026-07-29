from django.db import migrations, models


def classify_existing_platforms(apps, schema_editor):
    Platform = apps.get_model("core", "Platform")
    Platform.objects.filter(
        slug__in=["x", "twitter", "instagram", "tiktok", "youtube", "facebook"]
    ).update(channel_type="social")
    Platform.objects.filter(slug__in=["berita", "news", "media-online"]).update(
        channel_type="news"
    )


class Migration(migrations.Migration):
    dependencies = [("core", "0005_onboardingrequest")]

    operations = [
        migrations.AddField(
            model_name="platform",
            name="channel_type",
            field=models.CharField(
                choices=[
                    ("news", "Media Online"),
                    ("social", "Media Sosial"),
                    ("other", "Sumber Lain"),
                ],
                default="other",
                max_length=20,
            ),
        ),
        migrations.RunPython(classify_existing_platforms, migrations.RunPython.noop),
    ]
