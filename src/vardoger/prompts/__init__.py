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
