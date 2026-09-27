## Claude Code memory boundary

Claude Code already maintains per-repository auto memory for project learnings,
corrections, and context. The Vardoger result is a separate user-authored rules
layer. Keep it complementary:

- Emit only durable, cross-project preferences about how the assistant should
  communicate, reason, edit, validate, and collaborate with the user.
- Omit repository facts, file paths, one-off task state, session summaries, and
  commands that belong in project instructions or Claude Code auto memory.
- If a candidate rule merely repeats an episodic fact, drop it. If it expresses
  a stable preference evidenced across projects, state the preference once.
- Keep rules concise and non-conflicting because Claude Code loads user rules,
  project instructions, and auto memory together.
