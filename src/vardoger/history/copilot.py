# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Read GitHub Copilot CLI session-state JSONL files.

Current Copilot CLI releases store one event log per session at:
  <copilot-home>/session-state/<session-uuid>/events.jsonl

The Copilot home defaults to ``~/.copilot`` and is replaced completely when
``COPILOT_HOME`` is set.

Older releases stored the event log directly under ``session-state`` as
``<session-uuid>.jsonl``.  Both layouts are read so upgrading Copilot does not
make existing sessions disappear from vardoger.

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

from vardoger.config import CopilotConfig
from vardoger.history.models import Conversation, Message
from vardoger.models import CopilotEntry

logger = logging.getLogger(__name__)

_ROLE_BY_TYPE = {
    "user.message": "user",
    "assistant.message": "assistant",
}


def discover_copilot_files(
    copilot_dir: Path | None = None,
) -> list[tuple[Path, str]]:
    """Return ``(absolute_path, relative_path)`` pairs for Copilot event logs.

    The current nested layout is preferred over a legacy flat file with the
    same session ID.  Copilot may leave both representations present while a
    session is migrated, and analyzing both would double-count one session.
    """
    base = copilot_dir or CopilotConfig.from_env().session_state_dir
    if not base.is_dir():
        return []

    current_files = {
        path.parent.name: path for path in base.glob("*/events.jsonl") if path.is_file()
    }
    legacy_files = {
        path.stem: path
        for path in base.glob("*.jsonl")
        if path.is_file() and path.stem not in current_files
    }

    return sorted(
        (
            (path, str(path.relative_to(base)))
            for path in (*current_files.values(), *legacy_files.values())
        ),
        key=lambda item: item[1],
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
        session_id=_session_id(path),
        source_path=rel_path,
    )


def _session_id(path: Path) -> str:
    """Return the session ID for current nested or legacy flat event logs."""
    if path.name == "events.jsonl":
        return path.parent.name
    return path.stem
