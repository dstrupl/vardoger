# vardoger — OpenClaw Plugin

An OpenClaw skill that analyzes your conversation history and generates personalized instructions.

## Prerequisites

- **Python 3.11+** and **pipx** — see [installation instructions](../../README.md#prerequisites) in the main README
- **OpenClaw** (Node.js 22.16+ or 24) — [github.com/OpenClaw/OpenClaw](https://github.com/OpenClaw/OpenClaw)

## Install

```bash
pipx install vardoger
vardoger setup openclaw
```

This installs the vardoger analysis skill to `~/.openclaw/skills/vardoger/`. OpenClaw discovers it automatically on the next session.

## Usage

Once loaded, ask OpenClaw to "analyze my conversation history" or "run the vardoger skill."

### Where the personalization lands

- **Default — user-global scope:** writes to `~/.openclaw/skills/vardoger-personalization/SKILL.md`, which OpenClaw auto-discovers on every session.
- **Opt-in — project scope:** pass `project_path="<workspace root>"` (and `scope=project`) to land `<project>/skills/vardoger-personalization/SKILL.md`. vardoger refuses to write project-scoped skills into a directory that doesn't look like a real project (it requires `.git`, a language manifest, `AGENTS.md`, or an existing `.cursor/` in the path or one of its ancestors). Without that check, an MCP server launched from `$HOME` would silently drop skills into a location OpenClaw would never read. Supply a real workspace root or drop the `project_path` argument to write user-globally.

## Uninstall

Remove the `~/.openclaw/skills/vardoger/` directory.
