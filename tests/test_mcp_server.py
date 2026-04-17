# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for vardoger's MCP server tools.

Each ``@mcp.tool()`` decorated function in :mod:`vardoger.mcp_server`
remains directly callable, so we exercise them without spinning up the
MCP transport. Shared fixtures (``fake_home``, ``project_cwd``,
``patch_history_readers``, ``reset_mcp_cache``) isolate state to
``tmp_path``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vardoger import mcp_server
from vardoger.checkpoint import CheckpointStore

# ---------------------------------------------------------------------------
# status / personalize
# ---------------------------------------------------------------------------


def test_vardoger_status_reports_never_generated(fake_home: Path) -> None:
    payload = json.loads(mcp_server.vardoger_status())
    assert payload["platform"] == "cursor"
    assert payload["is_stale"] is True
    assert "never generated" in payload["reason"]


def test_vardoger_personalize_returns_orchestration_instructions(fake_home: Path) -> None:
    text = mcp_server.vardoger_personalize()
    assert "Personalize Your Assistant" in text
    assert "vardoger_status" in text


# ---------------------------------------------------------------------------
# prepare (with cache)
# ---------------------------------------------------------------------------


def test_vardoger_prepare_metadata(
    fake_home: Path,
    patch_history_readers: object,
    reset_mcp_cache: None,
) -> None:
    payload = json.loads(mcp_server.vardoger_prepare())
    assert payload["batches"] == 1
    assert payload["total_conversations"] == 2


def test_vardoger_prepare_returns_batch_content(
    fake_home: Path,
    patch_history_readers: object,
    reset_mcp_cache: None,
) -> None:
    text = mcp_server.vardoger_prepare(batch=1)
    assert "Conversation Batch 1 of 1" in text
    assert "---" in text


def test_vardoger_prepare_batch_out_of_range(
    fake_home: Path,
    patch_history_readers: object,
    reset_mcp_cache: None,
) -> None:
    text = mcp_server.vardoger_prepare(batch=99)
    assert "out of range" in text


def test_vardoger_prepare_reuses_cache(
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    reset_mcp_cache: None,
    make_conversations,
) -> None:
    """The second call must not re-read history."""
    convs = make_conversations()
    calls = {"count": 0}

    def counted(**_kwargs: object) -> list:
        calls["count"] += 1
        return convs

    monkeypatch.setattr("vardoger.mcp_server.read_cursor_history", counted)

    mcp_server.vardoger_prepare()
    mcp_server.vardoger_prepare()
    assert calls["count"] == 1
    assert mcp_server._cached_batches is not None


# ---------------------------------------------------------------------------
# synthesize_prompt
# ---------------------------------------------------------------------------


def test_vardoger_synthesize_prompt_without_feedback(fake_home: Path) -> None:
    text = mcp_server.vardoger_synthesize_prompt()
    assert text
    assert "---" not in text.splitlines()[0]


def test_vardoger_synthesize_prompt_prepends_feedback_context(fake_home: Path) -> None:
    store = CheckpointStore()
    record = store.get_feedback("cursor")
    record.kept_rules = ["keeper"]
    record.removed_rules = ["dropper"]
    record.added_rules = ["newcomer"]
    store.save()

    text = mcp_server.vardoger_synthesize_prompt()
    assert "keeper" in text
    assert "dropper" in text
    assert "newcomer" in text
    assert "---" in text


# ---------------------------------------------------------------------------
# write / preview
# ---------------------------------------------------------------------------


def test_vardoger_write_records_generation(
    fake_home: Path,
    project_cwd: Path,
) -> None:
    content = "# Personalization\n\n- keep it simple\n"
    result = mcp_server.vardoger_write(content, project_path=str(project_cwd))
    assert "wrote personalization" in result

    rules = project_cwd / ".cursor" / "rules" / "vardoger.md"
    assert rules.is_file()
    assert "- keep it simple" in rules.read_text()

    store = CheckpointStore()
    assert store.get_generation("cursor") is not None


def test_vardoger_preview_identical_returns_no_change(fake_home: Path, project_cwd: Path) -> None:
    content = "# Same\n\n- rule\n"
    mcp_server.vardoger_write(content, project_path=str(project_cwd))
    result = mcp_server.vardoger_preview(content, project_path=str(project_cwd))
    assert "no changes" in result


def test_vardoger_preview_shows_diff(fake_home: Path, project_cwd: Path) -> None:
    mcp_server.vardoger_write("# First\n\n- one\n", project_path=str(project_cwd))
    result = mcp_server.vardoger_preview("# First\n\n- two\n", project_path=str(project_cwd))
    assert "one" in result
    assert "two" in result
    assert result.startswith("---") or "@@" in result


# ---------------------------------------------------------------------------
# feedback
# ---------------------------------------------------------------------------


def test_vardoger_feedback_unknown_kind(fake_home: Path) -> None:
    assert "unknown feedback kind" in mcp_server.vardoger_feedback("maybe")


def test_vardoger_feedback_accept_records_event(fake_home: Path) -> None:
    assert "recorded accept" in mcp_server.vardoger_feedback("accept", reason="ok")

    store = CheckpointStore()
    record = store.get_feedback("cursor")
    assert any(e.kind == "accept" for e in record.events)


def test_vardoger_feedback_reject_reverts_to_previous(fake_home: Path, project_cwd: Path) -> None:
    mcp_server.vardoger_write("# First\n\n- one\n", project_path=str(project_cwd))
    mcp_server.vardoger_write("# Second\n\n- two\n", project_path=str(project_cwd))

    result = mcp_server.vardoger_feedback("reject", project_path=str(project_cwd))
    assert "reverted cursor" in result
    rules = (project_cwd / ".cursor" / "rules" / "vardoger.md").read_text()
    assert "one" in rules
    assert "two" not in rules


def test_vardoger_feedback_reject_clears_when_no_prior(fake_home: Path, project_cwd: Path) -> None:
    mcp_server.vardoger_write("# Only\n\n- single\n", project_path=str(project_cwd))
    result = mcp_server.vardoger_feedback("reject", project_path=str(project_cwd))
    assert "cleared cursor personalization" in result
    assert not (project_cwd / ".cursor" / "rules" / "vardoger.md").is_file()


def test_vardoger_feedback_reject_without_history(fake_home: Path) -> None:
    result = mcp_server.vardoger_feedback("reject")
    assert "nothing to revert" in result


# ---------------------------------------------------------------------------
# compare
# ---------------------------------------------------------------------------


def test_vardoger_compare_never_personalized(
    fake_home: Path,
    patch_history_readers: object,
) -> None:
    payload = json.loads(mcp_server.vardoger_compare())
    assert payload["platform"] == "cursor"
    assert payload["before"] is None
    assert payload["after"] is None
    assert any("never personalized" in c for c in payload["caveats"])


def test_vardoger_compare_with_window_after_generation(
    fake_home: Path,
    patch_history_readers: object,
) -> None:
    store = CheckpointStore()
    store.record_generation("cursor", conversations_analyzed=1, output_path="/tmp/out")
    store.save()

    payload = json.loads(mcp_server.vardoger_compare(window_days=30))
    assert payload["platform"] == "cursor"
    assert payload["cutoff"] is not None
