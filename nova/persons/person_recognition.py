"""
Kapitel 16 – Personenerkennung & Profiling

Erkennt, welche Person gerade mit Nova spricht (basierend auf
Stimme, Name oder selbst angegebenen Informationen) und lädt
das entsprechende Profil.

Neue Personen werden bei expliziter Selbstvorstellung ("ich heiße X")
automatisch angelegt; stilles Profiling unbekannter Dritter findet
nicht statt.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Muster, mit denen ein Nutzer seinen Namen angibt
_NAME_PATTERNS = [
    r"(?:ich heiße|ich heisse|ich bin|mein name ist|nennen sie mich|nenn mich)\s+([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*)",
    r"(?:i am|my name is|call me|i'm)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
]


class PersonRecognition:
    """
    Erkennt und verwaltet die Identität des Gesprächspartners.

    - Erkennt Namensangaben im Text
    - Lädt bekannte Profile aus dem RelationshipModel
    - Legt auf expliziten Wunsch neue Profile an
    """

    def __init__(self, relationship_model) -> None:
        self._rel = relationship_model
        self._active_person_id: Optional[int] = None

    # ------------------------------------------------------------------
    # Aktive Person
    # ------------------------------------------------------------------

    @property
    def active_person_id(self) -> Optional[int]:
        return self._active_person_id

    def set_active(self, person_id: Optional[int]) -> None:
        """Setzt die aktuell aktive Person."""
        self._active_person_id = person_id
        if person_id:
            self._rel.update_last_seen(person_id)
            logger.info("Aktive Person: ID %d.", person_id)

    def get_active_person(self):
        """Gibt das Person-Objekt der aktiven Person zurück (oder None)."""
        if self._active_person_id is None:
            return None
        return self._rel.get_by_id(self._active_person_id)

    # ------------------------------------------------------------------
    # Namensextraktion
    # ------------------------------------------------------------------

    def extract_name_from_text(self, text: str) -> Optional[str]:
        """
        Versucht, einen Eigennamen aus dem Text zu extrahieren.

        Returns:
            Erkannter Name oder None.
        """
        for pattern in _NAME_PATTERNS:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    # ------------------------------------------------------------------
    # Identifikation
    # ------------------------------------------------------------------

    def identify_from_text(self, text: str) -> Optional[int]:
        """
        Analysiert Text nach Selbstidentifikation.

        Wenn eine bekannte Person gefunden wird, wird sie als aktiv gesetzt.
        Wenn der Nutzer sich neu vorstellt (``ich heiße X`` / ``mein Name ist X``),
        wird automatisch ein neues Profil angelegt und aktiviert.

        Returns:
            Person-ID oder None.
        """
        name = self.extract_name_from_text(text)
        if not name:
            return self._active_person_id

        person = self._rel.find_by_name(name)
        if person:
            self.set_active(person.id)
            logger.info("Person erkannt: %s (ID %d).", name, person.id)
            return person.id

        # Selbstvorstellung ("ich heiße X", "mein Name ist X") → auto-registrieren
        text_lower = text.lower()
        self_intro = any(
            pat in text_lower
            for pat in ("ich heiße", "ich heisse", "mein name ist", "ich bin ")
        )
        if self_intro:
            person = self.register_new_person(name, trust_level=0.8)
            logger.info(
                "Neue Person (Selbstvorstellung) angelegt: %s (ID %d).",
                name, person.id,
            )
            return person.id

        # Fremde Person, kein automatisches Anlegen
        logger.info("Unbekannte Person genannt: %r – warte auf Bestätigung.", name)
        return self._active_person_id

    def register_new_person(
        self,
        name: str,
        profile: Optional[Dict] = None,
        trust_level: float = 0.5,
    ):
        """
        Legt eine neue Person explizit an (nach Nutzerbestätigung).

        Returns:
            Person-Objekt.
        """
        person = self._rel.add_person(
            name=name, profile=profile or {}, trust_level=trust_level
        )
        self.set_active(person.id)
        return person

    # ------------------------------------------------------------------
    # Abmelden
    # ------------------------------------------------------------------

    def logout(self) -> None:
        """Setzt den aktiven Gesprächspartner zurück (Session-Ende)."""
        self._active_person_id = None
        logger.debug("Aktive Person zurückgesetzt.")
