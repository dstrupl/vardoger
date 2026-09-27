## OpenClaw history compatibility

Vardoger reads legacy, pre-2.0 OpenClaw JSONL transcripts by default. OpenClaw
2.0 stores canonical history in per-agent SQLite databases; Vardoger never
queries those private tables. Current history can be read through the official
Gateway CLI only after the user explicitly opts in. Ask the user before setting
`VARDOGER_OPENCLAW_GATEWAY=1`, then run every prepare command with `--full`.
Vardoger invokes only the read-only `sessions.list` and `chat.history` methods
and does not accept a Gateway URL, token, or password. Without that approval,
stop the workflow and suggest OpenClaw's native `USER.md` and memory features.
