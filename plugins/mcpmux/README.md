# vardoger — McpMux community registry

Vardoger is live in [mcpmux/mcp-servers](https://github.com/mcpmux/mcp-servers),
the community-maintained JSON registry consumed by the
[McpMux](https://mcpmux.com) desktop gateway. McpMux proxies MCP tools into
Cursor, Claude Desktop, VS Code, and Windsurf through a single endpoint, so
the listing makes vardoger reachable from every McpMux client at once. The
original submission was merged in
[PR #113](https://github.com/mcpmux/mcp-servers/pull/113).

## What's in this folder

- [`vardoger.json`](./vardoger.json) — the server definition, shaped to the
  repo's `schemas/server-definition.schema.json` (JSON Schema 2020-12) with
  schema version `2.1`.

## Original submission recipe

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

5. After merge, the bundle updates within roughly an hour and McpMux desktop
   clients pick up the entry automatically.

## Maintenance

When vardoger ships a breaking change to the MCP tools or CLI flags, open a
follow-up PR against the same `servers/io.github-dstrupl-vardoger.json`
updating the transport block (and the `changelog_url` field if we decide to
expose one). Update [`../../MARKETPLACE_STATUS.md`](../../MARKETPLACE_STATUS.md)
in lock-step.
