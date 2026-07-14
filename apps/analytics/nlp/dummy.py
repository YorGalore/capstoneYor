"""Deterministic degraded provider (SRS §8.3): always returns a neutral result
without any external call, guaranteeing the pipeline can always produce output
even when every real model tier fails."""
from .base import Classification, Provider


class DummyProvider(Provider):
    model_version = "dummy-v1"

    def classify(self, text):
        return Classification(
            sentiment="neutral",
            confidence=0.0,
            emotions=["trust"],
            model_version=self.model_version,
        )
