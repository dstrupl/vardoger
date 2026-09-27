# Vardoger for Devin Local

This integration uses only Devin's documented extension and export surfaces:

- Devin CLI's `--export [PATH]` flag writes the conversation in ATIF format
  after each turn.
- `~/.config/devin/AGENTS.md` supplies global rules.
- `.devin/rules/*.md` supplies project rules.
- `~/.config/devin/skills/*/SKILL.md` supplies global skills.

Vardoger does **not** inspect Devin Desktop or Devin CLI private session
storage. History collection is therefore explicit and opt-in.

## Discovery result

The current official contracts were checked on 2026-09-27:

- [`devin --export [PATH]`](https://docs.devin.ai/cli/reference/commands)
  exports a local conversation in ATIF format after each turn. This is the
  history contract used by the adapter.
- [Lifecycle hooks](https://docs.devin.ai/cli/extensibility/hooks/lifecycle-hooks)
  expose submitted user prompts and lifecycle metadata, but no complete
  assistant-response event. They cannot produce a faithful transcript and
  are not used for collection.
- Devin's authenticated HTTP APIs manage cloud sessions. They are not a
  documented accessor for Devin Local history and would introduce network,
  credential, and account requirements, so they remain outside this local
  integration.
- No supported default path or API for reading previously unexported Devin
  Local conversations was found. Vardoger therefore does not guess at private
  databases or caches.

## Install and collect history

Install the native plugin from this repository:

```bash
devin plugins install dstrupl/vardoger#plugins/devin
```

The plugin bundles the `/vardoger:analyze` skill and an optional Vardoger MCP
server. The Python CLI must still be installed on `PATH` (`pipx install
vardoger`). Direct setup without plugin installation is also supported:

```bash
vardoger setup devin
devin --export ~/.vardoger/imports/devin/my-session.json -- "your prompt"
```

Choose a distinct filename for each session you want Vardoger to learn from.
The export file is updated after each turn. Existing sessions that were not
started with `--export` are not automatically imported.

Then ask Devin to personalize the assistant, invoke `/vardoger:analyze` (or
`/analyze` after direct setup), or run:

```bash
vardoger analyze --platform devin --scope global
```

Global output is written as a fenced Vardoger section inside
`~/.config/devin/AGENTS.md`. Project output uses the dedicated
`<project>/.devin/rules/vardoger.md` file with an `always_on` trigger:

```bash
vardoger analyze --platform devin --scope project --project /path/to/project
```

## Optional manual MCP registration

The native plugin includes `.mcp.json`. For a direct setup without the plugin,
Devin CLI can call Vardoger over MCP after adding a user-scoped stdio server:

```bash
devin mcp add -s user -e VARDOGER_MCP_PLATFORM=devin vardoger -- \
  python -m vardoger.mcp_server
```

Current Devin releases store user MCP configuration in
`~/.config/devin/mcp_config.json`.

## Product fit

Devin Local currently does not persist memories between sessions and
recommends skills for durable workflows. Vardoger is useful here as an
explicit, user-reviewed way to turn opted-in past sessions into portable
rules. It is not a transparent history scraper, and setup cannot retroactively
export sessions.
