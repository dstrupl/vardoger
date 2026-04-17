# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Read Cursor agent transcript JSONL files.

Cursor stores agent transcripts at:
  ~/.cursor/projects/<workspace-slug>/agent-transcripts/<uuid>/<uuid>.jsonl

Each line is a JSON object with:
  - role: "user" or "assistant"
  - message.content: list of content blocks, each with "type" and "text"
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from pydantic import ValidationError

from vardoger.history.models import Conversation, Message, extract_text
from vardoger.models import ContentBlock, CursorEntry

logger = logging.getLogger(__name__)

DEFAULT_CURSOR_DIR = Path.home() / ".cursor" / "projects"


def discover_cursor_files(
    cursor_dir: Path | None = None,
) -> list[tuple[Path, str]]:
    """Return (absolute_path, relative_path) pairs for all transcript files."""
    base = cursor_dir or DEFAULT_CURSOR_DIR
    if not base.is_dir():
        return []

    results: list[tuple[Path, str]] = []
    for project_dir in sorted(base.iterdir()):
        if not project_dir.is_dir():
            continue
        transcripts_dir = project_dir / "agent-transcripts"
        if not transcripts_dir.is_dir():
            continue
        for jsonl_file in sorted(transcripts_dir.rglob("*.jsonl")):
            rel = str(jsonl_file.relative_to(base))
            results.append((jsonl_file, rel))
    return results


def _parse_transcript(path: Path, project_slug: str, rel_path: str) -> Conversation | None:
    """Parse a single agent transcript JSONL file into a Conversation."""
    messages: list[Message] = []
    session_id = path.stem

    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    entry = CursorEntry.model_validate_json(stripped)
                except ValidationError:
                    continue

                if entry.role not in ("user", "assistant"):
                    continue

                raw_content = entry.message.get("content", [])
                content: list[ContentBlock | str]
                if isinstance(raw_content, list):
                    content = raw_content
                elif isinstance(raw_content, str):
                    content = [raw_content]
                else:
                    continue

                text = extract_text(content)
                if text.strip():
                    messages.append(Message(role=entry.role, content=text))
    except OSError as exc:
        logger.warning("Could not read %s: %s", path, exc)
        return None

    if not messages:
        return None

    return Conversation(
        messages=messages,
        platform="cursor",
        project=project_slug,
        session_id=session_id,
        source_path=rel_path,
    )


def read_cursor_history(
    cursor_dir: Path | None = None,
    file_filter: Callable[[Path, str], bool] | None = None,
) -> list[Conversation]:
    """Discover and parse Cursor agent transcripts.

    If file_filter is provided, it is called with (abs_path, rel_path) for
    each discovered file. Only files where the filter returns True are parsed.
    """
    base = cursor_dir or DEFAULT_CURSOR_DIR
    all_files = discover_cursor_files(cursor_dir)

    conversations: list[Conversation] = []
    skipped = 0

    for abs_path, rel_path in all_files:
        if file_filter and not file_filter(abs_path, rel_path):
            skipped += 1
            continue

        project_slug = abs_path.relative_to(base).parts[0]
        conv = _parse_transcript(abs_path, project_slug, rel_path)
        if conv is not None:
            conversations.append(conv)

    logger.info(
        "Cursor: found %d conversations (%d skipped) across %s",
        len(conversations),
        skipped,
        base,
    )
    return conversations
