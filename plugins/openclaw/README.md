# vardoger — OpenClaw Plugin

An OpenClaw skill that analyzes your conversation history and generates personalized instructions.

## Prerequisites

- **Python 3.11+** and **pipx** — see [installation instructions](../../README.md#prerequisites) in the main README
- **OpenClaw** (Node.js 22.16+ or 24) — [github.com/OpenClaw/OpenClaw](https://github.com/OpenClaw/OpenClaw)

## Install

```bash
pipx install vardoger
vardoger setup openclaw
```

This installs the vardoger analysis skill to `~/.openclaw/skills/vardoger/`. OpenClaw discovers it automatically on the next session.

## Usage

Once loaded, ask OpenClaw to "analyze my conversation history" or "run the vardoger skill."

## Uninstall

Remove the `~/.openclaw/skills/vardoger/` directory.
