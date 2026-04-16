# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""MCP server for Cursor integration.

Exposes vardoger's analysis pipeline as MCP tools:
  - vardoger_personalize() — entry point: returns orchestration instructions
  - vardoger_prepare() — returns batch metadata or a specific batch with summarize prompt
  - vardoger_synthesize_prompt() — returns the synthesis prompt
  - vardoger_write() — writes the final personalization to .cursor/rules/vardoger.md

The host AI model performs the actual analysis between prepare and write.

Usage (direct):
    python -m vardoger.mcp_server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from vardoger.digest import batch_conversations, format_batch
from vardoger.history.cursor import read_cursor_history
from vardoger.prompts import summarize_prompt, synthesize_prompt
from vardoger.staleness import check_staleness
from vardoger.writers.cursor import write_cursor_rules

mcp = FastMCP("vardoger")

_ORCHESTRATION_INSTRUCTIONS = """\
# vardoger — Personalize Your Assistant

Follow these steps to analyze the user's conversation history and generate \
a personalization. Report progress to the user after each step.

## Step 1: Check status

Call `vardoger_status()`.

If the personalization is fresh (not stale), tell the user their \
personalization is up to date and ask if they want to re-run anyway. \
If stale or never generated, continue.

## Step 2: Get batch metadata

Call `vardoger_prepare(batch=0)`.

This returns JSON like `{"batches": 3, "total_conversations": 29}`. \
Note the number of batches. Tell the user: "Found N conversations in M batches. \
Analyzing..."

## Step 3: Summarize each batch

For each batch from 1 to M, call `vardoger_prepare(batch=N)`.

The output contains a summarization prompt and conversation data. Read it \
carefully and produce a concise bullet-point summary of the behavioral signals \
you observe. Keep each summary for later.

Tell the user: "Analyzing batch N of M..."

## Step 4: Get the synthesis prompt

Call `vardoger_synthesize_prompt()`.

## Step 5: Synthesize

Following the synthesis prompt, combine all your batch summaries into a single \
personalization. The output should be clean markdown with actionable instructions.

## Step 6: Write the result

Call `vardoger_write(content="YOUR_PERSONALIZATION_HERE")`.

## Step 7: Report to the user

Tell the user what was written and where. Mention they can ask you to \
re-run vardoger any time to update the personalization.
"""


@mcp.tool()
def vardoger_status() -> str:
    """Check if the Cursor personalization is up to date.

    Returns a status report indicating whether the personalization needs
    refreshing, how many days since the last update, and how many new or
    changed conversations exist.
    """
    import json

    report = check_staleness("cursor")
    return json.dumps(
        {
            "platform": report.platform,
            "is_stale": report.is_stale,
            "days_since_generation": report.days_since_generation,
            "new_conversations": report.new_conversations,
            "changed_conversations": report.changed_conversations,
            "reason": report.reason,
        },
        indent=2,
    )


@mcp.tool()
def vardoger_personalize() -> str:
    """Personalize the AI assistant from conversation history.

    Call this tool when the user asks to personalize their assistant, analyze
    their conversation history, or mentions "vardoger". It returns step-by-step
    instructions for you to follow using the other vardoger tools.
    """
    return _ORCHESTRATION_INSTRUCTIONS


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
        return json.dumps(
            {
                "batches": len(batches),
                "total_conversations": total_convos,
            }
        )

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

    from vardoger.checkpoint import CheckpointStore

    target = Path(project_path) if project_path else None
    output = write_cursor_rules(content, project_path=target)

    store = CheckpointStore()
    store.record_generation("cursor", conversations_analyzed=0, output_path=str(output))
    store.save()

    return f"vardoger: wrote personalization to {output}"


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
