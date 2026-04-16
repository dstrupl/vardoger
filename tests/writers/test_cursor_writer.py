# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the Cursor prompt writer."""

import tempfile
from pathlib import Path

from vardoger.writers.cursor import write_cursor_rules


def test_creates_file_with_frontmatter():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        path = write_cursor_rules("test content", project_path=project)

        assert path.exists()
        text = path.read_text()
        assert "alwaysApply: true" in text
        assert "test content" in text
