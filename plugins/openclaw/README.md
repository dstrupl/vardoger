# vardoger — OpenClaw Plugin

An OpenClaw skill that analyzes your conversation history and generates personalized instructions.

## Prerequisites

- **Python 3.11+** and **pipx** — see [installation instructions](../../README.md#prerequisites) in the main README
- **OpenClaw** (Node.js 22.16+ or 24) — [github.com/OpenClaw/OpenClaw](https://github.com/OpenClaw/OpenClaw)

## Install

The direct setup path tracks the current PyPI release and is recommended:

```bash
pipx install vardoger
vardoger setup openclaw
```

This installs the vardoger analysis skill to `~/.openclaw/skills/vardoger/`. OpenClaw discovers it automatically on the next session.

Vardoger is also listed on
[ClawHub as `vardoger-analyze`](https://clawhub.ai/skills/vardoger-analyze).
Version `0.3.2` is live there as the `latest` tag and passed ClawHub's current
moderation scan. Install the CLI with `pipx` in either case because the skill
invokes it at runtime.

Maintainers publish future versions with the current CLI shape:

```bash
clawhub skill publish plugins/openclaw/skills/analyze \
  --slug vardoger-analyze \
  --name "vardoger — Analyze History" \
  --version X.Y.Z \
  --tags latest \
  --changelog "Describe the release"
```

## Usage

Once loaded, ask OpenClaw to "analyze my conversation history" or "run the vardoger skill."

### Where the personalization lands

- **Default — user-global scope:** writes to `~/.openclaw/skills/vardoger-personalization/SKILL.md`, which OpenClaw auto-discovers on every session.
- **Opt-in — project scope:** pass `project_path="<workspace root>"` (and `scope=project`) to land `<project>/skills/vardoger-personalization/SKILL.md`. vardoger refuses to write project-scoped skills into a directory that doesn't look like a real project (it requires `.git`, a language manifest, `AGENTS.md`, or an existing `.cursor/` in the path or one of its ancestors). Without that check, an MCP server launched from `$HOME` would silently drop skills into a location OpenClaw would never read. Supply a real workspace root or drop the `project_path` argument to write user-globally.

## Uninstall

Remove the `~/.openclaw/skills/vardoger/` directory.
