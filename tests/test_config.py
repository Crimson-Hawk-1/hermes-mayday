"""
Tests for the MaydayConfig configuration loader.
"""

from __future__ import annotations

import os
import pytest

from hermes_mayday.config import MaydayConfig
from conftest import MockPluginContext


class TestMaydayConfigDefaults:
    """Test that default values are applied correctly."""

    def test_defaults_are_sane(self, default_config: MaydayConfig) -> None:
        assert default_config.enabled is True
        assert default_config.max_repeats == 3
        assert default_config.window_size == 10
        assert default_config.halt_mode == "hard"
        assert default_config.report_dir == "./"
        assert "timestamp" in default_config.volatile_keys
        assert "request_id" in default_config.volatile_keys

    def test_from_context_with_none(self) -> None:
        """from_context(None) should return all defaults."""
        config = MaydayConfig.from_context(None)
        assert config.enabled is True
        assert config.max_repeats == 3

    def test_from_env_returns_defaults(self) -> None:
        """from_env() with no env vars should return defaults."""
        # Clear any existing MAYDAY_ vars
        for key in list(os.environ):
            if key.startswith("MAYDAY_"):
                del os.environ[key]
        config = MaydayConfig.from_env()
        assert config.max_repeats == 3
        assert config.halt_mode == "hard"


class TestMaydayConfigEnvOverrides:
    """Test that environment variables override defaults."""

    def test_max_repeats_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MAYDAY_MAX_REPEATS", "7")
        config = MaydayConfig.from_env()
        assert config.max_repeats == 7

    def test_window_size_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MAYDAY_WINDOW_SIZE", "20")
        config = MaydayConfig.from_env()
        assert config.window_size == 20

    def test_halt_mode_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MAYDAY_HALT_MODE", "soft")
        config = MaydayConfig.from_env()
        assert config.halt_mode == "soft"

    def test_enabled_false_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MAYDAY_ENABLED", "false")
        config = MaydayConfig.from_env()
        assert config.enabled is False

    def test_volatile_keys_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MAYDAY_VOLATILE_KEYS", "foo,bar,baz")
        config = MaydayConfig.from_env()
        assert config.volatile_keys == ["foo", "bar", "baz"]

    def test_report_dir_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MAYDAY_REPORT_DIR", "/tmp/mayday-reports")
        config = MaydayConfig.from_env()
        assert config.report_dir == "/tmp/mayday-reports"


class TestMaydayConfigPluginContext:
    """Test that PluginContext config takes precedence over env vars."""

    def test_context_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MAYDAY_MAX_REPEATS", "99")
        ctx = MockPluginContext(config={"max_repeats": 5})
        config = MaydayConfig.from_context(ctx)
        # Context value (5) should win over env (99)
        assert config.max_repeats == 5

    def test_context_bool_value(self) -> None:
        ctx = MockPluginContext(config={"enabled": False})
        config = MaydayConfig.from_context(ctx)
        assert config.enabled is False

    def test_context_list_value(self) -> None:
        ctx = MockPluginContext(config={"volatile_keys": ["alpha", "beta"]})
        config = MaydayConfig.from_context(ctx)
        assert config.volatile_keys == ["alpha", "beta"]


class TestMaydayConfigValidation:
    """Test that invalid values fall back to safe defaults."""

    def test_invalid_max_repeats_falls_back(self) -> None:
        config = MaydayConfig(max_repeats=-1)
        assert config.max_repeats == 3

    def test_zero_max_repeats_falls_back(self) -> None:
        config = MaydayConfig(max_repeats=0)
        assert config.max_repeats == 3

    def test_invalid_window_size_falls_back(self) -> None:
        config = MaydayConfig(window_size=0)
        assert config.window_size == 10

    def test_invalid_halt_mode_falls_back(self) -> None:
        config = MaydayConfig(halt_mode="invalid_mode")
        assert config.halt_mode == "hard"

    def test_invalid_env_int_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MAYDAY_MAX_REPEATS", "not_a_number")
        config = MaydayConfig.from_env()
        assert config.max_repeats == 3
