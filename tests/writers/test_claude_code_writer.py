# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the Claude Code prompt writer."""

import tempfile
from pathlib import Path

import pytest

from vardoger.writers._projects import NotAProjectError, find_project_root
from vardoger.writers.claude_code import (
    clear_claude_code_rules,
    read_claude_code_rules,
    write_claude_code_rules,
)


def _as_project(dir_: Path) -> Path:
    """Create ``dir_`` (if needed) and attach a ``.git`` marker."""
    dir_.mkdir(parents=True, exist_ok=True)
    (dir_ / ".git").mkdir(exist_ok=True)
    return dir_


def test_global_scope():
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        _ = home / ".claude" / "rules"

        path = write_claude_code_rules("test content", scope="global")
        assert path.exists()
        assert "test content" in path.read_text()

        path.unlink()
        path.parent.rmdir()


def test_project_scope():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))
        path = write_claude_code_rules("test content", scope="project", project_path=project)

        assert path.exists()
        assert path == project / ".claude" / "rules" / "vardoger.md"


def test_round_trip_project_scope():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))
        write_claude_code_rules("body", scope="project", project_path=project)
        assert read_claude_code_rules(scope="project", project_path=project) == "body"


def test_read_absent_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        assert read_claude_code_rules(scope="project", project_path=Path(tmp)) is None


def test_clear_removes_file():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))
        write_claude_code_rules("x", scope="project", project_path=project)
        assert clear_claude_code_rules(scope="project", project_path=project) is True
        assert read_claude_code_rules(scope="project", project_path=project) is None
        assert clear_claude_code_rules(scope="project", project_path=project) is False


# ---------------------------------------------------------------------------
# Project-marker validation — regression for
# https://github.com/dstrupl/vardoger/issues/21
# ---------------------------------------------------------------------------


def test_project_scope_refuses_non_project_dir(tmp_path: Path) -> None:
    """scope=project must reject a directory with no project markers."""
    bare = tmp_path / "nothome"
    bare.mkdir()
    with pytest.raises(NotAProjectError):
        write_claude_code_rules("content", scope="project", project_path=bare)


def test_project_scope_accepts_nested_subdir_of_project(tmp_path: Path) -> None:
    """Writing inside a project subdirectory is fine — marker lives in an ancestor."""
    project = _as_project(tmp_path / "proj")
    nested = project / "packages" / "service"
    nested.mkdir(parents=True)
    output = write_claude_code_rules("body", scope="project", project_path=nested)
    assert output.is_file()
    assert output == nested / ".claude" / "rules" / "vardoger.md"


def test_global_scope_does_not_validate_project(tmp_path: Path) -> None:
    """scope=global must not trigger project validation (writes under HOME)."""
    # The bare directory used as HOME has no marker; still fine.
    bare_home = tmp_path / "bare_home"
    bare_home.mkdir()
    from unittest.mock import patch

    with patch("vardoger.writers.claude_code.Path.home", return_value=bare_home):
        path = write_claude_code_rules("body", scope="global")
    assert path == bare_home / ".claude" / "rules" / "vardoger.md"


def test_find_project_root_detects_markers(tmp_path: Path) -> None:
    """Shared ``find_project_root`` finds any marker in an ancestor."""
    project = _as_project(tmp_path / "proj")
    nested = project / "a" / "b"
    nested.mkdir(parents=True)
    assert find_project_root(nested) == project.resolve()
