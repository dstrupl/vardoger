# vardoger — Cursor Plugin

Exposes vardoger as an MCP server that Cursor's agent can invoke to personalize your assistant.

## Prerequisites

- **Python 3.11+** and **pipx** — see [installation instructions](../../README.md#prerequisites) in the main README
- **Cursor** — [cursor.com](https://www.cursor.com/)

## Install

```bash
pipx install vardoger
vardoger setup cursor
```

This registers the vardoger MCP server in `~/.cursor/mcp.json`. Restart Cursor to activate.

## Usage

Ask the Cursor agent:

- "Personalize my assistant"
- "Run vardoger"
- "Analyze my conversation history"

The agent will call the `vardoger_personalize` tool, which returns step-by-step orchestration instructions. The agent then follows them automatically — preparing batches, summarizing, synthesizing, and writing the result to `.cursor/rules/vardoger.md`.

## Uninstall

Remove the `"vardoger"` key from `~/.cursor/mcp.json`.
