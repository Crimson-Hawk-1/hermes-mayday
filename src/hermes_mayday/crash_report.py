"""
Forensic crash report generator for hermes-mayday.

When the circuit breaker trips, this module dumps a timestamped
Markdown report containing the full action history, the offending
tool call, and diagnostic data for human debugging.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_mayday.config import MaydayConfig


class CrashReportWriter:
    """
    Writes forensic ``mayday-crash-report-*.md`` files when the
    circuit breaker trips.

    Reports are saved to the configured ``report_dir``, which defaults
    to the agent's current workspace. This ensures reports persist even
    on ephemeral/serverless deployments.
    """

    def __init__(self, config: MaydayConfig) -> None:
        self.config = config

    def write(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        occurrences: int,
        task_id: str,
        window_history: list[dict[str, Any]],
        diagnostics: dict[str, Any],
    ) -> str:
        """
        Generate a forensic crash report and write it to disk.

        Args:
            tool_name: The tool that triggered the circuit breaker.
            tool_args: The arguments that were being repeated.
            occurrences: How many times the action was repeated.
            task_id: The Hermes task/session ID.
            window_history: The full rolling window of recent actions.
            diagnostics: Circuit breaker diagnostic counters.

        Returns:
            The absolute path to the generated report file.
        """
        now = datetime.now(timezone.utc)
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        filename = f"mayday-crash-report-{timestamp_str}.md"

        # Resolve the output directory
        report_dir = self._resolve_report_dir()
        report_path = report_dir / filename

        # Build the report content
        content = self._build_report(
            tool_name=tool_name,
            tool_args=tool_args,
            occurrences=occurrences,
            task_id=task_id,
            window_history=window_history,
            diagnostics=diagnostics,
            timestamp=now,
        )

        # Write it
        report_path.write_text(content, encoding="utf-8")

        return str(report_path)

    def _resolve_report_dir(self) -> Path:
        """
        Resolve the report output directory.

        Checks (in order):
        1. The configured ``report_dir``
        2. ``HERMES_HOME`` environment variable
        3. Current working directory as fallback
        """
        configured = self.config.report_dir

        if configured and configured != "./":
            path = Path(configured)
        else:
            hermes_home = os.environ.get("HERMES_HOME")
            if hermes_home:
                path = Path(hermes_home)
            else:
                path = Path.cwd()

        path.mkdir(parents=True, exist_ok=True)
        return path

    def _build_report(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        occurrences: int,
        task_id: str,
        window_history: list[dict[str, Any]],
        diagnostics: dict[str, Any],
        timestamp: datetime,
    ) -> str:
        """Build the Markdown content for the crash report."""
        args_json = json.dumps(tool_args, indent=2, default=str)
        history_json = json.dumps(window_history, indent=2, default=str)
        diag_json = json.dumps(diagnostics, indent=2, default=str)

        return f"""# 🚨 MAYDAY — Circuit Breaker Crash Report

**Generated:** {timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}
**Task ID:** `{task_id}`
**Halt Mode:** `{self.config.halt_mode}`

---

## Fatal Loop Detected

The Mayday circuit breaker has tripped because the agent attempted
the **same action {occurrences} times** within a rolling window of
{self.config.window_size} actions.

This typically indicates the agent is stuck in an infinite retry loop,
repeatedly calling a failing tool without changing its approach.

---

## Offending Action

**Tool:** `{tool_name}`

**Arguments:**
```json
{args_json}
```

**Consecutive Occurrences:** {occurrences} (threshold: {self.config.max_repeats})

---

## Action History (Rolling Window)

The following actions were in the circuit breaker's rolling window
at the time of the trip. Identical hashes indicate repeated actions.

```json
{history_json}
```

---

## Circuit Breaker Diagnostics

```json
{diag_json}
```

---

## What To Do Next

1. **Investigate** why the tool `{tool_name}` is failing or returning
   the same result repeatedly.
2. **Check** whether the agent's context/memory has drifted from the
   original objective.
3. **Adjust** the circuit breaker settings if this was a false positive:
   - Increase `MAYDAY_MAX_REPEATS` (currently {self.config.max_repeats})
   - Increase `MAYDAY_WINDOW_SIZE` (currently {self.config.window_size})
   - Switch to `MAYDAY_HALT_MODE=soft` for warnings without halting
4. **Restart** the agent session once the root cause is addressed.

---

*Report generated by [hermes-mayday](https://github.com/your-username/hermes-mayday) v0.1.0*
"""
