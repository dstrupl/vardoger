# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the Codex prompt writer."""

import tempfile
from pathlib import Path

from vardoger.writers.codex import write_codex_rules


def test_creates_fenced_section():
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)

        path = write_codex_rules("test content", scope="project", project_path=home)

        assert path.exists()
        text = path.read_text()
        assert "<!-- vardoger:start -->" in text
        assert "test content" in text
        assert "<!-- vardoger:end -->" in text


def test_replaces_existing_section():
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        agents_md = home / "AGENTS.md"
        agents_md.write_text("# My rules\n\nSome content.\n")

        write_codex_rules("first pass", scope="project", project_path=home)
        write_codex_rules("second pass", scope="project", project_path=home)

        text = agents_md.read_text()
        assert "# My rules" in text
        assert "second pass" in text
        assert "first pass" not in text
        assert text.count("<!-- vardoger:start -->") == 1
