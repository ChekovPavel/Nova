"""
Kapitel 7 - Emotionsschicht

Novas Emotionen basieren auf dem Valence-Arousal-Dominance-Modell (VAD).
Der aktuelle Emotionszustand beeinflusst Ton und Inhalte von Antworten.
Emotionen klingen über Zeit ab (Decay) und werden durch Ereignisse ausgelöst.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import ClassVar

logger = logging.getLogger(__name__)

# Emotions-Bibliothek: Name → (valence, arousal, dominance)
# Skala je -1.0 bis +1.0
EMOTION_VECTORS: dict[str, tuple[float, float, float]] = {
    "joy": (0.80, 0.50, 0.40),
    "excitement": (0.70, 0.80, 0.50),
    "calm": (0.40, -0.30, 0.20),
    "neutral": (0.00, 0.00, 0.00),
    "curiosity": (0.50, 0.40, 0.30),
    "sadness": (-0.60, -0.40, -0.20),
    "frustration": (-0.50, 0.40, -0.30),
    "anger": (-0.70, 0.80, -0.40),
    "anxiety": (-0.40, 0.60, -0.50),
    "surprise": (0.20, 0.70, 0.00),
    "empathy": (0.60, 0.10, 0.20),
    "boredom": (-0.20, -0.50, -0.10),
}

_DECAY_RATE = 0.05  # Decay pro Sekunde (Richtung neutral)
_DECAY_INTERVAL = 10.0  # Decay-Berechnung alle N Sekunden


@dataclass
class EmotionState:
    """Aktueller Emotionszustand im VAD-Raum."""

    valence: float = 0.0  # -1 (negativ) bis +1 (positiv)
    arousal: float = 0.0  # -1 (schläfrig) bis +1 (aufgewühlt)
    dominance: float = 0.0  # -1 (unterwürfig) bis +1 (dominant)
    label: str = "neutral"
    intensity: float = 0.0  # 0.0-1.0
    history: list[str] = field(default_factory=list)
    last_update: float = field(default_factory=time.monotonic)


class EmotionEngine:
    """
    Verwaltet Novas aktuellen Emotionszustand.

    Emotionen werden durch Ereignisse (``trigger``) ausgelöst,
    klingen durch ``decay`` über Zeit ab und beeinflussen den
    Kommunikationsstil.
    """

    def __init__(self, personality) -> None:
        self._personality = personality
        self._state = EmotionState()
        self._last_decay = time.monotonic()

    # ------------------------------------------------------------------
    # Emotionen auslösen
    # ------------------------------------------------------------------

    def trigger(
        self,
        emotion: str,
        intensity: float = 0.5,
        source: str = "unknown",
    ) -> EmotionState:
        """
        Löst eine Emotion aus und mischt sie in den aktuellen Zustand.

        Args:
            emotion:   Name der Emotion (aus EMOTION_VECTORS).
            intensity: Stärke 0.0-1.0.
            source:    Ursache der Emotion (für Log/Verlauf).

        Returns:
            Neuer EmotionState.
        """
        self._apply_decay()

        if emotion not in EMOTION_VECTORS:
            logger.warning("Unbekannte Emotion: %s", emotion)
            return self._state

        v, a, d = EMOTION_VECTORS[emotion]
        alpha = max(0.0, min(1.0, intensity))

        # Mische neue Emotion in Zustand (gewichteter Durchschnitt)
        blend = 0.4 * alpha
        self._state.valence = self._state.valence * (1 - blend) + v * blend
        self._state.arousal = self._state.arousal * (1 - blend) + a * blend
        self._state.dominance = self._state.dominance * (1 - blend) + d * blend
        self._state.intensity = alpha
        self._state.label = emotion
        self._state.last_update = time.monotonic()
        self._state.history.append(f"{emotion}@{intensity:.2f}←{source}")
        if len(self._state.history) > 20:
            self._state.history.pop(0)

        logger.debug(
            "Emotion: %s (I=%.2f) | VAD=(%.2f, %.2f, %.2f)",
            emotion,
            alpha,
            self._state.valence,
            self._state.arousal,
            self._state.dominance,
        )
        return self._state

    # ------------------------------------------------------------------
    # Text-basierter Emotionserkenner (einfaches Keyword-Mapping)
    # ------------------------------------------------------------------

    _KEYWORD_MAP: ClassVar[dict[str, str]] = {
        "toll|super|klasse|freue|danke|schön|liebe": "joy",
        "traurig|schlimm|schrecklich|weine|verloren": "sadness",
        "wütend|scheiße|hass|furchtbar|Ärger": "anger",
        "nervös|angst|sorge|aufgeregt|unruhig": "anxiety",
        "langweilig|egal|meh": "boredom",
        "interessant|neugier|frage|wie|warum|was": "curiosity",
        "wow|überraschend|unerwartet": "surprise",
    }

    def detect_from_text(self, text: str) -> str | None:
        """Einfache Schlüsselworterkennung für die Emotion im Text."""
        import re

        text_lower = text.lower()
        for pattern, emotion in self._KEYWORD_MAP.items():
            if re.search(pattern, text_lower):
                return emotion
        return None

    def react_to_text(self, text: str, intensity: float = 0.3) -> None:
        """Löst automatisch eine Emotion aus, die zum Text passt."""
        emotion = self.detect_from_text(text)
        if emotion:
            self.trigger(emotion, intensity=intensity, source="text")

    def react_to_sentiment(self, sentiment: float, intensity: float = 0.3) -> None:
        """
        Reagiert auf einen numerischen Sentiment-Wert aus dem NLP-Prozessor.

        Mapping:
            sentiment >  0.50  → joy          (intensity x 1.2)
            sentiment >  0.15  → curiosity    (intensity x 0.8)
            sentiment < -0.50  → sadness      (intensity x 1.2)
            sentiment < -0.15  → frustration  (intensity x 0.8)
            |sentiment| ≤ 0.15 → keine Reaktion (neutraler Bereich)

        Args:
            sentiment: Wert -1.0 (sehr negativ) bis +1.0 (sehr positiv),
                       wie von NLPProcessor._estimate_sentiment() geliefert.
            intensity: Basis-Intensität; wird je nach Mapping skaliert.
        """
        if sentiment > 0.5:
            self.trigger("joy", intensity=intensity * 1.2, source="sentiment")
        elif sentiment > 0.15:
            self.trigger("curiosity", intensity=intensity * 0.8, source="sentiment")
        elif sentiment < -0.5:
            self.trigger("sadness", intensity=intensity * 1.2, source="sentiment")
        elif sentiment < -0.15:
            self.trigger("frustration", intensity=intensity * 0.8, source="sentiment")

    # ------------------------------------------------------------------
    # Decay (Abklingen)
    # ------------------------------------------------------------------

    def _apply_decay(self) -> None:
        """Lässt Emotionen Richtung neutral abklingen."""
        now = time.monotonic()
        dt = now - self._last_decay
        if dt < _DECAY_INTERVAL:
            return
        self._last_decay = now

        decay = min(_DECAY_RATE * dt, 0.3)
        self._state.valence *= 1 - decay
        self._state.arousal *= 1 - decay
        self._state.dominance *= 1 - decay
        self._state.intensity = max(0.0, self._state.intensity - decay)

        if abs(self._state.valence) < 0.05 and abs(self._state.arousal) < 0.05:
            self._state.label = "neutral"

    # ------------------------------------------------------------------
    # Zustand abrufen
    # ------------------------------------------------------------------

    @property
    def state(self) -> EmotionState:
        self._apply_decay()
        return self._state

    @property
    def current_label(self) -> str:
        return self.state.label

    def mood_modifier(self) -> str:
        """
        Gibt ein kurzes Adjektiv zurück, das die Stimmung beschreibt.
        Wird von der Antwortgenerierung genutzt.
        """
        v = self.state.valence
        a = self.state.arousal
        if v > 0.5 and a > 0.3:
            return "enthusiastisch"
        if v > 0.3:
            return "freundlich"
        if v < -0.4 and a > 0.3:
            return "besorgt"
        if v < -0.3:
            return "gedämpft"
        if a > 0.5:
            return "aufmerksam"
        return "gelassen"

    def __repr__(self) -> str:
        s = self.state
        return (
            f"<EmotionEngine label={s.label} "
            f"VAD=({s.valence:.2f},{s.arousal:.2f},{s.dominance:.2f})>"
        )
