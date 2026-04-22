# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Write vardoger output to GitHub Copilot's instructions files.

Copilot CLI reads instructions from two user-shared markdown files:
  ~/.copilot/copilot-instructions.md              (global)
  <project>/.github/copilot-instructions.md       (project)

Both files are typically authored by the user or their team, so vardoger
manages a fenced section delimited by HTML comments
(``<!-- vardoger:start -->`` / ``<!-- vardoger:end -->``) so we can update
the section idempotently without disturbing hand-written content.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from vardoger.writers._projects import ensure_project

logger = logging.getLogger(__name__)

START_MARKER = "<!-- vardoger:start -->"
END_MARKER = "<!-- vardoger:end -->"

_SECTION_RE = re.compile(
    re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
    re.DOTALL,
)


def _wrap(content: str) -> str:
    return f"{START_MARKER}\n{content}\n{END_MARKER}"


def _instructions_path(scope: str, project_path: Path | None) -> Path:
    if scope == "project":
        base = project_path or Path.cwd()
        return base / ".github" / "copilot-instructions.md"
    return Path.home() / ".copilot" / "copilot-instructions.md"


def write_copilot_rules(
    content: str,
    scope: str = "global",
    project_path: Path | None = None,
) -> Path:
    """Write the vardoger section into a Copilot instructions file.

    scope="global": writes to ``~/.copilot/copilot-instructions.md``
    scope="project": writes to ``<project>/.github/copilot-instructions.md``.
    The base directory (or an ancestor) must contain a project marker,
    otherwise :class:`vardoger.writers._projects.NotAProjectError` is
    raised (see https://github.com/dstrupl/vardoger/issues/21).

    If the file already exists and contains a vardoger section, that section
    is replaced. Otherwise the section is appended. Returns the path that was
    written.
    """
    if scope == "project":
        ensure_project(project_path or Path.cwd(), platform="GitHub Copilot CLI")
    output_path = _instructions_path(scope, project_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    section = _wrap(content)

    if output_path.is_file():
        existing = output_path.read_text(encoding="utf-8")
        if _SECTION_RE.search(existing):
            updated = _SECTION_RE.sub(section, existing)
        else:
            updated = existing.rstrip() + "\n\n" + section + "\n"
    else:
        updated = section + "\n"

    output_path.write_text(updated, encoding="utf-8")

    logger.info("Wrote Copilot rules to %s", output_path)
    return output_path


def read_copilot_rules(
    scope: str = "global",
    project_path: Path | None = None,
) -> str | None:
    """Return only the content inside the vardoger-managed fenced block.

    Returns ``None`` if the instructions file is absent or does not contain a
    vardoger section. User-authored content outside the section is ignored.
    """
    output_path = _instructions_path(scope, project_path)
    if not output_path.is_file():
        return None
    existing = output_path.read_text(encoding="utf-8")
    match = _SECTION_RE.search(existing)
    if match is None:
        return None
    section = match.group(0)
    inner = section[len(START_MARKER) : -len(END_MARKER)]
    return inner.strip("\n")


def clear_copilot_rules(
    scope: str = "global",
    project_path: Path | None = None,
) -> bool:
    """Remove the vardoger-managed fenced block from the instructions file.

    Leaves user-authored content intact. If the file becomes empty after
    removal, the file itself is deleted. Returns True if a block was removed.
    """
    output_path = _instructions_path(scope, project_path)
    if not output_path.is_file():
        return False
    existing = output_path.read_text(encoding="utf-8")
    if not _SECTION_RE.search(existing):
        return False
    updated = _SECTION_RE.sub("", existing).strip()
    if updated:
        output_path.write_text(updated + "\n", encoding="utf-8")
    else:
        output_path.unlink()
    logger.info("Removed Copilot vardoger section from %s", output_path)
    return True
