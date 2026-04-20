# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Read Cline task histories from VS Code globalStorage.

Cline (the saoudrizwan.claude-dev VS Code extension) keeps one directory per
task under VS Code's globalStorage. Within each task directory, the file
``api_conversation_history.json`` contains a JSON array of Anthropic-style
``{role, content}`` messages where ``content`` is either a plain string or a
list of content blocks.

Default layout on macOS::

    ~/Library/Application Support/Code/User/globalStorage/
        saoudrizwan.claude-dev/tasks/<task-id>/
        api_conversation_history.json

Linux / Windows map to analogous Code user directories; the ``cline_dir``
argument accepts any path containing a ``tasks/`` subtree with the same
layout so tests can drive the adapter against temp fixtures.
"""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Callable
from pathlib import Path

from pydantic import ValidationError

from vardoger.history.models import Conversation, Message, extract_text
from vardoger.models import ClineMessage

logger = logging.getLogger(__name__)


def _default_cline_dir() -> Path:
    """Return the platform-specific default Cline tasks directory."""
    home = Path.home()
    if sys.platform == "darwin":
        base = home / "Library" / "Application Support" / "Code" / "User" / "globalStorage"
    elif sys.platform.startswith("win"):
        appdata = Path.home() / "AppData" / "Roaming"
        base = appdata / "Code" / "User" / "globalStorage"
    else:
        base = home / ".config" / "Code" / "User" / "globalStorage"
    return base / "saoudrizwan.claude-dev" / "tasks"


DEFAULT_CLINE_DIR = _default_cline_dir()

RELEVANT_ROLES = {"user", "assistant"}


def discover_cline_files(
    cline_dir: Path | None = None,
) -> list[tuple[Path, str]]:
    """Return (absolute_path, relative_path) pairs for each task history JSON."""
    base = cline_dir or DEFAULT_CLINE_DIR
    if not base.is_dir():
        return []

    results: list[tuple[Path, str]] = []
    for task_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        history_path = task_dir / "api_conversation_history.json"
        if not history_path.is_file():
            continue
        rel = str(history_path.relative_to(base))
        results.append((history_path, rel))
    return results


def _parse_task(path: Path, task_id: str, rel_path: str) -> Conversation | None:
    """Parse one Cline api_conversation_history.json into a Conversation."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not read %s: %s", path, exc)
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("Invalid JSON in %s: %s", path, exc)
        return None
    if not isinstance(data, list):
        logger.warning("Expected JSON array in %s, got %s", path, type(data).__name__)
        return None

    messages: list[Message] = []
    for raw_entry in data:
        if not isinstance(raw_entry, dict):
            continue
        try:
            entry = ClineMessage.model_validate(raw_entry)
        except ValidationError:
            continue
        if entry.role not in RELEVANT_ROLES:
            continue
        text = extract_text(entry.content)
        if not text or not text.strip():
            continue
        messages.append(Message(role=entry.role, content=text))

    if not messages:
        return None

    return Conversation(
        messages=messages,
        platform="cline",
        project=None,
        session_id=task_id,
        source_path=rel_path,
    )


def read_cline_history(
    cline_dir: Path | None = None,
    file_filter: Callable[[Path, str], bool] | None = None,
) -> list[Conversation]:
    """Discover and parse every Cline task's api_conversation_history.json.

    If ``file_filter`` is provided, it is called with ``(abs_path, rel_path)``
    for each discovered file; only files where the filter returns True are
    parsed.
    """
    all_files = discover_cline_files(cline_dir)

    conversations: list[Conversation] = []
    skipped = 0

    for abs_path, rel_path in all_files:
        if file_filter and not file_filter(abs_path, rel_path):
            skipped += 1
            continue

        task_id = abs_path.parent.name
        conv = _parse_task(abs_path, task_id, rel_path)
        if conv is not None:
            conversations.append(conv)

    logger.info(
        "Cline: found %d conversations (%d skipped)",
        len(conversations),
        skipped,
    )
    return conversations
