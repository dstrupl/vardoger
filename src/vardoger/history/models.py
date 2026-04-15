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
