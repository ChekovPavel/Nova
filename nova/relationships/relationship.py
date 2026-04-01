"""
Kapitel 8 – Beziehungsmodell (bekannte Personen)

Verwaltet bekannte Personen mit ihren Profilen, Vertrauensstufen
und Interaktionshistorie.  Neue Personen werden nur auf expliziten
Wunsch des Nutzers angelegt.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Person:
    """Repräsentiert eine bekannte Person."""

    def __init__(self, row: Dict[str, Any], db) -> None:
        self._db = db
        self.id: int = row["id"]
        self.name: str = row["name"]
        self.aliases: List[str] = db.from_json(row.get("aliases", "[]"))
        self.profile: Dict[str, Any] = db.from_json(row.get("profile", "{}"))
        self.trust_level: float = row.get("trust_level", 0.5)
        self.first_seen: str = row.get("first_seen", _now_iso())
        self.last_seen: str = row.get("last_seen", _now_iso())

    def update_profile(self, key: str, value: Any) -> None:
        """Fügt einen Profilwert hinzu oder aktualisiert ihn."""
        self.profile[key] = value
        self._db.update(
            "persons",
            {
                "profile": self._db.to_json(self.profile),
                "last_seen": _now_iso(),
            },
            "id=?",
            (self.id,),
        )

    def update_trust(self, delta: float) -> None:
        """Ändert die Vertrauensstufe um delta (-1.0 … +1.0)."""
        self.trust_level = max(0.0, min(1.0, self.trust_level + delta))
        self._db.update(
            "persons",
            {"trust_level": self.trust_level},
            "id=?",
            (self.id,),
        )

    def mark_seen(self) -> None:
        """Aktualisiert den letzten Kontaktzeitpunkt."""
        self.last_seen = _now_iso()
        self._db.update(
            "persons", {"last_seen": self.last_seen}, "id=?", (self.id,)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "aliases": self.aliases,
            "profile": self.profile,
            "trust_level": self.trust_level,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }

    def __repr__(self) -> str:
        return f"<Person id={self.id} name={self.name!r} trust={self.trust_level:.2f}>"


class RelationshipModel:
    """
    Verwaltet bekannte Personen und deren Beziehungen zu Nova.

    Neue Personen werden **nur** auf explizite Anfrage des Nutzers
    angelegt (kein automatisches stilles Profiling).
    """

    def __init__(self, db) -> None:
        self._db = db
        self._cache: Dict[int, Person] = {}

    # ------------------------------------------------------------------
    # Personen anlegen
    # ------------------------------------------------------------------

    def add_person(
        self,
        name: str,
        aliases: Optional[List[str]] = None,
        profile: Optional[Dict[str, Any]] = None,
        trust_level: float = 0.5,
    ) -> Person:
        """
        Legt eine neue bekannte Person explizit an.

        Args:
            name:        Anzeigename.
            aliases:     Alternative Namen / Spitznamen.
            profile:     Anfangs-Profilwerte.
            trust_level: Anfängliche Vertrauensstufe (0–1).

        Returns:
            Person-Objekt.
        """
        row_data = {
            "name": name,
            "aliases": self._db.to_json(aliases or []),
            "profile": self._db.to_json(profile or {}),
            "trust_level": trust_level,
            "first_seen": _now_iso(),
            "last_seen": _now_iso(),
        }
        pid = self._db.insert("persons", row_data)
        row_data["id"] = pid
        person = Person(row_data, self._db)
        self._cache[pid] = person
        logger.info("Neue Person angelegt: %s (ID %d).", name, pid)
        return person

    # ------------------------------------------------------------------
    # Suchen
    # ------------------------------------------------------------------

    def find_by_name(self, name: str) -> Optional[Person]:
        """Sucht eine Person nach Name oder Alias (Volltext)."""
        name_lower = name.lower()
        # Cache
        for person in self._cache.values():
            if (person.name.lower() == name_lower
                    or name_lower in [a.lower() for a in person.aliases]):
                return person
        # DB
        rows = self._db.fetchall("SELECT * FROM persons")
        for row in rows:
            p = Person(dict(row), self._db)
            if (p.name.lower() == name_lower
                    or name_lower in [a.lower() for a in p.aliases]):
                self._cache[p.id] = p
                return p
        return None

    def get_by_id(self, person_id: int) -> Optional[Person]:
        if person_id in self._cache:
            return self._cache[person_id]
        row = self._db.fetchone(
            "SELECT * FROM persons WHERE id=?", (person_id,)
        )
        if row:
            p = Person(dict(row), self._db)
            self._cache[p.id] = p
            return p
        return None

    def list_persons(self) -> List[Person]:
        """Gibt alle bekannten Personen zurück."""
        rows = self._db.fetchall(
            "SELECT * FROM persons ORDER BY last_seen DESC"
        )
        result = []
        for row in rows:
            p = self._cache.get(row["id"]) or Person(dict(row), self._db)
            self._cache[p.id] = p
            result.append(p)
        return result

    # ------------------------------------------------------------------
    # Beziehungspflege
    # ------------------------------------------------------------------

    def update_last_seen(self, person_id: int) -> None:
        person = self.get_by_id(person_id)
        if person:
            person.mark_seen()

    def adjust_trust(self, person_id: int, delta: float) -> None:
        person = self.get_by_id(person_id)
        if person:
            person.update_trust(delta)
            logger.debug(
                "Vertrauen für %s: %.2f (Δ%.2f).",
                person.name, person.trust_level, delta,
            )

    def remove_person(self, person_id: int) -> bool:
        """Löscht eine Person (auf Nutzerwunsch)."""
        rows = self._db.execute(
            "DELETE FROM persons WHERE id=?", (person_id,), commit=True
        ).rowcount
        self._cache.pop(person_id, None)
        return rows > 0
