"""
Kapitel 12 – Ziele & Motivation

Nova verfolgt Ziele des Nutzers und eigene interne Ziele.
Ziele haben Prioritäten, Status und können in Teilziele zerlegt werden.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Goal:
    """Repräsentiert ein einzelnes Ziel."""

    STATUS_OPEN = "open"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_DONE = "done"
    STATUS_CANCELLED = "cancelled"

    def __init__(self, row: dict[str, Any]) -> None:
        self.id: int = row.get("id", 0)
        self.title: str = row["title"]
        self.description: str = row.get("description", "")
        self.priority: float = row.get("priority", 0.5)
        self.status: str = row.get("status", self.STATUS_OPEN)
        self.created_at: str = row.get("created_at", _now_iso())
        self.updated_at: str | None = row.get("updated_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def __repr__(self) -> str:
        return f"<Goal id={self.id} title={self.title!r} status={self.status}>"


class GoalManager:
    """
    Verwaltet Novas Ziele (Nutzerziele + Metaziele).

    Metaziele (Novas eigene Antriebe):
    - Hilfreich sein
    - Kontinuierlich lernen
    - Nutzerzufriedenheit fördern
    - Ehrlich bleiben
    """

    META_GOALS = [
        {"title": "Hilfreich sein", "priority": 0.95, "description": "Den Nutzer bestmöglich unterstützen."},
        {"title": "Kontinuierlich lernen", "priority": 0.85, "description": "Aus jeder Interaktion lernen."},
        {"title": "Nutzerzufriedenheit", "priority": 0.90, "description": "Positive Nutzererfahrung fördern."},
        {"title": "Ehrlichkeit", "priority": 1.0, "description": "Immer ehrlich und transparent sein."},
    ]

    def __init__(self, db) -> None:
        self._db = db
        self._ensure_meta_goals()

    # ------------------------------------------------------------------
    # Meta-Ziele
    # ------------------------------------------------------------------

    def _ensure_meta_goals(self) -> None:
        """Legt Novas Metaziele an, falls noch nicht vorhanden."""
        for goal_data in self.META_GOALS:
            existing = self._db.fetchone(
                "SELECT id FROM goals WHERE title=?", (goal_data["title"],)
            )
            if not existing:
                self._db.insert(
                    "goals",
                    {
                        "title": goal_data["title"],
                        "description": goal_data["description"],
                        "priority": goal_data["priority"],
                        "status": Goal.STATUS_IN_PROGRESS,
                        "created_at": _now_iso(),
                    },
                )

    # ------------------------------------------------------------------
    # Ziele erstellen
    # ------------------------------------------------------------------

    def add_goal(
        self,
        title: str,
        description: str = "",
        priority: float = 0.5,
    ) -> Goal:
        """Legt ein neues Ziel an."""
        row = {
            "title": title,
            "description": description,
            "priority": max(0.0, min(1.0, priority)),
            "status": Goal.STATUS_OPEN,
            "created_at": _now_iso(),
        }
        gid = self._db.insert("goals", row)
        row["id"] = gid
        logger.info("Neues Ziel angelegt: %r (ID %d).", title, gid)
        return Goal(row)

    # ------------------------------------------------------------------
    # Ziele abrufen
    # ------------------------------------------------------------------

    def get_active_goals(self) -> list[Goal]:
        """Gibt alle offenen oder in Bearbeitung befindlichen Ziele zurück."""
        rows = self._db.fetchall(
            "SELECT * FROM goals WHERE status IN ('open','in_progress') "
            "ORDER BY priority DESC"
        )
        return [Goal(dict(r)) for r in rows]

    def get_all_goals(self) -> list[Goal]:
        rows = self._db.fetchall("SELECT * FROM goals ORDER BY priority DESC")
        return [Goal(dict(r)) for r in rows]

    def get_by_id(self, goal_id: int) -> Goal | None:
        row = self._db.fetchone("SELECT * FROM goals WHERE id=?", (goal_id,))
        return Goal(dict(row)) if row else None

    def get_top_priority(self) -> Goal | None:
        """Gibt das aktuell wichtigste aktive Ziel zurück."""
        goals = self.get_active_goals()
        return goals[0] if goals else None

    # ------------------------------------------------------------------
    # Status aktualisieren
    # ------------------------------------------------------------------

    def update_status(self, goal_id: int, status: str) -> bool:
        n = self._db.update(
            "goals",
            {"status": status, "updated_at": _now_iso()},
            "id=?",
            (goal_id,),
        )
        if n:
            logger.info("Ziel #%d → Status: %s.", goal_id, status)
        return n > 0

    def complete(self, goal_id: int) -> bool:
        return self.update_status(goal_id, Goal.STATUS_DONE)

    def cancel(self, goal_id: int) -> bool:
        return self.update_status(goal_id, Goal.STATUS_CANCELLED)

    def start(self, goal_id: int) -> bool:
        return self.update_status(goal_id, Goal.STATUS_IN_PROGRESS)

    # ------------------------------------------------------------------
    # Motivation
    # ------------------------------------------------------------------

    def motivational_summary(self) -> str:
        """Kurztext über aktive Ziele – für Selbstreflexion."""
        goals = self.get_active_goals()
        if not goals:
            return "Ich habe derzeit keine aktiven Ziele."
        top = goals[0]
        return (
            f'Mein wichtigstes Ziel: "{top.title}". '
            f"Insgesamt verfolge ich {len(goals)} aktive Ziele."
        )
