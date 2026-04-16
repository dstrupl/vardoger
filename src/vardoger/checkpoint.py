# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Checkpoint store for incremental conversation processing.

Tracks which conversation files have already been analyzed by storing
a SHA-256 content hash per file. On subsequent runs, files whose hash
hasn't changed are skipped.

State is persisted to ~/.vardoger/state.json.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_STATE_DIR = Path.home() / ".vardoger"
STATE_VERSION = 1
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
        self._data: dict = self._load()

    def _load(self) -> dict:
        if not self._state_path.is_file():
            return {"version": STATE_VERSION, "checkpoints": {}}
        try:
            with open(self._state_path, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or data.get("version") != STATE_VERSION:
                logger.warning(
                    "Unrecognized checkpoint version in %s — starting fresh",
                    self._state_path,
                )
                return {"version": STATE_VERSION, "checkpoints": {}}
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "Could not read checkpoint state %s: %s — starting fresh",
                self._state_path,
                exc,
            )
            return {"version": STATE_VERSION, "checkpoints": {}}

    def save(self) -> None:
        """Persist current checkpoint state to disk."""
        self._state_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = self._state_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)
            f.write("\n")
        tmp_path.replace(self._state_path)

    def is_changed(self, platform: str, rel_path: str, abs_path: Path) -> bool:
        """Return True if the file is new or its content has changed."""
        current_hash = file_hash(abs_path)
        platform_ckpts = self._data.get("checkpoints", {}).get(platform, {})
        stored = platform_ckpts.get(rel_path)
        return not (stored and stored.get(HASH_ALGORITHM) == current_hash)

    def record(self, platform: str, rel_path: str, abs_path: Path) -> None:
        """Record a file as processed with its current content hash."""
        checkpoints = self._data.setdefault("checkpoints", {})
        platform_ckpts = checkpoints.setdefault(platform, {})
        platform_ckpts[rel_path] = {
            HASH_ALGORITHM: file_hash(abs_path),
            "processed_at": datetime.now(UTC).isoformat(),
        }

    def clear(self, platform: str | None = None) -> None:
        """Remove checkpoint data, optionally for a single platform."""
        if platform:
            self._data.get("checkpoints", {}).pop(platform, None)
        else:
            self._data["checkpoints"] = {}
