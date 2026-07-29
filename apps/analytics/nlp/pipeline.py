"""Tiered fallback pipeline (SRS §8.3): try each provider in order; on failure or
malformed output fall through to the next tier, always ending with the
deterministic DummyProvider so a result is guaranteed.

A configured OpenAI-compatible HTTP provider is the primary tier. The local
lexicon and neutral terminal fallback keep collection available during outages
and persist their model provenance explicitly.
"""
import logging

from .base import Classification
from .dummy import DummyProvider
from .http_provider import HttpNlpProvider
from .lexicon import LexiconProvider

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, providers):
        # Always guarantee a terminal degraded provider.
        self.providers = list(providers)
        if not self.providers or not isinstance(self.providers[-1], DummyProvider):
            self.providers.append(DummyProvider())

    def classify(self, text):
        for provider in self.providers:
            try:
                result = provider.classify(text)
            except Exception as exc:  # fall through to the next tier (SRS §8.3)
                logger.warning("NLP provider %s failed: %s", provider.model_version, exc)
                continue
            if _is_valid(result):
                return result
            logger.warning("NLP provider %s returned malformed output", provider.model_version)
        # Unreachable: DummyProvider always yields a valid result.
        return DummyProvider().classify(text)


def _is_valid(result):
    return (
        isinstance(result, Classification)
        and result.sentiment in {"positive", "negative", "neutral"}
    )


def default_pipeline():
    """Configured HTTP model, then deterministic local degraded tiers."""
    providers = []
    remote = HttpNlpProvider.from_config()
    if remote is not None:
        providers.append(remote)
    providers.append(LexiconProvider())
    return Pipeline(providers)


def classify(text):
    return default_pipeline().classify(text)
