# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Read OpenAI Codex session rollout JSONL files.

Codex stores session rollouts at:
  ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl
  ~/.codex/sessions/rollout-*.jsonl  (older format, flat)

Each file starts with a header line: {"id": "...", "timestamp": "..."}
Subsequent lines are messages: {"type": "message", "role": "user"|"assistant", "content": [...]}
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from pydantic import ValidationError

from vardoger.history.models import Conversation, Message, extract_text
from vardoger.models import CodexEntry

logger = logging.getLogger(__name__)

DEFAULT_CODEX_DIR = Path.home() / ".codex" / "sessions"

CODEX_TEXT_TYPES = ("input_text", "output_text", "text")


def discover_codex_files(
    codex_dir: Path | None = None,
) -> list[tuple[Path, str]]:
    """Return (absolute_path, relative_path) pairs for all rollout files."""
    base = codex_dir or DEFAULT_CODEX_DIR
    if not base.is_dir():
        return []

    results: list[tuple[Path, str]] = []
    for jsonl_file in sorted(base.rglob("rollout-*.jsonl")):
        rel = str(jsonl_file.relative_to(base))
        results.append((jsonl_file, rel))
    return results


def _parse_rollout(path: Path, rel_path: str) -> Conversation | None:
    """Parse a single Codex rollout JSONL file."""
    messages: list[Message] = []
    session_id: str | None = None

    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = CodexEntry.model_validate_json(line)
                except ValidationError:
                    continue

                if entry.id and entry.timestamp and not entry.type:
                    session_id = entry.id
                    continue

                if entry.type != "message":
                    continue

                if entry.role not in ("user", "assistant"):
                    continue

                text = extract_text(entry.content, text_types=CODEX_TEXT_TYPES)
                if text.strip():
                    messages.append(Message(role=entry.role, content=text))
    except OSError as exc:
        logger.warning("Could not read %s: %s", path, exc)
        return None

    if not messages:
        return None

    return Conversation(
        messages=messages,
        platform="codex",
        project=None,
        session_id=session_id or path.stem,
        source_path=rel_path,
    )


def read_codex_history(
    codex_dir: Path | None = None,
    file_filter: Callable[[Path, str], bool] | None = None,
) -> list[Conversation]:
    """Discover and parse Codex session rollout files.

    If file_filter is provided, it is called with (abs_path, rel_path) for
    each discovered file. Only files where the filter returns True are parsed.
    """
    all_files = discover_codex_files(codex_dir)

    conversations: list[Conversation] = []
    skipped = 0

    for abs_path, rel_path in all_files:
        if file_filter and not file_filter(abs_path, rel_path):
            skipped += 1
            continue

        conv = _parse_rollout(abs_path, rel_path)
        if conv is not None:
            conversations.append(conv)

    logger.info(
        "Codex: found %d conversations (%d skipped)",
        len(conversations),
        skipped,
    )
    return conversations
