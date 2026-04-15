"""Command-line interface for vardoger.

Usage:
    vardoger analyze --platform {cursor|claude-code|codex} [--scope global|project] [--project PATH]
                     [--full] [--since DAYS]
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from vardoger.analyze import analyze
from vardoger.checkpoint import CheckpointStore
from vardoger.history.cursor import read_cursor_history
from vardoger.history.claude_code import read_claude_code_history
from vardoger.history.codex import read_codex_history
from vardoger.writers.cursor import write_cursor_rules
from vardoger.writers.claude_code import write_claude_code_rules
from vardoger.writers.codex import write_codex_rules

logger = logging.getLogger(__name__)

PLATFORM_KEY = {
    "cursor": "cursor",
    "claude-code": "claude_code",
    "codex": "codex",
}


def _make_file_filter(
    checkpoint: CheckpointStore | None,
    platform_key: str,
    since_seconds: float | None,
) -> tuple[callable, dict]:
    """Build a file_filter callback and a mutable stats dict."""
    stats = {"skipped_mtime": 0, "skipped_hash": 0, "accepted": 0}
    now = time.time()

    def _filter(abs_path: Path, rel_path: str) -> bool:
        if since_seconds is not None:
            try:
                mtime = abs_path.stat().st_mtime
            except OSError:
                return False
            if (now - mtime) > since_seconds:
                stats["skipped_mtime"] += 1
                return False

        if checkpoint and not checkpoint.is_changed(platform_key, rel_path, abs_path):
            stats["skipped_hash"] += 1
            return False

        stats["accepted"] += 1
        return True

    return _filter, stats


def _run_analyze(args: argparse.Namespace) -> None:
    platform = args.platform
    platform_key = PLATFORM_KEY[platform]
    scope = args.scope
    project_path = Path(args.project) if args.project else None
    full = args.full
    since_days = args.since

    checkpoint: CheckpointStore | None = None
    if not full:
        checkpoint = CheckpointStore()

    since_seconds: float | None = None
    if since_days is not None:
        since_seconds = since_days * 86400

    file_filter, stats = _make_file_filter(checkpoint, platform_key, since_seconds)
    filter_fn = None if full else file_filter

    reader_kwargs: dict = {}
    if filter_fn:
        reader_kwargs["file_filter"] = filter_fn

    if platform == "cursor":
        conversations = read_cursor_history(**reader_kwargs)
    elif platform == "claude-code":
        conversations = read_claude_code_history(**reader_kwargs)
    elif platform == "codex":
        conversations = read_codex_history(**reader_kwargs)
    else:
        print(f"Unknown platform: {platform}", file=sys.stderr)
        sys.exit(1)

    if not conversations:
        skipped_total = stats["skipped_mtime"] + stats["skipped_hash"]
        if skipped_total > 0:
            print(f"No new conversations for {platform} ({skipped_total} unchanged, skipped).")
        else:
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

    if checkpoint:
        for conv in conversations:
            if conv.source_path:
                reader_base = _get_reader_base(platform)
                abs_path = reader_base / conv.source_path
                if abs_path.is_file():
                    checkpoint.record(platform_key, conv.source_path, abs_path)
        checkpoint.save()

    total_msgs = sum(c.message_count for c in conversations)
    skipped_total = stats["skipped_mtime"] + stats["skipped_hash"]
    parts = [f"{len(conversations)} conversations, {total_msgs} messages analyzed"]
    if skipped_total > 0:
        parts.append(f"{skipped_total} unchanged, skipped")

    print(f"vardoger: wrote personalization to {output}")
    print(f"  {' | '.join(parts)}.")


def _get_reader_base(platform: str) -> Path:
    """Return the base directory for a platform's history files."""
    from vardoger.history.cursor import DEFAULT_CURSOR_DIR
    from vardoger.history.claude_code import DEFAULT_CLAUDE_DIR
    from vardoger.history.codex import DEFAULT_CODEX_DIR

    return {
        "cursor": DEFAULT_CURSOR_DIR,
        "claude-code": DEFAULT_CLAUDE_DIR,
        "codex": DEFAULT_CODEX_DIR,
    }[platform]


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
    analyze_parser.add_argument(
        "--full",
        action="store_true",
        default=False,
        help="Bypass checkpoint and reprocess all history.",
    )
    analyze_parser.add_argument(
        "--since",
        type=int,
        default=None,
        metavar="DAYS",
        help="Only process files modified in the last N days.",
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
