"""
hermes-mayday — Circuit Breaker Plugin for Hermes Agent

Detects runaway tool loops and halts agent execution before it burns
your API credits. Generates forensic crash reports for human debugging.
"""

from __future__ import annotations

__version__ = "0.1.0"

from hermes_mayday.config import MaydayConfig
from hermes_mayday.circuit_breaker import MaydayCircuitBreaker
from hermes_mayday.crash_report import CrashReportWriter
from hermes_mayday.display import MaydayDisplay


def register(ctx) -> None:
    """
    Hermes plugin entry point.

    Called automatically by Hermes when it discovers this plugin via
    the ``hermes_agent.plugins`` entry point. Registers the Mayday
    circuit breaker on the ``pre_tool_call`` lifecycle hook.

    Args:
        ctx: The Hermes ``PluginContext`` object providing access to
             hook registration, configuration, and environment data.
    """
    # Load configuration from Hermes plugin config + env vars
    config = MaydayConfig.from_context(ctx)

    if not config.enabled:
        return

    # Initialize components
    display = MaydayDisplay()
    report_writer = CrashReportWriter(config=config)
    breaker = MaydayCircuitBreaker(
        config=config,
        display=display,
        report_writer=report_writer,
    )

    display.status_ok(
        f"Mayday v{__version__} armed — "
        f"max_repeats={config.max_repeats}, "
        f"window={config.window_size}, "
        f"mode={config.halt_mode}"
    )

    # Register the pre_tool_call hook with Hermes
    ctx.register_hook("pre_tool_call", breaker.intercept)
