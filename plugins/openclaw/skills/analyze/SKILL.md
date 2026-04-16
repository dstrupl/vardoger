# Analyze conversation history and generate personalized instructions

Use this skill to read your OpenClaw conversation history, extract behavioral patterns, and generate personalized instructions that help the assistant better understand your preferences and working style.

## How it works

vardoger prepares your conversation history in batches. You (the assistant) summarize each batch for behavioral signals, then synthesize all summaries into a personalization. vardoger writes the result.

## Steps

### 1. Verify vardoger is installed

```bash
command -v vardoger >/dev/null 2>&1 || { echo "vardoger not found. Install with: pipx install vardoger"; exit 1; }
```

### 2. Check if a refresh is needed

```bash
vardoger status --platform openclaw --json
```

If the output shows `"is_stale": false`, tell the user their personalization is up to date and ask if they want to re-run anyway. If stale or never generated, continue with the analysis.

### 3. Get batch metadata

```bash
vardoger prepare --platform openclaw
```

This prints JSON like `{"batches": 3, "total_conversations": 29}`. Note the number of batches. Tell the user: "Found N conversations in M batches. Analyzing..."

### 4. Summarize each batch

For each batch number from 1 to N, run:

```bash
vardoger prepare --platform openclaw --batch 1
```

The output contains a summarization prompt and conversation data. Read the output carefully and produce a concise bullet-point summary of the behavioral signals you observe in that batch. Keep your summary for later.

Tell the user which batch you are processing: "Analyzing batch 1 of N..."

Repeat for all batches (--batch 2, --batch 3, etc.).

### 5. Get the synthesis prompt

```bash
vardoger prepare --platform openclaw --synthesize
```

### 6. Synthesize the personalization

Following the synthesis prompt, combine all your batch summaries into a single personalization. The output should be clean markdown with actionable instructions for an AI assistant.

### 7. Write the result

Pipe your personalization to vardoger:

```bash
echo "YOUR_PERSONALIZATION_HERE" | vardoger write --platform openclaw --scope global
```

Replace `YOUR_PERSONALIZATION_HERE` with the actual personalization markdown you generated.

### 8. Report to the user

Tell the user what was written and where. Mention they can ask you to re-run vardoger any time to update the personalization.

## When to use

- When the user asks to personalize their assistant
- When the user asks to analyze their conversation history
- When the user mentions "vardoger"
