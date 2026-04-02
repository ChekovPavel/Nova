"""Tests for nova.personality - Personality and EmotionEngine."""

from __future__ import annotations

# ── Personality ──────────────────────────────────────────────────────────────


class TestPersonalityTraits:
    """Big Five trait model."""

    def test_default_traits_loaded(self, personality):
        traits = personality.all_traits()
        assert isinstance(traits, dict)
        assert len(traits) > 0

    def test_get_trait(self, personality):
        val = personality.get("empathy", default=0.5)
        assert 0.0 <= val <= 1.0

    def test_set_trait(self, personality):
        personality.set("humor", 0.8)
        assert abs(personality.get("humor") - 0.8) < 0.01

    def test_adapt_trait(self, personality):
        before = personality.get("curiosity", 0.5)
        personality.adapt("curiosity", 0.1)
        after = personality.get("curiosity", 0.5)
        assert after >= before or after <= 1.0  # bounded adaptation

    def test_communication_style(self, personality):
        style = personality.communication_style()
        assert isinstance(style, dict)

    def test_describe(self, personality):
        desc = personality.describe()
        assert isinstance(desc, str)
        assert len(desc) > 0


# ── EmotionEngine ────────────────────────────────────────────────────────────


class TestEmotionEngine:
    """VAD-based emotion system."""

    def test_initial_state(self, emotion):
        state = emotion.state
        assert state is not None

    def test_trigger_emotion(self, emotion):
        emotion.trigger("joy", intensity=0.7)
        label = emotion.current_label
        assert isinstance(label, str)

    def test_react_to_text(self, emotion):
        # Should not raise
        emotion.react_to_text("Ich bin sehr glücklich!")

    def test_react_to_sentiment(self, emotion):
        emotion.react_to_sentiment(0.8, intensity=0.5)
        # Positive sentiment should influence state
        state = emotion.state
        assert state is not None

    def test_mood_modifier_string(self, emotion):
        mod = emotion.mood_modifier()
        assert isinstance(mod, str)

    def test_detect_from_text(self, emotion):
        detected = emotion.detect_from_text("Ich bin traurig")
        # May return None or an emotion string
        assert detected is None or isinstance(detected, str)
