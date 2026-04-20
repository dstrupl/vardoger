# Security Policy

## Privacy posture

vardoger is designed around a non-negotiable constraint: **all conversation
history reading and analysis happens on the user's machine**. The project does
not open sockets, contact external services, or upload any conversation data.
Analysis is performed by the host AI assistant's own model through a
skill-driven pipeline (see `PRD.md`, Section 6). The only network traffic in
the normal workflow is `pipx install vardoger` / `uvx vardoger` pulling the
package from PyPI.

See [PRIVACY.md](PRIVACY.md) for the full data-handling policy (what
vardoger reads, writes, and never transmits).

If you discover a code path that violates this constraint (e.g., a dependency
that phones home, or a bug that exfiltrates local data), please treat it as a
security issue and report it privately.

## Supported versions

Only the most recent published release on PyPI is supported with security
fixes.

| Version       | Supported |
|---------------|-----------|
| 0.1.x         | Yes       |
| 0.1.0bN betas | No        |

## Reporting a vulnerability

Please do **not** open a public GitHub issue for security-sensitive reports.

1. Email the maintainer at `dstrupl@gmail.com` with:
   - A description of the issue and its impact.
   - Minimal reproduction steps (include vardoger version, Python version, and
     host platform — Cursor / Claude Code / Codex / OpenClaw / GitHub
     Copilot CLI / Windsurf / Cline).
   - Any logs, payloads, or screenshots relevant to the report. Redact
     conversation content; vardoger does not need it to reproduce most bugs.
2. Expect an acknowledgement within 3 business days.
3. I will work with you on a fix and a coordinated disclosure timeline; most
   issues are resolved within 30 days.

## Scope

In scope:

- Data-exfiltration bugs in vardoger's core or any shipped plugin.
- Path-traversal, TOCTOU, or arbitrary-write issues in the history adapters
  (`src/vardoger/history/`) and writers (`src/vardoger/writers/`).
- MCP server issues (`src/vardoger/mcp_server.py`) such as unsafe tool
  arguments, sandbox escapes, or prompt-injection paths that influence
  on-disk state.
- Dependency CVEs that affect vardoger's runtime behavior.

Out of scope:

- Social-engineering against PyPI or GitHub maintainers.
- Bugs that require the user to already have arbitrary code execution on
  their own machine.
- Issues in the upstream AI assistants (report those to Cursor, Anthropic,
  OpenAI, OpenClaw, GitHub/Microsoft, Codeium, or the Cline project
  directly).

## Acknowledgements

Reporters who follow this policy will be credited in the CHANGELOG unless they
request otherwise.
