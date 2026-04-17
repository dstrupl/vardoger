# vardoger

A cross-platform plugin for AI coding assistants (Cursor, Claude Code, OpenAI Codex, OpenClaw) that reads your conversation history, extracts behavioral patterns, and generates personalized system prompt additions — making the assistant progressively better suited to how you work.

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
vardoger setup cursor        # or claude-code, codex, openclaw
```

Then tell your assistant: **"Personalize my assistant."**

## CLI Commands

| Command | Purpose |
|---|---|
| `vardoger setup <platform>` | Register vardoger with a platform (`cursor`, `claude-code`, `codex`, `openclaw`). |
| `vardoger status [--platform X] [--json]` | Report whether each personalization is fresh or stale. |
| `vardoger prepare --platform X [--batch N] [--synthesize]` | Produce the batched prompts used by the AI-driven skill pipeline. |
| `vardoger write --platform X` | Read synthesized personalization from stdin and write it to the platform's rules file (supports YAML-frontmatter confidence metadata). |
| `vardoger feedback accept\|reject --platform X [--reason TEXT]` | Record whether you kept or rejected the last generation. `reject` auto-reverts to the prior generation. |
| `vardoger compare --platform X \| --all [--window DAYS] [--json]` | Compare heuristic conversation-quality metrics before vs. after the latest personalization. |

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
| **OpenClaw** | Session JSONL | `~/.openclaw/skills/vardoger-personalization/SKILL.md` | Skill |

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
plugins/openclaw/      # OpenClaw skill
tests/                 # all tests, mirroring src/ structure
```

- Platform-agnostic logic lives under `src/vardoger/`.
- Platform-specific integration (manifests, skills, install scripts) lives under `plugins/<platform>/`.
- Tests live in `tests/`, mirroring the source tree.

See [AGENTS.md](AGENTS.md) for full coding standards and quality checks.

### Quality gates

CI enforces a combined quality bar on every push and pull request:

- `ruff check` / `ruff format --check` — lint (incl. complexity, pylint, return, pathlib, tryceratops rules) and formatting.
- `mypy src/` — strict type checking.
- `pytest --cov=vardoger --cov-fail-under=80` — tests across Python 3.11–3.13 with a **combined 80% coverage floor**.
- A parallel security job runs `bandit -r src/` and `pip-audit --skip-editable` to catch common code smells and dependency CVEs.

Run the full bundle locally before pushing:

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest --cov=vardoger --cov-fail-under=80
```

## Contributing

Contributions are welcome. Short version:

1. Fork `dstrupl/vardoger` on GitHub and clone your fork.
2. `uv sync` and create a topic branch.
3. Make your changes with tests and run the quality-gate one-liner above.
4. Push to your fork and open a PR against `main`.

CI (`test` on Python 3.11/3.12/3.13 plus a `security` job) will run automatically on the PR. First-time contributors may need a maintainer to click **Approve and run** before the first workflow execution.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full walkthrough and [AGENTS.md](AGENTS.md) for coding standards and commit-message conventions.

## Releasing to PyPI

CI runs automatically on every push and PR (lint, type check, tests across Python 3.11–3.13). To publish a new version:

1. Bump `version` in `pyproject.toml`
2. Commit and push to `main`
3. Go to [Releases](https://github.com/dstrupl/vardoger/releases) > **Create a new release**
4. Create a new tag matching the version (e.g. `v0.1.0`), add a title and description
5. Click **Publish release**

The `publish.yml` workflow builds the package and uploads it to PyPI via [trusted publishers](https://docs.pypi.org/trusted-publishers/) (no API tokens needed). Once complete, `pipx install vardoger` will pull the new version.

## Status

Early development. See [PRD.md](PRD.md) for the full product requirements document.

## License

Licensed under the [Apache License, Version 2.0](LICENSE).
