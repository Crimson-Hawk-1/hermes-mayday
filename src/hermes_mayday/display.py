"""
Terminal display handler for hermes-mayday.

Provides rich, colored terminal output when the ``rich`` library is
installed, with a graceful fallback to plain-text ANSI output when
it is not.
"""

from __future__ import annotations

import sys

# Attempt to import rich; fall back gracefully
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class MaydayDisplay:
    """
    Terminal output for Mayday events.

    Automatically detects whether ``rich`` is available and switches
    between a colored, formatted display and a plain-text fallback.
    """

    def __init__(self) -> None:
        if RICH_AVAILABLE:
            self._console = Console(stderr=True)
        else:
            self._console = None

    # ── Public methods ──────────────────────────────────────────

    def status_ok(self, message: str) -> None:
        """Display a startup confirmation message."""
        if RICH_AVAILABLE and self._console:
            self._console.print(
                f"[bold green]✅ MAYDAY[/bold green] {message}"
            )
        else:
            self._print_plain(f"[MAYDAY OK] {message}")

    def warn_repeat(
        self, tool_name: str, occurrences: int, max_repeats: int
    ) -> None:
        """Warn that an action is approaching the repeat threshold."""
        msg = (
            f"Tool '{tool_name}' has been called {occurrences} time(s) "
            f"in the rolling window (threshold: {max_repeats}). "
            f"One more repeat will trip the circuit breaker."
        )
        if RICH_AVAILABLE and self._console:
            self._console.print(
                Panel(
                    f"[bold yellow]{msg}[/bold yellow]",
                    title="[yellow]⚠️  MAYDAY WARNING[/yellow]",
                    border_style="yellow",
                )
            )
        else:
            self._print_plain(f"[MAYDAY WARNING] {msg}")

    def alert_loop_detected(
        self, tool_name: str, occurrences: int, halt_mode: str
    ) -> None:
        """Display a critical alert when the circuit breaker trips."""
        action_text = "EXECUTION HALTED" if halt_mode == "hard" else "WARNING ONLY (soft mode)"

        if RICH_AVAILABLE and self._console:
            # Build the big red alert
            alert_text = Text()
            alert_text.append("\n")
            alert_text.append("  🚨 MAYDAY MAYDAY MAYDAY 🚨\n\n", style="bold red blink")
            alert_text.append(f"  Infinite loop detected on tool: ", style="bold white")
            alert_text.append(f"{tool_name}\n", style="bold cyan")
            alert_text.append(f"  Consecutive occurrences: ", style="bold white")
            alert_text.append(f"{occurrences}\n", style="bold red")
            alert_text.append(f"  Action: ", style="bold white")
            alert_text.append(f"{action_text}\n", style="bold red" if halt_mode == "hard" else "bold yellow")

            self._console.print(
                Panel(
                    alert_text,
                    title="[bold red]CIRCUIT BREAKER TRIPPED[/bold red]",
                    border_style="bold red",
                    padding=(1, 2),
                )
            )
        else:
            self._print_plain("")
            self._print_plain("=" * 56)
            self._print_plain("  🚨 MAYDAY MAYDAY MAYDAY 🚨")
            self._print_plain(f"  Infinite loop detected on tool: {tool_name}")
            self._print_plain(f"  Consecutive occurrences: {occurrences}")
            self._print_plain(f"  Action: {action_text}")
            self._print_plain("=" * 56)
            self._print_plain("")

    def report_saved(self, path: str) -> None:
        """Notify the developer that a crash report has been saved."""
        if RICH_AVAILABLE and self._console:
            self._console.print(
                f"[bold blue]📋 MAYDAY[/bold blue] "
                f"Crash report saved to: [underline]{path}[/underline]"
            )
        else:
            self._print_plain(f"[MAYDAY] Crash report saved to: {path}")

    # ── Private helpers ─────────────────────────────────────────

    @staticmethod
    def _print_plain(message: str) -> None:
        """Print to stderr without any rich formatting."""
        print(message, file=sys.stderr)
