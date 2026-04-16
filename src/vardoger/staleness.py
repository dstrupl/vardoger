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
}

DEFAULT_NEW_CONVERSATION_THRESHOLD = 5
DEFAULT_DAYS_THRESHOLD = 7


def _discover_files(platform: str) -> list[tuple]:
    """Return (abs_path, rel_path) pairs for a platform's history files."""
    from vardoger.history.claude_code import discover_claude_code_files
    from vardoger.history.codex import discover_codex_files
    from vardoger.history.cursor import discover_cursor_files
    from vardoger.history.openclaw import discover_openclaw_files

    if platform == "cursor":
        return discover_cursor_files()
    elif platform == "claude-code":
        return discover_claude_code_files()
    elif platform == "codex":
        return discover_codex_files()
    elif platform == "openclaw":
        return discover_openclaw_files()
    return []


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

    files = _discover_files(platform)
    new_count = 0
    changed_count = 0
    for abs_path, rel_path in files:
        if store.is_changed(platform_key, rel_path, abs_path):
            existing_ckpt = store.get_checkpoint(platform_key, rel_path)
            if existing_ckpt is not None:
                changed_count += 1
            else:
                new_count += 1

    total_new = new_count + changed_count
    is_stale = total_new >= new_threshold or days_since >= days_threshold

    if not is_stale:
        parts = [f"last updated {days_since} day{'s' if days_since != 1 else ''} ago"]
        if total_new > 0:
            parts.append(f"{total_new} new conversation{'s' if total_new != 1 else ''}")
        reason = "fresh (" + ", ".join(parts) + ")"
    elif total_new >= new_threshold:
        reason = (
            f"stale ({total_new} new/changed conversation"
            f"{'s' if total_new != 1 else ''}"
            f", last updated {days_since} day{'s' if days_since != 1 else ''} ago)"
        )
    else:
        reason = f"stale (last updated {days_since} days ago)"

    return StalenessReport(
        platform=platform,
        is_stale=is_stale,
        days_since_generation=days_since,
        new_conversations=new_count,
        changed_conversations=changed_count,
        reason=reason,
    )
