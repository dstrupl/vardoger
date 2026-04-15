"""Write vardoger output to Claude Code's rules directory.

Claude Code reads modular rules from:
  <project>/.claude/rules/**/*.md   (project-level)
  ~/.claude/rules/*.md              (user-level, global)
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


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
    if scope == "project":
        base = project_path or Path.cwd()
        rules_dir = base / ".claude" / "rules"
    else:
        rules_dir = Path.home() / ".claude" / "rules"

    rules_dir.mkdir(parents=True, exist_ok=True)

    output_path = rules_dir / "vardoger.md"
    output_path.write_text(content, encoding="utf-8")

    logger.info("Wrote Claude Code rules to %s", output_path)
    return output_path
