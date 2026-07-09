# vardoger — Official MCP Registry

Vardoger is live in the official
[Model Context Protocol Registry](https://github.com/modelcontextprotocol/registry)
as `io.github.dstrupl/vardoger`. The registry feed is consumed by Docker
Desktop's MCP gallery, VS Code's MCP picker, Windsurf's enterprise Internal MCP
Registry feature, and other MCP hosts.

The public registry currently serves `0.3.1`; the tracked `server.json` is
prepared for `0.3.2` and should be republished now that the corresponding PyPI
release exists.

## What's in this folder

- [`server.json`](./server.json) — the registry metadata, conforming to the
  December 2025 schema (`https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json`).

## Publishing a new version

1. **PyPI ownership marker.** The registry verifies ownership by searching for
   `mcp-name: io.github.dstrupl/vardoger` in the package's README (which PyPI
   publishes as the package description). The marker is already present in the
   repo-root `README.md` and in the published package description.
2. **Release to PyPI first.** The registry only hosts metadata. Confirm the
   version in `server.json` already exists on PyPI, and keep both registry
   version fields in lock-step with `pyproject.toml`.
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
curl -s 'https://prod.registry.modelcontextprotocol.io/v0.1/servers?search=vardoger&limit=10' \
  | jq '.servers[] | select(.server.name=="io.github.dstrupl/vardoger")'
```

Update [`../../MARKETPLACE_STATUS.md`](../../MARKETPLACE_STATUS.md) once the
response includes the new version. The matching Phase 4 checkbox in
[`../../PRD.md`](../../PRD.md) is already complete.
