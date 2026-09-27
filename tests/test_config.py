# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for centralized host configuration."""

from __future__ import annotations

from pathlib import Path

from vardoger.config import CopilotConfig, OpenClawConfig


def test_copilot_config_defaults_to_dot_copilot(fake_home: Path) -> None:
    config = CopilotConfig.from_env({})

    assert config.home == fake_home / ".copilot"
    assert config.session_state_dir == fake_home / ".copilot" / "session-state"
    assert config.instructions_path == fake_home / ".copilot" / "copilot-instructions.md"


def test_copilot_home_replaces_complete_default_root(tmp_path: Path) -> None:
    configured = tmp_path / "custom-copilot"
    config = CopilotConfig.from_env({"COPILOT_HOME": str(configured)})

    assert config.home == configured
    assert config.session_state_dir == configured / "session-state"
    assert config.instructions_path == configured / "copilot-instructions.md"


def test_openclaw_gateway_requires_explicit_enablement() -> None:
    assert OpenClawConfig.from_env({}).gateway_enabled is False
    assert OpenClawConfig.from_env({"VARDOGER_OPENCLAW_GATEWAY": "0"}).gateway_enabled is False


def test_openclaw_gateway_accepts_explicit_boolean_values() -> None:
    for value in ("1", "true", "YES", "on"):
        assert OpenClawConfig.from_env({"VARDOGER_OPENCLAW_GATEWAY": value}).gateway_enabled
