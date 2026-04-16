# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Platform setup for vardoger.

Handles post-install registration for each supported platform:
  - Cursor: registers MCP server in ~/.cursor/mcp.json
  - Claude Code: creates plugin directory and prints activation command
  - Codex: creates plugin directory and registers in marketplace.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CLAUDE_PLUGIN_JSON = {
    "name": "vardoger",
    "description": (
        "Personalizes your AI assistant by analyzing conversation "
        "history and generating tailored rules"
    ),
    "author": {"name": "dstrupl"},
}

CODEX_PLUGIN_JSON = {
    "name": "vardoger",
    "version": "0.1.0",
    "description": (
        "Personalizes your AI assistant by analyzing conversation "
        "history and generating tailored instructions"
    ),
    "author": {"name": "dstrupl"},
    "skills": "./skills/",
}


def _vardoger_plugin_dir() -> Path:
    return Path.home() / ".vardoger" / "plugins"


def _write_skill(plugin_dir: Path, platform: str) -> None:
    """Write the SKILL.md file for a CLI-based platform."""
    skill_dir = plugin_dir / "skills" / "analyze"
    skill_dir.mkdir(parents=True, exist_ok=True)

    if platform == "claude-code":
        title = "Analyze conversation history and generate personalized rules"
        desc = (
            "Use this skill to read your Claude Code conversation history, "
            "extract behavioral patterns, and generate a personalized rule "
            "file that helps the assistant better understand your preferences "
            "and working style."
        )
    else:
        title = "Analyze conversation history and generate personalized instructions"
        desc = (
            "Use this skill to read your Codex conversation history, "
            "extract behavioral patterns, and generate personalized "
            "instructions that help the assistant better understand your "
            "preferences and working style."
        )

    skill = f"""\
# {title}

{desc}

## How it works

vardoger prepares your conversation history in batches. You (the assistant) \
summarize each batch for behavioral signals, then synthesize all summaries \
into a personalization. vardoger writes the result.

## Steps

### 1. Verify vardoger is installed

```bash
command -v vardoger >/dev/null 2>&1 || \
  {{ echo "vardoger not found. Install with: pipx install vardoger"; exit 1; }}
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
    mcp_config = Path.home() / ".cursor" / "mcp.json"
    mcp_config.parent.mkdir(parents=True, exist_ok=True)

    config = json.loads(mcp_config.read_text(encoding="utf-8")) if mcp_config.is_file() else {}

    servers = config.setdefault("mcpServers", {})
    servers["vardoger"] = {
        "command": sys.executable,
        "args": ["-m", "vardoger.mcp_server"],
    }

    mcp_config.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    print(f"Registered vardoger MCP server in {mcp_config}")
    print("Restart Cursor to activate.")
    print()
    _print_getting_started()


def setup_claude_code() -> None:
    """Create the Claude Code plugin directory and print activation command."""
    plugin_dir = _vardoger_plugin_dir() / "claude-code"

    manifest_dir = plugin_dir / ".claude-plugin"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "plugin.json").write_text(
        json.dumps(CLAUDE_PLUGIN_JSON, indent=2) + "\n", encoding="utf-8"
    )

    _write_skill(plugin_dir, "claude-code")

    print(f"Created Claude Code plugin at {plugin_dir}")
    print()
    print("Activate by starting Claude Code with:")
    print(f"  claude --plugin-dir {plugin_dir}")
    print()
    _print_getting_started()


def setup_codex() -> None:
    """Create the Codex plugin directory and register in marketplace.json."""
    plugin_dir = _vardoger_plugin_dir() / "codex"

    manifest_dir = plugin_dir / ".codex-plugin"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "plugin.json").write_text(
        json.dumps(CODEX_PLUGIN_JSON, indent=2) + "\n", encoding="utf-8"
    )

    _write_skill(plugin_dir, "codex")

    marketplace_path = Path.home() / ".agents" / "plugins" / "marketplace.json"
    marketplace_path.parent.mkdir(parents=True, exist_ok=True)

    if marketplace_path.is_file():
        marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
    else:
        marketplace = {"name": "local", "plugins": []}

    plugins = marketplace.setdefault("plugins", [])
    existing = [p for p in plugins if p.get("name") != "vardoger"]
    existing.append(
        {
            "name": "vardoger",
            "source": {"source": "local", "path": str(plugin_dir)},
        }
    )
    marketplace["plugins"] = existing

    marketplace_path.write_text(json.dumps(marketplace, indent=2) + "\n", encoding="utf-8")

    print(f"Created Codex plugin at {plugin_dir}")
    print(f"Registered in {marketplace_path}")
    print("Open Codex and run /plugins to activate.")
    print()
    _print_getting_started()


def _print_getting_started() -> None:
    print('Getting started: say "personalize my assistant" to your AI assistant.')
