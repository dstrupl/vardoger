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

Last refreshed: **2026-04-27** (UTC).

2026-04-27: Discovered the **Claude Code Plugins** row had been flipped to **Live** prematurely on 2026-04-25 — the `Published` badge on the [claude.ai plugin-submissions dashboard](https://claude.ai/settings/plugins/submissions) only means "submission accepted and validated by Anthropic," it does NOT mean the plugin is merged into the `anthropics/claude-plugins-official` catalog that Claude Code clients actually read. Verified against [`https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/.claude-plugin/marketplace.json`](https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/.claude-plugin/marketplace.json): as of 2026-04-27 the catalog contains 160 plugins (15 under `external_plugins/` — `asana`, `context7`, `discord`, `fakechat`, `firebase`, `github`, `gitlab`, `greptile`, `imessage`, `laravel-boost`, `linear`, `playwright`, `serena`, `telegram`, `terraform`) and **vardoger is not among them**, confirming the in-product `/plugin` Discover tab's report. Split the single Claude Code row into two parallel rows (matching the Codex and Copilot patterns): **Claude Code — official directory** (re-downgraded to **Submitted** — awaiting catalog merge) and **Claude Code — custom** (new, **Live (self-served)**). Added `.claude-plugin/marketplace.json` at the repo root — schema matches the Anthropic-published file (string `source: "./plugins/claude-code"`, keys limited to the vocabulary actually used across the 160 official entries: `name`, `description`, `version`, `author`, `category: productivity`, `keywords`, `source`, `homepage`, `license`). Users install via `/plugin marketplace add dstrupl/vardoger` then `/plugin install vardoger@vardoger`. Monorepo layout is fine: the marketplace root is the repo root, plugin root is `./plugins/claude-code` relative to it (pattern mirrors Anthropic's own `./plugins/agent-sdk-dev` etc.). Documented the new install path in `plugins/claude-code/README.md`. Matching Phase 4 checkbox updated in `PRD.md`. Also added a new row for [**claudemarketplaces.com**](#claudemarketplacescom) — a third-party community aggregator that crawls GitHub daily for repos containing `.claude-plugin/marketplace.json` files and lists them automatically (no submission, no PR). Row seeded at **Pending ingestion (auto)**; the same manifest commit that served the custom row above is all the action needed — next poll ~2026-04-29 confirms the crawl picked us up.

Pass 3 (2026-04-25 late PM): Followed through on `github/awesome-copilot#1461` to get every pre-merge check green. Addressed the `skill-check` validator warning "No numbered workflow steps" by inspecting the validator source at [`dotnet/skills` `eng/skill-validator/src/Check/SkillProfiler.cs`](https://github.com/dotnet/skills/blob/main/eng/skill-validator/src/Check/SkillProfiler.cs) (regex is `^\d+\.\s`, multiline) and adding a numbered workflow overview section to `skills/vardoger-analyze/SKILL.md` that mirrors the existing detailed `## Steps` section. Then rebased the branch onto `upstream/staged` so the PR diff only touches the files the PR actually introduces — the old base (`63d08d5 chore: publish from staged` on `main`) had drifted far enough from current `staged` that the PR appeared to touch ~750 unrelated files. Post-rebase the PR shows a single file (`skills/vardoger-analyze/SKILL.md`) across four commits: `35db99f` (initial add), `b7a7c5a` (Copilot session-state path fix — was `1c7b29d` before the rebase rewrote it), `a7ab430` (numbered workflow overview), and `1776546` (regenerated `docs/README.skills.md` to include the new row — required by the `validate-readme` CI job which runs `npm start` and fails on any diff). One rabbit-hole worth recording: the first `validate-readme` recovery attempt also committed an "edit" to `docs/README.agents.md` that had been silently produced by running `npm start` offline — the generator drops the MCP catalog link column (`[apify](https://github.com/mcp/…)` → bare `apify`) when it can't reach GitHub's MCP catalog at runtime, so an offline regen looks like a real diff but is actually a network-dependent false positive; reverted the commit once the with-network regen produced the identical bytes already on `staged`. Final state: `validate-readme`, `skill-check`, `codespell`, and `check-line-endings` all pass. PR is still `BLOCKED` from merge by the same stale `github-actions` `CHANGES_REQUESTED` review (`PRR_kwDOO6BQUc73Iv1W`) left behind when the PR originally targeted `main` — the `check-pr-target` workflow only triggers on `opened` events so it never dismissed itself after the `staged` retarget. Posted a comment on the PR explaining the situation and pinging `@aaronpowell` and `@dvelton` asking a maintainer to dismiss the stale review ([issuecomment-4320268413](https://github.com/github/awesome-copilot/pull/1461#issuecomment-4320268413)).

Pass 2 (2026-04-25 PM): Audited every open submission and every Live listing for version-freshness vs. `vardoger 0.3.1`. Fixed four real defects that would otherwise surface to reviewers or end users:

- **`github/awesome-copilot#1461`**: PR description said "verified against `vardoger 0.2.1`" and "PyPI current version 0.2.1" (stale from the 2026-04-21 submission). The submitted `SKILL.md` also referenced `~/.copilot/history-session-state/`, which does not exist — the real CLI path is `~/.copilot/session-state/` (see `src/vardoger/history/copilot.py`). Edited the PR body to reference 0.3.1 and the correct path; pushed a fix to `dstrupl:add-vardoger-analyze-skill` correcting both places in the submitted `SKILL.md` (this commit was originally `1c7b29d`; the Pass 3 rebase onto `upstream/staged` rewrote it to [`b7a7c5a`](https://github.com/dstrupl/awesome-copilot/commit/b7a7c5a), which is the SHA reachable on the PR branch now). Also fixed the mirrored typo on line 59 of `plugins/copilot/README.md` in this repo.
- **`cline/mcp-marketplace#1394`**: issue body had the same stale "PyPI current version 0.2.1" line (submitted 2026-04-20 when PyPI was 0.2.1). Edited to 0.3.1.
- **`docker/mcp-registry#2949`**: `source.commit` was pinned to `1090cf27ee75bec233b78c7234c56d68b30f6651`, which is the **annotated tag object SHA** of `v0.3.1`, not the peeled commit SHA. The validator only does a regex check (`^[a-f0-9]{40}$`) so it passed, but `source.commit` is supposed to be a commit SHA. Fixed to `98c9006f87880d907944557d343028f2b53cf635` (`git rev-list -1 v0.3.1`) in both `plugins/docker-mcp/server.yaml` and the submission branch (pushed [`ca30a5d`](https://github.com/dstrupl/mcp-registry/commit/ca30a5d) to `dstrupl:add-vardoger`); updated the PR description to explain the correction. Also corrected `plugins/docker-mcp/README.md` step 2 to recommend `git rev-list -1 v0.3.1` (or `git rev-parse v0.3.1^{}`) instead of `git rev-parse v0.3.1` (which returns the tag object SHA for annotated tags).
- **McpMux tracked copy**: re-fetched the file at [`mcpmux/mcp-servers@main:servers/io.github-dstrupl-vardoger.json`](https://github.com/mcpmux/mcp-servers/blob/main/servers/io.github-dstrupl-vardoger.json). Upstream post-merge renamed the field `icon: "🪞"` → `logo: "https://avatars.githubusercontent.com/u/4134230?v=4"` (the `dstrupl` GitHub avatar — verified via the GitHub users API) and reformatted compact arrays/objects to multi-line. Overwrote `plugins/mcpmux/vardoger.json` with the upstream-current bytes so our tracked copy matches what's actually live.

**ClawHub findings (not fixable by republishing)**: the listing shows `latestVersion.license: "MIT-0"` despite our `SKILL.md` frontmatter carrying `license: Apache-2.0` (uploaded verbatim — the published `SKILL.md` sha256 `1bba696e…` matches the local file byte-for-byte). Inspected the CLI (`npx clawhub publish --help`, ClawHub CLI `v0.9.0 (4cc8e7d9)`): **there is no `--license` flag on `publish` or `sync`**, and ClawHub does not honor frontmatter `license:` — the listing was auto-assigned MIT-0. Additionally, the post-publish security scan has resolved (not "pending"): moderation verdict is `suspicious` with reason codes `suspicious.llm_suspicious` + `suspicious.vt_suspicious`. Reading the scan output, both scanners correctly describe the skill's real behavior — "high-privilege access to private data and the requirement to bypass sandbox protections for global file writes represent significant security and privacy risks" — and the rating is informational, not a hide. Republishing will not change either field. Resolving the license requires either a ClawHub support ticket or an owner-dashboard setting; the "suspicious" flag is ClawHub's honest assessment of a skill that legitimately needs broad `$HOME` read/write. Documented both facts on the ClawHub row.

**Clean submissions verified against 0.3.1** (no change needed): PyPI (`0.3.1` live; `mcp-name: io.github.dstrupl/vardoger` marker present in the long_description); Official MCP Registry (`curl …?search=vardoger` → `version: 0.3.1`, `packages[0].version: 0.3.1`, `status: active`, `isLatest: true`); McpMux (no version pin; runtime uses `vardoger` on PATH); Codex + Copilot custom marketplaces (both `source: "."` / `"local"`, install from `main@0.3.1`); Cursor Plugin Registry and Claude Code Plugins (manifests on `main` are `0.3.1`; runtime uses `uvx vardoger mcp` / git-clone of our repo, so end-users get 0.3.1 regardless of what the listing metadata snapshotted).

Pass 1 (2026-04-25 AM): **Claude Code Plugins** flipped to **Live** — the [claude.ai plugin-submissions dashboard](https://claude.ai/settings/plugins/submissions) now shows the Vardoger listing with a **Published** badge (submitted 2026-04-20, went live 2026-04-25). Row flipped from **Submitted** to **Live**; matching Phase 4 checkbox ticked in `PRD.md`. Also polled the remaining reviewer queues to re-verify their states: `github/awesome-copilot#1461` still OPEN with `reviewDecision=CHANGES_REQUESTED` (the lingering bot review) and no new human comments since 2026-04-21; `cline/mcp-marketplace#1394` still OPEN with zero comments; `docker/mcp-registry#2949` still OPEN with `reviewDecision=REVIEW_REQUIRED` and no comments. "Last checked" dates bumped to 2026-04-25 for those three rows; Cursor Plugin Registry has no public review API so its "Last checked" stays at 2026-04-22. Pruned the stale "Ready-to-publish — owner action required" pickup section — all three of its items (Official MCP Registry, Docker MCP Registry, ClawHub) were completed in the 2026-04-24 sweep and are already reflected in the table above.

Previous refresh (2026-04-24): Cut `vardoger 0.3.1` on PyPI and used the release to unblock the remaining MCP-registry surfaces in a single sweep: (1) published to the **Official MCP Registry** as `io.github.dstrupl/vardoger@0.3.1` — row flipped from **Not started — prep complete** to **Live**; (2) opened the **Docker MCP Registry** PR ([docker/mcp-registry#2949](https://github.com/docker/mcp-registry/pull/2949)) with `source.commit` pinned to the `v0.3.1` release SHA `1090cf27` and both `go run ./cmd/validate` + `go run ./cmd/build --tools vardoger` passing locally (9 tools discovered) — row flipped to **Submitted**; (3) republished the OpenClaw skill as `vardoger-analyze@0.3.1` (publish id `k97ak6n0cc882ajv2x9tb9s7gs85ekp4`) so the listing carries the explicit `license: Apache-2.0` — row's "Live on" date rolled forward. Earlier: added a runtime `Dockerfile` + `.dockerignore` at the repo root plus tracked `plugins/docker-mcp/server.yaml` / `README.md`; McpMux [PR #113](https://github.com/mcpmux/mcp-servers/pull/113) merged as [`495adbc`](https://github.com/mcpmux/mcp-servers/commit/495adbc131a7ea2acd8df29869b391cc2cb05cbe) — row flipped to **Live**; vardoger now reaches Cursor, Claude Desktop, VS Code, and Windsurf via the McpMux desktop gateway.

Earlier (2026-04-23): addressed @its-mash's review on PR #113 by switching the `VARDOGER_MCP_PLATFORM` input from free-text to a `select` with explicit options (seven supported platforms plus an "Auto-detect (default)" empty-value entry); mirrored the change in our tracked copy at `plugins/mcpmux/vardoger.json`.

Earlier (2026-04-22): ClawHub flipped to **Live (self-served)** the same day as `vardoger-analyze@0.3.0`; Windsurf re-verified (still no public submission); three cross-vendor MCP registry rows added (`modelcontextprotocol/registry`, McpMux, Docker MCP Registry); McpMux PR opened ([mcpmux/mcp-servers#113](https://github.com/mcpmux/mcp-servers/pull/113)) — row flipped to **Submitted**.

At-a-glance table — click any marketplace name for the full submission
history, surface details, and "last checked" context.

| Marketplace | Plugin root | Status | Submitted | Live on | Link |
| --- | --- | --- | --- | --- | --- |
| [**PyPI**](#pypi) | (repo root) | Live | 2026-04-20 | 2026-04-24 | [pypi.org/project/vardoger](https://pypi.org/project/vardoger/) |
| [**Cursor Plugin Registry**](#cursor-plugin-registry) | `plugins/cursor/` | Submitted | 2026-04-20 | — | [publisher dashboard](https://cursor.com/marketplace/publish) |
| [**Claude Code — official directory**](#claude-code--official-directory) | `plugins/claude-code/` | Submitted | 2026-04-20 | — | [submissions dashboard](https://claude.ai/settings/plugins/submissions) |
| [**Claude Code — custom**](#claude-code--custom) | `plugins/claude-code/` | Live (self-served) | 2026-04-27 | 2026-04-27 | `/plugin marketplace add dstrupl/vardoger` |
| [**Codex — custom**](#codex--custom) | `plugins/codex/` | Live (self-served) | 2026-04-20 | 2026-04-20 | `codex plugin marketplace add …` |
| [**Codex — official directory**](#codex--official-directory) | `plugins/codex/` | Not started — blocked upstream | — | — | [openai/codex#13712](https://github.com/openai/codex/pull/13712) |
| [**GitHub Copilot CLI — custom**](#github-copilot-cli--custom) | `plugins/copilot/` | Live (self-served) | 2026-04-20 | 2026-04-20 | `copilot plugin marketplace add …` |
| [**GitHub Copilot CLI — `awesome-copilot`**](#github-copilot-cli--awesome-copilot) | `plugins/copilot/` | Submitted | 2026-04-21 | — | [PR #1461](https://github.com/github/awesome-copilot/pull/1461) |
| [**Windsurf MCP Store**](#windsurf-mcp-store) | `plugins/windsurf/` | N/A | — | — | (no public submission form) |
| [**Official MCP Registry**](#official-mcp-registry) | `plugins/mcp-registry/` | Live | 2026-04-24 | 2026-04-24 | [registry feed](https://registry.modelcontextprotocol.io/v0/servers?search=vardoger) |
| [**McpMux community registry**](#mcpmux-community-registry) | `plugins/mcpmux/` | Live | 2026-04-22 | 2026-04-24 | [PR #113](https://github.com/mcpmux/mcp-servers/pull/113) |
| [**Docker MCP Registry**](#docker-mcp-registry) | `plugins/docker-mcp/` | Submitted | 2026-04-24 | — | [PR #2949](https://github.com/docker/mcp-registry/pull/2949) |
| [**Cline MCP Marketplace**](#cline-mcp-marketplace) | `plugins/cline/` | Submitted | 2026-04-20 | — | [issue #1394](https://github.com/cline/mcp-marketplace/issues/1394) |
| [**OpenClaw ClawHub**](#openclaw-clawhub) | `plugins/openclaw/skills/analyze/` | Live (self-served) | 2026-04-22 | 2026-04-24 | `npx clawhub publish …` |
| [**claudemarketplaces.com**](#claudemarketplacescom) | `.claude-plugin/marketplace.json` | Pending ingestion (auto) | 2026-04-27 | — | [claudemarketplaces.com](https://claudemarketplaces.com) |

## Per-marketplace details

### PyPI

- **Surface:** `pipx install vardoger`
- **Plugin root:** repo root

Current version `0.3.1`. Releases:
[v0.1.0](https://github.com/dstrupl/vardoger/releases/tag/v0.1.0) ·
[v0.2.0](https://github.com/dstrupl/vardoger/releases/tag/v0.2.0) ·
[v0.2.1](https://github.com/dstrupl/vardoger/releases/tag/v0.2.1) ·
[v0.2.2](https://github.com/dstrupl/vardoger/releases/tag/v0.2.2) ·
[v0.3.0](https://github.com/dstrupl/vardoger/releases/tag/v0.3.0) ·
[v0.3.1](https://github.com/dstrupl/vardoger/releases/tag/v0.3.1).
Listing at [pypi.org/project/vardoger](https://pypi.org/project/vardoger/).

### Cursor Plugin Registry

- **Surface:** [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish)
- **Plugin root:** `plugins/cursor/`

Manifest at `plugins/cursor/.cursor-plugin/plugin.json`; `mcp.json` boots via
`uvx vardoger mcp`. Logotype URL in the form:
`https://raw.githubusercontent.com/dstrupl/vardoger/main/assets/logo.svg`. No
public API for review state — check the Cursor publisher dashboard. Last
checked 2026-04-22: no reviewer response.

### Claude Code — official directory

- **Surface:** [claude.ai/settings/plugins/submit](https://claude.ai/settings/plugins/submit)
- **Plugin root:** `plugins/claude-code/`

Submitted via the claude.ai form (personal-account path; platform.claude.com
is the org-account alternative and feeds the same marketplace). Privacy Policy
URL: `https://github.com/dstrupl/vardoger/blob/main/PRIVACY.md`. Platforms
selected: Claude Code only (Cowork excluded — no `cowork` adapter and audience
is non-developer). The claude.ai plugin-submissions dashboard showed the
listing with a **Published** badge on 2026-04-25.

2026-04-27 correction: briefly flipped this row to **Live** on 2026-04-25 on
the basis of the `Published` badge alone, then reverted to **Submitted**
after discovering that badge does NOT mean the plugin is live in the catalog
Claude Code clients read. The in-product `/plugin` → Discover tab still
shows 160 plugins and vardoger isn't among them. Verified against the
source-of-truth manifest at
[`anthropics/claude-plugins-official/.claude-plugin/marketplace.json`](https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/.claude-plugin/marketplace.json):
the `external_plugins/` section lists 15 entries (asana, context7, discord,
fakechat, firebase, github, gitlab, greptile, imessage, laravel-boost,
linear, playwright, serena, telegram, terraform) and vardoger is absent. So
"Published" in the dashboard is tier 1 (Anthropic-side validation accepted)
and the merge into the public catalog is a separate tier-2 step with no
documented SLA.

Next poll 2026-05-02 (one week after "Published"): if vardoger is still not
in `external_plugins/`, either (a) open an issue at
[anthropics/claude-code#issues](https://github.com/anthropics/claude-code/issues)
referencing the 2026-04-25 publish date, or (b) check whether
`anthropics/claude-plugins-official` accepts direct community PRs for new
external plugins and open one if so.

In the meantime, users have two working install paths today:
`pipx install vardoger && vardoger setup claude-code` (the path we've always
shipped) and the self-hosted marketplace below.

### Claude Code — custom

- **Surface:** `/plugin marketplace add dstrupl/vardoger`
- **Plugin root:** `plugins/claude-code/`

Self-hosted marketplace manifest at `.claude-plugin/marketplace.json` in the
repo root. Users add this repo as a marketplace source and install from it:

```
/plugin marketplace add dstrupl/vardoger
/plugin install vardoger@vardoger
```

Added 2026-04-27 after confirming (a) the official-directory submission is
stuck at tier 1 with no documented timeline and (b) Claude Code's docs
explicitly support user-hosted marketplaces via a `.claude-plugin/marketplace.json`
file ([plugin-marketplaces reference](https://code.claude.com/docs/en/plugin-marketplaces.md)).
Monorepo-compatible: the manifest uses `"source": "./plugins/claude-code"`
(a relative string source resolved against the marketplace root, which is
the repo root) — the same pattern Anthropic's own plugins use (e.g.
`"source": "./plugins/agent-sdk-dev"` in the official catalog). Schema
fields used (`name`, `description`, `version`, `author`, `category`,
`keywords`, `source`, `homepage`, `license`) were selected by surveying
which keys actually appear across the 160 plugins in the official
`marketplace.json`, so the manifest is a drop-in if Anthropic ever merges
`vardoger` into `external_plugins/` using this entry verbatim.

No central registry to submit to — the manifest in our repo *is* the
marketplace, same as our Codex and Copilot custom marketplace rows. No
further maintenance required beyond bumping the two `version` fields
(top-level `metadata.version` and the per-plugin `version`) in lock-step
with each vardoger release.

### Codex — custom

- **Surface:** `codex plugin marketplace add …`
- **Plugin root:** `plugins/codex/`

Codex has no central registry for custom marketplaces — our public manifest
at `plugins/codex/marketplace.json` *is* the marketplace. Users install it
directly with
`codex plugin marketplace add https://github.com/dstrupl/vardoger.git --sparse plugins/codex`
(or the legacy `codex marketplace add` shim). Nothing to submit; flipped to
**Live** on 2026-04-22 after confirming there is no separate submission flow.

### Codex — official directory

- **Surface:** (pending self-serve)
- **Plugin root:** `plugins/codex/`

[openai/codex#13712](https://github.com/openai/codex/pull/13712) merged
2026-03-07, adding the curated plugin marketplace infrastructure. Per
[developers.openai.com/codex/plugins/build](https://developers.openai.com/codex/plugins/build),
"Adding plugins to the official Plugin Directory is coming soon. Self-serve
plugin publishing and management are coming soon." Last checked 2026-04-22 —
still no self-serve flow. Users install via the custom marketplace row above
in the meantime.

### GitHub Copilot CLI — custom

- **Surface:** `copilot plugin marketplace add dstrupl/vardoger:plugins/copilot`
- **Plugin root:** `plugins/copilot/`

Copilot CLI ships two default marketplaces (`copilot-plugins`,
`awesome-copilot`) and lets users register any GitHub repo as an additional
custom marketplace — there is no separate central registry to submit to. Our
public marketplace manifest at `plugins/copilot/marketplace.json` (plus the
plugin manifest at `plugins/copilot/.github/plugin/plugin.json` with a single
`analyze` skill) is installable today via
`copilot plugin marketplace add dstrupl/vardoger:plugins/copilot` or the
one-line alternative `copilot plugin install dstrupl/vardoger:plugins/copilot`.
The `awesome-copilot` listing is tracked as a separate row below. Flipped to
**Live** on 2026-04-22.

### GitHub Copilot CLI — `awesome-copilot`

- **Surface:** [PR #1461](https://github.com/github/awesome-copilot/pull/1461)
- **Plugin root:** `plugins/copilot/`

PR opened 2026-04-21 as `add-vardoger-analyze-skill`. Initial submission
targeted `main`; the `github-actions` bot requested a retarget to the
`staged` branch (auto-published to `main`), and the PR was re-pointed at
`staged` the same day.

2026-04-25 (Pass 2 — PM): edited the PR description to reference
`vardoger 0.3.1` (was stale at 0.2.1) and fixed the Copilot session-state path
in the submitted `SKILL.md` from `~/.copilot/history-session-state/` to
`~/.copilot/session-state/` (the real path our CLI reads; see
`src/vardoger/history/copilot.py`). Originally pushed as `1c7b29d`; the Pass 3
rebase rewrote it to
[`b7a7c5a`](https://github.com/dstrupl/awesome-copilot/commit/b7a7c5a).

2026-04-25 (Pass 3 — late PM): drove the remaining pre-merge checks to green.

1. **`skill-check` validator warning** "No numbered workflow steps" — traced
   to the regex `^\d+\.\s` (multiline) in [`dotnet/skills`
   `eng/skill-validator/src/Check/SkillProfiler.cs`](https://github.com/dotnet/skills/blob/main/eng/skill-validator/src/Check/SkillProfiler.cs).
   Added a numbered workflow overview section to `SKILL.md`
   ([`a7ab430`](https://github.com/dstrupl/awesome-copilot/commit/a7ab430))
   that restates the existing `## Steps` section as an ordered list at the
   top.
2. **Noisy PR diff** (user reported seeing ~750 unrelated files touched) —
   root cause was that the branch was originally opened against `main` at
   base commit `63d08d5` and then retargeted to `staged` without a rebase,
   so GitHub computed the diff against a very stale merge-base. Rebased
   `add-vardoger-analyze-skill` onto current `upstream/staged` (our three
   relevant commits replayed cleanly) and force-pushed with
   `--force-with-lease`. PR now shows a single file —
   `skills/vardoger-analyze/SKILL.md` — across four commits.
3. **`validate-readme` CI failure** — the workflow runs `npm start`
   (regenerates `README.md`, `docs/README.agents.md`, `docs/README.skills.md`,
   and `.github/plugin/marketplace.json`) then fails on any `git diff`. Ran
   `npm start` locally and committed the updated `docs/README.skills.md`
   row for vardoger-analyze
   ([`1776546`](https://github.com/dstrupl/awesome-copilot/commit/1776546)).
   Briefly committed an "edit" to `docs/README.agents.md` as well, then
   reverted — the generator is network-dependent (fetches the GitHub MCP
   catalog at runtime to render the table's link column), so an offline
   `npm start` produces a file that looks changed but is actually a
   network-dependent false positive. Re-running with network access
   produced the identical bytes already on `staged`, so that file no
   longer needs a commit.

All four CI jobs (`validate-readme`, `skill-check`, `codespell`,
`check-line-endings`) pass as of this pass.

PR is still `mergeable: BLOCKED` / `reviewDecision: CHANGES_REQUESTED`, but
the only outstanding review is the stale `github-actions`
`CHANGES_REQUESTED` from
[`.github/workflows/check-pr-target.yml`](https://github.com/github/awesome-copilot/blob/main/.github/workflows/check-pr-target.yml)
left over from when this PR originally targeted `main`. That workflow only
triggers on `pull_request_target.types: [opened]` against `main`, so
retargeting the PR to `staged` did not re-trigger it and it never dismissed
itself. Review id `PRR_kwDOO6BQUc73Iv1W`. Posted
[issuecomment-4320268413](https://github.com/github/awesome-copilot/pull/1461#issuecomment-4320268413)
explaining the stale-review situation and pinging `@aaronpowell` and
`@dvelton` to ask a maintainer to dismiss it — the PR author cannot dismiss
their own reviewer's review.

Last checked 2026-04-25: `OPEN` / `CHANGES_REQUESTED` (stale bot review
only); no human comments since 2026-04-21.

### Windsurf MCP Store

- **Surface:** (no public submission form)
- **Plugin root:** `plugins/windsurf/`

Re-verified 2026-04-22 against the
[Windsurf MCP docs](https://docs.windsurf.com/windsurf/cascade/mcp)
(`llms-full.txt`): the in-product MCP marketplace is still curated ("Official
MCPs show up with a blue checkmark, indicating that they are made by the
parent service company"), there is no public submission endpoint or PR repo,
and the only third-party install paths are (a) manual
`~/.codeium/windsurf/mcp_config.json` edit — already documented in
`plugins/windsurf/README.md` via `vardoger setup windsurf` — and (b) the
Enterprise "Internal MCP Registry" feature, which consumes schemas conforming
to [`modelcontextprotocol.io`](https://modelcontextprotocol.io/) (covered by
the Official MCP Registry row below). Revisit if Windsurf publishes a
self-serve submission flow.

### Official MCP Registry

- **Surface:** `mcp-publisher publish` against `registry.modelcontextprotocol.io`
- **Plugin root:** `plugins/mcp-registry/`

Published 2026-04-24 as `io.github.dstrupl/vardoger@0.3.1` via
`mcp-publisher publish` against `registry.modelcontextprotocol.io` (GitHub
OAuth device-flow login as `dstrupl`; tracked `server.json` lives at
`plugins/mcp-registry/server.json`). Ownership is established by the
`<!-- mcp-name: io.github.dstrupl/vardoger -->` marker in the repo-root
`README.md`, which the PyPI 0.3.1 wheel carries.

Verified via
`curl -sL "https://registry.modelcontextprotocol.io/v0/servers?search=vardoger"`:
`status=active`, `isLatest=true`, package pinned to PyPI `vardoger@0.3.1`,
stdio transport, lone `VARDOGER_MCP_PLATFORM` env var surfaced. The
[MCP Registry preview](https://registry.modelcontextprotocol.io/docs) feed
is ingested by Docker Desktop's MCP Toolkit, VS Code's MCP picker, Windsurf's
enterprise Internal MCP Registry feature, and any host that syncs it.

Next release: bump `version` in `plugins/mcp-registry/server.json` (both
top-level and `packages[0]`) in lock-step with the PyPI release and re-run
`mcp-publisher publish`. Before each publish, re-run `mcp-publisher init` in
a scratch dir and diff against the tracked file to catch any
`packageArguments` schema drift (see `plugins/mcp-registry/README.md`).

### McpMux community registry

- **Surface:** [PR #113](https://github.com/mcpmux/mcp-servers/pull/113)
- **Plugin root:** `plugins/mcpmux/`

[McpMux](https://mcpmux.com) is a desktop MCP gateway that proxies tools into
Cursor, Claude Desktop, VS Code, and Windsurf through one endpoint; one merged
PR lands vardoger in every McpMux client. Tracked server definition lives at
`plugins/mcpmux/vardoger.json` (schema version `2.1`, stdio transport invoking
`vardoger mcp`, categories `developer-tools` / `productivity` / `ai-ml`,
`platforms: ["all"]`).

PR #113 opened 2026-04-22 against `mcpmux/mcp-servers` from
`dstrupl:add-vardoger` with DCO sign-off; `node scripts/validate.js` reports
`PASS` + no ID/alias conflicts across the 106-server baseline. 2026-04-23:
addressed @its-mash's review (pushed
[80e6cb2](https://github.com/mcpmux/mcp-servers/commit/80e6cb2)) by switching
`VARDOGER_MCP_PLATFORM` from `text` to `select` with explicit options for each
supported platform plus an "Auto-detect (default)" empty-value entry;
`npm run validate:all` still reported 106 PASS / 0 FAIL and
`npm run check-conflicts` clean. 2026-04-24: @its-mash approved and merged as
[`495adbc`](https://github.com/mcpmux/mcp-servers/commit/495adbc131a7ea2acd8df29869b391cc2cb05cbe)
at 17:03 UTC. The McpMux bundle refreshes from `main` within ~an hour, so
desktop clients pick up the entry automatically from that point. No further
maintenance until vardoger ships a breaking MCP-tool or CLI change.

### Docker MCP Registry

- **Surface:** [PR #2949](https://github.com/docker/mcp-registry/pull/2949)
- **Plugin root:** `plugins/docker-mcp/`

Docker's catalog (surfaces at [hub.docker.com/mcp](https://hub.docker.com/mcp)
and inside Docker Desktop's MCP Toolkit) requires a working Docker image.
Decision 2026-04-24: let Docker build and sign the image for us
(`mcp/vardoger` on Docker Hub). Landed the runtime `Dockerfile` at the repo
root (multi-stage, non-root UID 1000, builds vardoger from the pinned source
commit, stdio `ENTRYPOINT ["vardoger","mcp"]`, expects the caller's host
`$HOME` bind-mounted at `/host-home`), plus `.dockerignore`, a tracked
`plugins/docker-mcp/server.yaml` (`category: productivity`, one parameterised
`home_path` volume, optional `VARDOGER_MCP_PLATFORM` env), and
`plugins/docker-mcp/README.md` with the submission steps. Cline history is
not accessible from the containerized build (depends on host-OS VS Code
globalStorage layout) — documented in both the `server.yaml` description and
the README; Cline users should continue to install via `pipx`.

Submission:
[`docker/mcp-registry#2949`](https://github.com/docker/mcp-registry/pull/2949)
from `dstrupl:add-vardoger` with `about.title` capitalized to `Vardoger`
(registry validator requires title-cased words). Pre-submit checks:
`go run ./cmd/validate --name vardoger` passed all 11 checks (name /
directory / title / YAML / commit / secrets / env / license / icon / remote /
OAuth) and `go run ./cmd/build --tools vardoger` produced `mcp/vardoger`
locally with 9 tools discovered.

2026-04-25: fixed `source.commit` — was pinned to
`1090cf27ee75bec233b78c7234c56d68b30f6651`, which is the annotated tag object
SHA of `v0.3.1`, not the peeled commit SHA. Docker's validator only runs a
`^[a-f0-9]{40}$` regex check so it passed, but `source.commit` is supposed to
be a commit SHA. Corrected to `98c9006f87880d907944557d343028f2b53cf635`
(`git rev-list -1 v0.3.1`) in both the tracked file and the submission
branch — pushed
[`ca30a5d`](https://github.com/dstrupl/mcp-registry/commit/ca30a5d). PR
description updated with the correction note. Also corrected
`plugins/docker-mcp/README.md` step 2 to recommend `git rev-list -1 v0.3.1`
(or `git rev-parse v0.3.1^{}`) instead of `git rev-parse v0.3.1`, which
returns the annotated tag object SHA.

Last checked 2026-04-25: still `OPEN` / `REVIEW_REQUIRED`, no reviewer
comments yet.

### Cline MCP Marketplace

- **Surface:** [issue #1394](https://github.com/cline/mcp-marketplace/issues/1394)
- **Plugin root:** `plugins/cline/`

Server submission issue
`[Server Submission]: vardoger — personalize AI assistants from local history`
opened 2026-04-20 at cline/mcp-marketplace. Install guidance for the
LLM-driven install flow at `plugins/cline/llms-install.md`; user-facing
readme at `plugins/cline/README.md`.

2026-04-25: edited the issue body to reference `vardoger 0.3.1` (was stale at
0.2.1 from the 2026-04-20 submission). Last checked 2026-04-25: still `OPEN`,
zero comments since filing.

### OpenClaw ClawHub

- **Surface:** `bunx --bun clawhub publish …` (after `bun clawhub login` — GitHub browser OAuth)
- **Plugin root:** `plugins/openclaw/skills/analyze/`

Originally published 2026-04-22 as `vardoger-analyze@0.3.0` (publish id
`k9796s5r5hk5ea46kxbpwk49dd85axz8`) with no `license:` field — ClawHub
defaulted to MIT-0. Republished 2026-04-24 as `vardoger-analyze@0.3.1`
(publish id `k97ak6n0cc882ajv2x9tb9s7gs85ekp4`) via
`bunx --bun clawhub publish plugins/openclaw/skills/analyze/ --slug vardoger-analyze --name "vardoger — Analyze History" --version 0.3.1 --tags latest --changelog "Add explicit Apache-2.0 license"`
so the listing now carries the explicit Apache-2.0 license matching the repo.
Post-publish `bunx --bun clawhub inspect vardoger-analyze` temporarily returns
`Skill is hidden while security scan is pending` — this is ClawHub's standard
quarantine window and clears automatically once the scan completes. Future
refreshes: bump `version:` in `plugins/openclaw/skills/analyze/SKILL.md`
(mirrored from the release tag) and re-run the same `clawhub publish` command
with the new version + changelog.

2026-04-25 audit: the live listing still shows `latestVersion.license: "MIT-0"`
despite the `license: Apache-2.0` frontmatter we re-submitted on 2026-04-24 —
inspected the CLI (`npx clawhub publish --help`, v0.9.0) and **ClawHub's
`publish`/`sync` commands have no `--license` flag** and the platform does
not honor frontmatter `license:`, so the MIT-0 label is platform-assigned and
not fixable by another republish. The post-publish security scan has also
resolved (no longer "pending"): moderation verdict is `suspicious` with
reasons `llm_suspicious` + `vt_suspicious`. The scan output correctly
describes the skill's real behavior ("high-privilege access to private data
and the requirement to bypass sandbox protections for global file writes") —
this is an accurate rating of vardoger's scope, not a false positive, and
the listing remains reachable. Decision: do not republish; document the state
and revisit if ClawHub adds a `--license` flag or a maintainer-appeal path.

### claudemarketplaces.com

- **Surface:** [claudemarketplaces.com](https://claudemarketplaces.com)
- **Plugin root:** `.claude-plugin/marketplace.json` (the repo-root manifest we
  added in the 2026-04-27 PR)

Third-party community aggregator of Claude Code plugin marketplaces, built
and maintained by `@mertduzgun` at
[`mertbuilds/claudemarketplaces.com`](https://github.com/mertbuilds/claudemarketplaces.com).
Explicitly "independent project, not affiliated with Anthropic."

**Registration:** none. Per the project README: *"The site automatically
searches GitHub daily to discover repositories with
`.claude-plugin/marketplace.json` files. All valid marketplaces are
automatically listed — no submission required."* So the same PR that
merged `.claude-plugin/marketplace.json` onto `main` (2026-04-27) is all
the action we need; the aggregator's crawl will pick it up on its next
pass.

Status 2026-04-27: the manifest was merged onto `main` roughly an hour
before this row was added. `claudemarketplaces.com/marketplace/vardoger`
currently returns 404 and the landing page has no vardoger hits, which is
expected pre-crawl. Next check ~2026-04-29 — if the listing has appeared,
flip this row to **Live** and fill in the "Live on" date.

No further maintenance expected beyond keeping the repo-root
`marketplace.json` valid. If the aggregator ever fails to crawl us after
more than a few days, the maintainer's contact paths are the `/feedback`
page on the site and issues on the backing GitHub repo.

## How to update this table

1. When you open a submission, move the row to **Submitted** and fill in the
   "Submitted" date (UTC).
2. When a marketplace reviewer responds, either move the row to
   **Changes requested** or **Live** (and fill in "Live on"). Add the
   feedback / merge notes to that marketplace's subsection under
   [Per-marketplace details](#per-marketplace-details).
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
- **Official MCP Registry** — `registry.modelcontextprotocol.io` is the
  canonical cross-vendor MCP feed, ingested by Docker Desktop's MCP Toolkit,
  VS Code's MCP picker, Windsurf's enterprise Internal MCP Registry feature,
  and any other MCP host that syncs it. One submission here radiates vardoger
  out to multiple hosts without per-vendor work — including the only
  Windsurf-reachable path for enterprise users.
- **McpMux** — single entry point into Cursor, Claude Desktop, VS Code, and
  Windsurf for users who run the McpMux desktop gateway; low-friction PR
  submission reaches all four clients at once.
- **Docker MCP Registry** — Docker Desktop's MCP Toolkit is a large
  distribution surface for containerized MCP servers; requires a Dockerfile
  and therefore depends on a separate decision to containerize vardoger.

## Next session pickup

Priority-ordered actions for the next agent/owner session. Each item links to
its entry under [Per-marketplace details](#per-marketplace-details) for the
full submission history and audit context.

### 1. Poll reviewer queues (re-verify before other work)

- **[Cursor Plugin Registry](#cursor-plugin-registry)** — no public review
  API; log into the
  [Cursor publisher dashboard](https://cursor.com/marketplace/publish) and
  check `plugins/cursor/` submission state. Last checked 2026-04-22.
- **[`awesome-copilot` PR #1461](#github-copilot-cli--awesome-copilot)** —
  `gh pr view 1461 --repo github/awesome-copilot --json state,reviewDecision,statusCheckRollup,comments`.
  All four CI jobs (`validate-readme`, `skill-check`, `codespell`,
  `check-line-endings`) are green as of the 2026-04-25 Pass 3 work; the PR is
  `BLOCKED` only by a stale `github-actions` `CHANGES_REQUESTED` review
  (`PRR_kwDOO6BQUc73Iv1W`) left over from the `staged`-branch retarget.
  Posted [issuecomment-4320268413](https://github.com/github/awesome-copilot/pull/1461#issuecomment-4320268413)
  asking `@aaronpowell` / `@dvelton` to dismiss the stale review. Next poll:
  (a) check whether a maintainer has dismissed the stale review or opened a
  human review, and (b) if no one has responded within ~a week, reply to the
  thread with a polite bump rather than re-pinging.
- **[Cline MCP Marketplace issue #1394](#cline-mcp-marketplace)** —
  `gh issue view 1394 --repo cline/mcp-marketplace --json state,comments`.
  Last checked 2026-04-25: still `OPEN`, zero comments since filing.
- **[Docker MCP Registry PR #2949](#docker-mcp-registry)** —
  `gh pr view 2949 --repo docker/mcp-registry --json state,reviewDecision,comments`.
  Last checked 2026-04-25: still `OPEN` / `REVIEW_REQUIRED`, no reviewer
  comments yet. Note: on 2026-04-25 we pushed
  [`ca30a5d`](https://github.com/dstrupl/mcp-registry/commit/ca30a5d)
  correcting `source.commit` from the annotated tag object SHA
  (`1090cf27…`) to the peeled commit SHA (`98c9006f…`); next poll should
  confirm `go run ./cmd/validate --name vardoger` still passes against the
  updated branch before a reviewer looks at it.
- **[Claude Code — official directory](#claude-code--official-directory)** —
  re-added to this list on 2026-04-27 after reverting the premature flip to
  **Live**. Check whether vardoger has been merged into
  `anthropics/claude-plugins-official/external_plugins/`: `curl -sL https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/.claude-plugin/marketplace.json | grep -c '"name": "vardoger"'`
  (expect `0` today, `1` once merged). First follow-up scheduled for
  2026-05-02 — if still absent by then, open an issue at
  [anthropics/claude-code#issues](https://github.com/anthropics/claude-code/issues)
  or a direct PR against `anthropics/claude-plugins-official` if that repo
  accepts community PRs for new external plugins.
- **[claudemarketplaces.com](#claudemarketplacescom)** — third-party
  aggregator; no submission, just wait for the daily GitHub crawl to
  discover our `.claude-plugin/marketplace.json`. Check: `curl -sI https://claudemarketplaces.com/marketplace/vardoger | head -1`
  should return `HTTP/2 200` once listed (was `404` on 2026-04-27). First
  follow-up scheduled for 2026-04-29 — if listed, flip the row to **Live**
  and fill in "Live on"; if still 404 after ~a week, open an issue at
  [mertbuilds/claudemarketplaces.com](https://github.com/mertbuilds/claudemarketplaces.com)
  or use the site's `/feedback` page.

McpMux PR #113 dropped off on 2026-04-24 — merged as
[`495adbc`](https://github.com/mcpmux/mcp-servers/commit/495adbc131a7ea2acd8df29869b391cc2cb05cbe);
row is now **Live**.

If any of the remaining rows flip, update the row's Status / Live on, add
merge notes to the corresponding
[per-marketplace subsection](#per-marketplace-details), and bump "Last
refreshed" at the top of this file in the same commit.

### 2. Not actionable today — revisit only on upstream change

- **Windsurf MCP Store** — re-verified 2026-04-22; still curated, no public
  submission endpoint. Revisit only if Windsurf announces a self-serve flow
  or makes the `windsurf-mcp-registry://` deeplink target third-party
  manifests. The Enterprise internal-registry path is covered by the
  **Official MCP Registry** row in the table above.
- **Codex official directory** — blocked upstream; watch
  `developers.openai.com/codex/plugins/build` for the "Self-serve plugin
  publishing and management are coming soon" banner to disappear.
