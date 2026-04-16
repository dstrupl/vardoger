# vardoger — Claude Code Plugin

A Claude Code plugin that analyzes your conversation history and generates personalized rules.

## Prerequisites

- **Python 3.11+** — [python.org/downloads](https://www.python.org/downloads/)
- **pipx** — [pipx.pypa.io/stable/installation](https://pipx.pypa.io/stable/installation/)
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

## Uninstall

Simply stop passing `--plugin-dir` when starting Claude Code.
