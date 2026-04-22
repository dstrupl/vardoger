# vardoger — GitHub Copilot CLI Plugin

A [GitHub Copilot CLI](https://docs.github.com/copilot/how-tos/copilot-cli) plugin
that analyzes your conversation history and generates personalized instructions.

## Prerequisites

- **Python 3.11+** and **pipx** — see [installation instructions](../../README.md#prerequisites) in the main README.
- **GitHub Copilot CLI** — see the [GitHub Copilot CLI install docs](https://docs.github.com/copilot/how-tos/copilot-cli/getting-started/installing-copilot-cli).

## Install

Two paths are supported. Pick one.

### Option A — Register the vardoger marketplace (recommended)

```bash
copilot plugin marketplace add dstrupl/vardoger:plugins/copilot
copilot plugin install vardoger@vardoger
pipx install vardoger   # installs the `vardoger` CLI the plugin shells out to
```

Copilot will fetch `plugins/copilot/` from the vardoger repo, recognise the
`marketplace.json` at its root, and offer the bundled `vardoger` plugin for
install. Re-run `copilot plugin marketplace update vardoger` later to pick
up new releases.

### Option B — Install directly from the Git subdirectory

If you would rather skip the marketplace registration step and install the
plugin in a single command:

```bash
copilot plugin install dstrupl/vardoger:plugins/copilot
pipx install vardoger
```

This installs into `~/.copilot/installed-plugins/_direct/<source-id>/` as a
"direct" install. Use `copilot plugin update vardoger` to refresh.

### Option C — Local marketplace (`pipx` + `vardoger setup copilot`)

```bash
pipx install vardoger
vardoger setup copilot
```

This ensures `~/.copilot/copilot-instructions.md` exists so that
`vardoger analyze --platform copilot` can write personalization into a
`<!-- vardoger:start --> ... <!-- vardoger:end -->` fenced section. This
path does **not** register the analyze skill with the Copilot CLI; use
Option A or B if you want Copilot to discover the `analyze` skill.

## Usage

Once installed via Option A or B, ask Copilot to analyze your Copilot CLI
history, or invoke the `analyze` skill directly. The skill shells out to
the `vardoger` CLI to read past conversations from
`~/.copilot/history-session-state/` and write a personalization to
`~/.copilot/copilot-instructions.md` (user scope) or
`.github/copilot-instructions.md` (project scope).

See the [vardoger repo README](../../README.md) for the full workflow.

### Where the personalization lands

- **Default — user-global scope:** writes/updates the fenced `<!-- vardoger:start --> ... <!-- vardoger:end -->` block inside `~/.copilot/copilot-instructions.md`, which Copilot auto-loads on every CLI session.
- **Opt-in — project scope:** pass `project_path="<workspace root>"` (and `scope=project`) to land the same fenced block inside `<project>/.github/copilot-instructions.md`. vardoger refuses to write project-scoped instructions into a directory that doesn't look like a real project (it requires `.git`, a language manifest, `AGENTS.md`, or an existing `.cursor/` in the path or one of its ancestors). Without that check, an MCP server launched from `$HOME` would silently drop rules under `~/.github/copilot-instructions.md`, which Copilot CLI never reads as project scope. Supply a real workspace root or drop the `project_path` argument to write user-globally.

## Uninstall

```bash
copilot plugin uninstall vardoger
copilot plugin marketplace remove vardoger   # only if you used Option A
```

Remove the fenced `<!-- vardoger:start --> ... <!-- vardoger:end -->` section
from your Copilot instructions file if you want to wipe the personalization
too.
