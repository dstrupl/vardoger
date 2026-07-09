# vardoger — Windsurf Integration

This directory is the install reference for using [vardoger](../../README.md)
with the [Windsurf](https://windsurf.com/) editor. Windsurf does not have a
public plugin submission form today — the in-product "MCP Store" curates
third-party servers but there is no self-serve submission endpoint. Vardoger's
current `main` branch carries the three direct integration surfaces Windsurf
supports:

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
- **Windsurf Editor** — [windsurf.com/download](https://windsurf.com/download).

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

The native installer was added after the `0.3.2` release and will be included
in the next PyPI version. Until then, the Git install above provides the
current `main` implementation; `pipx install vardoger` remains sufficient for
the released CLI writer and MCP server.

### 2. (Optional) Register vardoger as a Windsurf MCP server

If you want Windsurf to call into vardoger from Cascade, add it to your
Windsurf MCP configuration:

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
