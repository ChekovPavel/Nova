"""Tests for config validation in nova.core.nova."""
from __future__ import annotations

import pytest

from nova.core.nova import validate_config


class TestValidateConfig:
    """Configuration validation and defaults."""

    def test_empty_config_returns_defaults(self):
        result = validate_config({})
        assert result["db_path"] == "nova_data.db"
        assert result["stm_capacity"] == 20

    def test_valid_config_passes_through(self):
        cfg = {
            "db_path": "~/my/nova.db",
            "stm_capacity": 50,
            "secret_key": "abc123",
        }
        result = validate_config(cfg)
        assert result["db_path"] == "~/my/nova.db"
        assert result["stm_capacity"] == 50
        assert result["secret_key"] == "abc123"

    def test_invalid_type_replaced_with_default(self):
        cfg = {"stm_capacity": "not_an_int"}
        result = validate_config(cfg)
        assert result["stm_capacity"] == 20

    def test_below_minimum_clamped(self):
        cfg = {"stm_capacity": -5}
        result = validate_config(cfg)
        assert result["stm_capacity"] == 1  # min is 1

    def test_above_maximum_clamped(self):
        cfg = {"stm_capacity": 9999}
        result = validate_config(cfg)
        assert result["stm_capacity"] == 500  # max is 500

    def test_nested_config_validated(self):
        cfg = {
            "backup": {
                "max_backups": -1,
                "interval_sec": 10,  # below min of 60
            }
        }
        result = validate_config(cfg)
        assert result["backup"]["max_backups"] == 1
        assert result["backup"]["interval_sec"] == 60

    def test_nested_invalid_type_replaced(self):
        cfg = {
            "ollama": {
                "temperature": "hot",  # should be float
            }
        }
        result = validate_config(cfg)
        assert result["ollama"]["temperature"] == 0.7

    def test_unknown_keys_preserved(self):
        cfg = {"custom_setting": "value123"}
        result = validate_config(cfg)
        assert result["custom_setting"] == "value123"

    def test_none_secret_key_allowed(self):
        cfg = {"secret_key": None}
        result = validate_config(cfg)
        assert result["secret_key"] is None
