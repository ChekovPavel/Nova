"""
Kapitel 14 – Moduswechsel

Nova kann in verschiedene Betriebsmodi wechseln, die ihren
Kommunikationsstil, ihre Reaktionszeit und ihren Ressourcenverbrauch
beeinflussen.

Neue Modi:
- dating:  Romantisch-persönlicher Modus – warm, verspielt, emotional.
- meeting: Besprechungsmodus – sehr konzise, strukturiert, sachlich.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

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
    # Profilkontext: "private" (persönlich) oder "work" (Arbeit)
    profile_context: str = "private"


# ------------------------------------------------------------------
# Moduskatalog
# ------------------------------------------------------------------
MODES: dict[str, Mode] = {
    "normal": Mode(
        name="normal",
        description="Standardmodus für alltägliche Gespräche.",
        response_delay=0.0,
        verbosity="normal",
        emotion_sensitivity=0.7,
        allow_learning=True,
        profile_context="private",
    ),
    "work": Mode(
        name="work",
        description="Fokussierter Arbeitsmodus – sachlich und präzise.",
        response_delay=0.0,
        verbosity="concise",
        emotion_sensitivity=0.3,
        allow_learning=True,
        profile_context="work",
    ),
    "relax": Mode(
        name="relax",
        description="Entspannter Modus – locker und warm.",
        response_delay=0.2,
        verbosity="verbose",
        emotion_sensitivity=0.9,
        allow_learning=True,
        profile_context="private",
    ),
    "sleep": Mode(
        name="sleep",
        description="Schlafmodus – minimale Aktivität.",
        response_delay=0.0,
        verbosity="concise",
        emotion_sensitivity=0.1,
        allow_learning=False,
        sleep=True,
        profile_context="private",
    ),
    "focus": Mode(
        name="focus",
        description="Hochkonzentrations-Modus – keine Unterbrechungen.",
        response_delay=0.0,
        verbosity="concise",
        emotion_sensitivity=0.2,
        allow_learning=False,
        profile_context="work",
    ),
    "empathy": Mode(
        name="empathy",
        description="Empathie-Modus – emotional unterstützend.",
        response_delay=0.3,
        verbosity="verbose",
        emotion_sensitivity=1.0,
        allow_learning=True,
        profile_context="private",
    ),
    # --- Neue Modi ---
    "dating": Mode(
        name="dating",
        description="Dating-Modus – romantisch, warm, verspielt und neugierig.",
        response_delay=0.2,
        verbosity="verbose",
        emotion_sensitivity=0.95,
        allow_learning=True,
        profile_context="private",
    ),
    "meeting": Mode(
        name="meeting",
        description="Besprechungsmodus – sehr konzise, strukturiert und sachlich.",
        response_delay=0.0,
        verbosity="concise",
        emotion_sensitivity=0.15,
        allow_learning=True,
        profile_context="work",
    ),
}

_KEYWORD_TO_MODE: dict[str, str] = {
    "schlaf": "sleep",
    "arbeit": "work",
    "entspann": "relax",
    "ruh": "relax",
    "fokus": "focus",
    "empathi": "empathy",
    "normal": "normal",
    # Dating-Keywords
    "date": "dating",
    "flirt": "dating",
    "romantisch": "dating",
    "verliebt": "dating",
    "dating": "dating",
    # Meeting-Keywords
    "meeting": "meeting",
    "besprechung": "meeting",
    "konferenz": "meeting",
    "starte meeting": "meeting",
    "ich hab ein meeting": "meeting",
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
        self._previous: Mode | None = None
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

    @property
    def profile_context(self) -> str:
        """Gibt den Profilkontext des aktiven Modus zurück ('private' oder 'work')."""
        return self._current.profile_context

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
        logger.info(
            "Modus gewechselt: %s → %s (Profil: %s).",
            self._previous.name, self._current.name, self._current.profile_context,
        )

        # Emotionen an Modus anpassen
        if mode_name == "relax":
            self._emotion.trigger("calm", intensity=0.4, source="mode_switch")
        elif mode_name == "work":
            self._emotion.trigger("curiosity", intensity=0.3, source="mode_switch")
        elif mode_name == "empathy":
            self._emotion.trigger("empathy", intensity=0.5, source="mode_switch")
        elif mode_name == "dating":
            self._emotion.trigger("joy", intensity=0.5, source="mode_switch")
            self._emotion.trigger("excitement", intensity=0.4, source="mode_switch")
        elif mode_name == "meeting":
            self._emotion.trigger("curiosity", intensity=0.2, source="mode_switch")

        return self._current

    def switch_from_text(self, text: str) -> Mode | None:
        """Erkennt Moduswechsel-Intention im Text und führt ihn durch."""
        text_lower = text.lower()
        # Längere Keywords zuerst prüfen (Spezifizität)
        for keyword in sorted(_KEYWORD_TO_MODE, key=len, reverse=True):
            if keyword in text_lower:
                return self.switch(_KEYWORD_TO_MODE[keyword])
        return None

    def restore_previous(self) -> Mode | None:
        """Wechselt zurück zum vorherigen Modus."""
        if self._previous:
            return self.switch(self._previous.name)
        return None

    # ------------------------------------------------------------------
    # Hilfsmethoden
    # ------------------------------------------------------------------

    def is_sleeping(self) -> bool:
        return self._current.sleep

    def is_meeting(self) -> bool:
        """Gibt True zurück, wenn Nova im Besprechungsmodus ist."""
        return self._current.name == "meeting"

    def is_dating(self) -> bool:
        """Gibt True zurück, wenn Nova im Dating-Modus ist."""
        return self._current.name == "dating"

    def is_work_context(self) -> bool:
        """Gibt True zurück, wenn der aktive Modus zum Arbeitsprofil gehört."""
        return self._current.profile_context == "work"

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
            f"Emotionssensitivität: {m.emotion_sensitivity:.0%} | "
            f"Profil: {m.profile_context}"
        )
