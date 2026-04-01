"""
Kapitel 10 – Kurzzeitgedächtnis / STM

Das STM hält die aktuelle Konversation und kurzfristig relevante
Informationen in einer Deque mit konfigurierbarer Kapazität.
Einträge haben ein Ablaufdatum (time-to-live) und einen Relevanz-Score.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_TTL = 3600  # 1 Stunde in Sekunden


@dataclass
class STMEntry:
    """Ein einzelner Kurzzeitgedächtnis-Eintrag."""

    content: Any
    entry_type: str = "message"          # message | fact | emotion | context
    relevance: float = 0.5               # 0.0 – 1.0
    created_at: float = field(default_factory=time.monotonic)
    ttl: float = _DEFAULT_TTL            # Lebensdauer in Sekunden
    tags: List[str] = field(default_factory=list)

    @property
    def is_expired(self) -> bool:
        return (time.monotonic() - self.created_at) > self.ttl

    @property
    def age_seconds(self) -> float:
        return time.monotonic() - self.created_at


class ShortTermMemory:
    """
    Ringpuffer-basiertes Kurzzeitgedächtnis.

    Hält die letzten ``capacity`` Einträge.  Abgelaufene Einträge werden
    beim nächsten Zugriff oder explizit durch ``purge()`` entfernt.
    """

    def __init__(self, capacity: int = 20) -> None:
        self.capacity = capacity
        self._buffer: Deque[STMEntry] = deque(maxlen=capacity)

    # ------------------------------------------------------------------
    # Hinzufügen
    # ------------------------------------------------------------------

    def add(
        self,
        content: Any,
        entry_type: str = "message",
        relevance: float = 0.5,
        ttl: float = _DEFAULT_TTL,
        tags: Optional[List[str]] = None,
    ) -> STMEntry:
        """Fügt einen neuen Eintrag ins STM ein."""
        entry = STMEntry(
            content=content,
            entry_type=entry_type,
            relevance=relevance,
            ttl=ttl,
            tags=tags or [],
        )
        self._buffer.append(entry)
        logger.debug("STM: Eintrag hinzugefügt (type=%s, rel=%.2f).", entry_type, relevance)
        return entry

    def add_message(
        self, role: str, text: str, relevance: float = 0.5
    ) -> STMEntry:
        """Kurzform: Nachricht (user/nova) ins STM."""
        return self.add(
            content={"role": role, "text": text},
            entry_type="message",
            relevance=relevance,
        )

    # ------------------------------------------------------------------
    # Abrufen
    # ------------------------------------------------------------------

    def get_recent(
        self,
        n: int = 10,
        entry_type: Optional[str] = None,
        min_relevance: float = 0.0,
    ) -> List[STMEntry]:
        """Gibt die neuesten (nicht abgelaufenen) Einträge zurück."""
        self.purge()
        entries = list(self._buffer)
        if entry_type:
            entries = [e for e in entries if e.entry_type == entry_type]
        if min_relevance > 0.0:
            entries = [e for e in entries if e.relevance >= min_relevance]
        return entries[-n:]

    def get_messages(self, n: int = 10) -> List[Dict[str, str]]:
        """Gibt die letzten n Nachrichten als Liste von Dicts zurück."""
        entries = self.get_recent(n=n, entry_type="message")
        return [e.content for e in entries if isinstance(e.content, dict)]

    def search(self, keyword: str) -> List[STMEntry]:
        """Einfache Keyword-Suche im STM."""
        keyword_lower = keyword.lower()
        results = []
        for entry in self._buffer:
            if entry.is_expired:
                continue
            content_str = str(entry.content).lower()
            if keyword_lower in content_str or any(
                keyword_lower in t.lower() for t in entry.tags
            ):
                results.append(entry)
        return results

    # ------------------------------------------------------------------
    # Housekeeping
    # ------------------------------------------------------------------

    def purge(self) -> int:
        """Entfernt abgelaufene Einträge.  Gibt Anzahl zurück."""
        before = len(self._buffer)
        self._buffer = deque(
            (e for e in self._buffer if not e.is_expired),
            maxlen=self.capacity,
        )
        removed = before - len(self._buffer)
        if removed:
            logger.debug("STM: %d abgelaufene Einträge entfernt.", removed)
        return removed

    def clear(self) -> None:
        """Löscht das gesamte STM (z. B. beim Sitzungsende)."""
        self._buffer.clear()

    # ------------------------------------------------------------------
    # Eigenschaften
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._buffer)

    @property
    def is_empty(self) -> bool:
        return len(self._buffer) == 0

    def summary(self) -> Dict[str, Any]:
        """Kurze Zusammenfassung des STM-Zustands."""
        self.purge()
        by_type: Dict[str, int] = {}
        for e in self._buffer:
            by_type[e.entry_type] = by_type.get(e.entry_type, 0) + 1
        return {"count": len(self._buffer), "by_type": by_type}
