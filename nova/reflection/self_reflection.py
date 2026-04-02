"""
Kapitel 13 - Selbstreflexion

Nova reflektiert periodisch über ihren eigenen Zustand:
Emotionen, Ziele, Persönlichkeit und Erinnerungen.
Ergebnisse können in Gesprächen geteilt oder ins LTM gespeichert werden.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_REFLECTION_INTERVAL = 300  # Sekunden zwischen automatischen Reflexionen


@dataclass
class ReflectionResult:
    """Ergebnis einer Selbstreflexion."""

    emotional_state: str
    mood_modifier: str
    top_goal: str | None
    personality_summary: str
    recent_learnings: list[str] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.monotonic)


class SelfReflection:
    """
    Ermöglicht Nova die Reflexion über ihren eigenen Zustand.

    Kombiniert Informationen aus:
    - Emotionsmotor
    - Persönlichkeit
    - Ziele
    - LTM (jüngste Erinnerungen)
    """

    def __init__(self, personality, emotion, goals, ltm) -> None:
        self._personality = personality
        self._emotion = emotion
        self._goals = goals
        self._ltm = ltm
        self._last_reflection: ReflectionResult | None = None
        self._last_reflection_time: float = 0.0

    # ------------------------------------------------------------------
    # Reflexion ausführen
    # ------------------------------------------------------------------

    def reflect(self, force: bool = False) -> ReflectionResult:
        """
        Führt eine Selbstreflexion durch.

        Args:
            force: Wenn True, wird auch vor Ablauf des Intervalls reflektiert.

        Returns:
            ReflectionResult.
        """
        now = time.monotonic()
        if (
            not force
            and (now - self._last_reflection_time) < _REFLECTION_INTERVAL
            and self._last_reflection
        ):
            return self._last_reflection

        emotion = self._emotion.state
        mood = self._emotion.mood_modifier()
        top_goal = self._goals.get_top_priority()
        personality_desc = self._personality.describe()
        style = self._personality.communication_style()

        recent_mems = self._ltm.recall(limit=3, min_importance=0.5)
        learnings = [m.get("content", "")[:60] for m in recent_mems]

        insights = self._generate_insights(emotion, style, top_goal)

        result = ReflectionResult(
            emotional_state=emotion.label,
            mood_modifier=mood,
            top_goal=top_goal.title if top_goal else None,
            personality_summary=personality_desc,
            recent_learnings=learnings,
            insights=insights,
        )
        self._last_reflection = result
        self._last_reflection_time = now
        logger.debug("Selbstreflexion durchgeführt: %s", emotion.label)
        return result

    # ------------------------------------------------------------------
    # Einsichten generieren
    # ------------------------------------------------------------------

    def _generate_insights(self, emotion, style: dict[str, str], top_goal) -> list[str]:
        insights = []

        # Emotionaler Einblick
        if emotion.intensity > 0.6:
            insights.append(
                f"Ich bemerke eine starke Emotion: {emotion.label}. "
                "Das beeinflusst möglicherweise meine Antworten."
            )
        elif emotion.label == "neutral":
            insights.append("Mein emotionaler Zustand ist ausgeglichen.")

        # Ziel-Einblick
        if top_goal:
            insights.append(
                f'Ich priorisiere gerade das Ziel "{top_goal.title}". '
                "Das motiviert meine Handlungen."
            )

        # Persönlichkeits-Einblick
        openness = self._personality.get("openness")
        if openness > 0.8:
            insights.append(
                "Meine hohe Offenheit für Neues hilft mir, flexibel zu bleiben."
            )

        empathy = self._personality.get("empathy")
        if empathy > 0.8:
            insights.append(
                "Mein starkes Einfühlungsvermögen ermöglicht tiefere Verbindungen."
            )

        return insights

    # ------------------------------------------------------------------
    # Beschreibung für Antwortgenerierung
    # ------------------------------------------------------------------

    def as_text(self, force: bool = False) -> str:
        """Gibt die Reflexion als lesbaren Text zurück."""
        r = self.reflect(force=force)
        parts = [
            f"Aktueller Zustand: {r.mood_modifier} ({r.emotional_state}).",
            f"Persönlichkeit: {r.personality_summary}.",
        ]
        if r.top_goal:
            parts.append(f"Wichtigstes Ziel: {r.top_goal}.")
        if r.insights:
            parts.append("Einblick: " + r.insights[0])
        return " ".join(parts)

    def quick_status(self) -> dict[str, Any]:
        """Gibt einen kompakten Status-Dict zurück."""
        r = self.reflect()
        return {
            "emotion": r.emotional_state,
            "mood": r.mood_modifier,
            "goal": r.top_goal,
            "personality": r.personality_summary,
        }

    # ------------------------------------------------------------------
    # Meeting-Zusammenfassung
    # ------------------------------------------------------------------

    def summarize_meeting(self, stm_entries: list | None = None) -> str:
        """
        Erstellt eine Zusammenfassung des letzten Meetings aus STM-Einträgen.

        Args:
            stm_entries: Liste von STMEntry-Objekten (oder None für leere Zusammenfassung).

        Returns:
            Formatierter Zusammenfassungstext.
        """
        if not stm_entries:
            return "📋 Meeting beendet. Keine Gesprächseinträge vorhanden."

        messages = [
            e.content
            for e in stm_entries
            if hasattr(e, "content") and isinstance(e.content, dict)
        ]
        user_msgs = [m.get("text", "") for m in messages if m.get("role") == "user"]
        nova_msgs = [m.get("text", "") for m in messages if m.get("role") == "nova"]

        parts = ["📋 Meeting-Zusammenfassung:"]
        parts.append(
            f"• {len(user_msgs)} Nutzereingaben, {len(nova_msgs)} Nova-Antworten."
        )

        if user_msgs:
            first_topic = user_msgs[0][:80].rstrip()
            parts.append(
                f"• Erstes Thema: {first_topic}{'…' if len(user_msgs[0]) > 80 else ''}"
            )

        if len(user_msgs) > 1:
            last_topic = user_msgs[-1][:80].rstrip()
            parts.append(
                f"• Letztes Thema: {last_topic}{'…' if len(user_msgs[-1]) > 80 else ''}"
            )

        # Aktuelle Ziele einbeziehen
        top_goal = self._goals.get_top_priority()
        if top_goal:
            parts.append(f"• Relevantes Ziel: {top_goal.title}")

        parts.append(
            "Meeting abgeschlossen. Zusammenfassung im Langzeitgedächtnis gespeichert."
        )
        return "\n".join(parts)
