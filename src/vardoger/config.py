# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Centralized environment-backed configuration for supported hosts."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CopilotConfig:
    """Filesystem locations owned by GitHub Copilot CLI.

    ``COPILOT_HOME`` replaces the complete default ``~/.copilot`` directory,
    so every Copilot integration must derive its paths from the same root.
    """

    home: Path

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> CopilotConfig:
        """Build configuration from ``COPILOT_HOME`` and the current home."""
        values = os.environ if environ is None else environ
        configured_home = values.get("COPILOT_HOME", "").strip()
        home = Path(configured_home).expanduser() if configured_home else Path.home() / ".copilot"
        return cls(home=home)

    @property
    def session_state_dir(self) -> Path:
        """Directory containing current and legacy session event logs."""
        return self.home / "session-state"

    @property
    def instructions_path(self) -> Path:
        """User-global custom-instructions file."""
        return self.home / "copilot-instructions.md"


@dataclass(frozen=True)
class OpenClawConfig:
    """Opt-in access to OpenClaw's documented local Gateway CLI.

    Gateway reads are disabled by default because they connect to a running
    authenticated service rather than opening passive history files.  Vardoger
    never accepts a Gateway URL, token, or password; the official OpenClaw CLI
    resolves its own local configuration and authentication.
    """

    gateway_enabled: bool

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> OpenClawConfig:
        """Build configuration from an explicit boolean enablement flag."""
        values = os.environ if environ is None else environ
        raw = values.get("VARDOGER_OPENCLAW_GATEWAY", "").strip().lower()
        return cls(gateway_enabled=raw in {"1", "true", "yes", "on"})
