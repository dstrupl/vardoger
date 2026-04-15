# vardoger — Cursor Plugin

Exposes vardoger as an MCP server that Cursor's agent can invoke.

## Local Install

```bash
bash plugins/cursor/install.sh
```

This adds a `vardoger` entry to `~/.cursor/mcp.json`. Restart Cursor to pick it up.

## Usage

Once installed, ask the Cursor agent to "run vardoger" or "analyze my conversation history." The agent will see the `vardoger_analyze` tool and invoke it.

## Uninstall

Remove the `"vardoger"` key from `~/.cursor/mcp.json`.
