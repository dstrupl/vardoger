# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the GitHub Copilot instructions writer."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from vardoger.writers._projects import NotAProjectError, find_project_root
from vardoger.writers.copilot import (
    clear_copilot_rules,
    read_copilot_rules,
    write_copilot_rules,
)


def _as_project(dir_: Path) -> Path:
    """Create ``dir_`` (if needed) and attach a ``.git`` marker."""
    dir_.mkdir(parents=True, exist_ok=True)
    (dir_ / ".git").mkdir(exist_ok=True)
    return dir_


def test_creates_project_fenced_section():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))

        path = write_copilot_rules("test content", scope="project", project_path=project)

        assert path == project / ".github" / "copilot-instructions.md"
        assert path.is_file()
        text = path.read_text()
        assert "<!-- vardoger:start -->" in text
        assert "test content" in text
        assert "<!-- vardoger:end -->" in text


def test_replaces_existing_section():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))
        target = project / ".github" / "copilot-instructions.md"
        target.parent.mkdir(parents=True)
        target.write_text("# Team instructions\n\nSome content.\n")

        write_copilot_rules("first pass", scope="project", project_path=project)
        write_copilot_rules("second pass", scope="project", project_path=project)

        text = target.read_text()
        assert "# Team instructions" in text
        assert "second pass" in text
        assert "first pass" not in text
        assert text.count("<!-- vardoger:start -->") == 1


def test_global_scope_uses_home():
    with tempfile.TemporaryDirectory() as tmp:
        fake_home = Path(tmp)
        with patch("vardoger.writers.copilot.Path.home", return_value=fake_home):
            path = write_copilot_rules("body", scope="global")
        assert path == fake_home / ".copilot" / "copilot-instructions.md"
        assert path.is_file()
        assert "body" in path.read_text()


def test_read_extracts_only_fenced_block():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))
        target = project / ".github" / "copilot-instructions.md"
        target.parent.mkdir(parents=True)
        target.write_text("# Team content\n\nKeep this.\n")
        write_copilot_rules("vardoger body", scope="project", project_path=project)

        inner = read_copilot_rules(scope="project", project_path=project)
        assert inner == "vardoger body"


def test_read_returns_none_when_file_absent():
    with tempfile.TemporaryDirectory() as tmp:
        assert read_copilot_rules(scope="project", project_path=Path(tmp)) is None


def test_read_returns_none_when_no_section():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))
        target = project / ".github" / "copilot-instructions.md"
        target.parent.mkdir(parents=True)
        target.write_text("only user content")
        assert read_copilot_rules(scope="project", project_path=project) is None


def test_clear_preserves_user_content():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))
        target = project / ".github" / "copilot-instructions.md"
        target.parent.mkdir(parents=True)
        target.write_text("# Team content\n\nKeep this.\n")
        write_copilot_rules("vardoger body", scope="project", project_path=project)
        assert clear_copilot_rules(scope="project", project_path=project) is True

        remaining = target.read_text()
        assert "Keep this." in remaining
        assert "vardoger:start" not in remaining
        assert clear_copilot_rules(scope="project", project_path=project) is False


def test_clear_removes_file_when_only_vardoger_content():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))
        write_copilot_rules("vardoger body", scope="project", project_path=project)
        target = project / ".github" / "copilot-instructions.md"
        assert target.is_file()
        assert clear_copilot_rules(scope="project", project_path=project) is True
        assert not target.is_file()


# ---------------------------------------------------------------------------
# Project-marker validation — regression for
# https://github.com/dstrupl/vardoger/issues/21
# ---------------------------------------------------------------------------


def test_project_scope_refuses_non_project_dir(tmp_path: Path) -> None:
    """scope=project must reject a directory with no project markers."""
    bare = tmp_path / "nothome"
    bare.mkdir()
    with pytest.raises(NotAProjectError):
        write_copilot_rules("content", scope="project", project_path=bare)


def test_project_scope_accepts_nested_subdir_of_project(tmp_path: Path) -> None:
    """Writing inside a project subdirectory is fine."""
    project = _as_project(tmp_path / "proj")
    nested = project / "packages" / "service"
    nested.mkdir(parents=True)
    output = write_copilot_rules("body", scope="project", project_path=nested)
    assert output.is_file()
    assert output == nested / ".github" / "copilot-instructions.md"


def test_global_scope_does_not_validate_project(tmp_path: Path) -> None:
    """scope=global writes under ~/.copilot/ without project validation."""
    bare_home = tmp_path / "bare_home"
    bare_home.mkdir()
    with patch("vardoger.writers.copilot.Path.home", return_value=bare_home):
        path = write_copilot_rules("body", scope="global")
    assert path == bare_home / ".copilot" / "copilot-instructions.md"


def test_find_project_root_detects_package_json(tmp_path: Path) -> None:
    """package.json anchors a project root for Copilot."""
    project = tmp_path / "proj"
    project.mkdir()
    (project / "package.json").write_text("{}")
    nested = project / "a" / "b"
    nested.mkdir(parents=True)
    assert find_project_root(nested) == project.resolve()
