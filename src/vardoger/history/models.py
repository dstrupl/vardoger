# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Unified conversation data model shared across all platform adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    """A single user or assistant message."""

    role: str
    content: str
    timestamp: datetime | None = None


@dataclass
class Conversation:
    """A sequence of messages from one session."""

    messages: list[Message] = field(default_factory=list)
    platform: str = ""
    project: str | None = None
    session_id: str | None = None
    source_path: str | None = None

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def user_message_count(self) -> int:
        return sum(1 for m in self.messages if m.role == "user")

    @property
    def assistant_message_count(self) -> int:
        return sum(1 for m in self.messages if m.role == "assistant")


def extract_text(content: list | str, text_types: tuple[str, ...] = ("text",)) -> str:
    """Pull plain text from a message content payload.

    Works across Cursor, Claude Code, and Codex formats. Each platform uses
    slightly different content block type names; callers pass the relevant
    type strings via ``text_types``.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") in text_types:
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return ""
