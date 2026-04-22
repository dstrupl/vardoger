# Marketplace status

Tracking sheet for vardoger's presence on each AI-assistant marketplace. This
page is the single source of truth for external reviewers and for the
[Phase 4 PRD checkboxes](./PRD.md#phase-4--marketplace-publishing) — flip a
row here when its state changes, then update the PRD in the same PR.

Status vocabulary:

- **Not started** — no submission has been opened.
- **Draft** — submission form started / local testing in progress.
- **Submitted** — submission form or CLI publish completed; waiting for the
  marketplace reviewer.
- **Changes requested** — reviewer has responded with feedback we need to
  address.
- **Live** — listing is public and installable.

Last refreshed: **2026-04-22** (UTC).

| Marketplace                 | Surface                                           | Plugin root           | Status       | Submitted on | Live on | Notes                                                                                                                                 |
| --------------------------- | ------------------------------------------------- | --------------------- | ------------ | ------------ | ------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **PyPI**                    | `pipx install vardoger`                           | (repo root)           | Live         | 2026-04-20   | 2026-04-22 | Current version `0.3.0`. Releases: [v0.1.0](https://github.com/dstrupl/vardoger/releases/tag/v0.1.0) · [v0.2.0](https://github.com/dstrupl/vardoger/releases/tag/v0.2.0) · [v0.2.1](https://github.com/dstrupl/vardoger/releases/tag/v0.2.1) · [v0.2.2](https://github.com/dstrupl/vardoger/releases/tag/v0.2.2) · [v0.3.0](https://github.com/dstrupl/vardoger/releases/tag/v0.3.0). [pypi.org/project/vardoger](https://pypi.org/project/vardoger/). |
| **Cursor Plugin Registry**  | [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish) | `plugins/cursor/`     | Submitted    | 2026-04-20   | —       | Manifest at `plugins/cursor/.cursor-plugin/plugin.json`; `mcp.json` boots via `uvx vardoger mcp`. Logotype URL in the form: `https://raw.githubusercontent.com/dstrupl/vardoger/main/assets/logo.svg`. No public API for review state — check the Cursor publisher dashboard. Last checked 2026-04-22: no reviewer response. |
| **Claude Code Plugins**     | [claude.ai/settings/plugins/submit](https://claude.ai/settings/plugins/submit) | `plugins/claude-code/` | Submitted    | 2026-04-20   | —       | Submitted via the claude.ai form (personal-account path; platform.claude.com is the org-account alternative and feeds the same marketplace). Privacy Policy URL: `https://github.com/dstrupl/vardoger/blob/main/PRIVACY.md`. Platforms selected: Claude Code only (Cowork excluded — no `cowork` adapter and audience is non-developer). Last checked 2026-04-22: no reviewer response. |
| **Codex — custom**          | `codex marketplace add …`                         | `plugins/codex/`      | Not started  | —            | —       | Public manifest at `plugins/codex/marketplace.json` (Milestone 5 PR). One-line install: `codex marketplace add https://github.com/dstrupl/vardoger.git --sparse plugins/codex`. |
| **Codex — official directory** | (pending, see [openai/codex#13712](https://github.com/openai/codex/pull/13712)) | `plugins/codex/`      | Not started  | —            | —       | Watch for self-serve directory opening. Until then, users install via the custom marketplace row above.                               |
| **GitHub Copilot CLI — custom** | `copilot plugin marketplace add dstrupl/vardoger:plugins/copilot` | `plugins/copilot/` | Not started  | —            | —       | Public marketplace manifest at `plugins/copilot/marketplace.json`; plugin manifest at `plugins/copilot/.github/plugin/plugin.json` with a single `analyze` skill. One-line install alternative: `copilot plugin install dstrupl/vardoger:plugins/copilot`. |
| **GitHub Copilot CLI — `awesome-copilot`** | [PR #1461](https://github.com/github/awesome-copilot/pull/1461) | `plugins/copilot/` | Submitted | 2026-04-21 | — | PR opened 2026-04-21 as `add-vardoger-analyze-skill`. Initial submission targeted `main`; the `github-actions` bot requested a retarget to the `staged` branch (auto-published to `main`), and the PR was re-pointed at `staged` the same day. Awaiting human review. Last checked 2026-04-22: `reviewDecision=CHANGES_REQUESTED` is the lingering bot review — functionally waiting on a maintainer. |
| **Windsurf MCP Store**      | (no public submission form)                       | `plugins/windsurf/`   | N/A          | —            | —       | Windsurf's in-product MCP Store is editorial. Users install via the snippet in `plugins/windsurf/README.md` (`mcp_config.json` + `vardoger setup windsurf`). Revisit if Windsurf opens a self-serve submission flow. |
| **Cline MCP Marketplace**   | [issue #1394](https://github.com/cline/mcp-marketplace/issues/1394) | `plugins/cline/` | Submitted | 2026-04-20 | — | Server submission issue `[Server Submission]: vardoger — personalize AI assistants from local history` opened 2026-04-20 at cline/mcp-marketplace. Install guidance for the LLM-driven install flow at `plugins/cline/llms-install.md`; user-facing readme at `plugins/cline/README.md`. Last checked 2026-04-22: no reviewer comments yet. |
| **OpenClaw ClawHub**        | `openclaw skill publish .`                        | `plugins/openclaw/skills/analyze/` | Not started  | —            | —       | `SKILL.md` frontmatter already matches the ClawHub schema (`version`, `metadata.openclaw.requires.bins`, `homepage`). Verification happens via the ClawHub dashboard after `skill publish`. |

## How to update this table

1. When you open a submission, move the row to **Submitted** and fill in the
   "Submitted on" date (UTC).
2. When a marketplace reviewer responds, either move the row to
   **Changes requested** (and link the feedback in Notes) or **Live** (and fill
   in "Live on").
3. In the same PR, check the matching box under
   [PRD §5 Platform integrations](./PRD.md#phase-4--marketplace-publishing)
   so both files stay in sync.
4. Bump the "Last refreshed" date at the top of this file, and refresh the
   per-row "Last checked" notes for any rows you verified.

## Why each submission matters

- **Cursor registry** — removes the `pipx install` prerequisite for Cursor
  users; they can install directly from the in-app marketplace.
- **Claude Code directory** — same story for Claude Code; also enables
  discoverability and the `/plugin` install UX.
- **Codex custom + official** — Codex's self-serve directory is still
  being built, so the custom marketplace is our interim distribution.
- **Copilot CLI custom + `awesome-copilot`** — GitHub's plugin marketplace
  lets users register our repo as a source directly; `awesome-copilot` is
  supplementary for discoverability.
- **Windsurf** — no public submission form today; the per-user MCP config
  snippet is the primary install path.
- **Cline MCP marketplace** — single-click install for Cline users once
  merged; the `llms-install.md` file guides Cline through the install.
- **ClawHub** — ClawHub is the canonical skill registry for OpenClaw;
  publishing there is required for OpenClaw users to find vardoger.
