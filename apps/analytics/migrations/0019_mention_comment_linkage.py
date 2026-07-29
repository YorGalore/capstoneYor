from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("analytics", "0018_incident_draft_response_and_more")]

    operations = [
        migrations.AddField(
            model_name="mention",
            name="content_type",
            field=models.CharField(
                choices=[
                    ("post", "Posting/Artikel"),
                    ("comment", "Komentar/Balasan"),
                ],
                default="post",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="mention",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="comments",
                to="analytics.mention",
            ),
        ),
        migrations.AddField(
            model_name="mention",
            name="reported_comment_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddIndex(
            model_name="mention",
            index=models.Index(fields=["content_type"], name="analytics_m_content_6bf398_idx"),
        ),
    ]
