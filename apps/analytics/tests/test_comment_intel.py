from django.test import TestCase
from django.utils import timezone

from apps.core.models import Platform, Project, Tenant
from apps.analytics import comment_intel, selectors
from apps.analytics.metrics import resolve_evidence
from apps.analytics.models import Mention, ThreadInsight


class CommentIntelTestBase(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Pemkab Kulon Progo")
        self.project = Project.objects.create(tenant=self.tenant, name="Pemantauan")
        self.platform = Platform.objects.create(
            slug="fb", display_name="Facebook", method=Platform.METHOD_INTERNAL
        )
        self.now = timezone.now()

    def post(self, text="pemkab resmikan jembatan baru",
             sentiment=Mention.SENTIMENT_NEUTRAL):
        return Mention.objects.create(
            project=self.project, platform=self.platform, author_handle="@humas",
            content_snippet=text, sentiment=sentiment, emotion=Mention.EMOTION_TRUST,
            posted_at=self.now - timezone.timedelta(hours=6),
            content_type=Mention.CONTENT_POST,
        )

    def comment(self, parent, text="oke", sentiment=Mention.SENTIMENT_NEGATIVE,
                minutes=0, **kwargs):
        return Mention.objects.create(
            project=self.project, platform=self.platform,
            author_handle=kwargs.pop("handle", "@warga"),
            content_snippet=text, sentiment=sentiment, emotion=Mention.EMOTION_ANGER,
            posted_at=self.now - timezone.timedelta(hours=5) + timezone.timedelta(minutes=minutes),
            content_type=Mention.CONTENT_COMMENT, parent=parent, **kwargs
        )


class ToxicityAndStanceTest(CommentIntelTestBase):
    def test_root_posts_are_not_scored(self):
        post = self.post()
        self.assertIsNone(comment_intel.enrich(post))
        post.refresh_from_db()
        self.assertIsNone(post.toxicity_score)

    def test_abuse_is_scored_toxic(self):
        post = self.post()
        comment = self.comment(post, "dasar bangsat goblok semua pejabat")
        comment_intel.enrich(comment)
        comment.refresh_from_db()
        self.assertEqual(comment.toxicity_label, Mention.TOXICITY_TOXIC)

    def test_blunt_policy_criticism_is_not_toxic(self):
        """Criticism of a policy is civic speech. Scoring it as toxicity would
        make the toxicity metric a measure of dissent."""
        post = self.post()
        comment = self.comment(post, "kebijakan ini gagal total dan merugikan warga")
        comment_intel.enrich(comment)
        comment.refresh_from_db()
        self.assertEqual(comment.toxicity_label, Mention.TOXICITY_CLEAN)

    def test_stance_detects_disagreement(self):
        post = self.post()
        comment = self.comment(post, "bohong, ini cuma pencitraan")
        comment_intel.enrich(comment)
        comment.refresh_from_db()
        self.assertEqual(comment.stance, Mention.STANCE_DISAGREE)

    def test_stance_detects_agreement(self):
        post = self.post()
        comment = self.comment(post, "setuju, mantap sekali programnya")
        comment_intel.enrich(comment)
        comment.refresh_from_db()
        self.assertEqual(comment.stance, Mention.STANCE_AGREE)

    def test_quote_posts_are_treated_as_reactive_content(self):
        post = self.post()
        quote = self.comment(post, "bohong ini mah")
        quote.content_type = Mention.CONTENT_QUOTE
        quote.save(update_fields=["content_type"])
        comment_intel.enrich(quote)
        quote.refresh_from_db()
        self.assertEqual(quote.stance, Mention.STANCE_DISAGREE)


class StubProvider:
    model_version = "stub"

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    def analyse(self, text, parent_text=""):
        if self.error:
            raise self.error
        return self.result


class PipelineTest(CommentIntelTestBase):
    def test_falls_through_to_lexicon_when_the_model_fails(self):
        post = self.post()
        comment = self.comment(post, "bohong semua")
        pipeline = comment_intel.CommentPipeline([StubProvider(error=RuntimeError())])
        comment_intel.enrich(comment, pipeline=pipeline)
        comment.refresh_from_db()
        self.assertEqual(comment.comment_intel_model, "lexicon:comment-v1")

    def test_invalid_stance_from_the_model_is_rejected(self):
        with self.assertRaises(RuntimeError):
            comment_intel._signals({"toxicity": 0.1, "stance": "mungkin"})


class ThreadInsightTest(CommentIntelTestBase):
    def _thread(self, post_sentiment, comment_sentiments, texts=None):
        post = self.post(sentiment=post_sentiment)
        for index, sentiment in enumerate(comment_sentiments):
            text = (texts or {}).get(index, "komentar")
            comment = self.comment(
                post, text, sentiment=sentiment, minutes=index * 10,
                handle=f"@warga{index}",
            )
            comment_intel.enrich(comment)
        return post

    def test_thread_below_the_floor_produces_no_insight(self):
        post = self._thread(
            Mention.SENTIMENT_NEUTRAL, [Mention.SENTIMENT_NEGATIVE] * 2
        )
        self.assertIsNone(comment_intel.recompute_thread(post))

    def test_calm_post_with_furious_comments_shows_divergence(self):
        """The case a post-only dashboard misses entirely."""
        post = self._thread(
            Mention.SENTIMENT_NEUTRAL, [Mention.SENTIMENT_NEGATIVE] * 8
        )
        insight = comment_intel.recompute_thread(post)
        self.assertEqual(insight.comment_negative_pct, 100)
        self.assertEqual(insight.divergence_pp, 100)

    def test_opinion_shift_detects_a_thread_turning(self):
        post = self._thread(
            Mention.SENTIMENT_NEUTRAL,
            [Mention.SENTIMENT_POSITIVE] * 4 + [Mention.SENTIMENT_NEGATIVE] * 4,
        )
        insight = comment_intel.recompute_thread(post)
        self.assertEqual(insight.opinion_shift_pp, 100)

    def test_toxicity_pct_counts_only_comments_over_the_toxic_threshold(self):
        # Two abuse terms clear the toxic threshold; a single one lands at
        # "kasar", which is deliberately not counted as toxic.
        post = self._thread(
            Mention.SENTIMENT_NEUTRAL,
            [Mention.SENTIMENT_NEGATIVE] * 6,
            texts={0: "dasar bangsat goblok", 1: "tolol bangsat semua", 2: "kalian bego"},
        )
        insight = comment_intel.recompute_thread(post)
        self.assertEqual(insight.analysed_comment_count, 6)
        self.assertEqual(insight.toxicity_pct, 33)

    def test_recompute_is_idempotent(self):
        post = self._thread(
            Mention.SENTIMENT_NEUTRAL, [Mention.SENTIMENT_NEGATIVE] * 6
        )
        comment_intel.recompute_thread(post)
        comment_intel.recompute_thread(post)
        self.assertEqual(ThreadInsight.objects.filter(root_mention=post).count(), 1)

    def test_shrinking_below_the_floor_removes_a_stale_insight(self):
        post = self._thread(
            Mention.SENTIMENT_NEUTRAL, [Mention.SENTIMENT_NEGATIVE] * 6
        )
        comment_intel.recompute_thread(post)
        post.comments.all().delete()
        comment_intel.recompute_thread(post)
        self.assertFalse(ThreadInsight.objects.filter(root_mention=post).exists())

    def test_project_recompute_counts_qualifying_threads(self):
        self._thread(Mention.SENTIMENT_NEUTRAL, [Mention.SENTIMENT_NEGATIVE] * 6)
        self._thread(Mention.SENTIMENT_NEUTRAL, [Mention.SENTIMENT_NEGATIVE] * 2)
        self.assertEqual(comment_intel.recompute_threads(self.project), 1)


class ThreadSummaryTest(CommentIntelTestBase):
    def test_summary_metric_resolves_to_the_comments_it_counted(self):
        post = self.post(sentiment=Mention.SENTIMENT_NEUTRAL)
        for index in range(6):
            comment = self.comment(
                post, "gagal", minutes=index * 10, handle=f"@w{index}"
            )
            comment_intel.enrich(comment)
        comment_intel.recompute_thread(post)

        summary = selectors.thread_summary(self.project)
        self.assertEqual(summary["thread_count"], 1)
        metric = summary["threads"][0]["divergence"]
        self.assertEqual(
            resolve_evidence(self.project, metric.evidence).count(), metric.contributing
        )

    def test_summary_is_scoped_to_the_project(self):
        other = Project.objects.create(tenant=self.tenant, name="Proyek Lain")
        post = self.post()
        for index in range(6):
            self.comment(post, "gagal", minutes=index * 10, handle=f"@w{index}")
        comment_intel.recompute_thread(post)
        self.assertEqual(selectors.thread_summary(other)["thread_count"], 0)
