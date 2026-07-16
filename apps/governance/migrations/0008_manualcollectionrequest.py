import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("governance", "0007_project_owned_collection_config"),
    ]

    operations = [
        migrations.CreateModel(
            name="ManualCollectionRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("collection_type", models.CharField(choices=[("social", "Social Media"), ("news", "Berita Daring")], max_length=20)),
                ("status", models.CharField(choices=[("queued", "Dalam antrean"), ("running", "Sedang berjalan"), ("completed", "Selesai"), ("failed", "Gagal"), ("skipped", "Dilewati")], db_index=True, default="queued", max_length=20)),
                ("requested_by", models.CharField(max_length=150)),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("items_found", models.PositiveIntegerField(default=0)),
                ("sources_processed", models.PositiveIntegerField(default=0)),
                ("detail", models.CharField(blank=True, max_length=500)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.project")),
            ],
            options={"ordering": ["-requested_at"]},
        ),
        migrations.AddIndex(
            model_name="manualcollectionrequest",
            index=models.Index(fields=["status", "requested_at"], name="manual_collect_queue_idx"),
        ),
    ]
