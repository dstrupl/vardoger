# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the Cursor prompt writer."""

import tempfile
from pathlib import Path

from vardoger.writers.cursor import (
    clear_cursor_rules,
    read_cursor_rules,
    write_cursor_rules,
)


def test_creates_file_with_frontmatter():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        path = write_cursor_rules("test content", project_path=project)

        assert path.exists()
        text = path.read_text()
        assert "alwaysApply: true" in text
        assert "test content" in text


def test_round_trip_write_then_read():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        body = "# Body\n- rule A\n- rule B\n"
        write_cursor_rules(body, project_path=project)
        assert read_cursor_rules(project_path=project) == body


def test_read_returns_none_when_absent():
    with tempfile.TemporaryDirectory() as tmp:
        assert read_cursor_rules(project_path=Path(tmp)) is None


def test_clear_removes_file():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        write_cursor_rules("x", project_path=project)
        assert clear_cursor_rules(project_path=project) is True
        assert read_cursor_rules(project_path=project) is None
        # Second clear is a no-op.
        assert clear_cursor_rules(project_path=project) is False
