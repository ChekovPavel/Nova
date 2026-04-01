"""
Kapitel 2 – Kernlogik / Hauptschleife

Die MainLoop verarbeitet eingehende Nachrichten und koordiniert
alle Subsysteme für jede Nutzerinteraktion.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class MainLoop:
    """
    Novas Hauptverarbeitungsschleife.

    Ablauf pro Nachricht:
    1. Eingabe lesen (Text oder Voice)
    2. NLP verarbeiten
    3. Person identifizieren
    4. Sicherheitsprüfung
    5. Kontext aufbauen
    6. Antwort generieren
    7. Speichern (STM/LTM)
    8. Lernen
    9. Modus ggf. anpassen
    10. Antwort ausgeben
    """

    def __init__(self, nova) -> None:
        self._nova = nova
        self._running = False

    # ------------------------------------------------------------------
    # Hauptschleife (interaktiv)
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Startet die interaktive Konsolenschleife."""
        self._running = True
        n = self._nova
        print("\n🌟 Nova ist bereit. Tippe 'exit' zum Beenden.\n")

        while self._running:
            try:
                # Eingabe
                user_input = self._get_input()
                if user_input is None:
                    continue

                if user_input.lower().strip() in ("exit", "quit", "beenden"):
                    print("Nova: Auf Wiedersehen! 👋")
                    break

                response = self.process(user_input)
                print(f"Nova: {response}\n")

                # Sprachausgabe (falls aktiviert)
                if n.voice_io and n.voice_io.tts_available:
                    n.voice_io.speak(response)

            except KeyboardInterrupt:
                print("\nNova: Bis bald! 👋")
                break

        self._running = False

    # ------------------------------------------------------------------
    # Einzelne Nachricht verarbeiten
    # ------------------------------------------------------------------

    def process(self, user_input: str) -> str:
        """
        Verarbeitet eine Nutzereingabe und gibt Novas Antwort zurück.

        Args:
            user_input: Rohtext der Nutzereingabe.

        Returns:
            Antworttext.
        """
        n = self._nova
        if not user_input or not user_input.strip():
            return ""

        # 1. NLP
        nlp_result = n.nlp_processor.process(user_input)

        # 2. Person identifizieren
        person_id = n.person_recognition.identify_from_text(user_input)
        n.context_manager.set_active_person(person_id)

        # 3. Modus ggf. anpassen
        n.mode_manager.switch_from_text(user_input)

        # Schlafmodus: nur kurze Rückmeldung
        if n.mode_manager.is_sleeping():
            return "Ich bin im Schlafmodus. Sage 'Normalmodus' zum Aufwecken."

        # 4. Emotionen reagieren lassen
        n.emotion.react_to_text(user_input, intensity=0.3)

        # 5. Relevanz-Score berechnen & STM speichern
        relevance = n.relevance_filter.score(user_input)
        n.stm.add_message("user", user_input, relevance=relevance)

        # 6. Kontext aufbauen (LTM-Anreicherung)
        keywords = " ".join(nlp_result.keywords[:3])
        ltm_context = n.context_manager.enrich_with_ltm(
            keywords, max_memories=2
        )

        # 7. Lernen (falls Modus es erlaubt)
        if n.mode_manager.allows_learning():
            n.learner.learn_from_text(user_input)
            # Ziel-Slot direkt anlegen
            if nlp_result.slots.get("goal"):
                n.goals.add_goal(
                    nlp_result.slots["goal"],
                    priority=0.6,
                )
            # Explizite Erinnerung
            if nlp_result.intent == "store_memory" and nlp_result.slots.get("memory_content"):
                n.storage_depth.store(
                    content=nlp_result.slots["memory_content"],
                    importance=0.8,
                    category="fact",
                    tags=nlp_result.keywords[:3],
                )

        # 8. Antwort generieren
        response = n.response_generator.generate(
            nlp_result,
            extra_context={"ltm": ltm_context},
        )

        # Krisenmodus-Check
        if n.social_safety.in_crisis_mode:
            response = n.social_safety.crisis_response() + "\n\n" + response

        # 9. Antwort ins STM
        n.stm.add_message("nova", response, relevance=0.5)

        # 10. Periodische Selbstreflexion (alle 10 Nachrichten)
        stm_len = len(n.stm)
        if stm_len > 0 and stm_len % 10 == 0:
            n.reflection.reflect()

        return response

    # ------------------------------------------------------------------
    # Eingabe
    # ------------------------------------------------------------------

    def _get_input(self) -> Optional[str]:
        """Liest Nutzereingabe (Text oder Voice)."""
        n = self._nova
        # Versuche Voice-Eingabe
        if n.voice_io and n.voice_io.stt_available:
            text = n.voice_io.listen(timeout=3.0)
            if text:
                print(f"Du (Sprache): {text}")
                return text

        # Text-Fallback
        try:
            return input("Du: ").strip()
        except EOFError:
            return None

    # ------------------------------------------------------------------
    # Lebenszyklus
    # ------------------------------------------------------------------

    def stop(self) -> None:
        self._running = False
