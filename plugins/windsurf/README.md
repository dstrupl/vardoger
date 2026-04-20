# vardoger — Windsurf Integration

This directory is the install reference for using [vardoger](../../README.md)
with the [Windsurf](https://windsurf.com/) editor. Windsurf does not have a
public plugin submission form today — the in-product "MCP Store" curates
third-party servers but there is no self-serve submission endpoint. The two
integration surfaces that do work cleanly are:

1. **Personalization writer** — `vardoger analyze --platform windsurf` writes
   personalized rules that Windsurf auto-loads from
   `~/.codeium/windsurf/memories/global_rules.md` (global) or
   `<project>/.windsurf/rules/vardoger.md` (project).
2. **MCP server** — vardoger also ships an MCP server (`vardoger mcp`) that
   Windsurf can talk to from Cascade.

## Prerequisites

- **Python 3.11+** and **pipx** — see the main
  [installation instructions](../../README.md#prerequisites).
- **Windsurf Editor** — [windsurf.com/download](https://windsurf.com/download).

## Install

### 1. Install the vardoger CLI and prepare Windsurf paths

```bash
pipx install vardoger
vardoger setup windsurf
```

`vardoger setup windsurf` ensures the `memories/` and project `.windsurf/rules/`
directories exist. Running `vardoger analyze --platform windsurf` later writes
the personalization inside a `<!-- vardoger:start --> ... <!-- vardoger:end -->`
fenced section so existing rules you maintain by hand are preserved.

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
      "args": ["mcp"]
    }
  }
}
```

If the file already exists, merge the `"vardoger"` entry into the existing
`"mcpServers"` object rather than overwriting the file. Restart Windsurf;
Cascade > **MCPs** should then list `vardoger`.

## Usage

- `vardoger analyze --platform windsurf --scope global` — writes personalization
  to `~/.codeium/windsurf/memories/global_rules.md`.
- `vardoger analyze --platform windsurf --scope project` — writes personalization
  to `<project>/.windsurf/rules/vardoger.md`.

Ask Cascade to analyze your Windsurf conversation history, or invoke the
vardoger MCP server directly once it is registered.

## Uninstall

- Remove the fenced `<!-- vardoger:start --> ... <!-- vardoger:end -->` section
  from `global_rules.md` and any `.windsurf/rules/vardoger.md` files.
- Remove the `"vardoger"` entry from `mcp_config.json` if you added one.
- `pipx uninstall vardoger` to drop the CLI.
