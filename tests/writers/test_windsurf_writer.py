# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the Windsurf rules writer."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from vardoger.writers._projects import NotAProjectError, find_project_root
from vardoger.writers.windsurf import (
    clear_windsurf_rules,
    read_windsurf_rules,
    write_windsurf_rules,
)


def _as_project(dir_: Path) -> Path:
    """Create ``dir_`` (if needed) and attach a ``.git`` marker."""
    dir_.mkdir(parents=True, exist_ok=True)
    (dir_ / ".git").mkdir(exist_ok=True)
    return dir_


def test_project_scope_writes_dedicated_file():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))
        path = write_windsurf_rules("body", scope="project", project_path=project)

        assert path == project / ".windsurf" / "rules" / "vardoger.md"
        assert path.read_text() == "body"
        assert read_windsurf_rules(scope="project", project_path=project) == "body"


def test_project_scope_overwrites_in_place():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))
        write_windsurf_rules("first", scope="project", project_path=project)
        write_windsurf_rules("second", scope="project", project_path=project)
        path = project / ".windsurf" / "rules" / "vardoger.md"
        assert path.read_text() == "second"


def test_project_scope_clear_removes_file():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))
        write_windsurf_rules("body", scope="project", project_path=project)
        assert clear_windsurf_rules(scope="project", project_path=project) is True
        assert not (project / ".windsurf" / "rules" / "vardoger.md").is_file()
        assert clear_windsurf_rules(scope="project", project_path=project) is False


def test_global_scope_creates_fenced_section():
    with tempfile.TemporaryDirectory() as tmp:
        fake_home = Path(tmp)
        with patch("vardoger.writers.windsurf.Path.home", return_value=fake_home):
            path = write_windsurf_rules("content", scope="global")
        assert path == (fake_home / ".codeium" / "windsurf" / "memories" / "global_rules.md")
        text = path.read_text()
        assert "<!-- vardoger:start -->" in text
        assert "content" in text
        assert "<!-- vardoger:end -->" in text


def test_global_scope_preserves_user_content():
    with tempfile.TemporaryDirectory() as tmp:
        fake_home = Path(tmp)
        rules = fake_home / ".codeium" / "windsurf" / "memories" / "global_rules.md"
        rules.parent.mkdir(parents=True)
        rules.write_text("# My global rules\n\nKeep this.\n")

        with patch("vardoger.writers.windsurf.Path.home", return_value=fake_home):
            write_windsurf_rules("first", scope="global")
            write_windsurf_rules("second", scope="global")

        text = rules.read_text()
        assert "Keep this." in text
        assert "second" in text
        assert "first" not in text
        assert text.count("<!-- vardoger:start -->") == 1


def test_global_scope_read_returns_inner():
    with tempfile.TemporaryDirectory() as tmp:
        fake_home = Path(tmp)
        with patch("vardoger.writers.windsurf.Path.home", return_value=fake_home):
            write_windsurf_rules("inner", scope="global")
            assert read_windsurf_rules(scope="global") == "inner"


def test_global_scope_read_returns_none_when_absent():
    with tempfile.TemporaryDirectory() as tmp:
        fake_home = Path(tmp)
        with patch("vardoger.writers.windsurf.Path.home", return_value=fake_home):
            assert read_windsurf_rules(scope="global") is None


def test_global_scope_clear_preserves_user_content():
    with tempfile.TemporaryDirectory() as tmp:
        fake_home = Path(tmp)
        rules = fake_home / ".codeium" / "windsurf" / "memories" / "global_rules.md"
        rules.parent.mkdir(parents=True)
        rules.write_text("# User rules\n\nKeep.\n")

        with patch("vardoger.writers.windsurf.Path.home", return_value=fake_home):
            write_windsurf_rules("body", scope="global")
            assert clear_windsurf_rules(scope="global") is True

        remaining = rules.read_text()
        assert "Keep." in remaining
        assert "vardoger:start" not in remaining


def test_global_scope_clear_deletes_file_when_only_vardoger_content():
    with tempfile.TemporaryDirectory() as tmp:
        fake_home = Path(tmp)
        with patch("vardoger.writers.windsurf.Path.home", return_value=fake_home):
            write_windsurf_rules("body", scope="global")
            assert clear_windsurf_rules(scope="global") is True
        assert not (fake_home / ".codeium" / "windsurf" / "memories" / "global_rules.md").is_file()


# ---------------------------------------------------------------------------
# Project-marker validation — regression for
# https://github.com/dstrupl/vardoger/issues/21
# ---------------------------------------------------------------------------


def test_project_scope_refuses_non_project_dir(tmp_path: Path) -> None:
    """scope=project must reject a directory with no project markers."""
    bare = tmp_path / "nothome"
    bare.mkdir()
    with pytest.raises(NotAProjectError):
        write_windsurf_rules("content", scope="project", project_path=bare)


def test_project_scope_accepts_nested_subdir_of_project(tmp_path: Path) -> None:
    """Writing inside a project subdirectory is fine."""
    project = _as_project(tmp_path / "proj")
    nested = project / "packages" / "service"
    nested.mkdir(parents=True)
    output = write_windsurf_rules("body", scope="project", project_path=nested)
    assert output.is_file()
    assert output == nested / ".windsurf" / "rules" / "vardoger.md"


def test_global_scope_does_not_validate_project(tmp_path: Path) -> None:
    """scope=global writes under ~/.codeium/ without project validation."""
    bare_home = tmp_path / "bare_home"
    bare_home.mkdir()
    with patch("vardoger.writers.windsurf.Path.home", return_value=bare_home):
        path = write_windsurf_rules("body", scope="global")
    assert path == bare_home / ".codeium" / "windsurf" / "memories" / "global_rules.md"


def test_find_project_root_detects_cargo_toml(tmp_path: Path) -> None:
    """Cargo.toml anchors a project root."""
    project = tmp_path / "proj"
    project.mkdir()
    (project / "Cargo.toml").write_text("")
    nested = project / "a" / "b"
    nested.mkdir(parents=True)
    assert find_project_root(nested) == project.resolve()
