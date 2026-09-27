# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Read user-enabled Devin CLI conversation exports in ATIF format.

Devin CLI documents ``--export [PATH]`` as its supported conversation-export
surface.  Vardoger intentionally does not inspect Devin Desktop's or Devin
CLI's private session storage.  Users opt in by exporting trajectories into
``~/.vardoger/imports/devin`` (or by passing a directory explicitly).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from vardoger.history.models import Conversation, Message
from vardoger.models import AtifContentPart, AtifTrajectory

logger = logging.getLogger(__name__)

DEFAULT_DEVIN_DIR = Path.home() / ".vardoger" / "imports" / "devin"

_ROLE_BY_SOURCE = {"user": "user", "agent": "assistant"}


def discover_devin_files(devin_dir: Path | None = None) -> list[tuple[Path, str]]:
    """Return ATIF JSON candidates from Vardoger's explicit Devin import dir."""
    base = devin_dir or DEFAULT_DEVIN_DIR
    if not base.is_dir():
        return []
    return [
        (path, str(path.relative_to(base)))
        for path in sorted(base.rglob("*.json"))
        if path.is_file()
    ]


def read_devin_history(
    devin_dir: Path | None = None,
    file_filter: Callable[[Path, str], bool] | None = None,
) -> list[Conversation]:
    """Parse supported, user-created Devin CLI ATIF exports.

    Files that are not valid ATIF trajectories are ignored.  System steps,
    non-text media parts, and copied-context steps are omitted because the
    personalization pipeline consumes only new user/assistant dialogue.
    """
    conversations: list[Conversation] = []
    skipped = 0
    for abs_path, rel_path in discover_devin_files(devin_dir):
        if file_filter and not file_filter(abs_path, rel_path):
            skipped += 1
            continue
        conversation = _parse_trajectory(abs_path, rel_path)
        if conversation is not None:
            conversations.append(conversation)

    logger.info("Devin: found %d conversations (%d skipped)", len(conversations), skipped)
    return conversations


def _parse_trajectory(path: Path, rel_path: str) -> Conversation | None:
    """Parse one ATIF trajectory without reading any referenced media files."""
    try:
        trajectory = AtifTrajectory.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        logger.debug("Ignoring non-ATIF Devin export %s: %s", path, exc)
        return None

    if not trajectory.schema_version.startswith("ATIF-v"):
        return None

    messages: list[Message] = []
    for step in trajectory.steps:
        role = _ROLE_BY_SOURCE.get(step.source)
        if role is None or step.is_copied_context:
            continue
        text = _extract_text(step.message)
        if not text.strip():
            continue
        messages.append(
            Message(role=role, content=text, timestamp=_parse_timestamp(step.timestamp))
        )

    if not messages:
        return None

    return Conversation(
        messages=messages,
        platform="devin",
        session_id=trajectory.session_id or trajectory.trajectory_id or path.stem,
        source_path=rel_path,
    )


def _extract_text(message: list[AtifContentPart] | str) -> str:
    """Return textual ATIF content while leaving referenced media untouched."""
    if isinstance(message, str):
        return message
    return "\n".join(part.text for part in message if part.type == "text" and part.text)


def _parse_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
