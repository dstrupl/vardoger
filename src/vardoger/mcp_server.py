"""MCP server for Cursor integration.

Exposes vardoger's two-stage analysis pipeline as MCP tools:
  1. vardoger_prepare() — returns batch metadata or a specific batch with summarize prompt
  2. vardoger_synthesize_prompt() — returns the synthesis prompt
  3. vardoger_write() — writes the final personalization to .cursor/rules/vardoger.md

The host AI model performs the actual analysis between prepare and write.

Usage (direct):
    python -m vardoger.mcp_server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from vardoger.digest import batch_conversations, format_batch
from vardoger.history.cursor import read_cursor_history
from vardoger.prompts import summarize_prompt, synthesize_prompt
from vardoger.writers.cursor import write_cursor_rules

mcp = FastMCP("vardoger")

_cached_batches: list | None = None


def _get_batches() -> list:
    global _cached_batches
    if _cached_batches is None:
        conversations = read_cursor_history()
        _cached_batches = batch_conversations(conversations)
    return _cached_batches


@mcp.tool()
def vardoger_prepare(batch: int = 0) -> str:
    """Prepare conversation history for analysis.

    Call without arguments (or batch=0) to get metadata about how many
    batches are available. Then call with batch=1, batch=2, etc. to get
    each batch of conversations along with a summarization prompt.

    Args:
        batch: Batch number (1-based). 0 or omitted returns metadata.

    Returns:
        JSON metadata or batch content with summarize prompt.
    """
    import json

    batches = _get_batches()
    total_convos = sum(len(b) for b in batches)

    if batch == 0:
        return json.dumps({
            "batches": len(batches),
            "total_conversations": total_convos,
        })

    if batch < 1 or batch > len(batches):
        return f"Batch {batch} out of range (1-{len(batches)})."

    batch_text = format_batch(batches[batch - 1], batch, len(batches))
    prompt = summarize_prompt()
    return f"{prompt}\n\n---\n\n{batch_text}"


@mcp.tool()
def vardoger_synthesize_prompt() -> str:
    """Get the synthesis prompt for combining batch summaries into a personalization.

    Call this after you have summarized all batches. Use the returned prompt
    to guide your synthesis of all batch summaries into a final personalization.

    Returns:
        The synthesis prompt text.
    """
    return synthesize_prompt()


@mcp.tool()
def vardoger_write(content: str, project_path: str = "") -> str:
    """Write the final personalization to the Cursor rules file.

    Call this after synthesizing all batch summaries into a personalization.
    Pass the personalization text as the content argument.

    Args:
        content: The personalization markdown to write.
        project_path: Optional project directory. If empty, uses current directory.

    Returns:
        Confirmation of what was written.
    """
    from pathlib import Path

    target = Path(project_path) if project_path else None
    output = write_cursor_rules(content, project_path=target)
    return f"vardoger: wrote personalization to {output}"


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
