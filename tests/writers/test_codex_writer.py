# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the Codex prompt writer."""

import tempfile
from pathlib import Path

import pytest

from vardoger.writers._projects import NotAProjectError, find_project_root
from vardoger.writers.codex import clear_codex_rules, read_codex_rules, write_codex_rules


def _as_project(dir_: Path) -> Path:
    """Create ``dir_`` (if needed) and attach a ``.git`` marker."""
    dir_.mkdir(parents=True, exist_ok=True)
    (dir_ / ".git").mkdir(exist_ok=True)
    return dir_


def test_creates_fenced_section():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))

        path = write_codex_rules("test content", scope="project", project_path=project)

        assert path.exists()
        text = path.read_text()
        assert "<!-- vardoger:start -->" in text
        assert "test content" in text
        assert "<!-- vardoger:end -->" in text


def test_replaces_existing_section():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))
        agents_md = project / "AGENTS.md"
        agents_md.write_text("# My rules\n\nSome content.\n")

        write_codex_rules("first pass", scope="project", project_path=project)
        write_codex_rules("second pass", scope="project", project_path=project)

        text = agents_md.read_text()
        assert "# My rules" in text
        assert "second pass" in text
        assert "first pass" not in text
        assert text.count("<!-- vardoger:start -->") == 1


def test_read_extracts_only_fenced_block():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))
        agents_md = project / "AGENTS.md"
        # AGENTS.md is itself a project marker; pre-creating it means the
        # project is detected even without the ``.git`` stub, but we keep
        # both for consistency with the other tests.
        agents_md.write_text("# User rules\n\nKeep this.\n")
        write_codex_rules("vardoger body", scope="project", project_path=project)

        inner = read_codex_rules(scope="project", project_path=project)
        assert inner == "vardoger body"


def test_read_returns_none_when_file_absent():
    with tempfile.TemporaryDirectory() as tmp:
        assert read_codex_rules(scope="project", project_path=Path(tmp)) is None


def test_read_returns_none_when_no_section_present():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))
        (project / "AGENTS.md").write_text("only user content")
        assert read_codex_rules(scope="project", project_path=project) is None


def test_clear_preserves_user_content():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))
        agents_md = project / "AGENTS.md"
        agents_md.write_text("# User rules\n\nKeep this.\n")
        write_codex_rules("vardoger body", scope="project", project_path=project)
        assert clear_codex_rules(scope="project", project_path=project) is True

        remaining = agents_md.read_text()
        assert "Keep this." in remaining
        assert "vardoger:start" not in remaining
        assert clear_codex_rules(scope="project", project_path=project) is False


def test_clear_removes_file_when_only_vardoger_content():
    with tempfile.TemporaryDirectory() as tmp:
        project = _as_project(Path(tmp))
        write_codex_rules("vardoger body", scope="project", project_path=project)
        assert clear_codex_rules(scope="project", project_path=project) is True
        assert not (project / "AGENTS.md").is_file()


# ---------------------------------------------------------------------------
# Project-marker validation — regression for
# https://github.com/dstrupl/vardoger/issues/21
# ---------------------------------------------------------------------------


def test_project_scope_refuses_non_project_dir(tmp_path: Path) -> None:
    """scope=project must reject a directory with no project markers."""
    bare = tmp_path / "nothome"
    bare.mkdir()
    with pytest.raises(NotAProjectError):
        write_codex_rules("content", scope="project", project_path=bare)


def test_project_scope_accepts_nested_subdir_of_project(tmp_path: Path) -> None:
    """Writing inside a project subdirectory is fine."""
    project = _as_project(tmp_path / "proj")
    nested = project / "packages" / "service"
    nested.mkdir(parents=True)
    output = write_codex_rules("body", scope="project", project_path=nested)
    assert output.is_file()
    assert output == nested / "AGENTS.md"


def test_global_scope_does_not_validate_project(tmp_path: Path) -> None:
    """scope=global writes under ~/.codex/ without touching project validation."""
    bare_home = tmp_path / "bare_home"
    bare_home.mkdir()
    from unittest.mock import patch

    with patch("vardoger.writers.codex.Path.home", return_value=bare_home):
        path = write_codex_rules("body", scope="global")
    assert path == bare_home / ".codex" / "AGENTS.md"


def test_find_project_root_detects_agents_md(tmp_path: Path) -> None:
    """AGENTS.md alone should anchor a project root for Codex."""
    project = tmp_path / "proj"
    project.mkdir()
    (project / "AGENTS.md").write_text("")
    nested = project / "a" / "b"
    nested.mkdir(parents=True)
    assert find_project_root(nested) == project.resolve()
