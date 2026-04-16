# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the Cursor history adapter."""

import json
import tempfile
from pathlib import Path

from vardoger.history.cursor import discover_cursor_files, read_cursor_history


def _write_transcript(base: Path, slug: str, session_id: str, lines: list[dict]) -> None:
    transcript_dir = base / slug / "agent-transcripts" / session_id
    transcript_dir.mkdir(parents=True)
    jsonl_path = transcript_dir / f"{session_id}.jsonl"
    with open(jsonl_path, "w") as f:
        for entry in lines:
            f.write(json.dumps(entry) + "\n")


def test_reads_basic_transcript():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_transcript(
            base,
            "my-project",
            "sess-1",
            [
                {"role": "user", "message": {"content": [{"type": "text", "text": "Hello"}]}},
                {
                    "role": "assistant",
                    "message": {"content": [{"type": "text", "text": "Hi there"}]},
                },
            ],
        )

        convos = read_cursor_history(cursor_dir=base)
        assert len(convos) == 1
        assert convos[0].platform == "cursor"
        assert convos[0].message_count == 2
        assert convos[0].messages[0].role == "user"
        assert convos[0].messages[0].content == "Hello"


def test_source_path_set():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_transcript(
            base,
            "proj-a",
            "sess-1",
            [
                {"role": "user", "message": {"content": [{"type": "text", "text": "Hi"}]}},
            ],
        )

        convos = read_cursor_history(cursor_dir=base)
        assert len(convos) == 1
        assert convos[0].source_path == "proj-a/agent-transcripts/sess-1/sess-1.jsonl"


def test_discover_files():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_transcript(
            base,
            "proj-a",
            "s1",
            [
                {"role": "user", "message": {"content": "hi"}},
            ],
        )
        _write_transcript(
            base,
            "proj-b",
            "s2",
            [
                {"role": "user", "message": {"content": "hi"}},
            ],
        )

        files = discover_cursor_files(cursor_dir=base)
        assert len(files) == 2
        abs_paths = [f[0] for f in files]
        rel_paths = [f[1] for f in files]
        assert all(p.is_file() for p in abs_paths)
        assert "proj-a/agent-transcripts/s1/s1.jsonl" in rel_paths
        assert "proj-b/agent-transcripts/s2/s2.jsonl" in rel_paths


def test_file_filter_skips():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_transcript(
            base,
            "proj",
            "sess-1",
            [
                {"role": "user", "message": {"content": [{"type": "text", "text": "Hello"}]}},
            ],
        )
        _write_transcript(
            base,
            "proj",
            "sess-2",
            [
                {"role": "user", "message": {"content": [{"type": "text", "text": "World"}]}},
            ],
        )

        def reject_all(abs_path: Path, rel_path: str) -> bool:
            return False

        convos = read_cursor_history(cursor_dir=base, file_filter=reject_all)
        assert len(convos) == 0


def test_skips_empty_transcripts():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_transcript(
            base,
            "proj",
            "sess-empty",
            [
                {"role": "system", "message": {"content": "setup"}},
            ],
        )

        convos = read_cursor_history(cursor_dir=base)
        assert len(convos) == 0


def test_missing_directory():
    convos = read_cursor_history(cursor_dir=Path("/nonexistent"))
    assert convos == []
