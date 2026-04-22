# vardoger — Official MCP Registry submission

Draft submission for the official [Model Context Protocol Registry](https://github.com/modelcontextprotocol/registry)
(`registry.modelcontextprotocol.io`). Landing here gives vardoger presence in a
feed that is ingested by Docker Desktop's MCP gallery, VS Code's MCP picker,
Windsurf's enterprise Internal MCP Registry feature, and any other MCP host
that syncs the canonical registry.

## What's in this folder

- [`server.json`](./server.json) — the registry metadata, conforming to the
  December 2025 schema (`https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json`).

## Before publishing (one-time prep)

1. **PyPI ownership marker.** The registry verifies ownership by searching for
   `mcp-name: io.github.dstrupl/vardoger` in the package's README (which PyPI
   publishes as the package description). That marker is already added to the
   repo-root `README.md` as an HTML comment, so the next PyPI release will
   carry it automatically.
2. **Release to PyPI.** The registry only hosts metadata — the package itself
   must exist on PyPI at the version in `server.json`. Bump vardoger, build,
   and `uv publish` (or `twine upload`) before calling `mcp-publisher publish`,
   and keep `packages[0].version` in this file in lock-step with
   `pyproject.toml`.
3. **Validate locally.** Install the publisher CLI and re-generate the
   scaffold so any new required fields get caught:

   ```bash
   # macOS / Linux
   curl -L "https://github.com/modelcontextprotocol/registry/releases/latest/download/mcp-publisher_$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/').tar.gz" \
     | tar xz mcp-publisher && sudo mv mcp-publisher /usr/local/bin/
   mcp-publisher --help

   # From a scratch directory, generate a reference server.json template and
   # diff it against this file:
   mkdir -p /tmp/vardoger-mcp && cd /tmp/vardoger-mcp
   mcp-publisher init
   diff -u server.json <workspace>/plugins/mcp-registry/server.json
   ```

   In particular, confirm the `packageArguments` shape is accepted — the
   registry's `PositionalArgument`/`NamedArgument` definitions use an
   `allOf`/`oneOf` layout that's easier to verify by running the CLI than by
   reading the schema.

## Publishing

```bash
cd <workspace>
cp plugins/mcp-registry/server.json ./server.json   # CLI expects it in CWD
mcp-publisher login github                           # browser GitHub OAuth
mcp-publisher publish
rm server.json                                       # keep the tracked copy in plugins/mcp-registry/
```

Verify with:

```bash
curl -s https://registry.modelcontextprotocol.io/v0/servers \
  | jq '.servers[] | select(.name=="io.github.dstrupl/vardoger")'
```

Update [`../../MARKETPLACE_STATUS.md`](../../MARKETPLACE_STATUS.md) to mark the
row **Live** once the response includes the current version, and tick the
matching Phase 4 checkbox in [`../../PRD.md`](../../PRD.md).
