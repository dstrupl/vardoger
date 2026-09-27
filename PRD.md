# vardoger — Product Requirements Document

> **Version:** 0.4.0
> **Date:** 2026-09-27
> **Status:** Public beta (Phases 1–3 and 5 shipped; marketplace and host refresh in progress)
>
> **Implementation status legend:**
> - [x] Implemented
> - [ ] Not yet implemented

---

## 1. Overview and Vision

**vardoger** is a cross-platform plugin for AI coding assistants that observes how a developer works — their patterns, preferences, and communication style — and generates personalized system prompt additions that make the assistant better suited to that individual over time.

The name references the Scandinavian folklore concept of a *vardøger*: a spirit that arrives before you, preparing the way. In the same sense, vardoger prepares the AI assistant to anticipate how you work before you even start your next session.

The plugin reads conversation history that already exists on the user's
machine, asks the selected host assistant to analyze reviewable batches, and
produces configuration that each supported platform natively understands.
Vardoger operates no hosted backend; model-side processing follows the host
assistant's data policy.

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
| **Devin Local / legacy Windsurf** | Cognition | Direct skill + CLI/MCP setup; supported ATIF exports for Devin, legacy Cascade paths for Windsurf |
| **Cline** | Cline (open-source VS Code extension) | `cline/marketplace` pull request + `pipx install` direct-install fallback |

Each platform has its own conversation storage format, system prompt contribution mechanism, and plugin distribution channel. vardoger must integrate natively with all of them.

### 3.1 Current usefulness audit (2026-09-27)

Host-native memory has changed the product landscape. Vardoger should no
longer be positioned as seven independent replacements for native memory.

| Platform | Current value | Direction |
|---|---|---|
| Cursor | Useful with adaptation | Cross-project, user-owned rules remain differentiated; use current `.mdc` delivery and broaden history coverage. |
| Claude Code | Useful | Native memory is repository-scoped; keep global backfill and make output memory-aware. |
| Codex | Low incremental value | Keep a low-maintenance, explicit promote-to-`AGENTS.md` workflow; native Memories cover much of the loop. |
| OpenClaw | Low incremental value | Native memory overlaps strongly; keep the opt-in read-only Gateway path mainly for cross-host compilation and legacy JSONL migration. |
| GitHub Copilot CLI | Low incremental value | Native Memory and Chronicle overlap strongly; retain durable/cross-host export value after fixing current event discovery. |
| Devin Local | High value | Devin does not persist memories; use its documented opt-in ATIF export plus native AGENTS/rules/skills surfaces without inspecting private state. |
| Cline | Useful | Persistent rules and task history exist, but automatic cross-task preference learning does not; global delivery is now implemented. |

The strategic follow-on is Phase 7: compile an auditable profile across host
silos, then project it into portable and host-specific instruction surfaces.

---

## 4. Core Capabilities

### 4.1 Read Conversation History [x]

vardoger must discover and parse conversation history only where the platform exposes a documented or safely supported format. Current direct readers cover Cursor, Claude Code, OpenAI Codex, GitHub Copilot CLI, Devin CLI's user-enabled ATIF exports, legacy OpenClaw JSONL, legacy Windsurf/Cascade, and Cline. Current OpenClaw history is available through an explicit, full-read invocation of the official Gateway CLI; Vardoger never queries its private SQLite tables or accepts Gateway credentials. History access is read-only. Filesystem readers make no network calls; the opt-in OpenClaw reader delegates transport and authentication to the installed OpenClaw CLI.

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
| Project rules | Per-project | `.cursor/rules/*.mdc` (requires YAML frontmatter: `description`, `globs`, `alwaysApply`) |
| AGENTS.md | Per-project | `AGENTS.md` at project root or nested directories |
| User rules | Global (all projects) | Cursor Settings UI |

**vardoger target:** Write a `.cursor/rules/vardoger.mdc` file with `alwaysApply: true` in each project, or contribute a global user-level rule. The project-level approach is preferred because it is file-based and scriptable.

> **Status:** Implemented — writes `.cursor/rules/vardoger.mdc` with valid `description` and `alwaysApply: true` frontmatter. Pre-0.3.3 `vardoger.md` files remain readable for import and feedback continuity, but are never overwritten or deleted during the filename transition.

#### Distribution

Cursor has a first-party plugin marketplace and accepts repository plugins
using either its host-specific manifest or the portable Agent Plugins 1.0 root
manifest. It also supports **MCP servers** configured via `~/.cursor/mcp.json`,
which is Vardoger's direct-install fallback.

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

Codex supports Agent Plugins plus its legacy-compatible package shape:

- **Manifest:** Agent Plugins 1.0 root `plugin.json`; Vardoger 0.4.0 currently
  uses the `.codex-plugin/plugin.json` compatibility fallback
- **Marketplace:** Universal Plugins Directory + custom marketplace JSON
- **CLI:** `/plugins` in TUI, `@` to target skills
- **Bundled capabilities:** skills, MCP servers, app integrations
- **Local marketplaces:** `$REPO_ROOT/.agents/plugins/marketplace.json` or `~/.agents/plugins/marketplace.json`

Verified developers can submit through the OpenAI Platform. Review approval
is followed by an explicit publisher action before the plugin becomes public.

**Recommended approach:** Ship vardoger as a Codex plugin with:
- A **skill** for on-demand analysis
- Generated output written to `~/.codex/AGENTS.md` (or a vardoger-specific section within it)

> **Status:** [x] Plugin manifest and analyze skill implemented. Marketplace publishing deferred to Phase 4.

---

### 5.4 OpenClaw [x]

#### Conversation History Storage

| Source | Location | Format |
|---|---|---|
| Current canonical store | `~/.openclaw/agents/<agentId>/agent/openclaw-agent.sqlite` | Versioned SQLite; consumers must use OpenClaw's transcript accessor or supported export |
| Legacy transcripts | `~/.openclaw/agents/<agentId>/sessions/<channel>_<id>.jsonl` | Pre-2.0 JSONL retained as a legacy/archive format |

**Current status:** Vardoger detects canonical SQLite history and stops with an
actionable compatibility error rather than querying private, versioned tables
or analyzing stale archive JSONL. With explicit
`VARDOGER_OPENCLAW_GATEWAY=1` enablement and `--full`, it delegates
`sessions.list` and paginated `chat.history` calls to the official OpenClaw
CLI. Incremental checkpoints remain gated on stable message-anchor support.
Pre-2.0 JSONL remains supported.

**Discovery:** Detect `*/agent/openclaw-agent.sqlite` first. Only when no
canonical store exists, enumerate legacy `sessions/*.jsonl`.

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
| CLI session state | `~/.copilot/session-state/<session-id>/events.jsonl` | JSONL — one event per line capturing user turns, assistant turns, and tool invocations from `copilot` CLI sessions |

**Primary source for Phase 5:** Copilot CLI session-state JSONL files. VS Code Copilot Chat history is stored in opaque workspace storage and is excluded from Phase 5.

**Discovery:** Enumerate current nested `*/events.jsonl` sessions and retain
legacy flat `*.jsonl` discovery without double-counting migrated sessions.

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

### 5.6 Devin Desktop / legacy Windsurf [x]

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

**Recommended approach:** Ship a native skill for Windsurf's user skill directory, an install snippet for `mcp_config.json` that wires vardoger as an MCP server (`VARDOGER_MCP_PLATFORM=windsurf`), and a `vardoger setup windsurf` helper that installs the skill and prepares the rules path. Revisit marketplace submission if Windsurf opens a self-serve flow.

> **Status:** [x] Vardoger 0.4.0 supports the legacy Cascade product surface:
> the shared native skill, MCP snippet, user skill installer, history reader,
> and rules writer. Windsurf has since become Devin Desktop and new tabs
> default to Devin Local. Phase 6 adds a separate `devin` target for documented
> ATIF exports, native `.devin/*` rules, and `~/.config/devin/*` skills/rules;
> `windsurf` remains the legacy Cascade compatibility name.

#### Devin Local supported surface [x]

Devin CLI documents `--export [PATH]`, which refreshes a conversation export
in ATIF format after each turn. `vardoger setup devin` prepares
`~/.vardoger/imports/devin/` and installs a native skill under
`~/.config/devin/skills/analyze/`; Vardoger reads only exports the user places
in that import directory. It does not inspect Devin's private session store.

Global personalization is delivered to a fenced section in
`~/.config/devin/AGENTS.md`. Project personalization uses the dedicated
`.devin/rules/vardoger.md` rule with `trigger: always_on`.

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

**vardoger target:** Default to Cline's user-global rules directory at
`~/Documents/Cline/Rules/vardoger.md`. For project scope, detect whether
`.clinerules` is a directory or a file and choose the corresponding delivery
automatically.

> **Status:** Implemented — `src/vardoger/writers/cline.py` covers global
> delivery plus both legacy project layouts with focused tests.

#### Distribution

Cline now publishes third-party plugins, skills, and MCP servers through the
PR-based [`cline/marketplace`](https://github.com/cline/marketplace) catalog.
The prior GitHub-issue queue is retained only as submission history.

**Recommended approach:** Ship an `llms-install.md` that an LLM-driven install flow can follow, plus a user-facing README.

- Install guide: `plugins/cline/llms-install.md`
- User-facing readme: `plugins/cline/README.md`

> **Status:** [x] Install guide and README implemented; marketplace submission tracked in [`MARKETPLACE_STATUS.md`](./MARKETPLACE_STATUS.md).

---

## 6. Architecture Constraints

### 6.1 Local Data Handling [x]

Conversation discovery, parsing, checkpointing, and rule writes happen on the
user's machine. Vardoger operates no hosted service. Filesystem readers open no
network connection; the explicitly enabled OpenClaw reader delegates read-only
Gateway transport and authentication to the installed OpenClaw CLI without
accepting credentials itself. The selected host assistant performs
summarization and synthesis; if that assistant uses a cloud model, the excerpts
supplied to it are processed under the host/provider's data policy. These
boundaries must be disclosed before analysis rather than described as fully
local.

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
- [x] PyPI publishing for `pip install vardoger` / `pipx install vardoger` (current release: 0.4.0)
- [ ] Cursor Plugin Registry — **recovery submitted 2026-09-27, awaiting review**; Cursor confirmed receipt of the current Vardoger publisher application. The public route still displays “Marketplace Plugin Not Found,” so publication and signed-out installability remain open.
- [x] Claude Code community catalog + custom marketplace — **Live**, re-add verified 2026-07-09 in [`anthropics/claude-plugins-community`](https://github.com/anthropics/claude-plugins-community); the self-served `.claude-plugin/marketplace.json` path remains available through `/plugin marketplace add dstrupl/vardoger`.
- [ ] Codex custom marketplace + official directory — the self-served catalog is **Live** at `.agents/plugins/marketplace.json`; Codex CLI 0.146.0 clean-installed Vardoger 0.4.0. The portable manifest and deterministic archive (`c193c9c4…`) are validated, and the individual OpenAI developer identity is verified. The portal currently exposes only **With MCP**, not the documented **Skills only** upload path, so submission is blocked on OpenAI access/support rather than repository work.
- [x] Skill publishing to ClawHub for OpenClaw — publishing was achieved, but the [current public listing](https://clawhub.ai/dstrupl/vardoger-analyze) has regressed to 0.3.1 with security status `Review` and mandatory MIT-0 terms. An explicit distribution-license decision is required before another release.
- [x] Plugin packaging and marketplace submission for GitHub Copilot CLI — **custom marketplace live (self-served)** via `plugins/copilot/marketplace.json` (Copilot CLI has no central registry for custom marketplaces — users install directly via `copilot plugin marketplace add dstrupl/vardoger:plugins/copilot`); **`awesome-copilot` live** as [`vardoger-analyze`](https://github.com/github/awesome-copilot/blob/main/skills/vardoger-analyze/SKILL.md) ([PR #1461](https://github.com/github/awesome-copilot/pull/1461) merged 2026-04-28 by [`aaronpowell`](https://github.com/aaronpowell) into `staged` as [`2f4f41b8`](https://github.com/github/awesome-copilot/commit/2f4f41b8bdeae0a96a4370f9d77358eafec4fe8f); auto-published to `main`, installable today via `gh skills install github/awesome-copilot vardoger-analyze`)
- [ ] GitHub Copilot CLI default marketplace — [PR #56](https://github.com/github/copilot-plugins/pull/56) was rebased onto current upstream, reduced to the focused Vardoger object and README line, clean-installed with Copilot CLI 1.0.88, and marked ready. It is mergeable and awaits required review.
- [x] Windsurf and Devin direct distribution — 0.4.0 supports both the legacy Cascade skill/rules/history paths and first-class Devin ATIF imports, `.devin/*` rules, and `~/.config/devin/*` setup.
- [ ] Cline Marketplace submission — legacy [issue #1394](https://github.com/cline/mcp-marketplace/issues/1394) is still open but superseded. The validated current-catalog entry is submitted as [`cline/marketplace#143`](https://github.com/cline/marketplace/pull/143) and awaits review. Cline CLI 3.0.65 accepted the rendered install command and environment, and public Vardoger 0.4.0 completed MCP initialization with all nine tools; marketplace-card acceptance remains blocked on upstream merge.
- [x] Official MCP Registry submission — **Live** as [`io.github.dstrupl/vardoger@0.4.0`](https://registry.modelcontextprotocol.io/v0.1/servers?search=vardoger&limit=10), published and verified active/latest on 2026-09-27. Tracked at `plugins/mcp-registry/server.json`.
- [x] McpMux community registry submission ([`mcpmux/mcp-servers`](https://github.com/mcpmux/mcp-servers)) — **Live** (2026-04-24). [PR #113](https://github.com/mcpmux/mcp-servers/pull/113) merged as [`495adbc`](https://github.com/mcpmux/mcp-servers/commit/495adbc131a7ea2acd8df29869b391cc2cb05cbe) after addressing reviewer feedback (switched `VARDOGER_MCP_PLATFORM` from `text` to `select` input). Tracked server definition at `plugins/mcpmux/vardoger.json`; McpMux bundles `main` roughly hourly, so Cursor, Claude Desktop, VS Code, and Windsurf desktop clients on the McpMux gateway now pick up vardoger automatically.
- [ ] Docker MCP Registry submission ([`docker/mcp-registry`](https://github.com/docker/mcp-registry)) — **submitted, awaiting review** ([PR #2949](https://github.com/docker/mcp-registry/pull/2949)); the refreshed branch is rebased onto current upstream and `source.commit` is pinned to the peeled `v0.4.0` commit `f189c2a824b795c1f5985c3f4a6729f2d645e348`.

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

### Phase 6 — Host Evolution and Distribution Recovery [ ]

**Goal:** Bring the shipped integrations and marketplace artifacts up to the
current host contracts without breaking the existing 0.3.2 direct-install
paths. The combined work is versioned as 0.4.0 because it adds public CLI and
host-integration capabilities without breaking existing contracts.

- [x] Apply one shared Agent Plugins 1.0 format and metadata pattern across the
  Codex, Cursor, and Copilot packages, retaining thin host-specific
  compatibility overlays and their existing marketplace paths.
- [x] Add Cline global-scope delivery using its current user rules contract,
  preserve `.clinerules` project compatibility, and add focused writer/setup
  tests.
- [x] Correct Cursor rule delivery to the required `.mdc` format while keeping
  legacy `.md` files as a non-destructive read fallback.
- [x] Discover current nested Copilot `events.jsonl` sessions while preserving
  and deduplicating legacy flat JSONL history.
- [x] Centralize host path configuration and honor `COPILOT_HOME` consistently
  across Copilot history, writer, setup, and status code.
- [x] Detect OpenClaw 2.0 canonical SQLite safely, preserve legacy JSONL, emit
  valid skill frontmatter, and provide an explicit full-read adapter through
  the official Gateway CLI's `sessions.list` and `chat.history`. Disposable
  clean-profile live acceptance passed on OpenClaw 2026.9.6; incremental
  checkpoints remain open.
- [x] Add a first-class `devin` adapter around Devin CLI's documented,
  user-enabled ATIF `--export` contract; deliver global/project rules and a
  native skill through documented paths while retaining `windsurf` as the
  legacy Cascade alias. Private session storage remains out of scope.
- [x] Synchronize the Claude custom-marketplace metadata with the shipped
  plugin version.
- [x] Make Claude and Codex synthesis aware of native host memory so generated
  instructions retain durable cross-project preferences instead of duplicating
  episodic or repository-scoped host-managed context.
- [ ] Recover remaining marketplace reach: monitor the submitted Cursor
  recovery and obtain access/support for Codex's missing Skills-only portal
  path. Copilot PR #56 and Cline PR #143 await upstream review.
- [ ] Resolve whether ClawHub's mandatory MIT-0 distribution is acceptable;
  republish only if the owner accepts it and the OpenClaw integration remains
  supported after the native-memory review.
- [x] Publish the validated 0.4.0 compatibility release. PR #37 was rebase
  merged at `f189c2a`; main CI passed, annotated tag `v0.4.0` and the GitHub
  release are live, and trusted publication delivered matching wheel/sdist
  hashes to PyPI. The Official MCP Registry is also live at 0.4.0; Docker's
  separately versioned PR is refreshed and awaits review.

**Success criteria:** Current product defaults work without relying on legacy
paths, direct installs remain backward-compatible, and every public status row
has live installation evidence or an explicit, owned blocker.

---

### Phase 7 — Cross-Host Profile Compiler [in progress]

**Goal:** Reposition Vardoger around the durable value native memories do not
provide: a user-owned, reviewable profile that can combine evidence across
assistant silos and emit portable instructions.

- [x] Define a normalized preference/evidence model with source host,
  provenance, recency, confidence, and conflict state.
- [x] Deterministically aggregate explicitly selected, existing Vardoger
  generations across supported hosts without silently re-reading unreviewed
  raw transcripts.
- [x] Add a review-first CLI that renders the profile and exact `AGENTS.md`
  diff; require a separate `profile write --apply` invocation for mutation.
- [ ] Add editing, accept/reject history, and rollback for the shared profile.
- [x] Emit a portable, fenced `AGENTS.md` block while preserving all content
  outside Vardoger's markers.
- [ ] Add thin host-specific projections that avoid duplicating native memory.
- [x] Add confidence, deterministic recency retention, and regex-based
  drop/mask redaction controls before cross-host compilation.

**MVP boundary:** Conflict detection is deliberately deterministic and narrow:
it catches directly opposed directive prefixes over the same normalized text
(for example, “Prefer tabs” versus “Avoid tabs”), withholds both from active
instructions, and exposes the decision in the JSON audit. Semantic conflict
resolution, profile editing/history, native-memory deduplication, and automatic
host projection remain follow-on work.

**Rationale:** Cursor, Codex, Copilot, and OpenClaw now provide substantial
native memory or history-learning features. Their memories remain vendor
silos, while Claude's auto-memory is repository-scoped and Devin Local does
not persist memories. Cross-host ownership, provenance, and portability are
therefore the defensible product advantage.

---

## 8. Non-Goals and Out of Scope

The following are explicitly deferred or excluded:

| Item | Reason |
|---|---|
| **Analysis algorithm design** | Phase 2 (complete). Phase 1 proved the plumbing; Phase 2 added the intelligence. |
| **Vardoger-operated cloud service** | Architectural constraint. Vardoger has no backend; host-model processing may still be remote under the selected provider's policy. |
| **Real-time conversation monitoring** | vardoger operates on historical data, not live streams. It runs on-demand or on session start, not continuously. |
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

> **Decision:** On-demand by default. Users invoke the `vardoger_personalize` MCP tool or the `vardoger` CLI when they want a refresh. Claude Code additionally ships a `SessionStart` hook that surfaces a staleness reminder without auto-running analysis. A scheduled / background refresh path remains out of scope for Phase 5; it would conflict with the explicit, review-first model above.

### 9.5 History Scope Defaults — RESOLVED

> **Decision:** No default time window. The first run analyzes the user's full local conversation history — that is the moment the most signal is available at zero ongoing cost, and a windowed default would silently drop older sessions that the user never has a second chance to feed in. The per-conversation checkpoint store (see 4.5) bounds every subsequent run to the new or changed conversations only, so the "Too much: slow analysis" concern decays naturally after the first invocation. The `--since DAYS` flag (CLI: `vardoger analyze` / `vardoger prepare`) and the existing `--full` flag remain available as power-user knobs for users with very large local history who want to bound first-run cost or force a full re-crawl, respectively. The synthesis prompt itself is responsible for weighting recent over older behavior when patterns conflict; the reader's job is to surface everything the user has on disk.

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
| **JSONL** | JSON Lines format — one complete JSON object per line, used by several supported platforms for conversation storage. |
| **ATIF** | Agent Trajectory Interchange Format — the documented JSON export emitted by Devin CLI's `--export` flag. |

## Appendix B: Platform File Paths Summary

```
vardoger state:
  Checkpoints: ~/.vardoger/state.json (per-platform processing watermarks)
  Import dirs:  ~/.vardoger/imports/devin/ (created by vardoger setup devin)

Cursor:
  History:  ~/.cursor/projects/<slug>/agent-transcripts/<uuid>/<uuid>.jsonl
  History:  ~/.cursor/chats/<hash>/<uuid>/store.db
  Output:   <project>/.cursor/rules/vardoger.mdc
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
  History:  ~/.openclaw/agents/<agentId>/agent/openclaw-agent.sqlite
            (never queried directly; opt-in full read via official Gateway CLI)
            ~/.openclaw/agents/<agentId>/sessions/<channel>_<id>.jsonl (legacy)
  Output:   ~/.openclaw/skills/vardoger-personalization/SKILL.md (global)
            ./skills/vardoger-personalization/SKILL.md (project)
  Skill:    clawhub install (ClawHub registry) or ~/.openclaw/skills/ (local)

GitHub Copilot CLI:
  History:  ~/.copilot/session-state/<session-id>/events.jsonl
            ~/.copilot/session-state/*.jsonl (legacy fallback)
  Output:   ~/.copilot/copilot-instructions.md (global, fenced section)
            <project>/.github/copilot-instructions.md (project, fenced section)
  Plugin:   copilot plugin marketplace add dstrupl/vardoger:plugins/copilot

Devin Local:
  History:  ~/.vardoger/imports/devin/*.json (user-enabled `devin --export` ATIF)
  Output:   ~/.config/devin/AGENTS.md (global, fenced section)
            <project>/.devin/rules/vardoger.md (project, dedicated file)
  Skill:    ~/.config/devin/skills/analyze/SKILL.md
  Plugin:   Direct skill + CLI/MCP setup in plugins/devin/README.md

Windsurf:
  History:  ~/.codeium/windsurf/**/*.jsonl
  Output:   ~/.codeium/windsurf/memories/global_rules.md (global, fenced section)
            <project>/.windsurf/rules/vardoger.md (project, dedicated file)
  Skill:    ~/.codeium/windsurf/skills/vardoger-analyze/SKILL.md
  Plugin:   Direct skill + MCP setup in plugins/windsurf/README.md; MCP Store remains editorial

Cline:
  History:  <VS Code globalStorage>/saoudrizwan.claude-dev/tasks/<task-id>/api_conversation_history.json
  Output:   ~/Documents/Cline/Rules/vardoger.md (global default)
            <project>/.clinerules/vardoger.md (if .clinerules is a directory)
            <project>/.clinerules (fenced section, if .clinerules is a single file)
  Plugin:   Cline MCP Marketplace — install guide at plugins/cline/llms-install.md
```
