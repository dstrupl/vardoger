# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the Claude Code prompt writer."""

import tempfile
from pathlib import Path

from vardoger.writers.claude_code import (
    clear_claude_code_rules,
    read_claude_code_rules,
    write_claude_code_rules,
)


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
        project = Path(tmp)
        path = write_claude_code_rules("test content", scope="project", project_path=project)

        assert path.exists()
        assert path == project / ".claude" / "rules" / "vardoger.md"


def test_round_trip_project_scope():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        write_claude_code_rules("body", scope="project", project_path=project)
        assert read_claude_code_rules(scope="project", project_path=project) == "body"


def test_read_absent_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        assert read_claude_code_rules(scope="project", project_path=Path(tmp)) is None


def test_clear_removes_file():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        write_claude_code_rules("x", scope="project", project_path=project)
        assert clear_claude_code_rules(scope="project", project_path=project) is True
        assert read_claude_code_rules(scope="project", project_path=project) is None
        assert clear_claude_code_rules(scope="project", project_path=project) is False
