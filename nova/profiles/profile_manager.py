"""
Kapitel 24 – Kontext-Profilverwaltung

Trennt den Kontext von privaten und beruflichen Gesprächen.
Jedes Profil besitzt ein eigenes Kurzzeitgedächtnis (STM) und
einen eigenen Langzeitgedächtnis-Tag, so dass sich Dating-
und Arbeits-Kontext niemals vermischen.

Profile:
    private – für Dating, Relax, Empathie, Normal, Sleep
    work    – für Work, Meeting, Focus
"""

from __future__ import annotations

import logging
from typing import Any

from nova.memory.stm import ShortTermMemory

logger = logging.getLogger(__name__)

# Modi, die dem Arbeitsprofil zugeordnet sind
_WORK_MODES = frozenset({"work", "meeting", "focus"})


class ContextProfile:
    """Ein Kontextprofil mit eigenem STM und Session-Daten."""

    PRIVATE = "private"
    WORK = "work"

    def __init__(self, name: str, stm_capacity: int = 20) -> None:
        self.name: str = name
        self.stm: ShortTermMemory = ShortTermMemory(capacity=stm_capacity)
        self.topics: list[str] = []
        self.session_data: dict[str, Any] = {}

    def ltm_tag(self) -> str:
        """LTM-Tag, der Erinnerungen diesem Profil zuordnet."""
        return f"profile:{self.name}"

    def clear(self) -> None:
        """Löscht STM und Session-Daten (z. B. beim Profil-Reset)."""
        self.stm.clear()
        self.topics.clear()
        self.session_data.clear()
        logger.info("Kontextprofil '%s' zurückgesetzt.", self.name)

    def __repr__(self) -> str:
        return f"<ContextProfile name={self.name!r} stm_size={len(self.stm)}>"


class ProfileManager:
    """
    Verwaltet separate Kontextprofile für privaten und beruflichen Kontext.

    Beim Moduswechsel wird automatisch das passende Profil aktiviert:
    - work / meeting / focus  → Profil "work"
    - alle anderen Modi       → Profil "private"

    Das aktive Profil stellt sein STM zur Verfügung; Langzeitgedächtnis-
    Einträge werden mit dem Profil-Tag versehen, um eine spätere
    kontextbewusste Suche zu ermöglichen.
    """

    def __init__(self, stm_capacity: int = 20) -> None:
        self._profiles: dict[str, ContextProfile] = {
            ContextProfile.PRIVATE: ContextProfile(
                ContextProfile.PRIVATE, stm_capacity
            ),
            ContextProfile.WORK: ContextProfile(
                ContextProfile.WORK, stm_capacity
            ),
        }
        self._active_name: str = ContextProfile.PRIVATE

    # ------------------------------------------------------------------
    # Aktives Profil
    # ------------------------------------------------------------------

    @property
    def active(self) -> ContextProfile:
        """Gibt das aktive Kontextprofil zurück."""
        return self._profiles[self._active_name]

    @property
    def active_name(self) -> str:
        """Name des aktiven Profils ('private' oder 'work')."""
        return self._active_name

    def active_stm(self) -> ShortTermMemory:
        """Kurzform: STM des aktiven Profils."""
        return self.active.stm

    def active_ltm_tag(self) -> str:
        """LTM-Tag des aktiven Profils für kontextbewusstes Speichern."""
        return self.active.ltm_tag()

    # ------------------------------------------------------------------
    # Profilwechsel
    # ------------------------------------------------------------------

    def switch_for_mode(self, mode_name: str) -> str | None:
        """
        Wechselt das aktive Profil basierend auf dem Modus.

        Args:
            mode_name: Name des neuen Betriebsmodus.

        Returns:
            Name des neuen Profils, wenn ein Wechsel stattgefunden hat,
            sonst None.
        """
        target = ContextProfile.WORK if mode_name in _WORK_MODES else ContextProfile.PRIVATE
        if target != self._active_name:
            old = self._active_name
            self._active_name = target
            logger.info(
                "Kontextprofil gewechselt: %s → %s (Modus: %s).",
                old, target, mode_name,
            )
            return target
        return None

    def get_profile(self, name: str) -> ContextProfile | None:
        """Gibt ein Profil nach Name zurück."""
        return self._profiles.get(name)

    # ------------------------------------------------------------------
    # Informationen
    # ------------------------------------------------------------------

    def is_private(self) -> bool:
        """Gibt True zurück, wenn das private Profil aktiv ist."""
        return self._active_name == ContextProfile.PRIVATE

    def is_work(self) -> bool:
        """Gibt True zurück, wenn das Arbeitsprofil aktiv ist."""
        return self._active_name == ContextProfile.WORK

    def describe(self) -> str:
        profile = self.active
        return (
            f"Aktives Profil: {profile.name} | "
            f"STM-Einträge: {len(profile.stm)} | "
            f"LTM-Tag: {profile.ltm_tag()}"
        )

    def __repr__(self) -> str:
        return f"<ProfileManager active={self._active_name!r}>"
