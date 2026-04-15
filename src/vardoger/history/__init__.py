"""History reader adapters for each supported platform."""

from vardoger.history.cursor import read_cursor_history
from vardoger.history.claude_code import read_claude_code_history
from vardoger.history.codex import read_codex_history

__all__ = [
    "read_cursor_history",
    "read_claude_code_history",
    "read_codex_history",
]
