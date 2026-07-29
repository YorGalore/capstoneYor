from django.db import migrations, models
import django.db.models.deletion


def backfill_actor_sentiments(apps, schema_editor):
    Mention = apps.get_model("analytics", "Mention")
    Assessment = apps.get_model("analytics", "ActorSentimentAssessment")
    through = Mention.political_actors.through
    mentions = {
        mention.id: mention
        for mention in Mention.objects.only(
            "id", "sentiment", "sentiment_confidence", "sentiment_model"
        )
    }
    rows = []
    for link in through.objects.all().iterator():
        mention = mentions.get(link.mention_id)
        if mention is None:
            continue
        rows.append(Assessment(
            mention_id=link.mention_id,
            actor_id=link.politicalactor_id,
            sentiment=mention.sentiment,
            confidence=mention.sentiment_confidence,
            model=mention.sentiment_model,
            source="auto",
        ))
    Assessment.objects.bulk_create(rows, ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [("analytics", "0019_mention_comment_linkage")]

    operations = [
        migrations.CreateModel(
            name="ActorSentimentAssessment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sentiment", models.CharField(
                    choices=[
                        ("positive", "Positif"),
                        ("neutral", "Netral"),
                        ("negative", "Negatif"),
                    ],
                    max_length=20,
                )),
                ("confidence", models.FloatField(default=0.0)),
                ("model", models.CharField(blank=True, max_length=50)),
                ("source", models.CharField(
                    choices=[("auto", "Otomatis"), ("manual", "Manual")],
                    default="auto",
                    max_length=10,
                )),
                ("reviewed_by", models.CharField(blank=True, max_length=150)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("actor", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="sentiment_assessments",
                    to="analytics.politicalactor",
                )),
                ("mention", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="actor_sentiments",
                    to="analytics.mention",
                )),
            ],
            options={
                "ordering": ["actor__name"],
                "unique_together": {("mention", "actor")},
            },
        ),
        migrations.RunPython(backfill_actor_sentiments, migrations.RunPython.noop),
    ]
