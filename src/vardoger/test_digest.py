"""Tests for conversation batching and formatting."""

from vardoger.digest import batch_conversations, format_batch
from vardoger.history.models import Conversation, Message


def _make_conv(
    n_user: int = 2, n_assistant: int = 1, platform: str = "cursor", project: str = "proj"
) -> Conversation:
    msgs = []
    for i in range(n_user):
        msgs.append(Message(role="user", content=f"User message {i + 1}"))
    for i in range(n_assistant):
        msgs.append(Message(role="assistant", content=f"Assistant message {i + 1}"))
    return Conversation(messages=msgs, platform=platform, project=project)


def test_batch_empty():
    assert batch_conversations([]) == []


def test_batch_single():
    convos = [_make_conv() for _ in range(3)]
    batches = batch_conversations(convos, batch_size=10)
    assert len(batches) == 1
    assert len(batches[0]) == 3


def test_batch_exact_split():
    convos = [_make_conv() for _ in range(10)]
    batches = batch_conversations(convos, batch_size=5)
    assert len(batches) == 2
    assert len(batches[0]) == 5
    assert len(batches[1]) == 5


def test_batch_remainder():
    convos = [_make_conv() for _ in range(7)]
    batches = batch_conversations(convos, batch_size=3)
    assert len(batches) == 3
    assert len(batches[0]) == 3
    assert len(batches[1]) == 3
    assert len(batches[2]) == 1


def test_format_batch_includes_user_messages():
    conv = Conversation(
        messages=[
            Message(role="user", content="Help me with Python"),
            Message(role="assistant", content="Sure, here you go"),
            Message(role="user", content="Thanks, now add tests"),
        ],
        platform="cursor",
        project="my-app",
    )
    output = format_batch([conv], batch_number=1, total_batches=1)
    assert "Help me with Python" in output
    assert "Thanks, now add tests" in output
    assert "Sure, here you go" not in output


def test_format_batch_header():
    conv = _make_conv(platform="codex", project="api")
    output = format_batch([conv], batch_number=2, total_batches=5)
    assert "Batch 2 of 5" in output
    assert "codex" in output
    assert "api" in output


def test_format_batch_no_user_messages():
    conv = Conversation(
        messages=[Message(role="assistant", content="I can help")],
        platform="cursor",
    )
    output = format_batch([conv], batch_number=1, total_batches=1)
    assert "No user messages" in output


def test_format_batch_multiple_conversations():
    convos = [_make_conv(project=f"proj-{i}") for i in range(3)]
    output = format_batch(convos, batch_number=1, total_batches=1)
    assert "Conversation 1" in output
    assert "Conversation 2" in output
    assert "Conversation 3" in output
