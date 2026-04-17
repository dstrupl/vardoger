# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""User-feedback capture for generated personalizations.

Detects whether the user has edited the vardoger-managed rules file since
the last run and classifies each bullet line as kept / removed / added
relative to the content we wrote.

The result is recorded as a ``FeedbackEvent(kind="edit", ...)`` and the
rolled-up kept/removed/added lists are stored in the platform's
``FeedbackRecord`` so the next synthesis can steer away from rejected
patterns and preserve user-added ones.

This module is pure (no network, no AI calls) and safe to call at the top
of every CLI/MCP entry point.
"""

from __future__ import annotations

import difflib
import logging
import re
from datetime import UTC, datetime
from pathlib import Path

from vardoger.checkpoint import CheckpointStore, content_hash
from vardoger.models import FeedbackEvent

logger = logging.getLogger(__name__)

# CLI platform labels map to the keys we use inside state.json (the
# ``PLATFORM_KEY`` mapping in vardoger.cli). Kept local to avoid import cycles.
_PLATFORM_STATE_KEY = {
    "cursor": "cursor",
    "claude-code": "claude_code",
    "codex": "codex",
    "openclaw": "openclaw",
}

_BULLET_RE = re.compile(r"^\s*[-*]\s+(?P<text>.+?)\s*$")
_HEADING_RE = re.compile(r"^\s*#{1,6}\s+(?P<text>.+?)\s*$")


def _read_current_rules(platform: str, scope: str, project_path: Path | None) -> str | None:
    """Dispatch to the platform's read_<platform>_rules helper."""
    if platform == "cursor":
        from vardoger.writers.cursor import read_cursor_rules

        return read_cursor_rules(project_path=project_path)
    if platform == "claude-code":
        from vardoger.writers.claude_code import read_claude_code_rules

        return read_claude_code_rules(scope=scope, project_path=project_path)
    if platform == "codex":
        from vardoger.writers.codex import read_codex_rules

        return read_codex_rules(scope=scope, project_path=project_path)
    if platform == "openclaw":
        from vardoger.writers.openclaw import read_openclaw_rules

        return read_openclaw_rules(scope=scope, project_path=project_path)
    return None


def extract_bullets(markdown: str) -> list[str]:
    """Return every bullet line's text, in document order, deduplicated."""
    bullets: list[str] = []
    seen: set[str] = set()
    for line in markdown.splitlines():
        match = _BULLET_RE.match(line)
        if match is None:
            continue
        text = match.group("text").strip()
        if text and text not in seen:
            bullets.append(text)
            seen.add(text)
    return bullets


def diff_bullets(before: str, after: str) -> tuple[list[str], list[str], list[str]]:
    """Split bullets from ``before`` and ``after`` into (kept, removed, added).

    Matching is by exact text equality (case-sensitive, whitespace-trimmed),
    which intentionally treats small wording edits as a removal + addition.
    """
    before_bullets = extract_bullets(before)
    after_bullets = extract_bullets(after)

    before_set = set(before_bullets)
    after_set = set(after_bullets)

    kept = [b for b in before_bullets if b in after_set]
    removed = [b for b in before_bullets if b not in after_set]
    added = [b for b in after_bullets if b not in before_set]
    return kept, removed, added


def _merge_unique(existing: list[str], additions: list[str]) -> list[str]:
    """Append ``additions`` to ``existing`` preserving order, no duplicates."""
    seen = set(existing)
    result = list(existing)
    for item in additions:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def detect_edits(
    platform: str,
    store: CheckpointStore,
    scope: str = "global",
    project_path: Path | None = None,
) -> FeedbackEvent | None:
    """Detect user edits to the current rules file vs. the latest generation.

    Returns the appended ``FeedbackEvent`` (with a unified diff in
    ``summary``) if an edit was detected, otherwise ``None``. Caller is
    responsible for persisting the checkpoint store afterwards.
    """
    state_key = _PLATFORM_STATE_KEY.get(platform, platform)
    latest = store.get_generation(state_key)
    if latest is None or not latest.content:
        return None

    current = _read_current_rules(platform, scope, project_path)
    if current is None:
        return None

    current_hash = content_hash(current)
    if current_hash == latest.output_hash:
        return None

    kept, removed, added = diff_bullets(latest.content, current)

    record = store.get_feedback(state_key)
    record.kept_rules = _merge_unique(record.kept_rules, kept)
    record.removed_rules = _merge_unique(record.removed_rules, removed)
    record.added_rules = _merge_unique(record.added_rules, added)

    diff_text = "\n".join(
        difflib.unified_diff(
            latest.content.splitlines(),
            current.splitlines(),
            fromfile="vardoger-generated",
            tofile="user-edited",
            lineterm="",
        )
    )
    event = FeedbackEvent(
        recorded_at=datetime.now(UTC).isoformat(),
        kind="edit",
        summary=diff_text,
    )
    record.events.append(event)
    logger.info(
        "Detected user edits to %s rules: +%d/-%d bullets",
        platform,
        len(added),
        len(removed),
    )
    return event
