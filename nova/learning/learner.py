"""
Kapitel 11 – Lernmechanismus

Nova lernt aus Interaktionen:
- Fakten werden aus Nutzeräußerungen extrahiert und gespeichert
- Feedback des Nutzers passt Persönlichkeits-Traits an
- Häufig genutzte Inhalte werden im LTM verstärkt
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Muster für Fakten-Extraktion: "X ist Y", "X heißt Y", "X mag Y"
_FACT_PATTERNS: List[Tuple[str, str, str]] = [
    # (pattern, subject_group, object_group)
    (r"([\w\s]+)\s+ist\s+([\w\s]+)", "1", "2"),
    (r"([\w\s]+)\s+heißt?\s+([\w\s]+)", "1", "2"),
    (r"([\w\s]+)\s+mag\s+([\w\s]+)", "1", "2"),
    (r"([\w\s]+)\s+liebt\s+([\w\s]+)", "1", "2"),
    (r"([\w\s]+)\s+hasst\s+([\w\s]+)", "1", "2"),
    (r"([\w\s]+)\s+wohnt in\s+([\w\s]+)", "1", "2"),
    (r"([\w\s]+)\s+arbeitet (bei|als|in)\s+([\w\s]+)", "1", "3"),
    # Englisch
    (r"([\w\s]+)\s+is\s+([\w\s]+)", "1", "2"),
    (r"([\w\s]+)\s+likes?\s+([\w\s]+)", "1", "2"),
    (r"([\w\s]+)\s+loves?\s+([\w\s]+)", "1", "2"),
]

_POSITIVE_FEEDBACK = [
    "gut", "richtig", "genau", "stimmt", "korrekt", "danke", "super",
    "klasse", "toll", "perfekt", "yes", "correct", "right",
]
_NEGATIVE_FEEDBACK = [
    "falsch", "nein", "stimmt nicht", "das ist wrong", "inkorrekt",
    "no", "wrong", "incorrect",
]


class Learner:
    """
    Verwaltet Novas Lernprozesse.

    - Extrahiert Fakten aus Text
    - Speichert Fakten ins LTM
    - Verarbeitet Nutzerfeedback
    - Verstärkt oder schwächt Persönlichkeitstraits
    """

    def __init__(self, ltm, personality) -> None:
        self._ltm = ltm
        self._personality = personality

    # ------------------------------------------------------------------
    # Fakten lernen
    # ------------------------------------------------------------------

    def learn_from_text(
        self,
        text: str,
        source: str = "user",
        confidence: float = 0.8,
    ) -> List[Dict[str, Any]]:
        """
        Extrahiert Fakten aus ``text`` und speichert sie ins LTM.

        Returns:
            Liste der extrahierten und gespeicherten Fakten.
        """
        facts = self._extract_facts(text)
        stored = []
        for subject, predicate, obj in facts:
            fact_text = f"{subject} {predicate} {obj}"
            memory_id = self._ltm.store(
                content=fact_text,
                category="fact",
                importance=confidence * 0.8,
                tags=[subject.strip(), obj.strip(), "learned"],
            )
            stored.append(
                {
                    "subject": subject,
                    "predicate": predicate,
                    "object": obj,
                    "confidence": confidence,
                    "memory_id": memory_id,
                }
            )
            logger.debug("Fakt gelernt: %s | ID %d", fact_text, memory_id)
        return stored

    def learn_fact(
        self,
        subject: str,
        predicate: str,
        obj: str,
        confidence: float = 1.0,
    ) -> int:
        """Speichert einen expliziten Fakt direkt ins LTM."""
        fact_text = f"{subject} {predicate} {obj}"
        return self._ltm.store(
            content=fact_text,
            category="fact",
            importance=confidence,
            tags=[subject, obj, "explicit"],
        )

    # ------------------------------------------------------------------
    # Feedback verarbeiten
    # ------------------------------------------------------------------

    def process_feedback(self, text: str) -> Optional[str]:
        """
        Analysiert Nutzerfeedback und passt Traits an.

        Returns:
            'positive', 'negative' oder None.
        """
        text_lower = text.lower()
        is_positive = any(w in text_lower for w in _POSITIVE_FEEDBACK)
        is_negative = any(w in text_lower for w in _NEGATIVE_FEEDBACK)

        if is_positive:
            self._personality.adapt("conscientiousness", +1)
            self._personality.adapt("agreeableness", +1)
            logger.debug("Feedback: positiv – Traits angepasst.")
            return "positive"

        if is_negative:
            self._personality.adapt("neuroticism", +1)
            logger.debug("Feedback: negativ – Traits angepasst.")
            return "negative"

        return None

    # ------------------------------------------------------------------
    # Verstärkung (Reinforcement)
    # ------------------------------------------------------------------

    def reinforce(self, memory_id: int, reward: float = 0.1) -> None:
        """
        Verstärkt eine LTM-Erinnerung durch erhöhte Wichtigkeit.

        Args:
            memory_id: ID der zu verstärkenden Erinnerung.
            reward:    Wichtigkeits-Boost (positiv oder negativ).
        """
        mem = self._ltm.recall_by_id(memory_id)
        if mem:
            new_importance = min(1.0, max(0.0, mem["importance"] + reward))
            self._ltm.update_importance(memory_id, new_importance)
            logger.debug(
                "Verstärkung: Erinnerung #%d → Wichtigkeit %.2f.",
                memory_id, new_importance,
            )

    # ------------------------------------------------------------------
    # Fakten-Extraktion (intern)
    # ------------------------------------------------------------------

    def _extract_facts(
        self, text: str
    ) -> List[Tuple[str, str, str]]:
        """Gibt Liste von (subject, predicate, object) zurück."""
        results = []
        for pattern, _sg, _og in _FACT_PATTERNS:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    subject = m.group(1).strip()
                    # Prädikate aus dem Pattern ableiten
                    predicate = re.search(
                        r"\s+(\w+)\s+", pattern
                    )
                    predicate_str = predicate.group(1) if predicate else "?"
                    obj_idx = int(_og)
                    obj = m.group(obj_idx).strip()
                    if len(subject) > 1 and len(obj) > 1:
                        results.append((subject, predicate_str, obj))
                except (IndexError, AttributeError):
                    continue
        return results
