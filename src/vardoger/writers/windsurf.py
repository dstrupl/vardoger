# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Write vardoger output to Windsurf's rules files.

Windsurf supports two rules scopes:

* Global: ``~/.codeium/windsurf/memories/global_rules.md`` — a user-shared
  file, so vardoger manages a fenced section
  (``<!-- vardoger:start -->`` / ``<!-- vardoger:end -->``) and leaves any
  hand-authored content outside the block intact.
* Project: ``<project>/.windsurf/rules/vardoger.md`` — a dedicated file owned
  by vardoger; overwritten in place.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

START_MARKER = "<!-- vardoger:start -->"
END_MARKER = "<!-- vardoger:end -->"

_SECTION_RE = re.compile(
    re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
    re.DOTALL,
)


def _wrap(content: str) -> str:
    return f"{START_MARKER}\n{content}\n{END_MARKER}"


def _rules_path(scope: str, project_path: Path | None) -> Path:
    if scope == "project":
        base = project_path or Path.cwd()
        return base / ".windsurf" / "rules" / "vardoger.md"
    return Path.home() / ".codeium" / "windsurf" / "memories" / "global_rules.md"


def write_windsurf_rules(
    content: str,
    scope: str = "global",
    project_path: Path | None = None,
) -> Path:
    """Write Windsurf rules for the given scope and return the path written."""
    output_path = _rules_path(scope, project_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if scope == "project":
        output_path.write_text(content, encoding="utf-8")
        logger.info("Wrote Windsurf project rules to %s", output_path)
        return output_path

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
    logger.info("Wrote Windsurf global rules to %s", output_path)
    return output_path


def read_windsurf_rules(
    scope: str = "global",
    project_path: Path | None = None,
) -> str | None:
    """Return the vardoger-managed content for the given scope, or None."""
    output_path = _rules_path(scope, project_path)
    if not output_path.is_file():
        return None

    if scope == "project":
        return output_path.read_text(encoding="utf-8")

    existing = output_path.read_text(encoding="utf-8")
    match = _SECTION_RE.search(existing)
    if match is None:
        return None
    section = match.group(0)
    inner = section[len(START_MARKER) : -len(END_MARKER)]
    return inner.strip("\n")


def clear_windsurf_rules(
    scope: str = "global",
    project_path: Path | None = None,
) -> bool:
    """Remove vardoger's contribution for the given scope."""
    output_path = _rules_path(scope, project_path)
    if not output_path.is_file():
        return False

    if scope == "project":
        output_path.unlink()
        logger.info("Removed Windsurf project rules at %s", output_path)
        return True

    existing = output_path.read_text(encoding="utf-8")
    if not _SECTION_RE.search(existing):
        return False
    updated = _SECTION_RE.sub("", existing).strip()
    if updated:
        output_path.write_text(updated + "\n", encoding="utf-8")
    else:
        output_path.unlink()
    logger.info("Removed Windsurf vardoger section from %s", output_path)
    return True
