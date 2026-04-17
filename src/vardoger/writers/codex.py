# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Write vardoger output to Codex's AGENTS.md.

Codex reads global instructions from:
  ~/.codex/AGENTS.md

vardoger manages a fenced section delimited by HTML comments so it can
be idempotently updated without disturbing user-authored content.
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
    """Wrap content in vardoger markers."""
    return f"{START_MARKER}\n{content}\n{END_MARKER}"


def _agents_path(scope: str, project_path: Path | None) -> Path:
    if scope == "project":
        base = project_path or Path.cwd()
        return base / "AGENTS.md"
    codex_dir = Path.home() / ".codex"
    return codex_dir / "AGENTS.md"


def write_codex_rules(
    content: str,
    scope: str = "global",
    project_path: Path | None = None,
) -> Path:
    """Write the vardoger section into an AGENTS.md file for Codex.

    scope="global": writes to ~/.codex/AGENTS.md
    scope="project": writes to <project>/AGENTS.md

    If the file already exists and contains a vardoger section, that section
    is replaced. Otherwise the section is appended.

    Returns the path of the written file.
    """
    output_path = _agents_path(scope, project_path)
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

    logger.info("Wrote Codex rules to %s", output_path)
    return output_path


def read_codex_rules(
    scope: str = "global",
    project_path: Path | None = None,
) -> str | None:
    """Return only the content inside the vardoger-managed fenced block.

    Returns ``None`` if AGENTS.md is absent or does not contain a vardoger
    section. Other (user-authored) content in AGENTS.md is ignored.
    """
    output_path = _agents_path(scope, project_path)
    if not output_path.is_file():
        return None
    existing = output_path.read_text(encoding="utf-8")
    match = _SECTION_RE.search(existing)
    if match is None:
        return None
    section = match.group(0)
    inner = section[len(START_MARKER) : -len(END_MARKER)]
    return inner.strip("\n")


def clear_codex_rules(
    scope: str = "global",
    project_path: Path | None = None,
) -> bool:
    """Remove the vardoger-managed fenced block from AGENTS.md.

    Leaves user-authored content intact. If AGENTS.md becomes empty after
    removal, the file itself is deleted. Returns True if a block was removed.
    """
    output_path = _agents_path(scope, project_path)
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
    logger.info("Removed Codex vardoger section from %s", output_path)
    return True
