# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the OpenClaw history adapter."""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from vardoger.history.models import Conversation, Message
from vardoger.history.openclaw import (
    UnsupportedOpenClawHistoryError,
    _gateway_call,
    detect_openclaw_history_backend,
    discover_openclaw_files,
    read_openclaw_gateway_history,
    read_openclaw_history,
)
from vardoger.models import OpenClawGatewaySessionsParams


def _write_session(base: Path, subpath: str, lines: list[dict]) -> None:
    session_path = base / subpath
    session_path.parent.mkdir(parents=True, exist_ok=True)
    with open(session_path, "w") as f:
        for entry in lines:
            f.write(json.dumps(entry) + "\n")


def test_reads_basic_session():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "agent-1/sessions/telegram_user123.jsonl",
            [
                {
                    "id": "msg1",
                    "role": "user",
                    "content": "Hello there",
                    "timestamp": 1713200000.0,
                },
                {
                    "id": "msg2",
                    "parentId": "msg1",
                    "role": "assistant",
                    "content": "Hi! How can I help?",
                    "timestamp": 1713200001.0,
                },
            ],
        )

        convos = read_openclaw_history(openclaw_dir=base)
        assert len(convos) == 1
        assert convos[0].platform == "openclaw"
        assert convos[0].project == "agent-1"
        assert convos[0].session_id == "telegram_user123"
        assert convos[0].message_count == 2
        assert convos[0].messages[0].role == "user"
        assert convos[0].messages[0].content == "Hello there"
        assert convos[0].messages[1].role == "assistant"


def test_filters_system_and_tool_messages():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "agent-1/sessions/slack_chan.jsonl",
            [
                {"id": "s1", "role": "system", "content": "System prompt", "timestamp": 1.0},
                {"id": "u1", "role": "user", "content": "Help me", "timestamp": 2.0},
                {"id": "t1", "role": "tool", "content": "tool result", "timestamp": 3.0},
                {"id": "a1", "role": "assistant", "content": "Sure!", "timestamp": 4.0},
            ],
        )

        convos = read_openclaw_history(openclaw_dir=base)
        assert len(convos) == 1
        assert convos[0].message_count == 2
        roles = [m.role for m in convos[0].messages]
        assert roles == ["user", "assistant"]


def test_source_path_set():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "myagent/sessions/discord_abc.jsonl",
            [
                {"id": "m1", "role": "user", "content": "Hi", "timestamp": 1.0},
            ],
        )

        convos = read_openclaw_history(openclaw_dir=base)
        assert len(convos) == 1
        assert convos[0].source_path == "myagent/sessions/discord_abc.jsonl"


def test_discover_files():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "agent-a/sessions/telegram_1.jsonl",
            [{"id": "m1", "role": "user", "content": "Hi", "timestamp": 1.0}],
        )
        _write_session(
            base,
            "agent-b/sessions/slack_2.jsonl",
            [{"id": "m2", "role": "user", "content": "Hey", "timestamp": 2.0}],
        )

        files = discover_openclaw_files(openclaw_dir=base)
        assert len(files) == 2
        rel_paths = [f[1] for f in files]
        assert "agent-a/sessions/telegram_1.jsonl" in rel_paths
        assert "agent-b/sessions/slack_2.jsonl" in rel_paths


def test_detects_legacy_jsonl_backend(tmp_path: Path) -> None:
    _write_session(
        tmp_path,
        "agent-a/sessions/session.jsonl",
        [{"id": "m1", "role": "user", "content": "Hi", "timestamp": 1.0}],
    )

    assert detect_openclaw_history_backend(tmp_path) == "legacy-jsonl"


def test_detects_sqlite_and_refuses_stale_jsonl_fallback(tmp_path: Path) -> None:
    sqlite_store = tmp_path / "agent-a" / "agent" / "openclaw-agent.sqlite"
    sqlite_store.parent.mkdir(parents=True)
    sqlite_store.touch()
    _write_session(
        tmp_path,
        "agent-a/sessions/stale.jsonl",
        [{"id": "m1", "role": "user", "content": "Old", "timestamp": 1.0}],
    )

    assert detect_openclaw_history_backend(tmp_path) == "sqlite"
    with pytest.raises(
        UnsupportedOpenClawHistoryError,
        match="supported transcript accessor",
    ):
        read_openclaw_history(openclaw_dir=tmp_path)


def test_gateway_reader_uses_supported_read_methods_and_orders_pages() -> None:
    calls: list[tuple[str, dict]] = []

    def gateway_call(method: str, params) -> str:
        values = params.model_dump(exclude_none=True)
        calls.append((method, values))
        if method == "sessions.list":
            return json.dumps(
                {
                    "sessions": [
                        {"key": "agent:main:one", "sessionId": "s1", "agentId": "main"},
                        {"key": "agent:work:empty", "sessionId": "s2", "agentId": "work"},
                    ],
                    "total": 2,
                }
            )
        if values["sessionKey"] == "agent:work:empty":
            return json.dumps({"messages": [], "hasMore": False})
        if values["offset"] == 0:
            return json.dumps(
                {
                    "messages": [
                        {
                            "role": "assistant",
                            "content": [{"type": "text", "text": "Newer answer"}],
                            "__openclaw": {"id": "m2", "seq": 2},
                        },
                        {
                            "role": "assistant",
                            "content": "compacted",
                            "__openclaw": {"id": "c1", "kind": "compaction"},
                        },
                    ],
                    "hasMore": True,
                    "nextOffset": 10,
                }
            )
        return json.dumps(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "Older question",
                        "__openclaw": {"id": "m1", "seq": 1},
                    },
                    {"role": "tool", "content": "private tool payload"},
                ],
                "hasMore": False,
            }
        )

    conversations = read_openclaw_gateway_history(gateway_call)

    assert conversations == [
        Conversation(
            messages=[
                Message(role="user", content="Older question"),
                Message(role="assistant", content="Newer answer"),
            ],
            platform="openclaw",
            project="main",
            session_id="s1",
            source_path=None,
        )
    ]
    assert [method for method, _params in calls] == [
        "sessions.list",
        "chat.history",
        "chat.history",
        "chat.history",
    ]


def test_gateway_reader_rejects_broken_pagination() -> None:
    def gateway_call(method: str, _params) -> str:
        if method == "sessions.list":
            return '{"sessions":[{"key":"one"}]}'
        return '{"messages":[],"hasMore":true}'

    with pytest.raises(UnsupportedOpenClawHistoryError, match="without nextOffset"):
        read_openclaw_gateway_history(gateway_call)


def test_gateway_reader_rejects_repeated_offset() -> None:
    def gateway_call(method: str, _params) -> str:
        if method == "sessions.list":
            return '{"sessions":[{"key":"one"}]}'
        return '{"messages":[],"hasMore":true,"nextOffset":0}'

    with pytest.raises(UnsupportedOpenClawHistoryError, match="repeated a pagination offset"):
        read_openclaw_gateway_history(gateway_call)


def test_gateway_opt_in_requires_full_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VARDOGER_OPENCLAW_GATEWAY", "1")

    with pytest.raises(UnsupportedOpenClawHistoryError, match="Re-run with --full"):
        read_openclaw_history(file_filter=lambda _path, _rel: True)


def test_gateway_call_uses_local_cli_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[str] = []

    def fake_run(command, **_kwargs):
        observed.extend(command)
        return subprocess.CompletedProcess(command, 0, stdout='{"sessions":[]}', stderr="")

    monkeypatch.setattr("vardoger.history.openclaw.subprocess.run", fake_run)
    raw = _gateway_call("sessions.list", OpenClawGatewaySessionsParams(limit=1, offset=0))

    assert raw == '{"sessions":[]}'
    assert observed[:4] == ["openclaw", "gateway", "call", "sessions.list"]
    assert "--url" not in observed
    assert "--token" not in observed
    assert "--password" not in observed


def test_gateway_call_reports_missing_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(*_args, **_kwargs):
        raise FileNotFoundError

    monkeypatch.setattr("vardoger.history.openclaw.subprocess.run", missing)
    with pytest.raises(UnsupportedOpenClawHistoryError, match="not available on PATH"):
        _gateway_call("sessions.list", OpenClawGatewaySessionsParams(limit=1, offset=0))


def test_detects_absent_history_backend(tmp_path: Path) -> None:
    assert detect_openclaw_history_backend(tmp_path) == "none"


def test_file_filter_skips():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "agent-1/sessions/test.jsonl",
            [{"id": "m1", "role": "user", "content": "Hi", "timestamp": 1.0}],
        )

        convos = read_openclaw_history(
            openclaw_dir=base,
            file_filter=lambda _abs, _rel: False,
        )
        assert len(convos) == 0


def test_empty_session_skipped():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "agent-1/sessions/empty.jsonl",
            [
                {"id": "s1", "role": "system", "content": "System only", "timestamp": 1.0},
            ],
        )

        convos = read_openclaw_history(openclaw_dir=base)
        assert len(convos) == 0


def test_missing_directory():
    convos = read_openclaw_history(openclaw_dir=Path("/nonexistent"))
    assert convos == []


def test_metadata_ignored_gracefully():
    """Extra metadata fields are ignored by the Pydantic model."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "agent-1/sessions/rich.jsonl",
            [
                {
                    "id": "m1",
                    "role": "user",
                    "content": "Hello",
                    "timestamp": 1713200000.0,
                    "metadata": {
                        "userId": "u1",
                        "platform": "telegram",
                        "model": "gpt-4o",
                        "inputTokens": 10,
                        "outputTokens": 0,
                        "costUsd": 0.001,
                    },
                },
            ],
        )

        convos = read_openclaw_history(openclaw_dir=base)
        assert len(convos) == 1
        assert convos[0].messages[0].content == "Hello"
