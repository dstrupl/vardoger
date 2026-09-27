# vardoger — Devin Desktop / legacy Windsurf integration

This directory documents the integration originally built for
[Windsurf](https://windsurf.com/), now named **Devin Desktop**. Vardoger 0.3.2
supports the legacy Cascade surfaces listed below. New Devin Desktop tabs
default to Devin Local, whose preferred `.devin/*` and `~/.config/devin/*`
paths are handled by the separate [first-class Devin integration](../devin/README.md);
`windsurf` remains the legacy compatibility name.

1. **Native skill** — `vardoger setup windsurf` installs
   `~/.codeium/windsurf/skills/vardoger-analyze/SKILL.md`, which Cascade can
   invoke automatically or as `@vardoger-analyze`.
2. **Personalization writer** — `vardoger analyze --platform windsurf` writes
   personalized rules that Windsurf auto-loads from
   `~/.codeium/windsurf/memories/global_rules.md` (global) or
   `<project>/.windsurf/rules/vardoger.md` (project).
3. **MCP server** — vardoger also ships an MCP server (`vardoger mcp`) that
   Windsurf can talk to from Cascade.

The checked-in native package lives at `plugins/windsurf/skills/vardoger-analyze/`.
Windsurf also discovers project-scoped skills under `.windsurf/skills/` if a
team prefers to vendor it into a repository.

## Prerequisites

- **Python 3.11+** and **pipx** — see the main
  [installation instructions](../../README.md#prerequisites).
- **Devin Desktop** — [windsurf.com/editor](https://windsurf.com/editor), using
  legacy Cascade mode for the steps below.

## Install

### 1. Install the vardoger CLI, native skill, and rules path

```bash
pipx install --force 'git+https://github.com/dstrupl/vardoger.git@main'
vardoger setup windsurf
```

`vardoger setup windsurf` installs the native skill under
`~/.codeium/windsurf/skills/vardoger-analyze/` and prepares the global
`memories/` path. Running `vardoger analyze --platform windsurf` later writes
the personalization inside a `<!-- vardoger:start --> ... <!-- vardoger:end -->`
fenced section so existing rules you maintain by hand are preserved. Restart
Windsurf or start a new Cascade conversation after the first setup.

These paths apply to legacy Cascade. For Devin Local, use
`vardoger setup devin` and the explicit ATIF export flow documented in
[`plugins/devin/`](../devin/README.md).

### 2. (Optional) Register vardoger as a Windsurf MCP server

If you want legacy Cascade to call into vardoger, add it to the legacy MCP
configuration:

**macOS / Linux:** `~/.codeium/windsurf/mcp_config.json`
**Windows:** `%USERPROFILE%\.codeium\windsurf\mcp_config.json`

```json
{
  "mcpServers": {
    "vardoger": {
      "command": "vardoger",
      "args": ["mcp"],
      "env": {
        "VARDOGER_MCP_PLATFORM": "windsurf"
      }
    }
  }
}
```

The `VARDOGER_MCP_PLATFORM=windsurf` environment variable tells vardoger's
MCP server to default to your Windsurf history and rules locations rather
than Cursor's.

If the file already exists, merge the `"vardoger"` entry into the existing
`"mcpServers"` object rather than overwriting the file. Restart Windsurf;
Cascade > **MCPs** should then list `vardoger`.

Devin Local instead uses `~/.config/devin/mcp_config.json` and its own
`vardoger setup devin` flow.

## Usage

- `vardoger analyze --platform windsurf --scope global` — writes personalization
  to `~/.codeium/windsurf/memories/global_rules.md`.
- `vardoger analyze --platform windsurf --scope project` — writes personalization
  to `<project>/.windsurf/rules/vardoger.md`.

Ask Cascade to analyze your Windsurf conversation history, invoke
`@vardoger-analyze`, or call the vardoger MCP server once it is registered.

### Where the personalization lands

- **Default — user-global scope:** writes/updates the fenced `<!-- vardoger:start --> ... <!-- vardoger:end -->` block inside `~/.codeium/windsurf/memories/global_rules.md`, which Windsurf auto-loads for every workspace.
- **Opt-in — project scope:** pass `project_path="<workspace root>"` (and `scope=project`) to land `<project>/.windsurf/rules/vardoger.md`. vardoger refuses to write project-scoped rules into a directory that doesn't look like a real project (it requires `.git`, a language manifest, `AGENTS.md`, or an existing `.cursor/` in the path or one of its ancestors). Without that check, an MCP server launched from `$HOME` would silently drop rules under `~/.windsurf/rules/vardoger.md`, which Windsurf never reads as project scope. Supply a real workspace root or drop the `project_path` argument to write user-globally.

## Uninstall

- Remove the fenced `<!-- vardoger:start --> ... <!-- vardoger:end -->` section
  from `global_rules.md` and any `.windsurf/rules/vardoger.md` files.
- Remove `~/.codeium/windsurf/skills/vardoger-analyze/`.
- Remove the `"vardoger"` entry from `mcp_config.json` if you added one.
- `pipx uninstall vardoger` to drop the CLI.
