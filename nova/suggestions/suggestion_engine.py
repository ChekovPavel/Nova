"""
Kapitel 25 – Vorschlags-Engine

Generiert kontextbezogene Vorschläge für Dating und Arbeit:

- **Dating**: Date-Ideen basierend auf den gespeicherten Interessen
  einer Person.
- **Arbeit**: Meeting-Agendas und Aufgaben-Vorschläge basierend auf
  offenen Zielen.

Die Engine ist bewusst regelbasiert gehalten und benötigt kein LLM.
Wenn ein LLM verfügbar ist, können die Vorschläge als Prompt-Kontext
weitergegeben werden.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Fallback-Date-Ideen nach Kategorie (wenn keine Interessen bekannt)
_GENERIC_DATE_IDEAS: List[str] = [
    "Gemeinsames Kochen eines neuen Rezepts",
    "Spaziergang in einem Park oder am Wasser",
    "Besuch eines Flohmarkts oder Antiquitätenladens",
    "Kinoabend mit Wunschfilm",
    "Miniature-Golf oder Bowling",
    "Museumsbesuch",
    "Escape Room",
    "Konzert oder Livemusik",
    "Picknick im Freien",
    "Gemeinsames Brettspiel-Abend",
]

# Date-Ideen nach Interessengebiet
_DATE_IDEAS_BY_INTEREST: Dict[str, List[str]] = {
    "musik": [
        "Livekonzert besuchen",
        "Gemeinsam Musik entdecken und Playlists tauschen",
        "Karaoke-Abend",
    ],
    "sport": [
        "Kletterpark oder Bouldern ausprobieren",
        "Gemeinsam joggen oder Fahrrad fahren",
        "Sportveranstaltung besuchen",
    ],
    "kochen": [
        "Kochkurs zusammen besuchen",
        "Rezepte aus einer fremden Küche nachkochen",
        "Farmers Market erkunden und spontan kochen",
    ],
    "natur": [
        "Wanderung mit Picknick",
        "Botanischen Garten besuchen",
        "Sternenhimmel beobachten",
    ],
    "kunst": [
        "Galerie oder Ausstellung besuchen",
        "Gemeinsam malen oder zeichnen",
        "Töpfer-Workshop",
    ],
    "lesen": [
        "Buchhandlung erkunden und gegenseitig ein Buch aussuchen",
        "Gemeinsam ein Buch lesen und besprechen",
        "Literaturfestival besuchen",
    ],
    "reisen": [
        "Spontaner Tagesausflug in eine unbekannte Stadt",
        "Gemeinsam eine Reise planen",
        "Lokale Sehenswürdigkeiten wie Touristen erkunden",
    ],
    "film": [
        "Kinoabend mit Filmreihe",
        "Outdoor-Kino",
        "Film-Trivia-Abend",
    ],
    "technologie": [
        "Tech-Messe oder Maker Faire besuchen",
        "Escape Room mit technischer Note",
        "Computerspiele-Abend",
    ],
    "tiere": [
        "Tierheim besuchen und Tiere streicheln",
        "Zoo oder Tierpark",
        "Reiterausflug",
    ],
}


class SuggestionEngine:
    """
    Generiert kontextbewusste Vorschläge für Dating und professionelle Aktivitäten.

    Verwendet gespeicherte Personen-Interessen und offene Ziele als Basis.
    """

    def __init__(self, relationships, goals) -> None:
        """
        Args:
            relationships: RelationshipModel-Instanz.
            goals:         GoalManager-Instanz.
        """
        self._rel = relationships
        self._goals = goals

    # ------------------------------------------------------------------
    # Dating-Vorschläge
    # ------------------------------------------------------------------

    def date_ideas(
        self,
        person_id: Optional[int] = None,
        max_ideas: int = 5,
    ) -> List[str]:
        """
        Schlägt Date-Ideen vor, basierend auf den Interessen der Person.

        Args:
            person_id: ID der Person (optional). Falls None, werden
                       generische Ideen zurückgegeben.
            max_ideas: Maximale Anzahl an Vorschlägen.

        Returns:
            Liste von Date-Ideen als Strings.
        """
        ideas: List[str] = []
        interests: List[str] = []

        if person_id is not None:
            person = self._rel.get_by_id(person_id)
            if person:
                interests = [i.lower() for i in person.get_interests()]
                # Gespeicherte date_ideas direkt einfügen
                stored = person.get_date_ideas()
                ideas.extend(stored)

        # Ideen nach Interessen ergänzen
        for interest in interests:
            for keyword, themed_ideas in _DATE_IDEAS_BY_INTEREST.items():
                if keyword in interest:
                    ideas.extend(themed_ideas)

        # Generische Ideen auffüllen
        if len(ideas) < max_ideas:
            for idea in _GENERIC_DATE_IDEAS:
                if idea not in ideas:
                    ideas.append(idea)

        # Deduplizieren und Limit einhalten
        seen: set = set()
        result: List[str] = []
        for idea in ideas:
            if idea not in seen:
                seen.add(idea)
                result.append(idea)
            if len(result) >= max_ideas:
                break

        logger.debug("SuggestionEngine: %d Date-Ideen generiert.", len(result))
        return result

    def date_ideas_text(
        self,
        person_id: Optional[int] = None,
        max_ideas: int = 5,
    ) -> str:
        """
        Gibt Date-Ideen als formatierten Text zurück.

        Args:
            person_id: ID der Person (optional).
            max_ideas: Maximale Anzahl an Vorschlägen.

        Returns:
            Formatierter Vorschlagstext.
        """
        person_name = "euch"
        if person_id is not None:
            person = self._rel.get_by_id(person_id)
            if person:
                person_name = person.name

        ideas = self.date_ideas(person_id=person_id, max_ideas=max_ideas)
        if not ideas:
            return "Ich habe leider keine Date-Ideen gefunden."

        lines = [f"💘 Date-Ideen für {person_name}:"]
        for i, idea in enumerate(ideas, 1):
            lines.append(f"  {i}. {idea}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Arbeits-Vorschläge
    # ------------------------------------------------------------------

    def meeting_agenda(
        self,
        topic: str = "",
        participants: Optional[List[str]] = None,
        duration_minutes: int = 60,
    ) -> List[str]:
        """
        Generiert eine Meeting-Agenda.

        Args:
            topic:            Hauptthema des Meetings.
            participants:     Teilnehmerliste (optional).
            duration_minutes: Geplante Dauer in Minuten.

        Returns:
            Agenda als Liste von Punkten.
        """
        agenda: List[str] = []
        if participants:
            agenda.append(f"Teilnehmer: {', '.join(participants)}")
        agenda.append(f"Dauer: {duration_minutes} Minuten")
        agenda.append("─" * 30)
        agenda.append("1. Begrüßung & Ziele des Meetings (5 min)")
        if topic:
            agenda.append(f"2. Hauptthema: {topic} ({duration_minutes - 20} min)")
        else:
            agenda.append(f"2. Hauptthema besprechen ({duration_minutes - 20} min)")
        agenda.append("3. Offene Punkte & Fragen (10 min)")
        agenda.append("4. Nächste Schritte & Verantwortlichkeiten (5 min)")
        agenda.append("5. Zusammenfassung & Abschluss")
        logger.debug("SuggestionEngine: Meeting-Agenda für '%s' erstellt.", topic)
        return agenda

    def meeting_agenda_text(
        self,
        topic: str = "",
        participants: Optional[List[str]] = None,
        duration_minutes: int = 60,
    ) -> str:
        """Gibt die Meeting-Agenda als formatierten Text zurück."""
        title = f"📋 Meeting-Agenda" + (f": {topic}" if topic else "")
        lines = [title] + self.meeting_agenda(topic, participants, duration_minutes)
        return "\n".join(lines)

    def work_task_suggestions(self, max_tasks: int = 5) -> List[str]:
        """
        Schlägt offene Arbeitsaufgaben basierend auf dem GoalManager vor.

        Args:
            max_tasks: Maximale Anzahl Vorschläge.

        Returns:
            Liste von Aufgaben-Strings.
        """
        tasks: List[str] = []
        try:
            open_goals = self._goals.list_goals(status="open")
            for goal in open_goals[:max_tasks]:
                tasks.append(goal.title)
        except Exception as exc:
            logger.warning("Aufgaben-Vorschläge: Fehler beim Abrufen der Ziele: %s", exc)

        if not tasks:
            tasks = [
                "Offene E-Mails beantworten",
                "Aufgabenliste für heute priorisieren",
                "Meeting-Notizen nachbereiten",
                "Status-Update an Team senden",
                "Dokumentation aktualisieren",
            ]
        logger.debug("SuggestionEngine: %d Aufgaben-Vorschläge.", len(tasks))
        return tasks[:max_tasks]

    def work_task_suggestions_text(self, max_tasks: int = 5) -> str:
        """Gibt Aufgaben-Vorschläge als formatierten Text zurück."""
        tasks = self.work_task_suggestions(max_tasks=max_tasks)
        lines = ["💼 Aufgaben-Vorschläge:"]
        for i, task in enumerate(tasks, 1):
            lines.append(f"  {i}. {task}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Kontext-Vorschläge (modus-abhängig)
    # ------------------------------------------------------------------

    def suggest_for_context(
        self,
        mode_name: str,
        person_id: Optional[int] = None,
        topic: str = "",
    ) -> str:
        """
        Wählt automatisch passende Vorschläge basierend auf dem aktiven Modus.

        Args:
            mode_name: Aktiver Modus ('dating', 'work', 'meeting', ...).
            person_id: ID der aktiven Person (für Dating-Kontext).
            topic:     Thema (für Meeting-Kontext).

        Returns:
            Formatierter Vorschlagstext.
        """
        if mode_name == "dating":
            return self.date_ideas_text(person_id=person_id)
        if mode_name == "meeting":
            return self.meeting_agenda_text(topic=topic)
        if mode_name in ("work", "focus"):
            return self.work_task_suggestions_text()
        return ""

    def __repr__(self) -> str:
        return "<SuggestionEngine>"
