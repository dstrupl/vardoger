# vardoger — Cline Integration

This directory is the install reference for using [vardoger](../../README.md)
with [Cline](https://cline.bot/). Cline has two integration surfaces:

1. **Personalization writer** — `vardoger analyze --platform cline` writes
   personalized rules that Cline auto-loads from `<project>/.clinerules/`
   (project scope only; Cline does not have a user-global rules surface).
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

`vardoger setup cline` prints guidance about Cline's project-local rules
convention. Running `vardoger analyze --platform cline --scope project`
later writes personalization into `.clinerules/vardoger.md` (or a
`<!-- vardoger:start --> ... <!-- vardoger:end -->` fenced section inside
an existing single-file `.clinerules`).

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
MCP server to default to your Cline history and write to `.clinerules/`
rather than Cursor's `.cursor/rules/`. Cline will pick the change up on
next reload.

### 3. (Optional) Install via Cline's MCP marketplace

Cline maintains an [MCP marketplace](https://github.com/cline/mcp-marketplace)
that lets users install servers with one click. We publish install guidance
for Cline's "llms-install" flow in [`llms-install.md`](./llms-install.md).
Once vardoger is accepted into the marketplace, Cline users will be able to
install it directly from the MCP panel inside Cline. Until then, use the
manual configuration in step 2.

## Usage

- `vardoger analyze --platform cline --scope project` — writes personalization
  to `<project>/.clinerules/vardoger.md`.
- Ask Cline to analyze your Cline conversation history, or invoke the vardoger
  MCP server once it is registered.

## Uninstall

- Remove `.clinerules/vardoger.md` (or the fenced block in `.clinerules` if it
  is a single file).
- Remove the `"vardoger"` entry from your Cline MCP configuration if you added
  one.
- `pipx uninstall vardoger` to drop the CLI.
