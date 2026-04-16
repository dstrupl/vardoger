# vardoger

A cross-platform plugin for AI coding assistants (Cursor, Claude Code, OpenAI Codex) that reads your conversation history, extracts behavioral patterns, and generates personalized system prompt additions — making the assistant progressively better suited to how you work.

All processing happens locally. No data ever leaves your machine.

## Prerequisites

### Python 3.11+

| Platform | Command |
|---|---|
| **macOS** | `brew install python@3.13` ([install Homebrew](https://brew.sh/)) or [python.org/downloads/macos](https://www.python.org/downloads/macos/) |
| **Debian / Ubuntu** | `sudo apt install python3` |
| **Fedora** | `sudo dnf install python3` |
| **Windows** | `winget install Python.Python.3.13` or [python.org/downloads/windows](https://www.python.org/downloads/windows/) |

### pipx

Recommended for installing vardoger as an isolated CLI tool. Full instructions at [pipx.pypa.io/stable/installation](https://pipx.pypa.io/stable/installation/).

| Platform | Command |
|---|---|
| **macOS** | `brew install pipx && pipx ensurepath` |
| **Debian / Ubuntu** | `sudo apt install pipx && pipx ensurepath` |
| **Fedora** | `sudo dnf install pipx && pipx ensurepath` |
| **Windows** | `scoop install pipx` or `pip install --user pipx && pipx ensurepath` |

## Quick Start

```bash
pipx install vardoger
vardoger setup cursor        # or claude-code, or codex
```

Then tell your assistant: **"Personalize my assistant."**

## How It Works

1. **Read** — Parses conversation history already stored on disk by each platform
2. **Analyze** — The host AI model identifies patterns in your communication style, tech stack, workflow, and preferences
3. **Generate** — Produces a system prompt addition tailored to you
4. **Deliver** — Writes the addition to the platform's native config (`.cursor/rules/`, `.claude/rules/`, `AGENTS.md`, etc.)

## Supported Platforms

| Platform | History Source | Prompt Delivery | Integration |
|---|---|---|---|
| **Cursor** | Agent transcript JSONL | `.cursor/rules/vardoger.md` | MCP server |
| **Claude Code** | Session JSONL | `.claude/rules/vardoger.md` | Plugin with skill |
| **OpenAI Codex** | Session rollout JSONL | `~/.codex/AGENTS.md` | Plugin with skill |

## Development

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python package manager):

```bash
git clone https://github.com/dstrupl/vardoger.git
cd vardoger
uv sync
.venv/bin/vardoger --help
```

### Project Layout

```
src/vardoger/          # shared core — history reading, analysis, prompt generation
plugins/cursor/        # Cursor MCP server config, install script
plugins/claude-code/   # Claude Code plugin manifest, skills
plugins/codex/         # Codex plugin manifest, skills
tests/                 # all tests, mirroring src/ structure
```

- Platform-agnostic logic lives under `src/vardoger/`.
- Platform-specific integration (manifests, skills, install scripts) lives under `plugins/<platform>/`.
- Tests live in `tests/`, mirroring the source tree.

See [AGENTS.md](AGENTS.md) for full coding standards and quality checks.

## Status

Early development. See [PRD.md](PRD.md) for the full product requirements document.

## License

Licensed under the [Apache License, Version 2.0](LICENSE).
