# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Validate the portable Agent Plugins packages tracked in this repository."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from vardoger import __version__
from vardoger.models import ClaudePluginManifest, CursorMcpConfig

REPO_ROOT = Path(__file__).parents[1]
PLUGIN_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MCP_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"

VERSIONED_MANIFESTS = (
    "plugins/claude-code/.claude-plugin/plugin.json",
    "plugins/codex/.codex-plugin/plugin.json",
    "plugins/codex/plugin.json",
    "plugins/copilot/.github/plugin/plugin.json",
    "plugins/copilot/plugin.json",
    "plugins/cursor/.cursor-plugin/plugin.json",
    "plugins/cursor/plugin.json",
    "plugins/devin/.devin-plugin/plugin.json",
)


def test_runtime_mcp_dependency_stays_on_fastmcp_api() -> None:
    """Fresh installs must not resolve the incompatible MCP 2.x API."""
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert "mcp>=1.0.0,<2" in project["project"]["dependencies"]


@pytest.mark.parametrize("manifest_path", VERSIONED_MANIFESTS)
def test_release_manifests_match_package_version(manifest_path: str) -> None:
    """Release metadata must move in lock-step with the Python package."""
    manifest = json.loads((REPO_ROOT / manifest_path).read_text(encoding="utf-8"))

    assert manifest["version"] == __version__


def test_marketplace_and_registry_versions_match_package() -> None:
    """Nested distribution records must point at the release being prepared."""
    claude = json.loads(
        (REPO_ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8")
    )
    copilot = json.loads(
        (REPO_ROOT / "plugins/copilot/marketplace.json").read_text(encoding="utf-8")
    )
    registry = json.loads(
        (REPO_ROOT / "plugins/mcp-registry/server.json").read_text(encoding="utf-8")
    )

    assert claude["metadata"]["version"] == __version__
    assert claude["plugins"][0]["version"] == __version__
    assert copilot["metadata"]["version"] == __version__
    assert copilot["plugins"][0]["version"] == __version__
    assert registry["version"] == __version__
    assert registry["packages"][0]["version"] == __version__


def test_openclaw_skill_version_matches_package() -> None:
    """ClawHub frontmatter must carry the same version as the wheel."""
    skill = (REPO_ROOT / "plugins/openclaw/skills/analyze/SKILL.md").read_text(encoding="utf-8")

    assert f'version: "{__version__}"' in skill.split("---", 2)[1]


@pytest.mark.parametrize(
    ("platform", "description", "keywords"),
    [
        (
            "codex",
            "Personalizes your AI assistant from local conversation history using the active "
            "host model.",
            ["personalization", "productivity", "skills", "local-first"],
        ),
        (
            "copilot",
            "Personalizes your AI assistant from local conversation history using the active "
            "host model.",
            ["personalization", "productivity", "skills", "local-first"],
        ),
        (
            "cursor",
            "Personalizes your AI assistant from local conversation history using the active "
            "host model.",
            ["personalization", "productivity", "mcp", "local-first"],
        ),
    ],
)
def test_portable_plugin_manifest(
    platform: str,
    description: str,
    keywords: list[str],
) -> None:
    """Every portable manifest uses only the closed Agent Plugins 1.0 fields."""
    manifest_path = REPO_ROOT / "plugins" / platform / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest == {
        "$schema": PLUGIN_SCHEMA,
        "name": "vardoger",
        "version": __version__,
        "description": description,
        "author": {"name": "David Strupl"},
        "homepage": "https://github.com/dstrupl/vardoger",
        "repository": "https://github.com/dstrupl/vardoger",
        "license": "Apache-2.0",
        "keywords": keywords,
    }


@pytest.mark.parametrize(
    "compatibility_manifest",
    [
        "plugins/codex/.codex-plugin/plugin.json",
        "plugins/copilot/.github/plugin/plugin.json",
        "plugins/cursor/.cursor-plugin/plugin.json",
    ],
)
def test_legacy_compatibility_manifest_is_retained(compatibility_manifest: str) -> None:
    """Portable packaging must not break existing host-specific install paths."""
    assert (REPO_ROOT / compatibility_manifest).is_file()


def test_cursor_mcp_configuration_uses_portable_schema() -> None:
    """Cursor's MCP server declares the transport required by Agent Plugins 1.0."""
    mcp_path = REPO_ROOT / "plugins" / "cursor" / "mcp.json"
    mcp_config = json.loads(mcp_path.read_text(encoding="utf-8"))

    assert mcp_config == {
        "$schema": MCP_SCHEMA,
        "mcpServers": {
            "vardoger": {
                "type": "stdio",
                "command": "uvx",
                "args": ["vardoger", "mcp"],
            }
        },
    }


def test_codex_interface_meets_final_directory_text_limits() -> None:
    """Codex listing text must satisfy stricter final-submission limits."""
    manifest_path = REPO_ROOT / "plugins/codex/.codex-plugin/plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    interface = manifest["interface"]

    assert len(interface["displayName"]) <= 30
    assert len(interface["shortDescription"]) <= 30
    assert len(interface["developerName"]) <= 80
    assert interface["supportURL"] == "https://github.com/dstrupl/vardoger/issues"


def test_devin_native_plugin_package() -> None:
    """Devin gets its native manifest, skill, and defaulted MCP platform."""
    plugin_root = REPO_ROOT / "plugins" / "devin"
    manifest = ClaudePluginManifest.model_validate_json(
        (plugin_root / ".devin-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    mcp_config = CursorMcpConfig.model_validate_json(
        (plugin_root / ".mcp.json").read_text(encoding="utf-8")
    )

    assert manifest.name == "vardoger"
    assert manifest.skills == "./skills/"
    assert (plugin_root / "skills" / "analyze" / "SKILL.md").is_file()
    assert mcp_config.mcpServers["vardoger"].env == {"VARDOGER_MCP_PLATFORM": "devin"}
