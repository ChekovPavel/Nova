"""
Kapitel 8 - Beziehungsmodell (bekannte Personen)

Verwaltet bekannte Personen mit ihren Profilen, Vertrauensstufen
und Interaktionshistorie.  Neue Personen werden nur auf expliziten
Wunsch des Nutzers angelegt.

Erweitert mit Dating-Profil-Feldern, Beziehungsstatus und
einer Ereignis-Timeline für persönliche und professionelle Kontakte.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Gültige Beziehungsstatus-Werte
RELATIONSHIP_STATUSES = (
    "stranger",
    "acquaintance",
    "crush",
    "dating",
    "partner",
    "ex",
    "colleague",
    "friend",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Person:
    """Repräsentiert eine bekannte Person."""

    def __init__(self, row: dict[str, Any], db) -> None:
        self._db = db
        self.id: int = row["id"]
        self.name: str = row["name"]
        self.aliases: list[str] = db.from_json(row.get("aliases", "[]"))
        self.profile: dict[str, Any] = db.from_json(row.get("profile", "{}"))
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
        self._db.update("persons", {"last_seen": self.last_seen}, "id=?", (self.id,))

    # ------------------------------------------------------------------
    # Dating & Beziehungs-Helfer
    # ------------------------------------------------------------------

    @property
    def relationship_status(self) -> str:
        """Gibt den Beziehungsstatus zurück (Standardwert: 'acquaintance')."""
        return self.profile.get("relationship_status", "acquaintance")

    def set_relationship_status(self, status: str) -> None:
        """
        Setzt den Beziehungsstatus.

        Args:
            status: Einer der Werte in RELATIONSHIP_STATUSES.
        """
        if status not in RELATIONSHIP_STATUSES:
            logger.warning("Unbekannter Beziehungsstatus: %r", status)
            return
        self.update_profile("relationship_status", status)
        logger.info("Beziehungsstatus für %s: %s.", self.name, status)

    def add_interest(self, interest: str) -> None:
        """Fügt ein Interesse zur Interessenliste der Person hinzu."""
        interests: list[str] = self.profile.get("interests", [])
        if interest not in interests:
            interests.append(interest)
            self.update_profile("interests", interests)

    def get_interests(self) -> list[str]:
        """Gibt die gespeicherten Interessen der Person zurück."""
        return list(self.profile.get("interests", []))

    def set_date_idea(self, idea: str) -> None:
        """Speichert eine Date-Idee für diese Person."""
        ideas: list[str] = self.profile.get("date_ideas", [])
        if idea not in ideas:
            ideas.append(idea)
            self.update_profile("date_ideas", ideas)

    def get_date_ideas(self) -> list[str]:
        """Gibt gespeicherte Date-Ideen zurück."""
        return list(self.profile.get("date_ideas", []))

    def set_compatibility_notes(self, notes: str) -> None:
        """Speichert Kompatibilitätsnotizen."""
        self.update_profile("compatibility_notes", notes)

    def dating_info(self) -> dict[str, Any]:
        """
        Gibt eine Zusammenfassung der Dating-relevanten Profilfelder zurück.

        Returns:
            Dict mit relationship_status, interests, date_ideas, compatibility_notes
            und trust_level.
        """
        return {
            "name": self.name,
            "relationship_status": self.relationship_status,
            "interests": self.get_interests(),
            "date_ideas": self.get_date_ideas(),
            "compatibility_notes": self.profile.get("compatibility_notes", ""),
            "trust_level": self.trust_level,
            "last_seen": self.last_seen,
        }

    def trust_label(self) -> str:
        """Gibt ein menschenlesbares Trust-Level-Label zurück."""
        if self.trust_level < 0.2:
            return "unbekannt"
        if self.trust_level < 0.4:
            return "flüchtige Bekanntschaft"
        if self.trust_level < 0.6:
            return "Bekanntschaft"
        if self.trust_level < 0.8:
            return "vertraut"
        return "sehr vertraut"

    def to_dict(self) -> dict[str, Any]:
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
        return f"<Person id={self.id} name={self.name!r} trust={self.trust_level:.2f} status={self.relationship_status!r}>"


class RelationshipModel:
    """
    Verwaltet bekannte Personen und deren Beziehungen zu Nova.

    Neue Personen werden **nur** auf explizite Anfrage des Nutzers
    angelegt (kein automatisches stilles Profiling).
    """

    def __init__(self, db) -> None:
        self._db = db
        self._cache: dict[int, Person] = {}

    # ------------------------------------------------------------------
    # Personen anlegen
    # ------------------------------------------------------------------

    def add_person(
        self,
        name: str,
        aliases: list[str] | None = None,
        profile: dict[str, Any] | None = None,
        trust_level: float = 0.5,
    ) -> Person:
        """
        Legt eine neue bekannte Person explizit an.

        Args:
            name:        Anzeigename.
            aliases:     Alternative Namen / Spitznamen.
            profile:     Anfangs-Profilwerte.
            trust_level: Anfängliche Vertrauensstufe (0-1).

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

    def find_by_name(self, name: str) -> Person | None:
        """Sucht eine Person nach Name oder Alias (Volltext)."""
        name_lower = name.lower()
        # Cache
        for person in self._cache.values():
            if person.name.lower() == name_lower or name_lower in [
                a.lower() for a in person.aliases
            ]:
                return person
        # DB
        rows = self._db.fetchall("SELECT * FROM persons")
        for row in rows:
            p = Person(dict(row), self._db)
            if p.name.lower() == name_lower or name_lower in [
                a.lower() for a in p.aliases
            ]:
                self._cache[p.id] = p
                return p
        return None

    def get_by_id(self, person_id: int) -> Person | None:
        if person_id in self._cache:
            return self._cache[person_id]
        row = self._db.fetchone("SELECT * FROM persons WHERE id=?", (person_id,))
        if row:
            p = Person(dict(row), self._db)
            self._cache[p.id] = p
            return p
        return None

    def list_persons(self) -> list[Person]:
        """Gibt alle bekannten Personen zurück."""
        rows = self._db.fetchall("SELECT * FROM persons ORDER BY last_seen DESC")
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
                person.name,
                person.trust_level,
                delta,
            )

    def remove_person(self, person_id: int) -> bool:
        """Löscht eine Person (auf Nutzerwunsch)."""
        rows = self._db.execute(
            "DELETE FROM persons WHERE id=?", (person_id,), commit=True
        ).rowcount
        self._cache.pop(person_id, None)
        return rows > 0

    # ------------------------------------------------------------------
    # Ereignis-Timeline
    # ------------------------------------------------------------------

    def add_timeline_event(
        self,
        person_id: int,
        event_type: str,
        description: str = "",
    ) -> int | None:
        """
        Fügt ein Ereignis zur Timeline einer Person hinzu.

        Args:
            person_id:   ID der Person.
            event_type:  Typ des Ereignisses (z. B. 'date', 'meeting',
                         'conversation', 'milestone').
            description: Optionale Beschreibung.

        Returns:
            Datenbank-ID des Eintrags oder None bei unbekannter Person.
        """
        if not self.get_by_id(person_id):
            logger.warning("Timeline: Person %d nicht gefunden.", person_id)
            return None
        entry_id = self._db.insert(
            "person_timeline",
            {
                "person_id": person_id,
                "event_type": event_type,
                "description": description,
                "timestamp": _now_iso(),
            },
        )
        logger.debug(
            "Timeline: %s-Ereignis für Person %d gespeichert (#%d).",
            event_type,
            person_id,
            entry_id,
        )
        return entry_id

    def get_timeline(
        self,
        person_id: int,
        event_type: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Gibt die Ereignis-Timeline einer Person zurück.

        Args:
            person_id:  ID der Person.
            event_type: Optionaler Filter für den Ereignistyp.
            limit:      Maximale Anzahl Einträge.

        Returns:
            Liste von Ereignis-Dicts (neueste zuerst).
        """
        if event_type:
            rows = self._db.fetchall(
                "SELECT * FROM person_timeline "
                "WHERE person_id=? AND event_type=? "
                "ORDER BY timestamp DESC LIMIT ?",
                (person_id, event_type, limit),
            )
        else:
            rows = self._db.fetchall(
                "SELECT * FROM person_timeline "
                "WHERE person_id=? "
                "ORDER BY timestamp DESC LIMIT ?",
                (person_id, limit),
            )
        return [dict(row) for row in rows]

    def last_event(
        self,
        person_id: int,
        event_type: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Gibt das jüngste Ereignis einer Person zurück.

        Args:
            person_id:  ID der Person.
            event_type: Optionaler Ereignistyp-Filter.

        Returns:
            Ereignis-Dict oder None.
        """
        events = self.get_timeline(person_id, event_type=event_type, limit=1)
        return events[0] if events else None

    def days_since_last_event(
        self,
        person_id: int,
        event_type: str | None = None,
    ) -> float | None:
        """
        Berechnet die Tage seit dem letzten Ereignis.

        Returns:
            Anzahl Tage (float) oder None falls kein Ereignis vorhanden.
        """
        event = self.last_event(person_id, event_type=event_type)
        if not event:
            return None
        try:
            last_ts = datetime.fromisoformat(event["timestamp"])
            delta = datetime.now(timezone.utc) - last_ts
            return delta.total_seconds() / 86400
        except (ValueError, KeyError):
            return None
