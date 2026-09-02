"""
Circuit breaker engine for hermes-mayday.

Maintains a rolling window of action hashes and trips when the same
action repeats beyond the configured threshold.
"""

from __future__ import annotations

import hashlib
import json
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from hermes_mayday.config import MaydayConfig
from hermes_mayday.crash_report import CrashReportWriter
from hermes_mayday.display import MaydayDisplay


@dataclass
class ActionRecord:
    """A single recorded action in the rolling window."""

    tool_name: str
    args: dict[str, Any]
    action_hash: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MaydayCircuitBreaker:
    """
    Core loop-detection engine.

    Sits on the Hermes ``pre_tool_call`` hook and monitors every tool
    invocation for repetitive patterns. When the same action (identified
    by a deterministic hash of tool name + arguments) appears more than
    ``max_repeats`` times within the rolling window, the circuit breaker
    trips.

    In **hard** mode, it returns a block directive to Hermes, halting
    execution. In **soft** mode, it logs a warning but allows the agent
    to continue.
    """

    def __init__(
        self,
        config: MaydayConfig,
        display: MaydayDisplay,
        report_writer: CrashReportWriter,
    ) -> None:
        self.config = config
        self.display = display
        self.report_writer = report_writer

        # Rolling window of recent action hashes
        self._window: deque[ActionRecord] = deque(maxlen=config.window_size)

        # Lifetime counters for diagnostics
        self._total_calls: int = 0
        self._total_warnings: int = 0
        self._total_trips: int = 0

    # ── Public API ──────────────────────────────────────────────

    def intercept(
        self, tool_name: str, args: dict[str, Any], task_id: str
    ) -> dict[str, str] | None:
        """
        Hermes ``pre_tool_call`` hook handler.

        Called by Hermes before every tool execution. Returns ``None``
        to allow the tool call, or a block directive dict to halt it.

        Args:
            tool_name: Name of the tool being called (e.g. "run_bash_command").
            args: Dictionary of arguments passed to the tool.
            task_id: Hermes task/session identifier.

        Returns:
            ``None`` to allow the call, or
            ``{"action": "block", "message": "..."}`` to halt execution.
        """
        self._total_calls += 1

        # Hash the action, filtering out volatile keys
        action_hash = self._hash_action(tool_name, args)

        # Record it in the rolling window
        record = ActionRecord(
            tool_name=tool_name,
            args=args,
            action_hash=action_hash,
        )
        self._window.append(record)

        # Count how many times this exact hash appears in the window
        occurrences = self._count_occurrences(action_hash)

        if occurrences >= self.config.max_repeats:
            return self._trip(record, occurrences, task_id)

        # Warn when approaching the threshold (at max_repeats - 1)
        if occurrences == self.config.max_repeats - 1 and self.config.max_repeats > 1:
            self._total_warnings += 1
            self.display.warn_repeat(
                tool_name=tool_name,
                occurrences=occurrences,
                max_repeats=self.config.max_repeats,
            )

        return None  # Allow the call

    def get_diagnostics(self) -> dict[str, Any]:
        """Return current circuit breaker state for debugging."""
        return {
            "total_calls": self._total_calls,
            "total_warnings": self._total_warnings,
            "total_trips": self._total_trips,
            "window_size": len(self._window),
            "window_capacity": self.config.window_size,
            "halt_mode": self.config.halt_mode,
        }

    def reset(self) -> None:
        """Clear the rolling window and reset counters."""
        self._window.clear()
        self._total_calls = 0
        self._total_warnings = 0
        self._total_trips = 0

    # ── Private helpers ─────────────────────────────────────────

    def _hash_action(self, tool_name: str, args: dict[str, Any]) -> str:
        """
        Create a deterministic SHA-256 hash for a tool call.

        Strips volatile keys (timestamps, request IDs) from the arguments
        before hashing so that logically identical calls produce the same
        hash even if metadata differs.
        """
        cleaned_args = self._strip_volatile_keys(args)

        action_payload = json.dumps(
            {"tool": tool_name, "args": cleaned_args},
            sort_keys=True,
            default=str,  # Handle non-serializable types gracefully
        )
        return hashlib.sha256(action_payload.encode("utf-8")).hexdigest()

    def _strip_volatile_keys(self, args: dict[str, Any]) -> dict[str, Any]:
        """
        Recursively remove volatile keys from arguments.

        This prevents false negatives where two identical failing calls
        produce different hashes because of embedded timestamps.
        """
        volatile = set(self.config.volatile_keys)
        return self._strip_keys_recursive(args, volatile)

    def _strip_keys_recursive(
        self, obj: Any, volatile: set[str]
    ) -> Any:
        """Recursively strip volatile keys from nested dicts/lists."""
        if isinstance(obj, dict):
            return {
                k: self._strip_keys_recursive(v, volatile)
                for k, v in obj.items()
                if k not in volatile
            }
        if isinstance(obj, list):
            return [self._strip_keys_recursive(item, volatile) for item in obj]
        return obj

    def _count_occurrences(self, action_hash: str) -> int:
        """Count how many times this hash appears in the rolling window."""
        return sum(1 for record in self._window if record.action_hash == action_hash)

    def _trip(
        self,
        record: ActionRecord,
        occurrences: int,
        task_id: str,
    ) -> dict[str, str] | None:
        """
        Execute the circuit breaker trip sequence.

        1. Display a loud terminal alert
        2. Generate a forensic crash report
        3. Return block directive (hard mode) or None (soft mode)
        """
        self._total_trips += 1

        # Build context for the crash report
        window_history = [
            {
                "tool": r.tool_name,
                "args": r.args,
                "hash": r.action_hash[:12],
                "time": r.timestamp.isoformat(),
            }
            for r in self._window
        ]

        # 1. Terminal alert
        self.display.alert_loop_detected(
            tool_name=record.tool_name,
            occurrences=occurrences,
            halt_mode=self.config.halt_mode,
        )

        # 2. Crash report
        report_path = self.report_writer.write(
            tool_name=record.tool_name,
            tool_args=record.args,
            occurrences=occurrences,
            task_id=task_id,
            window_history=window_history,
            diagnostics=self.get_diagnostics(),
        )

        self.display.report_saved(report_path)

        # 3. Halt or warn
        if self.config.halt_mode == "hard":
            return {
                "action": "block",
                "message": (
                    f"🚨 MAYDAY: Circuit breaker tripped — "
                    f"tool '{record.tool_name}' repeated {occurrences} times. "
                    f"Crash report saved to: {report_path}"
                ),
            }

        # Soft mode: warn but don't block
        return None
