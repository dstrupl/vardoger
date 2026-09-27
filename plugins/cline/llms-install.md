# Install vardoger for Cline

This file is written for an AI assistant (e.g. Cline itself) running through
the current [Cline marketplace](https://github.com/cline/marketplace) install
flow. Follow these steps exactly.

## What vardoger is

vardoger is a **local-first** personalization tool. It reads local AI
assistant conversation histories (Cline, Cursor, Claude Code, Codex, Copilot
CLI, Windsurf, OpenClaw), extracts conventions and preferences, and writes a
personalization file that the assistant auto-loads. Nothing leaves the user's
machine through a Vardoger backend: Vardoger has no hosted service or
telemetry. History parsing, checkpoint state, and rule-file writes are local.
Excerpts analyzed by the active Cline model follow that model provider's data
policy.

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

The output should be `0.4.0` or newer.

If this server was installed from the current Cline marketplace, its generated
configuration runs `uvx vardoger mcp`; a separate `pipx` install is not needed.

## Step 2 — Prepare Cline rules

Run:

```bash
vardoger setup cline
```

This prepares Cline's documented user-global rules directory. The writer
creates `~/Documents/Cline/Rules/vardoger.md` when the user runs
`vardoger analyze --platform cline`. An explicit `--scope project --project
<workspace>` instead writes `.clinerules/vardoger.md` in that project.

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
default to Cline's user-global rules rather than Cursor's rules. An MCP write
with `scope="project"` and `project_path="<workspace>"` selects project-only
`.clinerules` delivery.

Use Cline's built-in MCP editor if available; do not hand-edit the JSON
file if Cline exposes an "Add server" UI that accepts the snippet above.

## Step 4 — Verify

After Cline reloads its MCP servers, ask the user:

> I've installed vardoger. Try saying "analyze my Cline history" to generate
> a user-global personalization file at
> `~/Documents/Cline/Rules/vardoger.md`, or ask for an explicit project-scoped
> rule instead.

## Uninstall

If the user wants to remove vardoger later:

```bash
pipx uninstall vardoger
```

Also remove the `"vardoger"` entry from `cline_mcp_settings.json` and delete
`~/Documents/Cline/Rules/vardoger.md`. Delete `.clinerules/vardoger.md` only
from projects where Vardoger was explicitly asked to write project-scoped
personalization.
