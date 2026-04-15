"""History reader adapters for each supported platform."""

from vardoger.history.cursor import discover_cursor_files, read_cursor_history
from vardoger.history.claude_code import discover_claude_code_files, read_claude_code_history
from vardoger.history.codex import discover_codex_files, read_codex_history

__all__ = [
    "discover_cursor_files",
    "discover_claude_code_files",
    "discover_codex_files",
    "read_cursor_history",
    "read_claude_code_history",
    "read_codex_history",
]
