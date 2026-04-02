"""Tests for main.py – entry point helpers."""
from __future__ import annotations

import json

from main import load_config, setup_logging


class TestLoadConfig:
    """Configuration loading from JSON file."""

    def test_load_valid_config(self, tmp_path):
        cfg_file = tmp_path / "cfg.json"
        cfg_file.write_text(json.dumps({"stm_capacity": 30}))
        cfg = load_config(str(cfg_file))
        assert cfg["stm_capacity"] == 30

    def test_missing_file_returns_empty(self):
        cfg = load_config("/tmp/nonexistent_config_xyz.json")
        assert cfg == {}

    def test_invalid_json_returns_empty(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{invalid json!!")
        cfg = load_config(str(bad))
        assert cfg == {}


class TestSetupLogging:
    """Logging initialisation."""

    def test_setup_does_not_raise(self):
        setup_logging("DEBUG")
        setup_logging("INFO")
        setup_logging("WARNING")
