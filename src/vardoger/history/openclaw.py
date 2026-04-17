# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Read OpenClaw session JSONL files.

OpenClaw stores session transcripts at:
  ~/.openclaw/agents/<agentId>/sessions/<channel>_<id>.jsonl

Each line is a JSON object with:
  - id: unique message identifier
  - parentId: parent message ID (tree structure)
  - role: "user", "assistant", "system", or "tool"
  - content: message text (plain string)
  - timestamp: Unix timestamp in seconds
  - metadata: userId, platform, model, token counts, etc.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from pydantic import ValidationError

from vardoger.history.models import Conversation, Message
from vardoger.models import OpenClawEntry

logger = logging.getLogger(__name__)

DEFAULT_OPENCLAW_DIR = Path.home() / ".openclaw" / "agents"


def discover_openclaw_files(
    openclaw_dir: Path | None = None,
) -> list[tuple[Path, str]]:
    """Return (absolute_path, relative_path) pairs for all session files."""
    base = openclaw_dir or DEFAULT_OPENCLAW_DIR
    if not base.is_dir():
        return []

    results: list[tuple[Path, str]] = []
    for agent_dir in sorted(base.iterdir()):
        if not agent_dir.is_dir():
            continue
        sessions_dir = agent_dir / "sessions"
        if not sessions_dir.is_dir():
            continue
        for jsonl_file in sorted(sessions_dir.glob("*.jsonl")):
            rel = str(jsonl_file.relative_to(base))
            results.append((jsonl_file, rel))
    return results


def _parse_session(path: Path, agent_id: str, rel_path: str) -> Conversation | None:
    """Parse a single OpenClaw session JSONL file into a Conversation."""
    messages: list[Message] = []
    session_id = path.stem

    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    entry = OpenClawEntry.model_validate_json(stripped)
                except ValidationError:
                    continue

                if entry.role not in ("user", "assistant"):
                    continue

                if entry.content.strip():
                    messages.append(Message(role=entry.role, content=entry.content))
    except OSError as exc:
        logger.warning("Could not read %s: %s", path, exc)
        return None

    if not messages:
        return None

    return Conversation(
        messages=messages,
        platform="openclaw",
        project=agent_id,
        session_id=session_id,
        source_path=rel_path,
    )


def read_openclaw_history(
    openclaw_dir: Path | None = None,
    file_filter: Callable[[Path, str], bool] | None = None,
) -> list[Conversation]:
    """Discover and parse OpenClaw session transcripts.

    If file_filter is provided, it is called with (abs_path, rel_path) for
    each discovered file. Only files where the filter returns True are parsed.
    """
    base = openclaw_dir or DEFAULT_OPENCLAW_DIR
    all_files = discover_openclaw_files(openclaw_dir)

    conversations: list[Conversation] = []
    skipped = 0

    for abs_path, rel_path in all_files:
        if file_filter and not file_filter(abs_path, rel_path):
            skipped += 1
            continue

        agent_id = abs_path.relative_to(base).parts[0]
        conv = _parse_session(abs_path, agent_id, rel_path)
        if conv is not None:
            conversations.append(conv)

    logger.info(
        "OpenClaw: found %d conversations (%d skipped) across %s",
        len(conversations),
        skipped,
        base,
    )
    return conversations
