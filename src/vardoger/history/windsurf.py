# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Read Windsurf (Codeium) cascade conversation history.

Windsurf persists workspace conversations under ``~/.codeium/windsurf/`` on
macOS and Linux (and the analogous ``%APPDATA%`` path on Windows). Schemas
have shifted across Codeium releases, so this adapter parses defensively:

* Any ``*.jsonl`` file under the windsurf directory is treated as a potential
  transcript.
* Each line is expected to be a JSON object carrying at minimum ``role`` and
  ``content``; ``content`` may be a plain string or a list of content blocks
  (Anthropic/OpenAI-style). Everything else is tolerated via Pydantic's
  ``extra="ignore"``.
* Lines without a recognisable user/assistant role or without any text are
  skipped, mirroring the OpenClaw adapter's behaviour.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from pydantic import ValidationError

from vardoger.history.models import Conversation, Message, extract_text
from vardoger.models import WindsurfEntry

logger = logging.getLogger(__name__)

DEFAULT_WINDSURF_DIR = Path.home() / ".codeium" / "windsurf"

RELEVANT_ROLES = {"user", "assistant"}


def discover_windsurf_files(
    windsurf_dir: Path | None = None,
) -> list[tuple[Path, str]]:
    """Return (absolute_path, relative_path) pairs for Windsurf transcripts.

    Walks ``windsurf_dir`` recursively for ``*.jsonl`` files. Returns an empty
    list when the directory is absent (e.g. Windsurf not installed).
    """
    base = windsurf_dir or DEFAULT_WINDSURF_DIR
    if not base.is_dir():
        return []

    results: list[tuple[Path, str]] = []
    for jsonl_file in sorted(base.rglob("*.jsonl")):
        if not jsonl_file.is_file():
            continue
        rel = str(jsonl_file.relative_to(base))
        results.append((jsonl_file, rel))
    return results


def _parse_session(path: Path, rel_path: str) -> Conversation | None:
    """Parse a single Windsurf JSONL transcript into a Conversation."""
    messages: list[Message] = []
    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    entry = WindsurfEntry.model_validate_json(stripped)
                except ValidationError:
                    continue

                if entry.role not in RELEVANT_ROLES:
                    continue

                text = extract_text(entry.content)
                if not text or not text.strip():
                    continue

                messages.append(Message(role=entry.role, content=text))
    except OSError as exc:
        logger.warning("Could not read %s: %s", path, exc)
        return None

    if not messages:
        return None

    workspace = path.parent.name or None
    return Conversation(
        messages=messages,
        platform="windsurf",
        project=workspace,
        session_id=path.stem,
        source_path=rel_path,
    )


def read_windsurf_history(
    windsurf_dir: Path | None = None,
    file_filter: Callable[[Path, str], bool] | None = None,
) -> list[Conversation]:
    """Discover and parse Windsurf cascade transcripts.

    If ``file_filter`` is provided, it is called with ``(abs_path, rel_path)``
    for each discovered file; only files where the filter returns True are
    parsed.
    """
    all_files = discover_windsurf_files(windsurf_dir)

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
        "Windsurf: found %d conversations (%d skipped)",
        len(conversations),
        skipped,
    )
    return conversations
