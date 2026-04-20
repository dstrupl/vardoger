# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the Windsurf rules writer."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from vardoger.writers.windsurf import (
    clear_windsurf_rules,
    read_windsurf_rules,
    write_windsurf_rules,
)


def test_project_scope_writes_dedicated_file():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        path = write_windsurf_rules("body", scope="project", project_path=project)

        assert path == project / ".windsurf" / "rules" / "vardoger.md"
        assert path.read_text() == "body"
        assert read_windsurf_rules(scope="project", project_path=project) == "body"


def test_project_scope_overwrites_in_place():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        write_windsurf_rules("first", scope="project", project_path=project)
        write_windsurf_rules("second", scope="project", project_path=project)
        path = project / ".windsurf" / "rules" / "vardoger.md"
        assert path.read_text() == "second"


def test_project_scope_clear_removes_file():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
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
