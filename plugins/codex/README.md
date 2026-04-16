# vardoger — Codex Plugin

A Codex plugin that analyzes your conversation history and generates personalized instructions.

## Prerequisites

- **Python 3.11+** — [python.org/downloads](https://www.python.org/downloads/)
- **pipx** — [pipx.pypa.io/stable/installation](https://pipx.pypa.io/stable/installation/)
- **OpenAI Codex CLI** — [github.com/openai/codex](https://github.com/openai/codex)

## Install

```bash
pipx install vardoger
vardoger setup codex
```

This creates the plugin directory at `~/.vardoger/plugins/codex/` and registers it in `~/.agents/plugins/marketplace.json`. Open Codex and run `/plugins` to activate.

## Local Development Install

If you're developing vardoger from source, create or edit `~/.agents/plugins/marketplace.json` manually:

```json
{
  "name": "local-dev",
  "plugins": [
    {
      "name": "vardoger",
      "source": {
        "source": "local",
        "path": "/path/to/vardoger/plugins/codex"
      }
    }
  ]
}
```

Then open Codex and run `/plugins` to install from the local marketplace.

Make sure you have run `uv sync` ([install uv](https://docs.astral.sh/uv/getting-started/installation/)) in the vardoger repo root first so the CLI is available.

## Usage

Once installed, ask Codex to "analyze my conversation history" or use `@vardoger`.

## Uninstall

Remove the entry from `~/.agents/plugins/marketplace.json` and uninstall via `/plugins`.
