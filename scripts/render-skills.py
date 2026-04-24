#!/usr/bin/env python3
# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Render the three per-platform analyze/SKILL.md files from the shared template.

The analyze skill body is identical across Claude Code, Codex, and OpenClaw
except for the platform name shown in prose and the `--platform` slug used in
example CLI invocations. OpenClaw additionally needs extra YAML frontmatter to
satisfy ClawHub's schema (see `openclaw/clawhub` docs/skill-format.md).

Usage:

    uv run scripts/render-skills.py            # regenerate files in place
    uv run scripts/render-skills.py --check    # fail if outputs would change

CI should run the `--check` form so drift between the template and the
per-platform SKILL.md files fails the build.
"""

from __future__ import annotations

import argparse
import difflib
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from vardoger.prompts import analyze_skill_body  # noqa: E402

TEMPLATE_PATH = REPO_ROOT / "src" / "vardoger" / "prompts" / "analyze_skill_body.md"


@dataclass(frozen=True)
class PluginTarget:
    """One rendering target: which SKILL.md file and how to fill it."""

    platform_slug: str
    platform_name: str
    output: Path
    frontmatter: tuple[str, ...] = field(default_factory=tuple)


_COMMON_FRONTMATTER = (
    "name: analyze",
    'description: "Use when the user asks to personalize their assistant, to use'
    " vardoger, or to analyze their {platform_name} conversation history. Runs the"
    ' vardoger CLI to read past conversations and generate tailored instructions."',
)


_TARGETS: tuple[PluginTarget, ...] = (
    PluginTarget(
        platform_slug="claude-code",
        platform_name="Claude Code",
        output=REPO_ROOT / "plugins" / "claude-code" / "skills" / "analyze" / "SKILL.md",
    ),
    PluginTarget(
        platform_slug="codex",
        platform_name="Codex",
        output=REPO_ROOT / "plugins" / "codex" / "skills" / "analyze" / "SKILL.md",
    ),
    PluginTarget(
        platform_slug="copilot",
        platform_name="GitHub Copilot CLI",
        output=REPO_ROOT / "plugins" / "copilot" / "skills" / "analyze" / "SKILL.md",
    ),
    PluginTarget(
        platform_slug="openclaw",
        platform_name="OpenClaw",
        output=REPO_ROOT / "plugins" / "openclaw" / "skills" / "analyze" / "SKILL.md",
        # ClawHub requires version + metadata.openclaw.requires.* (see
        # openclaw/clawhub docs/skill-format.md).
        frontmatter=(
            'version: "0.3.1"',
            "license: Apache-2.0",
            'homepage: "https://github.com/dstrupl/vardoger"',
            "metadata:",
            "  openclaw:",
            "    requires:",
            "      bins:",
            "        - vardoger",
        ),
    ),
)


def _render(target: PluginTarget) -> str:
    """Compose the frontmatter + body for a single plugin target."""
    body = analyze_skill_body(target.platform_slug, target.platform_name)
    common = tuple(
        line.replace("{platform_name}", target.platform_name) for line in _COMMON_FRONTMATTER
    )
    frontmatter_lines = ("---", *common, *target.frontmatter, "---", "")
    return "\n".join(frontmatter_lines) + body


def _diff(expected: str, actual: str, label: str) -> str:
    diff = difflib.unified_diff(
        actual.splitlines(keepends=True),
        expected.splitlines(keepends=True),
        fromfile=f"{label} (on disk)",
        tofile=f"{label} (expected)",
    )
    return "".join(diff)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail with a non-zero exit code if any SKILL.md would change.",
    )
    args = parser.parse_args(argv)

    if not TEMPLATE_PATH.is_file():
        sys.stderr.write(f"template not found: {TEMPLATE_PATH}\n")
        return 2

    drift = False
    for target in _TARGETS:
        rendered = _render(target)
        current = target.output.read_text(encoding="utf-8") if target.output.exists() else ""

        if rendered == current:
            continue

        if args.check:
            drift = True
            sys.stderr.write(
                f"drift: {target.output.relative_to(REPO_ROOT)} is out of sync with "
                f"{TEMPLATE_PATH.relative_to(REPO_ROOT)}\n"
            )
            sys.stderr.write(_diff(rendered, current, str(target.output.relative_to(REPO_ROOT))))
        else:
            target.output.parent.mkdir(parents=True, exist_ok=True)
            target.output.write_text(rendered, encoding="utf-8")
            print(f"wrote {target.output.relative_to(REPO_ROOT)}")

    if drift:
        sys.stderr.write("\nRun `uv run scripts/render-skills.py` to regenerate.\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
