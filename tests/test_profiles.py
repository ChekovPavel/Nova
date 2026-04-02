"""Tests for nova.profiles.profile_manager – ProfileManager."""
from __future__ import annotations

import pytest


class TestProfileSwitching:
    """Private ↔ work context separation."""

    def test_default_is_private(self, profile_manager):
        assert profile_manager.active_name == "private"

    def test_switch_to_work(self, profile_manager):
        result = profile_manager.switch_for_mode("work")
        assert profile_manager.active_name == "work"

    def test_switch_to_private_mode(self, profile_manager):
        profile_manager.switch_for_mode("work")
        profile_manager.switch_for_mode("normal")
        assert profile_manager.active_name == "private"

    def test_dating_is_private(self, profile_manager):
        profile_manager.switch_for_mode("dating")
        assert profile_manager.is_private()

    def test_meeting_is_work(self, profile_manager):
        profile_manager.switch_for_mode("meeting")
        assert profile_manager.is_work()


class TestProfileSTM:
    """Each profile has its own STM."""

    def test_separate_stm_instances(self, profile_manager):
        private_stm = profile_manager.active_stm()
        profile_manager.switch_for_mode("work")
        work_stm = profile_manager.active_stm()
        assert private_stm is not work_stm

    def test_ltm_tag(self, profile_manager):
        tag = profile_manager.active_ltm_tag()
        assert "private" in tag or "work" in tag


class TestProfileDescribe:
    def test_describe(self, profile_manager):
        desc = profile_manager.describe()
        assert isinstance(desc, str)
