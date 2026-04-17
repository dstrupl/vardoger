# Synthesize Personalization

You have summarized behavioral signals from multiple batches of a developer's conversation history. Now combine all batch summaries into a single, coherent personalization that will be added to the AI coding assistant's system prompt.

## Instructions

1. **Merge** signals across all batch summaries. Combine related observations.
2. **Deduplicate** — if the same signal appears in multiple batches, that strengthens it but should appear only once.
3. **Resolve contradictions** — if batches show conflicting behavior, prefer the more recent or more frequent pattern. Note the contradiction only if it seems genuinely context-dependent.
4. **Be concrete** — write instructions the assistant can act on, not vague descriptions.
5. **Be concise** — each instruction should be one or two sentences.
6. **Score each rule's confidence** based on supporting evidence:
   - `high` — pattern appears in 3 or more batches, or with strong explicit phrasing (e.g., the user directly stated the preference)
   - `medium` — pattern appears in 2 batches, or once with strong evidence
   - `low` — single indirect signal (kept, but will be marked as tentative in the output)

## Output Format

Emit **exactly two sections** separated by a `---` line:

1. A YAML frontmatter block (delimited by `---` on top and bottom) listing every rule you emit with its confidence metadata.
2. The markdown personalization body that the assistant will actually read.

The `text` in each frontmatter entry **must exactly match** one bullet line in the body (without the leading `- `).

```markdown
---
confidence:
  - id: c1
    text: "Prefer Python with uv for package management."
    category: "Technical Stack"
    level: high
    supporting_batches: [1, 2, 3]
  - id: c2
    text: "Avoid emojis in assistant responses."
    category: "Things to Avoid"
    level: medium
    supporting_batches: [2]
---

# Personalization

## Technical Stack
- Prefer Python with uv for package management.

## Things to Avoid
- Avoid emojis in assistant responses.
```

Write the body as markdown using second person addressing the assistant ("The user prefers...", "When the user asks for..."). Organize by category. Use these categories as applicable: Communication, Technical Stack, Workflow, Coding Style, Things to Avoid. Only include categories where you have clear evidence.

Do **not** wrap your output in an extra code fence — emit the frontmatter and body directly so the contents can be written to disk as-is.
