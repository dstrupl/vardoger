# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the Codex history adapter."""

import json
import tempfile
from pathlib import Path

from vardoger.history.codex import discover_codex_files, read_codex_history


def _write_rollout(base: Path, subpath: str, lines: list[dict]) -> None:
    rollout_path = base / subpath
    rollout_path.parent.mkdir(parents=True, exist_ok=True)
    with open(rollout_path, "w") as f:
        for entry in lines:
            f.write(json.dumps(entry) + "\n")


def test_reads_basic_rollout():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_rollout(
            base,
            "2026/04/15/rollout-test-abc.jsonl",
            [
                {"id": "abc", "timestamp": "2026-04-15T10:00:00Z"},
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "Hello"}],
                },
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "Hi"}],
                },
            ],
        )

        convos = read_codex_history(codex_dir=base)
        assert len(convos) == 1
        assert convos[0].platform == "codex"
        assert convos[0].session_id == "abc"
        assert convos[0].message_count == 2


def test_source_path_set():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_rollout(
            base,
            "2026/04/15/rollout-test-abc.jsonl",
            [
                {"id": "abc", "timestamp": "2026-04-15T10:00:00Z"},
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "Hello"}],
                },
            ],
        )

        convos = read_codex_history(codex_dir=base)
        assert len(convos) == 1
        assert convos[0].source_path == "2026/04/15/rollout-test-abc.jsonl"


def test_discover_files():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_rollout(
            base,
            "2026/04/15/rollout-a.jsonl",
            [
                {"id": "a", "timestamp": "2026-04-15T10:00:00Z"},
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "Hi"}],
                },
            ],
        )
        _write_rollout(
            base,
            "rollout-flat.jsonl",
            [
                {"id": "b", "timestamp": "2025-07-17T16:00:00Z"},
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "Hi"}],
                },
            ],
        )

        files = discover_codex_files(codex_dir=base)
        assert len(files) == 2
        rel_paths = [f[1] for f in files]
        assert "2026/04/15/rollout-a.jsonl" in rel_paths
        assert "rollout-flat.jsonl" in rel_paths


def test_file_filter_skips():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_rollout(
            base,
            "rollout-test.jsonl",
            [
                {"id": "x", "timestamp": "2026-04-15T10:00:00Z"},
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "Hi"}],
                },
            ],
        )

        convos = read_codex_history(
            codex_dir=base,
            file_filter=lambda _abs, _rel: False,
        )
        assert len(convos) == 0


def test_reads_flat_rollout():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_rollout(
            base,
            "rollout-flat-test.jsonl",
            [
                {"id": "flat-1", "timestamp": "2025-07-17T16:00:00Z"},
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "Test"}],
                },
            ],
        )

        convos = read_codex_history(codex_dir=base)
        assert len(convos) == 1


def test_missing_directory():
    convos = read_codex_history(codex_dir=Path("/nonexistent"))
    assert convos == []
