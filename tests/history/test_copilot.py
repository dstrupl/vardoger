# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the GitHub Copilot CLI history adapter."""

import json
import tempfile
from pathlib import Path

import pytest

from vardoger.history.copilot import discover_copilot_files, read_copilot_history
from vardoger.history.models import Conversation, Message


def _write_session(base: Path, name: str, lines: list[dict]) -> None:
    path = base / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for entry in lines:
            f.write(json.dumps(entry) + "\n")


def test_reads_basic_session():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "45a14135-5849-47ab-bdd4-adf408b7e291.jsonl",
            [
                {
                    "type": "session.start",
                    "data": {"sessionId": "45a14135", "copilotVersion": "0.0.343"},
                    "id": "3321a6c1",
                    "timestamp": "2025-10-17T18:16:33.233Z",
                    "parentId": None,
                },
                {
                    "type": "session.info",
                    "data": {"infoType": "mcp", "message": "Connected"},
                    "id": "023e7afc",
                    "timestamp": "2025-10-17T18:16:34.868Z",
                    "parentId": "3321a6c1",
                },
                {
                    "type": "user.message",
                    "data": {"content": "Fix the color scheme.", "attachments": []},
                    "id": "8459357b",
                    "timestamp": "2025-10-17T18:17:25.278Z",
                    "parentId": "023e7afc",
                },
                {
                    "type": "assistant.message",
                    "data": {"messageId": "4ba6078a", "content": "Sure.", "toolRequests": []},
                    "id": "bf2e15be",
                    "timestamp": "2025-10-17T18:17:31.962Z",
                    "parentId": "8459357b",
                },
            ],
        )

        convos = read_copilot_history(copilot_dir=base)
        assert len(convos) == 1
        assert convos[0].platform == "copilot"
        assert convos[0].session_id == "45a14135-5849-47ab-bdd4-adf408b7e291"
        assert convos[0].message_count == 2
        roles = [m.role for m in convos[0].messages]
        assert roles == ["user", "assistant"]
        assert convos[0].messages[0].content == "Fix the color scheme."


def test_filters_session_metadata_and_tool_only_turns():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "session-a.jsonl",
            [
                {
                    "type": "session.start",
                    "data": {"sessionId": "s"},
                    "id": "x",
                    "timestamp": "2025-10-17T00:00:00Z",
                    "parentId": None,
                },
                {
                    "type": "assistant.message",
                    "data": {
                        "messageId": "m1",
                        "content": "",
                        "toolRequests": [{"toolCallId": "1", "name": "bash"}],
                    },
                    "id": "a",
                    "timestamp": "2025-10-17T00:00:01Z",
                    "parentId": "x",
                },
                {
                    "type": "user.message",
                    "data": {"content": "Hi", "attachments": []},
                    "id": "u",
                    "timestamp": "2025-10-17T00:00:02Z",
                    "parentId": "a",
                },
            ],
        )

        convos = read_copilot_history(copilot_dir=base)
        assert len(convos) == 1
        assert [m.role for m in convos[0].messages] == ["user"]


def test_source_path_set():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "abc.jsonl",
            [
                {
                    "type": "user.message",
                    "data": {"content": "Hi"},
                    "id": "u",
                    "timestamp": "2025-10-17T00:00:00Z",
                    "parentId": None,
                },
            ],
        )

        convos = read_copilot_history(copilot_dir=base)
        assert len(convos) == 1
        assert convos[0].source_path == "abc.jsonl"


def test_discover_files():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "a.jsonl",
            [{"type": "user.message", "data": {"content": "Hi"}, "id": "u", "timestamp": "t"}],
        )
        _write_session(
            base,
            "b.jsonl",
            [{"type": "user.message", "data": {"content": "Hey"}, "id": "u", "timestamp": "t"}],
        )

        files = discover_copilot_files(copilot_dir=base)
        rel_paths = [f[1] for f in files]
        assert sorted(rel_paths) == ["a.jsonl", "b.jsonl"]


def test_discovery_honors_copilot_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    configured_home = tmp_path / "custom-copilot"
    _write_session(
        configured_home / "session-state",
        "session/events.jsonl",
        [{"type": "user.message", "data": {"content": "Custom root"}}],
    )
    monkeypatch.setenv("COPILOT_HOME", str(configured_home))

    files = discover_copilot_files()

    assert files == [
        (
            configured_home / "session-state" / "session" / "events.jsonl",
            "session/events.jsonl",
        )
    ]


def test_reads_current_nested_session_layout():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "current-session/events.jsonl",
            [
                {
                    "type": "user.message",
                    "data": {"content": "Use the current layout."},
                    "id": "u",
                    "timestamp": "2026-09-27T00:00:00Z",
                },
                {
                    "type": "assistant.message",
                    "data": {"content": "Done."},
                    "id": "a",
                    "timestamp": "2026-09-27T00:00:01Z",
                },
            ],
        )

        assert read_copilot_history(copilot_dir=base) == [
            Conversation(
                messages=[
                    Message(role="user", content="Use the current layout."),
                    Message(role="assistant", content="Done."),
                ],
                platform="copilot",
                project=None,
                session_id="current-session",
                source_path="current-session/events.jsonl",
            )
        ]


def test_current_layout_wins_over_duplicate_legacy_session():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "same-session.jsonl",
            [{"type": "user.message", "data": {"content": "Legacy duplicate"}}],
        )
        _write_session(
            base,
            "same-session/events.jsonl",
            [{"type": "user.message", "data": {"content": "Current session"}}],
        )

        files = discover_copilot_files(copilot_dir=base)
        conversations = read_copilot_history(copilot_dir=base)

        assert [(path.relative_to(base).as_posix(), rel) for path, rel in files] == [
            ("same-session/events.jsonl", "same-session/events.jsonl")
        ]
        assert conversations == [
            Conversation(
                messages=[Message(role="user", content="Current session")],
                platform="copilot",
                project=None,
                session_id="same-session",
                source_path="same-session/events.jsonl",
            )
        ]


def test_file_filter_skips():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "a.jsonl",
            [{"type": "user.message", "data": {"content": "Hi"}, "id": "u", "timestamp": "t"}],
        )

        convos = read_copilot_history(
            copilot_dir=base,
            file_filter=lambda _abs, _rel: False,
        )
        assert convos == []


def test_empty_session_skipped():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "only-metadata.jsonl",
            [
                {
                    "type": "session.start",
                    "data": {},
                    "id": "x",
                    "timestamp": "t",
                    "parentId": None,
                },
            ],
        )

        convos = read_copilot_history(copilot_dir=base)
        assert convos == []


def test_missing_directory():
    assert read_copilot_history(copilot_dir=Path("/nonexistent")) == []
