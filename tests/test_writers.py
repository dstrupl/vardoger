"""Tests for the prompt writers."""

import tempfile
from pathlib import Path

from vardoger.writers.cursor import write_cursor_rules
from vardoger.writers.claude_code import write_claude_code_rules
from vardoger.writers.codex import write_codex_rules


def test_cursor_writer_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        path = write_cursor_rules("test content", project_path=project)

        assert path.exists()
        text = path.read_text()
        assert "alwaysApply: true" in text
        assert "test content" in text


def test_claude_code_writer_global():
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        rules_dir = home / ".claude" / "rules"

        path = write_claude_code_rules("test content", scope="global")
        assert path.exists()
        assert "test content" in path.read_text()

        path.unlink()
        path.parent.rmdir()


def test_claude_code_writer_project():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        path = write_claude_code_rules("test content", scope="project", project_path=project)

        assert path.exists()
        assert path == project / ".claude" / "rules" / "vardoger.md"


def test_codex_writer_creates_section():
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        agents_md = home / "AGENTS.md"

        path = write_codex_rules("test content", scope="project", project_path=home)

        assert path.exists()
        text = path.read_text()
        assert "<!-- vardoger:start -->" in text
        assert "test content" in text
        assert "<!-- vardoger:end -->" in text


def test_codex_writer_replaces_existing_section():
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
