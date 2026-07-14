"""Deterministic lexicon classifier for Bahasa Indonesia + English (FR-5.2).

A real, dependency-free classifier used as the working default in the demo and as
a fallback tier below any configured LLM provider. Substring matching keeps it
forgiving of Indonesian affixes (e.g. "bermanfaat" matches "manfaat").
"""
from .base import Classification, Provider

POSITIVE_WORDS = {
    "bagus", "baik", "berhasil", "sukses", "meningkat", "membaik", "positif",
    "apresiasi", "dukungan", "capaian", "prestasi", "unggul", "lancar", "manfaat",
    "optimis", "puas", "solusi", "efektif", "membantu", "senang", "gembira",
    "mendukung", "hebat", "good", "great", "success", "improve", "benefit",
    "support", "excellent", "happy", "best",
}
NEGATIVE_WORDS = {
    "buruk", "gagal", "krisis", "turun", "menurun", "negatif", "korupsi", "kecewa",
    "protes", "tolak", "kritik", "masalah", "rusak", "bencana", "darurat",
    "kesulitan", "kerugian", "konflik", "ancaman", "marah", "mengecewakan",
    "anjlok", "bad", "fail", "crisis", "corruption", "protest", "reject",
    "problem", "disaster", "angry", "worst",
}

# Plutchik's 8 primary emotions → indicative keywords (id + en).
EMOTION_WORDS = {
    "joy": {"senang", "gembira", "bahagia", "suka", "syukur", "joy", "happy", "glad"},
    "trust": {"percaya", "dukung", "apresiasi", "andal", "trust", "support", "reliable"},
    "fear": {"takut", "cemas", "khawatir", "waspada", "ancaman", "fear", "afraid", "worried"},
    "surprise": {"kaget", "terkejut", "heran", "mengejutkan", "surprise", "shock"},
    "sadness": {"sedih", "kecewa", "duka", "prihatin", "sad", "disappointed"},
    "disgust": {"jijik", "muak", "benci", "disgust"},
    "anger": {"marah", "geram", "murka", "kesal", "protes", "angry", "furious"},
    "anticipation": {"harap", "nanti", "rencana", "tunggu", "antisipasi", "expect", "anticipate"},
}

_SENTIMENT_TO_EMOTION = {
    "positive": "joy",
    "negative": "anger",
    "neutral": "trust",
}


def _count(words, text):
    return sum(1 for w in words if w in text)


class LexiconProvider(Provider):
    model_version = "lexicon-v1"

    def classify(self, text):
        text = (text or "").lower()
        pos = _count(POSITIVE_WORDS, text)
        neg = _count(NEGATIVE_WORDS, text)

        if pos > neg:
            sentiment = "positive"
        elif neg > pos:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        total = pos + neg
        if total == 0:
            confidence = 0.3
        else:
            confidence = round(min(1.0, 0.5 + 0.5 * abs(pos - neg) / total), 3)

        emotions = [e for e, words in EMOTION_WORDS.items() if _count(words, text)]
        if not emotions:
            emotions = [_SENTIMENT_TO_EMOTION[sentiment]]

        return Classification(
            sentiment=sentiment,
            confidence=confidence,
            emotions=emotions,
            model_version=self.model_version,
        )
