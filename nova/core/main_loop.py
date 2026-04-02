"""
Kapitel 2 – Kernlogik / Hauptschleife

Die MainLoop verarbeitet eingehende Nachrichten und koordiniert
alle Subsysteme für jede Nutzerinteraktion.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Maximale Anzahl STM-Einträge, die für die Meeting-Zusammenfassung ausgewertet werden
_MAX_MEETING_ENTRIES_FOR_SUMMARY = 50


class MainLoop:
    """
    Novas Hauptverarbeitungsschleife.

    Ablauf pro Nachricht:
    1. Eingabe lesen (Text oder Voice)
    2. NLP verarbeiten
    3. Person identifizieren
    4. Modus ggf. anpassen (inkl. Profilwechsel + Meeting-Summary)
    5. Sicherheitsprüfung
    6. Kontext aufbauen
    7. Antwort generieren (inkl. modusspezifischem Stil)
    8. Speichern (STM/LTM mit Profil-Tag)
    9. Lernen
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

        # 2a. Profil der aktiven Person aus Text anreichern (auto-learning)
        if n.profile_enricher and person_id:
            active_person = n.person_recognition.get_active_person()
            if active_person:
                n.profile_enricher.enrich_from_text(active_person, user_input)

        # 3. Modus ggf. anpassen
        prev_mode = n.mode_manager.name
        switched_mode = n.mode_manager.switch_from_text(user_input)
        current_mode = n.mode_manager.name

        # 3a. Meeting verlassen → Zusammenfassung erstellen
        meeting_summary: str | None = None
        if prev_mode == "meeting" and current_mode != "meeting":
            meeting_entries = n.stm.get_recent(_MAX_MEETING_ENTRIES_FOR_SUMMARY, entry_type="message")
            meeting_summary = n.reflection.summarize_meeting(meeting_entries)
            n.ltm.store(
                meeting_summary,
                category="meeting",
                importance=0.8,
                tags=["meeting", "summary", "profile:work"],
            )
            logger.info("Meeting-Zusammenfassung gespeichert.")

        # 3b. Kontextprofil wechseln (privat ↔ Arbeit)
        if n.profile_manager:
            switched_profile = n.profile_manager.switch_for_mode(current_mode)
            if switched_profile:
                # STM im ContextManager auf das neue Profil umschalten
                n.context_manager.set_stm(n.profile_manager.active_stm())
                # nova.stm bleibt als Hauptreferenz auf dasselbe Objekt zeigen
                n.stm = n.profile_manager.active_stm()

        # Schlafmodus: nur kurze Rückmeldung
        if n.mode_manager.is_sleeping():
            return "Ich bin im Schlafmodus. Sage 'Normalmodus' zum Aufwecken."

        # 4. Emotionen reagieren lassen (Keyword + Sentiment)
        n.emotion.react_to_text(user_input, intensity=0.3)
        if nlp_result.sentiment != 0.0:
            n.emotion.react_to_sentiment(nlp_result.sentiment, intensity=0.25)

        # 5. Relevanz-Score berechnen & STM speichern (profilbewusst)
        relevance = n.relevance_filter.score(user_input)
        n.stm.add_message("user", user_input, relevance=relevance)

        # 6. Kontext aufbauen (LTM-Anreicherung, profilbewusst)
        keywords = " ".join(nlp_result.keywords[:3])
        active_profile_tag = (
            n.profile_manager.active_ltm_tag() if n.profile_manager else None
        )
        ltm_context = n.context_manager.enrich_with_ltm(
            keywords, max_memories=2, profile_tag=active_profile_tag
        )

        # 7. Lernen (falls Modus es erlaubt)
        if n.mode_manager.allows_learning():
            n.learner.learn_from_text(user_input)
            if nlp_result.slots.get("goal"):
                n.goals.add_goal(
                    nlp_result.slots["goal"],
                    priority=0.6,
                )
            if nlp_result.intent == "store_memory" and nlp_result.slots.get("memory_content"):
                # Profil-Tag beim Speichern mitgeben
                profile_tag = (
                    n.profile_manager.active_ltm_tag()
                    if n.profile_manager
                    else "profile:private"
                )
                n.storage_depth.store(
                    content=nlp_result.slots["memory_content"],
                    importance=0.8,
                    category="fact",
                    tags=[*nlp_result.keywords[:3], profile_tag],
                )

        # 8. Antwort generieren
        response = n.response_generator.generate(
            nlp_result,
            extra_context={"ltm": ltm_context},
        )

        # 8a. Online-Suche (Kapitel 16.6) – bei expliziter Suchanfrage
        if nlp_result.slots.get("search_query") and n.web_search:
            query = nlp_result.slots.get("search_query", "").strip()
            # Mindestlänge: zu kurze Queries liefern kaum brauchbare Ergebnisse
            if len(query) >= 3:
                search_result = n.web_search.search_person(query)
                formatted = n.web_search.format_result(search_result)
                # Suchergebnis ins LTM speichern
                if search_result.get("abstract"):
                    n.ltm.store(
                        content=f"Websuche '{query}': {search_result['abstract']}",
                        category="fact",
                        importance=0.6,
                        tags=[query.lower(), "web_search"],
                    )
                response = response + "\n\n\U0001f50e **Online gefunden:**\n" + formatted
            else:
                logger.debug(
                    "WebSearch: Suchanfrage zu kurz (%r), \u00fcbersprungen.", query
                )

        # Krisenmodus-Check
        if n.social_safety.in_crisis_mode:
            response = n.social_safety.crisis_response() + "\n\n" + response

        # Meeting verlassen: Zusammenfassung voranstellen
        if meeting_summary:
            response = meeting_summary + "\n\n" + response

        # Modusspezifische Stil-Hinweise (Dating: Vorschläge, Meeting: Agenda)
        if switched_mode and n.suggestion_engine:
            context_person_id = (
                n.context_manager.get_active_person().id
                if n.context_manager.get_active_person()
                else None
            )
            suggestion = n.suggestion_engine.suggest_for_context(
                mode_name=current_mode,
                person_id=context_person_id,
                topic=keywords,
            )
            if suggestion:
                response = response + "\n\n" + suggestion

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

    def _get_input(self) -> str | None:
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
