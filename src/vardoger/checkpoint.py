# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Checkpoint store for incremental conversation processing.

Tracks which conversation files have already been analyzed by storing
a SHA-256 content hash per file. On subsequent runs, files whose hash
hasn't changed are skipped.

Also records per-platform generation metadata (timestamp, conversation
count, output path) so that staleness detection can determine whether
the personalization needs refreshing.

State is persisted to ~/.vardoger/state.json.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from vardoger.models import CheckpointState, FileCheckpoint, GenerationRecord

logger = logging.getLogger(__name__)

DEFAULT_STATE_DIR = Path.home() / ".vardoger"
STATE_VERSION = 2
HASH_ALGORITHM = "sha256"
READ_CHUNK_SIZE = 65536


def file_hash(path: Path) -> str:
    """Compute the SHA-256 hex digest of a file's contents."""
    h = hashlib.new(HASH_ALGORITHM)
    with open(path, "rb") as f:
        while chunk := f.read(READ_CHUNK_SIZE):
            h.update(chunk)
    return h.hexdigest()


class CheckpointStore:
    """Manages per-platform checkpoint state for incremental processing."""

    def __init__(self, state_dir: Path | None = None) -> None:
        self._state_dir = state_dir or DEFAULT_STATE_DIR
        self._state_path = self._state_dir / "state.json"
        self._state: CheckpointState = self._load()

    @staticmethod
    def _migrate(data: dict) -> dict:
        """Migrate older state versions to the current schema."""
        version = data.get("version")
        if version == 1:
            data["version"] = STATE_VERSION
            data.setdefault("generations", {})
        return data

    def _load(self) -> CheckpointState:
        if not self._state_path.is_file():
            return CheckpointState()
        try:
            with open(self._state_path, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                logger.warning("Invalid checkpoint data in %s — starting fresh", self._state_path)
                return CheckpointState()
            version = data.get("version")
            if isinstance(version, int) and version < STATE_VERSION:
                logger.info("Migrating checkpoint state from v%d to v%d", version, STATE_VERSION)
                data = self._migrate(data)
            elif version != STATE_VERSION:
                logger.warning(
                    "Unrecognized checkpoint version %s in %s — starting fresh",
                    version,
                    self._state_path,
                )
                return CheckpointState()
            return CheckpointState.model_validate(data)
        except ValidationError as exc:
            logger.warning(
                "Invalid checkpoint structure in %s: %s — starting fresh",
                self._state_path,
                exc,
            )
            return CheckpointState()
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "Could not read checkpoint state %s: %s — starting fresh",
                self._state_path,
                exc,
            )
            return CheckpointState()

    def save(self) -> None:
        """Persist current checkpoint state to disk."""
        self._state_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = self._state_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(self._state.model_dump_json(indent=2))
            f.write("\n")
        tmp_path.replace(self._state_path)

    def is_changed(self, platform: str, rel_path: str, abs_path: Path) -> bool:
        """Return True if the file is new or its content has changed."""
        current_hash = file_hash(abs_path)
        platform_ckpts = self._state.checkpoints.get(platform, {})
        stored = platform_ckpts.get(rel_path)
        return not (stored and stored.sha256 == current_hash)

    def record(self, platform: str, rel_path: str, abs_path: Path) -> None:
        """Record a file as processed with its current content hash."""
        if platform not in self._state.checkpoints:
            self._state.checkpoints[platform] = {}
        self._state.checkpoints[platform][rel_path] = FileCheckpoint(
            sha256=file_hash(abs_path),
            processed_at=datetime.now(UTC).isoformat(),
        )

    def record_generation(
        self,
        platform: str,
        conversations_analyzed: int,
        output_path: str,
    ) -> None:
        """Record that a personalization was generated for a platform."""
        self._state.generations[platform] = GenerationRecord(
            generated_at=datetime.now(UTC).isoformat(),
            conversations_analyzed=conversations_analyzed,
            output_path=output_path,
        )

    def get_generation(self, platform: str) -> GenerationRecord | None:
        """Return generation metadata for a platform, or None if never generated."""
        return self._state.generations.get(platform)

    def get_checkpoint(self, platform: str, rel_path: str) -> FileCheckpoint | None:
        """Return checkpoint for a specific file, or None if not tracked."""
        return self._state.checkpoints.get(platform, {}).get(rel_path)

    def clear(self, platform: str | None = None) -> None:
        """Remove checkpoint data, optionally for a single platform."""
        if platform:
            self._state.checkpoints.pop(platform, None)
        else:
            self._state.checkpoints = {}
