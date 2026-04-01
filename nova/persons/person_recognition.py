"""
Kapitel 16 – Personenerkennung & Profiling

Erkennt, welche Person gerade mit Nova spricht (basierend auf
Stimme, Name oder selbst angegebenen Informationen) und lädt
das entsprechende Profil.

Hinweis: Automatisches stilles Profiling unbekannter Dritter
(Kapitel 16.6) ist bewusst nicht implementiert.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Muster, mit denen ein Nutzer seinen Namen angibt
_NAME_PATTERNS = [
    r"(?:ich heiße|ich bin|mein name ist|nennen sie mich|nenn mich)\s+([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*)",
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
        Wenn eine neue Person erkannt wird, wird auf explizite Bestätigung
        gewartet (kein automatisches Anlegen).

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

        # Unbekannt – kein automatisches Anlegen, nur melden
        logger.info("Unbekannte Person genannt: %r – warte auf Bestätigung.", name)
        return None

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
