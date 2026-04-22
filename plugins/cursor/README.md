# vardoger — Cursor Plugin

Exposes vardoger as an MCP server that Cursor's agent can invoke to personalize your assistant.

## Prerequisites

- **Cursor** — [cursor.com](https://www.cursor.com/)
- One of:
  - **[uv](https://docs.astral.sh/uv/getting-started/installation/)** (recommended, used by the shipped `mcp.json`) — vardoger is fetched on demand via `uvx vardoger mcp`.
  - **[pipx](https://pipx.pypa.io/stable/installation/)** — for installs that pre-stage the CLI (see the fallback below).
- **Python 3.11+** — both `uv` and `pipx` will fetch a compatible Python if one is not already installed; see the [main README prerequisites](../../README.md#prerequisites) for manual installs.

## Install from Cursor Marketplace

Once listed, install from the Cursor Marketplace panel and restart Cursor. The plugin ships a `.cursor-plugin/plugin.json` manifest plus an `mcp.json` that launches the server via `uvx` — no extra setup is needed if `uv` is on your PATH.

## Install via pipx (fallback)

If `uv` is not available, run the classic setup once:

```bash
pipx install vardoger
vardoger setup cursor
```

This registers the vardoger MCP server in `~/.cursor/mcp.json` using the pipx-resolved Python interpreter. Restart Cursor to activate.

## Local Development Install

Point Cursor at this directory as a local plugin:

```bash
ln -s "$(pwd)/plugins/cursor" ~/.cursor/plugins/local/vardoger
```

Reload Cursor (Developer: Reload Window). The plugin's `mcp.json` runs `uvx vardoger mcp`; if you want to test against an in-tree build, swap the command to your local `.venv/bin/vardoger mcp` while iterating.

## Usage

Ask the Cursor agent:

- "Personalize my assistant"
- "Run vardoger"
- "Analyze my conversation history"

The agent will call the `vardoger_personalize` tool, which returns step-by-step orchestration instructions. The agent then follows them automatically — preparing batches, summarizing, synthesizing, and delivering the result.

### Where the personalization lands

vardoger analyses your *global* Cursor conversation history, so the output it produces is user-level (applies to every workspace), not project-level. Delivery defaults reflect that:

- **Default — User Rules (copy-paste):** The agent surfaces a ready-to-paste block. You paste it into **Cursor Settings → Rules → User Rules** once; it then applies across every project. Edit the block freely — the bullets are starting points derived from patterns in your chat history, not commandments.
- **Opt-in — project-scoped file:** Ask the agent "also drop this into my current workspace" and it will call `vardoger_write` with `project_path=<your workspace root>`. vardoger writes `<project>/.cursor/rules/vardoger.md` *only* if that directory (or one of its ancestors) looks like a real project (contains `.git`, a language manifest, `AGENTS.md`, or an existing `.cursor/`). If it doesn't, the write is refused with an actionable error — vardoger will not silently drop a rules file into `$HOME` or any other non-project location.

### Reusing a personalization from another workspace

If you've already curated a `vardoger.md` in another Cursor workspace, tell the agent: "you can also check workspace X and workspace Y." The agent calls `vardoger_import` with those paths; vardoger returns any `vardoger.md` it finds so the agent can offer to reuse, merge, or ignore it before running a fresh analysis.

## Uninstall

Uninstall from the Cursor Marketplace panel (or remove the `"vardoger"` key from `~/.cursor/mcp.json` if installed via `vardoger setup cursor`).
