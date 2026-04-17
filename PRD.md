# vardoger — Product Requirements Document

> **Version:** 0.1.0-draft
> **Date:** 2026-04-15
> **Status:** Draft
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
| **Cursor** | Anysphere | VS Code extension marketplace + MCP servers |
| **Claude Code** | Anthropic | Claude Code plugin marketplace (GitHub-based) |
| **OpenAI Codex** | OpenAI | Codex plugin directory + custom marketplaces |
| **OpenClaw** | OpenClaw (open-source) | ClawHub skill registry + local skill directories |

Each platform has its own conversation storage format, system prompt contribution mechanism, and plugin distribution channel. vardoger must integrate natively with all of them.

---

## 4. Core Capabilities

### 4.1 Read Conversation History [x]

vardoger must be able to discover and parse all locally stored conversation history for the active user across supported platforms (Cursor, Claude Code, OpenAI Codex, OpenClaw). This is read-only access to files already on disk — no network calls, no API integrations, no platform authentication required.

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

> **Status:** [x] MCP server implemented (stdio transport) with `vardoger_personalize` entry-point tool plus `vardoger_prepare`, `vardoger_synthesize_prompt`, and `vardoger_write` implementation tools. VS Code Marketplace publishing deferred to Phase 4.

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

### 5.4 OpenClaw [ ]

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

The core analysis logic must be shared across all three platform integrations. Platform-specific code should be limited to:
- History discovery and parsing (adapters per platform)
- Prompt output formatting and delivery (writers per platform)
- Plugin packaging and distribution

---

## 7. Phasing

### Phase 1 — Foundation: Read and Contribute [x]

**Goal:** Ship a working plugin on all three platforms that can read conversation history and write a (placeholder) system prompt addition.

**Deliverables:**
- [x] History reader adapters for Cursor, Claude Code, and Codex (JSONL parsers)
- [ ] History reader adapter for OpenClaw (JSONL parser)
- [ ] ~~History reader adapters for SQLite sources (Cursor chat DB, Codex state DB)~~ — **Deferred.** Cursor SQLite stores contain non-agent UI state in undocumented formats; Codex SQLite indexes the same JSONL files. JSONL provides cleaner data.
- [x] A unified internal representation of conversation data
- [x] Platform-native prompt writers that produce valid configuration files
- [x] `vardoger setup` CLI command for post-install platform registration (Cursor MCP, Claude Code plugin dir, Codex marketplace.json)
- [x] Distribution via `pipx install vardoger` verified; `vardoger_personalize` MCP entry-point tool guides Cursor agent through the analysis flow
- [x] A placeholder analysis step that produces a minimal, hard-coded prompt addition (proving the pipeline works end-to-end)
- [x] Local plugin install for all three platforms (Cursor MCP, Claude Code plugin, Codex plugin)
- [ ] Local skill install for OpenClaw

**Success criteria:** A user can install vardoger via `pipx install vardoger`, run `vardoger setup <platform>`, and see a vardoger-authored rule file appear in the correct location — no marketplace required.

> **Status:** Complete for Cursor, Claude Code, and Codex. OpenClaw integration pending. Marketplace publishing deferred to Phase 4 (after limited beta).

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

### Phase 4 — Marketplace Publishing [ ]

**Goal:** Publish vardoger to the official plugin marketplaces after validating through limited beta.

**Deliverables:**
- [ ] Plugin packaging and marketplace submission for Cursor (VS Code Marketplace VSIX)
- [ ] Plugin packaging and marketplace submission for Claude Code (`anthropics/claude-plugins-official`)
- [ ] Plugin packaging and marketplace submission for Codex (official plugin directory)
- [ ] Skill publishing to ClawHub for OpenClaw
- [ ] PyPI publishing for `pip install vardoger`

**Prerequisites:** Limited beta with direct installs (`pipx install vardoger && vardoger setup <platform>`) validates the UX and analysis quality across real users.

**Success criteria:** A user can discover and install vardoger through each platform's native marketplace UI.

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

### 9.3 Prompt Delivery Mode

Should vardoger auto-write to platform config files, or generate text for the user to review and place?

- **Auto-write:** Zero friction; the user installs and runs; personalization just works
- **Review-first:** The user sees what will be written and approves it; higher trust but more friction
- **Both:** Default to review-first with an auto-write opt-in after the user gains trust

### 9.4 Analysis Trigger

When should vardoger run its analysis?

- **On-demand:** User explicitly invokes a skill/command
- **Session start hook:** Automatically on each new session (with staleness check)
- **Scheduled:** Periodic background refresh (may not be possible in all plugin models)

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
| **JSONL** | JSON Lines format — one complete JSON object per line, used by all three platforms for conversation storage. |

## Appendix B: Platform File Paths Summary

```
vardoger state:
  Checkpoints: ~/.vardoger/state.json (per-platform processing watermarks)
  Plugin dirs:  ~/.vardoger/plugins/{claude-code,codex,openclaw}/ (created by vardoger setup)

Cursor:
  History:  ~/.cursor/projects/<slug>/agent-transcripts/<uuid>/<uuid>.jsonl
  History:  ~/.cursor/chats/<hash>/<uuid>/store.db
  Output:   <project>/.cursor/rules/vardoger.md
  Plugin:   VS Code Marketplace (VSIX) or ~/.cursor/mcp.json (MCP server)

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
```
