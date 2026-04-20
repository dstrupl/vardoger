# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Staleness detection for vardoger personalizations.

Determines whether a platform's generated personalization is out of date
by comparing the current conversation history against the checkpoint and
generation metadata stored in state.json.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from vardoger.checkpoint import CheckpointStore
from vardoger.models import StalenessReport

logger = logging.getLogger(__name__)

PLATFORM_KEY = {
    "cursor": "cursor",
    "claude-code": "claude_code",
    "codex": "codex",
    "openclaw": "openclaw",
    "copilot": "copilot",
    "windsurf": "windsurf",
    "cline": "cline",
}

DEFAULT_NEW_CONVERSATION_THRESHOLD = 5
DEFAULT_DAYS_THRESHOLD = 7


def _discover_files(platform: str) -> list[tuple]:
    """Return (abs_path, rel_path) pairs for a platform's history files."""
    from vardoger.history.claude_code import discover_claude_code_files
    from vardoger.history.cline import discover_cline_files
    from vardoger.history.codex import discover_codex_files
    from vardoger.history.copilot import discover_copilot_files
    from vardoger.history.cursor import discover_cursor_files
    from vardoger.history.openclaw import discover_openclaw_files
    from vardoger.history.windsurf import discover_windsurf_files

    dispatch = {
        "cursor": discover_cursor_files,
        "claude-code": discover_claude_code_files,
        "codex": discover_codex_files,
        "openclaw": discover_openclaw_files,
        "copilot": discover_copilot_files,
        "windsurf": discover_windsurf_files,
        "cline": discover_cline_files,
    }
    discover = dispatch.get(platform)
    return discover() if discover is not None else []


def _count_new_and_changed(
    store: CheckpointStore,
    platform_key: str,
    files: list[tuple],
) -> tuple[int, int]:
    """Return (new_count, changed_count) across the discovered files."""
    new_count = 0
    changed_count = 0
    for abs_path, rel_path in files:
        if not store.is_changed(platform_key, rel_path, abs_path):
            continue
        if store.get_checkpoint(platform_key, rel_path) is not None:
            changed_count += 1
        else:
            new_count += 1
    return new_count, changed_count


def _describe(is_stale: bool, total_new: int, days_since: int, new_threshold: int) -> str:
    """Format the human-readable ``reason`` field for a staleness report."""
    if not is_stale:
        parts = [f"last updated {days_since} day{'s' if days_since != 1 else ''} ago"]
        if total_new > 0:
            parts.append(f"{total_new} new conversation{'s' if total_new != 1 else ''}")
        return "fresh (" + ", ".join(parts) + ")"
    if total_new >= new_threshold:
        return (
            f"stale ({total_new} new/changed conversation"
            f"{'s' if total_new != 1 else ''}"
            f", last updated {days_since} day{'s' if days_since != 1 else ''} ago)"
        )
    return f"stale (last updated {days_since} days ago)"


def check_staleness(
    platform: str,
    checkpoint: CheckpointStore | None = None,
    new_threshold: int = DEFAULT_NEW_CONVERSATION_THRESHOLD,
    days_threshold: int = DEFAULT_DAYS_THRESHOLD,
) -> StalenessReport:
    """Check whether a platform's personalization needs refreshing.

    A personalization is stale when:
    - It was never generated, OR
    - At least ``new_threshold`` conversation files are new/changed, OR
    - At least ``days_threshold`` days have passed since the last generation.
    """
    store = checkpoint or CheckpointStore()
    platform_key = PLATFORM_KEY.get(platform, platform)
    generation = store.get_generation(platform_key)

    if generation is None:
        return StalenessReport(
            platform=platform,
            is_stale=True,
            days_since_generation=None,
            new_conversations=0,
            changed_conversations=0,
            reason="never generated — run vardoger to personalize",
        )

    generated_at = datetime.fromisoformat(generation.generated_at)
    days_since = (datetime.now(UTC) - generated_at).days

    new_count, changed_count = _count_new_and_changed(
        store, platform_key, _discover_files(platform)
    )
    total_new = new_count + changed_count
    is_stale = total_new >= new_threshold or days_since >= days_threshold

    return StalenessReport(
        platform=platform,
        is_stale=is_stale,
        days_since_generation=days_since,
        new_conversations=new_count,
        changed_conversations=changed_count,
        reason=_describe(is_stale, total_new, days_since, new_threshold),
    )
