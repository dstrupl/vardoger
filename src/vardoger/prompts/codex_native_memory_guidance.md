## Codex memory boundary

Codex already uses local memories to carry useful context forward, while
`AGENTS.md` is the durable instruction layer. The Vardoger result belongs only
in the instruction layer. Keep it complementary:

- Emit only stable, cross-project preferences that Codex should follow in every
  applicable session.
- Omit episodic context, task status, repository facts, file paths, and recalled
  events that belong in Codex memories or project documentation.
- If a candidate rule merely restates remembered context, drop it. If it turns
  repeated evidence into an actionable working agreement, state it once.
- Keep the result compact so it does not crowd out project-specific `AGENTS.md`
  guidance, which is more specific and should remain authoritative.
