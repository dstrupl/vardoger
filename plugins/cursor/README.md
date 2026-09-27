# vardoger — Cursor Plugin

Exposes vardoger as an MCP server that Cursor's agent can invoke to personalize your assistant.

## Prerequisites

- **Cursor** — [cursor.com](https://www.cursor.com/)
- One of:
  - **[uv](https://docs.astral.sh/uv/getting-started/installation/)** (recommended, used by the shipped `mcp.json`) — vardoger is fetched on demand via `uvx vardoger mcp`.
  - **[pipx](https://pipx.pypa.io/stable/installation/)** — for installs that pre-stage the CLI (see the fallback below).
- **Python 3.11+** — both `uv` and `pipx` will fetch a compatible Python if one is not already installed; see the [main README prerequisites](../../README.md#prerequisites) for manual installs.

## Cursor Marketplace status

The former [Vardoger marketplace route](https://cursor.com/marketplace/vardoger)
currently reports **Marketplace Plugin Not Found**. Until the refreshed package
is re-submitted and visible again, use the direct setup or local-development
path below.

The source package is ready for that re-submission: it includes an Agent
Plugins 1.0 root [`plugin.json`](./plugin.json) and a schema-valid
[`mcp.json`](./mcp.json) with an explicit `stdio` transport. The existing
`.cursor-plugin/plugin.json` remains available for legacy Cursor installs.
The locally validated listing copy and remaining owner gates are in the
[marketplace recovery package](./submission/README.md).

## Install via pipx (fallback)

If `uv` is not available, run the classic setup once:

```bash
pipx install vardoger
vardoger setup cursor
```

This registers the vardoger MCP server in `~/.cursor/mcp.json` using the pipx-resolved Python interpreter. Restart Cursor to activate.

## Local development install

Cursor only follows local-plugin symlinks when their targets also resolve
inside `~/.cursor/plugins/local`, so copy the package there from the repository
root rather than linking back to the checkout:

```bash
mkdir -p ~/.cursor/plugins/local
cp -R plugins/cursor ~/.cursor/plugins/local/vardoger
```

Start with no existing `~/.cursor/plugins/local/vardoger` directory; if one is
already present, preserve or remove it deliberately before copying. Reload
Cursor (**Developer: Reload Window**). The plugin's `mcp.json` runs
`uvx vardoger mcp`; to test an in-tree build, edit only the copied package and
point its command at the checkout's absolute `.venv/bin/vardoger` path.

## Usage

Ask the Cursor agent:

- "Personalize my assistant"
- "Run vardoger"
- "Analyze my conversation history"

The agent will call the `vardoger_personalize` tool, which returns step-by-step orchestration instructions. The agent then follows them automatically — preparing batches, summarizing, synthesizing, and delivering the result.

### Where the personalization lands

vardoger analyses your *global* Cursor conversation history, so the output it produces is user-level (applies to every workspace), not project-level. Delivery defaults reflect that:

Cursor's [current rules contract](https://cursor.com/docs/rules) requires
project rules to use the `.mdc` extension and YAML frontmatter; plain `.md`
files in `.cursor/rules/` are ignored.

- **Default — User Rules (copy-paste):** `vardoger_write` saves the rendered block to a convenience copy-source file at `~/.vardoger/cursor-user-rules.md` and prints that absolute path at the top of its response. Cmd+click the path in Cursor's chat to open the file in an editor tab, then copy the whole file into **Cursor Settings → Rules → User Rules**. Pasting there is what actually activates the rules — Cursor's User Rules live in its settings database, not on disk, so the copy-source file is just there so you don't have to dig for the block inside a collapsed tool-call card. Re-running `vardoger_write` overwrites that file with the latest generation; rejecting via `vardoger_feedback` reject either rewrites it with the previous generation or deletes it. Edit the block freely once pasted — the bullets are starting points derived from patterns in your chat history, not commandments.
- **Opt-in — project-scoped file:** Ask the agent "also drop this into my current workspace" and it will call `vardoger_write` with `project_path=<your workspace root>`. vardoger writes `<project>/.cursor/rules/vardoger.mdc` with Cursor's required frontmatter *only* if that directory (or one of its ancestors) looks like a real project (contains `.git`, a language manifest, `AGENTS.md`, or an existing `.cursor/`). If it doesn't, the write is refused with an actionable error — vardoger will not silently drop a rules file into `$HOME` or any other non-project location.

### Reusing a personalization from another workspace

If you've already curated a `vardoger.mdc` in another Cursor workspace, tell the agent: "you can also check workspace X and workspace Y." The agent calls `vardoger_import` with those paths; vardoger returns the current `.mdc`, or a legacy pre-0.4.0 `vardoger.md` as a read-only fallback, so the agent can offer to reuse, merge, or ignore it before running a fresh analysis. New writes and clears affect only `vardoger.mdc`; the legacy file is preserved.

## Uninstall

If installed from a restored marketplace listing, uninstall it from Cursor's
plugin panel. If installed via `vardoger setup cursor`, remove the `"vardoger"`
key from `~/.cursor/mcp.json`.
