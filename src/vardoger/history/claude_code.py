"""Read Claude Code session JSONL files.

Claude Code stores session transcripts at:
  ~/.claude/projects/<encoded-path>/<session-uuid>.jsonl

Each line is a JSON object with:
  - type: "user", "assistant", "system", "file-history-snapshot", etc.
  - message.role: "user" or "assistant"
  - message.content: list of content blocks (type + text/thinking)
  - sessionId, timestamp, uuid, cwd, ...

A sessions-index.json in each project dir provides a manifest.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from vardoger.history.models import Conversation, Message

logger = logging.getLogger(__name__)

DEFAULT_CLAUDE_DIR = Path.home() / ".claude" / "projects"

RELEVANT_TYPES = {"user", "assistant"}


def _extract_text(message: dict) -> str:
    """Pull plain text from a Claude Code message payload."""
    content = message.get("content", [])
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return ""


def _parse_session(path: Path, project_name: str) -> Conversation | None:
    """Parse a single Claude Code session JSONL file."""
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

                entry_type = entry.get("type", "")
                if entry_type not in RELEVANT_TYPES:
                    continue

                msg_payload = entry.get("message", {})
                if not isinstance(msg_payload, dict):
                    continue

                role = msg_payload.get("role", entry_type)
                if role not in ("user", "assistant"):
                    continue

                text = _extract_text(msg_payload)
                if text.strip():
                    messages.append(
                        Message(role=role, content=text)
                    )
    except OSError as exc:
        logger.warning("Could not read %s: %s", path, exc)
        return None

    if not messages:
        return None

    return Conversation(
        messages=messages,
        platform="claude_code",
        project=project_name,
        session_id=session_id,
    )


def _discover_sessions_from_index(project_dir: Path) -> list[Path]:
    """Use sessions-index.json to find session files."""
    index_path = project_dir / "sessions-index.json"
    if not index_path.is_file():
        return []

    try:
        with open(index_path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

    paths = []
    for entry in data.get("entries", []):
        full_path = entry.get("fullPath")
        if full_path:
            p = Path(full_path)
            if p.is_file():
                paths.append(p)
            else:
                alt = project_dir / f"{entry.get('sessionId', '')}.jsonl"
                if alt.is_file():
                    paths.append(alt)
    return paths


def _discover_sessions_by_glob(project_dir: Path) -> list[Path]:
    """Fallback: find JSONL files directly in the project directory."""
    return sorted(
        p
        for p in project_dir.glob("*.jsonl")
        if p.is_file()
    )


def read_claude_code_history(
    claude_dir: Path | None = None,
) -> list[Conversation]:
    """Discover and parse all Claude Code session transcripts."""
    base = claude_dir or DEFAULT_CLAUDE_DIR
    if not base.is_dir():
        logger.info("Claude Code projects directory not found: %s", base)
        return []

    conversations: list[Conversation] = []

    for project_dir in sorted(base.iterdir()):
        if not project_dir.is_dir():
            continue

        session_files = _discover_sessions_from_index(project_dir)
        if not session_files:
            session_files = _discover_sessions_by_glob(project_dir)

        for jsonl_file in session_files:
            conv = _parse_session(jsonl_file, project_dir.name)
            if conv is not None:
                conversations.append(conv)

    logger.info(
        "Claude Code: found %d conversations across %s",
        len(conversations),
        base,
    )
    return conversations
