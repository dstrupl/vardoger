# vardoger — Claude Code Plugin

A Claude Code plugin that analyzes your conversation history and generates personalized rules.

## Prerequisites

- **Python 3.11+** and **pipx** — see [installation instructions](../../README.md#prerequisites) in the main README
- **Claude Code CLI** (`claude`) — [docs.anthropic.com/en/docs/claude-code](https://docs.anthropic.com/en/docs/claude-code/overview)

## Install

```bash
pipx install vardoger
vardoger setup claude-code
```

This creates the plugin directory at `~/.vardoger/plugins/claude-code/` and prints the activation command.

## Local Development Install

If you're developing vardoger from source, you can point Claude Code at the repo's plugin directory instead:

```bash
claude --plugin-dir /path/to/vardoger/plugins/claude-code
```

Make sure you have run `uv sync` ([install uv](https://docs.astral.sh/uv/getting-started/installation/)) in the vardoger repo root first so the CLI is available.

## Usage

Once loaded, ask Claude Code to "analyze my conversation history" or "run the vardoger skill."

### Where the personalization lands

- **Default — user-global scope:** writes to `~/.claude/rules/vardoger.md`, which Claude Code auto-loads on every session.
- **Opt-in — project scope:** pass `project_path="<workspace root>"` (and `scope=project`) to land `<project>/.claude/rules/vardoger.md`. vardoger refuses to write project-scoped rules into a directory that doesn't look like a real project (it requires `.git`, a language manifest, `AGENTS.md`, or an existing `.cursor/` in the path or one of its ancestors). This is intentional — without the check, an MCP server launched from `$HOME` would silently drop rules in a location Claude Code would never load. Supply a real workspace root or drop the `project_path` argument to write user-globally.

## Uninstall

Simply stop passing `--plugin-dir` when starting Claude Code.
