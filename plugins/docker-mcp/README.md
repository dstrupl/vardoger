# vardoger — Docker MCP Registry submission

Tracked copy of the [`docker/mcp-registry`](https://github.com/docker/mcp-registry)
entry that publishes `mcp/vardoger` on Docker Hub and lists vardoger in Docker
Desktop's MCP Toolkit.

## What's in this folder

- [`server.yaml`](./server.yaml) — the registry metadata Docker's
  `task create` wizard emits, pinned to a specific vardoger release commit so
  Docker's build pipeline produces a reproducible `mcp/vardoger:<tag>` image.

## Runtime contract

The runtime image lives at [`../../Dockerfile`](../../Dockerfile) in the
repository root. It:

- Builds vardoger from the pinned source commit (multi-stage Python 3.12 slim).
- Runs as a non-root user (UID 1000).
- Exposes `vardoger mcp` as the `ENTRYPOINT` so the MCP host drives it over
  stdio, identical to `pipx`-installed deployments.
- Expects the caller's host `$HOME` to be bind-mounted at `/host-home` and
  sets `HOME=/host-home` so `Path.home()` resolves against real host paths
  (`~/.cursor`, `~/.claude`, `~/.codex`, `~/.openclaw`, `~/.copilot`,
  `~/.codeium/windsurf`, `~/.vardoger`).

### Platforms not covered by this image

- **Cline** — Cline stores its task history under VS Code's `globalStorage`,
  which lives at different host paths on macOS (`~/Library/Application Support/Code/...`),
  Linux (`~/.config/Code/...`), and Windows (`%APPDATA%\Code\...`). vardoger's
  Cline adapter resolves that path from `sys.platform` at runtime, which
  inside a Linux container always reports `linux`. Users on Cline should
  install via `pipx install vardoger` instead of the Docker image.

## Before submitting (one-time prep)

1. **Cut a PyPI release.** `server.yaml` points at a specific commit in
   `dstrupl/vardoger`. Cut the release (e.g. `v0.3.1`) and let the
   [`publish.yml`](../../.github/workflows/publish.yml) workflow push the new
   wheel to PyPI. The Docker Hub image tag Docker builds for us tracks the
   tag plus `latest`, so a bump here means a bump on Docker Hub after the
   registry merges the PR.
2. **Pin `source.commit`.** Replace the `TBD` placeholder in
   [`server.yaml`](./server.yaml) with the commit SHA of the release tag
   (`git rev-parse v0.3.1`).
3. **Smoke-test the image locally.** From a checkout at that commit:

   ```bash
   docker build -t mcp/vardoger:dev .
   docker run --rm -i \
     -e VARDOGER_MCP_PLATFORM=cursor \
     -v "$HOME:/host-home" \
     mcp/vardoger:dev
   # (stdio — the process stays attached; exit with Ctrl-D / SIGINT)
   ```

   The container should start, read `$HOME/.cursor/...`, and respond on
   stdio. Any `PermissionError` against `/host-home/.vardoger/state.tmp`
   means the bind mount is not writable for UID 1000; re-run with
   `--user $(id -u):$(id -g)`.

## Submitting the PR

Docker's contributor flow (see
[`docker/mcp-registry/CONTRIBUTING.md`](https://github.com/docker/mcp-registry/blob/main/CONTRIBUTING.md))
expects the entry under `servers/<name>/server.yaml`. From a fresh clone of
that repo on a machine with Go 1.24+, Docker Desktop, and
[Task](https://taskfile.dev/):

```bash
# Option A — let Docker's wizard populate the file from the pinned repo+commit:
task wizard   # follow the prompts; point it at github.com/dstrupl/vardoger

# Option B — scaffold from scratch and then overwrite with our tracked copy:
task create -- --category productivity https://github.com/dstrupl/vardoger
cp <vardoger-workspace>/plugins/docker-mcp/server.yaml servers/vardoger/server.yaml

# Either way, run both checks before opening the PR:
task validate -- --name vardoger
task build    -- --tools  vardoger
```

Both commands must exit green — the pipeline builds `mcp/vardoger` from the
pinned commit, runs it, and verifies `tools/list` returns vardoger's MCP
tools. File the PR against
[`docker/mcp-registry`](https://github.com/docker/mcp-registry) using
`.github/PULL_REQUEST_TEMPLATE.md`.

After the PR merges, Docker builds and signs `mcp/vardoger` on Docker Hub,
and the entry becomes installable from Docker Desktop's MCP Toolkit. Update
[`../../MARKETPLACE_STATUS.md`](../../MARKETPLACE_STATUS.md) to flip the row
to **Live** and tick the matching Phase 4 checkbox in
[`../../PRD.md`](../../PRD.md).
