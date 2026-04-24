# Install vardoger for Cline

This file is written for an AI assistant (e.g. Cline itself) running through
the [Cline MCP marketplace](https://github.com/cline/mcp-marketplace) install
flow. Follow these steps exactly.

## What vardoger is

vardoger is a **local-first** personalization tool. It reads local AI
assistant conversation histories (Cline, Cursor, Claude Code, Codex, Copilot
CLI, Windsurf, OpenClaw), extracts conventions and preferences, and writes a
personalization file that the assistant auto-loads. Nothing leaves the user's
machine: no telemetry, no uploads, no network calls.

## Prerequisites

1. Ensure Python 3.11 or newer is available on the user's machine (`python3
   --version`). If missing, install from [python.org](https://www.python.org/).
2. Ensure `pipx` is installed (`pipx --version`). If missing:
   ```bash
   python3 -m pip install --user pipx
   python3 -m pipx ensurepath
   ```
   The user may need to restart their shell after `ensurepath`.

## Step 1 — Install the vardoger CLI

Run:

```bash
pipx install vardoger
```

Verify:

```bash
vardoger --version
```

The output should be `0.3.1` or newer.

## Step 2 — Prepare Cline rules

Run:

```bash
vardoger setup cline
```

This prints guidance only; no files are written yet. The writer creates
`.clinerules/vardoger.md` inside the user's current project when the user
actually runs `vardoger analyze --platform cline --scope project`.

## Step 3 — Register the MCP server with Cline

Cline's MCP configuration lives under `cline_mcp_settings.json` in the
Cline extension's VS Code/Cursor/Windsurf storage directory. Add (or
merge) the following server entry:

```json
{
  "mcpServers": {
    "vardoger": {
      "command": "vardoger",
      "args": ["mcp"],
      "env": {
        "VARDOGER_MCP_PLATFORM": "cline"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

The `VARDOGER_MCP_PLATFORM=cline` environment variable is required — it
tells the vardoger MCP server to analyze Cline conversation history and
write personalization to `.clinerules/vardoger.md` rather than Cursor's
`.cursor/rules/vardoger.md`.

Use Cline's built-in MCP editor if available; do not hand-edit the JSON
file if Cline exposes an "Add server" UI that accepts the snippet above.

## Step 4 — Verify

After Cline reloads its MCP servers, ask the user:

> I've installed vardoger. Try saying "analyze my Cline history" to generate
> a personalization file at `.clinerules/vardoger.md` in your current project,
> or ask me to call the vardoger MCP tools directly.

## Uninstall

If the user wants to remove vardoger later:

```bash
pipx uninstall vardoger
```

Also remove the `"vardoger"` entry from `cline_mcp_settings.json` and delete
`.clinerules/vardoger.md` from any projects where it was written.
