"""Command-line interface for vardoger.

Usage:
    vardoger analyze --platform {cursor|claude-code|codex} [--scope global|project] [--project PATH]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from vardoger.analyze import analyze
from vardoger.history.cursor import read_cursor_history
from vardoger.history.claude_code import read_claude_code_history
from vardoger.history.codex import read_codex_history
from vardoger.writers.cursor import write_cursor_rules
from vardoger.writers.claude_code import write_claude_code_rules
from vardoger.writers.codex import write_codex_rules

PLATFORM_READERS = {
    "cursor": read_cursor_history,
    "claude-code": read_claude_code_history,
    "codex": read_codex_history,
}


def _run_analyze(args: argparse.Namespace) -> None:
    platform = args.platform
    scope = args.scope
    project_path = Path(args.project) if args.project else None

    reader = PLATFORM_READERS[platform]
    conversations = reader()

    if not conversations:
        print(f"No conversation history found for {platform}.")
        return

    prompt_addition = analyze(conversations)

    if platform == "cursor":
        output = write_cursor_rules(prompt_addition, project_path=project_path)
    elif platform == "claude-code":
        output = write_claude_code_rules(
            prompt_addition, scope=scope, project_path=project_path
        )
    elif platform == "codex":
        output = write_codex_rules(
            prompt_addition, scope=scope, project_path=project_path
        )
    else:
        print(f"Unknown platform: {platform}", file=sys.stderr)
        sys.exit(1)

    print(f"vardoger: wrote personalization to {output}")
    print(f"  {len(conversations)} conversations, "
          f"{sum(c.message_count for c in conversations)} messages analyzed.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="vardoger",
        description="Personalize AI coding assistants from conversation history.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )

    subparsers = parser.add_subparsers(dest="command")

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Read history, analyze, and write a personalized prompt addition.",
    )
    analyze_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    analyze_parser.add_argument(
        "--platform",
        required=True,
        choices=["cursor", "claude-code", "codex"],
        help="Target platform.",
    )
    analyze_parser.add_argument(
        "--scope",
        choices=["global", "project"],
        default="global",
        help="Write scope: global (user-wide) or project-local. Default: global.",
    )
    analyze_parser.add_argument(
        "--project",
        default=None,
        help="Project directory path (used with --scope project).",
    )

    args = parser.parse_args(argv)

    verbose = getattr(args, "verbose", False)
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(name)s: %(message)s",
    )

    if args.command == "analyze":
        _run_analyze(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
