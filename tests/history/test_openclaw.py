# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the OpenClaw history adapter."""

import json
import tempfile
from pathlib import Path

from vardoger.history.openclaw import discover_openclaw_files, read_openclaw_history


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
