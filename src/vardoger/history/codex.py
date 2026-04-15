"""Read OpenAI Codex session rollout JSONL files.

Codex stores session rollouts at:
  ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl
  ~/.codex/sessions/rollout-*.jsonl  (older format, flat)

Each file starts with a header line: {"id": "...", "timestamp": "..."}
Subsequent lines are messages: {"type": "message", "role": "user"|"assistant", "content": [...]}
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from vardoger.history.models import Conversation, Message

logger = logging.getLogger(__name__)

DEFAULT_CODEX_DIR = Path.home() / ".codex" / "sessions"


def _extract_text(content: list | str) -> str:
    """Pull plain text from Codex message content."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") in ("input_text", "output_text", "text"):
                    parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return ""


def _parse_rollout(path: Path) -> Conversation | None:
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
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if "id" in entry and "timestamp" in entry and "type" not in entry:
                    session_id = entry["id"]
                    continue

                if entry.get("type") != "message":
                    continue

                role = entry.get("role", "")
                if role not in ("user", "assistant"):
                    continue

                text = _extract_text(entry.get("content", []))
                if text.strip():
                    messages.append(Message(role=role, content=text))
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
    )


def read_codex_history(
    codex_dir: Path | None = None,
) -> list[Conversation]:
    """Discover and parse all Codex session rollout files."""
    base = codex_dir or DEFAULT_CODEX_DIR
    if not base.is_dir():
        logger.info("Codex sessions directory not found: %s", base)
        return []

    conversations: list[Conversation] = []

    for jsonl_file in sorted(base.rglob("rollout-*.jsonl")):
        conv = _parse_rollout(jsonl_file)
        if conv is not None:
            conversations.append(conv)

    logger.info(
        "Codex: found %d conversations across %s",
        len(conversations),
        base,
    )
    return conversations
