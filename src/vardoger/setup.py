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

CLAUDE_PLUGIN_MANIFEST = ClaudePluginManifest(
    name="vardoger",
    description=(
        "Personalizes your AI assistant by analyzing conversation "
        "history and generating tailored rules"
    ),
    author=PluginAuthor(name="dstrupl"),
)

CODEX_PLUGIN_MANIFEST = CodexPluginManifest(
    name="vardoger",
    version="0.1.0",
    description=(
        "Personalizes your AI assistant by analyzing conversation "
        "history and generating tailored instructions"
    ),
    author=PluginAuthor(name="dstrupl"),
    homepage="https://github.com/dstrupl/vardoger",
    repository="https://github.com/dstrupl/vardoger",
    license="Apache-2.0",
    keywords=["personalization", "productivity", "assistant"],
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


def _write_skill(plugin_dir: Path, platform: str) -> None:
    """Write the SKILL.md file for a CLI-based platform."""
    skill_dir = plugin_dir / "skills" / "analyze"
    skill_dir.mkdir(parents=True, exist_ok=True)

    platform_labels = {
        "claude-code": ("Claude Code", "rules"),
        "codex": ("Codex", "instructions"),
        "openclaw": ("OpenClaw", "instructions"),
    }
    label, artifact = platform_labels.get(platform, (platform, "instructions"))

    if platform == "claude-code":
        title = f"Analyze conversation history and generate personalized {artifact}"
        desc = (
            f"Use this skill to read your {label} conversation history, "
            "extract behavioral patterns, and generate a personalized rule "
            "file that helps the assistant better understand your preferences "
            "and working style."
        )
    else:
        title = f"Analyze conversation history and generate personalized {artifact}"
        desc = (
            f"Use this skill to read your {label} conversation history, "
            "extract behavioral patterns, and generate personalized "
            "instructions that help the assistant better understand your "
            "preferences and working style."
        )

    frontmatter_desc = (
        f"Use when the user asks to personalize their assistant, to use vardoger, "
        f"or to analyze their {label} conversation history. Runs the vardoger CLI "
        f"to read past conversations and generate tailored {artifact}."
    )

    skill = f"""\
---
name: analyze
description: "{frontmatter_desc}"
---

# {title}

{desc}

## How it works

vardoger prepares your conversation history in batches. You (the assistant) \
summarize each batch for behavioral signals, then synthesize all summaries \
into a personalization. vardoger writes the result.

## Sandbox note (read before running any command)

vardoger reads and writes files **outside** the current workspace:

- Reads conversation history from the platform's session directory \
(e.g. `~/.codex/sessions/`, `~/.claude/projects/`, etc.).
- Writes a checkpoint state file to `~/.vardoger/state.json` (created on \
first run).
- Writes the final personalization to the platform's rules file \
(e.g. `~/.codex/AGENTS.md`, `~/.claude/rules/vardoger.md`).

When the host asks to approve a `vardoger` command, approve it with \
write access beyond the workspace. Otherwise the first `vardoger prepare` \
call will fail with `PermissionError: ... ~/.vardoger/state.tmp` because \
the sandbox blocks writes outside the current working directory.

## Steps

### 1. Verify vardoger is installed

```bash
if ! command -v vardoger >/dev/null 2>&1; then
  cat <<'INSTALL_EOF'
vardoger CLI is not installed.

This skill calls the vardoger CLI to read your conversation history and
write a personalization file, so the CLI must be on PATH.

Install options:

  # Recommended while vardoger is in beta (pre-1.0):
  pipx install --pip-args="--pre" vardoger

  # Once vardoger reaches 1.0, the --pip-args flag is not needed:
  pipx install vardoger

  # Or run without installing:
  uvx vardoger --help

If you do not have pipx, see https://pipx.pypa.io/stable/installation/.

Project page: https://github.com/dstrupl/vardoger

After installing, re-run the personalization request.
INSTALL_EOF
  exit 1
fi
```

### 2. Get batch metadata

```bash
vardoger prepare --platform {platform}
```

This prints JSON like `{{"batches": 3, "total_conversations": 29}}`. Note the \
number of batches. Tell the user: "Found N conversations in M batches. Analyzing..."

### 3. Summarize each batch

For each batch number from 1 to N, run:

```bash
vardoger prepare --platform {platform} --batch 1
```

The output contains a summarization prompt and conversation data. Read the \
output carefully and produce a concise bullet-point summary of the behavioral \
signals you observe in that batch. Keep your summary for later.

Tell the user which batch you are processing: "Analyzing batch 1 of N..."

Repeat for all batches (--batch 2, --batch 3, etc.).

### 4. Get the synthesis prompt

```bash
vardoger prepare --platform {platform} --synthesize
```

### 5. Synthesize the personalization

Following the synthesis prompt, combine all your batch summaries into a \
single personalization. The output should be clean markdown with actionable \
instructions for an AI assistant.

### 6. Write the result

Pipe your personalization to vardoger:

```bash
echo "YOUR_PERSONALIZATION_HERE" | vardoger write --platform {platform} --scope global
```

Replace `YOUR_PERSONALIZATION_HERE` with the actual personalization markdown \
you generated.

### 7. Report to the user

Tell the user what was written and where. Mention they can ask you to re-run \
vardoger any time to update the personalization.

## When to use

- When the user asks to personalize their assistant
- When the user asks to analyze their conversation history
- When the user mentions "vardoger"
"""
    (skill_dir / "SKILL.md").write_text(skill, encoding="utf-8")


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
        CLAUDE_PLUGIN_MANIFEST.model_dump_json(indent=2) + "\n", encoding="utf-8"
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


def _print_getting_started() -> None:
    print('Getting started: say "personalize my assistant" to your AI assistant.')
