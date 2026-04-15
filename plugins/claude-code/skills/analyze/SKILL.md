# Analyze conversation history and generate personalized rules

Use this skill to read your Claude Code conversation history, extract behavioral patterns, and generate a personalized rule file that helps the assistant better understand your preferences and working style.

## How it works

vardoger prepares your conversation history in batches. You (the assistant) summarize each batch for behavioral signals, then synthesize all summaries into a personalization. vardoger writes the result.

## Steps

### 1. Find vardoger

```bash
VARDOGER="$(find /Users -maxdepth 5 -path '*/vardoger/.venv/bin/vardoger' 2>/dev/null | head -1)"
if [ -z "$VARDOGER" ]; then
  echo "vardoger not found. Please run 'uv sync' in the vardoger repository first."
  exit 1
fi
```

### 2. Get batch metadata

```bash
"$VARDOGER" prepare --platform claude-code
```

This prints JSON like `{"batches": 3, "total_conversations": 29}`. Note the number of batches.

### 3. Summarize each batch

For each batch number from 1 to N, run:

```bash
"$VARDOGER" prepare --platform claude-code --batch 1
```

The output contains a summarization prompt and conversation data. Read the output carefully and produce a concise bullet-point summary of the behavioral signals you observe in that batch. Keep your summary for later.

Repeat for all batches (--batch 2, --batch 3, etc.).

### 4. Get the synthesis prompt

```bash
"$VARDOGER" prepare --platform claude-code --synthesize
```

### 5. Synthesize the personalization

Following the synthesis prompt, combine all your batch summaries into a single personalization. The output should be clean markdown with actionable instructions for an AI assistant.

### 6. Write the result

Pipe your personalization to vardoger:

```bash
echo "YOUR_PERSONALIZATION_HERE" | "$VARDOGER" write --platform claude-code --scope global
```

Replace `YOUR_PERSONALIZATION_HERE` with the actual personalization markdown you generated.

### 7. Report to the user

Tell the user what was written and where.

## When to use

- When the user asks to personalize their assistant
- When the user asks to analyze their conversation history
- When the user mentions "vardoger"
