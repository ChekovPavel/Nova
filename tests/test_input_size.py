"""Tests for input size validation in nova.safety.social_safety."""

from __future__ import annotations


class TestInputSizeValidation:
    """DoS protection via input length limits."""

    def test_normal_length_allowed(self, safety):
        assert safety.check_input("Hallo Nova, wie geht es dir?") is True

    def test_very_long_input_blocked(self, safety):
        long_text = "a" * 15_000
        assert safety.check_input(long_text) is False

    def test_exactly_at_limit_allowed(self, safety):
        text = "x" * 10_000
        assert safety.check_input(text) is True

    def test_one_over_limit_blocked(self, safety):
        text = "x" * 10_001
        assert safety.check_input(text) is False

    def test_long_input_increments_block_count(self, safety):
        initial = safety.block_count
        safety.check_input("y" * 15_000)
        assert safety.block_count == initial + 1
