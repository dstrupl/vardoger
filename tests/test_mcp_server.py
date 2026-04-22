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

from vardoger import __version__ as _VARDOGER_VERSION
from vardoger import mcp_server
from vardoger.checkpoint import CheckpointStore
from vardoger.history.models import Conversation, Message

# ---------------------------------------------------------------------------
# initialize handshake
# ---------------------------------------------------------------------------


def test_initialize_response_reports_vardoger_version() -> None:
    """`initialize` must report vardoger's version, not the FastMCP SDK version."""
    # Regression test for https://github.com/dstrupl/vardoger/issues/13.
    opts = mcp_server.mcp._mcp_server.create_initialization_options()
    assert opts.server_name == "vardoger"
    assert opts.server_version == _VARDOGER_VERSION


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
    assert mcp_server._get_batches.cache_info().currsize == 1


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


# ---------------------------------------------------------------------------
# Regression tests for https://github.com/dstrupl/vardoger/issues/18:
# cwd-launched MCP server must NOT silently drop files in a non-project dir.
# ---------------------------------------------------------------------------


def test_vardoger_write_no_project_path_returns_user_rules_block(
    fake_home: Path,
    bare_cwd: Path,
) -> None:
    """Default delivery for Cursor is a User Rules copy-source file + inline block."""
    content = "# Personalization\n\n- stay concise\n"
    result = mcp_server.vardoger_write(content)

    assert "User Rules" in result
    assert "- stay concise" in result
    # No .cursor/rules landed in the cwd (the $HOME-equivalent case).
    assert not (bare_cwd / ".cursor" / "rules" / "vardoger.md").exists()

    # The convenience copy-source file lives under the fake ~/.vardoger/ so
    # users get a clickable path in the response instead of hunting through a
    # collapsed tool-call card.
    copy_path = fake_home / ".vardoger" / mcp_server._USER_RULES_COPY_FILENAME
    assert copy_path.is_file()
    assert "- stay concise" in copy_path.read_text(encoding="utf-8")
    # Response must name the tool explicitly and link to the copy-source path.
    assert "vardoger_write" in result
    assert str(copy_path) in result

    # Generation is still recorded so status/feedback stay consistent; the
    # sentinel (not the helper path) stays in ``output_path`` because the
    # helper file is NOT a Cursor-loaded location.
    store = CheckpointStore()
    record = store.get_generation("cursor")
    assert record is not None
    assert record.output_path == mcp_server._USER_RULES_OUTPUT_SENTINEL


def test_vardoger_write_user_rules_helper_file_is_overwritten_on_rerun(
    fake_home: Path,
    bare_cwd: Path,
) -> None:
    """Re-running vardoger_write overwrites the copy-source with the latest block."""
    mcp_server.vardoger_write("# Gen 1\n\n- first\n")
    mcp_server.vardoger_write("# Gen 2\n\n- second\n")

    copy_path = fake_home / ".vardoger" / mcp_server._USER_RULES_COPY_FILENAME
    text = copy_path.read_text(encoding="utf-8")
    assert "- second" in text
    assert "- first" not in text


def test_vardoger_write_user_rules_survives_copy_file_write_failure(
    fake_home: Path,
    bare_cwd: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the copy-source write fails, the response still inlines the block."""
    monkeypatch.setattr(mcp_server, "_write_user_rules_copy", lambda _content: None)
    result = mcp_server.vardoger_write("# Only\n\n- fallback\n")
    assert "could not save a copy-source file" in result
    assert "BEGIN vardoger personalization" in result
    assert "- fallback" in result


def test_vardoger_write_refuses_non_project_path(
    fake_home: Path,
    tmp_path: Path,
) -> None:
    """Explicit project_path that isn't a project → refuse, don't write."""
    bogus = tmp_path / "definitely-not-a-project"
    bogus.mkdir()

    result = mcp_server.vardoger_write(
        "# p\n\n- rule\n",
        project_path=str(bogus),
    )
    assert "refused to write" in result
    assert not (bogus / ".cursor" / "rules" / "vardoger.md").exists()

    # Nothing was recorded either.
    store = CheckpointStore()
    assert store.get_generation("cursor") is None


def test_vardoger_preview_no_project_path_shows_user_rules_block(
    fake_home: Path,
    bare_cwd: Path,
) -> None:
    result = mcp_server.vardoger_preview("# Preview\n\n- dry run\n")
    assert "no project_path given" in result
    assert "- dry run" in result
    # Preview must name the would-be copy-source path but NOT create it.
    would_be = fake_home / ".vardoger" / mcp_server._USER_RULES_COPY_FILENAME
    assert str(would_be) in result
    assert not would_be.exists()


def test_vardoger_feedback_reject_user_rules_generation(
    fake_home: Path,
    bare_cwd: Path,
) -> None:
    """Rejecting a User-Rules-only generation rewrites the copy-source to the previous block."""
    mcp_server.vardoger_write("# First\n\n- keep one\n")
    mcp_server.vardoger_write("# Second\n\n- replace with this\n")

    copy_path = fake_home / ".vardoger" / mcp_server._USER_RULES_COPY_FILENAME
    # Sanity: the latest-generation content is currently on disk.
    assert "- replace with this" in copy_path.read_text(encoding="utf-8")

    result = mcp_server.vardoger_feedback("reject")
    assert "User Rules" in result
    assert "- keep one" in result

    # After reject, copy-source reflects the PREVIOUS (re-offered) generation,
    # not the just-rejected one; and no project-scoped file appeared.
    restored = copy_path.read_text(encoding="utf-8")
    assert "- keep one" in restored
    assert "- replace with this" not in restored
    assert not (bare_cwd / ".cursor" / "rules" / "vardoger.md").exists()


def test_vardoger_feedback_reject_only_user_rules_generation(
    fake_home: Path,
    bare_cwd: Path,
) -> None:
    """Rejecting the only generation deletes the stale copy-source file."""
    mcp_server.vardoger_write("# Only\n\n- single\n")
    copy_path = fake_home / ".vardoger" / mcp_server._USER_RULES_COPY_FILENAME
    assert copy_path.is_file()

    result = mcp_server.vardoger_feedback("reject")
    assert "Settings → Rules → User Rules" in result
    assert str(copy_path) in result
    assert not copy_path.exists()


# ---------------------------------------------------------------------------
# vardoger_import: deliberate discovery of existing vardoger.md files.
# ---------------------------------------------------------------------------


def test_vardoger_import_returns_contents_for_found_paths(tmp_path: Path) -> None:
    proj_a = tmp_path / "a"
    proj_b = tmp_path / "b"
    proj_c = tmp_path / "c"
    for p in (proj_a, proj_b, proj_c):
        p.mkdir()

    (proj_a / ".cursor" / "rules").mkdir(parents=True)
    (proj_a / ".cursor" / "rules" / "vardoger.md").write_text("A rules\n", encoding="utf-8")
    (proj_c / ".cursor" / "rules").mkdir(parents=True)
    (proj_c / ".cursor" / "rules" / "vardoger.md").write_text("C rules\n", encoding="utf-8")

    payload = json.loads(mcp_server.vardoger_import([str(proj_a), str(proj_b), str(proj_c)]))

    paths = {entry["path"] for entry in payload}
    assert str(proj_a / ".cursor" / "rules" / "vardoger.md") in paths
    assert str(proj_c / ".cursor" / "rules" / "vardoger.md") in paths
    # proj_b has no vardoger.md — should be silently skipped, not errored.
    assert len(payload) == 2

    by_path = {entry["path"]: entry["content"] for entry in payload}
    assert by_path[str(proj_a / ".cursor" / "rules" / "vardoger.md")] == "A rules\n"


def test_vardoger_import_empty_list_returns_empty_json() -> None:
    assert mcp_server.vardoger_import([]) == "[]"


def test_vardoger_import_skips_invalid_entries(tmp_path: Path) -> None:
    """Non-strings, empty strings, and bogus paths should be ignored, not raise."""
    payload = json.loads(
        mcp_server.vardoger_import(
            ["", str(tmp_path / "nonexistent"), "   "]  # type: ignore[list-item]
        )
    )
    assert payload == []


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


# ---------------------------------------------------------------------------
# Platform routing (the fix for #12): the MCP surface must respect the
# platform parameter and the VARDOGER_MCP_PLATFORM env-var default.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("platform", list(mcp_server.PLATFORM_CHOICES))
def test_vardoger_status_honors_platform_argument(fake_home: Path, platform: str) -> None:
    payload = json.loads(mcp_server.vardoger_status(platform=platform))
    assert payload["platform"] == platform


def test_vardoger_status_rejects_unknown_platform(fake_home: Path) -> None:
    result = mcp_server.vardoger_status(platform="emacs")
    assert "unknown platform" in result
    assert "emacs" in result


def test_vardoger_status_env_var_default(
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(mcp_server._DEFAULT_PLATFORM_ENV, "cline")
    payload = json.loads(mcp_server.vardoger_status())
    assert payload["platform"] == "cline"


def test_vardoger_personalize_threads_platform_through_instructions(
    fake_home: Path,
) -> None:
    text = mcp_server.vardoger_personalize(platform="windsurf")
    assert "Windsurf" in text
    assert 'platform="windsurf"' in text


def test_vardoger_prepare_reads_selected_platform_history(
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    reset_mcp_cache: None,
) -> None:
    """Calling prepare with platform=cline must hit the cline reader,
    not the cursor reader. This is the concrete bug from #12."""
    cline_calls = {"count": 0}
    cursor_calls = {"count": 0}

    def _cursor(**_kwargs: object) -> list:
        cursor_calls["count"] += 1
        return []

    def _cline(**_kwargs: object) -> list:
        cline_calls["count"] += 1
        return [
            Conversation(
                messages=[Message(role="user", content="hi")],
                platform="cline",
                session_id="c1",
                source_path="c1.json",
            )
        ]

    monkeypatch.setattr("vardoger.mcp_server.read_cursor_history", _cursor)
    monkeypatch.setattr("vardoger.history.cline.read_cline_history", _cline)

    payload = json.loads(mcp_server.vardoger_prepare(platform="cline"))
    assert payload["platform"] == "cline"
    assert payload["total_conversations"] == 1
    assert cline_calls["count"] == 1
    assert cursor_calls["count"] == 0


def test_vardoger_write_routes_to_selected_platform_writer(
    fake_home: Path,
    project_cwd: Path,
) -> None:
    """Writing with platform=claude-code must land in Claude Code's rules
    directory, not .cursor/rules/vardoger.md."""
    result = mcp_server.vardoger_write(
        "# Personalization\n\n- stay focused\n",
        platform="claude-code",
        scope="project",
        project_path=str(project_cwd),
    )
    assert "wrote personalization" in result

    cursor_out = project_cwd / ".cursor" / "rules" / "vardoger.md"
    claude_out = project_cwd / ".claude" / "rules" / "vardoger.md"
    assert not cursor_out.is_file()
    assert claude_out.is_file()
    assert "stay focused" in claude_out.read_text()

    store = CheckpointStore()
    assert store.get_generation("claude_code") is not None
    assert store.get_generation("cursor") is None


def test_vardoger_write_cline_defaults_to_project_scope(
    fake_home: Path,
    project_cwd: Path,
) -> None:
    """Cline has no global scope; omitting scope must not explode."""
    result = mcp_server.vardoger_write(
        "# Personalization\n\n- keep things local\n",
        platform="cline",
        project_path=str(project_cwd),
    )
    assert "wrote personalization" in result
    clinerules = project_cwd / ".clinerules"
    assert clinerules.is_file() or (clinerules / "vardoger.md").is_file()


def test_vardoger_feedback_records_against_correct_state_key(fake_home: Path) -> None:
    """Feedback for claude-code must not leak into the cursor state slot."""
    mcp_server.vardoger_feedback("accept", platform="claude-code", reason="ok")

    store = CheckpointStore()
    claude_record = store.get_feedback("claude_code")
    cursor_record = store.get_feedback("cursor")
    assert any(e.kind == "accept" for e in claude_record.events)
    assert not any(e.kind == "accept" for e in cursor_record.events)


def test_vardoger_compare_honors_platform(
    fake_home: Path,
    patch_history_readers: object,
) -> None:
    payload = json.loads(mcp_server.vardoger_compare(platform="codex"))
    assert payload["platform"] == "codex"
