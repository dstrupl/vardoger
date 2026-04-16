# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Prompt writers that deliver generated content to each platform's config."""

from vardoger.writers.claude_code import write_claude_code_rules
from vardoger.writers.codex import write_codex_rules
from vardoger.writers.cursor import write_cursor_rules

__all__ = [
    "write_claude_code_rules",
    "write_codex_rules",
    "write_cursor_rules",
]
