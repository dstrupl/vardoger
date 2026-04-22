# vardoger — McpMux community registry submission

Draft submission for [mcpmux/mcp-servers](https://github.com/mcpmux/mcp-servers),
the community-maintained JSON registry consumed by the
[McpMux](https://mcpmux.com) desktop gateway. McpMux proxies MCP tools into
Cursor, Claude Desktop, VS Code, and Windsurf through a single endpoint, so
being listed here lands vardoger in one gateway reachable from every McpMux
client at once.

## What's in this folder

- [`vardoger.json`](./vardoger.json) — the server definition, shaped to the
  repo's `schemas/server-definition.schema.json` (JSON Schema 2020-12) with
  schema version `2.1`.

## Before opening the PR

1. Fork and clone [`mcpmux/mcp-servers`](https://github.com/mcpmux/mcp-servers).
2. Copy this file into `servers/` on the fork. The upstream repo names every
   server file after its `id` field (see `CONTRIBUTING.md` §"Adding a Server"),
   so the filename must mirror `id` — i.e. `io.github-dstrupl-vardoger.json`,
   not `vardoger.json`:

   ```bash
   cp <workspace>/plugins/mcpmux/vardoger.json \
      <fork>/servers/io.github-dstrupl-vardoger.json
   # The in-repo `$schema` reference ("../schemas/server-definition.schema.json")
   # already resolves once the file is in `servers/`; leave it as-is.
   ```

3. Validate against their schema and check for ID/alias conflicts. The upstream
   repo ships both `pnpm-lock.yaml` and `package-lock.json`, so either package
   manager works:

   ```bash
   cd <fork>
   pnpm install   # or: npm install
   pnpm validate servers/io.github-dstrupl-vardoger.json
   pnpm check-conflicts
   ```

4. Open the PR. The upstream repo enforces a DCO sign-off (Elastic License 2.0
   contributor terms), so `git commit -s` is required — not optional:

   ```bash
   git add servers/io.github-dstrupl-vardoger.json
   git commit -s -m "Add vardoger"
   git push origin <branch>
   gh pr create --title "Add vardoger" \
     --body "Personalize AI coding assistants from local conversation history. Runs vardoger CLI via stdio. See https://github.com/dstrupl/vardoger."
   ```

5. Wait for CI + maintainer review. On merge, the bundle updates within an
   hour and McpMux desktop clients pick up the entry automatically.

## Maintenance

When vardoger ships a breaking change to the MCP tools or CLI flags, open a
follow-up PR against the same `servers/io.github-dstrupl-vardoger.json`
updating the transport block (and the `changelog_url` field if we decide to
expose one). Update [`../../MARKETPLACE_STATUS.md`](../../MARKETPLACE_STATUS.md)
in lock-step.
