"""
Kapitel 5 – Kontext-Management

Der ContextManager aggregiert Informationen aus STM, LTM und
Beziehungsmodell zu einem kohärenten Kontext für die
Antwortgenerierung.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Bündelt den aktuellen Gesprächskontext.

    Verwaltet:
    - Aktuelle Session-Metadaten
    - Aggregierten Kontext aus STM + LTM
    - Informationen über den aktiven Gesprächspartner
    - Gesprächsthemen und offene Fragen
    """

    def __init__(self, stm, ltm, relationships) -> None:
        self._stm = stm
        self._ltm = ltm
        self._rel = relationships
        self._active_person_id: Optional[int] = None
        self._topics: List[str] = []
        self._open_questions: List[str] = []
        self._session_data: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------

    def set_active_person(self, person_id: Optional[int]) -> None:
        self._active_person_id = person_id

    def get_active_person(self):
        if self._active_person_id is None:
            return None
        return self._rel.get_by_id(self._active_person_id)

    def set_session_data(self, key: str, value: Any) -> None:
        self._session_data[key] = value

    def get_session_data(self, key: str, default: Any = None) -> Any:
        return self._session_data.get(key, default)

    # ------------------------------------------------------------------
    # Themen & Fragen
    # ------------------------------------------------------------------

    def add_topic(self, topic: str) -> None:
        """Vermerkt ein neues Gesprächsthema."""
        if topic and topic not in self._topics:
            self._topics.append(topic)
            if len(self._topics) > 10:
                self._topics.pop(0)

    def add_open_question(self, question: str) -> None:
        """Merkt eine noch unbeantwortete Frage vor."""
        if question not in self._open_questions:
            self._open_questions.append(question)

    def resolve_question(self, question: str) -> None:
        self._open_questions = [
            q for q in self._open_questions if q != question
        ]

    # ------------------------------------------------------------------
    # Kontext-Snapshot
    # ------------------------------------------------------------------

    def snapshot(self, n_messages: int = 8) -> Dict[str, Any]:
        """
        Erzeugt einen vollständigen Kontext-Snapshot.

        Returns:
            Dict mit Nachrichten, Person, Themen, offenen Fragen und
            Session-Daten.
        """
        messages = self._stm.get_messages(n=n_messages)
        person = self.get_active_person()

        return {
            "messages": messages,
            "person": person.to_dict() if person else None,
            "topics": list(self._topics),
            "open_questions": list(self._open_questions),
            "session": dict(self._session_data),
        }

    def get_recent_text(self, n: int = 5) -> str:
        """Gibt die letzten n Nachrichten als lesbaren String zurück."""
        messages = self._stm.get_messages(n=n)
        parts = []
        for msg in messages:
            role = msg.get("role", "?")
            text = msg.get("text", "")
            parts.append(f"{role}: {text}")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Hilfsmethoden
    # ------------------------------------------------------------------

    def enrich_with_ltm(
        self, query: str, max_memories: int = 3
    ) -> List[Dict[str, Any]]:
        """Lädt relevante LTM-Erinnerungen für den aktuellen Kontext."""
        if not query:
            return []
        return self._ltm.recall(query=query, limit=max_memories)

    def clear_session(self) -> None:
        """Setzt den Sitzungskontext zurück (nicht das Gedächtnis)."""
        self._stm.clear()
        self._topics.clear()
        self._open_questions.clear()
        self._session_data.clear()
        self._active_person_id = None
        logger.info("Sitzungskontext zurückgesetzt.")

    def __repr__(self) -> str:
        person = self.get_active_person()
        return (
            f"<ContextManager person={person.name if person else 'None'} "
            f"topics={self._topics} stm_size={len(self._stm)}>"
        )
