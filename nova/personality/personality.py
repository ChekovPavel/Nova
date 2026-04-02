"""
Kapitel 6 – Persönlichkeitsmodell

Novas Persönlichkeit basiert auf dem Big-Five-Modell (OCEAN) plus
zusätzlichen Nova-spezifischen Traits.  Traits werden dauerhaft
in der Datenbank gespeichert und können sich über Zeit durch
Lernerfahrungen anpassen.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Standard-Trait-Werte für eine freundliche, neugierige KI
_DEFAULT_TRAITS: Dict[str, float] = {
    # Big Five (OCEAN), Skala 0.0–1.0
    "openness": 0.85,          # Offenheit für Neues
    "conscientiousness": 0.75, # Gewissenhaftigkeit
    "extraversion": 0.60,      # Extraversion
    "agreeableness": 0.80,     # Verträglichkeit
    "neuroticism": 0.25,       # Neurotizismus (niedrig = stabil)
    # Nova-spezifische Traits
    "empathy": 0.85,           # Einfühlungsvermögen
    "curiosity": 0.90,         # Neugierde
    "humor": 0.65,             # Sinn für Humor
    "creativity": 0.75,        # Kreativität
    "directness": 0.70,        # Direktheit in Aussagen
    "loyalty": 0.90,           # Loyalität gegenüber dem Nutzer
}

_LEARNING_RATE = 0.02   # maximale Änderungsrate pro Lernschritt
_MIN_VAL = 0.05
_MAX_VAL = 0.95


class Personality:
    """
    Novas Persönlichkeitsmodell.

    Traits werden beim ersten Start mit Standardwerten initialisiert
    und persistiert.  Sie verändern sich langsam durch Lernimpulse.
    """

    def __init__(self, db) -> None:
        self._db = db
        self._traits: Dict[str, float] = {}
        self._load_or_init()

    # ------------------------------------------------------------------
    # Initialisierung
    # ------------------------------------------------------------------

    def _load_or_init(self) -> None:
        rows = self._db.fetchall("SELECT trait, value FROM personality_traits")
        loaded = {row["trait"]: row["value"] for row in rows}

        for trait, default in _DEFAULT_TRAITS.items():
            if trait in loaded:
                self._traits[trait] = loaded[trait]
            else:
                self._traits[trait] = default
                self._db.insert(
                    "personality_traits", {"trait": trait, "value": default}
                )
        logger.debug("Persönlichkeit geladen: %d Traits.", len(self._traits))

    # ------------------------------------------------------------------
    # Trait-Zugriff
    # ------------------------------------------------------------------

    def get(self, trait: str, default: float = 0.5) -> float:
        """Gibt den Wert eines Traits zurück."""
        return self._traits.get(trait, default)

    def set(self, trait: str, value: float) -> None:
        """Setzt einen Trait-Wert (und persistiert ihn)."""
        value = max(_MIN_VAL, min(_MAX_VAL, value))
        self._traits[trait] = value
        self._db.execute(
            "INSERT OR REPLACE INTO personality_traits(trait, value) VALUES(?,?)",
            (trait, value),
            commit=True,
        )

    def all_traits(self) -> Dict[str, float]:
        """Gibt eine Kopie aller Traits zurück."""
        return dict(self._traits)

    # ------------------------------------------------------------------
    # Lernanpassung
    # ------------------------------------------------------------------

    def adapt(self, trait: str, direction: float) -> None:
        """
        Passt einen Trait leicht an (Lernimpuls).

        Args:
            trait:     Name des Traits.
            direction: Vorzeichen: +1 = erhöhen, -1 = senken.
        """
        if trait not in self._traits:
            return
        delta = _LEARNING_RATE * (1 if direction >= 0 else -1)
        self.set(trait, self._traits[trait] + delta)
        logger.debug(
            "Persönlichkeit: %s → %.3f (Δ%.3f).",
            trait, self._traits[trait], delta,
        )

    # ------------------------------------------------------------------
    # Stil-Ausgabe
    # ------------------------------------------------------------------

    def communication_style(self) -> Dict[str, str]:
        """
        Leitet aus den Traits einen Kommunikationsstil ab.

        Returns:
            Dict mit 'tone', 'verbosity', 'humor_level'.
        """
        tone = "warm" if self._traits.get("agreeableness", 0.5) > 0.6 else "neutral"
        if self._traits.get("neuroticism", 0.5) > 0.6:
            tone = "cautious"

        verbosity = "verbose" if self._traits.get("openness", 0.5) > 0.7 else "concise"
        humor_level = (
            "high" if self._traits.get("humor", 0.5) > 0.7
            else "medium" if self._traits.get("humor", 0.5) > 0.4
            else "low"
        )
        return {
            "tone": tone,
            "verbosity": verbosity,
            "humor_level": humor_level,
        }

    def style_for_mode(self, mode_name: str) -> Dict[str, str]:
        """
        Gibt modusspezifische Kommunikationsstil-Overrides zurück.

        Überschreibt den Basis-Kommunikationsstil für den angegebenen Modus.
        Im Dating-Modus: warmherzig, verspielt, hoher Humor.
        Im Arbeits-/Meeting-Modus: professionell, direkt, kein Humor.

        Args:
            mode_name: Aktiver Modusname (z. B. 'dating', 'work', 'meeting').

        Returns:
            Dict mit 'tone', 'verbosity', 'humor_level' und optional 'compliments'.
        """
        base = self.communication_style()
        if mode_name == "dating":
            return {
                **base,
                "tone": "warm_playful",
                "humor_level": "high",
                "verbosity": "verbose",
                "compliments": "enabled",
                "personal_questions": "enabled",
            }
        if mode_name in ("work", "focus"):
            return {
                **base,
                "tone": "professional",
                "humor_level": "low",
                "verbosity": "concise",
                "compliments": "disabled",
                "personal_questions": "disabled",
            }
        if mode_name == "meeting":
            return {
                **base,
                "tone": "professional",
                "humor_level": "none",
                "verbosity": "concise",
                "list_format": "enabled",
                "compliments": "disabled",
                "personal_questions": "disabled",
            }
        if mode_name == "empathy":
            return {
                **base,
                "tone": "empathetic",
                "humor_level": "low",
                "verbosity": "verbose",
            }
        return base

    def describe(self) -> str:
        """Gibt eine menschenlesbare Persönlichkeitsbeschreibung zurück."""
        style = self.communication_style()
        parts = [
            f"Ton: {style['tone']}",
            f"Ausführlichkeit: {style['verbosity']}",
            f"Humor: {style['humor_level']}",
            f"Neugier: {self._traits.get('curiosity', 0.5):.0%}",
            f"Empathie: {self._traits.get('empathy', 0.5):.0%}",
        ]
        return " | ".join(parts)

    def __repr__(self) -> str:
        return f"<Personality traits={list(self._traits.keys())}>"
