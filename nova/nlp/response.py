"""
Kapitel 4 – Antwortgenerierung

Erstellt Novas Antworten auf Basis von:
- Intent des NLP-Ergebnisses
- Aktuellem Emotionszustand
- Persönlichkeitstil
- Kontext (aktive Person, Themen)
- SocialSafetyLayer-Prüfung

Kann optional an ein LLM-Backend (Kapitel 20) delegieren.
"""

from __future__ import annotations

import logging
import random
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """
    Generiert Novas textuelle Antworten.

    Strategie:
    1. SocialSafetyLayer prüft Eingabe und Ausgabe
    2. Intent-spezifische Vorlage wird ausgewählt
    3. Stimmungsmodifikator (Emotion) wird eingebaut
    4. Persönlichkeitsstil wird angewendet
    5. Optional: LLM-Delegation für komplexe Antworten
    """

    def __init__(
        self,
        personality,
        emotion,
        context_manager,
        social_safety,
        llm_client=None,
    ) -> None:
        self._personality = personality
        self._emotion = emotion
        self._context = context_manager
        self._safety = social_safety
        self._llm = llm_client  # optional, wird in Kap 20 gesetzt

    # ------------------------------------------------------------------
    # Hauptmethode
    # ------------------------------------------------------------------

    def generate(
        self,
        nlp_result,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Erzeugt eine Antwort auf ein NLPResult.

        Args:
            nlp_result:    Ergebnis aus NLPProcessor.process().
            extra_context: Zusätzlicher Kontext (z. B. LTM-Erinnerungen).

        Returns:
            Antworttext als String.
        """
        # Sicherheitsprüfung der Eingabe
        if not self._safety.check_input(nlp_result.raw_text):
            return self._safety.blocked_response()

        # LLM-Delegation, falls verfügbar und sinnvoll
        if self._llm and nlp_result.intent in ("question", "general", "help"):
            context_snapshot = self._context.snapshot()
            response = self._llm.complete(
                user_input=nlp_result.raw_text,
                context=context_snapshot,
            )
            if response:
                return self._apply_style(response)

        # Regelbasierte Antwort
        response = self._rule_based_response(nlp_result, extra_context or {})
        response = self._apply_style(response)

        # Sicherheitsprüfung der Ausgabe
        if not self._safety.check_output(response):
            return self._safety.blocked_response()

        return response

    # ------------------------------------------------------------------
    # Regelbasierte Antworten
    # ------------------------------------------------------------------

    _GREETINGS = [
        "Hallo! Schön, dass du da bist. 😊",
        "Hi! Wie kann ich dir helfen?",
        "Hey! Was gibt's?",
        "Guten Tag! Womit darf ich dienen?",
    ]
    _FAREWELLS = [
        "Tschüss! Bis bald. 👋",
        "Auf Wiedersehen! Ich freue mich auf unser nächstes Gespräch.",
        "Machs gut! Ich bin immer für dich da.",
    ]
    _THANKS_RESPONSES = [
        "Gern geschehen! 😊",
        "Immer wieder! Dafür bin ich hier.",
        "Kein Problem!",
    ]

    def _rule_based_response(
        self, nlp_result, extra_context: Dict
    ) -> str:
        intent = nlp_result.intent
        slots = nlp_result.slots
        person = self._context.get_active_person()
        name_suffix = f", {person.name}" if person else ""

        if intent == "greeting":
            base = random.choice(self._GREETINGS)
            return base.replace("!", f"{name_suffix}!") if name_suffix else base

        if intent == "farewell":
            return random.choice(self._FAREWELLS)

        if intent == "thanks":
            return random.choice(self._THANKS_RESPONSES)

        if intent == "store_memory":
            content = slots.get("memory_content", nlp_result.raw_text)
            return (
                f'Ich habe mir gemerkt: "{content}". '
                "Du kannst jederzeit danach fragen."
            )

        if intent == "recall_memory":
            memories = self._context.enrich_with_ltm(
                nlp_result.raw_text, max_memories=3
            )
            if memories:
                items = "; ".join(m.get("content", "") for m in memories[:3])
                return f"Ich erinnere mich: {items}."
            return "Dazu habe ich leider noch keine Erinnerungen gespeichert."

        if intent == "set_goal":
            goal = slots.get("goal", nlp_result.raw_text)
            return (
                f'Verstanden! Ich merke mir dein Ziel: "{goal}". '
                "Ich werde dich dabei unterstützen."
            )

        if intent == "emotion_share":
            return self._empathic_response(nlp_result.raw_text)

        if intent == "reflection":
            return self._self_reflection_snippet()

        if intent == "mode_change":
            return self._mode_change_response(nlp_result.raw_text)

        if intent == "question":
            return self._answer_question(nlp_result)

        if intent == "help":
            return self._help_response()

        # Fallback
        return self._fallback_response(nlp_result)

    # ------------------------------------------------------------------
    # Spezialantworten
    # ------------------------------------------------------------------

    def _empathic_response(self, text: str) -> str:
        text_lower = text.lower()
        if any(w in text_lower for w in ["traurig", "sad", "schlimm"]):
            return (
                "Das tut mir leid zu hören. 💙 Ich bin für dich da – "
                "möchtest du darüber sprechen?"
            )
        if any(w in text_lower for w in ["glücklich", "happy", "freude", "toll"]):
            return "Das freut mich sehr! 😊 Erzähl mir mehr davon!"
        if any(w in text_lower for w in ["wütend", "angry", "ärger"]):
            return (
                "Ich verstehe, dass dich das wütend macht. "
                "Lass es raus – ich höre zu."
            )
        return "Ich fühle mit dir. Wie geht es dir gerade genau?"

    def _self_reflection_snippet(self) -> str:
        mood = self._emotion.mood_modifier()
        traits = self._personality.communication_style()
        return (
            f"Gerade fühle ich mich {mood}. Mein Kommunikationsstil ist "
            f"{traits['tone']} und {traits['verbosity']}. "
            "Ich lerne ständig dazu und freue mich über unsere Gespräche."
        )

    def _mode_change_response(self, text: str) -> str:
        text_lower = text.lower()
        if "schlaf" in text_lower:
            return "Ich wechsle in den Schlafmodus. Gute Nacht! 🌙"
        if "arbeit" in text_lower:
            return "Arbeitsmodus aktiviert. Was soll ich für dich erledigen?"
        if "entspann" in text_lower or "ruh" in text_lower:
            return "Entspannungsmodus aktiviert. Lass uns durchatmen. 🌿"
        return "Modus gewechselt."

    def _answer_question(self, nlp_result) -> str:
        keywords = nlp_result.keywords
        if keywords:
            query = " ".join(keywords[:3])
            memories = self._context.enrich_with_ltm(query, max_memories=2)
            if memories:
                return (
                    f"Dazu weiß ich: {memories[0].get('content', '')}. "
                    "Möchtest du mehr Details?"
                )
        return (
            "Das ist eine interessante Frage. Leider habe ich dazu noch keine "
            "gespeicherte Information. Kannst du mir mehr erzählen?"
        )

    def _help_response(self) -> str:
        return (
            "Ich kann dir unter anderem helfen mit:\n"
            "• Fragen beantworten und Dinge erklären\n"
            "• Dinge merken und später daran erinnern\n"
            "• Ziele verfolgen und planen\n"
            "• Gespräche führen und zuhören\n"
            "Was brauchst du?"
        )

    def _fallback_response(self, nlp_result) -> str:
        mood = self._emotion.mood_modifier()
        style = self._personality.communication_style()
        if style["verbosity"] == "concise":
            return "Interessant. Erzähl mir mehr darüber."
        return (
            f"Das ist ein spannendes Thema! Ich denke darüber nach … "
            f"(Ich bin gerade {mood}.) Magst du das vertiefen?"
        )

    # ------------------------------------------------------------------
    # Stil-Anpassung
    # ------------------------------------------------------------------

    def _apply_style(self, text: str) -> str:
        """Passt den Text an Novas aktuellen Stil an."""
        style = self._personality.communication_style()
        # Concise: lange Texte kürzen (Heuristik)
        if style["verbosity"] == "concise" and len(text) > 200:
            sentences = text.split(". ")
            text = ". ".join(sentences[:2]) + ("." if len(sentences) > 2 else "")
        return text
