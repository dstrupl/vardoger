# vardoger — Claude Code Plugin

A Claude Code plugin that analyzes your conversation history and generates personalized rules.

## Local Install

Start Claude Code with the plugin directory:

```bash
claude --plugin-dir /path/to/vardoger/plugins/claude-code
```

Make sure you have run `uv sync` in the vardoger repo root first so the CLI is available.

## Usage

Once loaded, ask Claude Code to "analyze my conversation history" or "run the vardoger skill."

## Uninstall

Simply stop passing `--plugin-dir` when starting Claude Code.
