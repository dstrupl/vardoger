---
name: analyze
description: "Use when the user asks to personalize their assistant, to use vardoger, or to analyze their GitHub Copilot CLI conversation history. Runs the vardoger CLI to read past conversations and generate tailored instructions."
---
# Analyze conversation history and generate personalized instructions

Use this skill to read your GitHub Copilot CLI conversation history, extract behavioral patterns, and generate personalized instructions that help the assistant better understand your preferences and working style.

## How it works

vardoger prepares your conversation history in batches. You (the assistant) summarize each batch for behavioral signals, then synthesize all summaries into a personalization. vardoger writes the result.

## Sandbox note (read before running any command)

vardoger reads and writes files **outside** the current workspace:

- Reads conversation history from the platform's session directory (e.g. `~/.codex/sessions/`, `~/.claude/projects/`, `~/.cursor/projects/`, `~/.openclaw/agents/`).
- Writes a checkpoint state file to `~/.vardoger/state.json` (created on first run).
- Writes the final personalization to the platform's rules file (e.g. `~/.codex/AGENTS.md`, `~/.claude/rules/vardoger.md`, `.cursor/rules/vardoger.md`, `~/.openclaw/skills/vardoger-personalization/SKILL.md`).

When the host asks to approve a `vardoger` command, approve it with write access beyond the workspace. Otherwise the first `vardoger prepare` call will fail with `PermissionError: ... ~/.vardoger/state.tmp` because the sandbox blocks writes outside the current working directory.

## Steps

### 1. Verify vardoger is installed

```bash
if ! command -v vardoger >/dev/null 2>&1; then
  cat <<'INSTALL_EOF'
vardoger CLI is not installed.

This skill calls the vardoger CLI to read your conversation history and
write a personalization file, so the CLI must be on PATH.

Install options:

  # Recommended:
  pipx install vardoger

  # Or run without installing:
  uvx vardoger --help

If you do not have pipx, see https://pipx.pypa.io/stable/installation/.

Project page: https://github.com/dstrupl/vardoger

After installing, re-run the personalization request.
INSTALL_EOF
  exit 1
fi
```

### 2. Check if a refresh is needed

```bash
vardoger status --platform copilot --json
```

If the output shows `"is_stale": false`, tell the user their personalization is up to date and ask if they want to re-run anyway. If stale or never generated, continue with the analysis.

### 3. Get batch metadata

```bash
vardoger prepare --platform copilot
```

This prints JSON like `{"batches": 3, "total_conversations": 29}`. Note the number of batches. Tell the user: "Found N conversations in M batches. Analyzing..."

### 4. Summarize each batch

For each batch number from 1 to N, run:

```bash
vardoger prepare --platform copilot --batch 1
```

The output contains a summarization prompt and conversation data. Read the output carefully and produce a concise bullet-point summary of the behavioral signals you observe in that batch. Keep your summary for later.

Tell the user which batch you are processing: "Analyzing batch 1 of N..."

Repeat for all batches (--batch 2, --batch 3, etc.).

### 5. Get the synthesis prompt

```bash
vardoger prepare --platform copilot --synthesize
```

### 6. Synthesize the personalization

Following the synthesis prompt, combine all your batch summaries into a single personalization. The output should be clean markdown with actionable instructions for an AI assistant.

### 7. Write the result

Pipe your personalization to vardoger:

```bash
echo "YOUR_PERSONALIZATION_HERE" | vardoger write --platform copilot --scope global
```

Replace `YOUR_PERSONALIZATION_HERE` with the actual personalization markdown you generated.

### 8. Report to the user

Tell the user what was written and where. Mention they can ask you to re-run vardoger any time to update the personalization.

## When to use

- When the user asks to personalize their assistant
- When the user asks to analyze their conversation history
- When the user mentions "vardoger"
