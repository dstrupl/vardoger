# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the Cline history adapter."""

import json
import tempfile
from pathlib import Path

from vardoger.history.cline import discover_cline_files, read_cline_history


def _write_task(base: Path, task_id: str, messages: list[dict]) -> Path:
    task_dir = base / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    history = task_dir / "api_conversation_history.json"
    history.write_text(json.dumps(messages))
    return history


def test_reads_basic_task():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_task(
            base,
            "1700000000000",
            [
                {"role": "user", "content": "Refactor this module"},
                {"role": "assistant", "content": "Will do"},
            ],
        )

        convos = read_cline_history(cline_dir=base)
        assert len(convos) == 1
        assert convos[0].platform == "cline"
        assert convos[0].session_id == "1700000000000"
        assert convos[0].message_count == 2
        assert convos[0].messages[0].content == "Refactor this module"


def test_reads_content_blocks():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_task(
            base,
            "task-blocks",
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Part 1"},
                        {"type": "text", "text": "Part 2"},
                    ],
                },
                {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "OK"},
                        {"type": "tool_use", "id": "t1", "name": "write"},
                    ],
                },
            ],
        )

        convos = read_cline_history(cline_dir=base)
        assert len(convos) == 1
        assert convos[0].messages[0].content == "Part 1\nPart 2"
        assert convos[0].messages[1].content == "OK"


def test_skips_system_role():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_task(
            base,
            "t",
            [
                {"role": "system", "content": "system prompt"},
                {"role": "user", "content": "Hi"},
            ],
        )

        convos = read_cline_history(cline_dir=base)
        assert len(convos) == 1
        assert [m.role for m in convos[0].messages] == ["user"]


def test_source_path_and_session_id():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_task(base, "abc-task", [{"role": "user", "content": "hi"}])
        convos = read_cline_history(cline_dir=base)
        assert convos[0].source_path == "abc-task/api_conversation_history.json"
        assert convos[0].session_id == "abc-task"


def test_discover_files():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_task(base, "one", [{"role": "user", "content": "hi"}])
        _write_task(base, "two", [{"role": "user", "content": "hey"}])
        (base / "not-a-task.txt").write_text("ignore me")

        files = discover_cline_files(cline_dir=base)
        rel_paths = sorted(f[1] for f in files)
        assert rel_paths == [
            "one/api_conversation_history.json",
            "two/api_conversation_history.json",
        ]


def test_file_filter_skips():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_task(base, "t", [{"role": "user", "content": "hi"}])

        convos = read_cline_history(
            cline_dir=base,
            file_filter=lambda _abs, _rel: False,
        )
        assert convos == []


def test_invalid_json_returns_empty():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        task_dir = base / "bad"
        task_dir.mkdir()
        (task_dir / "api_conversation_history.json").write_text("not json")
        assert read_cline_history(cline_dir=base) == []


def test_non_array_json_ignored():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        task_dir = base / "bad"
        task_dir.mkdir()
        (task_dir / "api_conversation_history.json").write_text('{"messages": []}')
        assert read_cline_history(cline_dir=base) == []


def test_missing_directory():
    assert read_cline_history(cline_dir=Path("/nonexistent")) == []


def test_empty_content_skipped():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_task(
            base,
            "empty",
            [
                {"role": "user", "content": ""},
                {"role": "assistant", "content": "   "},
            ],
        )
        assert read_cline_history(cline_dir=base) == []
