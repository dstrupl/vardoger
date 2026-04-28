# vardoger — Product Requirements Document

> **Version:** 0.3.1
> **Date:** 2026-04-28
> **Status:** Public beta (Phases 1–3 and 5 shipped; Phase 4 in progress)
>
> **Implementation status legend:**
> - [x] Implemented
> - [ ] Not yet implemented

---

## 1. Overview and Vision

**vardoger** is a cross-platform plugin for AI coding assistants that observes how a developer works — their patterns, preferences, and communication style — and generates personalized system prompt additions that make the assistant better suited to that individual over time.

The name references the Scandinavian folklore concept of a *vardøger*: a spirit that arrives before you, preparing the way. In the same sense, vardoger prepares the AI assistant to anticipate how you work before you even start your next session.

The plugin reads conversation history that already exists on the user's machine, analyzes it locally (no data ever leaves the device), and produces configuration that each supported platform natively understands — making the assistant progressively more attuned to its user.

---

## 2. Problem Statement

AI coding assistants ship with generic system prompts optimized for the average user. They do not learn from repeated interactions. A developer who consistently prefers concise answers still gets verbose explanations. A developer who always works in Python and pytest still gets asked clarifying questions about their stack. A developer who hates emojis still gets them.

Every platform already records conversation history locally. That history is a rich signal about what the user values, how they communicate, what tools and patterns they favor, and what frustrates them. Today, no tool closes the loop: nobody reads that history, extracts behavioral patterns, and feeds them back into the system prompt.

vardoger fills that gap.

---

## 3. Target Platforms

vardoger targets the leading AI coding environments:

| Platform | Vendor | Distribution Model |
|---|---|---|
| **Cursor** | Anysphere | Cursor Plugin Registry (MCP server) + `pipx install` direct-install fallback |
| **Claude Code** | Anthropic | Claude Code plugin marketplace (GitHub-based) |
| **OpenAI Codex** | OpenAI | Codex plugin directory + custom marketplaces |
| **OpenClaw** | OpenClaw (open-source) | ClawHub skill registry + local skill directories |
| **GitHub Copilot CLI** | GitHub / Microsoft | Copilot CLI plugin marketplace (custom sources) + `pipx install` direct-install fallback |
| **Windsurf** | Codeium / Cognition | Windsurf MCP Store (editorial) + per-user `mcp_config.json` install snippet |
| **Cline** | Cline (open-source VS Code extension) | Cline MCP Marketplace (issue submission) + `pipx install` direct-install fallback |

Each platform has its own conversation storage format, system prompt contribution mechanism, and plugin distribution channel. vardoger must integrate natively with all of them.

---

## 4. Core Capabilities

### 4.1 Read Conversation History [x]

vardoger must be able to discover and parse all locally stored conversation history for the active user across supported platforms (Cursor, Claude Code, OpenAI Codex, OpenClaw, GitHub Copilot CLI, Windsurf, Cline). This is read-only access to files already on disk — no network calls, no API integrations, no platform authentication required.

### 4.2 Analyze Patterns Locally [x]

Using AI capabilities available on the user's machine (the host platform's own model access, or a local model), vardoger analyzes conversation history to extract behavioral patterns. The analysis algorithm is explicitly deferred to a future phase (see Section 8), but the infrastructure to invoke it must be in place.

> **Status:** Implemented via skill-driven two-stage pipeline. The `prepare` command batches conversations and provides summarization/synthesis prompts. The host AI model performs the actual analysis. The `write` command stores the result.

### 4.3 Generate System Prompt Additions [x]

Based on the analysis, vardoger produces a text artifact — a set of instructions, preferences, and behavioral guidance — formatted as a valid system prompt addition for each target platform.

> **Status:** Implemented. The synthesis prompt guides the host model to produce structured, actionable prompt additions organized by category (communication, technical stack, workflow, coding style, things to avoid).

### 4.4 Deliver via Platform-Native Mechanisms [x]

The generated prompt addition is written to the location each platform natively reads, so it takes effect without any manual intervention from the user. The exact delivery mechanism per platform is detailed in Section 5.

### 4.5 Incremental Processing [x]

vardoger must maintain a lightweight checkpoint record of which conversations have already been processed. On subsequent runs, only new or updated conversations are read and analyzed. This avoids redundant work, speeds up repeated invocations, and provides a stable foundation for continuous refinement.

The checkpoint store must:
- Record per-conversation identifiers (session ID, file path, or content hash) and the timestamp of last processing
- Be platform-aware — each platform adapter manages its own checkpoint namespace
- Live locally alongside other vardoger state (e.g., `~/.vardoger/checkpoints/` or a single `~/.vardoger/state.json`)
- Be resilient to missing or corrupt state — a missing checkpoint simply means "reprocess everything"
- Support a `--full` / `--force` flag to bypass checkpoints and reprocess all history on demand

---

## 5. Platform Integration Details

### 5.1 Cursor [x]

#### Conversation History Storage [x]

| Source | Location | Format |
|---|---|---|
| Agent transcripts | `~/.cursor/projects/<workspace-slug>/agent-transcripts/<uuid>/<uuid>.jsonl` | JSONL — one JSON object per line; fields include `role` (`user` / `assistant`) and `message` payload (including tool calls) | [x] |
| Chat history | `~/.cursor/chats/<hash>/<uuid>/store.db` | SQLite database | [ ] |
| Code tracking | `~/.cursor/ai-tracking/ai-code-tracking.db` | SQLite database | [ ] |

**Primary source for Phase 1:** Agent transcript JSONL files. These are the richest, most structured, and most accessible records of user-assistant interaction.

**Discovery:** Enumerate directories under `~/.cursor/projects/` to find all workspace slugs, then walk `agent-transcripts/` within each.

#### System Prompt Contribution [x]

| Mechanism | Scope | Path |
|---|---|---|
| Project rules | Per-project | `.cursor/rules/*.md` (supports YAML frontmatter: `description`, `globs`, `alwaysApply`) |
| AGENTS.md | Per-project | `AGENTS.md` at project root or nested directories |
| User rules | Global (all projects) | Cursor Settings UI |

**vardoger target:** Write a `.cursor/rules/vardoger.md` file with `alwaysApply: true` in each project, or contribute a global user-level rule. The project-level approach is preferred because it is file-based and scriptable.

> **Status:** Implemented — writes `.cursor/rules/vardoger.md` with `alwaysApply: true` frontmatter.

#### Distribution

Cursor is VS Code-based. Extensions are published to the **Visual Studio Marketplace** as standard VSIX packages. There is no separate Cursor-specific marketplace.

Additionally, Cursor supports **MCP servers** configured via `~/.cursor/mcp.json`. vardoger can expose analysis capabilities as MCP tools alongside or instead of a VS Code extension.

**Recommended approach:** Ship as an MCP server (configured in `mcp.json`) that exposes vardoger commands as tools the agent can invoke. This aligns with Cursor's AI-native plugin model better than a traditional VS Code extension. Install via `pipx install vardoger && vardoger setup cursor`.

> **Status:** [x] MCP server implemented (stdio transport) with the `vardoger_personalize` entry-point tool plus implementation tools `vardoger_status`, `vardoger_prepare`, `vardoger_synthesize_prompt`, `vardoger_write`, `vardoger_preview`, `vardoger_feedback`, and `vardoger_compare`. The server is platform-agnostic — every tool accepts a `platform` argument (or reads `VARDOGER_MCP_PLATFORM`) and routes to the correct per-platform history reader and writer, so the same server is reused by the Cursor, Claude Code, Codex, OpenClaw, Copilot CLI, Windsurf, and Cline installs. Cursor Plugin Registry publishing tracked under Phase 4; see [`MARKETPLACE_STATUS.md`](./MARKETPLACE_STATUS.md).

---

### 5.2 Claude Code [x]

#### Conversation History Storage [x]

| Source | Location | Format |
|---|---|---|
| Session transcripts | `~/.claude/projects/<encoded-path>/<session-uuid>.jsonl` | JSONL — each line has `type` (`user`, `assistant`, `permission-mode`, `file-history-snapshot`), `message` payload, `sessionId`, `cwd`, `version` |
| Session index | `~/.claude/projects/<path>/sessions-index.json` | JSON — `entries[]` with `sessionId`, `fullPath`, summary, `messageCount`, git branch |
| Prompt history | `~/.claude/history.jsonl` | JSONL — one object per line with `display` (user input), `timestamp`, `project` |

**Primary source for Phase 1:** Per-project session JSONL files under `~/.claude/projects/`. The `sessions-index.json` provides a useful manifest for discovery without parsing every transcript.

**Discovery:** Enumerate directories under `~/.claude/projects/`. Each directory name is a dash-encoded absolute path (e.g., `-Users-dastrupl-work-myproject`). Use `sessions-index.json` when present to identify sessions, fall back to globbing `*.jsonl`.

**Path encoding:** The encoded path uses dashes as separators, with leading slash replaced by a dash. Example: `/Users/dastrupl/myproject` becomes `-Users-dastrupl-myproject`.

#### System Prompt Contribution

| Mechanism | Scope | Path |
|---|---|---|
| Project CLAUDE.md | Per-project (team-shareable) | `./CLAUDE.md` or `./.claude/CLAUDE.md` |
| User CLAUDE.md | Global (all projects) | `~/.claude/CLAUDE.md` |
| Local CLAUDE.md | Per-project (private) | `./CLAUDE.local.md` (gitignored) |
| Modular rules | Per-project | `.claude/rules/**/*.md` (optional YAML `paths:` frontmatter) |
| User rules | Global | `~/.claude/rules/*.md` |
| CLI flag | Per-session | `--append-system-prompt` |

**Important:** CLAUDE.md content is delivered as a **user message after the system prompt**, not as part of the literal system prompt. This still effectively guides model behavior.

**vardoger target:** Write to `~/.claude/rules/vardoger.md` for global personalization, or `.claude/rules/vardoger.md` per project. The modular rules approach is cleanest — it avoids modifying the user's hand-written CLAUDE.md files.

> **Status:** Implemented — writes to `~/.claude/rules/vardoger.md` (global) or `<project>/.claude/rules/vardoger.md` (project scope).

#### Distribution

Claude Code has a **first-class plugin system**:

- **Manifest:** `.claude-plugin/plugin.json`
- **Marketplace:** `anthropics/claude-plugins-official` GitHub repository
- **CLI:** `claude plugin install|uninstall|enable|disable|update`
- **Scopes:** user, project, local, managed
- **Bundled capabilities:** skills, hooks, MCP servers, agents, commands

Plugins are git repositories. Installation clones into `~/.claude/plugins/cache/`. The official marketplace is a curated GitHub repo that indexes available plugins.

**Recommended approach:** Ship vardoger as a Claude Code plugin with:
- A **skill** (`skills/analyze/SKILL.md`) that users invoke to trigger analysis
- A **hook** on `SessionStart` to check if the prompt addition is stale and suggest refresh
- Generated output written to `~/.claude/rules/vardoger.md` or `.claude/rules/vardoger.md`

> **Status:** [x] Plugin manifest and analyze skill implemented. [x] SessionStart hook for staleness check. Marketplace publishing deferred to Phase 4.

---

### 5.3 OpenAI Codex [x]

#### Conversation History Storage [x]

| Source | Location | Format |
|---|---|---|
| Session rollouts | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` | JSONL — organized by date, one file per rollout/session |
| History | `~/.codex/history.jsonl` | JSONL — persistence controlled by `[history]` config |
| State | `~/.codex/state_*.sqlite` | SQLite |

**Primary source for Phase 1:** Session rollout JSONL files under `~/.codex/sessions/`. The date-based directory structure makes it straightforward to scope analysis to recent activity.

**Discovery:** Walk the `~/.codex/sessions/` directory tree. Files are organized as `YYYY/MM/DD/rollout-*.jsonl`.

#### System Prompt Contribution

| Mechanism | Scope | Path |
|---|---|---|
| Global AGENTS.md | All projects | `~/.codex/AGENTS.md` (or `AGENTS.override.md`) |
| Project AGENTS.md | Per-project | `AGENTS.md` / `AGENTS.override.md` at project root, concatenated root-to-cwd |
| Fallback filenames | Per-project | Configured via `project_doc_fallback_filenames` in `config.toml` |

**Merge behavior:** Files are concatenated from the global level down to the current working directory. Only one file per directory level is loaded (first non-empty from: `AGENTS.override.md`, then `AGENTS.md`, then fallbacks). Total size capped at `project_doc_max_bytes` (default 32 KiB).

**vardoger target:** Write to `~/.codex/AGENTS.md` for global personalization (appending a vardoger section), or maintain a separate file referenced via `project_doc_fallback_filenames`. The global approach is simplest for user-wide personalization.

> **Status:** Implemented — writes fenced `<!-- vardoger:start/end -->` section to `~/.codex/AGENTS.md` with idempotent replacement.

#### Distribution

Codex has a plugin system similar in structure to Claude Code:

- **Manifest:** `.codex-plugin/plugin.json`
- **Marketplace:** Official curated directory + custom marketplace JSON
- **CLI:** `/plugins` in TUI, `@` to target skills
- **Bundled capabilities:** skills, MCP servers, app integrations
- **Local marketplaces:** `$REPO_ROOT/.agents/plugins/marketplace.json` or `~/.agents/plugins/marketplace.json`

Self-serve publishing to the official directory is listed as "coming soon."

**Recommended approach:** Ship vardoger as a Codex plugin with:
- A **skill** for on-demand analysis
- Generated output written to `~/.codex/AGENTS.md` (or a vardoger-specific section within it)

> **Status:** [x] Plugin manifest and analyze skill implemented. Marketplace publishing deferred to Phase 4.

---

### 5.4 OpenClaw [x]

#### Conversation History Storage

| Source | Location | Format |
|---|---|---|
| Session transcripts | `~/.openclaw/agents/<agentId>/sessions/<channel>_<id>.jsonl` | JSONL — one message per line; fields include `id`, `parentId`, `role` (`user` / `assistant` / `system` / `tool`), `content`, `timestamp` (Unix seconds), `metadata` (userId, platform, model, token counts) |

**Primary source:** Per-agent session JSONL files under `~/.openclaw/agents/`. The format is flat (no nested content blocks), making it the simplest of all supported platforms.

**Discovery:** Walk `~/.openclaw/agents/` to find agent IDs, then enumerate `sessions/*.jsonl` within each.

#### System Prompt Contribution

OpenClaw uses a **skill system** with SKILL.md files that get injected into the agent's system prompt. Skills are discovered from:

| Mechanism | Scope | Path |
|---|---|---|
| Workspace skills | Per-project | `./skills/<name>/SKILL.md` |
| User skills | Global (all agents) | `~/.openclaw/skills/<name>/SKILL.md` |
| Bundled skills | Built-in | Shipped with OpenClaw |

**vardoger target:** Write a `~/.openclaw/skills/vardoger-personalization/SKILL.md` containing the generated personalization as a skill that loads on every session. For per-project scope, write to `./skills/vardoger-personalization/SKILL.md`.

#### Distribution

OpenClaw has a skill registry called **ClawHub**:

- **Install:** `clawhub install <skill-slug>`
- **Update:** `clawhub update --all`
- **Local skills:** Placed directly in `~/.openclaw/skills/`
- **MCP support:** Configured in `~/.config/openclaw/openclaw.json5` (stdio and SSE modes)

**Recommended approach:** Ship vardoger as an OpenClaw skill with:
- An **analysis skill** (`~/.openclaw/skills/vardoger/SKILL.md`) that users invoke to trigger analysis
- Generated output written as a separate **personalization skill** (`~/.openclaw/skills/vardoger-personalization/SKILL.md`)

Install via `pipx install vardoger && vardoger setup openclaw`. ClawHub publishing deferred to Phase 4.

---

### 5.5 GitHub Copilot CLI [x]

#### Conversation History Storage [x]

| Source | Location | Format |
|---|---|---|
| CLI session state | `~/.copilot/session-state/*.jsonl` | JSONL — one event per line capturing user turns, assistant turns, and tool invocations from `copilot` CLI sessions |

**Primary source for Phase 5:** Copilot CLI session-state JSONL files. VS Code Copilot Chat history is stored in opaque workspace storage and is excluded from Phase 5.

**Discovery:** Enumerate `~/.copilot/session-state/*.jsonl`.

#### System Prompt Contribution [x]

| Mechanism | Scope | Path |
|---|---|---|
| Global instructions | All projects | `~/.copilot/copilot-instructions.md` |
| Project instructions | Per-project | `<project>/.github/copilot-instructions.md` |

**vardoger target:** Write a fenced `<!-- vardoger:start --> … <!-- vardoger:end -->` block into the appropriate instructions file, leaving any user-authored content above/below the block untouched. Global is the default; project scope is selected via `--scope project` on the CLI or the `scope` argument on the MCP tools.

> **Status:** Implemented — `src/vardoger/writers/copilot.py` manages the fenced section idempotently in both scopes.

#### Distribution

Copilot CLI supports registering third-party plugin marketplaces via `copilot plugin marketplace add <source>`.

**Recommended approach:** Ship vardoger as a Copilot CLI plugin exposing an `analyze` skill, with generated output written via `vardoger write --platform copilot`.

- Public marketplace manifest: `plugins/copilot/marketplace.json`
- Plugin manifest: `plugins/copilot/.github/plugin/plugin.json`
- One-line install: `copilot plugin marketplace add dstrupl/vardoger:plugins/copilot`

> **Status:** [x] Plugin manifest and analyze skill implemented; marketplace submission tracked in [`MARKETPLACE_STATUS.md`](./MARKETPLACE_STATUS.md).

---

### 5.6 Windsurf [x]

#### Conversation History Storage [x]

| Source | Location | Format |
|---|---|---|
| Cascade transcripts | `~/.codeium/windsurf/**/*.jsonl` | JSONL — one message/event per line |

**Primary source for Phase 5:** Windsurf's on-disk Cascade conversation JSONL files. vardoger walks the tree recursively to tolerate Windsurf's evolving subdirectory layout.

#### System Prompt Contribution [x]

| Mechanism | Scope | Path |
|---|---|---|
| Global memories | All projects | `~/.codeium/windsurf/memories/global_rules.md` (fenced `<!-- vardoger:start/end -->` section) |
| Project rules | Per-project | `<project>/.windsurf/rules/vardoger.md` (dedicated file) |

**vardoger target:** Default to the global scope (fenced section in `global_rules.md`). Project scope writes a standalone file under `.windsurf/rules/`.

> **Status:** Implemented — `src/vardoger/writers/windsurf.py` handles both scopes.

#### Distribution

Windsurf's in-product MCP Store is currently editorial with no public submission form.

**Recommended approach:** Ship an install snippet for `mcp_config.json` that wires vardoger as an MCP server (`VARDOGER_MCP_PLATFORM=windsurf`), plus a `vardoger setup windsurf` helper that records the install location in the checkpoint store. Revisit marketplace submission if Windsurf opens a self-serve flow.

> **Status:** [x] `plugins/windsurf/README.md` contains the install snippet; `vardoger setup windsurf` registers the integration locally.

---

### 5.7 Cline [x]

#### Conversation History Storage [x]

| Source | Location | Format |
|---|---|---|
| Cline task transcripts | VS Code `globalStorage/saoudrizwan.claude-dev/tasks/<task-id>/api_conversation_history.json` | JSON — per-task conversation blob with user/assistant turns and tool calls |

**Primary source for Phase 5:** Cline's per-task `api_conversation_history.json`. The adapter resolves the VS Code `globalStorage` root across macOS/Linux/Windows.

#### System Prompt Contribution [x]

| Mechanism | Scope | Path |
|---|---|---|
| Project `.clinerules/` directory | Per-project | `<project>/.clinerules/vardoger.md` (dedicated file) |
| Project `.clinerules` file | Per-project | `<project>/.clinerules` (fenced `<!-- vardoger:start/end -->` section) |

**vardoger target:** Project scope only — Cline does not currently expose a stable global-rules mechanism that is safe to write to. The writer detects whether `.clinerules` is a directory or a file and chooses the corresponding delivery automatically.

> **Status:** Implemented — `src/vardoger/writers/cline.py` with tests covering both layouts.

#### Distribution

Cline publishes third-party servers through the Cline MCP Marketplace (GitHub-issue submission). Submissions require a brief server description, a link to an `llms-install.md` install guide, and a logo.

**Recommended approach:** Ship an `llms-install.md` that an LLM-driven install flow can follow, plus a user-facing README.

- Install guide: `plugins/cline/llms-install.md`
- User-facing readme: `plugins/cline/README.md`

> **Status:** [x] Install guide and README implemented; marketplace submission tracked in [`MARKETPLACE_STATUS.md`](./MARKETPLACE_STATUS.md).

---

## 6. Architecture Constraints

### 6.1 Local-Only Processing [x]

All conversation history reading and analysis happens exclusively on the user's machine. No data is transmitted to any external service. This is a non-negotiable architectural constraint, not a preference.

**Rationale:** Conversation history contains proprietary code, internal discussions, credentials that were accidentally pasted, and other sensitive material. Users must be able to trust that vardoger never exfiltrates this data.

### 6.2 AI Model Access [x]

vardoger needs AI capabilities for the analysis phase. Since no cloud service is used, the analysis must run through one of:

1. **Host platform's model access** — Use the same AI model the coding assistant already has access to (e.g., invoke the assistant itself to analyze its own history via a skill or tool call)
2. **Local model** — Use a locally running model (e.g., via Ollama, llama.cpp, or similar)
3. **User-configured API** — Allow the user to point at their own API key for a model provider (the key and calls are the user's own; vardoger does not intermediate)

> **Decision:** Option 1 (host platform model access). The `prepare` command provides batched conversation data with summarization/synthesis prompts. The host assistant performs the analysis using its own model. Zero additional setup required.

### 6.3 Idempotent Output [x]

vardoger must be able to re-run analysis and regenerate prompt additions without accumulating stale or duplicate content. Each run produces a complete replacement for the vardoger-managed section of the prompt configuration.

### 6.4 Non-Destructive Integration [x]

vardoger must never modify user-authored configuration files. It writes only to files it owns (e.g., `vardoger.md` in a rules directory) or to clearly demarcated sections within shared files (e.g., a `<!-- vardoger:start -->` / `<!-- vardoger:end -->` block in AGENTS.md).

### 6.5 Cross-Platform Portability [x]

The core analysis logic must be shared across all platform integrations. Platform-specific code should be limited to:
- History discovery and parsing (adapters per platform)
- Prompt output formatting and delivery (writers per platform)
- Plugin packaging and distribution

---

## 7. Phasing

### Phase 1 — Foundation: Read and Contribute [x]

**Goal:** Ship a working plugin on every supported platform that can read conversation history and write a (placeholder) system prompt addition.

**Deliverables:**
- [x] History reader adapters for Cursor, Claude Code, and Codex (JSONL parsers)
- [x] History reader adapter for OpenClaw (JSONL parser)
- [ ] ~~History reader adapters for SQLite sources (Cursor chat DB, Codex state DB)~~ — **Deferred.** Cursor SQLite stores contain non-agent UI state in undocumented formats; Codex SQLite indexes the same JSONL files. JSONL provides cleaner data.
- [x] A unified internal representation of conversation data
- [x] Platform-native prompt writers that produce valid configuration files
- [x] `vardoger setup` CLI command for post-install platform registration (Cursor MCP, Claude Code plugin dir, Codex marketplace.json)
- [x] Distribution via `pipx install vardoger` verified; `vardoger_personalize` MCP entry-point tool guides Cursor agent through the analysis flow
- [x] A placeholder analysis step that produces a minimal, hard-coded prompt addition (proving the pipeline works end-to-end)
- [x] Local plugin install for Cursor (MCP), Claude Code, and Codex
- [x] Local skill install for OpenClaw

**Success criteria:** A user can install vardoger via `pipx install vardoger`, run `vardoger setup <platform>`, and see a vardoger-authored rule file appear in the correct location — no marketplace required.

> **Status:** Complete for Cursor, Claude Code, Codex, and OpenClaw. Marketplace publishing deferred to Phase 4 (after limited beta).

### Phase 2 — Intelligence: AI-Powered Analysis [x]

**Goal:** Replace the placeholder analysis with real AI-driven pattern extraction.

**Deliverables:**
- [x] Checkpoint store that tracks processed conversations to enable incremental runs (see 4.5)
- [x] Analysis pipeline that processes conversation history through an AI model
- [x] Pattern categories: communication preferences, technical stack, workflow habits, pain points, coding style
- [x] Prompt generation that translates extracted patterns into effective system prompt instructions
- [x] Configurable analysis scope (last N days, specific projects, all history)

**Success criteria:** The generated prompt addition measurably changes assistant behavior in ways the user recognizes as personalized.

> **Status:** Implemented via two-stage skill-driven pipeline (prepare/summarize/synthesize/write). Prompts define five pattern categories. Host AI model performs all reasoning.

### Phase 3 — Refinement Loop [x]

**Goal:** Make personalization continuous and self-improving.

**Deliverables:**
- [x] Staleness detection and automatic refresh suggestions
- [x] User feedback mechanism (accept/reject/edit generated rules) — `vardoger feedback accept|reject` with auto-revert, edit detection via bullet-level diffs fed back into the synthesis prompt
- [x] Confidence scoring for extracted patterns — synthesis now emits YAML frontmatter per-rule (`high`/`medium`/`low`); low-confidence rules are marked `(tentative)` in the written output
- [x] A/B style comparison (before/after personalization quality) — `vardoger compare` buckets conversations around the latest generation and reports correction/satisfaction/emoji/restart heuristics

**Success criteria:** The system improves its personalization over time without requiring manual intervention.

### Phase 4 — Marketplace Publishing (in progress)

**Goal:** Publish vardoger to the official plugin marketplaces after validating through limited beta.

**Deliverables:**
- [x] PyPI publishing for `pip install vardoger` / `pipx install vardoger` (current release: 0.3.1)
- [ ] Plugin packaging and marketplace submission for Cursor Plugin Registry — **submitted, awaiting review** (`plugins/cursor/`)
- [ ] Plugin packaging and marketplace submission for Claude Code (custom marketplace + official directory) — **custom marketplace live (self-served)** via `.claude-plugin/marketplace.json` at the repo root (users install with `/plugin marketplace add dstrupl/vardoger` → `/plugin install vardoger@vardoger`, pointing at `plugins/claude-code/` via a `./plugins/claude-code` relative source — the same pattern Anthropic's own official-catalog plugins use); **official directory still submitted, awaiting catalog merge** — the [claude.ai plugin-submissions dashboard](https://claude.ai/settings/plugins/submissions) shows a **Published** badge (submitted 2026-04-20), but `anthropics/claude-plugins-official/.claude-plugin/marketplace.json` (the public catalog Claude Code clients read) does not yet contain vardoger as of 2026-04-27. The "Published" badge is tier-1 validation only; the tier-2 merge into the public catalog is a separate step with no documented SLA.
- [ ] Plugin packaging and marketplace submission for Codex (custom marketplace + official directory) — **custom marketplace live (self-served)** via `plugins/codex/marketplace.json` (Codex has no central registry for custom marketplaces — users install directly via `codex plugin marketplace add …`); **official directory blocked upstream** — [openai/codex#13712](https://github.com/openai/codex/pull/13712) merged 2026-03-07, but OpenAI's build-plugins docs still say "Self-serve plugin publishing and management are coming soon" as of 2026-04-22
- [x] Skill publishing to ClawHub for OpenClaw — **live (self-served)** as [`vardoger-analyze@0.3.1`](https://clawhub.ai/skills/vardoger-analyze) (originally published 2026-04-22 as 0.3.0 with publish id `k9796s5r5hk5ea46kxbpwk49dd85axz8`; republished 2026-04-24 as 0.3.1 with publish id `k97ak6n0cc882ajv2x9tb9s7gs85ekp4` so the listing carries an explicit `license: Apache-2.0` matching the repo).
- [x] Plugin packaging and marketplace submission for GitHub Copilot CLI — **custom marketplace live (self-served)** via `plugins/copilot/marketplace.json` (Copilot CLI has no central registry for custom marketplaces — users install directly via `copilot plugin marketplace add dstrupl/vardoger:plugins/copilot`); **`awesome-copilot` live** as [`vardoger-analyze`](https://github.com/github/awesome-copilot/blob/main/skills/vardoger-analyze/SKILL.md) ([PR #1461](https://github.com/github/awesome-copilot/pull/1461) merged 2026-04-28 by [`aaronpowell`](https://github.com/aaronpowell) into `staged` as [`2f4f41b8`](https://github.com/github/awesome-copilot/commit/2f4f41b8bdeae0a96a4370f9d77358eafec4fe8f); auto-published to `main`, installable today via `gh skills install github/awesome-copilot vardoger-analyze`)
- [ ] Windsurf MCP Store listing — **N/A today** (re-verified 2026-04-22; no public submission form, in-product marketplace is curated). The Enterprise "Internal MCP Registry" path is covered by the official MCP Registry row below.
- [ ] Cline MCP Marketplace submission — **submitted, awaiting review** ([issue #1394](https://github.com/cline/mcp-marketplace/issues/1394) opened 2026-04-20)
- [x] Official MCP Registry submission (`registry.modelcontextprotocol.io`) — **Live** (2026-04-24) as [`io.github.dstrupl/vardoger@0.3.1`](https://registry.modelcontextprotocol.io/v0/servers?search=vardoger). Published via `mcp-publisher publish` after GitHub OAuth device-flow login as `dstrupl`; ownership is established by the `<!-- mcp-name: io.github.dstrupl/vardoger -->` marker that 0.3.1 ships inside the PyPI package description. Tracked `server.json` at `plugins/mcp-registry/server.json`; `status=active`, `isLatest=true`, stdio transport pinned to PyPI `vardoger@0.3.1`. Feed is ingested by Docker Desktop, VS Code MCP picker, and Windsurf Enterprise internal registries.
- [x] McpMux community registry submission ([`mcpmux/mcp-servers`](https://github.com/mcpmux/mcp-servers)) — **Live** (2026-04-24). [PR #113](https://github.com/mcpmux/mcp-servers/pull/113) merged as [`495adbc`](https://github.com/mcpmux/mcp-servers/commit/495adbc131a7ea2acd8df29869b391cc2cb05cbe) after addressing reviewer feedback (switched `VARDOGER_MCP_PLATFORM` from `text` to `select` input). Tracked server definition at `plugins/mcpmux/vardoger.json`; McpMux bundles `main` roughly hourly, so Cursor, Claude Desktop, VS Code, and Windsurf desktop clients on the McpMux gateway now pick up vardoger automatically.
- [ ] Docker MCP Registry submission ([`docker/mcp-registry`](https://github.com/docker/mcp-registry)) — **submitted, awaiting review** ([PR #2949](https://github.com/docker/mcp-registry/pull/2949) opened 2026-04-24 from `dstrupl:add-vardoger`). Runtime `Dockerfile` lives at the repo root (multi-stage Python 3.12 slim, non-root UID 1000, builds vardoger from the pinned source commit, stdio `ENTRYPOINT ["vardoger","mcp"]`, expects host `$HOME` bind-mounted at `/host-home`). Tracked `server.yaml` and submission walkthrough at `plugins/docker-mcp/`; `source.commit` pinned to the `v0.3.1` release SHA `1090cf27ee75bec233b78c7234c56d68b30f6651`. Local pre-submit: `go run ./cmd/validate --name vardoger` passed all 11 checks; `go run ./cmd/build --tools vardoger` produced `mcp/vardoger` and discovered 9 tools. Docker will build and sign `mcp/vardoger` on Docker Hub once the PR merges.

Full per-marketplace status (with submission dates and review feedback) lives in [`MARKETPLACE_STATUS.md`](./MARKETPLACE_STATUS.md), which is the single source of truth for Phase 4 progress.

**Prerequisites:** Limited beta with direct installs (`pipx install vardoger && vardoger setup <platform>`) validates the UX and analysis quality across real users.

**Success criteria:** A user can discover and install vardoger through each platform's native marketplace UI.

### Phase 5 — Tier 1 Platform Expansion [x]

**Goal:** Extend vardoger to the three most popular AI coding assistants that are not yet supported. These cover the largest remaining segment of developers for whom local, history-driven personalization makes sense, and each already exposes both a machine-readable local conversation store and a file-based instructions/rules hook that vardoger can write to non-destructively.

**Target platforms (unranked within Tier 1):**

| Platform | Vendor | Rationale |
|---|---|---|
| **GitHub Copilot** | GitHub / Microsoft | Largest absolute install base among AI coding tools (~4.7M paid subscribers, ~20M total users, ~90% Fortune-100 adoption as of early 2026). Well-defined per-user instructions file (`~/.copilot/copilot-instructions.md`) and per-repo file (`.github/copilot-instructions.md`). Local CLI session data lives under `~/.copilot/session-state/`; VS Code chat history lives in workspace storage. |
| **Windsurf** | Codeium / Cognition | ~1M+ users; the strongest Cursor alternative in the AI-native IDE category. Clean, file-based rules model: `global_rules.md` for user-wide personalization and `.windsurf/rules/*.md` per workspace. Cascade memories and per-workspace conversation data are already stored locally. |
| **Cline** | Cline (open-source VS Code extension) | ~5M VS Code installs and ~58k GitHub stars as of 2026 — the largest open-source agent by adoption. Conversation history stored as JSON per-task under `globalStorage/saoudrizwan.claude-dev/tasks/<task-id>/`. Rules hook: `.clinerules`. Adding a Cline adapter also makes a future port to its downstream forks (Roo Code, Kilo Code) near-trivial, which is captured as a follow-on in Phase 6 rather than here. |

**Deliverables:**

- [x] History reader adapter per platform (`src/vardoger/history/<platform>.py`)
- [x] Platform-native prompt writer per platform (`src/vardoger/writers/<platform>.py`) with fenced, idempotent output analogous to the existing Codex `AGENTS.md` writer
- [x] `vardoger setup <platform>` subcommand per platform, covering install-time registration where required
- [x] Checkpoint-store namespace per platform, consistent with the existing per-platform scheme in `~/.vardoger/state.json`
- [x] Tests mirroring existing adapter/writer coverage and respecting the 80% combined-coverage floor
- [x] Updates to `README.md`, `PRIVACY.md` (paths read and written), and `SECURITY.md` (scope of the new adapters/writers)

**Prerequisites:**

Phases 2 and 3 must be complete (they are). Phase 4 (marketplace publishing for the original four platforms) does not need to block Phase 5; the two tracks can proceed in parallel, since Phase 5 ships additional adapters/writers through the same `pipx install vardoger && vardoger setup <platform>` flow that Phase 1 established.

**Success criteria:**

A user on any Tier 1 platform can run `pipx install vardoger && vardoger setup <platform>` and observe a vardoger-authored rule/instructions file appear in the platform's native location, with all conversation-history reading and analysis remaining strictly local.

**Explicitly out of scope for Phase 5:**

- **Tier 2 platforms** (Roo Code, Kilo Code, Zed, Aider) — tracked for a later phase. Roo Code and Kilo Code are expected to be near-mechanical extensions of the Cline adapter; Zed already recognises several rules filenames vardoger emits for other platforms.
- **Platforms whose history storage or instructions mechanism is still in flux** as of early 2026 (Gemini CLI, Qwen Code, Continue.dev, JetBrains Junie, Amazon Q Developer, Block Goose, TRAE, OpenHands, Sourcegraph Cody, Plandex). These are revisited once their on-disk contracts stabilise.
- **Marketplace / extension-store publishing for Tier 1 platforms** — Phase 5 targets only the direct-install flow (`pipx install vardoger`), mirroring the Phase 1 success criterion. Marketplace submission for these platforms is a separate follow-on.

---

## 8. Non-Goals and Out of Scope

The following are explicitly deferred or excluded:

| Item | Reason |
|---|---|
| **Analysis algorithm design** | Phase 2 (complete). Phase 1 proved the plumbing; Phase 2 added the intelligence. |
| **Cloud processing service** | Architectural constraint. All processing is local. |
| **Real-time conversation monitoring** | vardoger operates on historical data, not live streams. It runs on-demand or on session start, not continuously. |
| **Cross-platform history merging** | If a user uses both Cursor and Claude Code, each platform's history is analyzed independently. Merging signals across tools is a future consideration. |
| **Prompt effectiveness measurement** | Measuring whether the generated prompts actually improve outcomes requires instrumentation that is out of scope for the initial phases. |
| **Team/org-level personalization** | vardoger is for individual users. Team-wide prompt tuning is a different product. |

---

## 9. Open Questions

These decisions are intentionally left open and will be resolved during implementation planning:

### 9.1 Implementation Language — RESOLVED

> **Decision:** Python. Good AI/ML ecosystem for Phase 2, works as MCP server for Cursor, and as CLI invoked by skills in Claude Code and Codex. Package management via uv.

~~The core logic must be packaged for three different plugin ecosystems.~~

### 9.2 MVP Platform Priority — RESOLVED

> **Decision:** All three simultaneously. Proves cross-platform architecture from the start. All three are implemented and working locally.

### 9.3 Prompt Delivery Mode — RESOLVED

> **Decision:** Review-first delivery with an explicit `write` step, plus a safe rollback path. `vardoger_preview` (MCP) or `vardoger prepare --synthesize` surfaces the synthesized prompt before anything is written; `vardoger_write` / `vardoger write` commits it to the platform's native file; `vardoger_feedback reject` / `vardoger feedback reject` auto-reverts to the prior generation.

### 9.4 Analysis Trigger — RESOLVED

> **Decision:** On-demand by default. Users invoke the `vardoger_personalize` MCP tool or the `vardoger` CLI when they want a refresh. Claude Code additionally ships a `SessionStart` hook that surfaces a staleness reminder without auto-running analysis. A scheduled / background refresh path remains out of scope for Phase 5; it would conflict with the local-only, review-first model above.

### 9.5 History Scope Defaults

How much conversation history should vardoger analyze by default?

- Too little: misses patterns
- Too much: slow analysis, stale signals from old behavior
- Likely default: last 30 days, configurable

---

## Appendix A: Glossary

| Term | Definition |
|---|---|
| **System prompt** | The initial instructions given to an AI model before user interaction begins. Controls personality, capabilities, constraints, and behavior. |
| **Prompt addition** | A supplementary block of text appended to or included alongside the system prompt, typically via platform-specific configuration files. |
| **Conversation history** | The recorded transcript of past user-assistant interactions, stored locally by each platform. |
| **History adapter** | A vardoger component that reads and normalizes conversation history from a specific platform's storage format. |
| **Prompt writer** | A vardoger component that formats and delivers the generated prompt addition to a specific platform's configuration mechanism. |
| **Checkpoint store** | A local record of which conversations have already been processed, enabling incremental analysis without reprocessing old data. |
| **JSONL** | JSON Lines format — one complete JSON object per line, used by every currently supported platform for conversation storage. |

## Appendix B: Platform File Paths Summary

```
vardoger state:
  Checkpoints: ~/.vardoger/state.json (per-platform processing watermarks)
  Plugin dirs:  ~/.vardoger/plugins/{cursor,claude-code,codex,openclaw,copilot,windsurf,cline}/ (created by vardoger setup)

Cursor:
  History:  ~/.cursor/projects/<slug>/agent-transcripts/<uuid>/<uuid>.jsonl
  History:  ~/.cursor/chats/<hash>/<uuid>/store.db
  Output:   <project>/.cursor/rules/vardoger.md
  Plugin:   Cursor Plugin Registry or ~/.cursor/mcp.json (MCP server)

Claude Code:
  History:  ~/.claude/projects/<encoded-path>/<session-uuid>.jsonl
  Index:    ~/.claude/projects/<encoded-path>/sessions-index.json
  Output:   ~/.claude/rules/vardoger.md or <project>/.claude/rules/vardoger.md
  Plugin:   claude plugin install (GitHub marketplace)

OpenAI Codex:
  History:  ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl
  History:  ~/.codex/history.jsonl
  Output:   ~/.codex/AGENTS.md (vardoger section) or project AGENTS.md
  Plugin:   /plugins in TUI (official directory or custom marketplace)

OpenClaw:
  History:  ~/.openclaw/agents/<agentId>/sessions/<channel>_<id>.jsonl
  Output:   ~/.openclaw/skills/vardoger-personalization/SKILL.md (global)
            ./skills/vardoger-personalization/SKILL.md (project)
  Skill:    clawhub install (ClawHub registry) or ~/.openclaw/skills/ (local)

GitHub Copilot CLI:
  History:  ~/.copilot/session-state/*.jsonl
  Output:   ~/.copilot/copilot-instructions.md (global, fenced section)
            <project>/.github/copilot-instructions.md (project, fenced section)
  Plugin:   copilot plugin marketplace add dstrupl/vardoger:plugins/copilot

Windsurf:
  History:  ~/.codeium/windsurf/**/*.jsonl
  Output:   ~/.codeium/windsurf/memories/global_rules.md (global, fenced section)
            <project>/.windsurf/rules/vardoger.md (project, dedicated file)
  Plugin:   Windsurf MCP Store (editorial) — install snippet in plugins/windsurf/README.md

Cline:
  History:  <VS Code globalStorage>/saoudrizwan.claude-dev/tasks/<task-id>/api_conversation_history.json
  Output:   <project>/.clinerules/vardoger.md (if .clinerules is a directory)
            <project>/.clinerules (fenced section, if .clinerules is a single file)
  Plugin:   Cline MCP Marketplace — install guide at plugins/cline/llms-install.md
```
