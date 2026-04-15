# Analyze conversation history and generate personalized rules

Use this skill to read your Claude Code conversation history and generate a personalized rule file that helps the assistant better understand your preferences and working style.

## Steps

1. Run the vardoger CLI to analyze history and write rules:

```bash
VARDOGER_VENV="$(find /Users -maxdepth 5 -path '*/vardoger/.venv/bin/vardoger' 2>/dev/null | head -1)"
if [ -z "$VARDOGER_VENV" ]; then
  echo "vardoger not found. Please run 'uv sync' in the vardoger repository first."
  exit 1
fi
"$VARDOGER_VENV" analyze --platform claude-code --scope global
```

2. Report the output path and statistics to the user.

## What it does

- Reads all Claude Code session transcripts from `~/.claude/projects/`
- Extracts conversation patterns (placeholder in v0.1)
- Writes a personalized rule to `~/.claude/rules/vardoger.md`

## When to use

- When the user asks to personalize their assistant
- When the user asks to analyze their conversation history
- When the user mentions "vardoger"
