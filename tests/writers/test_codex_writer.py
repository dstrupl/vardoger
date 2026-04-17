# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the Codex prompt writer."""

import tempfile
from pathlib import Path

from vardoger.writers.codex import clear_codex_rules, read_codex_rules, write_codex_rules


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


def test_read_extracts_only_fenced_block():
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        agents_md = home / "AGENTS.md"
        agents_md.write_text("# User rules\n\nKeep this.\n")
        write_codex_rules("vardoger body", scope="project", project_path=home)

        inner = read_codex_rules(scope="project", project_path=home)
        assert inner == "vardoger body"


def test_read_returns_none_when_file_absent():
    with tempfile.TemporaryDirectory() as tmp:
        assert read_codex_rules(scope="project", project_path=Path(tmp)) is None


def test_read_returns_none_when_no_section_present():
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        (home / "AGENTS.md").write_text("only user content")
        assert read_codex_rules(scope="project", project_path=home) is None


def test_clear_preserves_user_content():
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        agents_md = home / "AGENTS.md"
        agents_md.write_text("# User rules\n\nKeep this.\n")
        write_codex_rules("vardoger body", scope="project", project_path=home)
        assert clear_codex_rules(scope="project", project_path=home) is True

        remaining = agents_md.read_text()
        assert "Keep this." in remaining
        assert "vardoger:start" not in remaining
        assert clear_codex_rules(scope="project", project_path=home) is False


def test_clear_removes_file_when_only_vardoger_content():
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        write_codex_rules("vardoger body", scope="project", project_path=home)
        assert clear_codex_rules(scope="project", project_path=home) is True
        assert not (home / "AGENTS.md").is_file()
