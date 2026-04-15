"""Prompt writers that deliver generated content to each platform's config."""

from vardoger.writers.cursor import write_cursor_rules
from vardoger.writers.claude_code import write_claude_code_rules
from vardoger.writers.codex import write_codex_rules

__all__ = [
    "write_cursor_rules",
    "write_claude_code_rules",
    "write_codex_rules",
]
