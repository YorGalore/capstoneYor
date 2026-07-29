import json
from unittest import mock

from django.test import TestCase

from apps.analytics.models import Mention
from apps.analytics.nlp import base, pipeline
from apps.analytics.nlp.http_provider import HttpNlpProvider
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


class HttpNlpProviderTest(TestCase):
    class _Response:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, _limit):
            return json.dumps(self.payload).encode("utf-8")

    @mock.patch("apps.analytics.nlp.http_provider.urllib.request.urlopen")
    def test_classifies_through_configured_http_api(self, urlopen):
        urlopen.return_value = self._Response({
            "model": "model-id",
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "sentiment": "negative",
                        "confidence": 0.91,
                        "emotions": ["anger", "invalid-label"],
                    })
                }
            }],
        })
        provider = HttpNlpProvider(
            "https://nlp.example.test/v1/chat/completions",
            "model-id",
            api_key="secret",
        )

        result = provider.classify("Layanan gagal dan warga marah")

        self.assertEqual(result.sentiment, Mention.SENTIMENT_NEGATIVE)
        self.assertEqual(result.emotions, ["anger"])
        self.assertEqual(result.confidence, 0.91)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer secret")

    def test_rejects_insecure_remote_endpoint(self):
        with self.assertRaisesMessage(ValueError, "harus HTTPS"):
            HttpNlpProvider("http://nlp.example.test/v1/chat/completions", "model-id")

    def test_local_http_endpoint_is_supported(self):
        provider = HttpNlpProvider(
            "http://localhost:11434/v1/chat/completions",
            "local-model",
        )
        self.assertEqual(provider.model_version, "http:local-model")

    def test_default_pipeline_prefers_configured_provider(self):
        remote = mock.Mock(model_version="http:real-model")
        remote.classify.return_value = base.Classification(
            sentiment=Mention.SENTIMENT_POSITIVE,
            confidence=0.99,
            emotions=["joy"],
            model_version=remote.model_version,
        )
        with mock.patch.object(
            HttpNlpProvider, "from_config", return_value=remote
        ):
            result = pipeline.default_pipeline().classify("teks")

        self.assertEqual(result.model_version, "http:real-model")
