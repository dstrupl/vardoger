# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for prompt template loading."""

import pytest

from vardoger.prompts import (
    analyze_skill_body,
    load_prompt,
    summarize_prompt,
    synthesize_prompt,
)


def test_summarize_prompt_loads():
    text = summarize_prompt()
    assert len(text) > 0
    assert isinstance(text, str)


def test_synthesize_prompt_loads():
    text = synthesize_prompt()
    assert len(text) > 0
    assert isinstance(text, str)


def test_claude_synthesis_excludes_auto_memory_content() -> None:
    text = synthesize_prompt("claude-code")

    assert "Claude Code memory boundary" in text
    assert "Omit repository facts" in text
    assert "durable, cross-project preferences" in text


def test_codex_synthesis_positions_agents_against_memories() -> None:
    text = synthesize_prompt("codex")

    assert "Codex memory boundary" in text
    assert "`AGENTS.md` is the durable instruction layer" in text
    assert "If a candidate rule merely restates remembered context, drop it" in text


def test_openclaw_skill_explains_sqlite_history_limit() -> None:
    text = analyze_skill_body("openclaw", "OpenClaw")

    assert "2.0 stores canonical history in per-agent SQLite databases" in text
    assert "Ask the user before setting" in text
    assert "stop the workflow and suggest OpenClaw" in text


def test_devin_skill_explains_opt_in_atif_exports() -> None:
    text = analyze_skill_body("devin", "Devin Local")

    assert "documented, user-enabled ATIF exports" in text
    assert "--export ~/.vardoger/imports/devin/" in text


def test_load_nonexistent_prompt():
    with pytest.raises(FileNotFoundError):
        load_prompt("nonexistent_prompt_name")
