# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for user-feedback diffing and edit detection."""

from __future__ import annotations

import tempfile
from pathlib import Path

from vardoger.checkpoint import CheckpointStore, content_hash
from vardoger.feedback import detect_edits, diff_bullets, extract_bullets

GENERATED = """\
# Personalization

## Technical Stack
- Prefer Python with uv.
- Use ruff for linting.

## Things to Avoid
- Avoid emojis.
"""


def test_extract_bullets_orders_and_dedupes():
    text = "# H\n- a\n- b\n- a\n  - c\n"
    assert extract_bullets(text) == ["a", "b", "c"]


def test_diff_bullets_splits_into_three_buckets():
    before = "- kept 1\n- kept 2\n- gone\n"
    after = "- kept 1\n- kept 2\n- shiny new\n"
    kept, removed, added = diff_bullets(before, after)
    assert kept == ["kept 1", "kept 2"]
    assert removed == ["gone"]
    assert added == ["shiny new"]


def test_diff_bullets_ignores_non_bullet_content():
    before = "# Heading\n- a\nparagraph\n"
    after = "## Heading\n- a\nparagraph edit\n"
    kept, removed, added = diff_bullets(before, after)
    assert kept == ["a"]
    assert removed == []
    assert added == []


def test_detect_edits_returns_none_when_no_prior_generation():
    with tempfile.TemporaryDirectory() as tmp:
        store = CheckpointStore(state_dir=Path(tmp) / "state")
        # No generation recorded; cursor read won't matter.
        assert detect_edits("cursor", store, project_path=Path(tmp) / "proj") is None


def test_detect_edits_returns_none_when_file_matches(tmp_path):
    from vardoger.writers.cursor import write_cursor_rules

    project = tmp_path / "proj"
    store = CheckpointStore(state_dir=tmp_path / "state")

    output = write_cursor_rules(GENERATED, project_path=project)
    store.record_generation(
        "cursor",
        conversations_analyzed=0,
        output_path=str(output),
        content=GENERATED,
        output_hash=content_hash(GENERATED),
    )

    assert detect_edits("cursor", store, project_path=project) is None


def test_detect_edits_classifies_changes(tmp_path):
    from vardoger.writers.cursor import write_cursor_rules

    project = tmp_path / "proj"
    store = CheckpointStore(state_dir=tmp_path / "state")

    output = write_cursor_rules(GENERATED, project_path=project)
    store.record_generation(
        "cursor",
        conversations_analyzed=0,
        output_path=str(output),
        content=GENERATED,
        output_hash=content_hash(GENERATED),
    )

    edited = GENERATED.replace("- Avoid emojis.", "- Avoid emojis in production docs.").replace(
        "- Use ruff for linting.", "- Use ruff for linting.\n- Always write tests."
    )
    output.write_text(
        output.read_text().replace(
            GENERATED,
            edited,
        )
    )

    event = detect_edits("cursor", store, project_path=project)
    assert event is not None
    assert event.kind == "edit"
    assert "Always write tests" in event.summary

    record = store.get_feedback("cursor")
    assert "Prefer Python with uv." in record.kept_rules
    assert "Use ruff for linting." in record.kept_rules
    assert "Avoid emojis." in record.removed_rules
    assert "Always write tests." in record.added_rules
    assert "Avoid emojis in production docs." in record.added_rules


def test_detect_edits_is_idempotent_after_reverting(tmp_path):
    from vardoger.writers.cursor import write_cursor_rules

    project = tmp_path / "proj"
    store = CheckpointStore(state_dir=tmp_path / "state")

    output = write_cursor_rules(GENERATED, project_path=project)
    store.record_generation(
        "cursor",
        conversations_analyzed=0,
        output_path=str(output),
        content=GENERATED,
        output_hash=content_hash(GENERATED),
    )

    # No edit yet.
    assert detect_edits("cursor", store, project_path=project) is None

    # Make and then undo an edit.
    edited_text = GENERATED + "- extra\n"
    output.write_text(output.read_text().replace(GENERATED, edited_text))
    first = detect_edits("cursor", store, project_path=project)
    assert first is not None

    # Write the same content back (simulating a user revert).
    output.write_text(output.read_text().replace(edited_text, GENERATED))
    second = detect_edits("cursor", store, project_path=project)
    assert second is None
