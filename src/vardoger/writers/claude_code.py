# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Write vardoger output to Claude Code's rules directory.

Claude Code reads modular rules from:
  <project>/.claude/rules/**/*.md   (project-level)
  ~/.claude/rules/*.md              (user-level, global)
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _rules_path(scope: str, project_path: Path | None) -> Path:
    if scope == "project":
        base = project_path or Path.cwd()
        rules_dir = base / ".claude" / "rules"
    else:
        rules_dir = Path.home() / ".claude" / "rules"
    return rules_dir / "vardoger.md"


def write_claude_code_rules(
    content: str,
    scope: str = "global",
    project_path: Path | None = None,
) -> Path:
    """Write the vardoger rule file for Claude Code.

    scope="global": writes to ~/.claude/rules/vardoger.md
    scope="project": writes to <project>/.claude/rules/vardoger.md

    Returns the path of the written file.
    """
    output_path = _rules_path(scope, project_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")

    logger.info("Wrote Claude Code rules to %s", output_path)
    return output_path


def read_claude_code_rules(
    scope: str = "global",
    project_path: Path | None = None,
) -> str | None:
    """Return the current contents of the vardoger rules file, or None."""
    output_path = _rules_path(scope, project_path)
    if not output_path.is_file():
        return None
    return output_path.read_text(encoding="utf-8")


def clear_claude_code_rules(
    scope: str = "global",
    project_path: Path | None = None,
) -> bool:
    """Delete the vardoger rules file if it exists. Returns True if removed."""
    output_path = _rules_path(scope, project_path)
    if output_path.is_file():
        output_path.unlink()
        logger.info("Removed Claude Code rules at %s", output_path)
        return True
    return False
