"""Backfill sentiment/emotion for mentions that predate the NLP layer, or whose
model version differs from the current one (FR-5). Runs through the same
pluggable pipeline as ingestion.
"""
from django.core.management.base import BaseCommand

from apps.analytics import taxonomy
from apps.analytics.models import Mention
from apps.analytics.nlp import default_pipeline


class Command(BaseCommand):
    help = "Re-run the NLP pipeline over mentions missing an enrichment result."

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Re-enrich every mention, not just unscored ones.")

    def handle(self, *args, **options):
        qs = Mention.objects.all() if options["all"] else Mention.objects.filter(sentiment_model="")
        updated = 0
        labeled = 0
        classifier = default_pipeline()
        for mention in qs.iterator(chunk_size=200):
            result = classifier.classify(mention.content_snippet)
            mention.sentiment = result.sentiment
            mention.sentiment_confidence = result.confidence
            mention.sentiment_model = result.model_version
            mention.emotion = result.emotions[0] if result.emotions else Mention.EMOTION_TRUST
            mention.emotion_labels = result.emotions
            mention.save(update_fields=[
                "sentiment", "sentiment_confidence", "sentiment_model", "emotion", "emotion_labels",
            ])
            # Also map the mention onto the Issue Taxonomy; a manual label is never
            # overwritten (FR-3A.3), and unmatched content stays in the review queue.
            if taxonomy.auto_label(mention) is not None:
                labeled += 1
            updated += 1
        self.stdout.write(
            self.style.SUCCESS(f"Enriched {updated} mention(s); auto-labeled {labeled}.")
        )
