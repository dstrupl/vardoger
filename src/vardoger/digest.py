"""Conversation batching and formatting for AI analysis.

Splits conversations into batches and formats them as markdown with full
user messages for the host AI model to summarize. Assistant messages are
excluded -- the user's words reveal their preferences and style.
"""

from __future__ import annotations

from vardoger.history.models import Conversation

DEFAULT_BATCH_SIZE = 10


def batch_conversations(
    conversations: list[Conversation],
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> list[list[Conversation]]:
    """Split conversations into batches of the given size."""
    if not conversations:
        return []
    return [conversations[i : i + batch_size] for i in range(0, len(conversations), batch_size)]


def format_batch(batch: list[Conversation], batch_number: int, total_batches: int) -> str:
    """Format a batch of conversations as markdown with full user messages."""
    lines: list[str] = [
        f"# Conversation Batch {batch_number} of {total_batches}",
        "",
    ]

    for i, conv in enumerate(batch, 1):
        header_parts = [f"## Conversation {i}"]
        if conv.platform:
            header_parts.append(f"(platform: {conv.platform}")
            if conv.project:
                header_parts[-1] += f", project: {conv.project}"
            header_parts[-1] += (
                f", {conv.message_count} messages, {conv.user_message_count} from user)"
            )
        lines.append(" ".join(header_parts))
        lines.append("")

        user_msgs = [m for m in conv.messages if m.role == "user"]
        if not user_msgs:
            lines.append("*No user messages in this conversation.*")
            lines.append("")
            continue

        for msg in user_msgs:
            lines.append(f"- {msg.content}")
            lines.append("")

    return "\n".join(lines)
