"""
Tests for the CrashReportWriter forensic report generator.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_mayday.config import MaydayConfig
from hermes_mayday.crash_report import CrashReportWriter


class TestCrashReportCreation:
    """Test that crash reports are created correctly."""

    def test_report_file_is_created(self, report_writer: CrashReportWriter, tmp_path: Path) -> None:
        """A crash report file should be created in the configured directory."""
        path = report_writer.write(
            tool_name="run_bash_command",
            tool_args={"command": "python build.py"},
            occurrences=3,
            task_id="task-123",
            window_history=[],
            diagnostics={},
        )

        report_path = Path(path)
        assert report_path.exists()
        assert report_path.name.startswith("mayday-crash-report-")
        assert report_path.suffix == ".md"

    def test_report_naming_convention(self, report_writer: CrashReportWriter) -> None:
        """Report filename should follow mayday-crash-report-YYYYMMDD_HHMMSS.md."""
        path = report_writer.write(
            tool_name="test_tool",
            tool_args={},
            occurrences=3,
            task_id="task-456",
            window_history=[],
            diagnostics={},
        )

        filename = Path(path).name
        # Pattern: mayday-crash-report-20260902_123456.md
        assert filename.startswith("mayday-crash-report-")
        assert filename.endswith(".md")
        # The timestamp portion should be 15 chars (YYYYMMDD_HHMMSS)
        timestamp_part = filename.replace("mayday-crash-report-", "").replace(".md", "")
        assert len(timestamp_part) == 15


class TestCrashReportContent:
    """Test that crash reports contain the expected sections."""

    def test_report_contains_tool_name(self, report_writer: CrashReportWriter) -> None:
        path = report_writer.write(
            tool_name="run_bash_command",
            tool_args={"command": "python build.py"},
            occurrences=3,
            task_id="task-789",
            window_history=[],
            diagnostics={},
        )

        content = Path(path).read_text(encoding="utf-8")
        assert "run_bash_command" in content

    def test_report_contains_task_id(self, report_writer: CrashReportWriter) -> None:
        path = report_writer.write(
            tool_name="test_tool",
            tool_args={},
            occurrences=3,
            task_id="task-unique-id",
            window_history=[],
            diagnostics={},
        )

        content = Path(path).read_text(encoding="utf-8")
        assert "task-unique-id" in content

    def test_report_contains_mayday_header(self, report_writer: CrashReportWriter) -> None:
        path = report_writer.write(
            tool_name="test_tool",
            tool_args={},
            occurrences=5,
            task_id="task-000",
            window_history=[],
            diagnostics={},
        )

        content = Path(path).read_text(encoding="utf-8")
        assert "MAYDAY" in content
        assert "Circuit Breaker" in content

    def test_report_contains_args_json(self, report_writer: CrashReportWriter) -> None:
        test_args = {"command": "npm run build", "cwd": "/app"}
        path = report_writer.write(
            tool_name="run_bash_command",
            tool_args=test_args,
            occurrences=3,
            task_id="task-args",
            window_history=[],
            diagnostics={},
        )

        content = Path(path).read_text(encoding="utf-8")
        assert "npm run build" in content
        assert "/app" in content

    def test_report_contains_window_history(self, report_writer: CrashReportWriter) -> None:
        history = [
            {"tool": "read_file", "args": {"path": "x.py"}, "hash": "abc123", "time": "2026-09-02T10:00:00"},
            {"tool": "read_file", "args": {"path": "x.py"}, "hash": "abc123", "time": "2026-09-02T10:00:01"},
        ]

        path = report_writer.write(
            tool_name="read_file",
            tool_args={"path": "x.py"},
            occurrences=3,
            task_id="task-hist",
            window_history=history,
            diagnostics={},
        )

        content = Path(path).read_text(encoding="utf-8")
        assert "abc123" in content
        assert "Action History" in content

    def test_report_contains_next_steps(self, report_writer: CrashReportWriter) -> None:
        path = report_writer.write(
            tool_name="test_tool",
            tool_args={},
            occurrences=3,
            task_id="task-steps",
            window_history=[],
            diagnostics={},
        )

        content = Path(path).read_text(encoding="utf-8")
        assert "What To Do Next" in content


class TestCrashReportDirectory:
    """Test that reports respect the configured output directory."""

    def test_report_saved_to_configured_dir(self, tmp_path: Path) -> None:
        custom_dir = tmp_path / "custom_reports"
        config = MaydayConfig(report_dir=str(custom_dir))
        writer = CrashReportWriter(config=config)

        path = writer.write(
            tool_name="test_tool",
            tool_args={},
            occurrences=3,
            task_id="task-dir",
            window_history=[],
            diagnostics={},
        )

        assert Path(path).parent == custom_dir
        assert custom_dir.exists()

    def test_report_dir_created_if_missing(self, tmp_path: Path) -> None:
        deep_dir = tmp_path / "deep" / "nested" / "reports"
        config = MaydayConfig(report_dir=str(deep_dir))
        writer = CrashReportWriter(config=config)

        writer.write(
            tool_name="test_tool",
            tool_args={},
            occurrences=3,
            task_id="task-mkdir",
            window_history=[],
            diagnostics={},
        )

        assert deep_dir.exists()
