# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Platform setup for vardoger.

Handles post-install registration for each supported platform:
  - Cursor: registers MCP server in ~/.cursor/mcp.json
  - Claude Code: creates plugin directory and prints activation command
  - Codex: creates plugin directory and registers in marketplace.json
  - OpenClaw: installs analysis skill to ~/.openclaw/skills/vardoger/
"""

from __future__ import annotations

import sys
from pathlib import Path

from pydantic import ValidationError

from vardoger.models import (
    ClaudePluginManifest,
    CodexMarketplace,
    CodexPluginInterface,
    CodexPluginManifest,
    CursorMcpConfig,
    MarketplaceInterface,
    MarketplacePlugin,
    MarketplacePluginPolicy,
    MarketplacePluginSource,
    McpServerConfig,
    PluginAuthor,
)
from vardoger.prompts import analyze_skill_body

CLAUDE_PLUGIN_MANIFEST = ClaudePluginManifest(
    name="vardoger",
    version="0.2.0",
    description=(
        "Personalizes your AI assistant by analyzing conversation "
        "history and generating tailored rules. Runs entirely on your machine."
    ),
    author=PluginAuthor(name="David Strupl"),
    homepage="https://github.com/dstrupl/vardoger",
    repository="https://github.com/dstrupl/vardoger",
    license="Apache-2.0",
    keywords=["personalization", "productivity", "skills", "local-first"],
)

CODEX_PLUGIN_MANIFEST = CodexPluginManifest(
    name="vardoger",
    version="0.2.0",
    description=(
        "Personalizes your AI assistant by analyzing conversation "
        "history and generating tailored instructions. Runs entirely on your machine."
    ),
    author=PluginAuthor(name="David Strupl"),
    homepage="https://github.com/dstrupl/vardoger",
    repository="https://github.com/dstrupl/vardoger",
    license="Apache-2.0",
    keywords=["personalization", "productivity", "skills", "local-first"],
    interface=CodexPluginInterface(
        displayName="Vardoger",
        shortDescription="Personalize your assistant from your own conversation history",
        longDescription=(
            "Vardoger reads your Codex conversation history locally, extracts "
            "behavioral patterns, and generates a personalized AGENTS.md "
            "addition so the assistant adapts to how you actually work. "
            "All processing happens on your machine — no data leaves it."
        ),
        developerName="dstrupl",
        category="Productivity",
        capabilities=["Read", "Write"],
        websiteURL="https://github.com/dstrupl/vardoger",
    ),
)


def _vardoger_plugin_dir() -> Path:
    return Path.home() / ".vardoger" / "plugins"


_PLATFORM_LABELS: dict[str, str] = {
    "claude-code": "Claude Code",
    "codex": "Codex",
    "openclaw": "OpenClaw",
}


def _render_skill(platform: str) -> str:
    """Compose frontmatter + shared body into a full SKILL.md for a platform."""
    label = _PLATFORM_LABELS.get(platform, platform)
    description = (
        f"Use when the user asks to personalize their assistant, to use vardoger, "
        f"or to analyze their {label} conversation history. Runs the vardoger CLI "
        f"to read past conversations and generate tailored instructions."
    )
    frontmatter = f'---\nname: analyze\ndescription: "{description}"\n---\n'
    return frontmatter + analyze_skill_body(platform, label)


def _write_skill(plugin_dir: Path, platform: str) -> None:
    """Write the SKILL.md file for a CLI-based platform."""
    skill_dir = plugin_dir / "skills" / "analyze"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(_render_skill(platform), encoding="utf-8")


def setup_cursor() -> None:
    """Register the vardoger MCP server in ~/.cursor/mcp.json."""
    mcp_config_path = Path.home() / ".cursor" / "mcp.json"
    mcp_config_path.parent.mkdir(parents=True, exist_ok=True)

    if mcp_config_path.is_file():
        raw = mcp_config_path.read_text(encoding="utf-8")
        try:
            config = CursorMcpConfig.model_validate_json(raw)
        except ValidationError:
            config = CursorMcpConfig()
    else:
        config = CursorMcpConfig()

    config.mcpServers["vardoger"] = McpServerConfig(
        command=sys.executable,
        args=["-m", "vardoger.mcp_server"],
    )

    mcp_config_path.write_text(config.model_dump_json(indent=2) + "\n", encoding="utf-8")

    print(f"Registered vardoger MCP server in {mcp_config_path}")
    print("Restart Cursor to activate.")
    print()
    _print_getting_started()


def setup_claude_code() -> None:
    """Create the Claude Code plugin directory and print activation command."""
    plugin_dir = _vardoger_plugin_dir() / "claude-code"

    manifest_dir = plugin_dir / ".claude-plugin"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "plugin.json").write_text(
        CLAUDE_PLUGIN_MANIFEST.model_dump_json(indent=2, exclude_none=True) + "\n",
        encoding="utf-8",
    )

    _write_skill(plugin_dir, "claude-code")

    print(f"Created Claude Code plugin at {plugin_dir}")
    print()
    print("Activate by starting Claude Code with:")
    print(f"  claude --plugin-dir {plugin_dir}")
    print()
    _print_getting_started()


def setup_codex() -> None:
    """Create the Codex plugin directory and register in marketplace.json.

    Codex resolves each plugin's ``source.path`` relative to the *parent* of
    the ``.agents/`` directory that holds ``marketplace.json`` (e.g. ``$HOME``
    for the personal marketplace) — not the ``.agents/plugins/`` folder
    itself. We therefore install the plugin under ``~/.codex/plugins/vardoger``
    and reference it as ``./.codex/plugins/vardoger`` so Codex can locate the
    manifest and show the plugin with its display name, description, and an
    install button in ``/plugins``.
    """
    marketplace_path = Path.home() / ".agents" / "plugins" / "marketplace.json"
    marketplace_path.parent.mkdir(parents=True, exist_ok=True)
    plugin_rel_path = "./.codex/plugins/vardoger"
    plugin_dir = Path.home() / ".codex" / "plugins" / "vardoger"

    manifest_dir = plugin_dir / ".codex-plugin"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "plugin.json").write_text(
        CODEX_PLUGIN_MANIFEST.model_dump_json(indent=2, exclude_none=True) + "\n",
        encoding="utf-8",
    )

    _write_skill(plugin_dir, "codex")

    if marketplace_path.is_file():
        raw = marketplace_path.read_text(encoding="utf-8")
        try:
            marketplace = CodexMarketplace.model_validate_json(raw)
        except ValidationError:
            marketplace = CodexMarketplace()
    else:
        marketplace = CodexMarketplace()

    if marketplace.interface is None:
        marketplace.interface = MarketplaceInterface(displayName="Local Plugins")

    marketplace.plugins = [p for p in marketplace.plugins if p.name != "vardoger"]
    marketplace.plugins.append(
        MarketplacePlugin(
            name="vardoger",
            source=MarketplacePluginSource(source="local", path=plugin_rel_path),
            policy=MarketplacePluginPolicy(
                installation="AVAILABLE",
                authentication="ON_INSTALL",
            ),
            category="Productivity",
        )
    )

    marketplace_path.write_text(
        marketplace.model_dump_json(indent=2, exclude_none=True) + "\n",
        encoding="utf-8",
    )

    print(f"Created Codex plugin at {plugin_dir}")
    print(f"Registered in {marketplace_path}")
    print("Restart Codex, run /plugins, pick the 'Local Plugins' marketplace, and install.")
    print()
    _print_getting_started()


def setup_openclaw() -> None:
    """Install the vardoger analysis skill into OpenClaw's user skill directory."""
    skill_dir = Path.home() / ".openclaw" / "skills" / "vardoger"
    skill_dir.mkdir(parents=True, exist_ok=True)

    _write_skill(skill_dir, "openclaw")

    print(f"Installed vardoger skill to {skill_dir}")
    print("OpenClaw will discover it automatically on the next session.")
    print()
    _print_getting_started()


def setup_copilot() -> None:
    """Prepare the GitHub Copilot CLI instructions path for vardoger output.

    Copilot CLI does have a plugin marketplace (see ``plugins/copilot/`` in
    this repo) but plugin installation goes through ``copilot plugin install``
    rather than a ``vardoger setup`` flow. This command focuses on the
    personalization surface: it ensures ``~/.copilot/copilot-instructions.md``
    exists (creating a short placeholder when absent) so that
    ``vardoger analyze --platform copilot`` can write a fenced
    ``<!-- vardoger:start --> ... <!-- vardoger:end -->`` block without
    clobbering user-authored instructions.
    """
    instructions_path = Path.home() / ".copilot" / "copilot-instructions.md"
    instructions_path.parent.mkdir(parents=True, exist_ok=True)

    if not instructions_path.is_file():
        instructions_path.write_text(
            "# Copilot CLI instructions\n\n"
            "This file is read by GitHub Copilot CLI. vardoger will manage a\n"
            "fenced section below marked by `<!-- vardoger:start -->` and\n"
            "`<!-- vardoger:end -->`. Everything outside that section is\n"
            "yours to edit.\n",
            encoding="utf-8",
        )

    print(f"Prepared Copilot instructions at {instructions_path}")
    print("Run `vardoger analyze --platform copilot` to generate a personalization.")
    print()
    print("Optional: install the analyze skill as a Copilot CLI plugin so you can")
    print("invoke it from inside Copilot.")
    print("  copilot plugin marketplace add dstrupl/vardoger:plugins/copilot")
    print("  copilot plugin install vardoger@vardoger")
    print()
    _print_getting_started()


def setup_windsurf() -> None:
    """Prepare Windsurf rules directories for vardoger output.

    Windsurf has no plugin registry. This command ensures both the global
    memories directory and the project ``.windsurf/rules`` directory exist so
    the writer can drop files in without surprising the user on first run.
    """
    global_dir = Path.home() / ".codeium" / "windsurf" / "memories"
    global_dir.mkdir(parents=True, exist_ok=True)

    rules_path = global_dir / "global_rules.md"
    if not rules_path.is_file():
        rules_path.write_text(
            "# Windsurf global rules\n\n"
            "This file is read by Windsurf cascade. vardoger will manage a\n"
            "fenced section below marked by `<!-- vardoger:start -->` and\n"
            "`<!-- vardoger:end -->`. Everything outside that section is\n"
            "yours to edit.\n",
            encoding="utf-8",
        )

    print(f"Prepared Windsurf global rules at {rules_path}")
    print("Run `vardoger analyze --platform windsurf` to generate a personalization.")
    print()
    _print_getting_started()


def setup_cline() -> None:
    """Prepare Cline rules path for vardoger output.

    Cline has no global rules path and no plugin registry. This command just
    prints guidance; the writer creates ``.clinerules`` on first analyze.
    """
    print("Cline uses project-local rules only.")
    print("Run `vardoger analyze --platform cline --scope project --project .`")
    print("inside a project directory to generate a personalization.")
    print("The writer will create ``.clinerules`` (or ``.clinerules/vardoger.md``")
    print("if a ``.clinerules/`` directory already exists).")
    print()
    _print_getting_started()


def _print_getting_started() -> None:
    print('Getting started: say "personalize my assistant" to your AI assistant.')
