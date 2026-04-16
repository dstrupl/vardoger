# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the placeholder analysis step."""

from vardoger.analyze import analyze
from vardoger.history.models import Conversation, Message


def test_analyze_returns_statistics():
    convos = [
        Conversation(
            messages=[
                Message(role="user", content="Hello"),
                Message(role="assistant", content="Hi"),
            ],
            platform="cursor",
            project="proj-a",
        ),
        Conversation(
            messages=[
                Message(role="user", content="Help"),
            ],
            platform="cursor",
            project="proj-b",
        ),
    ]
    result = analyze(convos)
    assert "Conversations analyzed: 2" in result
    assert "Total messages: 3" in result
    assert "User messages: 2" in result
    assert "Assistant messages: 1" in result
    assert "Projects seen: 2" in result


def test_analyze_empty():
    result = analyze([])
    assert "Conversations analyzed: 0" in result
    assert "Projects seen" not in result


def test_analyze_no_projects():
    convos = [
        Conversation(messages=[Message(role="user", content="Hi")]),
    ]
    result = analyze(convos)
    assert "Projects seen" not in result
