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

vardoger targets the three leading AI coding environments:

| Platform | Vendor | Distribution Model |
|---|---|---|
| **Cursor** | Anysphere | VS Code extension marketplace + MCP servers |
| **Claude Code** | Anthropic | Claude Code plugin marketplace (GitHub-based) |
| **OpenAI Codex** | OpenAI | Codex plugin directory + custom marketplaces |

Each platform has its own conversation storage format, system prompt contribution mechanism, and plugin distribution channel. vardoger must integrate natively with all three.

---

## 4. Core Capabilities

### 4.1 Read Conversation History [x]

vardoger must be able to discover and parse all locally stored conversation history for the active user across supported platforms. This is read-only access to files already on disk — no network calls, no API integrations, no platform authentication required.

### 4.2 Analyze Patterns Locally [ ]

Using AI capabilities available on the user's machine (the host platform's own model access, or a local model), vardoger analyzes conversation history to extract behavioral patterns. The analysis algorithm is explicitly deferred to a future phase (see Section 8), but the infrastructure to invoke it must be in place.

> **Status:** Placeholder analysis implemented — returns real statistics but no AI-powered pattern extraction yet.

### 4.3 Generate System Prompt Additions [x]

Based on the analysis, vardoger produces a text artifact — a set of instructions, preferences, and behavioral guidance — formatted as a valid system prompt addition for each target platform.

> **Status:** Generates valid prompt additions with placeholder content. Real personalized content depends on 4.2.

### 4.4 Deliver via Platform-Native Mechanisms [x]

The generated prompt addition is written to the location each platform natively reads, so it takes effect without any manual intervention from the user. The exact delivery mechanism per platform is detailed in Section 5.

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

**Recommended approach:** Ship as an MCP server (configured in `mcp.json`) that exposes vardoger commands as tools the agent can invoke. This aligns with Cursor's AI-native plugin model better than a traditional VS Code extension.

> **Status:** [x] MCP server implemented (stdio transport, `vardoger_analyze` tool). [ ] VS Code Marketplace publishing not yet done.

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

> **Status:** [x] Plugin manifest and analyze skill implemented. [ ] SessionStart hook not yet implemented. [ ] Marketplace publishing not yet done.

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

> **Status:** [x] Plugin manifest and analyze skill implemented. [ ] Marketplace publishing not yet done.

---

## 6. Architecture Constraints

### 6.1 Local-Only Processing [x]

All conversation history reading and analysis happens exclusively on the user's machine. No data is transmitted to any external service. This is a non-negotiable architectural constraint, not a preference.

**Rationale:** Conversation history contains proprietary code, internal discussions, credentials that were accidentally pasted, and other sensitive material. Users must be able to trust that vardoger never exfiltrates this data.

### 6.2 AI Model Access [ ]

vardoger needs AI capabilities for the analysis phase. Since no cloud service is used, the analysis must run through one of:

1. **Host platform's model access** — Use the same AI model the coding assistant already has access to (e.g., invoke the assistant itself to analyze its own history via a skill or tool call)
2. **Local model** — Use a locally running model (e.g., via Ollama, llama.cpp, or similar)
3. **User-configured API** — Allow the user to point at their own API key for a model provider (the key and calls are the user's own; vardoger does not intermediate)

Option 1 is the preferred approach for Phase 1 because it requires zero additional setup.

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

### Phase 1 — Foundation: Read and Contribute

**Goal:** Ship a working plugin on all three platforms that can read conversation history and write a (placeholder) system prompt addition.

**Deliverables:**
- [x] History reader adapters for Cursor, Claude Code, and Codex (JSONL parsers)
- [ ] History reader adapters for SQLite sources (Cursor chat DB, Codex state DB)
- [x] A unified internal representation of conversation data
- [x] Platform-native prompt writers that produce valid configuration files
- [ ] Plugin packaging and marketplace submission for all three platforms
- [x] A placeholder analysis step that produces a minimal, hard-coded prompt addition (proving the pipeline works end-to-end)
- [x] Local plugin install for all three platforms (Cursor MCP, Claude Code plugin, Codex plugin)

**Success criteria:** A user can install vardoger from the plugin marketplace on any supported platform, run it, and see a vardoger-authored rule file appear in the correct location.

> **Status:** End-to-end pipeline works locally on all three platforms. Marketplace publishing remains.

### Phase 2 — Intelligence: AI-Powered Analysis [ ]

**Goal:** Replace the placeholder analysis with real AI-driven pattern extraction.

**Deliverables:**
- [ ] Analysis pipeline that processes conversation history through an AI model
- [ ] Pattern categories: communication preferences, technical stack, workflow habits, pain points, coding style
- [ ] Prompt generation that translates extracted patterns into effective system prompt instructions
- [ ] Configurable analysis scope (last N days, specific projects, all history)

**Success criteria:** The generated prompt addition measurably changes assistant behavior in ways the user recognizes as personalized.

### Phase 3 — Refinement Loop [ ]

**Goal:** Make personalization continuous and self-improving.

**Deliverables:**
- [ ] Incremental analysis (process only new conversations since last run)
- [ ] Staleness detection and automatic refresh suggestions
- [ ] User feedback mechanism (accept/reject/edit generated rules)
- [ ] Confidence scoring for extracted patterns
- [ ] A/B style comparison (before/after personalization quality)

**Success criteria:** The system improves its personalization over time without requiring manual intervention.

---

## 8. Non-Goals and Out of Scope

The following are explicitly deferred or excluded:

| Item | Reason |
|---|---|
| **Analysis algorithm design** | Deferred to Phase 2. Phase 1 proves the plumbing; the intelligence comes later. |
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
| **JSONL** | JSON Lines format — one complete JSON object per line, used by all three platforms for conversation storage. |

## Appendix B: Platform File Paths Summary

```
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
```
