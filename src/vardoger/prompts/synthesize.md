# Synthesize Personalization

You have summarized behavioral signals from multiple batches of a developer's conversation history. Now combine all batch summaries into a single, coherent personalization that will be added to the AI coding assistant's system prompt.

## Instructions

1. **Merge** signals across all batch summaries. Combine related observations.
2. **Deduplicate** — if the same signal appears in multiple batches, that strengthens it but should appear only once.
3. **Resolve contradictions** — if batches show conflicting behavior, prefer the more recent or more frequent pattern. Note the contradiction only if it seems genuinely context-dependent.
4. **Be concrete** — write instructions the assistant can act on, not vague descriptions.
5. **Be concise** — each instruction should be one or two sentences.

## Output Format

Write the personalization as markdown. Use second person addressing the assistant ("The user prefers...", "When the user asks for..."). Organize by category. The output will be placed directly into a rules file, so it must be self-contained and actionable.

```markdown
# Personalization

## Communication
- [instruction for the assistant]

## Technical Stack
- [instruction for the assistant]

## Workflow
- [instruction for the assistant]

## Coding Style
- [instruction for the assistant]

## Things to Avoid
- [instruction for the assistant]
```

Only include categories where you have clear evidence. Omit empty categories. Do not include the surrounding code fence — output raw markdown.
