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

The package includes an Agent Plugins 1.0 root [`plugin.json`](./plugin.json),
so Copilot discovers `skills/analyze/SKILL.md` from the standard fixed
location. The existing `.github/plugin/plugin.json` manifest remains in place
for compatibility with older Copilot CLI releases and the current marketplace.

### Option B — Install directly from the Git subdirectory

If you would rather skip the marketplace registration step and install the
plugin in a single command:

```bash
copilot plugin install dstrupl/vardoger:plugins/copilot
pipx install vardoger
```

This installs into `~/.copilot/installed-plugins/_direct/<source-id>/` as a
"direct" install. Use `copilot plugin update vardoger` to refresh.

### Published skill and default-marketplace status

The standalone `vardoger-analyze` skill is also live in
[`github/awesome-copilot`](https://github.com/github/awesome-copilot):

```bash
gh skills install github/awesome-copilot vardoger-analyze
```

Draft [`github/copilot-plugins#56`](https://github.com/github/copilot-plugins/pull/56)
proposes Vardoger for the separate default plugin marketplace. As of
2026-09-27 it is still a draft and conflicts with current upstream, so it is
not an installation route yet. It will be rebased and refreshed to the current
upstream before review, and its branch must be updated with the portable
package now tracked here. Options A and B above remain the supported
full-plugin paths today.

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
the `vardoger` CLI to read past conversations from the Copilot configuration
directory and write a personalization to its `copilot-instructions.md` (user scope) or
`.github/copilot-instructions.md` (project scope).

The configuration directory defaults to `~/.copilot`. When `COPILOT_HOME` is
set, Vardoger uses that complete replacement root consistently for history,
status/checkpoint discovery, setup, and global instructions, matching Copilot
CLI itself.

Current Copilot CLI releases keep each transcript at
`<copilot-home>/session-state/<session-id>/events.jsonl`, as documented in the
[Copilot CLI configuration-directory reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference#session-state).
Vardoger also reads the legacy `<copilot-home>/session-state/<session-id>.jsonl`
layout used by older Copilot CLI releases. If both files exist for one session,
the current nested event log wins so the conversation is not analyzed twice.

See the [vardoger repo README](../../README.md) for the full workflow.

### Why use Vardoger when Copilot has Memory?

[Copilot Memory](https://docs.github.com/en/copilot/concepts/agents/copilot-memory)
can already retain repository facts and inferred or stated personal preferences.
Vardoger is complementary rather than required: it produces an explicit,
reviewable instructions block from a user-selected local history corpus, keeps
those instructions until the user changes them, and uses the same workflow
across supported assistants. Copilot automatically removes memories that go
unused for 28 days, while a Vardoger-generated instruction remains in the
user's file. Users satisfied with Copilot's managed Memory may not need this
integration; Vardoger is most useful when control, auditability, or
cross-assistant portability matters.

### Where the personalization lands

- **Default — user-global scope:** writes/updates the fenced `<!-- vardoger:start --> ... <!-- vardoger:end -->` block inside `<copilot-home>/copilot-instructions.md`, which Copilot auto-loads on every CLI session.
- **Opt-in — project scope:** pass `project_path="<workspace root>"` (and `scope=project`) to land the same fenced block inside `<project>/.github/copilot-instructions.md`. vardoger refuses to write project-scoped instructions into a directory that doesn't look like a real project (it requires `.git`, a language manifest, `AGENTS.md`, or an existing `.cursor/` in the path or one of its ancestors). Without that check, an MCP server launched from `$HOME` would silently drop rules under `~/.github/copilot-instructions.md`, which Copilot CLI never reads as project scope. Supply a real workspace root or drop the `project_path` argument to write user-globally.

## Uninstall

```bash
copilot plugin uninstall vardoger
copilot plugin marketplace remove vardoger   # only if you used Option A
```

Remove the fenced `<!-- vardoger:start --> ... <!-- vardoger:end -->` section
from your Copilot instructions file if you want to wipe the personalization
too.
