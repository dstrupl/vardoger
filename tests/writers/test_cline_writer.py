# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the Cline rules writer."""

import tempfile
from pathlib import Path

import pytest

from vardoger.writers._projects import NotAProjectError, find_project_root
from vardoger.writers.cline import (
    clear_cline_rules,
    read_cline_rules,
    write_cline_rules,
)


def _as_project(dir_: Path) -> Path:
    """Create ``dir_`` (if needed) and attach a ``.git`` marker."""
    dir_.mkdir(parents=True, exist_ok=True)
    (dir_ / ".git").mkdir(exist_ok=True)
    return dir_


def test_creates_fenced_section_in_file():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))
        path = write_cline_rules("body", scope="project", project_path=project)
        assert path == project / ".clinerules"
        text = path.read_text()
        assert "<!-- vardoger:start -->" in text
        assert "body" in text
        assert "<!-- vardoger:end -->" in text


def test_replaces_existing_section():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))
        rules = project / ".clinerules"
        rules.write_text("# Team rules\n\nKeep this.\n")

        write_cline_rules("first", scope="project", project_path=project)
        write_cline_rules("second", scope="project", project_path=project)

        text = rules.read_text()
        assert "Keep this." in text
        assert "second" in text
        assert "first" not in text
        assert text.count("<!-- vardoger:start -->") == 1


def test_read_extracts_fenced_block():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))
        (project / ".clinerules").write_text("# User\n\nUser content.\n")
        write_cline_rules("vardoger body", scope="project", project_path=project)
        assert read_cline_rules(scope="project", project_path=project) == "vardoger body"


def test_read_returns_none_when_absent():
    with tempfile.TemporaryDirectory() as tmp:
        # Read does NOT trigger project validation (it just returns None).
        assert read_cline_rules(scope="project", project_path=Path(tmp)) is None


def test_clear_preserves_user_content():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))
        rules = project / ".clinerules"
        rules.write_text("# Team rules\n\nKeep this.\n")
        write_cline_rules("body", scope="project", project_path=project)
        assert clear_cline_rules(scope="project", project_path=project) is True
        remaining = rules.read_text()
        assert "Keep this." in remaining
        assert "vardoger:start" not in remaining


def test_clear_removes_file_when_only_vardoger():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))
        write_cline_rules("body", scope="project", project_path=project)
        assert clear_cline_rules(scope="project", project_path=project) is True
        assert not (project / ".clinerules").is_file()


def test_dedicated_file_when_directory_exists():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))
        (project / ".clinerules").mkdir()

        path = write_cline_rules("body", scope="project", project_path=project)
        assert path == project / ".clinerules" / "vardoger.md"
        assert path.read_text() == "body"
        assert read_cline_rules(scope="project", project_path=project) == "body"

        write_cline_rules("second", scope="project", project_path=project)
        assert path.read_text() == "second"

        assert clear_cline_rules(scope="project", project_path=project) is True
        assert not path.is_file()


def test_global_scope_raises():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        with pytest.raises(ValueError, match="global"):
            write_cline_rules("body", scope="global", project_path=project)
        with pytest.raises(ValueError, match="global"):
            read_cline_rules(scope="global", project_path=project)
        with pytest.raises(ValueError, match="global"):
            clear_cline_rules(scope="global", project_path=project)


# ---------------------------------------------------------------------------
# Project-marker validation — regression for
# https://github.com/dstrupl/vardoger/issues/21
#
# Cline is the most exposed platform: its *only* scope is project, so the
# check fires on every call — including the default-scope, no-project_path
# case an MCP server launched with cwd=$HOME routinely produces.
# ---------------------------------------------------------------------------


def test_refuses_non_project_dir(tmp_path: Path) -> None:
    """Writing into a directory with no markers must raise, not silently land."""
    bare = tmp_path / "nothome"
    bare.mkdir()
    with pytest.raises(NotAProjectError):
        write_cline_rules("content", scope="project", project_path=bare)


def test_refuses_cwd_when_cwd_is_bare(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With project_path omitted, cwd is the fallback — and cwd=$HOME must refuse.

    This is the out-of-the-box cline-from-MCP bug: scope defaults to
    ``project`` and cwd defaults to ``$HOME``, so vardoger would land
    ``~/.clinerules`` at a path Cline never reads.
    """
    bare = tmp_path / "nothome"
    bare.mkdir()
    monkeypatch.chdir(bare)
    with pytest.raises(NotAProjectError):
        write_cline_rules("content")


def test_accepts_nested_subdir_of_project(tmp_path: Path) -> None:
    """Writing inside a project subdirectory is fine."""
    project = _as_project(tmp_path / "proj")
    nested = project / "packages" / "service"
    nested.mkdir(parents=True)
    output = write_cline_rules("body", scope="project", project_path=nested)
    assert output.is_file()
    # .clinerules lands at the supplied ``nested`` path, not at the detected
    # project root — the validator's job is "is this inside a project?",
    # not "relocate the write".
    assert output == nested / ".clinerules"


def test_find_project_root_detects_git(tmp_path: Path) -> None:
    """``.git`` anchors a project root for Cline."""
    project = _as_project(tmp_path / "proj")
    nested = project / "a" / "b"
    nested.mkdir(parents=True)
    assert find_project_root(nested) == project.resolve()
