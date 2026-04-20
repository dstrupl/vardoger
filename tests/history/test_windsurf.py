# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the Windsurf history adapter."""

import json
import tempfile
from pathlib import Path

from vardoger.history.windsurf import discover_windsurf_files, read_windsurf_history


def _write_session(base: Path, subpath: str, lines: list[dict]) -> None:
    path = base / subpath
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for entry in lines:
            f.write(json.dumps(entry) + "\n")


def test_reads_string_content():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "workspaces/my-project/cascade.jsonl",
            [
                {"role": "user", "content": "Hello Windsurf", "timestamp": 1.0},
                {"role": "assistant", "content": "Hi there", "timestamp": 2.0},
            ],
        )

        convos = read_windsurf_history(windsurf_dir=base)
        assert len(convos) == 1
        assert convos[0].platform == "windsurf"
        assert convos[0].project == "my-project"
        assert convos[0].session_id == "cascade"
        assert convos[0].message_count == 2
        assert convos[0].messages[0].content == "Hello Windsurf"


def test_reads_content_blocks():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "workspaces/proj/chat.jsonl",
            [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "Block form"}],
                },
                {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "Reply one"},
                        {"type": "tool_use", "id": "t1", "name": "read"},
                    ],
                },
            ],
        )

        convos = read_windsurf_history(windsurf_dir=base)
        assert len(convos) == 1
        assert convos[0].messages[0].content == "Block form"
        assert convos[0].messages[1].content == "Reply one"


def test_skips_non_user_assistant_roles():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "ws/a.jsonl",
            [
                {"role": "system", "content": "be nice"},
                {"role": "tool", "content": "ran tool"},
                {"role": "user", "content": "Hi"},
            ],
        )

        convos = read_windsurf_history(windsurf_dir=base)
        assert len(convos) == 1
        assert [m.role for m in convos[0].messages] == ["user"]


def test_empty_content_skipped():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "ws/empty.jsonl",
            [
                {"role": "user", "content": ""},
                {"role": "assistant", "content": "   "},
            ],
        )

        assert read_windsurf_history(windsurf_dir=base) == []


def test_source_path_set():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "workspaces/p/chat.jsonl",
            [{"role": "user", "content": "Hi"}],
        )

        convos = read_windsurf_history(windsurf_dir=base)
        assert convos[0].source_path == "workspaces/p/chat.jsonl"


def test_discover_files_recursive():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(base, "a/one.jsonl", [{"role": "user", "content": "hi"}])
        _write_session(base, "b/c/two.jsonl", [{"role": "user", "content": "hi"}])

        files = discover_windsurf_files(windsurf_dir=base)
        rel_paths = sorted(f[1] for f in files)
        assert rel_paths == ["a/one.jsonl", "b/c/two.jsonl"]


def test_file_filter_skips():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(base, "ws/a.jsonl", [{"role": "user", "content": "hi"}])

        convos = read_windsurf_history(
            windsurf_dir=base,
            file_filter=lambda _abs, _rel: False,
        )
        assert convos == []


def test_missing_directory():
    assert read_windsurf_history(windsurf_dir=Path("/nonexistent")) == []


def test_metadata_ignored_gracefully():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_session(
            base,
            "ws/a.jsonl",
            [
                {
                    "role": "user",
                    "content": "Hello",
                    "timestamp": 1713200000.0,
                    "metadata": {"model": "cascade", "tokens": 10},
                    "turnId": "abc",
                },
            ],
        )

        convos = read_windsurf_history(windsurf_dir=base)
        assert len(convos) == 1
        assert convos[0].messages[0].content == "Hello"
