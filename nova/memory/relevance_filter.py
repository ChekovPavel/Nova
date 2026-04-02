"""
Kapitel 23 - RelevanzFilter / STM-Verarbeitung

Bewertet eingehende Nachrichten und STM-Einträge nach Relevanz,
filtert Rauschen heraus und bereitet Kontextfenster für die
Antwortgenerierung vor.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Schlüsselwort-Gewichte für Relevanzberechnung
# -----------------------------------------------------------------------
_HIGH_RELEVANCE_PATTERNS = [
    r"\b(wichtig|dringend|unbedingt|vergiss nicht|merke dir|bitte)\b",
    r"\b(immer|niemals|nie|absolut|kritisch)\b",
]
_LOW_RELEVANCE_PATTERNS = [
    r"^\s*(ok|okay|ок|gut|ja|nein|danke|bitte|hmm|aha|oh)\s*$",
    r"^\s*[\U0001F600-\U0001FFFF]+\s*$",  # nur Emojis
]


class RelevanceFilter:
    """
    Bewertet STM-Einträge und Nachrichten nach ihrer Relevanz.

    Wird von ContextManager und StorageDepth genutzt, um das
    Kontextfenster für Nova-Antworten optimal zu befüllen.
    """

    def __init__(self, stm, ltm) -> None:
        self._stm = stm
        self._ltm = ltm

    # ------------------------------------------------------------------
    # Relevanz-Score berechnen
    # ------------------------------------------------------------------

    def score(
        self,
        text: str,
        base_score: float = 0.5,
        boost_tags: list[str] | None = None,
    ) -> float:
        """
        Berechnet einen Relevanz-Score (0.0-1.0) für einen Text.

        Args:
            text:       Zu bewertender Text.
            base_score: Ausgangswert.
            boost_tags: Tags, die den Score erhöhen.

        Returns:
            Relevanz-Score zwischen 0.0 und 1.0.
        """
        score = base_score

        # Kurze Trivialantworten runtergewichten
        for pattern in _LOW_RELEVANCE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.UNICODE):
                score -= 0.3
                break

        # Schlüsselwörter hochgewichten
        for pattern in _HIGH_RELEVANCE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                score += 0.2
                break

        # Länge als schwaches Signal
        word_count = len(text.split())
        if word_count > 20:
            score += 0.1
        elif word_count < 3:
            score -= 0.1

        # Tags-Boost
        if boost_tags:
            score += 0.05 * len(boost_tags)

        return max(0.0, min(1.0, score))

    # ------------------------------------------------------------------
    # Kontextfenster aufbauen
    # ------------------------------------------------------------------

    def build_context_window(
        self,
        n_recent: int = 8,
        min_relevance: float = 0.2,
        include_ltm: bool = True,
        ltm_query: str = "",
        ltm_limit: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Baut das Kontextfenster für die Antwortgenerierung auf.

        Kombiniert aktuelle STM-Nachrichten mit relevanten LTM-Einhalten.

        Returns:
            Geordnete Liste von Kontext-Dicts.
        """
        context: list[dict[str, Any]] = []

        # STM-Nachrichten
        recent = self._stm.get_recent(n=n_recent, min_relevance=min_relevance)
        for entry in recent:
            context.append(
                {
                    "source": "stm",
                    "type": entry.entry_type,
                    "content": entry.content,
                    "relevance": entry.relevance,
                }
            )

        # LTM-Hintergrundinformation
        if include_ltm and ltm_query:
            memories = self._ltm.recall(
                query=ltm_query, limit=ltm_limit, min_importance=0.5
            )
            for mem in memories:
                context.append(
                    {
                        "source": "ltm",
                        "type": mem.get("category", "general"),
                        "content": mem.get("content", ""),
                        "relevance": mem.get("importance", 0.5),
                    }
                )

        # Nach Relevanz absteigend sortieren
        context.sort(key=lambda x: x["relevance"], reverse=True)
        return context

    # ------------------------------------------------------------------
    # STM bereinigen
    # ------------------------------------------------------------------

    def filter_stm(self, min_relevance: float = 0.1) -> int:
        """
        Entfernt irrelevante Einträge aus dem STM.

        Returns:
            Anzahl entfernter Einträge.
        """
        purged = self._stm.purge()
        entries = self._stm.get_recent(n=999)
        removed = 0
        for entry in entries:
            if entry.relevance < min_relevance:
                # Relevanz auf 0 setzen und beim nächsten purge entfernen
                entry.relevance = 0.0
                entry.ttl = 0  # sofort ablaufen
                removed += 1
        return purged + removed

    # ------------------------------------------------------------------
    # Zusammenfassung
    # ------------------------------------------------------------------

    def summarize_context(
        self, context: list[dict[str, Any]], max_chars: int = 500
    ) -> str:
        """Erstellt eine kurze Textzusammenfassung des Kontexts."""
        parts = []
        total = 0
        for item in context:
            content = item.get("content", "")
            if isinstance(content, dict):
                content = content.get("text", str(content))
            snippet = str(content)[:100]
            if total + len(snippet) > max_chars:
                break
            parts.append(snippet)
            total += len(snippet)
        return " | ".join(parts)
