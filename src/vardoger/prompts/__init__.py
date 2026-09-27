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


def synthesize_prompt(platform: str | None = None) -> str:
    """Return the synthesis prompt with host-specific memory boundaries.

    Claude Code and Codex both have host-managed memory. Their additions make
    Vardoger generate durable behavioral instructions instead of competing
    episodic context. Other hosts retain the shared synthesis prompt.
    """
    base = load_prompt("synthesize")
    guidance_by_platform = {
        "claude-code": "claude_code_native_memory_guidance",
        "codex": "codex_native_memory_guidance",
    }
    guidance_name = guidance_by_platform.get(platform or "")
    if guidance_name is None:
        return base
    return f"{load_prompt(guidance_name)}\n\n---\n\n{base}"


def analyze_skill_body(platform_slug: str, platform_name: str) -> str:
    """Return the analyze/SKILL.md body with platform placeholders filled in.

    The frontmatter is composed separately by each caller because it varies
    between marketplaces (e.g., ClawHub requires `version` and
    `metadata.openclaw.requires.bins`).
    """
    template = load_prompt("analyze_skill_body")
    body = template.replace("{PLATFORM_NAME}", platform_name).replace(
        "{PLATFORM_SLUG}", platform_slug
    )
    if platform_slug == "openclaw":
        compatibility = load_prompt("openclaw_history_compatibility")
        return f"{compatibility}\n\n{body}"
    if platform_slug == "devin":
        export_note = load_prompt("devin_history_export")
        return f"{export_note}\n\n{body}"
    return body


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
