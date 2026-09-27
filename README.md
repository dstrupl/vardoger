# vardoger

A cross-platform plugin for AI coding assistants (Cursor, Claude Code, OpenAI Codex, OpenClaw, GitHub Copilot CLI, Devin Local, legacy Windsurf, and Cline) that reads supported local conversation-history formats, extracts behavioral patterns, and generates personalized system prompt additions — making the assistant progressively better suited to how you work. Current format limitations are called out per platform below rather than silently reading undocumented stores.

History discovery, parsing, checkpoints, and generated rules stay on your
machine. Analysis is performed by the host assistant you invoke, so selected
conversation excerpts follow that assistant and model provider's data policy.
Vardoger operates no backend and sends no telemetry.

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
vardoger setup cursor        # or claude-code, codex, openclaw, copilot, devin, windsurf, cline
```

Then tell your assistant: **"Personalize my assistant."**

> Looking for the in-app plugin listings? Track review status for each
> marketplace (PyPI, Cursor, Claude Code, Codex, Copilot CLI, Devin Desktop,
> Cline,
> ClawHub) in [`MARKETPLACE_STATUS.md`](./MARKETPLACE_STATUS.md).
> Vardoger is currently live on PyPI, the Claude Code community catalog,
> self-hosted Codex and Copilot marketplaces, McpMux, and the Official MCP
> Registry. The former Cursor listing is currently unavailable. ClawHub has
> regressed to 0.3.1 and is intentionally frozen because its mandatory MIT-0
> terms conflict with this Apache-2.0 project. Current OpenClaw history has a
> live-accepted, opt-in full-read Gateway CLI path through the direct install.

> **Previous pre-releases.** `pipx install vardoger` now resolves to the stable
> `0.4.0` release. The beta install paths below stay here for anyone still pinning
> an earlier release; new installs should not need them.
>
> ```bash
> # opt into future pre-releases (0.2.0bN, etc.):
> pipx install --pip-args="--pre" vardoger
> # or pin an older pre-release:
> pipx install vardoger==0.1.0b3
> # or run without installing:
> uvx vardoger --help
> ```

## CLI Commands

| Command | Purpose |
|---|---|
| `vardoger setup <platform>` | Register vardoger with a platform (`cursor`, `claude-code`, `codex`, `openclaw`, `copilot`, `devin`, `windsurf`, `cline`). |
| `vardoger status [--platform X] [--json]` | Report whether each personalization is fresh or stale. |
| `vardoger prepare --platform X [--batch N] [--synthesize]` | Produce the batched prompts used by the AI-driven skill pipeline. |
| `vardoger write --platform X` | Read synthesized personalization from stdin and write it to the platform's rules file (supports YAML-frontmatter confidence metadata). |
| `vardoger feedback accept\|reject --platform X [--reason TEXT]` | Record whether you kept or rejected the last generation. `reject` auto-reverts to the prior generation. |
| `vardoger compare --platform X \| --all [--window DAYS] [--json]` | Compare heuristic conversation-quality metrics before vs. after the latest personalization. |
| `vardoger profile sources [--platform X] [--json]` | List saved generations and their stable one-based selection IDs. |
| `vardoger profile preview --source X:N [--source Y:latest]` | Compile explicitly selected generations into a normalized cross-host profile and show the portable `AGENTS.md` diff without writing. |
| `vardoger profile write --source X:N --target ./AGENTS.md [--apply]` | Show the same diff; update only Vardoger's fenced block when the user explicitly adds `--apply`. |

## How It Works

1. **Read** — Parses supported conversation files already stored on disk, including opted-in Devin ATIF exports
2. **Analyze** — The host AI model identifies patterns in your communication style, tech stack, workflow, and preferences
3. **Generate** — Produces a system prompt addition tailored to you
4. **Deliver** — Writes the addition to the platform's native config (`.cursor/rules/`, `.claude/rules/`, `AGENTS.md`, etc.)

> **First run vs. incremental runs.** By default vardoger does not apply a
> time window — the first run reads your full local history (that is when the
> signal is richest and a windowed default would silently drop older sessions
> you never get a second chance to feed in). After that, a per-conversation
> checkpoint store at `~/.vardoger/state.json` ensures every subsequent run
> only reprocesses new or changed conversations, so refreshes stay fast.
> If you have very large local history and want to cap the first-run cost,
> pass `--since DAYS` (e.g. `vardoger prepare --platform cursor --since 90`);
> use `--full` to force a full re-crawl that bypasses the checkpoint.

### Cross-host profile compiler

The profile compiler combines only existing Vardoger generations that you
select; it does not silently reopen raw transcripts. Generation indexes are
one-based, while `latest` resolves to the newest saved generation for that
platform:

```bash
# Discover the reviewed generations available for selection.
vardoger profile sources

# Read-only: render the profile, audit summary, and exact AGENTS.md diff.
vardoger profile preview \
  --source claude-code:latest \
  --source codex:2 \
  --target ./AGENTS.md

# Optional controls are applied before rendering and included in the audit.
vardoger profile preview \
  --source codex:latest \
  --min-confidence medium \
  --max-age 180 \
  --redact '@example\.com' \
  --target ./AGENTS.md

# Still preview-only without --apply. This is the explicit write step.
vardoger profile write \
  --source claude-code:latest \
  --source codex:2 \
  --target ./AGENTS.md \
  --apply
```

The normalized JSON audit is available with `profile preview --json`. It
records source platform, generation, output hash/path, observation time,
recency, confidence, conflicts, supersession, and exclusions. Opposing rules
such as “Prefer tabs” and “Avoid tabs” are withheld from active instructions
until reviewed. Writes preserve everything outside
`<!-- vardoger-profile:start -->` and `<!-- vardoger-profile:end -->`.

## Supported Platforms

| Platform | History Source | Prompt Delivery | Integration |
|---|---|---|---|
| **Cursor** | Agent transcript JSONL | `.cursor/rules/vardoger.mdc` | [Marketplace plugin + MCP](plugins/cursor/README.md) |
| **Claude Code** | Session JSONL | `.claude/rules/vardoger.md` | [Community/custom plugin](plugins/claude-code/README.md) |
| **OpenAI Codex** | Session rollout JSONL | `~/.codex/AGENTS.md` | [Repository marketplace plugin](plugins/codex/README.md) |
| **OpenClaw** | Legacy JSONL or opt-in full read through official Gateway CLI; private SQLite is never queried | `~/.openclaw/skills/vardoger-personalization/SKILL.md` | [Analyzer + Gateway compatibility status](plugins/openclaw/README.md) |
| **GitHub Copilot CLI** | `~/.copilot/session-state/<session-id>/events.jsonl` plus legacy flat JSONL | `~/.copilot/copilot-instructions.md` (global) or `<project>/.github/copilot-instructions.md` (project) — managed inside a `<!-- vardoger:start -->` fenced section | [Custom plugin + published skill](plugins/copilot/README.md) |
| **Devin Local** | User-enabled Devin CLI `--export` ATIF JSON under `~/.vardoger/imports/devin/` | `~/.config/devin/AGENTS.md` (global, fenced section) or `<project>/.devin/rules/vardoger.md` | [ATIF + skill + rules integration](plugins/devin/README.md) |
| **Legacy Windsurf / Cascade** | `~/.codeium/windsurf/**/*.jsonl` | `~/.codeium/windsurf/memories/global_rules.md` (global, fenced section) or `<project>/.windsurf/rules/vardoger.md` (project, dedicated file) | [Legacy Cascade skill + CLI + MCP](plugins/windsurf/README.md) |
| **Cline** | VS Code `globalStorage/.../tasks/*/api_conversation_history.json` | `~/Documents/Cline/Rules/vardoger.md` (global) or the existing `.clinerules` project layouts | [CLI + MCP](plugins/cline/README.md) |

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
.agents/plugins/       # repository-level Codex marketplace catalog
plugins/_shared/       # shared analysis/personalization skill authored once
plugins/cursor/        # Cursor MCP server config, install script
plugins/claude-code/   # Claude Code plugin manifest, skills
plugins/codex/         # Codex plugin manifest, skills
plugins/openclaw/      # OpenClaw skill
plugins/copilot/       # GitHub Copilot CLI plugin manifest, skills
plugins/devin/         # Devin Local ATIF export, skill, and rules integration
plugins/windsurf/      # Legacy Cascade install snippet and rules delivery
plugins/cline/         # Cline integration and marketplace install guidance
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

1. Bump the package, generated setup manifests, platform manifests, and registry
   metadata together; close the matching section in `CHANGELOG.md`.
2. Run the complete quality, security, plugin-validation, and build checks.
3. Commit and push to `main`, then wait for all required checks.
4. Create an annotated `vX.Y.Z` tag and publish the matching
   [GitHub release](https://github.com/dstrupl/vardoger/releases).

The `publish.yml` workflow builds the package and uploads it to PyPI via [trusted publishers](https://docs.pypi.org/trusted-publishers/) (no API tokens needed). Once complete, `pipx install vardoger` will pull the new version.

## Status

Public beta. Version `0.4.0` is published on PyPI and tagged on GitHub; this
source tree tracks that released version.
See [`MARKETPLACE_STATUS.md`](./MARKETPLACE_STATUS.md) for live listings and
the remaining official-directory submissions.
See [`MANUAL_SUBMISSION_RUNBOOK.md`](./MANUAL_SUBMISSION_RUNBOOK.md) for the
owner-only submission, review, and publication steps.
See [PRD.md](PRD.md) for the full product requirements document.

## Privacy and security

- [PRIVACY.md](PRIVACY.md) — what vardoger reads, writes, and (importantly) does not send anywhere.
- [SECURITY.md](SECURITY.md) — how to report a vulnerability privately.

## License

Licensed under the [Apache License, Version 2.0](LICENSE).
See also the public [Privacy Policy](PRIVACY.md) and [Terms of Use](TERMS.md).

<!-- mcp-name: io.github.dstrupl/vardoger -->
