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

## Uninstall

```bash
copilot plugin uninstall vardoger
copilot plugin marketplace remove vardoger   # only if you used Option A
```

Remove the fenced `<!-- vardoger:start --> ... <!-- vardoger:end -->` section
from your Copilot instructions file if you want to wipe the personalization
too.
