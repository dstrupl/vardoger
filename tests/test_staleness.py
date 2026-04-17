# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for staleness detection."""

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from vardoger.checkpoint import CheckpointStore
from vardoger.models import GenerationRecord, StalenessReport
from vardoger.staleness import _describe, check_staleness


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_never_generated_is_stale():
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp) / "state"
        store = CheckpointStore(state_dir=state_dir)

        with patch("vardoger.staleness._discover_files", return_value=[]):
            report = check_staleness("cursor", checkpoint=store)

        assert report.is_stale
        assert report.days_since_generation is None
        assert "never generated" in report.reason


def test_fresh_when_recently_generated_no_new_files():
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp) / "state"
        store = CheckpointStore(state_dir=state_dir)
        store.record_generation("cursor", conversations_analyzed=5, output_path="/out")
        store.save()

        store2 = CheckpointStore(state_dir=state_dir)
        with patch("vardoger.staleness._discover_files", return_value=[]):
            report = check_staleness("cursor", checkpoint=store2)

        assert not report.is_stale
        assert report.days_since_generation == 0
        assert "fresh" in report.reason


def test_stale_when_many_new_conversations():
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp) / "state"
        data_dir = Path(tmp) / "data"

        store = CheckpointStore(state_dir=state_dir)
        store.record_generation("cursor", conversations_analyzed=5, output_path="/out")
        store.save()

        files = []
        for i in range(6):
            f = data_dir / f"conv{i}.jsonl"
            _write_file(f, f"content {i}")
            files.append((f, f"conv{i}.jsonl"))

        store2 = CheckpointStore(state_dir=state_dir)
        with patch("vardoger.staleness._discover_files", return_value=files):
            report = check_staleness("cursor", checkpoint=store2, new_threshold=5)

        assert report.is_stale
        assert report.new_conversations == 6
        assert "stale" in report.reason


def test_stale_when_old_generation():
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp) / "state"
        store = CheckpointStore(state_dir=state_dir)

        old_time = (datetime.now(UTC) - timedelta(days=10)).isoformat()
        store._state.generations["cursor"] = [
            GenerationRecord(
                generated_at=old_time,
                conversations_analyzed=5,
                output_path="/out",
            )
        ]
        store.save()

        store2 = CheckpointStore(state_dir=state_dir)
        with patch("vardoger.staleness._discover_files", return_value=[]):
            report = check_staleness("cursor", checkpoint=store2, days_threshold=7)

        assert report.is_stale
        assert report.days_since_generation == 10
        assert "stale" in report.reason


def test_fresh_below_threshold():
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp) / "state"
        data_dir = Path(tmp) / "data"

        store = CheckpointStore(state_dir=state_dir)
        store.record_generation("cursor", conversations_analyzed=5, output_path="/out")
        store.save()

        files = []
        for i in range(3):
            f = data_dir / f"conv{i}.jsonl"
            _write_file(f, f"content {i}")
            files.append((f, f"conv{i}.jsonl"))

        store2 = CheckpointStore(state_dir=state_dir)
        with patch("vardoger.staleness._discover_files", return_value=files):
            report = check_staleness("cursor", checkpoint=store2, new_threshold=5)

        assert not report.is_stale
        assert report.new_conversations == 3
        assert "fresh" in report.reason


def test_changed_vs_new_conversations():
    """Changed files (already checkpointed) are counted separately from new files."""
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp) / "state"
        data_dir = Path(tmp) / "data"

        store = CheckpointStore(state_dir=state_dir)

        existing = data_dir / "old.jsonl"
        _write_file(existing, "original content")
        store.record("cursor", "old.jsonl", existing)
        store.record_generation("cursor", conversations_analyzed=1, output_path="/out")
        store.save()

        existing.write_text("modified content")
        new_file = data_dir / "new.jsonl"
        _write_file(new_file, "brand new")

        files = [(existing, "old.jsonl"), (new_file, "new.jsonl")]

        store2 = CheckpointStore(state_dir=state_dir)
        with patch("vardoger.staleness._discover_files", return_value=files):
            report = check_staleness("cursor", checkpoint=store2, new_threshold=5)

        assert report.changed_conversations == 1
        assert report.new_conversations == 1


def test_describe_fresh_mentions_days_and_new_count():
    reason = _describe(is_stale=False, total_new=3, days_since=2, new_threshold=5)
    assert "fresh" in reason
    assert "2 days ago" in reason
    assert "3 new conversations" in reason


def test_describe_fresh_without_new_conversations_omits_count():
    reason = _describe(is_stale=False, total_new=0, days_since=1, new_threshold=5)
    assert reason == "fresh (last updated 1 day ago)"


def test_describe_stale_new_threshold_branch():
    reason = _describe(is_stale=True, total_new=6, days_since=3, new_threshold=5)
    assert reason.startswith("stale (6 new/changed conversations")
    assert "3 days ago" in reason


def test_describe_stale_days_threshold_branch():
    reason = _describe(is_stale=True, total_new=0, days_since=10, new_threshold=5)
    assert reason == "stale (last updated 10 days ago)"


def test_report_dataclass_fields():
    report = StalenessReport(
        platform="cursor",
        is_stale=True,
        days_since_generation=None,
        new_conversations=0,
        changed_conversations=0,
        reason="never generated",
    )
    assert report.platform == "cursor"
    assert report.is_stale is True
    assert report.days_since_generation is None
