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

## Install from the vardoger marketplace

vardoger also ships a self-hosted Claude Code marketplace manifest at [`.claude-plugin/marketplace.json`](../../.claude-plugin/marketplace.json) in the repo root. From inside Claude Code:

```
/plugin marketplace add dstrupl/vardoger
/plugin install vardoger@vardoger
```

The first command registers this repo as a marketplace source; the second installs the plugin from it. You still need `pipx install vardoger` on your `$PATH` so the skill's CLI is available at runtime.

## Local Development Install

If you're developing vardoger from source, you can point Claude Code at the repo's plugin directory instead:

```bash
claude --plugin-dir /path/to/vardoger/plugins/claude-code
```

Make sure you have run `uv sync` ([install uv](https://docs.astral.sh/uv/getting-started/installation/)) in the vardoger repo root first so the CLI is available.

## Relationship to Claude Code's built-in memory

Claude Code now writes per-project memory files to `~/.claude/projects/<encoded-path>/memory/` during a session. vardoger is complementary to that feature, not a replacement:

- **Memory** is captured live, in one session at a time — it reflects whatever Claude noticed in the moment.
- **vardoger** reads your full on-disk session history in batches and extracts cross-session patterns (tech-stack habits, recurring workflows, stylistic preferences) that are hard to see from any single conversation.

The two stay out of each other's way: vardoger discovers sessions via a non-recursive `*.jsonl` glob on each project directory and writes its output to `~/.claude/rules/vardoger.md` (or `<project>/.claude/rules/vardoger.md`), so it never reads from or writes to the `memory/` tree. Both files are loaded into the prompt side-by-side.

Typical reasons to keep running vardoger alongside memory:

- **Backfill** — memory only grows from the point you enabled it; vardoger mines the history that already exists on disk.
- **Cross-session aggregation** — patterns that only emerge across many conversations (not a single correction).
- **Global scope** — vardoger's default writes user-globally to `~/.claude/rules/vardoger.md`, so preferences apply across all projects. Memory is per-project.
- **Reviewable output** — one consolidated rules file you can read, edit, or diff, versus many small memory files accumulating silently.

## Usage

Once loaded, ask Claude Code to "analyze my conversation history" or "run the vardoger skill."

### Where the personalization lands

- **Default — user-global scope:** writes to `~/.claude/rules/vardoger.md`, which Claude Code auto-loads on every session.
- **Opt-in — project scope:** pass `project_path="<workspace root>"` (and `scope=project`) to land `<project>/.claude/rules/vardoger.md`. vardoger refuses to write project-scoped rules into a directory that doesn't look like a real project (it requires `.git`, a language manifest, `AGENTS.md`, or an existing `.cursor/` in the path or one of its ancestors). This is intentional — without the check, an MCP server launched from `$HOME` would silently drop rules in a location Claude Code would never load. Supply a real workspace root or drop the `project_path` argument to write user-globally.

## Uninstall

Simply stop passing `--plugin-dir` when starting Claude Code.
