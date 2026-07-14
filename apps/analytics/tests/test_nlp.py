from django.test import TestCase

from apps.analytics.models import Mention
from apps.analytics.nlp import base, pipeline
from apps.analytics.nlp.dummy import DummyProvider
from apps.analytics.nlp.lexicon import LexiconProvider


class LexiconProviderTest(TestCase):
    def setUp(self):
        self.provider = LexiconProvider()

    def test_positive_text(self):
        result = self.provider.classify("Program ini sangat berhasil dan bermanfaat")
        self.assertEqual(result.sentiment, Mention.SENTIMENT_POSITIVE)
        self.assertGreater(result.confidence, 0.5)
        self.assertLessEqual(result.confidence, 1.0)

    def test_negative_text(self):
        result = self.provider.classify("kebijakan gagal dan menuai protes serta krisis")
        self.assertEqual(result.sentiment, Mention.SENTIMENT_NEGATIVE)

    def test_neutral_text_low_confidence(self):
        result = self.provider.classify("rapat dijadwalkan pada hari senin")
        self.assertEqual(result.sentiment, Mention.SENTIMENT_NEUTRAL)

    def test_english_supported(self):
        result = self.provider.classify("this program is a great success and very good")
        self.assertEqual(result.sentiment, Mention.SENTIMENT_POSITIVE)

    def test_result_carries_model_version(self):
        result = self.provider.classify("bagus")
        self.assertTrue(result.model_version)


class FallbackChainTest(TestCase):
    class _Failing(base.Provider):
        model_version = "failing-v1"

        def classify(self, text):
            raise RuntimeError("model unavailable")

    def test_falls_through_to_next_provider(self):
        chain = pipeline.Pipeline([self._Failing(), LexiconProvider()])
        result = chain.classify("program berhasil dan bermanfaat")
        self.assertEqual(result.sentiment, Mention.SENTIMENT_POSITIVE)

    def test_dummy_guarantees_a_result_when_all_fail(self):
        chain = pipeline.Pipeline([self._Failing()])
        result = chain.classify("apapun")
        # pipeline always appends a deterministic degraded provider (SRS §8.3)
        self.assertEqual(result.sentiment, Mention.SENTIMENT_NEUTRAL)
        self.assertEqual(result.model_version, DummyProvider.model_version)

    def test_default_pipeline_classifies(self):
        result = pipeline.classify("program gagal dan mengecewakan")
        self.assertEqual(result.sentiment, Mention.SENTIMENT_NEGATIVE)
