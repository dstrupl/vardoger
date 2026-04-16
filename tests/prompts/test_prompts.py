# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for prompt template loading."""

import pytest

from vardoger.prompts import load_prompt, summarize_prompt, synthesize_prompt


def test_summarize_prompt_loads():
    text = summarize_prompt()
    assert len(text) > 0
    assert isinstance(text, str)


def test_synthesize_prompt_loads():
    text = synthesize_prompt()
    assert len(text) > 0
    assert isinstance(text, str)


def test_load_nonexistent_prompt():
    with pytest.raises(FileNotFoundError):
        load_prompt("nonexistent_prompt_name")
