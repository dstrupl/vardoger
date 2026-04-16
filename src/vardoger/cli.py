"""Command-line interface for vardoger.

Usage:
    vardoger setup   <platform>
    vardoger analyze --platform X [--scope S] [--project P] [--full] [--since DAYS]
    vardoger prepare --platform X [--full] [--since DAYS] [--batch N] [--synthesize]
    vardoger write   --platform X [--scope S] [--project P]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections.abc import Callable
from pathlib import Path

from vardoger.analyze import analyze
from vardoger.checkpoint import CheckpointStore
from vardoger.digest import batch_conversations, format_batch
from vardoger.history.claude_code import read_claude_code_history
from vardoger.history.codex import read_codex_history
from vardoger.history.cursor import read_cursor_history
from vardoger.history.models import Conversation
from vardoger.prompts import summarize_prompt, synthesize_prompt
from vardoger.writers.claude_code import write_claude_code_rules
from vardoger.writers.codex import write_codex_rules
from vardoger.writers.cursor import write_cursor_rules

logger = logging.getLogger(__name__)

PLATFORM_KEY = {
    "cursor": "cursor",
    "claude-code": "claude_code",
    "codex": "codex",
}

PLATFORM_CHOICES = ["cursor", "claude-code", "codex"]


def _make_file_filter(
    checkpoint: CheckpointStore | None,
    platform_key: str,
    since_seconds: float | None,
) -> tuple[Callable[..., bool], dict[str, int]]:
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


def _read_conversations(
    platform: str, full: bool, since_days: int | None
) -> tuple[list[Conversation], CheckpointStore | None, dict[str, int]]:
    """Read conversations with checkpoint/mtime filtering.

    Returns (conversations, checkpoint, stats).
    """
    platform_key = PLATFORM_KEY[platform]

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

    return conversations, checkpoint, stats


def _write_platform(platform: str, content: str, scope: str, project_path: Path | None) -> Path:
    """Write content to the appropriate platform rules location."""
    if platform == "cursor":
        return write_cursor_rules(content, project_path=project_path)
    elif platform == "claude-code":
        return write_claude_code_rules(content, scope=scope, project_path=project_path)
    elif platform == "codex":
        return write_codex_rules(content, scope=scope, project_path=project_path)
    else:
        print(f"Unknown platform: {platform}", file=sys.stderr)
        sys.exit(1)


def _get_reader_base(platform: str) -> Path:
    """Return the base directory for a platform's history files."""
    from vardoger.history.claude_code import DEFAULT_CLAUDE_DIR
    from vardoger.history.codex import DEFAULT_CODEX_DIR
    from vardoger.history.cursor import DEFAULT_CURSOR_DIR

    return {
        "cursor": DEFAULT_CURSOR_DIR,
        "claude-code": DEFAULT_CLAUDE_DIR,
        "codex": DEFAULT_CODEX_DIR,
    }[platform]


def _save_checkpoint(
    checkpoint: CheckpointStore | None, conversations: list[Conversation], platform: str
) -> None:
    """Record processed conversations in the checkpoint store."""
    if not checkpoint:
        return
    platform_key = PLATFORM_KEY[platform]
    reader_base = _get_reader_base(platform)
    for conv in conversations:
        if conv.source_path:
            abs_path = reader_base / conv.source_path
            if abs_path.is_file():
                checkpoint.record(platform_key, conv.source_path, abs_path)
    checkpoint.save()


# -- setup --


def _run_setup(args: argparse.Namespace) -> None:
    from vardoger.setup import setup_claude_code, setup_codex, setup_cursor

    platform = args.platform
    if platform == "cursor":
        setup_cursor()
    elif platform == "claude-code":
        setup_claude_code()
    elif platform == "codex":
        setup_codex()


# -- analyze (legacy placeholder) --


def _run_analyze(args: argparse.Namespace) -> None:
    platform = args.platform
    scope = args.scope
    project_path = Path(args.project) if args.project else None

    conversations, checkpoint, stats = _read_conversations(platform, args.full, args.since)

    if not conversations:
        skipped_total = stats["skipped_mtime"] + stats["skipped_hash"]
        if skipped_total > 0:
            print(f"No new conversations for {platform} ({skipped_total} unchanged, skipped).")
        else:
            print(f"No conversation history found for {platform}.")
        return

    prompt_addition = analyze(conversations)
    output = _write_platform(platform, prompt_addition, scope, project_path)
    _save_checkpoint(checkpoint, conversations, platform)

    total_msgs = sum(c.message_count for c in conversations)
    skipped_total = stats["skipped_mtime"] + stats["skipped_hash"]
    parts = [f"{len(conversations)} conversations, {total_msgs} messages analyzed"]
    if skipped_total > 0:
        parts.append(f"{skipped_total} unchanged, skipped")

    print(f"vardoger: wrote personalization to {output}")
    print(f"  {' | '.join(parts)}.")


# -- prepare (AI pipeline stage 1) --


def _run_prepare(args: argparse.Namespace) -> None:
    platform = args.platform

    if args.synthesize:
        print(synthesize_prompt())
        return

    conversations, checkpoint, stats = _read_conversations(platform, args.full, args.since)

    if not conversations:
        skipped_total = stats["skipped_mtime"] + stats["skipped_hash"]
        if skipped_total > 0:
            print(
                f"No new conversations for {platform} ({skipped_total} unchanged, skipped).",
                file=sys.stderr,
            )
        else:
            print(f"No conversation history found for {platform}.", file=sys.stderr)
        print(json.dumps({"batches": 0, "total_conversations": 0}))
        return

    batches = batch_conversations(conversations)

    if args.batch is None:
        metadata = {
            "batches": len(batches),
            "total_conversations": len(conversations),
        }
        print(json.dumps(metadata))
        return

    batch_idx = args.batch - 1
    if batch_idx < 0 or batch_idx >= len(batches):
        print(f"Batch {args.batch} out of range (1-{len(batches)}).", file=sys.stderr)
        sys.exit(1)

    batch_text = format_batch(batches[batch_idx], args.batch, len(batches))
    prompt = summarize_prompt()
    print(prompt)
    print()
    print("---")
    print()
    print(batch_text)

    _save_checkpoint(checkpoint, conversations, platform)


# -- write (AI pipeline stage 2) --


def _run_write(args: argparse.Namespace) -> None:
    platform = args.platform
    scope = args.scope
    project_path = Path(args.project) if args.project else None

    content = sys.stdin.read()
    if not content.strip():
        print("No content received on stdin.", file=sys.stderr)
        sys.exit(1)

    output = _write_platform(platform, content, scope, project_path)
    print(f"vardoger: wrote personalization to {output}")


# -- CLI argument parsing --


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add arguments shared across subcommands."""
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    parser.add_argument(
        "--platform",
        required=True,
        choices=PLATFORM_CHOICES,
        help="Target platform.",
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="vardoger",
        description="Personalize AI coding assistants from conversation history.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )

    subparsers = parser.add_subparsers(dest="command")

    # setup
    setup_parser = subparsers.add_parser(
        "setup",
        help="Register vardoger with an AI coding assistant platform.",
    )
    setup_parser.add_argument(
        "platform",
        choices=PLATFORM_CHOICES,
        help="Platform to set up.",
    )

    # analyze (legacy placeholder)
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="(Legacy) Read history, run placeholder analysis, and write output.",
    )
    _add_common_args(analyze_parser)
    analyze_parser.add_argument(
        "--scope",
        choices=["global", "project"],
        default="global",
        help="Write scope: global (user-wide) or project-local.",
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

    # prepare
    prepare_parser = subparsers.add_parser(
        "prepare",
        help="Prepare conversation batches for AI analysis.",
    )
    _add_common_args(prepare_parser)
    prepare_parser.add_argument(
        "--full",
        action="store_true",
        default=False,
        help="Bypass checkpoint and reprocess all history.",
    )
    prepare_parser.add_argument(
        "--since",
        type=int,
        default=None,
        metavar="DAYS",
        help="Only process files modified in the last N days.",
    )
    prepare_parser.add_argument(
        "--batch",
        type=int,
        default=None,
        metavar="N",
        help="Return batch N (1-based). Without this, returns metadata.",
    )
    prepare_parser.add_argument(
        "--synthesize",
        action="store_true",
        default=False,
        help="Print the synthesize prompt instead of conversation data.",
    )

    # write
    write_parser = subparsers.add_parser(
        "write",
        help="Write personalization from stdin to the platform rules location.",
    )
    _add_common_args(write_parser)
    write_parser.add_argument(
        "--scope",
        choices=["global", "project"],
        default="global",
        help="Write scope: global (user-wide) or project-local.",
    )
    write_parser.add_argument(
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

    if args.command == "setup":
        _run_setup(args)
    elif args.command == "analyze":
        _run_analyze(args)
    elif args.command == "prepare":
        _run_prepare(args)
    elif args.command == "write":
        _run_write(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
