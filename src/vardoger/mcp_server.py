"""MCP server for Cursor integration.

Exposes vardoger analysis as an MCP tool that Cursor's agent can invoke.
Runs over stdio transport.

Usage (direct):
    python -m vardoger.mcp_server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from vardoger.analyze import analyze
from vardoger.history.cursor import read_cursor_history
from vardoger.writers.cursor import write_cursor_rules

mcp = FastMCP("vardoger")


@mcp.tool()
def vardoger_analyze(project_path: str = "") -> str:
    """Analyze your Cursor conversation history and generate a personalized rule file.

    Reads all agent transcripts from your Cursor history, extracts patterns,
    and writes a personalized rule to .cursor/rules/vardoger.md in the
    specified project (or the current directory).

    Args:
        project_path: Optional project directory. If empty, uses current directory.

    Returns:
        Summary of what was generated.
    """
    from pathlib import Path

    conversations = read_cursor_history()

    if not conversations:
        return "No Cursor conversation history found."

    prompt_addition = analyze(conversations)

    target = Path(project_path) if project_path else None
    output = write_cursor_rules(prompt_addition, project_path=target)

    total_messages = sum(c.message_count for c in conversations)
    return (
        f"vardoger: wrote personalization to {output}\n"
        f"Analyzed {len(conversations)} conversations with {total_messages} messages."
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
