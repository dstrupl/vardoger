# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the shared extract_text helper."""

from vardoger.history.models import extract_text


def test_string_content():
    assert extract_text("plain text") == "plain text"


def test_list_with_text_blocks():
    content = [
        {"type": "text", "text": "Hello"},
        {"type": "text", "text": "World"},
    ]
    assert extract_text(content) == "Hello\nWorld"


def test_list_with_mixed_types():
    content = [
        {"type": "text", "text": "visible"},
        {"type": "tool_call", "name": "grep"},
    ]
    assert extract_text(content) == "visible"


def test_list_with_plain_strings():
    content = ["hello", "world"]
    assert extract_text(content) == "hello\nworld"


def test_custom_text_types():
    content = [
        {"type": "input_text", "text": "user input"},
        {"type": "output_text", "text": "model output"},
        {"type": "text", "text": "ignored"},
    ]
    result = extract_text(content, text_types=("input_text", "output_text"))
    assert "user input" in result
    assert "model output" in result
    assert "ignored" not in result


def test_empty_list():
    assert extract_text([]) == ""


def test_non_list_non_string():
    assert extract_text(42) == ""  # type: ignore[arg-type]
