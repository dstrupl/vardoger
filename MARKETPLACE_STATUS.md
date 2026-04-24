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

Last refreshed: **2026-04-24** (UTC). Docker MCP Registry unblocked: added a runtime `Dockerfile` + `.dockerignore` at the repo root and a tracked `plugins/docker-mcp/server.yaml` / `README.md`; row flipped from **blocked on Dockerfile** to **Prep complete — awaits 0.3.1 release** so `source.commit` can be pinned to the release tag before opening the PR against `docker/mcp-registry`. Earlier the same day: McpMux [PR #113](https://github.com/mcpmux/mcp-servers/pull/113) merged as [`495adbc`](https://github.com/mcpmux/mcp-servers/commit/495adbc131a7ea2acd8df29869b391cc2cb05cbe) — row flipped to **Live**; vardoger now reaches Cursor, Claude Desktop, VS Code, and Windsurf via the McpMux desktop gateway.

Previous refresh (2026-04-23): addressed @its-mash's review on PR #113 by switching the `VARDOGER_MCP_PLATFORM` input from free-text to a `select` with explicit options (seven supported platforms plus an "Auto-detect (default)" empty-value entry); mirrored the change in our tracked copy at `plugins/mcpmux/vardoger.json`.

Earlier (2026-04-22): ClawHub flipped to **Live (self-served)** the same day as `vardoger-analyze@0.3.0`; Windsurf re-verified (still no public submission); three cross-vendor MCP registry rows added (`modelcontextprotocol/registry`, McpMux, Docker MCP Registry); McpMux PR opened ([mcpmux/mcp-servers#113](https://github.com/mcpmux/mcp-servers/pull/113)) — row flipped to **Submitted**.

| Marketplace                 | Surface                                           | Plugin root           | Status       | Submitted on | Live on | Notes                                                                                                                                 |
| --------------------------- | ------------------------------------------------- | --------------------- | ------------ | ------------ | ------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **PyPI**                    | `pipx install vardoger`                           | (repo root)           | Live         | 2026-04-20   | 2026-04-22 | Current version `0.3.0`. Releases: [v0.1.0](https://github.com/dstrupl/vardoger/releases/tag/v0.1.0) · [v0.2.0](https://github.com/dstrupl/vardoger/releases/tag/v0.2.0) · [v0.2.1](https://github.com/dstrupl/vardoger/releases/tag/v0.2.1) · [v0.2.2](https://github.com/dstrupl/vardoger/releases/tag/v0.2.2) · [v0.3.0](https://github.com/dstrupl/vardoger/releases/tag/v0.3.0). [pypi.org/project/vardoger](https://pypi.org/project/vardoger/). |
| **Cursor Plugin Registry**  | [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish) | `plugins/cursor/`     | Submitted    | 2026-04-20   | —       | Manifest at `plugins/cursor/.cursor-plugin/plugin.json`; `mcp.json` boots via `uvx vardoger mcp`. Logotype URL in the form: `https://raw.githubusercontent.com/dstrupl/vardoger/main/assets/logo.svg`. No public API for review state — check the Cursor publisher dashboard. Last checked 2026-04-22: no reviewer response. |
| **Claude Code Plugins**     | [claude.ai/settings/plugins/submit](https://claude.ai/settings/plugins/submit) | `plugins/claude-code/` | Submitted    | 2026-04-20   | —       | Submitted via the claude.ai form (personal-account path; platform.claude.com is the org-account alternative and feeds the same marketplace). Privacy Policy URL: `https://github.com/dstrupl/vardoger/blob/main/PRIVACY.md`. Platforms selected: Claude Code only (Cowork excluded — no `cowork` adapter and audience is non-developer). Last checked 2026-04-22: no reviewer response. |
| **Codex — custom**          | `codex plugin marketplace add …`                  | `plugins/codex/`      | Live (self-served) | 2026-04-20 | 2026-04-20 | Codex has no central registry for custom marketplaces — our public manifest at `plugins/codex/marketplace.json` *is* the marketplace. Users install it directly with `codex plugin marketplace add https://github.com/dstrupl/vardoger.git --sparse plugins/codex` (or the legacy `codex marketplace add` shim). Nothing to submit; flipped to **Live** on 2026-04-22 after confirming there is no separate submission flow. |
| **Codex — official directory** | (pending self-serve)                           | `plugins/codex/`      | Not started — blocked upstream | — | — | [openai/codex#13712](https://github.com/openai/codex/pull/13712) merged 2026-03-07, adding the curated plugin marketplace infrastructure. Per [developers.openai.com/codex/plugins/build](https://developers.openai.com/codex/plugins/build), "Adding plugins to the official Plugin Directory is coming soon. Self-serve plugin publishing and management are coming soon." Last checked 2026-04-22 — still no self-serve flow. Users install via the custom marketplace row above in the meantime. |
| **GitHub Copilot CLI — custom** | `copilot plugin marketplace add dstrupl/vardoger:plugins/copilot` | `plugins/copilot/` | Live (self-served) | 2026-04-20 | 2026-04-20 | Copilot CLI ships two default marketplaces (`copilot-plugins`, `awesome-copilot`) and lets users register any GitHub repo as an additional custom marketplace — there is no separate central registry to submit to. Our public marketplace manifest at `plugins/copilot/marketplace.json` (plus the plugin manifest at `plugins/copilot/.github/plugin/plugin.json` with a single `analyze` skill) is installable today via `copilot plugin marketplace add dstrupl/vardoger:plugins/copilot` or the one-line alternative `copilot plugin install dstrupl/vardoger:plugins/copilot`. The `awesome-copilot` listing is tracked as a separate row below. Flipped to **Live** on 2026-04-22. |
| **GitHub Copilot CLI — `awesome-copilot`** | [PR #1461](https://github.com/github/awesome-copilot/pull/1461) | `plugins/copilot/` | Submitted | 2026-04-21 | — | PR opened 2026-04-21 as `add-vardoger-analyze-skill`. Initial submission targeted `main`; the `github-actions` bot requested a retarget to the `staged` branch (auto-published to `main`), and the PR was re-pointed at `staged` the same day. Awaiting human review. Last checked 2026-04-22: `reviewDecision=CHANGES_REQUESTED` is the lingering bot review — functionally waiting on a maintainer. |
| **Windsurf MCP Store**      | (no public submission form)                       | `plugins/windsurf/`   | N/A          | —            | —       | Re-verified 2026-04-22 against the [Windsurf MCP docs](https://docs.windsurf.com/windsurf/cascade/mcp) (`llms-full.txt`): the in-product MCP marketplace is still curated ("Official MCPs show up with a blue checkmark, indicating that they are made by the parent service company"), there is no public submission endpoint or PR repo, and the only third-party install paths are (a) manual `~/.codeium/windsurf/mcp_config.json` edit — already documented in `plugins/windsurf/README.md` via `vardoger setup windsurf` — and (b) the Enterprise "Internal MCP Registry" feature, which consumes schemas conforming to [`modelcontextprotocol.io`](https://modelcontextprotocol.io/) (covered by the official MCP Registry row below). Revisit if Windsurf publishes a self-serve submission flow. |
| **Official MCP Registry**   | `mcp-publisher publish` against `registry.modelcontextprotocol.io` | `plugins/mcp-registry/` | Not started — prep complete | — | — | The [MCP Registry preview](https://registry.modelcontextprotocol.io/docs) is the canonical cross-vendor MCP server feed (API-frozen at v0.1 as of 2025-10-24). Listings here are ingested by Docker Desktop's MCP Toolkit, VS Code's MCP picker, Windsurf's enterprise Internal MCP Registry feature, and any host that syncs the feed. Draft `server.json` lives at `plugins/mcp-registry/server.json` (schema `https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json`, name `io.github.dstrupl/vardoger`, `packages[0]` pointing at PyPI `vardoger@0.3.0`). Ownership marker `<!-- mcp-name: io.github.dstrupl/vardoger -->` already added to the repo-root `README.md`, so the next PyPI release will carry it automatically — publishing from the current 0.3.0 wheel requires re-cutting a PyPI release first so the marker ships in the package description. Before `mcp-publisher publish`, re-run `mcp-publisher init` in a scratch dir and diff against the tracked file to catch any `packageArguments` schema drift (see `plugins/mcp-registry/README.md`). |
| **McpMux community registry** | [PR #113](https://github.com/mcpmux/mcp-servers/pull/113) | `plugins/mcpmux/` | Live         | 2026-04-22   | 2026-04-24 | [McpMux](https://mcpmux.com) is a desktop MCP gateway that proxies tools into Cursor, Claude Desktop, VS Code, and Windsurf through one endpoint; one merged PR lands vardoger in every McpMux client. Tracked server definition lives at `plugins/mcpmux/vardoger.json` (schema version `2.1`, stdio transport invoking `vardoger mcp`, categories `developer-tools` / `productivity` / `ai-ml`, `platforms: ["all"]`). PR #113 opened 2026-04-22 against `mcpmux/mcp-servers` from `dstrupl:add-vardoger` with DCO sign-off; `node scripts/validate.js` reports `PASS` + no ID/alias conflicts across the 106-server baseline. 2026-04-23: addressed @its-mash's review (pushed [80e6cb2](https://github.com/mcpmux/mcp-servers/commit/80e6cb2)) by switching `VARDOGER_MCP_PLATFORM` from `text` to `select` with explicit options for each supported platform plus an "Auto-detect (default)" empty-value entry; `npm run validate:all` still reported 106 PASS / 0 FAIL and `npm run check-conflicts` clean. 2026-04-24: @its-mash approved and merged as [`495adbc`](https://github.com/mcpmux/mcp-servers/commit/495adbc131a7ea2acd8df29869b391cc2cb05cbe) at 17:03 UTC. The McpMux bundle refreshes from `main` within ~an hour, so desktop clients pick up the entry automatically from that point. No further maintenance until vardoger ships a breaking MCP-tool or CLI change. |
| **Docker MCP Registry**     | PR to [`docker/mcp-registry`](https://github.com/docker/mcp-registry) | `plugins/docker-mcp/` | Prep complete — awaits 0.3.1 release | — | — | Docker's catalog (surfaces at [hub.docker.com/mcp](https://hub.docker.com/mcp) and inside Docker Desktop's MCP Toolkit) requires a working Docker image. Decision 2026-04-24: let Docker build and sign the image for us (`mcp/vardoger` on Docker Hub) via `task create --category productivity`. Landed the runtime `Dockerfile` at the repo root (multi-stage, non-root UID 1000, builds vardoger from the pinned source commit, stdio `ENTRYPOINT ["vardoger","mcp"]`, expects the caller's host `$HOME` bind-mounted at `/host-home`), plus `.dockerignore`, a tracked `plugins/docker-mcp/server.yaml` (`category: productivity`, one parameterised `home_path` volume, optional `VARDOGER_MCP_PLATFORM` env), and `plugins/docker-mcp/README.md` with the `task wizard` / `task create` / `task validate` / `task build -- --tools` submission steps. Cline history is not accessible from the containerized build (depends on host-OS VS Code globalStorage layout) — documented in both the `server.yaml` description and the README; Cline users should continue to install via `pipx`. Remaining work: (1) cut `vardoger 0.3.1` on PyPI, (2) pin `source.commit` in `server.yaml` to the release tag SHA, (3) run `task validate` + `task build -- --tools vardoger` from a fresh `docker/mcp-registry` clone, (4) open the PR. |
| **Cline MCP Marketplace**   | [issue #1394](https://github.com/cline/mcp-marketplace/issues/1394) | `plugins/cline/` | Submitted | 2026-04-20 | — | Server submission issue `[Server Submission]: vardoger — personalize AI assistants from local history` opened 2026-04-20 at cline/mcp-marketplace. Install guidance for the LLM-driven install flow at `plugins/cline/llms-install.md`; user-facing readme at `plugins/cline/README.md`. Last checked 2026-04-22: no reviewer comments yet. |
| **OpenClaw ClawHub**        | `bunx --bun clawhub publish …` (after `bun clawhub login` — GitHub browser OAuth) | `plugins/openclaw/skills/analyze/` | Live (self-served) — awaits 0.3.1 republish | 2026-04-22 | 2026-04-22 | Published 2026-04-22 as `vardoger-analyze@0.3.0` (publish id `k9796s5r5hk5ea46kxbpwk49dd85axz8`). Verified via `bunx --bun clawhub inspect vardoger-analyze` (owner `dstrupl`, latest `0.3.0`, tag `latest=0.3.0`) and `bunx --bun clawhub search vardoger` (ranked hit). 2026-04-24: added `license: Apache-2.0` to `plugins/openclaw/skills/analyze/SKILL.md` frontmatter so the next publish carries the repo license (the initial 0.3.0 submission declared no `license:` field and ClawHub defaulted to MIT-0). Republish / refresh with `bunx --bun clawhub publish plugins/openclaw/skills/analyze/ --slug vardoger-analyze --name "vardoger — Analyze History" --version <next> --tags latest --changelog "<note>"` after bumping the skill's `version:` to match. |

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
the relevant table row above for the full context.

### 1. Poll reviewer queues (re-verify before other work)

- **Cursor Plugin Registry** — no public review API; log into the
  [Cursor publisher dashboard](https://cursor.com/marketplace/publish) and
  check `plugins/cursor/` submission state. Last checked 2026-04-22.
- **Claude Code Plugins** — no public review API; check
  [claude.ai/settings/plugins](https://claude.ai/settings/plugins). Last
  checked 2026-04-22.
- **`awesome-copilot` PR #1461** —
  `gh pr view github/awesome-copilot#1461 --json state,reviewDecision,comments`.
  Functionally waiting on a human maintainer; the only lingering review is the
  bot's `CHANGES_REQUESTED` that preceded the `staged`-branch retarget.
- **Cline MCP Marketplace issue #1394** —
  `gh issue view cline/mcp-marketplace#1394 --json state,comments`. No
  reviewer comments as of 2026-04-22.

McpMux PR #113 dropped off this list on 2026-04-24 — merged as
[`495adbc`](https://github.com/mcpmux/mcp-servers/commit/495adbc131a7ea2acd8df29869b391cc2cb05cbe);
row is now **Live**.

If any of these flipped, update the row's Status/Live on/Notes and bump
"Last refreshed" at the top of this file in the same commit.

### 2. Ready-to-publish — owner action required

These are prepped and all gated on the same release step: cut `vardoger 0.3.1`
on PyPI. After that, three downstream publishes fan out in parallel.

- **Step 0 — cut `vardoger 0.3.1`.** `version` in `pyproject.toml`,
  `packages[0].version` in `plugins/mcp-registry/server.json`, and the
  `version:` frontmatter in `plugins/openclaw/skills/analyze/SKILL.md` all
  move in lock-step. Tag `v0.3.1` on GitHub; the `publish.yml` workflow
  pushes the wheel to PyPI via trusted publishers. 0.3.1 is what ships the
  `<!-- mcp-name: io.github.dstrupl/vardoger -->` marker in the PyPI
  package description and the explicit `license: Apache-2.0` field in the
  OpenClaw skill.

- **Official MCP Registry (`registry.modelcontextprotocol.io`)** — once
  0.3.1 is on PyPI, from a fresh clone on a shell with a browser:
  1. Install `mcp-publisher` (see `plugins/mcp-registry/README.md`).
  2. Copy `plugins/mcp-registry/server.json` to the repo root (the CLI reads
     from `./server.json`), confirm `packages[0].version` is `0.3.1`, run
     `mcp-publisher init` in a scratch dir and diff against the tracked file
     to catch `packageArguments` schema drift.
  3. `mcp-publisher login github && mcp-publisher publish`.
  4. Verify:
     `curl -s https://registry.modelcontextprotocol.io/v0/servers | jq '.servers[] | select(.name=="io.github.dstrupl/vardoger")'`.
  5. Flip the row to **Live** and tick the Phase 4 checkbox in `PRD.md`.

- **Docker MCP Registry** (`docker/mcp-registry`) — once the v0.3.1 tag
  exists:
  1. Pin `source.commit` in `plugins/docker-mcp/server.yaml` to
     `git rev-parse v0.3.1`.
  2. Smoke-test the image locally:
     `docker build -t mcp/vardoger:dev .` then
     `docker run --rm -i -v "$HOME:/host-home" mcp/vardoger:dev` (stdio).
  3. Fork `docker/mcp-registry`, drop the tracked `server.yaml` at
     `servers/vardoger/server.yaml`, run
     `task validate -- --name vardoger` and `task build -- --tools vardoger`,
     and open the PR using `.github/PULL_REQUEST_TEMPLATE.md`. See
     `plugins/docker-mcp/README.md` for the full walkthrough.

- **ClawHub** — republish the analyze skill so the listing carries the
  explicit Apache-2.0 license (strict parity with the repo):
  `bunx --bun clawhub publish plugins/openclaw/skills/analyze/ --slug vardoger-analyze --name "vardoger — Analyze History" --version 0.3.1 --tags latest --changelog "Add explicit Apache-2.0 license"`.
  Verify with
  `bunx --bun clawhub inspect vardoger-analyze` and flip the row's "Live on"
  date in the row above.

### 3. Not actionable today — revisit only on upstream change

- **Windsurf MCP Store** — re-verified 2026-04-22; still curated, no public
  submission endpoint. Revisit only if Windsurf announces a self-serve flow
  or makes the `windsurf-mcp-registry://` deeplink target third-party
  manifests. The Enterprise internal-registry path is covered by the MCP
  Registry row (item 2).
- **Codex official directory** — blocked upstream; watch
  `developers.openai.com/codex/plugins/build` for the "Self-serve plugin
  publishing and management are coming soon" banner to disappear.
