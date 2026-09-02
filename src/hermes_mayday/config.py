"""
Configuration loader for hermes-mayday.

Reads settings from the Hermes PluginContext config schema first,
then falls back to environment variables, then to sensible defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class MaydayConfig:
    """All tunable parameters for the Mayday circuit breaker."""

    enabled: bool = True
    max_repeats: int = 3
    window_size: int = 10
    halt_mode: str = "hard"  # "hard" or "soft"
    report_dir: str = "./"
    volatile_keys: list[str] = field(
        default_factory=lambda: [
            "timestamp",
            "request_id",
            "trace_id",
            "created_at",
            "updated_at",
        ]
    )

    def __post_init__(self) -> None:
        """Validate configuration values after initialization."""
        if self.max_repeats < 1:
            self.max_repeats = 3
        if self.window_size < 1:
            self.window_size = 10
        if self.halt_mode not in ("hard", "soft"):
            self.halt_mode = "hard"

    @classmethod
    def from_context(cls, ctx) -> MaydayConfig:
        """
        Build a MaydayConfig from a Hermes PluginContext.

        Attempts to read values from the Hermes plugin config schema
        first (``ctx.config``), then falls back to environment variables
        prefixed with ``MAYDAY_``, then to dataclass defaults.

        Args:
            ctx: The Hermes PluginContext (or None for standalone usage).

        Returns:
            A fully-resolved MaydayConfig instance.
        """
        return cls(
            enabled=cls._resolve_bool(ctx, "enabled", "MAYDAY_ENABLED", True),
            max_repeats=cls._resolve_int(ctx, "max_repeats", "MAYDAY_MAX_REPEATS", 3),
            window_size=cls._resolve_int(ctx, "window_size", "MAYDAY_WINDOW_SIZE", 10),
            halt_mode=cls._resolve_str(ctx, "halt_mode", "MAYDAY_HALT_MODE", "hard"),
            report_dir=cls._resolve_str(ctx, "report_dir", "MAYDAY_REPORT_DIR", "./"),
            volatile_keys=cls._resolve_list(
                ctx,
                "volatile_keys",
                "MAYDAY_VOLATILE_KEYS",
                ["timestamp", "request_id", "trace_id", "created_at", "updated_at"],
            ),
        )

    @classmethod
    def from_env(cls) -> MaydayConfig:
        """
        Build a MaydayConfig from environment variables only.

        Useful for standalone usage outside of Hermes.
        """
        return cls.from_context(ctx=None)

    # ── Private resolution helpers ──────────────────────────────

    @staticmethod
    def _get_plugin_setting(ctx, key: str):
        """
        Attempt to read a setting from the Hermes PluginContext.

        Returns None if ctx is None or the key is not found.
        """
        if ctx is None:
            return None
        try:
            # Hermes exposes plugin settings via ctx.config or similar
            config = getattr(ctx, "config", None)
            if config and isinstance(config, dict):
                return config.get(key)
        except Exception:
            pass
        return None

    @classmethod
    def _resolve_bool(
        cls, ctx, config_key: str, env_key: str, default: bool
    ) -> bool:
        # Try Hermes config first
        val = cls._get_plugin_setting(ctx, config_key)
        if val is not None:
            if isinstance(val, bool):
                return val
            return str(val).lower() in ("true", "1", "yes")

        # Try environment variable
        env_val = os.environ.get(env_key)
        if env_val is not None:
            return env_val.lower() in ("true", "1", "yes")

        return default

    @classmethod
    def _resolve_int(
        cls, ctx, config_key: str, env_key: str, default: int
    ) -> int:
        val = cls._get_plugin_setting(ctx, config_key)
        if val is not None:
            try:
                return int(val)
            except (ValueError, TypeError):
                pass

        env_val = os.environ.get(env_key)
        if env_val is not None:
            try:
                return int(env_val)
            except ValueError:
                pass

        return default

    @classmethod
    def _resolve_str(
        cls, ctx, config_key: str, env_key: str, default: str
    ) -> str:
        val = cls._get_plugin_setting(ctx, config_key)
        if val is not None:
            return str(val)

        env_val = os.environ.get(env_key)
        if env_val is not None:
            return env_val

        return default

    @classmethod
    def _resolve_list(
        cls, ctx, config_key: str, env_key: str, default: list[str]
    ) -> list[str]:
        val = cls._get_plugin_setting(ctx, config_key)
        if val is not None:
            if isinstance(val, list):
                return val
            return [v.strip() for v in str(val).split(",") if v.strip()]

        env_val = os.environ.get(env_key)
        if env_val is not None:
            return [v.strip() for v in env_val.split(",") if v.strip()]

        return default
