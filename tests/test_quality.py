# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for A/B quality comparison (``vardoger.quality``)."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from vardoger.checkpoint import CheckpointStore
from vardoger.history.models import Conversation, Message
from vardoger.quality import (
    compare,
    correction_rate,
    emoji_rate,
    pushback_length,
    restart_rate,
    satisfaction_signal,
)


def _conv(messages: list[tuple[str, str, datetime | None]]) -> Conversation:
    return Conversation(messages=[Message(role=r, content=c, timestamp=t) for r, c, t in messages])


def test_correction_rate_counts_matching_user_messages():
    convs = [
        _conv(
            [
                ("user", "please implement foo", None),
                ("assistant", "sure", None),
                ("user", "no, that's wrong", None),
                ("assistant", "retrying", None),
                ("user", "thanks", None),
            ]
        )
    ]
    # Only 1 of 3 user messages contains any correction token ("no"/"wrong").
    assert correction_rate(convs) == 1 / 3


def test_satisfaction_signal_counts_thanks_tokens():
    convs = [
        _conv(
            [
                ("user", "thanks a lot!", None),
                ("user", "perfect", None),
                ("user", "keep going", None),
            ]
        )
    ]
    assert satisfaction_signal(convs) == 2 / 3


def test_pushback_length_only_after_assistant():
    convs = [
        _conv(
            [
                ("user", "hello", None),  # not counted (no prior assistant)
                ("assistant", "hi", None),
                ("user", "abcd", None),  # counted (len 4)
                ("assistant", "ok", None),
                ("user", "abcdefgh", None),  # counted (len 8)
            ]
        )
    ]
    assert pushback_length(convs) == (4 + 8) / 2


def test_restart_rate_looks_at_first_five_user_turns():
    hit = _conv(
        [
            ("user", "hi", None),
            ("user", "no stop", None),
            ("assistant", "ok", None),
        ]
    )
    miss = _conv(
        [
            ("user", "hi", None),
            ("user", "please continue", None),
            ("user", "looks great", None),
        ]
    )
    assert restart_rate([hit, miss]) == 0.5


def test_emoji_rate_only_assistant_messages():
    convs = [
        _conv(
            [
                ("user", "great job 🎉", None),
                ("assistant", "thanks!", None),
                ("assistant", "done 🚀", None),
            ]
        )
    ]
    assert emoji_rate(convs) == 0.5


def _mk_conv_at(ts: datetime, text: str = "hello world") -> Conversation:
    return _conv([("user", text, ts), ("assistant", "reply", ts)])


def test_compare_splits_around_cutoff():
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp) / "state"
        store = CheckpointStore(state_dir=state_dir)
        cutoff = datetime(2026, 1, 15, tzinfo=UTC)
        store.record_generation(
            "cursor",
            conversations_analyzed=0,
            output_path="/x",
            content="",
            output_hash="",
        )
        latest = store.get_generation("cursor")
        assert latest is not None
        latest.generated_at = cutoff.isoformat()
        store.save()

        before = [_mk_conv_at(cutoff - timedelta(days=i + 1)) for i in range(6)]
        after = [_mk_conv_at(cutoff + timedelta(days=i + 1)) for i in range(7)]

        comp = compare("cursor", conversations=before + after, store=store)

        assert comp.before is not None
        assert comp.after is not None
        assert comp.before.sample_conversations == 6
        assert comp.after.sample_conversations == 7
        assert "small sample" not in " ".join(comp.caveats)


def test_compare_small_sample_caveat():
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp) / "state"
        store = CheckpointStore(state_dir=state_dir)
        cutoff = datetime(2026, 1, 15, tzinfo=UTC)
        store.record_generation(
            "cursor",
            conversations_analyzed=0,
            output_path="/x",
            content="",
            output_hash="",
        )
        latest = store.get_generation("cursor")
        assert latest is not None
        latest.generated_at = cutoff.isoformat()
        store.save()

        convs = [
            _mk_conv_at(cutoff - timedelta(days=1)),
            _mk_conv_at(cutoff - timedelta(days=2)),
            _mk_conv_at(cutoff + timedelta(days=1)),
        ]
        comp = compare("cursor", conversations=convs, store=store)

        assert any("small sample" in c for c in comp.caveats)


def test_compare_window_restricts_both_buckets():
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp) / "state"
        store = CheckpointStore(state_dir=state_dir)
        cutoff = datetime(2026, 1, 15, tzinfo=UTC)
        store.record_generation(
            "cursor",
            conversations_analyzed=0,
            output_path="/x",
            content="",
            output_hash="",
        )
        latest = store.get_generation("cursor")
        assert latest is not None
        latest.generated_at = cutoff.isoformat()
        store.save()

        inside_before = [_mk_conv_at(cutoff - timedelta(days=2))]
        outside_before = [_mk_conv_at(cutoff - timedelta(days=30))]
        inside_after = [_mk_conv_at(cutoff + timedelta(days=2))]
        outside_after = [_mk_conv_at(cutoff + timedelta(days=30))]

        comp = compare(
            "cursor",
            conversations=inside_before + outside_before + inside_after + outside_after,
            window_days=5,
            store=store,
        )

        assert comp.before is not None
        assert comp.after is not None
        assert comp.before.sample_conversations == 1
        assert comp.after.sample_conversations == 1


def test_compare_returns_empty_when_never_personalized():
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp) / "state"
        store = CheckpointStore(state_dir=state_dir)

        comp = compare("cursor", conversations=[], store=store)

        assert comp.before is None
        assert comp.after is None
        assert comp.cutoff is None
        assert any("never personalized" in c for c in comp.caveats)
