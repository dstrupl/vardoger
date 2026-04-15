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
    if scope == "project":
        base = project_path or Path.cwd()
        output_path = base / "AGENTS.md"
    else:
        codex_dir = Path.home() / ".codex"
        codex_dir.mkdir(parents=True, exist_ok=True)
        output_path = codex_dir / "AGENTS.md"

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
