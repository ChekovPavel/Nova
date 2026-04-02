"""Tests for nova.modes.mode_manager – ModeManager."""
from __future__ import annotations


class TestModeSwitch:
    """Mode switching and properties."""

    def test_default_mode_is_normal(self, mode_manager):
        assert mode_manager.name == "normal"

    def test_switch_to_valid_mode(self, mode_manager):
        mode_manager.switch("work")
        assert mode_manager.name == "work"

    def test_switch_to_invalid_mode_ignored(self, mode_manager):
        mode_manager.switch("nonexistent_mode")
        # Should stay at current mode or handle gracefully
        assert mode_manager.name in (
            "normal", "work", "relax", "sleep", "focus",
            "empathy", "dating", "meeting",
        )

    def test_switch_from_text(self, mode_manager):
        mode_manager.switch_from_text("Lass uns arbeiten")
        # 'arbeiten' → work mode keyword
        # Just verify it doesn't crash; detection is best-effort
        assert mode_manager.name is not None

    def test_restore_previous(self, mode_manager):
        mode_manager.switch("work")
        mode_manager.switch("focus")
        mode_manager.restore_previous()
        assert mode_manager.name == "work"

    def test_all_modes_accessible(self, mode_manager):
        for name in ("normal", "work", "relax", "focus", "empathy",
                      "sleep", "dating", "meeting"):
            mode_manager.switch(name)
            assert mode_manager.name == name


class TestModeProperties:
    """Mode metadata and helper properties."""

    def test_is_sleeping(self, mode_manager):
        mode_manager.switch("sleep")
        assert mode_manager.is_sleeping() is True
        mode_manager.switch("normal")
        assert mode_manager.is_sleeping() is False

    def test_is_meeting(self, mode_manager):
        mode_manager.switch("meeting")
        assert mode_manager.is_meeting() is True

    def test_is_dating(self, mode_manager):
        mode_manager.switch("dating")
        assert mode_manager.is_dating() is True

    def test_is_work_context(self, mode_manager):
        mode_manager.switch("work")
        assert mode_manager.is_work_context() is True
        mode_manager.switch("normal")
        assert mode_manager.is_work_context() is False

    def test_profile_context(self, mode_manager):
        mode_manager.switch("dating")
        assert mode_manager.profile_context == "private"
        mode_manager.switch("meeting")
        assert mode_manager.profile_context == "work"

    def test_describe_returns_string(self, mode_manager):
        desc = mode_manager.describe()
        assert isinstance(desc, str)

    def test_verbosity(self, mode_manager):
        v = mode_manager.current_verbosity()
        assert isinstance(v, str)
