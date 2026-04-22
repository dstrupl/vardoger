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


def _make_cursor_project(project: Path) -> Path:
    """Create a directory with a ``.git`` marker so the writers accept it.

    Every project-scope writer now refuses to drop rules into a directory
    that doesn't look like a project (``.git``/manifest/``AGENTS.md``/
    ``.cursor``); see https://github.com/dstrupl/vardoger/issues/18 (for
    Cursor) and https://github.com/dstrupl/vardoger/issues/21 (for the
    generalisation to the other writers).
    """
    project.mkdir(parents=True, exist_ok=True)
    (project / ".git").mkdir(exist_ok=True)
    return project


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

    project = _make_cursor_project(tmp_path / "proj")
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

    project = _make_cursor_project(tmp_path / "proj")
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


def _seed_generation(store: CheckpointStore, platform: str, output: Path, content: str) -> None:
    """Record a generation whose hash matches what ``read_*_rules`` will echo back.

    Each platform's read helper strips whitespace/fences, so record the
    post-round-trip content rather than the raw input so edit detection only
    fires on real user changes.
    """
    store.record_generation(
        platform,
        conversations_analyzed=0,
        output_path=str(output),
        content=content,
        output_hash=content_hash(content),
    )


def test_detect_edits_covers_copilot(tmp_path):
    from vardoger.writers.copilot import read_copilot_rules, write_copilot_rules

    project = _make_cursor_project(tmp_path / "proj")
    store = CheckpointStore(state_dir=tmp_path / "state")

    output = write_copilot_rules(GENERATED, scope="project", project_path=project)
    round_tripped = read_copilot_rules(scope="project", project_path=project)
    assert round_tripped is not None
    _seed_generation(store, "copilot", output, round_tripped)

    assert detect_edits("copilot", store, scope="project", project_path=project) is None

    edited = round_tripped + "\n- custom user rule"
    write_copilot_rules(edited, scope="project", project_path=project)

    event = detect_edits("copilot", store, scope="project", project_path=project)
    assert event is not None
    record = store.get_feedback("copilot")
    assert "custom user rule" in record.added_rules


def test_detect_edits_covers_windsurf(tmp_path):
    from vardoger.writers.windsurf import read_windsurf_rules, write_windsurf_rules

    project = _make_cursor_project(tmp_path / "proj")
    store = CheckpointStore(state_dir=tmp_path / "state")

    output = write_windsurf_rules(GENERATED, scope="project", project_path=project)
    round_tripped = read_windsurf_rules(scope="project", project_path=project)
    assert round_tripped is not None
    _seed_generation(store, "windsurf", output, round_tripped)

    assert detect_edits("windsurf", store, scope="project", project_path=project) is None

    edited = round_tripped + "\n- windsurf extra"
    write_windsurf_rules(edited, scope="project", project_path=project)

    event = detect_edits("windsurf", store, scope="project", project_path=project)
    assert event is not None
    record = store.get_feedback("windsurf")
    assert "windsurf extra" in record.added_rules


def test_detect_edits_covers_cline(tmp_path):
    from vardoger.writers.cline import read_cline_rules, write_cline_rules

    project = _make_cursor_project(tmp_path / "proj")
    store = CheckpointStore(state_dir=tmp_path / "state")

    output = write_cline_rules(GENERATED, scope="project", project_path=project)
    round_tripped = read_cline_rules(scope="project", project_path=project)
    assert round_tripped is not None
    _seed_generation(store, "cline", output, round_tripped)

    assert detect_edits("cline", store, scope="project", project_path=project) is None

    edited = round_tripped + "\n- cline extra rule"
    write_cline_rules(edited, scope="project", project_path=project)

    event = detect_edits("cline", store, scope="project", project_path=project)
    assert event is not None
    record = store.get_feedback("cline")
    assert "cline extra rule" in record.added_rules


def test_detect_edits_cline_skips_global_scope(tmp_path):
    store = CheckpointStore(state_dir=tmp_path / "state")
    store.record_generation(
        "cline",
        conversations_analyzed=0,
        output_path="/tmp/ignored",
        content=GENERATED,
        output_hash=content_hash(GENERATED),
    )
    # Global scope is not supported for Cline: detect_edits returns None instead of raising.
    assert detect_edits("cline", store, scope="global") is None


def test_detect_edits_is_idempotent_after_reverting(tmp_path):
    from vardoger.writers.cursor import write_cursor_rules

    project = _make_cursor_project(tmp_path / "proj")
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
