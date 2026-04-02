"""
Kapitel 16.7 – Automatische Profil-Anreicherung

Erkennt neue Personenattribute in Gesprächstexten und aktualisiert
das Profil der aktiven Person automatisch.

Erkannte Felder:
  - interests   (Liste)  – Hobbys und Interessen
  - nationality (String) – Nationalität / Herkunftsland
  - job         (String) – Beruf / Tätigkeit
  - age         (int)    – Alter
  - city        (String) – Wohnort
  - languages   (Liste)  – Gesprochene Sprachen

Prinzip: Nur explizite Ich-Aussagen werden verarbeitet (z. B.
"ich mag Tennis", "ich komme aus Berlin"), um Fehlzuordnungen zu
vermeiden. Neue Werte werden in das Person-Profil UND ins LTM
geschrieben.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Erkennungsmuster
# Tupel-Format: (feld, pattern, gruppe, normalisierungs-callable_oder_None)
# ---------------------------------------------------------------------------
_PATTERNS: list[tuple[str, str, int, Any | None]] = [
    # --- Interessen / Hobbys ------------------------------------------------
    # "mein Hobby ist X" / "meine Hobbys sind X, Y"
    (
        "interests",
        r"mein(?:e)?\s+hobbys?\s+(?:sind?|ist)\s+(.+?)(?:\.|!|$)",
        1, None,
    ),
    # "in meiner Freizeit mache/spiele/treibe/lese/fahre ich X"
    (
        "interests",
        r"in meiner freizeit\s+(?:\w+\s+)?(?:ich\s+)?(.+?)(?:\.|!|$)",
        1, None,
    ),
    # "ich spiele gern(e) X / ich mache gern(e) X / ich treibe gern X"
    (
        "interests",
        r"ich\s+(?:spiele|mache|treibe|fahre|lese|sehe|schaue)\s+gern(?:e)?\s+(.+?)(?:\.|!|,|$)",
        1, None,
    ),
    # "ich interessiere mich für X"
    (
        "interests",
        r"ich\s+interessiere\s+mich\s+für\s+(.+?)(?:\.|!|,|$)",
        1, None,
    ),
    # "ich mag X" (kurz, häufig)
    (
        "interests",
        r"ich\s+mag\s+(?:auch\s+)?(.+?)(?:\.|!|,|$)",
        1, None,
    ),
    # "ich liebe X" (stärker)
    (
        "interests",
        r"ich\s+liebe\s+(?:auch\s+)?(.+?)(?:\.|!|,|$)",
        1, None,
    ),

    # --- Nationalität / Herkunft --------------------------------------------
    # "ich komme aus [Land]"
    (
        "nationality",
        r"ich\s+komme\s+aus\s+([A-ZÄÖÜ][a-zäöüß]+(?:[\s-][A-ZÄÖÜ][a-zäöüß]+)*)",
        1, None,
    ),
    # "meine Nationalität / Herkunft ist X"
    (
        "nationality",
        r"meine\s+(?:nationalität|herkunft|heimat)\s+ist\s+(.+?)(?:\.|!|,|$)",
        1, None,
    ),
    # "ich bin Deutscher / Österreicherin / Türke ..."  (Nationalitäts-Adjektive)
    (
        "nationality",
        r"ich\s+bin\s+(Deutsch(?:er|e|in)?|Oesterreich(?:er|erin)?|"
        r"Schweizer(?:in)?|Tuerk(?:e|in)?|Itali(?:ener|enerin)?|"
        r"Franzos(?:e|in)|Spanier(?:in)?|Amerikan(?:er|erin)?|"
        r"Brit(?:e|in)?|Russe|Russin|Pol(?:e|in)|Japan(?:er|erin)?|"
        r"Chinese|Chinesin|Indi(?:er|erin)?|Grieche|Griechin|"
        r"Ungar(?:in)?|Niederlaend(?:er|erin)?|"
        r"Belgi(?:er|erin)?|Schwed(?:e|in)?|Norweg(?:er|erin)?|"
        r"Daen(?:e|in)?|Finn(?:e|in)?|Portugies(?:e|in)?)",
        1, None,
    ),

    # --- Beruf / Tätigkeit --------------------------------------------------
    # "ich arbeite als X"
    (
        "job",
        r"ich\s+arbeite\s+als\s+(.+?)(?:\.|!|,|$)",
        1, str.strip,
    ),
    # "ich bin X von Beruf"
    (
        "job",
        r"ich\s+bin\s+(.+?)\s+von\s+beruf",
        1, str.strip,
    ),
    # "mein Beruf / Job / Arbeit ist X"
    (
        "job",
        r"mein(?:e)?\s+(?:beruf|job|arbeit|stelle|position)\s+ist\s+(.+?)(?:\.|!|,|$)",
        1, str.strip,
    ),
    # "ich studiere X" / "ich bin Student der X"
    (
        "job",
        r"ich\s+studiere\s+(.+?)(?:\.|!|,|$)",
        1, lambda s: f"Student ({s.strip()})",
    ),

    # --- Alter --------------------------------------------------------------
    # "ich bin 25 Jahre alt" / "ich bin 25"
    (
        "age",
        r"ich\s+bin\s+(\d{1,3})\s+jahre?(?:\s+alt)?",
        1, int,
    ),

    # --- Wohnort / Stadt ----------------------------------------------------
    # "ich wohne in X" / "ich lebe in X"
    (
        "city",
        r"ich\s+(?:wohne|lebe)\s+in\s+([A-ZÄÖÜ][a-zäöüß]+(?:[\s-][A-ZÄÖÜ][a-zäöüß]+)*)",
        1, None,
    ),
    # "ich bin in X aufgewachsen"
    (
        "city",
        r"ich\s+bin\s+in\s+([A-ZÄÖÜ][a-zäöüß]+(?:[\s-][A-ZÄÖÜ][a-zäöüß]+)*)\s+aufgewachsen",
        1, None,
    ),

    # --- Sprachen -----------------------------------------------------------
    # "ich spreche (auch) X"
    (
        "languages",
        r"ich\s+spreche\s+(?:auch\s+)?([A-ZÄÖÜ]?[a-zäöüß]+(?:isch)?)",
        1, None,
    ),
    # "meine Muttersprache ist X"
    (
        "languages",
        r"meine\s+muttersprache\s+ist\s+([A-ZÄÖÜ]?[a-zäöüß]+)",
        1, None,
    ),
]

# Wörter, die als Hobby/Interesse zu kurz oder zu generisch sind
_INTEREST_STOPWORDS = {
    "dich", "mich", "das", "die", "der", "es", "ihn", "sie", "wir",
    "uns", "euch", "auch", "sehr", "nicht", "noch", "mal",
    "doch", "gar", "kein", "keine", "halt", "ja", "nein",
}

# Maximale Länge für einen Interessenswert.
# Werte über ~40 Zeichen sind wahrscheinlich ganze Sätze statt echte Interessen
# (z. B. "ich mag es, wenn das Wetter schön ist" → zu lang, kein Hobby).
_MAX_INTEREST_LEN = 40


def _clean_interest(value: str) -> str | None:
    """Bereinigt und validiert einen Interessenswert."""
    value = value.strip().rstrip(".,!?")
    # Zu lang → wahrscheinlich ein ganzer Satz
    if len(value) > _MAX_INTEREST_LEN:
        return None
    # Zu kurz oder Stopwort
    if len(value) < 3 or value.lower() in _INTEREST_STOPWORDS:
        return None
    return value


def _split_list_value(value: str) -> list[str]:
    """Splittet 'A, B und C' in ['A', 'B', 'C']."""
    # Erst " und " / " & " trennen, dann Komma
    value = re.sub(r"\s+(?:und|&|sowie)\s+", ",", value, flags=re.IGNORECASE)
    return [v.strip() for v in value.split(",") if v.strip()]


class ProfileEnricher:
    """
    Erkennt neue Personenattribute in Gesprächstexten und
    aktualisiert das Personenprofil automatisch.

    Wird in der MainLoop nach jeder Benutzernachricht aufgerufen,
    sofern eine aktive Person gesetzt ist.
    """

    def __init__(self, ltm) -> None:
        self._ltm = ltm

    # ------------------------------------------------------------------
    # Haupt-Methode
    # ------------------------------------------------------------------

    def enrich_from_text(
        self,
        person,
        text: str,
    ) -> dict[str, Any]:
        """
        Analysiert ``text`` auf neue Profilattribute und speichert
        Neuigkeiten in person.profile und im LTM.

        Args:
            person: Person-Objekt (muss update_profile() unterstützen).
            text:   Nutzereingabe.

        Returns:
            Dict mit neu hinzugefügten Attributen, z. B.:
            {"interests": ["Tennis"], "nationality": "Deutsch"}.
            Leeres Dict, wenn nichts Neues erkannt wurde.
        """
        added: dict[str, Any] = {}
        text_lower = text  # Patterns nutzen re.IGNORECASE

        for field, pattern, group, transform in _PATTERNS:
            for match in re.finditer(pattern, text_lower, re.IGNORECASE):
                try:
                    raw_value = match.group(group).strip()
                except IndexError:
                    continue

                if not raw_value:
                    continue

                # Transformation anwenden (z. B. int, strip, lambda)
                try:
                    value = transform(raw_value) if transform else raw_value
                except (ValueError, TypeError):
                    continue

                if field in ("interests", "languages"):
                    # Listenfeld – jeden Einzelwert prüfen
                    items = _split_list_value(str(value))
                    for item in items:
                        cleaned = _clean_interest(item)
                        if cleaned is None:
                            continue
                        new_items = self._add_to_list_field(
                            person, field, cleaned
                        )
                        if new_items:
                            added.setdefault(field, []).extend(new_items)

                else:
                    # Skalares Feld – nur überschreiben wenn wirklich neu
                    new_value = self._update_scalar_field(
                        person, field, value
                    )
                    if new_value is not None:
                        added[field] = new_value

        if added:
            logger.info(
                "ProfileEnricher: %s – neue Attribute: %s",
                person.name, added,
            )
            self._store_in_ltm(person, added)

        return added

    # ------------------------------------------------------------------
    # Interne Helfer
    # ------------------------------------------------------------------

    def _add_to_list_field(
        self, person, field: str, new_item: str
    ) -> list[str]:
        """
        Fügt new_item zu einem Listenfeld hinzu, falls es noch nicht
        enthalten ist. Gibt Liste der tatsächlich hinzugefügten Elemente zurück.
        """
        existing: list[str] = person.profile.get(field, [])
        existing_lower = [e.lower() for e in existing]
        if new_item.lower() in existing_lower:
            return []  # Bereits vorhanden

        updated = [*list(existing), new_item]
        person.update_profile(field, updated)
        return [new_item]

    def _update_scalar_field(
        self, person, field: str, new_value: Any
    ) -> Any | None:
        """
        Aktualisiert ein skalares Profilfeld, wenn es noch nicht gesetzt
        oder leer ist. Gibt den neuen Wert zurück (oder None wenn schon da).
        """
        existing = person.profile.get(field)
        if existing is not None and str(existing).strip():
            # Nur wenn tatsächlich etwas Neues kam (andere Werte)
            if str(existing).lower() == str(new_value).lower():
                return None
            # Wert hat sich geändert – aktualisieren
            person.update_profile(field, new_value)
            return new_value
        # Noch nicht gesetzt
        person.update_profile(field, new_value)
        return new_value

    def _store_in_ltm(self, person, added: dict[str, Any]) -> None:
        """Speichert neu erkannte Attribute als Fakten im LTM."""
        for field, value in added.items():
            if isinstance(value, list):
                for item in value:
                    content = f"{person.name} {field}: {item}"
                    self._ltm.store(
                        content=content,
                        category="person",
                        importance=0.75,
                        tags=[person.name.lower(), field, "auto_enriched"],
                    )
            else:
                content = f"{person.name} {field}: {value}"
                self._ltm.store(
                    content=content,
                    category="person",
                    importance=0.75,
                    tags=[person.name.lower(), field, "auto_enriched"],
                )
