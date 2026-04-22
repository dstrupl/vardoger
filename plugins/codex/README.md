# vardoger — Codex Plugin

A Codex plugin that analyzes your conversation history and generates personalized instructions.

## Prerequisites

- **Python 3.11+** and **pipx** — see [installation instructions](../../README.md#prerequisites) in the main README
- **OpenAI Codex CLI** — [github.com/openai/codex](https://github.com/openai/codex)

## Install

Two paths are supported. Pick one.

### Option A — Public marketplace (Codex 0.x with `marketplace add`, recommended)

If your Codex build includes the `codex marketplace add` command ([openai/codex#17087](https://github.com/openai/codex/pull/17087)), register the vardoger marketplace with one line:

```bash
codex marketplace add https://github.com/dstrupl/vardoger.git --sparse plugins/codex
pipx install vardoger   # installs the `vardoger` CLI the plugin shells out to
```

Then restart Codex, run `/plugins`, pick the **vardoger** marketplace, and install the `vardoger` plugin.

This pulls `plugins/codex/` out of the repo (containing `marketplace.json`, `.codex-plugin/plugin.json`, and the analyze skill), installs it under `$CODEX_HOME/.tmp/marketplaces/vardoger/`, and records the source in `$CODEX_HOME/config.toml`. Re-run the command or `codex marketplace update` to pull later releases.

### Option B — Local marketplace (`pipx` + `vardoger setup codex`, always works)

```bash
pipx install vardoger
vardoger setup codex
```

This creates the plugin directory at `~/.codex/plugins/vardoger/` and registers it in `~/.agents/plugins/marketplace.json`.

Then:

1. **Restart Codex** so it re-reads the marketplace file.
2. Run `/plugins`, switch the source to **Local Plugins**, and install vardoger.

> Codex resolves `source.path` relative to the parent of the `.agents/`
> directory holding `marketplace.json` — i.e. `$HOME` for the personal
> marketplace. That is why the entry points to `./.codex/plugins/vardoger`
> rather than `./vardoger`.

## Local Development Install

If you're developing vardoger from source, copy the plugin to
`~/.codex/plugins/vardoger/` and register it in `~/.agents/plugins/marketplace.json`:

```bash
mkdir -p ~/.codex/plugins
cp -R /path/to/vardoger/plugins/codex ~/.codex/plugins/vardoger
```

Then create or edit `~/.agents/plugins/marketplace.json`:

```json
{
  "name": "local",
  "interface": {
    "displayName": "Local Plugins"
  },
  "plugins": [
    {
      "name": "vardoger",
      "source": {
        "source": "local",
        "path": "./.codex/plugins/vardoger"
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
      },
      "category": "Productivity"
    }
  ]
}
```

Restart Codex and run `/plugins` to install from the local marketplace.

Make sure you have run `uv sync` ([install uv](https://docs.astral.sh/uv/getting-started/installation/)) in the vardoger repo root first so the CLI is available.

## Usage

Once installed, ask Codex to "analyze my conversation history" or use `@vardoger`.

### Where the personalization lands

- **Default — user-global scope:** writes to `~/.codex/AGENTS.md` (or appends a `<!-- vardoger -->` block to it), which Codex auto-loads on every session.
- **Opt-in — project scope:** pass `project_path="<workspace root>"` (and `scope=project`) to land `<project>/AGENTS.md`. vardoger refuses to write project-scoped instructions into a directory that doesn't look like a real project (it requires `.git`, a language manifest, `AGENTS.md`, or an existing `.cursor/` in the path or one of its ancestors). Without that check, an MCP server launched from `$HOME` would silently drop rules into a location Codex would never load. Supply a real workspace root or drop the `project_path` argument to write user-globally.

## Uninstall

Remove the entry from `~/.agents/plugins/marketplace.json` and uninstall via `/plugins`.
