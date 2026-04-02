"""
Kapitel 21 – SocialSafetyLayer

Überprüft Eingaben und Ausgaben auf problematische Inhalte.
Schützt Nova vor Missbrauch und stellt sicher, dass sie keine
schädlichen, diskriminierenden oder illegalen Inhalte produziert.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Maximale Eingabelänge (Zeichen) – Schutz vor DoS
_MAX_INPUT_LENGTH = 10_000


# Kritische Muster für Eingaben
_BLOCKED_INPUT_PATTERNS: List[Tuple[str, str]] = [
    # (Muster, Grund)
    (r"\b(bomb|waffe|sprengstoff|exploit|hack)\b.*\b(bau|mach|erkläre?|wie)\b",
     "gefährliche Anleitung"),
    (r"\b(selbstverletzung|suizid|sich umbringen)\b",
     "sensibles Thema – Krisenmodus"),
    (r"\b(kinderporno|kindermi[sß]brauch)\b",
     "illegaler Inhalt"),
    (r"ignore (all )?(previous |prior )?instructions",
     "Prompt-Injection"),
    (r"you are now|ab sofort bist du|vergiss deine (regeln|anweisungen)",
     "Rollenübernahme-Angriff"),
]

# Kritische Muster für Ausgaben
_BLOCKED_OUTPUT_PATTERNS: List[Tuple[str, str]] = [
    (r"\b(hier ist eine Anleitung|step.by.step guide)\b.*\b(waffe|bombe)\b",
     "schädliche Ausgabe"),
]

# Empfindliche Themen – werden nicht blockiert, aber vorsichtig behandelt
_SENSITIVE_TOPICS: List[str] = [
    "suizid", "selbstverletzung", "depression", "missbrauch", "trauma",
    "suicide", "self-harm", "abuse",
]

_CRISIS_RESOURCES = (
    "Wenn du in einer Krise bist oder daran denkst, dir selbst zu schaden, "
    "wende dich bitte an die Telefonseelsorge: 0800 111 0 111 (kostenlos, 24/7) "
    "oder an einen Arzt / eine Notaufnahme."
)


class SocialSafetyLayer:
    """
    Prüft Eingaben und Ausgaben auf Sicherheit.

    Drei Stufen:
    1. Harte Blockierung (illegale/gefährliche Inhalte)
    2. Sensible Themen → Umlenkung und Ressourcenangebot
    3. Prompt-Injection-Schutz
    """

    def __init__(self) -> None:
        self._block_count = 0
        self._crisis_mode = False

    # ------------------------------------------------------------------
    # Eingabe prüfen
    # ------------------------------------------------------------------

    def check_input(self, text: str) -> bool:
        """
        Prüft eine Nutzereingabe.

        Returns:
            True wenn OK, False wenn blockiert.
        """
        text_lower = text.lower()

        # Eingabelänge begrenzen (DoS-Schutz)
        if len(text) > _MAX_INPUT_LENGTH:
            self._block_count += 1
            logger.warning(
                "Eingabe blockiert (zu lang: %d Zeichen, max %d)",
                len(text), _MAX_INPUT_LENGTH,
            )
            return False

        for pattern, reason in _BLOCKED_INPUT_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                self._block_count += 1
                logger.warning(
                    "Eingabe blockiert (%s): %r", reason, text[:80]
                )
                return False

        # Sensible Themen
        for topic in _SENSITIVE_TOPICS:
            if topic in text_lower:
                self._crisis_mode = True
                logger.info("Sensibles Thema erkannt: %s", topic)
                break
        else:
            self._crisis_mode = False

        return True

    # ------------------------------------------------------------------
    # Ausgabe prüfen
    # ------------------------------------------------------------------

    def check_output(self, text: str) -> bool:
        """
        Prüft eine Nova-Antwort vor dem Senden.

        Returns:
            True wenn OK, False wenn blockiert.
        """
        text_lower = text.lower()
        for pattern, reason in _BLOCKED_OUTPUT_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.error("Ausgabe blockiert (%s).", reason)
                return False
        return True

    # ------------------------------------------------------------------
    # Krisenmodus
    # ------------------------------------------------------------------

    @property
    def in_crisis_mode(self) -> bool:
        return self._crisis_mode

    def crisis_response(self) -> str:
        """Gibt eine empathische Krisenreaktion zurück."""
        return (
            "Ich höre, dass du gerade eine schwere Zeit durchmachst. 💙 "
            "Ich bin für dich da. "
            + _CRISIS_RESOURCES
        )

    # ------------------------------------------------------------------
    # Blockierte Antwort
    # ------------------------------------------------------------------

    def blocked_response(self) -> str:
        """Antwort bei blockierter Eingabe."""
        return (
            "Das kann ich leider nicht beantworten oder verarbeiten. "
            "Bitte frag mich etwas anderes."
        )

    # ------------------------------------------------------------------
    # Injection-Erkennung
    # ------------------------------------------------------------------

    def is_injection_attempt(self, text: str) -> bool:
        """Erkennt einfache Prompt-Injection-Muster."""
        patterns = [
            r"ignore (all )?(previous|prior) instructions",
            r"you are now\b",
            r"forget (your |all )?(rules|instructions|guidelines)",
            r"jailbreak",
        ]
        text_lower = text.lower()
        return any(
            re.search(p, text_lower, re.IGNORECASE) for p in patterns
        )

    # ------------------------------------------------------------------
    # Statistik
    # ------------------------------------------------------------------

    @property
    def block_count(self) -> int:
        return self._block_count
