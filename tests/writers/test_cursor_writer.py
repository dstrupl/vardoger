# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the Cursor prompt writer."""

import tempfile
from pathlib import Path

import pytest

from vardoger.writers.cursor import (
    NotAProjectError,
    _find_project_root,
    clear_cursor_rules,
    read_cursor_rules,
    write_cursor_rules,
)


def _as_project(dir_: Path) -> Path:
    """Create ``dir_`` (if needed) and attach a ``.git`` marker so the writer accepts it."""
    dir_.mkdir(parents=True, exist_ok=True)
    (dir_ / ".git").mkdir(exist_ok=True)
    return dir_


def test_creates_file_with_frontmatter():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))
        path = write_cursor_rules("test content", project_path=project)

        assert path.exists()
        text = path.read_text()
        assert "alwaysApply: true" in text
        assert "test content" in text


def test_round_trip_write_then_read():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))
        body = "# Body\n- rule A\n- rule B\n"
        write_cursor_rules(body, project_path=project)
        assert read_cursor_rules(project_path=project) == body


def test_read_returns_none_when_absent():
    with tempfile.TemporaryDirectory() as tmp:
        assert read_cursor_rules(project_path=Path(tmp)) is None


def test_clear_removes_file():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))
        write_cursor_rules("x", project_path=project)
        assert clear_cursor_rules(project_path=project) is True
        assert read_cursor_rules(project_path=project) is None
        # Second clear is a no-op.
        assert clear_cursor_rules(project_path=project) is False


# ---------------------------------------------------------------------------
# Project-marker validation — regression for
# https://github.com/dstrupl/vardoger/issues/18
# ---------------------------------------------------------------------------


def test_write_refuses_non_project_dir(tmp_path: Path) -> None:
    """A path with no project markers must be rejected, not silently written."""
    bare = tmp_path / "nothome"
    bare.mkdir()
    with pytest.raises(NotAProjectError):
        write_cursor_rules("content", project_path=bare)


def test_write_accepts_nested_subdir_of_project(tmp_path: Path) -> None:
    """Writing inside a project subdirectory is fine — the marker lives in an ancestor."""
    project = _as_project(tmp_path / "proj")
    nested = project / "packages" / "service"
    nested.mkdir(parents=True)
    output = write_cursor_rules("body", project_path=nested)
    assert output.is_file()
    assert (nested / ".cursor" / "rules" / "vardoger.md").is_file()


def test_find_project_root_detects_each_marker(tmp_path: Path) -> None:
    """Each marker in PROJECT_MARKERS should independently anchor a project root."""
    for marker in ("pyproject.toml", "package.json", "AGENTS.md", ".cursor"):
        sub = tmp_path / f"proj-{marker.lstrip('.').replace('.', '-')}"
        sub.mkdir()
        if marker.endswith((".toml", ".json", ".md")):
            (sub / marker).write_text("")
        else:
            (sub / marker).mkdir()
        assert _find_project_root(sub) == sub.resolve()
