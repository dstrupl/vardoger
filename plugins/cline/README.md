# vardoger — Cline Integration

This directory is the install reference for using [vardoger](../../README.md)
with [Cline](https://cline.bot/). Vardoger has two implemented
integration surfaces:

1. **Personalization writer** — `vardoger analyze --platform cline` writes
   user-global rules to `~/Documents/Cline/Rules/vardoger.md`. Explicit
   project scope retains the existing `<project>/.clinerules` integration.
2. **MCP server** — vardoger ships an MCP server (`vardoger mcp`) that Cline
   can call from its chat UI.

## Prerequisites

- **Python 3.11+** and **pipx** — see the main
  [installation instructions](../../README.md#prerequisites).
- **Cline** — [cline.bot](https://cline.bot/) (installed as a VS Code, Cursor,
  or Windsurf extension).

## Install

### 1. Install the vardoger CLI and prepare Cline rules

```bash
pipx install vardoger
vardoger setup cline
```

`vardoger setup cline` prepares Cline's documented user-global rules directory.
Running `vardoger analyze --platform cline` writes a dedicated
`~/Documents/Cline/Rules/vardoger.md` file. To keep personalization inside one
workspace, pass `--scope project --project .`; Vardoger then writes
`.clinerules/vardoger.md` or manages a fenced section inside an existing
single-file `.clinerules`.

### 2. (Optional) Register vardoger as a Cline MCP server

If you want Cline to call into vardoger from its chat UI, add it to Cline's
MCP configuration. Open Cline's **MCP Servers** panel (or edit the JSON
directly) and add:

```json
{
  "mcpServers": {
    "vardoger": {
      "command": "vardoger",
      "args": ["mcp"],
      "env": {
        "VARDOGER_MCP_PLATFORM": "cline"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

The `VARDOGER_MCP_PLATFORM=cline` environment variable tells vardoger's
MCP server to default to your Cline history and user-global rules rather than
Cursor's rules. Pass `scope="project"` and `project_path="<workspace>"` to an
MCP write when the personalization should apply to only one project. Cline
will pick the change up on next reload.

### 3. (Future) Install via Cline's marketplace

Cline's current [`cline/marketplace`](https://github.com/cline/marketplace)
catalog accepts validated pull requests for plugins, skills, and MCP servers.
Vardoger has not submitted there yet, but the current MCP entry and PR text are
prepared and schema-validated in the [submission package](./submission/README.md).
Use the manual configuration in step 2 until an upstream PR is approved and
the catalog entry is public.
The old [cline/mcp-marketplace issue #1394](https://github.com/cline/mcp-marketplace/issues/1394)
remains open only as historical evidence of the superseded issue-based flow.

## Usage

- `vardoger analyze --platform cline` — writes user-wide personalization to
  `~/Documents/Cline/Rules/vardoger.md`.
- `vardoger analyze --platform cline --scope project --project .` — writes
  project-only personalization using the existing `.clinerules` layout.
- Ask Cline to analyze your Cline conversation history, or invoke the vardoger
  MCP server once it is registered.

### Where the personalization lands

- **Global (default):** `~/Documents/Cline/Rules/vardoger.md`, Cline's
  documented default global rules directory. Vardoger owns this dedicated
  file, so it does not alter other global rule files.
- **Project:** `<project>/.clinerules/vardoger.md` when `.clinerules` is a
  directory, or a Vardoger-managed fenced block when `.clinerules` is a file.
- **Project validation remains on.** Vardoger verifies that `project_path`
  lives inside a real project. If it refuses a project write, pass the real
  workspace root or use global scope.

## Uninstall

- Remove `~/Documents/Cline/Rules/vardoger.md` for global personalization.
- Remove `.clinerules/vardoger.md` (or the fenced block in `.clinerules` if it
  is a single file) for project personalization.
- Remove the `"vardoger"` entry from your Cline MCP configuration if you added
  one.
- `pipx uninstall vardoger` to drop the CLI.
