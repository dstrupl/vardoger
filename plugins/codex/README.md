# vardoger — Codex Plugin

A Codex plugin that analyzes your conversation history and generates personalized instructions.

## Local Install

Create or edit `~/.agents/plugins/marketplace.json`:

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

Make sure you have run `uv sync` in the vardoger repo root first so the CLI is available.

## Usage

Once installed, ask Codex to "analyze my conversation history" or use `@vardoger`.

## Uninstall

Remove the entry from `~/.agents/plugins/marketplace.json` and uninstall via `/plugins`.
