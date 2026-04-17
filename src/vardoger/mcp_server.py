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

import functools

from mcp.server.fastmcp import FastMCP

from vardoger.digest import batch_conversations, format_batch
from vardoger.feedback import detect_edits
from vardoger.history.cursor import read_cursor_history
from vardoger.personalization import annotate_tentative, parse_personalization
from vardoger.prompts import feedback_context_prompt, summarize_prompt, synthesize_prompt
from vardoger.staleness import check_staleness
from vardoger.writers.cursor import (
    clear_cursor_rules,
    read_cursor_rules,
    write_cursor_rules,
)

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
    report = check_staleness("cursor")
    return report.model_dump_json(indent=2)


@mcp.tool()
def vardoger_personalize() -> str:
    """Personalize the AI assistant from conversation history.

    Call this tool when the user asks to personalize their assistant, analyze
    their conversation history, or mentions "vardoger". It returns step-by-step
    instructions for you to follow using the other vardoger tools.
    """
    from vardoger.checkpoint import CheckpointStore

    store = CheckpointStore()
    event = detect_edits("cursor", store)
    if event is not None:
        store.save()
    return _ORCHESTRATION_INSTRUCTIONS


@functools.lru_cache(maxsize=1)
def _get_batches() -> list:
    """Return the current Cursor history split into batches.

    Wrapped in ``lru_cache`` so the (relatively expensive) history read runs
    once per process; tests can clear the cache via
    ``_get_batches.cache_clear()``.
    """
    conversations = read_cursor_history()
    return batch_conversations(conversations)


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
    If the user has previously edited the generated rules, a feedback-context
    block is prepended so the synthesis respects those edits.

    Returns:
        The synthesis prompt text (optionally prefixed with feedback context).
    """
    from vardoger.checkpoint import CheckpointStore

    store = CheckpointStore()
    record = store.get_feedback("cursor")
    context = feedback_context_prompt(record.kept_rules, record.removed_rules, record.added_rules)
    prompt = synthesize_prompt()
    if context is None:
        return prompt
    return f"{context}\n\n---\n\n{prompt}"


@mcp.tool()
def vardoger_write(content: str, project_path: str = "") -> str:
    """Write the final personalization to the Cursor rules file.

    Call this after synthesizing all batch summaries into a personalization.
    Pass the personalization text as the content argument. If the content
    begins with a YAML frontmatter block (as produced by the synthesis
    prompt), low-confidence rules will be annotated with "(tentative)"
    before being written.

    Args:
        content: The personalization markdown to write (with optional YAML frontmatter).
        project_path: Optional project directory. If empty, uses current directory.

    Returns:
        Confirmation of what was written.
    """
    from pathlib import Path

    from vardoger.checkpoint import CheckpointStore, content_hash

    doc = parse_personalization(content)
    rendered = annotate_tentative(doc)

    target = Path(project_path) if project_path else None
    output = write_cursor_rules(rendered, project_path=target)

    store = CheckpointStore()
    store.record_generation(
        "cursor",
        conversations_analyzed=0,
        output_path=str(output),
        content=rendered,
        output_hash=content_hash(rendered),
        confidence=doc.confidence,
    )
    store.save()

    return f"vardoger: wrote personalization to {output}"


@mcp.tool()
def vardoger_preview(content: str, project_path: str = "") -> str:
    """Show a unified diff between proposed personalization and the current file.

    Applies the same frontmatter parsing + tentative annotation as
    ``vardoger_write`` so the preview matches what would be written. Does
    not modify any files.

    Args:
        content: The proposed personalization (with optional YAML frontmatter).
        project_path: Optional project directory. If empty, uses current directory.

    Returns:
        A unified diff, or a note if the file is identical / absent.
    """
    import difflib
    from pathlib import Path

    target = Path(project_path) if project_path else None
    doc = parse_personalization(content)
    rendered = annotate_tentative(doc)
    current = read_cursor_rules(project_path=target) or ""

    if current == rendered:
        return "vardoger: proposed content matches the current file — no changes."

    diff = "\n".join(
        difflib.unified_diff(
            current.splitlines(),
            rendered.splitlines(),
            fromfile="current",
            tofile="proposed",
            lineterm="",
        )
    )
    return diff or "vardoger: no textual diff produced."


@mcp.tool()
def vardoger_feedback(kind: str, reason: str = "", project_path: str = "") -> str:
    """Record accept/reject feedback for the latest Cursor personalization.

    - ``accept`` simply records that the user confirmed the generation.
    - ``reject`` also auto-reverts the rules file to the previous generation,
      or clears it entirely when no prior generation exists.

    Args:
        kind: "accept" or "reject".
        reason: Optional free-text reason recorded on the feedback event.
        project_path: Optional project directory. If empty, uses current directory.

    Returns:
        Human-readable confirmation.
    """
    from datetime import UTC, datetime
    from pathlib import Path

    from vardoger.checkpoint import CheckpointStore
    from vardoger.models import FeedbackEvent

    if kind not in {"accept", "reject"}:
        return f"vardoger: unknown feedback kind {kind!r} (expected 'accept' or 'reject')."

    target = Path(project_path) if project_path else None
    store = CheckpointStore()
    event = FeedbackEvent(
        recorded_at=datetime.now(UTC).isoformat(),
        kind=kind,  # type: ignore[arg-type]
        summary=reason,
    )
    store.record_feedback_event("cursor", event)

    if kind == "accept":
        store.save()
        return "vardoger: recorded accept for cursor."

    rejected = store.pop_generation("cursor")
    if rejected is None:
        store.save()
        return "vardoger: nothing to revert for cursor."

    previous = store.get_generation("cursor")
    if previous is not None and previous.content:
        output = write_cursor_rules(previous.content, project_path=target)
        store.save()
        return f"vardoger: reverted cursor to previous generation ({output})."

    cleared = clear_cursor_rules(project_path=target)
    store.save()
    if cleared:
        return "vardoger: cleared cursor personalization (no prior generation)."
    return "vardoger: no cursor personalization file to clear."


@mcp.tool()
def vardoger_compare(window_days: int = 0) -> str:
    """Compare conversation quality before vs. after the latest personalization.

    Returns a JSON ``QualityComparison`` for the Cursor platform. Metrics are
    heuristic signals (correction rate, pushback length, satisfaction tokens,
    restart rate, emoji rate) bucketed around the most recent generation's
    timestamp.

    Args:
        window_days: Optional symmetric window in days around the cutoff. Use
            0 (default) to include all history.

    Returns:
        ``QualityComparison.model_dump_json()`` — a JSON object with ``before``,
        ``after``, ``delta_notes``, and ``caveats``.
    """
    from vardoger.quality import compare as compare_quality

    window: int | None = window_days if window_days and window_days > 0 else None
    comp = compare_quality("cursor", window_days=window)
    return comp.model_dump_json(indent=2)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
