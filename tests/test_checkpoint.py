# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the checkpoint store."""

import json
import tempfile
from pathlib import Path

from vardoger.checkpoint import CheckpointStore, file_hash


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_file_hash_deterministic():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "a.txt"
        p.write_text("hello world")
        h1 = file_hash(p)
        h2 = file_hash(p)
        assert h1 == h2
        assert len(h1) == 64


def test_file_hash_differs_on_content_change():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "a.txt"
        p.write_text("version 1")
        h1 = file_hash(p)
        p.write_text("version 2")
        h2 = file_hash(p)
        assert h1 != h2


def test_new_file_is_changed():
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp) / "state"
        data_file = Path(tmp) / "data" / "test.jsonl"
        _write_file(data_file, '{"msg": "hello"}')

        store = CheckpointStore(state_dir=state_dir)
        assert store.is_changed("cursor", "proj/test.jsonl", data_file)


def test_recorded_file_is_not_changed():
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp) / "state"
        data_file = Path(tmp) / "data" / "test.jsonl"
        _write_file(data_file, '{"msg": "hello"}')

        store = CheckpointStore(state_dir=state_dir)
        store.record("cursor", "proj/test.jsonl", data_file)
        store.save()

        store2 = CheckpointStore(state_dir=state_dir)
        assert not store2.is_changed("cursor", "proj/test.jsonl", data_file)


def test_modified_file_is_changed():
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp) / "state"
        data_file = Path(tmp) / "data" / "test.jsonl"
        _write_file(data_file, '{"msg": "hello"}')

        store = CheckpointStore(state_dir=state_dir)
        store.record("cursor", "proj/test.jsonl", data_file)
        store.save()

        data_file.write_text('{"msg": "changed"}')

        store2 = CheckpointStore(state_dir=state_dir)
        assert store2.is_changed("cursor", "proj/test.jsonl", data_file)


def test_save_creates_state_dir():
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp) / "nested" / "state"
        store = CheckpointStore(state_dir=state_dir)
        store.save()
        assert (state_dir / "state.json").is_file()


def test_load_corrupt_state_starts_fresh():
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp) / "state"
        state_dir.mkdir()
        (state_dir / "state.json").write_text("not json at all")

        store = CheckpointStore(state_dir=state_dir)
        data_file = Path(tmp) / "data.jsonl"
        _write_file(data_file, "content")
        assert store.is_changed("cursor", "data.jsonl", data_file)


def test_load_wrong_version_starts_fresh():
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp) / "state"
        state_dir.mkdir()
        (state_dir / "state.json").write_text(
            json.dumps({"version": 999, "checkpoints": {"cursor": {"f.jsonl": {"sha256": "abc"}}}})
        )

        store = CheckpointStore(state_dir=state_dir)
        data_file = Path(tmp) / "f.jsonl"
        _write_file(data_file, "content")
        assert store.is_changed("cursor", "f.jsonl", data_file)


def test_clear_removes_platform_data():
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp) / "state"
        data_file = Path(tmp) / "test.jsonl"
        _write_file(data_file, "content")

        store = CheckpointStore(state_dir=state_dir)
        store.record("cursor", "test.jsonl", data_file)
        store.record("codex", "test.jsonl", data_file)
        store.clear(platform="cursor")

        assert store.is_changed("cursor", "test.jsonl", data_file)
        assert not store.is_changed("codex", "test.jsonl", data_file)


def test_clear_all():
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp) / "state"
        data_file = Path(tmp) / "test.jsonl"
        _write_file(data_file, "content")

        store = CheckpointStore(state_dir=state_dir)
        store.record("cursor", "test.jsonl", data_file)
        store.clear()

        assert store.is_changed("cursor", "test.jsonl", data_file)


def test_platforms_are_independent():
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp) / "state"
        data_file = Path(tmp) / "test.jsonl"
        _write_file(data_file, "content")

        store = CheckpointStore(state_dir=state_dir)
        store.record("cursor", "test.jsonl", data_file)

        assert not store.is_changed("cursor", "test.jsonl", data_file)
        assert store.is_changed("codex", "test.jsonl", data_file)


# -- v2 generation metadata --


def test_record_and_get_generation():
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp) / "state"
        store = CheckpointStore(state_dir=state_dir)

        assert store.get_generation("cursor") is None

        store.record_generation("cursor", conversations_analyzed=10, output_path="/out.md")
        store.save()

        store2 = CheckpointStore(state_dir=state_dir)
        gen = store2.get_generation("cursor")
        assert gen is not None
        assert gen["conversations_analyzed"] == 10
        assert gen["output_path"] == "/out.md"
        assert "generated_at" in gen


def test_v1_migration_preserves_checkpoints():
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp) / "state"
        state_dir.mkdir()

        v1_data = {
            "version": 1,
            "checkpoints": {
                "cursor": {
                    "proj/test.jsonl": {"sha256": "abc123", "processed_at": "2026-04-01T00:00:00"}
                }
            },
        }
        (state_dir / "state.json").write_text(json.dumps(v1_data))

        store = CheckpointStore(state_dir=state_dir)
        assert store._data["version"] == 2
        assert "generations" in store._data
        assert store._data["checkpoints"]["cursor"]["proj/test.jsonl"]["sha256"] == "abc123"


def test_v1_migration_adds_empty_generations():
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp) / "state"
        state_dir.mkdir()

        v1_data = {"version": 1, "checkpoints": {}}
        (state_dir / "state.json").write_text(json.dumps(v1_data))

        store = CheckpointStore(state_dir=state_dir)
        assert store._data["version"] == 2
        assert store._data["generations"] == {}


def test_generation_metadata_per_platform():
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp) / "state"
        store = CheckpointStore(state_dir=state_dir)

        store.record_generation("cursor", conversations_analyzed=5, output_path="/a")
        store.record_generation("claude_code", conversations_analyzed=10, output_path="/b")
        store.save()

        store2 = CheckpointStore(state_dir=state_dir)
        assert store2.get_generation("cursor")["conversations_analyzed"] == 5
        assert store2.get_generation("claude_code")["conversations_analyzed"] == 10
        assert store2.get_generation("codex") is None
