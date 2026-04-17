# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Prompt templates for AI analysis, loaded from .md files at runtime."""

from __future__ import annotations

from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    """Load a prompt template by name (without extension)."""
    path = _PROMPTS_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


def summarize_prompt() -> str:
    return load_prompt("summarize")


def synthesize_prompt() -> str:
    return load_prompt("synthesize")


def feedback_context_prompt(
    kept_rules: list[str],
    removed_rules: list[str],
    added_rules: list[str],
) -> str | None:
    """Return a rendered feedback-context prompt, or None if no feedback is recorded.

    Intended to be prepended to the synthesis prompt whenever the user has
    previously edited the generated personalization.
    """
    if not (kept_rules or removed_rules or added_rules):
        return None
    template = load_prompt("feedback_context")
    return template.format(
        kept_rules=_format_bullets(kept_rules),
        removed_rules=_format_bullets(removed_rules),
        added_rules=_format_bullets(added_rules),
    )


def _format_bullets(items: list[str]) -> str:
    if not items:
        return "- (none)"
    return "\n".join(f"- {item}" for item in items)
