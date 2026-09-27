# vardoger — OpenClaw integration

An OpenClaw skill that analyzes legacy JSONL or opt-in Gateway conversation
history and generates personalized instructions.

## Current compatibility

OpenClaw 2.0 moved canonical sessions and transcripts to per-agent SQLite
databases. Vardoger never queries those private tables. Current history is read
only through the official `openclaw gateway call` CLI, using the read-only
`sessions.list` and `chat.history` RPCs. This route is opt-in and currently
requires a full read because Vardoger's file-hash checkpoints have not yet been
migrated to Gateway message anchors:

```bash
VARDOGER_OPENCLAW_GATEWAY=1 vardoger prepare --platform openclaw --full
```

Vardoger does not accept a Gateway URL, token, or password. The official CLI
resolves its own configured target and authentication. Without the opt-in flag,
Vardoger detects current SQLite and stops with an actionable error rather than
silently analyzing stale JSONL left after migration. Pre-2.0 JSONL remains
supported locally.

Generated `vardoger-personalization` skills remain valid: Vardoger writes the
required `name` and `description` YAML frontmatter. Generating one from current
history requires the explicit full Gateway workflow above.

For OpenClaw-only personalization, prefer OpenClaw's native
[`USER.md` and memory workflow](https://docs.openclaw.ai/concepts/memory).
OpenClaw already defines `USER.md` for stable preferences and working context,
and can backfill retained sessions into its native memory system. Vardoger is
still useful for legacy OpenClaw installs; its strongest future role here is
likely importing preferences learned from other supported assistants.

References: [session storage](https://docs.openclaw.ai/reference/session-management-compaction/store),
[skill format](https://docs.openclaw.ai/tools/creating-skills),
[Gateway history access](https://docs.openclaw.ai/gateway/clients), and
[Gateway CLI calls](https://docs.openclaw.ai/cli/gateway/query).

## Prerequisites

- **Python 3.11+** and **pipx** — see [installation instructions](../../README.md#prerequisites) in the main README
- **OpenClaw** with its currently supported Node.js runtime — [github.com/OpenClaw/OpenClaw](https://github.com/OpenClaw/OpenClaw)

## Install

The direct setup path tracks the current PyPI release for legacy and Gateway
workflows:

```bash
pipx install vardoger
vardoger setup openclaw
```

This installs the vardoger analysis skill to `~/.openclaw/skills/vardoger/`. OpenClaw discovers it automatically on the next session.

Vardoger is also listed on
[ClawHub as `vardoger-analyze`](https://clawhub.ai/dstrupl/vardoger-analyze),
but the public listing currently exposes 0.3.1 with security status `Review`
and mandatory MIT-0 terms. The source skill declares Apache-2.0, so do not use
ClawHub for a new install or publish another version until the owner explicitly
decides whether MIT-0 distribution is acceptable. This distribution issue is
separate from the Gateway runtime path, which passed disposable-profile live
acceptance on 2026-09-27.

If the owner accepts ClawHub's distribution terms, maintainers can publish a
ClawHub-specific artifact with the current CLI shape:

```bash
clawhub skill publish plugins/openclaw/skills/analyze \
  --slug vardoger-analyze \
  --name "vardoger — Analyze History" \
  --version X.Y.Z \
  --tags latest \
  --changelog "Describe the release"
```

## Usage

On a legacy JSONL installation, ask OpenClaw to "analyze my conversation
history" or "run the vardoger skill." On OpenClaw 2.0, explicitly opt in to
the full Gateway workflow above. For OpenClaw-only personalization, native
memory remains the simpler default.

### Where the personalization lands

- **Default — user-global scope:** writes to `~/.openclaw/skills/vardoger-personalization/SKILL.md`, which OpenClaw auto-discovers on every session.
- **Opt-in — project scope:** pass `project_path="<workspace root>"` (and `scope=project`) to land `<project>/skills/vardoger-personalization/SKILL.md`. vardoger refuses to write project-scoped skills into a directory that doesn't look like a real project (it requires `.git`, a language manifest, `AGENTS.md`, or an existing `.cursor/` in the path or one of its ancestors). Without that check, an MCP server launched from `$HOME` would silently drop skills into a location OpenClaw would never read. Supply a real workspace root or drop the `project_path` argument to write user-globally.

## Uninstall

Remove the `~/.openclaw/skills/vardoger/` directory.
