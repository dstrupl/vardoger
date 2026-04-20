# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `PRIVACY.md` documenting what vardoger reads, writes, and does not
  transmit. Linked from `README.md` and `SECURITY.md`. Needed for the
  Claude Code plugin directory submission ("Privacy Policy URL" is
  required for Anthropic-verified listings).

### Added

- Public Codex custom-marketplace manifest at `plugins/codex/marketplace.json`,
  installable with `codex marketplace add https://github.com/dstrupl/vardoger.git --sparse plugins/codex`
  ([openai/codex#17087](https://github.com/openai/codex/pull/17087)).
- Instructions for the new install path in `plugins/codex/README.md`.

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
