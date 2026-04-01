"""
Kapitel 22 – SpeicherTiefe-System

Entscheidet, ob ein Inhalt ins STM, LTM oder beide Speicher geschrieben
wird.  Die Tiefe richtet sich nach Wichtigkeit, Emotionalität und
explizitem Konsolidierungsbedarf.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Schwellenwerte
_LTM_IMPORTANCE_THRESHOLD = 0.6   # ab hier → LTM
_STM_ONLY_THRESHOLD = 0.3         # darunter → STM only (wird vergessen)
_EMOTIONAL_BOOST = 0.2            # emotionaler Inhalt wird wichtiger


class StorageDepth:
    """
    Koordiniert die Tiefenspeicherung von Inhalten.

    Entscheidungslogik:
        importance >= 0.6  →  LTM (+ STM-Spiegel)
        0.3 ≤ importance < 0.6 →  STM only
        importance < 0.3  →  ignoriert (kein Speicher)
    """

    def __init__(self, ltm, stm) -> None:
        self._ltm = ltm
        self._stm = stm

    # ------------------------------------------------------------------
    # Hauptmethode
    # ------------------------------------------------------------------

    def store(
        self,
        content: Any,
        importance: float = 0.5,
        category: str = "general",
        entry_type: str = "message",
        tags: Optional[List[str]] = None,
        emotional: bool = False,
        encrypt: bool = False,
    ) -> Dict[str, Any]:
        """
        Speichert ``content`` in den passenden Speicher(n).

        Returns:
            Dict mit ``stm`` (STMEntry|None) und ``ltm_id`` (int|None).
        """
        if emotional:
            importance = min(1.0, importance + _EMOTIONAL_BOOST)

        result: Dict[str, Any] = {"stm": None, "ltm_id": None}

        if importance < _STM_ONLY_THRESHOLD:
            logger.debug("StorageDepth: Inhalt unter Schwelle – verworfen.")
            return result

        # STM immer (wenn genug Relevanz)
        stm_entry = self._stm.add(
            content=content,
            entry_type=entry_type,
            relevance=importance,
            tags=tags or [],
        )
        result["stm"] = stm_entry

        # LTM nur wenn Wichtigkeit hoch genug
        if importance >= _LTM_IMPORTANCE_THRESHOLD:
            content_str = (
                content if isinstance(content, str) else str(content)
            )
            ltm_id = self._ltm.store(
                content=content_str,
                category=category,
                importance=importance,
                tags=tags,
                encrypt=encrypt,
            )
            result["ltm_id"] = ltm_id
            logger.debug(
                "StorageDepth: Inhalt in LTM #%d gespeichert (imp=%.2f).",
                ltm_id,
                importance,
            )
        return result

    # ------------------------------------------------------------------
    # Konsolidierung (STM → LTM)
    # ------------------------------------------------------------------

    def consolidate(
        self,
        min_relevance: float = 0.6,
        category: str = "general",
    ) -> int:
        """
        Überträgt wichtige STM-Einträge ins LTM (Konsolidierung).

        Returns:
            Anzahl konsolidierter Einträge.
        """
        entries = self._stm.get_recent(
            n=100, min_relevance=min_relevance
        )
        count = 0
        for entry in entries:
            content_str = (
                entry.content
                if isinstance(entry.content, str)
                else str(entry.content)
            )
            self._ltm.store(
                content=content_str,
                category=category,
                importance=entry.relevance,
                tags=entry.tags,
            )
            count += 1
        if count:
            logger.info(
                "StorageDepth: %d STM-Einträge ins LTM konsolidiert.", count
            )
        return count

    # ------------------------------------------------------------------
    # Statistik
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        return {
            "stm": self._stm.summary(),
            "ltm": self._ltm.stats(),
        }
