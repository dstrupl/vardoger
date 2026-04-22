# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Shared project-marker validation for the platform writers.

Every writer's project-scope branch falls back to :func:`Path.cwd()` when
no ``project_path`` is supplied. Because MCP servers launched from an
IDE routinely run with ``cwd=$HOME``, that fallback used to produce a
file at a location the respective tool would never load from — a silent
failure mode first documented for Cursor in
https://github.com/dstrupl/vardoger/issues/18 and generalised in
https://github.com/dstrupl/vardoger/issues/21.

This module centralises the "does this directory look like a project?"
check so each writer can refuse to run against a non-project path
instead of dropping a file nobody reads.

The marker list intentionally matches Cursor's: any VCS metadata, a
language manifest, an ``AGENTS.md`` authored by the user, or an
existing platform-owned directory (``.cursor``) all count as evidence
that Cursor (and by extension the other tools) would actually load
rules from here. The per-tool "owned" directories (``.claude``,
``.windsurf``, ``.clinerules``, ``.github``) are *not* added to the
marker set — those would bootstrap themselves into being valid the
moment vardoger wrote into them, defeating the check.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_MARKERS: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "pyproject.toml",
        "package.json",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "AGENTS.md",
        ".cursor",
    }
)


class NotAProjectError(RuntimeError):
    """Raised when a target path cannot be identified as a project root.

    Each platform's tool (Cursor, Claude Code, Codex, OpenClaw, Copilot
    CLI, Windsurf, Cline) loads project-scope rules from a directory
    nested inside a real project. Writing outside such a directory
    produces a file the tool will never read, so writers refuse and
    surface this error instead.
    """


def find_project_root(start: Path) -> Path | None:
    """Walk up from ``start`` looking for a project marker.

    Returns the first directory (``start`` itself or an ancestor) that
    contains any member of :data:`PROJECT_MARKERS`, or ``None`` if no
    such directory is found before reaching the filesystem root.
    """
    try:
        current = start.resolve()
    except OSError:
        return None

    # ``Path.parents`` stops at the filesystem root; we also want to
    # inspect ``current`` itself, hence the chain.
    for candidate in (current, *current.parents):
        for marker in PROJECT_MARKERS:
            if (candidate / marker).exists():
                return candidate
    return None


def ensure_project(project_path: Path, *, platform: str | None = None) -> None:
    """Refuse to operate on a path that has no project marker in scope.

    ``platform`` (when supplied) is mentioned in the error message so
    the calling tool's user sees a recognisable hint in the traceback /
    MCP response — the check itself is platform-agnostic.
    """
    root = find_project_root(project_path)
    if root is not None:
        return

    platform_note = f" {platform}" if platform else ""
    msg = (
        f"{project_path} is not inside a project (no .git, language manifest, "
        "AGENTS.md or .cursor/ found in it or any ancestor);"
        f"{platform_note} does not load rules from paths like this, so "
        "refusing to write. Pass an explicit project_path that points at a "
        "real project root, or choose a different scope."
    )
    raise NotAProjectError(msg)


# Private aliases kept so the legacy ``from vardoger.writers.cursor import
# _find_project_root, _ensure_project`` imports continue to work. They are
# not part of the module's public surface.
_find_project_root = find_project_root
_ensure_project = ensure_project
