# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""History reader adapters for each supported platform."""

from vardoger.history.claude_code import discover_claude_code_files, read_claude_code_history
from vardoger.history.codex import discover_codex_files, read_codex_history
from vardoger.history.cursor import discover_cursor_files, read_cursor_history

__all__ = [
    "discover_claude_code_files",
    "discover_codex_files",
    "discover_cursor_files",
    "read_claude_code_history",
    "read_codex_history",
    "read_cursor_history",
]
