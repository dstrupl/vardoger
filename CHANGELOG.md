# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] — 2026-04-22

### Changed (**breaking** for MCP callers of every non-Cursor writer)

- `vardoger_write` for Cursor no longer silently falls back to
  `Path.cwd() / ".cursor/rules/vardoger.md"` when the caller omits
  `project_path`. Because the Cursor MCP server is launched by Cursor with
  `cwd=$HOME`, the previous behaviour dropped the personalization at
  `~/.cursor/rules/vardoger.md` — a path Cursor never reads — making the
  whole orchestration a silent no-op. New behaviour:
  - Omit `project_path` → vardoger saves the rendered block to a
    convenience copy-source file at
    `~/.vardoger/cursor-user-rules.md` and returns a response that leads
    with that absolute path (Cursor renders it as a cmd+click link, so
    users no longer have to dig for the block inside a collapsed
    "Ran Vardoger Write in vardoger" tool-call card). The same block is
    also inlined in the response as a fallback. The intended destination
    is *Cursor Settings → Rules → User Rules* (the correct home for a
    personalization derived from *global* conversation history); the
    copy-source file is **not** loaded by Cursor — it only exists as a
    copy source. Re-running `vardoger_write` overwrites it with the
    latest generation; `vardoger_feedback reject` rewrites it with the
    previous generation (if any) or deletes it otherwise. If the file
    cannot be written (sandboxed shell, read-only FS, …) vardoger logs a
    warning and falls back to an inline-only response so the user still
    gets the block.
  - Pass `project_path=<workspace>` → vardoger now validates that the
    target (or one of its ancestors) contains a project marker
    (`.git`, a language manifest, `AGENTS.md`, or `.cursor/`) and
    refuses to write otherwise. `write_cursor_rules` raises
    `NotAProjectError` for non-project paths.
  ([#18](https://github.com/dstrupl/vardoger/issues/18))
- Project-scope writes for the six non-Cursor writers (`claude-code`,
  `codex`, `openclaw`, `copilot`, `windsurf`, `cline`) now enforce the
  same project-marker check. Before this release, calling
  `vardoger_write(platform=X, scope="project")` without a `project_path`
  from an MCP server launched with `cwd=$HOME` silently dropped rules
  into locations the target tool does not read (e.g. `~/AGENTS.md` for
  Codex, `~/.github/copilot-instructions.md` for Copilot,
  `~/.windsurf/rules/vardoger.md` for Windsurf, `~/.clinerules/vardoger.md`
  for Cline). The shared `writers/_projects.py` module now centralises
  `PROJECT_MARKERS`, `NotAProjectError`, `find_project_root`, and
  `ensure_project`, and every writer calls `ensure_project(...)` on the
  project-scope branch. Cline validates unconditionally — it has no
  global scope, so even the default no-`project_path` call now refuses
  when cwd is not a project. `vardoger_write` and `vardoger_feedback`
  translate `NotAProjectError` into platform-appropriate actionable
  messages (everyone else is told to retry with `scope=global`; Cline
  is told to pass a real `project_path` because it has no global
  fallback).
  ([#21](https://github.com/dstrupl/vardoger/issues/21))

### Added

- `vardoger_import(paths=[...])` MCP tool: given a list of candidate
  workspace roots, returns the contents of any
  `<workspace>/.cursor/rules/vardoger.md` it finds so the orchestrating
  model can offer to reuse or merge an existing personalization instead
  of regenerating from scratch. The tool deliberately avoids filesystem
  scanning — the agent supplies the candidate list from its own context.
- `vardoger_personalize` orchestration walkthrough updated to (a) call
  `vardoger_import` before generation when other workspaces are known,
  and (b) default the final delivery to User Rules with the project-file
  path as an explicit opt-in.
- "Where the personalization lands" section on every plugin README
  (`cursor`, `claude-code`, `codex`, `openclaw`, `copilot`, `windsurf`,
  `cline`) explaining the refusal behaviour, the marker requirements,
  and the per-platform recovery path.

### Changed

- Bumped plugin manifest versions (`plugins/{cursor,claude-code,codex,copilot}`
  plugin.json, `plugins/copilot/marketplace.json`, and the OpenClaw SKILL
  frontmatter) to `0.3.0` in lock-step with the Python package.

## [0.2.2] — 2026-04-21

### Fixed

- MCP server (`vardoger mcp`) no longer hardcodes the `cursor` platform.
  Every `@mcp.tool` gained an optional `platform` argument covering all
  seven supported platforms (cursor, claude-code, codex, openclaw,
  copilot, windsurf, cline). When omitted, the server resolves the
  default from the `VARDOGER_MCP_PLATFORM` environment variable, falling
  back to `cursor` for backwards compatibility. Tool docstrings no longer
  say "Cursor" by name, so non-Cursor clients (Cline, Windsurf, ...) see
  accurate descriptions in their MCP tool picker. `vardoger_write` and
  `vardoger_feedback` now also accept an optional `scope` argument and
  pick the platform-appropriate default (`project` for Cline, `global`
  otherwise). ([#12](https://github.com/dstrupl/vardoger/issues/12))
- Plugin install snippets for Cline (`plugins/cline/README.md`,
  `plugins/cline/llms-install.md`) and Windsurf (`plugins/windsurf/README.md`)
  now set `VARDOGER_MCP_PLATFORM` in the MCP server `env` block so those
  clients analyze their own history and write to their own rules location.
- MCP `initialize` handshake now reports vardoger's own version in
  `serverInfo.version` instead of the bundled FastMCP SDK version
  (previously `"1.27.0"`). Clients that surface the connected server's
  version in their MCP panel can now trust the number they see.
  ([#13](https://github.com/dstrupl/vardoger/issues/13))

### Changed

- Bumped plugin manifest versions (`plugins/{cursor,claude-code,codex,copilot}`
  plugin.json, `plugins/copilot/marketplace.json`, and the OpenClaw SKILL
  frontmatter) to `0.2.2` in lock-step with the Python package. No
  runtime behavior changed on top of the bug fixes above.

## [0.2.1] — 2026-04-20

### Added

- GitHub Copilot CLI plugin directory at `plugins/copilot/`, with a
  marketplace manifest (`marketplace.json`) and plugin manifest
  (`.github/plugin/plugin.json`) installable via
  `copilot plugin marketplace add dstrupl/vardoger:plugins/copilot` or the
  one-line direct install `copilot plugin install dstrupl/vardoger:plugins/copilot`.
  `scripts/render-skills.py` gained a Copilot target so the shared skill
  template emits `plugins/copilot/skills/analyze/SKILL.md` alongside the
  other platforms.
- Windsurf install reference at `plugins/windsurf/README.md` with a
  ready-to-merge `mcp_config.json` snippet.
- Cline install reference at `plugins/cline/README.md` plus a
  `plugins/cline/llms-install.md` tailored to the Cline MCP marketplace's
  LLM-driven install flow.
- `MARKETPLACE_STATUS.md` (then `docs/marketplace-status.md`) now tracks Copilot CLI (custom + the
  `awesome-copilot` list), Windsurf, and Cline rows, and refreshes the
  PyPI row with the 0.2.0 / 0.2.1 release tags.

### Changed

- Bumped plugin manifest versions (`plugins/{cursor,claude-code,codex,copilot}`
  plugin.json and the OpenClaw SKILL frontmatter) to `0.2.1` in lock-step
  with the Python package.
- `setup_copilot()` docstring and console prose now point users at the new
  Copilot plugin marketplace entry; the existing
  `~/.copilot/copilot-instructions.md` behavior is unchanged, so 0.1.0 and
  0.2.0 users do not need to upgrade.

## [0.2.0] — 2026-04-20

### Added

- Phase 5 Tier 1 platform expansion: GitHub Copilot CLI, Windsurf, and
  Cline are now first-class platforms. Each ships a history adapter
  (`src/vardoger/history/{copilot,windsurf,cline}.py`) that parses the
  platform's native local session storage, a prompt writer
  (`src/vardoger/writers/{copilot,windsurf,cline}.py`) that emits an
  idempotent fenced section (or dedicated file, where the platform
  prefers that) so hand-authored instructions are never overwritten,
  and a `vardoger setup <platform>` flow. Checkpointing, staleness,
  feedback, and A/B quality comparison all treat the three new
  platforms the same as the original four. Project-scope only for
  Cline (it does not define a global rules location).
- `PRIVACY.md` documenting what vardoger reads, writes, and does not
  transmit. Linked from `README.md` and `SECURITY.md`. Needed for the
  Claude Code plugin directory submission ("Privacy Policy URL" is
  required for Anthropic-verified listings).
- Public Codex custom-marketplace manifest at `plugins/codex/marketplace.json`,
  installable with `codex marketplace add https://github.com/dstrupl/vardoger.git --sparse plugins/codex`
  ([openai/codex#17087](https://github.com/openai/codex/pull/17087)).
- Instructions for the new install path in `plugins/codex/README.md`.

### Changed

- Bumped plugin manifest versions (`plugins/{cursor,claude-code,codex}`
  plugin.json and the OpenClaw SKILL frontmatter) to `0.2.0` in lock-step
  with the Python package.
- `analyze.py` now reads its "Generated by vardoger" banner from
  `vardoger.__version__` so future bumps only touch one string.

### Fixed

- `scripts/smoke-test-release.sh` no longer invokes the unsupported
  `vardoger --version`; reports the installed version via `pipx runpip show`.

## [0.1.0] — 2026-04-20

### Added

- Phase 4 marketplace-ready release.
- Plugin manifests for all four platforms carry consistent metadata (`name`,
  `version`, `description`, `author`, `homepage`, `repository`, `license`,
  `keywords`).
- Cursor native plugin layout: `.cursor-plugin/plugin.json` and a self-bootstrapping
  `mcp.json` that launches the CLI via `uvx` with a `pipx run` fallback.
- OpenClaw SKILL frontmatter now matches the ClawHub schema
  (`version`, `metadata.openclaw.requires.bins`, `homepage`).
- Shared analyze-skill template under `plugins/_shared/` with `scripts/render-skills.py`
  to keep the three per-platform `SKILL.md` files in sync.
- Repo-level `SECURITY.md`, `CHANGELOG.md`, and committed `assets/logo.svg`.
- Public `plugins/codex/marketplace.json` so users can install via Codex's
  custom-marketplace flow without cloning the repo.

### Changed

- `Development Status` classifier bumped from `3 - Alpha` to `4 - Beta`.
- README install instructions default to the stable `pipx install vardoger` path;
  the `--pre` / `uvx vardoger@...` flow is kept under "Previous pre-releases."
- PRD Phase 1 checkboxes for OpenClaw history adapter and local skill install
  flipped to match reality.

### Removed

- Stale pre-release wheel and sdist artifacts from `dist/`.

## [0.1.0b3] — 2026-04-17

### Fixed

- Codex plugin registration path and sandbox-aware CLI invocation (#3).
- `prepare` now only checkpoints after the final batch to avoid premature commits.

### Added

- YAML frontmatter emitted in generated `SKILL.md` outputs.

## [0.1.0b2] — 2026-04-17

### Changed

- Pinned `astral-sh/setup-uv` to `v8.1.0` for reproducible CI installs.
- Documented the beta install path (`pipx install --pre vardoger`).
- Bumped CI action versions.

## [0.1.0b1] — 2026-04-17

### Added

- First public beta on PyPI via trusted-publisher release workflow.
- Cross-platform core: Cursor, Claude Code, OpenAI Codex, and OpenClaw.
- Phase 1 — history readers, platform-native prompt writers, `vardoger setup`.
- Phase 2 — skill-driven analysis pipeline (`prepare`/`synthesize`/`write`).
- Phase 3 — staleness detection, feedback accept/reject with auto-revert,
  confidence scoring, and A/B comparison.
- 80% combined test-coverage floor enforced in CI plus `bandit` + `pip-audit`
  security job.
