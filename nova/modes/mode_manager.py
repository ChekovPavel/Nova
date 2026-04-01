"""
Kapitel 14 – Moduswechsel

Nova kann in verschiedene Betriebsmodi wechseln, die ihren
Kommunikationsstil, ihre Reaktionszeit und ihren Ressourcenverbrauch
beeinflussen.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class Mode:
    """Definition eines Betriebsmodus."""
    name: str
    description: str
    response_delay: float   # Sekunden
    verbosity: str          # concise | normal | verbose
    emotion_sensitivity: float  # 0.0–1.0
    allow_learning: bool
    sleep: bool = False


# ------------------------------------------------------------------
# Moduskatalog
# ------------------------------------------------------------------
MODES: Dict[str, Mode] = {
    "normal": Mode(
        name="normal",
        description="Standardmodus für alltägliche Gespräche.",
        response_delay=0.0,
        verbosity="normal",
        emotion_sensitivity=0.7,
        allow_learning=True,
    ),
    "work": Mode(
        name="work",
        description="Fokussierter Arbeitsmodus – sachlich und präzise.",
        response_delay=0.0,
        verbosity="concise",
        emotion_sensitivity=0.3,
        allow_learning=True,
    ),
    "relax": Mode(
        name="relax",
        description="Entspannter Modus – locker und warm.",
        response_delay=0.2,
        verbosity="verbose",
        emotion_sensitivity=0.9,
        allow_learning=True,
    ),
    "sleep": Mode(
        name="sleep",
        description="Schlafmodus – minimale Aktivität.",
        response_delay=0.0,
        verbosity="concise",
        emotion_sensitivity=0.1,
        allow_learning=False,
        sleep=True,
    ),
    "focus": Mode(
        name="focus",
        description="Hochkonzentrations-Modus – keine Unterbrechungen.",
        response_delay=0.0,
        verbosity="concise",
        emotion_sensitivity=0.2,
        allow_learning=False,
    ),
    "empathy": Mode(
        name="empathy",
        description="Empathie-Modus – emotional unterstützend.",
        response_delay=0.3,
        verbosity="verbose",
        emotion_sensitivity=1.0,
        allow_learning=True,
    ),
}

_KEYWORD_TO_MODE: Dict[str, str] = {
    "schlaf": "sleep",
    "arbeit": "work",
    "entspann": "relax",
    "ruh": "relax",
    "fokus": "focus",
    "empathi": "empathy",
    "normal": "normal",
}


class ModeManager:
    """
    Verwaltet Novas aktiven Betriebsmodus.

    Reagiert auf explizite Moduswechsel und automatische
    Trigger (z. B. späte Uhrzeit → Schlafmodus).
    """

    def __init__(self, emotion) -> None:
        self._emotion = emotion
        self._current: Mode = MODES["normal"]
        self._previous: Optional[Mode] = None
        self._mode_start: float = time.monotonic()

    # ------------------------------------------------------------------
    # Moduswechsel
    # ------------------------------------------------------------------

    @property
    def current(self) -> Mode:
        return self._current

    @property
    def name(self) -> str:
        return self._current.name

    def switch(self, mode_name: str) -> Mode:
        """
        Wechselt in den angegebenen Modus.

        Args:
            mode_name: Name des Modus (aus MODES).

        Returns:
            Neuer Modus.
        """
        mode_name = mode_name.lower()
        if mode_name not in MODES:
            logger.warning("Unbekannter Modus: %r – bleibe bei %s.", mode_name, self._current.name)
            return self._current

        self._previous = self._current
        self._current = MODES[mode_name]
        self._mode_start = time.monotonic()
        logger.info("Modus gewechselt: %s → %s.", self._previous.name, self._current.name)

        # Emotionen an Modus anpassen
        if mode_name == "relax":
            self._emotion.trigger("calm", intensity=0.4, source="mode_switch")
        elif mode_name == "work":
            self._emotion.trigger("curiosity", intensity=0.3, source="mode_switch")
        elif mode_name == "empathy":
            self._emotion.trigger("empathy", intensity=0.5, source="mode_switch")

        return self._current

    def switch_from_text(self, text: str) -> Optional[Mode]:
        """Erkennt Moduswechsel-Intention im Text und führt ihn durch."""
        text_lower = text.lower()
        for keyword, mode_name in _KEYWORD_TO_MODE.items():
            if keyword in text_lower:
                return self.switch(mode_name)
        return None

    def restore_previous(self) -> Optional[Mode]:
        """Wechselt zurück zum vorherigen Modus."""
        if self._previous:
            return self.switch(self._previous.name)
        return None

    # ------------------------------------------------------------------
    # Hilfsmethoden
    # ------------------------------------------------------------------

    def is_sleeping(self) -> bool:
        return self._current.sleep

    def allows_learning(self) -> bool:
        return self._current.allow_learning

    def current_verbosity(self) -> str:
        return self._current.verbosity

    def time_in_mode(self) -> float:
        """Zeit in Sekunden seit dem letzten Moduswechsel."""
        return time.monotonic() - self._mode_start

    def describe(self) -> str:
        m = self._current
        return (
            f"Modus: {m.name} | {m.description} | "
            f"Ausführlichkeit: {m.verbosity} | "
            f"Emotionssensitivität: {m.emotion_sensitivity:.0%}"
        )
