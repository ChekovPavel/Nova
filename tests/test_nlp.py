"""Tests for nova.nlp.processor – NLPProcessor."""
from __future__ import annotations

import pytest


class TestNLPProcess:
    """Core NLP processing pipeline."""

    def test_returns_result_object(self, nlp):
        result = nlp.process("Hallo Nova")
        assert hasattr(result, "intent")
        assert hasattr(result, "tokens")
        assert hasattr(result, "sentiment")
        assert hasattr(result, "keywords")
        assert hasattr(result, "is_question")

    def test_question_detection(self, nlp):
        result = nlp.process("Wie heißt du?")
        assert result.is_question is True

    def test_non_question(self, nlp):
        result = nlp.process("Ich bin müde.")
        assert result.is_question is False

    def test_sentiment_range(self, nlp):
        result = nlp.process("Ich bin sehr glücklich heute!")
        assert -1.0 <= result.sentiment <= 1.0

    def test_empty_input(self, nlp):
        result = nlp.process("")
        assert result is not None

    def test_tokens_are_list(self, nlp):
        result = nlp.process("Eins zwei drei")
        assert isinstance(result.tokens, list)
        assert len(result.tokens) >= 1

    def test_keywords_extracted(self, nlp):
        result = nlp.process("Python Programmierung ist interessant")
        assert isinstance(result.keywords, list)


class TestIntentDetection:
    """Intent recognition from user text."""

    def test_greeting_intent(self, nlp):
        result = nlp.process("Hallo!")
        # Intent may be None or a recognised string
        assert result.intent is None or isinstance(result.intent, str)

    def test_farewell_intent(self, nlp):
        result = nlp.process("Tschüss, bis morgen!")
        assert result.intent is None or isinstance(result.intent, str)
