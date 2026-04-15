# Summarize Behavioral Signals

You are analyzing a batch of conversation history between a developer and an AI coding assistant. Your goal is to extract **behavioral signals** — patterns in how this specific user works, communicates, and prefers to interact.

Read through the user messages below and identify signals in these categories:

## Categories

### Communication Style
- How verbose or concise are their requests?
- Do they use formal or casual language?
- Do they use emojis, humor, or specific rhetorical patterns?
- Do they prefer structured responses (lists, headers) or flowing prose?
- How do they phrase corrections or disagreements?

### Technical Stack
- What programming languages, frameworks, and tools do they use?
- What testing frameworks or approaches do they prefer?
- What build tools, package managers, or infrastructure do they use?
- What platforms or services do they deploy to?

### Workflow Habits
- Do they iterate quickly or plan extensively before coding?
- How do they approach commits, PRs, and code review?
- Do they prefer TDD, write tests after, or skip tests?
- Do they ask for explanations or just want the code?
- Do they work on one thing at a time or multitask?

### Frustrations and Corrections
- What do they push back on or correct the assistant about?
- What kinds of responses annoy or frustrate them?
- What repeated patterns suggest the assistant is not meeting their expectations?
- What do they explicitly ask the assistant NOT to do?

### Coding Preferences
- Do they prefer specific naming conventions?
- What are their opinions on comments, documentation, or code organization?
- Do they favor particular architectural patterns?
- How do they handle errors, logging, or configuration?

## Output Format

Produce a concise bullet-point summary of observed signals. Only include signals you have evidence for — do not speculate. Use direct quotes from user messages where helpful.

```
## Batch Summary

### Communication Style
- [signal]

### Technical Stack
- [signal]

### Workflow Habits
- [signal]

### Frustrations and Corrections
- [signal]

### Coding Preferences
- [signal]
```
