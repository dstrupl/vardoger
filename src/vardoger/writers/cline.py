# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Write vardoger output to Cline's user-global or project rules.

Cline reads user-global rules from ``~/Documents/Cline/Rules``. vardoger
owns a dedicated ``vardoger.md`` file in that directory.

Cline reads project rules from either:

* ``<project>/.clinerules`` — a single markdown file. vardoger manages a
  fenced section (``<!-- vardoger:start -->`` / ``<!-- vardoger:end -->``)
  to avoid clobbering hand-authored content.
* ``<project>/.clinerules/`` — a directory of rules files. When a directory
  exists, vardoger owns a dedicated file inside it: ``vardoger.md``.
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


def cline_global_rules_dir() -> Path:
    """Return Cline's documented default user-global rules directory."""
    return Path.home() / "Documents" / "Cline" / "Rules"


def write_cline_rules(
    content: str,
    scope: str = "global",
    project_path: Path | None = None,
) -> Path:
    """Write vardoger rules for Cline and return the path written.

    Global rules use Cline's documented user rules directory. Project rules
    retain the existing ``.clinerules`` file-or-directory behavior and require
    a real project marker (see https://github.com/dstrupl/vardoger/issues/21).
    """
    if scope == "project":
        ensure_project(project_path or Path.cwd(), platform="Cline")
    output_path, dedicated = _resolve_target(scope, project_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if dedicated:
        output_path.write_text(content, encoding="utf-8")
        logger.info("Wrote Cline %s rules to %s (dedicated file)", scope, output_path)
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
    logger.info("Wrote Cline rules to %s (fenced section)", output_path)
    return output_path


def read_cline_rules(
    scope: str = "global",
    project_path: Path | None = None,
) -> str | None:
    """Return the vardoger-managed rule body, or ``None`` if absent."""
    output_path, dedicated = _resolve_target(scope, project_path)
    if not output_path.is_file():
        return None

    if dedicated:
        return output_path.read_text(encoding="utf-8")

    existing = output_path.read_text(encoding="utf-8")
    match = _SECTION_RE.search(existing)
    if match is None:
        return None
    section = match.group(0)
    inner = section[len(START_MARKER) : -len(END_MARKER)]
    return inner.strip("\n")


def clear_cline_rules(
    scope: str = "global",
    project_path: Path | None = None,
) -> bool:
    """Remove vardoger's contribution from the selected Cline rules scope."""
    output_path, dedicated = _resolve_target(scope, project_path)
    if not output_path.is_file():
        return False

    if dedicated:
        output_path.unlink()
        logger.info("Removed Cline %s vardoger.md at %s", scope, output_path)
        return True

    existing = output_path.read_text(encoding="utf-8")
    if not _SECTION_RE.search(existing):
        return False
    updated = _SECTION_RE.sub("", existing).strip()
    if updated:
        output_path.write_text(updated + "\n", encoding="utf-8")
    else:
        output_path.unlink()
    logger.info("Removed Cline vardoger section from %s", output_path)
    return True


def _wrap(content: str) -> str:
    return f"{START_MARKER}\n{content}\n{END_MARKER}"


def _resolve_project_target(project_path: Path | None) -> tuple[Path, bool]:
    """Return (path, uses_dedicated_file).

    If ``.clinerules`` exists as a directory, target ``.clinerules/vardoger.md``
    as a dedicated file. Otherwise target the ``.clinerules`` file itself with
    a fenced section.
    """
    base = project_path or Path.cwd()
    candidate = base / ".clinerules"
    if candidate.is_dir():
        return candidate / "vardoger.md", True
    return candidate, False


def _resolve_target(scope: str, project_path: Path | None) -> tuple[Path, bool]:
    """Return the rules path and whether vardoger owns the whole file."""
    if scope == "global":
        return cline_global_rules_dir() / "vardoger.md", True
    return _resolve_project_target(project_path)
