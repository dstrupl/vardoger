# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
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
from collections.abc import Callable
from pathlib import Path

from vardoger.history.models import Conversation, Message, extract_text

logger = logging.getLogger(__name__)

DEFAULT_CLAUDE_DIR = Path.home() / ".claude" / "projects"

RELEVANT_TYPES = {"user", "assistant"}


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
    return sorted(p for p in project_dir.glob("*.jsonl") if p.is_file())


def discover_claude_code_files(
    claude_dir: Path | None = None,
) -> list[tuple[Path, str]]:
    """Return (absolute_path, relative_path) pairs for all session files."""
    base = claude_dir or DEFAULT_CLAUDE_DIR
    if not base.is_dir():
        return []

    results: list[tuple[Path, str]] = []
    for project_dir in sorted(base.iterdir()):
        if not project_dir.is_dir():
            continue

        session_files = _discover_sessions_from_index(project_dir)
        if not session_files:
            session_files = _discover_sessions_by_glob(project_dir)

        for jsonl_file in session_files:
            try:
                rel = str(jsonl_file.relative_to(base))
            except ValueError:
                rel = str(jsonl_file)
            results.append((jsonl_file, rel))
    return results


def _parse_session(path: Path, project_name: str, rel_path: str) -> Conversation | None:
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

                text = extract_text(msg_payload.get("content", []))
                if text.strip():
                    messages.append(Message(role=role, content=text))
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
        source_path=rel_path,
    )


def read_claude_code_history(
    claude_dir: Path | None = None,
    file_filter: Callable[[Path, str], bool] | None = None,
) -> list[Conversation]:
    """Discover and parse Claude Code session transcripts.

    If file_filter is provided, it is called with (abs_path, rel_path) for
    each discovered file. Only files where the filter returns True are parsed.
    """
    base = claude_dir or DEFAULT_CLAUDE_DIR
    all_files = discover_claude_code_files(claude_dir)

    conversations: list[Conversation] = []
    skipped = 0

    for abs_path, rel_path in all_files:
        if file_filter and not file_filter(abs_path, rel_path):
            skipped += 1
            continue

        project_name = (
            abs_path.relative_to(base).parts[0]
            if abs_path.is_relative_to(base)
            else abs_path.parent.name
        )
        conv = _parse_session(abs_path, project_name, rel_path)
        if conv is not None:
            conversations.append(conv)

    logger.info(
        "Claude Code: found %d conversations (%d skipped) across %s",
        len(conversations),
        skipped,
        base,
    )
    return conversations
