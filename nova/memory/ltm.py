"""
Kapitel 9 – Langzeitgedächtnis (LTM)

Das LTM speichert Erinnerungen dauerhaft in der Datenbank.
Wichtige Inhalte können verschlüsselt abgelegt werden.
Erinnerungen besitzen Kategorien, Tags und einen Wichtigkeitswert.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LongTermMemory:
    """Persistentes Langzeitgedächtnis für Nova."""

    CATEGORIES = {
        "fact",        # allgemeines Faktenwissen
        "event",       # erlebte Ereignisse
        "person",      # Wissen über Personen
        "emotion",     # emotionale Erinnerungen
        "goal",        # zielrelevante Inhalte
        "preference",  # Vorlieben und Abneigungen
        "skill",       # erlernte Fähigkeiten
        "meeting",     # Besprechungs-Zusammenfassungen
        "general",     # sonstige Inhalte
    }

    def __init__(self, db, security) -> None:
        self._db = db
        self._security = security

    # ------------------------------------------------------------------
    # Speichern
    # ------------------------------------------------------------------

    def store(
        self,
        content: str,
        category: str = "general",
        importance: float = 0.5,
        tags: list[str] | None = None,
        encrypt: bool = False,
    ) -> int:
        """
        Speichert eine Erinnerung und gibt die ID zurück.

        Args:
            content:    Inhalt der Erinnerung.
            category:   Kategorie (siehe CATEGORIES).
            importance: Wichtigkeit 0.0–1.0.
            tags:       Optionale Schlagwörter.
            encrypt:    Wenn True, wird der Inhalt verschlüsselt.

        Returns:
            Datenbank-ID der neuen Erinnerung.
        """
        if category not in self.CATEGORIES:
            category = "general"

        stored_content = (
            self._security.encrypt(content) if encrypt else content
        )
        row = {
            "category": category,
            "content": stored_content,
            "importance": max(0.0, min(1.0, importance)),
            "encrypted": int(encrypt),
            "created_at": _now_iso(),
            "accessed_at": _now_iso(),
            "access_count": 0,
            "tags": self._db.to_json(tags or []),
        }
        memory_id = self._db.insert("memories", row)
        logger.debug("LTM: Erinnerung #%d gespeichert (%s).", memory_id, category)
        return memory_id

    # ------------------------------------------------------------------
    # Abrufen
    # ------------------------------------------------------------------

    def recall(
        self,
        query: str = "",
        category: str | None = None,
        min_importance: float = 0.0,
        limit: int = 10,
        profile_tag: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Sucht nach Erinnerungen.

        Args:
            query:          Suchbegriff (Volltext in content und tags).
            category:       Optionaler Kategorie-Filter.
            min_importance: Mindest-Wichtigkeit.
            limit:          Maximale Trefferanzahl.
            profile_tag:    Optionaler Profil-Filter (z. B. 'profile:work').
                            Gibt nur Erinnerungen zurück, die diesen Tag
                            enthalten **oder** überhaupt keinen ``profile:``-Tag
                            besitzen (unmarkierte Erinnerungen gelten als
                            profilübergreifend).

        Returns:
            Liste von Erinnerungs-Dicts.
        """
        sql_parts = ["SELECT * FROM memories WHERE importance >= ?"]
        params: list = [min_importance]

        if category:
            sql_parts.append("AND category = ?")
            params.append(category)

        if query:
            sql_parts.append("AND (content LIKE ? OR tags LIKE ?)")
            q = f"%{query}%"
            params.extend([q, q])

        if profile_tag:
            # Erinnerungen mit passendem Profil-Tag ODER ohne jeglichen Profil-Tag
            sql_parts.append(
                "AND (tags LIKE ? OR tags NOT LIKE '%profile:%')"
            )
            params.append(f"%{profile_tag}%")

        sql_parts.append("ORDER BY importance DESC, access_count DESC LIMIT ?")
        params.append(limit)

        rows = self._db.fetchall(" ".join(sql_parts), tuple(params))
        results = []
        for row in rows:
            entry = dict(row)
            if entry.get("encrypted"):
                entry["content"] = self._security.decrypt(entry["content"])
            entry["tags"] = self._db.from_json(entry.get("tags", "[]"))
            results.append(entry)
            # Zugriffsstatistik aktualisieren
            self._db.execute(
                "UPDATE memories SET accessed_at=?, access_count=access_count+1 WHERE id=?",
                (_now_iso(), entry["id"]),
                commit=True,
            )
        return results

    def recall_by_id(self, memory_id: int) -> dict[str, Any] | None:
        """Gibt eine einzelne Erinnerung anhand ihrer ID zurück."""
        row = self._db.fetchone(
            "SELECT * FROM memories WHERE id=?", (memory_id,)
        )
        if not row:
            return None
        entry = dict(row)
        if entry.get("encrypted"):
            entry["content"] = self._security.decrypt(entry["content"])
        entry["tags"] = self._db.from_json(entry.get("tags", "[]"))
        return entry

    def get_important(self, top_n: int = 5) -> list[dict[str, Any]]:
        """Gibt die wichtigsten Erinnerungen zurück."""
        return self.recall(min_importance=0.7, limit=top_n)

    # ------------------------------------------------------------------
    # Löschen & Aktualisieren
    # ------------------------------------------------------------------

    def forget(self, memory_id: int) -> bool:
        """Löscht eine Erinnerung dauerhaft."""
        rows = self._db.execute(
            "DELETE FROM memories WHERE id=?", (memory_id,), commit=True
        ).rowcount
        return rows > 0

    def update_importance(self, memory_id: int, importance: float) -> None:
        """Aktualisiert die Wichtigkeit einer Erinnerung."""
        self._db.update(
            "memories",
            {"importance": max(0.0, min(1.0, importance))},
            "id=?",
            (memory_id,),
        )

    # ------------------------------------------------------------------
    # Statistik
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """Gibt eine Übersicht über das LTM zurück."""
        total = self._db.fetchone("SELECT COUNT(*) AS n FROM memories")
        by_cat = self._db.fetchall(
            "SELECT category, COUNT(*) AS n FROM memories GROUP BY category"
        )
        return {
            "total": total["n"] if total else 0,
            "by_category": {row["category"]: row["n"] for row in by_cat},
        }
