# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Read GitHub Copilot CLI session-state JSONL files.

Copilot stores one JSONL file per session at:
  ~/.copilot/session-state/<session-uuid>.jsonl

Each line is a JSON object of the form::

    {
      "type": "user.message" | "assistant.message" | "session.start" | ...,
      "id": "...",
      "timestamp": "2025-10-17T18:17:25.278Z",
      "parentId": "..." | null,
      "data": {"content": "...", ...}
    }

Only ``user.message`` and ``assistant.message`` carry chat text; everything
else (session lifecycle, auth info, tool-request-only assistant turns with
empty ``content``) is skipped.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from pydantic import ValidationError

from vardoger.history.models import Conversation, Message
from vardoger.models import CopilotEntry

logger = logging.getLogger(__name__)

DEFAULT_COPILOT_DIR = Path.home() / ".copilot" / "session-state"

_ROLE_BY_TYPE = {
    "user.message": "user",
    "assistant.message": "assistant",
}


def discover_copilot_files(
    copilot_dir: Path | None = None,
) -> list[tuple[Path, str]]:
    """Return (absolute_path, relative_path) pairs for every session JSONL."""
    base = copilot_dir or DEFAULT_COPILOT_DIR
    if not base.is_dir():
        return []

    results: list[tuple[Path, str]] = []
    for jsonl_file in sorted(base.glob("*.jsonl")):
        rel = str(jsonl_file.relative_to(base))
        results.append((jsonl_file, rel))
    return results


def _parse_session(path: Path, rel_path: str) -> Conversation | None:
    """Parse a single Copilot session JSONL file into a Conversation."""
    messages: list[Message] = []
    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    entry = CopilotEntry.model_validate_json(stripped)
                except ValidationError:
                    continue

                role = _ROLE_BY_TYPE.get(entry.type)
                if role is None:
                    continue

                text = entry.data.content
                if not text or not text.strip():
                    continue

                messages.append(Message(role=role, content=text))
    except OSError as exc:
        logger.warning("Could not read %s: %s", path, exc)
        return None

    if not messages:
        return None

    return Conversation(
        messages=messages,
        platform="copilot",
        project=None,
        session_id=path.stem,
        source_path=rel_path,
    )


def read_copilot_history(
    copilot_dir: Path | None = None,
    file_filter: Callable[[Path, str], bool] | None = None,
) -> list[Conversation]:
    """Discover and parse Copilot CLI session transcripts.

    If ``file_filter`` is provided, it is called with ``(abs_path, rel_path)``
    for each discovered file. Only files where the filter returns True are
    parsed.
    """
    all_files = discover_copilot_files(copilot_dir)

    conversations: list[Conversation] = []
    skipped = 0

    for abs_path, rel_path in all_files:
        if file_filter and not file_filter(abs_path, rel_path):
            skipped += 1
            continue

        conv = _parse_session(abs_path, rel_path)
        if conv is not None:
            conversations.append(conv)

    logger.info(
        "Copilot: found %d conversations (%d skipped)",
        len(conversations),
        skipped,
    )
    return conversations
