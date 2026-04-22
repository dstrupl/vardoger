# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Shared pytest fixtures for vardoger tests.

These fixtures are opt-in (no ``autouse``) so they only affect tests that
request them by parameter. Existing tests are unaffected.
"""

from __future__ import annotations

import io
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from vardoger.history.models import Conversation, Message


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect HOME, Path.home(), and the checkpoint state dir into ``tmp_path``.

    Most CLI/MCP entry points construct a ``CheckpointStore()`` without
    arguments, so the test-visible state file must live under ``tmp_path``
    rather than the developer's real ``~/.vardoger/``.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr("vardoger.checkpoint.DEFAULT_STATE_DIR", home / ".vardoger")
    return home


@pytest.fixture
def project_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Chdir into a fresh project dir so writers rooted at ``Path.cwd()`` stay isolated.

    The directory contains a ``.git`` stub so that writers which now enforce
    "must be inside a project" (see :mod:`vardoger.writers.cursor`) recognise
    it as a real project root.
    """
    project = tmp_path / "project"
    project.mkdir()
    (project / ".git").mkdir()
    monkeypatch.chdir(project)
    return project


@pytest.fixture
def bare_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Chdir into a directory with NO project markers.

    Used to exercise the ``$HOME``-launched MCP-server scenario (see
    https://github.com/dstrupl/vardoger/issues/18): callers that do not
    pass ``project_path`` must not be allowed to silently drop a rules
    file in a non-project directory.
    """
    bare = tmp_path / "nothome"
    bare.mkdir()
    monkeypatch.chdir(bare)
    return bare


def _build_conversations(count: int = 2) -> list[Conversation]:
    """Return a small list of conversations that exercise the heuristic metrics."""
    msgs = [
        Message(role="user", content="do the thing please"),
        Message(role="assistant", content="ok"),
        Message(role="user", content="no, no actually that's wrong, revert"),
        Message(role="assistant", content="reverted"),
    ]
    return [
        Conversation(
            messages=list(msgs),
            platform="cursor",
            session_id=f"session-{i}",
            source_path=f"fake-{i}.jsonl",
        )
        for i in range(count)
    ]


@pytest.fixture
def make_conversations() -> Callable[..., list[Conversation]]:
    return _build_conversations


@pytest.fixture
def patch_history_readers(
    monkeypatch: pytest.MonkeyPatch,
    make_conversations: Callable[..., list[Conversation]],
) -> list[Conversation]:
    """Route every platform's ``read_*_history`` call through a fixture list."""
    convs = make_conversations()

    def _return(**_kwargs: object) -> list[Conversation]:
        return convs

    def _return_for_platform(_platform: str) -> list[Conversation]:
        return convs

    monkeypatch.setattr("vardoger.cli.read_cursor_history", _return)
    monkeypatch.setattr("vardoger.cli.read_claude_code_history", _return)
    monkeypatch.setattr("vardoger.cli.read_codex_history", _return)
    monkeypatch.setattr("vardoger.history.openclaw.read_openclaw_history", _return)
    monkeypatch.setattr("vardoger.mcp_server.read_cursor_history", _return)
    monkeypatch.setattr("vardoger.quality._read_conversations_for", _return_for_platform)
    return convs


@pytest.fixture
def stdin_feeder(monkeypatch: pytest.MonkeyPatch) -> Callable[[str], None]:
    """Replace ``sys.stdin`` with a StringIO of the given text."""

    def _feed(text: str) -> None:
        monkeypatch.setattr(sys, "stdin", io.StringIO(text))

    return _feed


@pytest.fixture
def reset_mcp_cache() -> None:
    """Clear the ``_get_batches`` LRU cache so each test starts fresh."""
    import vardoger.mcp_server as mcp_mod

    mcp_mod._get_batches.cache_clear()
