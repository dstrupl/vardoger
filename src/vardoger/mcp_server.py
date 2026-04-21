# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""MCP server for vardoger — usable from any MCP-capable client.

Exposes vardoger's analysis pipeline as MCP tools that operate on any
supported platform (Cursor, Claude Code, Codex, OpenClaw, Copilot CLI,
Windsurf, or Cline). Each tool takes an optional ``platform`` argument; if
omitted, the server resolves the default platform in this order:

1. the ``VARDOGER_MCP_PLATFORM`` environment variable, or
2. ``"cursor"`` (preserved for backwards compatibility with clients
   installed before this became configurable).

Tools exposed:
  - vardoger_personalize() — entry point: returns orchestration instructions
  - vardoger_status()       — reports staleness of the target platform
  - vardoger_prepare()      — returns batch metadata or batch content
  - vardoger_synthesize_prompt() — returns the synthesis prompt
  - vardoger_write()        — writes the final personalization
  - vardoger_preview()      — shows a unified diff without touching files
  - vardoger_feedback()     — records accept/reject and can revert
  - vardoger_compare()      — A/B conversation quality around last generation

The host AI model performs the actual analysis between prepare and write;
the server only handles file I/O and state bookkeeping.

Usage (direct):
    python -m vardoger.mcp_server
"""

from __future__ import annotations

import functools
import importlib
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from vardoger.digest import batch_conversations, format_batch
from vardoger.feedback import detect_edits
from vardoger.history.cursor import read_cursor_history
from vardoger.history.models import Conversation
from vardoger.personalization import annotate_tentative, parse_personalization
from vardoger.prompts import feedback_context_prompt, summarize_prompt, synthesize_prompt
from vardoger.staleness import check_staleness

mcp = FastMCP("vardoger")

# ---------------------------------------------------------------------------
# Platform registry
# ---------------------------------------------------------------------------

PLATFORM_CHOICES: tuple[str, ...] = (
    "cursor",
    "claude-code",
    "codex",
    "openclaw",
    "copilot",
    "windsurf",
    "cline",
)

PLATFORM_LABELS: dict[str, str] = {
    "cursor": "Cursor",
    "claude-code": "Claude Code",
    "codex": "Codex",
    "openclaw": "OpenClaw",
    "copilot": "GitHub Copilot CLI",
    "windsurf": "Windsurf",
    "cline": "Cline",
}

# ``CheckpointStore`` keys its platform dicts on the underscore variant so
# that JSON state files stay valid Python attribute-shaped strings. The CLI
# name (``claude-code``) and state key (``claude_code``) only diverge for
# Claude Code today, but we keep a full mapping for symmetry.
_STATE_KEY: dict[str, str] = {
    "cursor": "cursor",
    "claude-code": "claude_code",
    "codex": "codex",
    "openclaw": "openclaw",
    "copilot": "copilot",
    "windsurf": "windsurf",
    "cline": "cline",
}

# Cline has no user-global rules location; default to project scope so that
# ``vardoger_write(platform="cline")`` writes somewhere sensible without
# forcing every caller to pass ``scope``.
_DEFAULT_SCOPE: dict[str, str] = {
    "cursor": "global",
    "claude-code": "global",
    "codex": "global",
    "openclaw": "global",
    "copilot": "global",
    "windsurf": "global",
    "cline": "project",
}

_DEFAULT_PLATFORM_ENV = "VARDOGER_MCP_PLATFORM"


def _env_default_platform() -> str:
    """Resolve the default platform from the environment (evaluated per call).

    We look this up per invocation rather than caching at import time so
    test suites that patch ``os.environ`` mid-session see their new value.
    """
    candidate = os.environ.get(_DEFAULT_PLATFORM_ENV, "").strip()
    if candidate in PLATFORM_CHOICES:
        return candidate
    return "cursor"


def _resolve_platform(platform: str) -> tuple[str | None, str | None]:
    """Return (platform, None) on success or (None, error_message) on failure.

    An empty string resolves to the configured default. Unknown names are
    reported back to the caller rather than raised so the MCP client can
    surface the message to the user.
    """
    if not platform:
        return _env_default_platform(), None
    if platform in PLATFORM_CHOICES:
        return platform, None
    choices = ", ".join(PLATFORM_CHOICES)
    return None, (f"vardoger: unknown platform {platform!r}; expected one of {choices}.")


def _resolve_scope(platform: str, scope: str) -> str:
    return scope if scope else _DEFAULT_SCOPE[platform]


def _label(platform: str) -> str:
    return PLATFORM_LABELS.get(platform, platform)


# ---------------------------------------------------------------------------
# Per-platform dispatch. A single registry maps each CLI-style platform name
# to the fully qualified names of its reader/writer helpers; ``_resolve`` does
# the lazy import so we never drag a non-target platform's history code into
# memory just because the MCP server starts up.
# ---------------------------------------------------------------------------


class _PlatformLookupError(KeyError):
    """Raised when internal dispatch can't find a known platform."""


_HISTORY_READER_QUALNAMES: dict[str, str] = {
    "cursor": "vardoger.history.cursor:read_cursor_history",
    "claude-code": "vardoger.history.claude_code:read_claude_code_history",
    "codex": "vardoger.history.codex:read_codex_history",
    "openclaw": "vardoger.history.openclaw:read_openclaw_history",
    "copilot": "vardoger.history.copilot:read_copilot_history",
    "windsurf": "vardoger.history.windsurf:read_windsurf_history",
    "cline": "vardoger.history.cline:read_cline_history",
}


def _qualnames(prefix: str, suffix: str) -> dict[str, str]:
    """Build a qualname map for writers/readers/clearers.

    Writer functions share a naming convention: ``<prefix>_<platform>_<suffix>``
    living in ``vardoger.writers.<platform>``. ``claude-code`` uses an
    underscore in Python identifiers, hence the small normalization.
    """
    out: dict[str, str] = {}
    for platform in PLATFORM_CHOICES:
        module_slug = platform.replace("-", "_")
        out[platform] = f"vardoger.writers.{module_slug}:{prefix}_{module_slug}_{suffix}"
    return out


_WRITER_QUALNAMES: dict[str, str] = _qualnames("write", "rules")
_READER_QUALNAMES: dict[str, str] = _qualnames("read", "rules")
_CLEARER_QUALNAMES: dict[str, str] = _qualnames("clear", "rules")

# Cursor's writer predates the shared ``scope`` argument and doesn't accept
# it; these platforms need the scope keyword forwarded.
_WRITERS_TAKING_SCOPE: frozenset[str] = frozenset(
    {"claude-code", "codex", "openclaw", "copilot", "windsurf", "cline"}
)


@functools.cache
def _resolve_qualname(qualname: str) -> Any:
    """Import ``module:attr`` lazily and return the attribute."""
    module_name, attr = qualname.split(":", 1)
    return getattr(importlib.import_module(module_name), attr)


def _history_reader(platform: str) -> Callable[..., list[Conversation]]:
    """Return the ``read_<platform>_history`` callable for ``platform``."""
    if platform == "cursor":
        return read_cursor_history
    qualname = _HISTORY_READER_QUALNAMES.get(platform)
    if qualname is None:
        raise _PlatformLookupError(platform)
    reader: Callable[..., list[Conversation]] = _resolve_qualname(qualname)
    return reader


def _writer_kwargs(platform: str, scope: str, project_path: Path | None) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"project_path": project_path}
    if platform in _WRITERS_TAKING_SCOPE:
        kwargs["scope"] = scope
    return kwargs


def _write_rules(
    platform: str,
    content: str,
    scope: str,
    project_path: Path | None,
) -> Path:
    qualname = _WRITER_QUALNAMES.get(platform)
    if qualname is None:
        raise _PlatformLookupError(platform)
    writer = _resolve_qualname(qualname)
    result: Path = writer(content, **_writer_kwargs(platform, scope, project_path))
    return result


def _read_rules(
    platform: str,
    scope: str,
    project_path: Path | None,
) -> str | None:
    qualname = _READER_QUALNAMES.get(platform)
    if qualname is None:
        raise _PlatformLookupError(platform)
    reader = _resolve_qualname(qualname)
    kwargs: dict[str, Any] = {"project_path": project_path}
    if platform in _WRITERS_TAKING_SCOPE:
        kwargs["scope"] = scope
    result: str | None = reader(**kwargs)
    return result


def _clear_rules(
    platform: str,
    scope: str,
    project_path: Path | None,
) -> bool:
    qualname = _CLEARER_QUALNAMES.get(platform)
    if qualname is None:
        raise _PlatformLookupError(platform)
    clearer = _resolve_qualname(qualname)
    kwargs: dict[str, Any] = {"project_path": project_path}
    if platform in _WRITERS_TAKING_SCOPE:
        kwargs["scope"] = scope
    result: bool = clearer(**kwargs)
    return result


# ---------------------------------------------------------------------------
# Orchestration instructions
# ---------------------------------------------------------------------------

_ORCHESTRATION_TEMPLATE = """\
# vardoger — Personalize Your Assistant ({label})

Follow these steps to analyze the user's {label} conversation history and \
generate a personalization. Report progress to the user after each step.

Every tool below accepts an optional `platform` argument. Pass \
`platform="{platform}"` on every call in this session so the server keeps \
reading and writing {label} state consistently, even if its default is \
something else.

## Step 1: Check status

Call `vardoger_status(platform="{platform}")`.

If the personalization is fresh (not stale), tell the user their \
personalization is up to date and ask if they want to re-run anyway. \
If stale or never generated, continue.

## Step 2: Get batch metadata

Call `vardoger_prepare(platform="{platform}", batch=0)`.

This returns JSON like `{{"batches": 3, "total_conversations": 29}}`. \
Note the number of batches. Tell the user: "Found N conversations in M \
batches. Analyzing..."

## Step 3: Summarize each batch

For each batch from 1 to M, call \
`vardoger_prepare(platform="{platform}", batch=N)`.

The output contains a summarization prompt and conversation data. Read it \
carefully and produce a concise bullet-point summary of the behavioral \
signals you observe. Keep each summary for later.

Tell the user: "Analyzing batch N of M..."

## Step 4: Get the synthesis prompt

Call `vardoger_synthesize_prompt(platform="{platform}")`.

## Step 5: Synthesize

Following the synthesis prompt, combine all your batch summaries into a \
single personalization. The output should be clean markdown with actionable \
instructions.

## Step 6: Write the result

Call `vardoger_write(platform="{platform}", content="YOUR_PERSONALIZATION_HERE")`.

## Step 7: Report to the user

Tell the user what was written and where. Mention they can ask you to \
re-run vardoger any time to update the personalization.
"""


def _orchestration_instructions(platform: str) -> str:
    return _ORCHESTRATION_TEMPLATE.format(platform=platform, label=_label(platform))


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def vardoger_status(platform: str = "") -> str:
    """Check whether the personalization for a platform is up to date.

    Args:
        platform: One of cursor, claude-code, codex, openclaw, copilot,
            windsurf, cline. Empty uses the server default (env var
            ``VARDOGER_MCP_PLATFORM`` or ``cursor``).

    Returns:
        JSON ``StalenessReport`` indicating whether the personalization
        needs refreshing, how many days since the last update, and how
        many new or changed conversations exist.
    """
    resolved, err = _resolve_platform(platform)
    if resolved is None or err is not None:
        return err or "vardoger: unknown platform."
    report = check_staleness(resolved)
    return report.model_dump_json(indent=2)


@mcp.tool()
def vardoger_personalize(platform: str = "") -> str:
    """Personalize the AI assistant from its conversation history.

    Call this tool when the user asks to personalize their assistant, to
    analyze their conversation history, or mentions "vardoger". Returns
    step-by-step instructions for the calling model to follow using the
    other vardoger tools.

    Args:
        platform: One of cursor, claude-code, codex, openclaw, copilot,
            windsurf, cline. Empty uses the server default (env var
            ``VARDOGER_MCP_PLATFORM`` or ``cursor``).

    Returns:
        A markdown walkthrough of the remaining vardoger calls.
    """
    from vardoger.checkpoint import CheckpointStore

    resolved, err = _resolve_platform(platform)
    if resolved is None or err is not None:
        return err or "vardoger: unknown platform."

    store = CheckpointStore()
    event = detect_edits(resolved, store)
    if event is not None:
        store.save()
    return _orchestration_instructions(resolved)


@functools.lru_cache(maxsize=len(PLATFORM_CHOICES))
def _get_batches(platform: str = "cursor") -> list:
    """Return the current history for ``platform`` split into batches.

    Wrapped in ``lru_cache`` so the (relatively expensive) history read runs
    once per platform per process; tests can clear the cache via
    ``_get_batches.cache_clear()``.
    """
    reader = _history_reader(platform)
    conversations = reader()
    return batch_conversations(conversations)


@mcp.tool()
def vardoger_prepare(batch: int = 0, platform: str = "") -> str:
    """Prepare conversation history for analysis.

    Call without ``batch`` (or with ``batch=0``) to get metadata about how
    many batches are available. Then call with ``batch=1``, ``batch=2``,
    etc. to get each batch of conversations along with the summarization
    prompt.

    Args:
        batch: Batch number (1-based). 0 or omitted returns metadata only.
        platform: One of cursor, claude-code, codex, openclaw, copilot,
            windsurf, cline. Empty uses the server default.

    Returns:
        JSON metadata for ``batch=0``, otherwise the summarize prompt
        concatenated with the batch's conversation content.
    """
    import json

    resolved, err = _resolve_platform(platform)
    if resolved is None or err is not None:
        return err or "vardoger: unknown platform."

    batches = _get_batches(resolved)
    total_convos = sum(len(b) for b in batches)

    if batch == 0:
        return json.dumps(
            {
                "platform": resolved,
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
def vardoger_synthesize_prompt(platform: str = "") -> str:
    """Get the synthesis prompt for combining batch summaries.

    Call this after you have summarized all batches. Use the returned
    prompt to guide the synthesis of those batch summaries into a final
    personalization. If the user has previously edited the generated
    rules, a feedback-context block is prepended so the synthesis respects
    those edits.

    Args:
        platform: One of cursor, claude-code, codex, openclaw, copilot,
            windsurf, cline. Empty uses the server default.

    Returns:
        The synthesis prompt text (optionally prefixed with feedback
        context).
    """
    from vardoger.checkpoint import CheckpointStore

    resolved, err = _resolve_platform(platform)
    if resolved is None or err is not None:
        return err or "vardoger: unknown platform."

    store = CheckpointStore()
    record = store.get_feedback(_STATE_KEY[resolved])
    context = feedback_context_prompt(record.kept_rules, record.removed_rules, record.added_rules)
    prompt = synthesize_prompt()
    if context is None:
        return prompt
    return f"{context}\n\n---\n\n{prompt}"


@mcp.tool()
def vardoger_write(
    content: str,
    platform: str = "",
    scope: str = "",
    project_path: str = "",
) -> str:
    """Write the final personalization to the target platform's rules file.

    Call this after synthesizing all batch summaries. If ``content`` begins
    with a YAML frontmatter block (as produced by the synthesis prompt),
    low-confidence rules are annotated with "(tentative)" before being
    written.

    Args:
        content: The personalization markdown to write (with optional YAML
            frontmatter).
        platform: One of cursor, claude-code, codex, openclaw, copilot,
            windsurf, cline. Empty uses the server default.
        scope: "global" or "project". Empty selects the platform's default
            (project for cline, global otherwise). Ignored for Cursor
            (Cursor's writer always targets ``<project>/.cursor/rules/``).
        project_path: Optional project directory. Empty uses the current
            working directory.

    Returns:
        Human-readable confirmation of what was written.
    """
    from vardoger.checkpoint import CheckpointStore, content_hash

    resolved, err = _resolve_platform(platform)
    if resolved is None or err is not None:
        return err or "vardoger: unknown platform."
    resolved_scope = _resolve_scope(resolved, scope)

    doc = parse_personalization(content)
    rendered = annotate_tentative(doc)

    target = Path(project_path) if project_path else None
    output = _write_rules(resolved, rendered, resolved_scope, target)

    store = CheckpointStore()
    store.record_generation(
        _STATE_KEY[resolved],
        conversations_analyzed=0,
        output_path=str(output),
        content=rendered,
        output_hash=content_hash(rendered),
        confidence=doc.confidence,
    )
    store.save()

    return f"vardoger: wrote personalization to {output}"


@mcp.tool()
def vardoger_preview(
    content: str,
    platform: str = "",
    scope: str = "",
    project_path: str = "",
) -> str:
    """Show a unified diff between a proposed personalization and the current file.

    Applies the same frontmatter parsing + tentative annotation as
    ``vardoger_write`` so the preview matches what would be written. Does
    not modify any files.

    Args:
        content: The proposed personalization (with optional YAML frontmatter).
        platform: One of cursor, claude-code, codex, openclaw, copilot,
            windsurf, cline. Empty uses the server default.
        scope: "global" or "project". Empty selects the platform's default.
        project_path: Optional project directory. Empty uses the current
            working directory.

    Returns:
        A unified diff, or a note if the file is identical / absent.
    """
    import difflib

    resolved, err = _resolve_platform(platform)
    if resolved is None or err is not None:
        return err or "vardoger: unknown platform."
    resolved_scope = _resolve_scope(resolved, scope)

    target = Path(project_path) if project_path else None
    doc = parse_personalization(content)
    rendered = annotate_tentative(doc)
    current = _read_rules(resolved, resolved_scope, target) or ""

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
def vardoger_feedback(
    kind: str,
    platform: str = "",
    reason: str = "",
    scope: str = "",
    project_path: str = "",
) -> str:
    """Record accept/reject feedback for the latest personalization.

    - ``accept`` simply records that the user confirmed the generation.
    - ``reject`` also auto-reverts the rules file to the previous generation,
      or clears it entirely when no prior generation exists.

    Args:
        kind: "accept" or "reject".
        platform: One of cursor, claude-code, codex, openclaw, copilot,
            windsurf, cline. Empty uses the server default.
        reason: Optional free-text reason recorded on the feedback event.
        scope: "global" or "project". Empty selects the platform's default.
        project_path: Optional project directory. Empty uses the current
            working directory.

    Returns:
        Human-readable confirmation.
    """
    from datetime import UTC, datetime

    from vardoger.checkpoint import CheckpointStore
    from vardoger.models import FeedbackEvent

    if kind not in {"accept", "reject"}:
        return f"vardoger: unknown feedback kind {kind!r} (expected 'accept' or 'reject')."

    resolved, err = _resolve_platform(platform)
    if resolved is None or err is not None:
        return err or "vardoger: unknown platform."
    resolved_scope = _resolve_scope(resolved, scope)
    state_key = _STATE_KEY[resolved]

    target = Path(project_path) if project_path else None
    store = CheckpointStore()
    event = FeedbackEvent(
        recorded_at=datetime.now(UTC).isoformat(),
        kind=kind,  # type: ignore[arg-type]
        summary=reason,
    )
    store.record_feedback_event(state_key, event)

    if kind == "accept":
        store.save()
        return f"vardoger: recorded accept for {resolved}."

    message = _apply_reject(store, resolved, resolved_scope, target, state_key)
    store.save()
    return message


def _apply_reject(
    store: Any,
    platform: str,
    scope: str,
    project_path: Path | None,
    state_key: str,
) -> str:
    """Pop the latest generation and either revert to the prior one or clear the file."""
    rejected = store.pop_generation(state_key)
    if rejected is None:
        return f"vardoger: nothing to revert for {platform}."

    previous = store.get_generation(state_key)
    if previous is not None and previous.content:
        output = _write_rules(platform, previous.content, scope, project_path)
        return f"vardoger: reverted {platform} to previous generation ({output})."

    cleared = _clear_rules(platform, scope, project_path)
    if cleared:
        return f"vardoger: cleared {platform} personalization (no prior generation)."
    return f"vardoger: no {platform} personalization file to clear."


@mcp.tool()
def vardoger_compare(window_days: int = 0, platform: str = "") -> str:
    """Compare conversation quality before vs. after the latest personalization.

    Metrics are heuristic signals (correction rate, pushback length,
    satisfaction tokens, restart rate, emoji rate) bucketed around the
    most recent generation's timestamp.

    Args:
        window_days: Optional symmetric window in days around the cutoff.
            Use 0 (default) to include all history.
        platform: One of cursor, claude-code, codex, openclaw, copilot,
            windsurf, cline. Empty uses the server default.

    Returns:
        ``QualityComparison.model_dump_json()`` — a JSON object with
        ``before``, ``after``, ``delta_notes``, and ``caveats``.
    """
    from vardoger.quality import compare as compare_quality

    resolved, err = _resolve_platform(platform)
    if resolved is None or err is not None:
        return err or "vardoger: unknown platform."

    window: int | None = window_days if window_days and window_days > 0 else None
    comp = compare_quality(resolved, window_days=window)
    return comp.model_dump_json(indent=2)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
