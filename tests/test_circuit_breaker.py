"""
Tests for the MaydayCircuitBreaker loop detection engine.
"""

from __future__ import annotations

import pytest

from hermes_mayday.circuit_breaker import MaydayCircuitBreaker
from conftest import SAMPLE_TOOL_CALL, SAMPLE_TOOL_CALL_WITH_VOLATILE, DIFFERENT_TOOL_CALL


class TestLoopDetection:
    """Test that identical repeated actions trigger the circuit breaker."""

    def test_identical_actions_trip_at_threshold(self, breaker: MaydayCircuitBreaker) -> None:
        """Three identical calls (default max_repeats=3) should trip on the third."""
        tc = SAMPLE_TOOL_CALL

        # First two calls should be allowed
        result1 = breaker.intercept(tc["tool_name"], tc["args"], tc["task_id"])
        result2 = breaker.intercept(tc["tool_name"], tc["args"], tc["task_id"])
        assert result1 is None
        assert result2 is None

        # Third call should trip
        result3 = breaker.intercept(tc["tool_name"], tc["args"], tc["task_id"])
        assert result3 is not None
        assert result3["action"] == "block"
        assert "MAYDAY" in result3["message"]

    def test_different_actions_dont_trip(self, breaker: MaydayCircuitBreaker) -> None:
        """Alternating between different tools should not trip.

        With max_repeats=3 and window_size=10, alternating between two
        tools will accumulate occurrences in the window. We keep the
        iteration count low enough that neither tool reaches the threshold.
        """
        tc1 = SAMPLE_TOOL_CALL
        tc2 = DIFFERENT_TOOL_CALL

        # 2 rounds = 4 total calls = 2 occurrences each (below threshold of 3)
        for _ in range(2):
            r1 = breaker.intercept(tc1["tool_name"], tc1["args"], tc1["task_id"])
            r2 = breaker.intercept(tc2["tool_name"], tc2["args"], tc2["task_id"])
            assert r1 is None
            assert r2 is None

    def test_strict_breaker_trips_at_two(self, strict_breaker: MaydayCircuitBreaker) -> None:
        """A breaker with max_repeats=2 should trip on the second identical call."""
        tc = SAMPLE_TOOL_CALL

        result1 = strict_breaker.intercept(tc["tool_name"], tc["args"], tc["task_id"])
        assert result1 is None

        result2 = strict_breaker.intercept(tc["tool_name"], tc["args"], tc["task_id"])
        assert result2 is not None
        assert result2["action"] == "block"

    def test_actions_outside_window_dont_accumulate(self, strict_breaker: MaydayCircuitBreaker) -> None:
        """
        If we push enough different actions to overflow the window,
        the old identical actions should be forgotten.
        """
        tc = SAMPLE_TOOL_CALL

        # One occurrence of the target action
        strict_breaker.intercept(tc["tool_name"], tc["args"], tc["task_id"])

        # Fill the window with different actions to push the first one out
        for i in range(10):
            strict_breaker.intercept("different_tool", {"i": i}, tc["task_id"])

        # Now the same action again — should be treated as occurrence #1, not #2
        result = strict_breaker.intercept(tc["tool_name"], tc["args"], tc["task_id"])
        assert result is None


class TestVolatileKeyFiltering:
    """Test that volatile keys are stripped before hashing."""

    def test_same_action_with_different_timestamps_match(self, breaker: MaydayCircuitBreaker) -> None:
        """
        Two logically identical calls with different timestamps should
        produce the same hash (because 'timestamp' is volatile).
        """
        args_v1 = {
            "command": "python build.py",
            "timestamp": "2026-09-02T10:00:00Z",
            "request_id": "req-001",
        }
        args_v2 = {
            "command": "python build.py",
            "timestamp": "2026-09-02T10:00:05Z",
            "request_id": "req-002",
        }

        hash1 = breaker._hash_action("run_bash_command", args_v1)
        hash2 = breaker._hash_action("run_bash_command", args_v2)

        assert hash1 == hash2, "Volatile keys should be stripped — hashes must match"

    def test_different_commands_produce_different_hashes(self, breaker: MaydayCircuitBreaker) -> None:
        """Actions with different non-volatile args should have different hashes."""
        args_v1 = {"command": "python build.py"}
        args_v2 = {"command": "python test.py"}

        hash1 = breaker._hash_action("run_bash_command", args_v1)
        hash2 = breaker._hash_action("run_bash_command", args_v2)

        assert hash1 != hash2

    def test_nested_volatile_keys_are_stripped(self, breaker: MaydayCircuitBreaker) -> None:
        """Volatile keys nested inside dicts should also be stripped."""
        args_v1 = {
            "config": {"path": "/etc/app.conf", "timestamp": "2026-01-01"},
        }
        args_v2 = {
            "config": {"path": "/etc/app.conf", "timestamp": "2026-12-31"},
        }

        hash1 = breaker._hash_action("read_file", args_v1)
        hash2 = breaker._hash_action("read_file", args_v2)

        assert hash1 == hash2


class TestSoftMode:
    """Test that soft mode warns but doesn't block."""

    def test_soft_mode_returns_none_on_trip(self, soft_breaker: MaydayCircuitBreaker) -> None:
        """In soft mode, the breaker should return None even when tripped."""
        tc = SAMPLE_TOOL_CALL

        for _ in range(5):
            result = soft_breaker.intercept(tc["tool_name"], tc["args"], tc["task_id"])

        # Even after many repeats, soft mode should never return a block
        assert result is None

    def test_soft_mode_still_generates_report(self, soft_breaker: MaydayCircuitBreaker) -> None:
        """Soft mode should still generate a crash report when tripped."""
        tc = SAMPLE_TOOL_CALL

        for _ in range(3):
            soft_breaker.intercept(tc["tool_name"], tc["args"], tc["task_id"])

        assert soft_breaker._total_trips >= 1


class TestDiagnostics:
    """Test the diagnostic reporting."""

    def test_diagnostics_track_calls(self, breaker: MaydayCircuitBreaker) -> None:
        tc = SAMPLE_TOOL_CALL
        breaker.intercept(tc["tool_name"], tc["args"], tc["task_id"])
        breaker.intercept(tc["tool_name"], tc["args"], tc["task_id"])

        diag = breaker.get_diagnostics()
        assert diag["total_calls"] == 2
        assert diag["window_size"] == 2

    def test_diagnostics_track_trips(self, breaker: MaydayCircuitBreaker) -> None:
        tc = SAMPLE_TOOL_CALL
        for _ in range(3):
            breaker.intercept(tc["tool_name"], tc["args"], tc["task_id"])

        diag = breaker.get_diagnostics()
        assert diag["total_trips"] == 1

    def test_reset_clears_state(self, breaker: MaydayCircuitBreaker) -> None:
        tc = SAMPLE_TOOL_CALL
        breaker.intercept(tc["tool_name"], tc["args"], tc["task_id"])
        breaker.reset()

        diag = breaker.get_diagnostics()
        assert diag["total_calls"] == 0
        assert diag["window_size"] == 0
