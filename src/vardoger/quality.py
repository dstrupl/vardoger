# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""A/B style quality comparison over conversation history.

Compute a small set of heuristic metrics over user/assistant messages and split
conversations into a ``before`` and ``after`` bucket based on the timestamp of
the most recent vardoger personalization (``GenerationRecord.generated_at``).

The metrics are intentionally lightweight and run locally. They are meant to
give a directional signal about how personalization is affecting the user's
interaction patterns, not to be a statistical proof.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta

from vardoger.checkpoint import CheckpointStore
from vardoger.history.models import Conversation, Message
from vardoger.models import QualityComparison, QualityMetrics

logger = logging.getLogger(__name__)

# Compiled regexes — per AGENTS.md performance guidance, module-level constants.
_CORRECTION_RE = re.compile(r"(?i)\b(no|wrong|don't|stop|actually|not what)\b")
_SATISFACTION_RE = re.compile(r"(?i)\b(thanks|thx|lgtm|perfect|great|nice)\b")
# Match any emoji-range code points. Covers most user-visible emoji.
_EMOJI_RE = re.compile("[\U0001f300-\U0001faff\U00002600-\U000027bf\U0001f600-\U0001f64f]")

_SMALL_SAMPLE_THRESHOLD = 5


class UnknownPlatformError(ValueError):
    """Raised when a platform identifier is not recognized."""

    def __init__(self, platform: str) -> None:
        super().__init__(f"Unknown platform: {platform}")
        self.platform = platform


# ---------------------------------------------------------------------------
# Metric helpers (public for tests)
# ---------------------------------------------------------------------------


def correction_rate(conversations: list[Conversation]) -> float:
    """Fraction of user messages containing a correction/pushback token."""
    total = 0
    hits = 0
    for conv in conversations:
        for m in conv.messages:
            if m.role != "user":
                continue
            total += 1
            if _CORRECTION_RE.search(m.content or ""):
                hits += 1
    return hits / total if total else 0.0


def pushback_length(conversations: list[Conversation]) -> float:
    """Mean character length of user messages that immediately follow an assistant turn."""
    lengths: list[int] = []
    for conv in conversations:
        prev_role: str | None = None
        for m in conv.messages:
            if m.role == "user" and prev_role == "assistant":
                lengths.append(len(m.content or ""))
            prev_role = m.role
    if not lengths:
        return 0.0
    return sum(lengths) / len(lengths)


def satisfaction_signal(conversations: list[Conversation]) -> float:
    """Fraction of user messages with a positive/thanks token."""
    total = 0
    hits = 0
    for conv in conversations:
        for m in conv.messages:
            if m.role != "user":
                continue
            total += 1
            if _SATISFACTION_RE.search(m.content or ""):
                hits += 1
    return hits / total if total else 0.0


def restart_rate(conversations: list[Conversation]) -> float:
    """Fraction of conversations whose first 5 user turns include a correction token."""
    total = 0
    hits = 0
    for conv in conversations:
        user_msgs: list[Message] = [m for m in conv.messages if m.role == "user"]
        if not user_msgs:
            continue
        total += 1
        window = user_msgs[:5]
        if any(_CORRECTION_RE.search(m.content or "") for m in window):
            hits += 1
    return hits / total if total else 0.0


def emoji_rate(conversations: list[Conversation]) -> float:
    """Fraction of assistant messages containing at least one emoji code point."""
    total = 0
    hits = 0
    for conv in conversations:
        for m in conv.messages:
            if m.role != "assistant":
                continue
            total += 1
            if _EMOJI_RE.search(m.content or ""):
                hits += 1
    return hits / total if total else 0.0


def _metrics(conversations: list[Conversation]) -> QualityMetrics:
    sample_messages = sum(c.message_count for c in conversations)
    return QualityMetrics(
        correction_rate=correction_rate(conversations),
        pushback_length=pushback_length(conversations),
        satisfaction_signal=satisfaction_signal(conversations),
        restart_rate=restart_rate(conversations),
        emoji_rate=emoji_rate(conversations),
        sample_conversations=len(conversations),
        sample_messages=sample_messages,
    )


# ---------------------------------------------------------------------------
# Bucketing
# ---------------------------------------------------------------------------


def _conversation_timestamp(conv: Conversation) -> datetime | None:
    """Return the conversation's latest message timestamp, or None."""
    latest: datetime | None = None
    for m in conv.messages:
        if m.timestamp is None:
            continue
        if latest is None or m.timestamp > latest:
            latest = m.timestamp
    return latest


def _parse_cutoff(value: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        logger.warning("Invalid cutoff timestamp %r — treating as missing", value)
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _partition(
    conversations: list[Conversation],
    cutoff: datetime,
    window_days: int | None,
) -> tuple[list[Conversation], list[Conversation]]:
    """Split conversations into (before, after) buckets around the cutoff.

    If ``window_days`` is provided, both buckets are restricted symmetrically to
    ``[cutoff - window, cutoff)`` and ``[cutoff, cutoff + window)`` respectively.
    Conversations with no timestamped messages are dropped from both buckets.
    """
    window = timedelta(days=window_days) if window_days else None
    before: list[Conversation] = []
    after: list[Conversation] = []
    for conv in conversations:
        ts = _conversation_timestamp(conv)
        if ts is None:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        if ts < cutoff:
            if window is None or ts >= cutoff - window:
                before.append(conv)
        elif window is None or ts < cutoff + window:
            after.append(conv)
    return before, after


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _read_conversations_for(platform: str) -> list[Conversation]:
    """Load every available conversation for a platform (no checkpoint filter)."""
    if platform == "cursor":
        from vardoger.history.cursor import read_cursor_history

        return read_cursor_history()
    if platform == "claude-code":
        from vardoger.history.claude_code import read_claude_code_history

        return read_claude_code_history()
    if platform == "codex":
        from vardoger.history.codex import read_codex_history

        return read_codex_history()
    if platform == "openclaw":
        from vardoger.history.openclaw import read_openclaw_history

        return read_openclaw_history()
    raise UnknownPlatformError(platform)


_PLATFORM_STATE_KEY = {
    "cursor": "cursor",
    "claude-code": "claude_code",
    "codex": "codex",
    "openclaw": "openclaw",
}


def compare(
    platform: str,
    *,
    window_days: int | None = None,
    conversations: list[Conversation] | None = None,
    store: CheckpointStore | None = None,
) -> QualityComparison:
    """Compare quality metrics before and after the most recent generation.

    Parameters
    ----------
    platform:
        Public platform name (``cursor``, ``claude-code``, ``codex``, ``openclaw``).
    window_days:
        Optional symmetric window around the cutoff. ``None`` keeps all history.
    conversations:
        Optional pre-loaded conversations (used by tests). When omitted, reads
        from the platform's default location.
    store:
        Optional checkpoint store (used by tests). When omitted, a fresh one is
        opened.
    """
    store = store or CheckpointStore()
    state_key = _PLATFORM_STATE_KEY[platform]
    record = store.get_generation(state_key)

    if conversations is None:
        conversations = _read_conversations_for(platform)

    if record is None:
        return QualityComparison(
            platform=platform,
            cutoff=None,
            before=None,
            after=None,
            delta_notes=[],
            caveats=["never personalized — no cutoff to compare against"],
        )

    cutoff = _parse_cutoff(record.generated_at)
    if cutoff is None:
        return QualityComparison(
            platform=platform,
            cutoff=record.generated_at,
            before=None,
            after=None,
            delta_notes=[],
            caveats=["invalid cutoff timestamp on latest generation"],
        )

    before_convs, after_convs = _partition(conversations, cutoff, window_days)
    before = _metrics(before_convs)
    after = _metrics(after_convs)

    caveats: list[str] = []
    if (
        before.sample_conversations < _SMALL_SAMPLE_THRESHOLD
        or after.sample_conversations < _SMALL_SAMPLE_THRESHOLD
    ):
        caveats.append("small sample: treat deltas as directional")

    delta_notes = _format_delta_notes(before, after)

    return QualityComparison(
        platform=platform,
        cutoff=record.generated_at,
        before=before,
        after=after,
        delta_notes=delta_notes,
        caveats=caveats,
    )


def _format_delta_notes(before: QualityMetrics, after: QualityMetrics) -> list[str]:
    notes: list[str] = []
    pairs: list[tuple[str, float, float, bool]] = [
        ("correction_rate", before.correction_rate, after.correction_rate, False),
        ("pushback_length", before.pushback_length, after.pushback_length, False),
        (
            "satisfaction_signal",
            before.satisfaction_signal,
            after.satisfaction_signal,
            True,
        ),
        ("restart_rate", before.restart_rate, after.restart_rate, False),
        ("emoji_rate", before.emoji_rate, after.emoji_rate, False),
    ]
    for name, b, a, higher_is_better in pairs:
        if b == 0 and a == 0:
            continue
        delta = a - b
        arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
        direction = "better" if (delta > 0) == higher_is_better else "worse"
        if delta == 0:
            direction = "unchanged"
        notes.append(f"{name}: {b:.3f} {arrow} {a:.3f} ({direction})")
    return notes
