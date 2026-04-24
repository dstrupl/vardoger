# syntax=docker/dockerfile:1.7
#
# vardoger MCP server image.
#
# Built from the pinned commit referenced in
# plugins/docker-mcp/server.yaml by Docker's mcp-registry pipeline and
# published as mcp/vardoger on Docker Hub. Launched on stdio as
# `vardoger mcp` by Docker Desktop's MCP Toolkit and other MCP hosts that
# consume the Docker MCP Registry feed.
#
# Runtime contract: the caller bind-mounts their host $HOME to /host-home
# and HOME inside the container points there, so the Path.home() lookups
# vardoger does for ~/.cursor, ~/.claude, ~/.codex, ~/.openclaw, ~/.copilot,
# ~/.codeium/windsurf, and ~/.vardoger resolve against real host paths.
# Cline history is not accessible in this image because Cline's location
# depends on the host-OS VS Code globalStorage layout (documented in
# plugins/docker-mcp/README.md); Cline users should install via pipx.

FROM python:3.12-slim AS build

WORKDIR /src

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN pip install --no-cache-dir --prefix=/install .


FROM python:3.12-slim

COPY --from=build /install /usr/local

# Non-root runtime user. Docker Desktop's filesystem shim maps UIDs
# transparently across bind mounts on macOS and Windows; on Linux hosts
# whose user UID differs from 1000 the caller can override with
# `--user $(id -u):$(id -g)` at `docker run` time.
RUN useradd --create-home --home-dir /home/vardoger --uid 1000 \
        --shell /usr/sbin/nologin vardoger \
 && mkdir -p /host-home \
 && chown vardoger:vardoger /host-home

USER vardoger
ENV HOME=/host-home \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /host-home

ENTRYPOINT ["vardoger", "mcp"]
