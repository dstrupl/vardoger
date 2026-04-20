# Marketplace status

Tracking sheet for vardoger's presence on each AI-assistant marketplace. This
page is the single source of truth for external reviewers and for the
[Phase 4 PRD checkboxes](../PRD.md#phase-4--marketplace-publishing) — flip a
row here when its state changes, then update the PRD in the same PR.

Status vocabulary:

- **Not started** — no submission has been opened.
- **Draft** — submission form started / local testing in progress.
- **Submitted** — submission form or CLI publish completed; waiting for the
  marketplace reviewer.
- **Changes requested** — reviewer has responded with feedback we need to
  address.
- **Live** — listing is public and installable.

| Marketplace                 | Surface                                           | Plugin root           | Status       | Submitted on | Live on | Notes                                                                                                                                 |
| --------------------------- | ------------------------------------------------- | --------------------- | ------------ | ------------ | ------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **PyPI**                    | `pipx install vardoger`                           | (repo root)           | Live         | 2026-04-20   | 2026-04-20 | [v0.1.0 release](https://github.com/dstrupl/vardoger/releases/tag/v0.1.0) · [pypi.org/project/vardoger](https://pypi.org/project/vardoger/) |
| **Cursor Plugin Registry**  | [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish) | `plugins/cursor/`     | Not started  | —            | —       | Manifest at `plugins/cursor/.cursor-plugin/plugin.json`; `mcp.json` boots via `uvx vardoger mcp`.                                     |
| **Claude Code Plugins**     | [clau.de/plugin-directory-submission](https://clau.de/plugin-directory-submission) | `plugins/claude-code/` | Not started  | —            | —       | Manifest at `plugins/claude-code/.claude-plugin/plugin.json`; verify against [anthropics/claude-code#34813](https://github.com/anthropics/claude-code/issues/34813) and [#36651](https://github.com/anthropics/claude-code/issues/36651) before submitting. |
| **Codex — custom**          | `codex marketplace add …`                         | `plugins/codex/`      | Not started  | —            | —       | Public manifest at `plugins/codex/marketplace.json` (Milestone 5 PR). One-line install: `codex marketplace add https://github.com/dstrupl/vardoger.git --sparse plugins/codex`. |
| **Codex — official directory** | (pending, see [openai/codex#13712](https://github.com/openai/codex/pull/13712)) | `plugins/codex/`      | Not started  | —            | —       | Watch for self-serve directory opening. Until then, users install via the custom marketplace row above.                               |
| **OpenClaw ClawHub**        | `openclaw skill publish .`                        | `plugins/openclaw/skills/analyze/` | Not started  | —            | —       | `SKILL.md` frontmatter already matches the ClawHub schema (`version`, `metadata.openclaw.requires.bins`, `homepage`). Verification happens via the ClawHub dashboard after `skill publish`. |

## How to update this table

1. When you open a submission, move the row to **Submitted** and fill in the
   "Submitted on" date (UTC).
2. When a marketplace reviewer responds, either move the row to
   **Changes requested** (and link the feedback in Notes) or **Live** (and fill
   in "Live on").
3. In the same PR, check the matching box under
   [PRD §5 Platform integrations](../PRD.md#phase-4--marketplace-publishing)
   so both files stay in sync.

## Why each submission matters

- **Cursor registry** — removes the `pipx install` prerequisite for Cursor
  users; they can install directly from the in-app marketplace.
- **Claude Code directory** — same story for Claude Code; also enables
  discoverability and the `/plugin` install UX.
- **Codex custom + official** — Codex's self-serve directory is still
  being built, so the custom marketplace is our interim distribution.
- **ClawHub** — ClawHub is the canonical skill registry for OpenClaw;
  publishing there is required for OpenClaw users to find vardoger.
