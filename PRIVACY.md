# Privacy Policy

**Last updated:** 2026-04-20

This document describes how the vardoger project handles data. vardoger is a
free, open-source, Apache-2.0–licensed plugin for AI coding assistants
(Cursor, Claude Code, OpenAI Codex, OpenClaw, GitHub Copilot CLI, Windsurf,
Cline). This policy applies to the
vardoger CLI and every plugin published under
[github.com/dstrupl/vardoger](https://github.com/dstrupl/vardoger).

## TL;DR

vardoger runs entirely on your machine. It does **not** collect, transmit, or
store any of your conversation history or personal data on servers operated
by the project. There is no account, no telemetry, and no analytics.

## What vardoger reads

When you run `vardoger prepare`, `vardoger analyze`, `vardoger status`, or
related commands, the CLI reads the local session files that your AI
assistant already stores on your own disk:

| Platform     | Path read                                                             |
| ------------ | --------------------------------------------------------------------- |
| Cursor          | `~/.cursor/projects/<project>/agent-transcripts/*.jsonl`           |
| Claude Code     | `~/.claude/projects/<project>/*.jsonl`                             |
| Codex           | `~/.codex/sessions/**/*.jsonl`                                     |
| OpenClaw        | `~/.openclaw/agents/<agent>/sessions/*.jsonl`                      |
| GitHub Copilot  | `~/.copilot/session-state/*.jsonl`                                 |
| Windsurf        | `~/.codeium/windsurf/**/*.jsonl`                                   |
| Cline           | VS Code `globalStorage/.../tasks/*/api_conversation_history.json`  |

These files are produced by the AI assistant itself; vardoger only reads
them. vardoger never reaches into other directories, the system password
store, browser state, SSH keys, or any location that does not explicitly
belong to the assistant being personalized.

## What vardoger writes

vardoger writes to two locations on your machine:

1. **Checkpoint state.** `~/.vardoger/state.json` records which batches have
   been processed, timestamps, and feedback metadata. You can inspect it,
   copy it, or delete it at any time.
2. **The platform's personalization file**, e.g.
   `~/.codex/AGENTS.md`, `~/.claude/rules/vardoger.md`,
   `.cursor/rules/vardoger.md`,
   `~/.openclaw/skills/vardoger-personalization/SKILL.md`,
   `~/.copilot/copilot-instructions.md` (or the project-scoped
   `<project>/.github/copilot-instructions.md`),
   `~/.codeium/windsurf/memories/global_rules.md` (or the project-scoped
   `<project>/.windsurf/rules/vardoger.md`), or
   `<project>/.clinerules` / `<project>/.clinerules/vardoger.md`. For
   Copilot, Windsurf's global rules, and Cline's single-file mode vardoger
   only manages a section delimited by `<!-- vardoger:start -->` and
   `<!-- vardoger:end -->` so it never overwrites hand-authored
   instructions. This is the only on-disk output the host AI assistant
   will read back.

The checkpoint file is staged in a `.tmp` sibling and atomically renamed
into place, so a crashed run cannot corrupt it. Each generation of the
personalization is also recorded inside `state.json`, so you can roll back
to the previous version with `vardoger feedback reject`.

## What vardoger does **not** do

- vardoger does not open network sockets. `grep -rn` the source tree for
  `urllib`, `http.client`, `requests`, or `socket` — you will find none of
  them in the analysis path.
- vardoger does not ship telemetry, usage analytics, crash reporting, or
  remote configuration fetchers.
- vardoger has no account system, no login, no license check, no "phone
  home" on first run.
- vardoger does not copy your conversation history into the repository, the
  CLI cache, or any other location outside the two paths listed above.

The only network traffic caused by vardoger in normal operation is the
initial `pipx install vardoger` / `uvx vardoger` call made by your package
manager, which contacts [PyPI](https://pypi.org/project/vardoger/) to fetch
the wheel. That traffic is governed by the
[PyPI privacy policy](https://policies.python.org/pypi.org/Privacy-Notice/).

## How analysis actually happens

vardoger implements the "summarize each batch, then synthesize" workflow by
calling back into the **host AI assistant** (the one the user is already
chatting with). When you run `vardoger prepare --batch 1`, vardoger prints a
batch of your own conversation excerpts to stdout and the host assistant —
Claude Code, Cursor, Codex, OpenClaw, GitHub Copilot CLI, Windsurf, or
Cline — reads them in order to produce a summary.

That means any model-side processing of your conversation data happens
under the **host assistant's** privacy policy, not under vardoger's. vardoger
does not introduce a new cloud relationship; it just lets the assistant you
are already using read your local history one batch at a time. Relevant
policies:

- **Claude Code / Cowork:**
  [anthropic.com/legal/privacy](https://www.anthropic.com/legal/privacy)
- **Cursor:**
  [cursor.com/privacy](https://cursor.com/privacy)
- **OpenAI Codex:**
  [openai.com/policies/privacy-policy](https://openai.com/policies/privacy-policy)
- **OpenClaw:** refer to the OpenClaw project's published policy.
- **GitHub Copilot CLI:**
  [docs.github.com/site-policy/privacy-policies/github-general-privacy-statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement)
- **Windsurf (Codeium):**
  [codeium.com/privacy-policy](https://codeium.com/privacy-policy)
- **Cline:** refer to the Cline project's published policy.

If you want stricter control, you can disable the relevant assistant's
cloud features (e.g., "Privacy Mode" in Cursor, enterprise settings in
Claude Code) before running vardoger. vardoger respects whatever the host
assistant is configured to do.

## Children's privacy

vardoger is a developer tool and is not directed at children under 13. The
project does not knowingly collect data from children.

## Log files

vardoger does not produce persistent log files by default. When invoked
with the `-v` / `--verbose` flag it writes human-readable status messages
to stderr; nothing is persisted unless you redirect the output yourself.

## Updates to this policy

Material changes to this policy will be noted in
[CHANGELOG.md](./CHANGELOG.md) and in the commit history of this file. The
"Last updated" date above always reflects the most recent change.

## Contact

For privacy questions or requests:

- Email: `dstrupl@gmail.com`
- Public issues (non-sensitive): [github.com/dstrupl/vardoger/issues](https://github.com/dstrupl/vardoger/issues)

For security-sensitive reports (data-exfiltration bugs, path-traversal,
etc.), please follow [SECURITY.md](./SECURITY.md) instead of filing a
public issue.
