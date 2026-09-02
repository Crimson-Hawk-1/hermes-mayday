"""
Shared pytest fixtures for hermes-mayday tests.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from hermes_mayday.config import MaydayConfig
from hermes_mayday.circuit_breaker import MaydayCircuitBreaker
from hermes_mayday.crash_report import CrashReportWriter
from hermes_mayday.display import MaydayDisplay


class MockPluginContext:
    """
    A mock Hermes PluginContext for testing.

    Mimics the interface used by ``MaydayConfig.from_context()`` so
    we can test configuration resolution without a real Hermes install.
    """

    def __init__(self, config: dict | None = None) -> None:
        self.config = config or {}
        self._registered_hooks: dict[str, list] = {}

    def register_hook(self, hook_name: str, handler) -> None:
        """Record hook registrations for test verification."""
        self._registered_hooks.setdefault(hook_name, []).append(handler)

    def get_registered_hooks(self, hook_name: str) -> list:
        """Get all handlers registered for a given hook."""
        return self._registered_hooks.get(hook_name, [])


@pytest.fixture
def default_config() -> MaydayConfig:
    """A MaydayConfig with all default values."""
    return MaydayConfig()


@pytest.fixture
def strict_config() -> MaydayConfig:
    """A strict MaydayConfig that trips after 2 repeats in a 5-action window."""
    return MaydayConfig(max_repeats=2, window_size=5)


@pytest.fixture
def soft_config() -> MaydayConfig:
    """A soft-mode MaydayConfig that warns but doesn't block."""
    return MaydayConfig(halt_mode="soft")


@pytest.fixture
def display() -> MaydayDisplay:
    """A MaydayDisplay instance."""
    return MaydayDisplay()


@pytest.fixture
def report_writer(tmp_path: Path) -> CrashReportWriter:
    """A CrashReportWriter that writes to a temporary directory."""
    config = MaydayConfig(report_dir=str(tmp_path))
    return CrashReportWriter(config=config)


@pytest.fixture
def breaker(default_config: MaydayConfig, display: MaydayDisplay, tmp_path: Path) -> MaydayCircuitBreaker:
    """A MaydayCircuitBreaker with default settings, writing reports to tmp."""
    config = MaydayConfig(report_dir=str(tmp_path))
    writer = CrashReportWriter(config=config)
    return MaydayCircuitBreaker(config=config, display=display, report_writer=writer)


@pytest.fixture
def strict_breaker(strict_config: MaydayConfig, display: MaydayDisplay, tmp_path: Path) -> MaydayCircuitBreaker:
    """A strict MaydayCircuitBreaker that trips after 2 repeats."""
    config = MaydayConfig(max_repeats=2, window_size=5, report_dir=str(tmp_path))
    writer = CrashReportWriter(config=config)
    return MaydayCircuitBreaker(config=config, display=display, report_writer=writer)


@pytest.fixture
def soft_breaker(soft_config: MaydayConfig, display: MaydayDisplay, tmp_path: Path) -> MaydayCircuitBreaker:
    """A soft-mode breaker that warns but doesn't block."""
    config = MaydayConfig(halt_mode="soft", report_dir=str(tmp_path))
    writer = CrashReportWriter(config=config)
    return MaydayCircuitBreaker(config=config, display=display, report_writer=writer)


@pytest.fixture
def mock_ctx() -> MockPluginContext:
    """A mock Hermes PluginContext with no custom config."""
    return MockPluginContext()


# ── Sample data ─────────────────────────────────────────────────

SAMPLE_TOOL_CALL = {
    "tool_name": "run_bash_command",
    "args": {"command": "python build.py", "timeout": 30},
    "task_id": "task-abc-123",
}

SAMPLE_TOOL_CALL_WITH_VOLATILE = {
    "tool_name": "run_bash_command",
    "args": {
        "command": "python build.py",
        "timeout": 30,
        "timestamp": "2026-09-02T10:00:00Z",
        "request_id": "req-xyz-789",
    },
    "task_id": "task-abc-123",
}

DIFFERENT_TOOL_CALL = {
    "tool_name": "read_file",
    "args": {"path": "/home/user/config.json"},
    "task_id": "task-abc-123",
}
