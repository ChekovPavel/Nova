"""
Kapitel 3 – Sprachverarbeitung / NLP-Basis

Verarbeitet Nutzeringaben: Tokenisierung, Intent-Erkennung,
Slot-Extraktion und Spracherkennnung.
Verwendet ausschließlich die Python-Standardbibliothek als Kern;
optional kann spaCy / transformers ergänzt werden.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Intent-Definitionen
# ------------------------------------------------------------------
_INTENTS: dict[str, list[str]] = {
    "greeting":       [r"\b(hallo|hi|hey|guten morgen|guten abend|servus|moin)\b"],
    "farewell":       [r"\b(tschüss|auf wiedersehen|bye|ciao|bis später|tschau)\b"],
    "thanks":         [r"\b(danke|vielen dank|thx|thank you|merci)\b"],
    "question":       [r"^(wer|was|wie|wann|wo|warum|welche?|ist|sind|kann|könntest|würdest|hast du)\b", r"\?$"],
    "help":           [r"\b(hilf mir|hilfe|kannst du|kannst du mir|bitte erkläre?)\b"],
    "store_memory":   [r"\b(merke dir|vergiss nicht|notiere|speichere)\b"],
    "recall_memory":  [r"\b(erinnerst du dich|weißt du noch|was weißt du über)\b"],
    "search_online":  [r"\b(such(e)? (mal |nach |online )?|google|suche nach|wer ist|was ist|finde (?:heraus|etwas) über|was weißt du über|kennst du)\b"],
    "set_goal":       [r"\b(mein ziel ist|ich möchte|ich will|ich plane)\b"],
    "mode_change":    [r"\b(schlafmodus|arbeitsmodus|entspannungsmodus|ruhemodus)\b"],
    "emotion_share":  [r"\b(ich bin (traurig|glücklich|wütend|fröhlich|ängstlich|aufgeregt))\b"],
    "add_person":     [r"\b(das ist|ich stelle vor|kenn(st du)? (mein|meinen|meine))\b"],
    "reflection":     [r"\b(was denkst du über dich|reflektiere|selbstreflexion|wie geht es dir)\b"],
    "general":        [],  # Fallback
}


@dataclass
class NLPResult:
    """Ergebnis einer NLP-Verarbeitung."""
    raw_text: str
    normalized: str
    tokens: list[str]
    intent: str
    intent_confidence: float
    slots: dict[str, Any] = field(default_factory=dict)
    language: str = "de"
    is_question: bool = False
    sentiment: float = 0.0   # -1.0 (negativ) bis +1.0 (positiv)
    keywords: list[str] = field(default_factory=list)


class NLPProcessor:
    """
    Grundlegender NLP-Prozessor für Nova.

    Führt aus:
    - Text-Normalisierung
    - Tokenisierung
    - Intent-Erkennung (regelbasiert)
    - Slot-Extraktion
    - Sentiment-Einschätzung (Keyword-basiert)
    - Spracherkennung (de/en)
    """

    # Einfache Sentiment-Wörter
    _POSITIVE_WORDS = {
        "gut", "super", "toll", "klasse", "schön", "freude", "liebe",
        "danke", "perfekt", "wunderbar", "großartig", "yes", "great", "good",
    }
    _NEGATIVE_WORDS = {
        "schlecht", "schrecklich", "traurig", "wütend", "hasse", "nervig",
        "problem", "fehler", "nein", "leider", "bad", "terrible", "sad",
    }

    def __init__(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Verarbeitung
    # ------------------------------------------------------------------

    def process(self, text: str) -> NLPResult:
        """
        Verarbeitet eine Nutzereingabe und gibt ein NLPResult zurück.
        """
        normalized = self._normalize(text)
        tokens = self._tokenize(normalized)
        language = self._detect_language(normalized)
        intent, confidence = self._detect_intent(normalized)
        slots = self._extract_slots(normalized, intent)
        sentiment = self._estimate_sentiment(tokens)
        keywords = self._extract_keywords(tokens)
        is_question = "?" in text or intent == "question"

        return NLPResult(
            raw_text=text,
            normalized=normalized,
            tokens=tokens,
            intent=intent,
            intent_confidence=confidence,
            slots=slots,
            language=language,
            is_question=is_question,
            sentiment=sentiment,
            keywords=keywords,
        )

    # ------------------------------------------------------------------
    # Normalisierung
    # ------------------------------------------------------------------

    def _normalize(self, text: str) -> str:
        """Lowercased, bereinigt Whitespace."""
        text = text.strip()
        text = re.sub(r"\s+", " ", text)
        return text

    # ------------------------------------------------------------------
    # Tokenisierung
    # ------------------------------------------------------------------

    def _tokenize(self, text: str) -> list[str]:
        """Einfache Whitespace- + Satzzeichen-Tokenisierung."""
        tokens = re.findall(r"\b\w+\b", text.lower())
        return tokens

    # ------------------------------------------------------------------
    # Spracherkennung
    # ------------------------------------------------------------------

    _DE_MARKERS = {"ich", "du", "ist", "ein", "die", "der", "das", "und", "nicht"}
    _EN_MARKERS = {"i", "you", "is", "the", "and", "not", "a", "to", "it"}

    def _detect_language(self, text: str) -> str:
        tokens = set(re.findall(r"\b\w+\b", text.lower()))
        de_score = len(tokens & self._DE_MARKERS)
        en_score = len(tokens & self._EN_MARKERS)
        return "en" if en_score > de_score else "de"

    # ------------------------------------------------------------------
    # Intent-Erkennung
    # ------------------------------------------------------------------

    def _detect_intent(self, text: str) -> tuple[str, float]:
        text_lower = text.lower()
        best_intent = "general"
        best_score = 0.0

        for intent, patterns in _INTENTS.items():
            if not patterns:
                continue
            matches = sum(
                1 for p in patterns
                if re.search(p, text_lower, re.IGNORECASE)
            )
            score = matches / len(patterns)
            if score > best_score:
                best_score = score
                best_intent = intent

        confidence = min(1.0, best_score + 0.3) if best_score > 0 else 0.3
        return best_intent, confidence

    # ------------------------------------------------------------------
    # Slot-Extraktion
    # ------------------------------------------------------------------

    def _extract_slots(self, text: str, intent: str) -> dict[str, Any]:
        slots: dict[str, Any] = {}

        # Namen aus Kontext
        name_match = re.search(
            r"(?:ich heiße|ich bin|mein name ist|call me|i am|i'm)\s+([A-ZÄÖÜ][a-zäöüß]+)",
            text, re.IGNORECASE,
        )
        if name_match:
            slots["name"] = name_match.group(1)

        # Ziel
        goal_match = re.search(
            r"(?:mein ziel ist|ich möchte|ich will|ich plane)\s+(.+?)(?:\.|$)",
            text, re.IGNORECASE,
        )
        if goal_match:
            slots["goal"] = goal_match.group(1).strip()

        # Speichern-Inhalt
        if intent == "store_memory":
            mem_match = re.search(
                r"(?:merke dir|vergiss nicht|notiere|speichere)[,:\s]+(.+)",
                text, re.IGNORECASE,
            )
            if mem_match:
                slots["memory_content"] = mem_match.group(1).strip()

        # Suchanfrage (für search_online UND question-Intent mit "wer/was ist X")
        if intent in ("search_online", "question"):
            search_match = re.search(
                r"(?:such(?:e)?\s+(?:mal\s+)?(?:nach\s+)?|"
                r"google\s+|suche\s+(?:nach\s+)?|"
                r"wer\s+ist\s+|was\s+ist\s+|"
                r"finde\s+(?:heraus|etwas)\s+ueber\s+|"
                r"finde\s+(?:heraus|etwas)\s+über\s+|"
                r"was\s+weißt\s+du\s+über\s+|"
                r"was\s+weisst\s+du\s+ueber\s+|"
                r"kennst\s+du\s+)"
                r"(.+?)(?:\?|!|\.|$)",
                text, re.IGNORECASE,
            )
            if search_match:
                # Gruppe 1 enthält immer die Suchanfrage (nach dem Trigger-Ausdruck)
                raw_query = search_match.group(1).strip()
                # Trailing noise-words entfernen ("online", "mal", "bitte")
                raw_query = re.sub(
                    r"\s+(?:online|mal|bitte|doch|jetzt)\s*$",
                    "", raw_query, flags=re.IGNORECASE,
                ).strip()
                if raw_query:
                    slots["search_query"] = raw_query

        return slots

    # ------------------------------------------------------------------
    # Sentiment
    # ------------------------------------------------------------------

    def _estimate_sentiment(self, tokens: list[str]) -> float:
        pos = sum(1 for t in tokens if t in self._POSITIVE_WORDS)
        neg = sum(1 for t in tokens if t in self._NEGATIVE_WORDS)
        total = pos + neg
        if total == 0:
            return 0.0
        return (pos - neg) / total

    # ------------------------------------------------------------------
    # Keywords
    # ------------------------------------------------------------------

    _STOP_WORDS = {
        "ich", "du", "er", "sie", "es", "wir", "ihr", "die", "der", "das",
        "ein", "eine", "und", "oder", "aber", "nicht", "ist", "bin", "hat",
        "i", "you", "he", "she", "it", "we", "the", "a", "an", "is", "are",
        "and", "or", "not", "have", "has",
    }

    def _extract_keywords(self, tokens: list[str]) -> list[str]:
        seen = set()
        keywords = []
        for t in tokens:
            if t not in self._STOP_WORDS and len(t) > 2 and t not in seen:
                keywords.append(t)
                seen.add(t)
        return keywords[:10]
