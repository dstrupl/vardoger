# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the Claude Code history adapter."""

import json
import tempfile
from pathlib import Path

from vardoger.history.claude_code import discover_claude_code_files, read_claude_code_history


def _write_session(base: Path, project_name: str, session_id: str, lines: list[dict]) -> None:
    project_dir = base / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = project_dir / f"{session_id}.jsonl"
    with open(jsonl_path, "w") as f:
        for entry in lines:
            f.write(json.dumps(entry) + "\n")


def test_reads_basic_session():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "-Users-test-proj",
            "abc-123",
            [
                {
                    "type": "user",
                    "message": {"role": "user", "content": [{"type": "text", "text": "Help me"}]},
                    "sessionId": "abc-123",
                },
                {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "Sure"}],
                    },
                    "sessionId": "abc-123",
                },
            ],
        )

        convos = read_claude_code_history(claude_dir=base)
        assert len(convos) == 1
        assert convos[0].platform == "claude_code"
        assert convos[0].message_count == 2


def test_source_path_set():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "-Users-test-proj",
            "abc-123",
            [
                {
                    "type": "user",
                    "message": {"role": "user", "content": "Hello"},
                    "sessionId": "abc-123",
                },
            ],
        )

        convos = read_claude_code_history(claude_dir=base)
        assert len(convos) == 1
        assert convos[0].source_path == "-Users-test-proj/abc-123.jsonl"


def test_discover_files():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "-proj-a",
            "s1",
            [
                {"type": "user", "message": {"role": "user", "content": "hi"}, "sessionId": "s1"},
            ],
        )
        _write_session(
            base,
            "-proj-b",
            "s2",
            [
                {"type": "user", "message": {"role": "user", "content": "hi"}, "sessionId": "s2"},
            ],
        )

        files = discover_claude_code_files(claude_dir=base)
        assert len(files) == 2
        rel_paths = [f[1] for f in files]
        assert "-proj-a/s1.jsonl" in rel_paths
        assert "-proj-b/s2.jsonl" in rel_paths


def test_file_filter_skips():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "-proj",
            "sess-1",
            [
                {
                    "type": "user",
                    "message": {"role": "user", "content": "Hello"},
                    "sessionId": "sess-1",
                },
            ],
        )

        convos = read_claude_code_history(
            claude_dir=base,
            file_filter=lambda _abs, _rel: False,
        )
        assert len(convos) == 0


def test_filters_non_message_types():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "-proj",
            "sess-1",
            [
                {"type": "file-history-snapshot", "messageId": "x", "snapshot": {}},
                {
                    "type": "user",
                    "message": {"role": "user", "content": "Hello"},
                    "sessionId": "sess-1",
                },
                {"type": "permission-mode", "mode": "auto"},
            ],
        )

        convos = read_claude_code_history(claude_dir=base)
        assert len(convos) == 1
        assert convos[0].message_count == 1


def test_missing_directory():
    convos = read_claude_code_history(claude_dir=Path("/nonexistent"))
    assert convos == []
