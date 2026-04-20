# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the GitHub Copilot instructions writer."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from vardoger.writers.copilot import (
    clear_copilot_rules,
    read_copilot_rules,
    write_copilot_rules,
)


def test_creates_project_fenced_section():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)

        path = write_copilot_rules("test content", scope="project", project_path=project)

        assert path == project / ".github" / "copilot-instructions.md"
        assert path.is_file()
        text = path.read_text()
        assert "<!-- vardoger:start -->" in text
        assert "test content" in text
        assert "<!-- vardoger:end -->" in text


def test_replaces_existing_section():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
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
        project = Path(tmp)
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
        project = Path(tmp)
        target = project / ".github" / "copilot-instructions.md"
        target.parent.mkdir(parents=True)
        target.write_text("only user content")
        assert read_copilot_rules(scope="project", project_path=project) is None


def test_clear_preserves_user_content():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
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
        project = Path(tmp)
        write_copilot_rules("vardoger body", scope="project", project_path=project)
        target = project / ".github" / "copilot-instructions.md"
        assert target.is_file()
        assert clear_copilot_rules(scope="project", project_path=project) is True
        assert not target.is_file()
