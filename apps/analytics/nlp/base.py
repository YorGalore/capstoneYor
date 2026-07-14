"""NLP provider interface and the shared Classification result type."""
from dataclasses import dataclass, field


@dataclass
class Classification:
    sentiment: str                       # Mention.SENTIMENT_*
    confidence: float = 0.0              # 0.0–1.0 (FR-5.1)
    emotions: list = field(default_factory=list)  # Plutchik labels (FR-6.1)
    model_version: str = ""


class Provider:
    """Base class for a sentiment/emotion provider. Implementations must return a
    Classification or raise, so the pipeline can fall through to the next tier."""

    model_version = "base"

    def classify(self, text):  # pragma: no cover - interface
        raise NotImplementedError
