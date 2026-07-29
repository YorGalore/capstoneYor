"""Pluggable NLP layer for sentiment and emotion (FR-5, FR-6).

The classifier is swappable behind a stable interface (SRS §8.6) and runs through
a tiered fallback chain (SRS §8.3): a configured primary/secondary model, then a
deterministic degraded provider that needs no external model call — so the demo
and tests never depend on a live LLM.
"""
from .pipeline import classify, default_pipeline

__all__ = ["classify", "default_pipeline"]
