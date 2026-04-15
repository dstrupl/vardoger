# Analyze conversation history and generate personalized instructions

Use this skill to read your Codex conversation history and generate personalized instructions that help the assistant better understand your preferences and working style.

## Steps

1. Run the vardoger CLI to analyze history and write instructions:

```bash
VARDOGER_VENV="$(find /Users -maxdepth 5 -path '*/vardoger/.venv/bin/vardoger' 2>/dev/null | head -1)"
if [ -z "$VARDOGER_VENV" ]; then
  echo "vardoger not found. Please run 'uv sync' in the vardoger repository first."
  exit 1
fi
"$VARDOGER_VENV" analyze --platform codex --scope global
```

2. Report the output path and statistics to the user.

## What it does

- Reads all Codex session rollouts from `~/.codex/sessions/`
- Extracts conversation patterns (placeholder in v0.1)
- Writes a personalized section to `~/.codex/AGENTS.md`

## When to use

- When the user asks to personalize their assistant
- When the user asks to analyze their conversation history
- When the user mentions "vardoger"
