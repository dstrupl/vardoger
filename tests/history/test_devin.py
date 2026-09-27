# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for supported Devin CLI ATIF exports."""

from __future__ import annotations

from pathlib import Path

from vardoger.history.devin import discover_devin_files, read_devin_history


def _write_atif(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """{
  "schema_version": "ATIF-v1.8",
  "session_id": "devin-session",
  "agent": {"name": "devin", "version": "3000.3"},
  "steps": [
    {"step_id": 1, "source": "system", "message": "system prompt"},
    {"step_id": 2, "source": "user", "message": "Keep the API small",
     "timestamp": "2026-09-27T10:00:00Z"},
    {"step_id": 3, "source": "agent", "message": [
      {"type": "text", "text": "Understood"},
      {"type": "image", "source": {"media_type": "image/png", "path": "images/a.png"}}
    ]},
    {"step_id": 4, "source": "user", "message": "copied", "is_copied_context": true}
  ]
}
""",
        encoding="utf-8",
    )


def test_reads_text_from_atif_export(tmp_path: Path) -> None:
    export = tmp_path / "nested" / "session.json"
    _write_atif(export)

    conversations = read_devin_history(devin_dir=tmp_path)

    assert len(conversations) == 1
    conversation = conversations[0]
    assert conversation.platform == "devin"
    assert conversation.session_id == "devin-session"
    assert conversation.source_path == "nested/session.json"
    assert [(message.role, message.content) for message in conversation.messages] == [
        ("user", "Keep the API small"),
        ("assistant", "Understood"),
    ]
    assert conversation.messages[0].timestamp is not None


def test_ignores_non_atif_and_empty_trajectories(tmp_path: Path) -> None:
    (tmp_path / "other.json").write_text('{"not": "atif"}', encoding="utf-8")
    (tmp_path / "empty.json").write_text(
        '{"schema_version":"ATIF-v1.8","agent":{"name":"devin","version":"1"},'
        '"steps":[{"step_id":1,"source":"system","message":"only system"}]}',
        encoding="utf-8",
    )

    assert read_devin_history(devin_dir=tmp_path) == []


def test_discovery_and_filter_are_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"
    _write_atif(first)
    _write_atif(second)

    assert discover_devin_files(tmp_path) == [(first, "a.json"), (second, "b.json")]
    seen: list[str] = []
    conversations = read_devin_history(
        devin_dir=tmp_path,
        file_filter=lambda _path, rel: seen.append(rel) is None and rel == "b.json",
    )

    assert seen == ["a.json", "b.json"]
    assert len(conversations) == 1
    assert conversations[0].source_path == "b.json"
