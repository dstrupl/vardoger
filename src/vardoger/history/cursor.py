"""Read Cursor agent transcript JSONL files.

Cursor stores agent transcripts at:
  ~/.cursor/projects/<workspace-slug>/agent-transcripts/<uuid>/<uuid>.jsonl

Each line is a JSON object with:
  - role: "user" or "assistant"
  - message.content: list of content blocks, each with "type" and "text"
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path

from vardoger.history.models import Conversation, Message

logger = logging.getLogger(__name__)

DEFAULT_CURSOR_DIR = Path.home() / ".cursor" / "projects"


def _extract_text(message: dict) -> str:
    """Pull plain text from a Cursor message payload."""
    content = message.get("content", [])
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return ""


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
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                role = entry.get("role")
                if role not in ("user", "assistant"):
                    continue

                msg_payload = entry.get("message", {})
                if isinstance(msg_payload, dict):
                    text = _extract_text(msg_payload)
                else:
                    text = str(msg_payload)

                if text.strip():
                    messages.append(Message(role=role, content=text))
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
