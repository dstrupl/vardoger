# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the Cline rules writer."""

import tempfile
from pathlib import Path

import pytest

from vardoger.writers.cline import (
    clear_cline_rules,
    read_cline_rules,
    write_cline_rules,
)


def test_creates_fenced_section_in_file():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        path = write_cline_rules("body", scope="project", project_path=project)
        assert path == project / ".clinerules"
        text = path.read_text()
        assert "<!-- vardoger:start -->" in text
        assert "body" in text
        assert "<!-- vardoger:end -->" in text


def test_replaces_existing_section():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
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
        project = Path(tmp)
        (project / ".clinerules").write_text("# User\n\nUser content.\n")
        write_cline_rules("vardoger body", scope="project", project_path=project)
        assert read_cline_rules(scope="project", project_path=project) == "vardoger body"


def test_read_returns_none_when_absent():
    with tempfile.TemporaryDirectory() as tmp:
        assert read_cline_rules(scope="project", project_path=Path(tmp)) is None


def test_clear_preserves_user_content():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        rules = project / ".clinerules"
        rules.write_text("# Team rules\n\nKeep this.\n")
        write_cline_rules("body", scope="project", project_path=project)
        assert clear_cline_rules(scope="project", project_path=project) is True
        remaining = rules.read_text()
        assert "Keep this." in remaining
        assert "vardoger:start" not in remaining


def test_clear_removes_file_when_only_vardoger():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        write_cline_rules("body", scope="project", project_path=project)
        assert clear_cline_rules(scope="project", project_path=project) is True
        assert not (project / ".clinerules").is_file()


def test_dedicated_file_when_directory_exists():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
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
