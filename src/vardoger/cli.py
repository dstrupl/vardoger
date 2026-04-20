# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Command-line interface for vardoger.

Usage:
    vardoger setup   <platform>
    vardoger status  [--platform X] [--json]
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
from vardoger.checkpoint import CheckpointStore, content_hash
from vardoger.digest import batch_conversations, format_batch
from vardoger.feedback import detect_edits
from vardoger.history.claude_code import read_claude_code_history
from vardoger.history.codex import read_codex_history
from vardoger.history.cursor import read_cursor_history
from vardoger.history.models import Conversation
from vardoger.models import FeedbackEvent, HookOutput, SessionStartContext
from vardoger.personalization import annotate_tentative, parse_personalization
from vardoger.prompts import feedback_context_prompt, summarize_prompt, synthesize_prompt
from vardoger.quality import compare as compare_quality
from vardoger.staleness import check_staleness
from vardoger.writers.claude_code import clear_claude_code_rules, write_claude_code_rules
from vardoger.writers.codex import clear_codex_rules, write_codex_rules
from vardoger.writers.cursor import clear_cursor_rules, write_cursor_rules
from vardoger.writers.openclaw import clear_openclaw_rules, write_openclaw_rules

logger = logging.getLogger(__name__)

PLATFORM_KEY = {
    "cursor": "cursor",
    "claude-code": "claude_code",
    "codex": "codex",
    "openclaw": "openclaw",
}

PLATFORM_CHOICES = ["cursor", "claude-code", "codex", "openclaw"]


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
    elif platform == "openclaw":
        from vardoger.history.openclaw import read_openclaw_history

        conversations = read_openclaw_history(**reader_kwargs)
    else:
        print(f"Unknown platform: {platform}", file=sys.stderr)
        sys.exit(1)

    return conversations, checkpoint, stats


def _write_platform(platform: str, content: str, scope: str, project_path: Path | None) -> Path:
    """Write content to the appropriate platform rules location."""
    if platform == "cursor":
        return write_cursor_rules(content, project_path=project_path)
    if platform == "claude-code":
        return write_claude_code_rules(content, scope=scope, project_path=project_path)
    if platform == "codex":
        return write_codex_rules(content, scope=scope, project_path=project_path)
    if platform == "openclaw":
        return write_openclaw_rules(content, scope=scope, project_path=project_path)
    print(f"Unknown platform: {platform}", file=sys.stderr)
    sys.exit(1)


def _clear_platform(platform: str, scope: str, project_path: Path | None) -> bool:
    """Remove the vardoger-managed rules for a platform. Returns True if removed."""
    if platform == "cursor":
        return clear_cursor_rules(project_path=project_path)
    if platform == "claude-code":
        return clear_claude_code_rules(scope=scope, project_path=project_path)
    if platform == "codex":
        return clear_codex_rules(scope=scope, project_path=project_path)
    if platform == "openclaw":
        return clear_openclaw_rules(scope=scope, project_path=project_path)
    print(f"Unknown platform: {platform}", file=sys.stderr)
    sys.exit(1)


def _get_reader_base(platform: str) -> Path:
    """Return the base directory for a platform's history files."""
    from vardoger.history.claude_code import DEFAULT_CLAUDE_DIR
    from vardoger.history.codex import DEFAULT_CODEX_DIR
    from vardoger.history.cursor import DEFAULT_CURSOR_DIR
    from vardoger.history.openclaw import DEFAULT_OPENCLAW_DIR

    return {
        "cursor": DEFAULT_CURSOR_DIR,
        "claude-code": DEFAULT_CLAUDE_DIR,
        "codex": DEFAULT_CODEX_DIR,
        "openclaw": DEFAULT_OPENCLAW_DIR,
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
    from vardoger.setup import setup_claude_code, setup_codex, setup_cursor, setup_openclaw

    platform = args.platform
    if platform == "cursor":
        setup_cursor()
    elif platform == "claude-code":
        setup_claude_code()
    elif platform == "codex":
        setup_codex()
    elif platform == "openclaw":
        setup_openclaw()


# -- status --


def _run_status(args: argparse.Namespace) -> None:
    platforms = [args.platform] if args.platform else PLATFORM_CHOICES
    use_json = getattr(args, "json", False)

    reports = []
    for platform in platforms:
        report = check_staleness(platform)
        reports.append(report)

    if use_json:
        import json as _json

        print(_json.dumps([r.model_dump() for r in reports], indent=2))
    else:
        for r in reports:
            label = f"{r.platform}:"
            print(f"{label:<14} {r.reason}")


# -- hook-session-start (hidden, invoked by plugin hooks) --


def _run_hook_session_start(args: argparse.Namespace) -> None:
    """Output a Claude Code SessionStart hook JSON response if stale."""
    platform = args.platform
    report = check_staleness(platform)
    if not report.is_stale:
        return

    hook = HookOutput(
        hookSpecificOutput=SessionStartContext(
            additionalContext=(
                f"vardoger personalization is {report.reason}. "
                "Consider running the vardoger analyze skill to refresh."
            ),
        )
    )
    print(hook.model_dump_json())


# -- analyze (legacy placeholder) --


def _check_for_edits(platform: str, scope: str, project_path: Path | None) -> None:
    """Record any user edits to the current rules file before we generate new ones."""
    store = CheckpointStore()
    event = detect_edits(platform, store, scope=scope, project_path=project_path)
    if event is not None:
        store.save()


def _run_analyze(args: argparse.Namespace) -> None:
    platform = args.platform
    scope = args.scope
    project_path = Path(args.project) if args.project else None

    _check_for_edits(platform, scope, project_path)

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

    store = checkpoint or CheckpointStore()
    store.record_generation(
        PLATFORM_KEY[platform],
        conversations_analyzed=len(conversations),
        output_path=str(output),
        content=prompt_addition,
        output_hash=content_hash(prompt_addition),
    )
    store.save()

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
        store = CheckpointStore()
        record = store.get_feedback(PLATFORM_KEY[platform])
        context = feedback_context_prompt(
            record.kept_rules, record.removed_rules, record.added_rules
        )
        if context is not None:
            print(context)
            print()
            print("---")
            print()
        print(synthesize_prompt())
        return

    _check_for_edits(platform, scope="global", project_path=None)

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

    # Only checkpoint after the assistant has iterated through every batch.
    # Saving on earlier batches would cause the next `prepare --batch N+1` call
    # to see a smaller history and report a different total batch count,
    # breaking the iteration mid-way.
    if args.batch == len(batches):
        _save_checkpoint(checkpoint, conversations, platform)


# -- write (AI pipeline stage 2) --


def _run_write(args: argparse.Namespace) -> None:
    platform = args.platform
    scope = args.scope
    project_path = Path(args.project) if args.project else None

    raw = sys.stdin.read()
    if not raw.strip():
        print("No content received on stdin.", file=sys.stderr)
        sys.exit(1)

    doc = parse_personalization(raw)
    rendered = annotate_tentative(doc)

    output = _write_platform(platform, rendered, scope, project_path)

    store = CheckpointStore()
    store.record_generation(
        PLATFORM_KEY[platform],
        conversations_analyzed=0,
        output_path=str(output),
        content=rendered,
        output_hash=content_hash(rendered),
        confidence=doc.confidence,
    )
    store.save()

    print(f"vardoger: wrote personalization to {output}")


# -- feedback (accept / reject) --


def _run_feedback(args: argparse.Namespace) -> None:
    from datetime import UTC, datetime

    platform = args.platform
    action = args.action
    scope = args.scope
    project_path = Path(args.project) if args.project else None
    reason = getattr(args, "reason", "") or ""

    state_key = PLATFORM_KEY[platform]
    store = CheckpointStore()

    if action == "accept":
        event = FeedbackEvent(
            recorded_at=datetime.now(UTC).isoformat(),
            kind="accept",
            summary=reason,
        )
        store.record_feedback_event(state_key, event)
        store.save()
        print(f"vardoger: recorded accept for {platform}.")
        return

    if action == "reject":
        event = FeedbackEvent(
            recorded_at=datetime.now(UTC).isoformat(),
            kind="reject",
            summary=reason,
        )
        store.record_feedback_event(state_key, event)

        rejected = store.pop_generation(state_key)
        if rejected is None:
            print(f"vardoger: nothing to revert for {platform}.", file=sys.stderr)
            store.save()
            return

        previous = store.get_generation(state_key)
        if previous is not None and previous.content:
            output = _write_platform(platform, previous.content, scope, project_path)
            store.save()
            print(f"vardoger: reverted {platform} to previous generation ({output}).")
            return

        cleared = _clear_platform(platform, scope, project_path)
        store.save()
        if cleared:
            print(f"vardoger: cleared {platform} personalization (no prior generation).")
        else:
            print(f"vardoger: no {platform} personalization file to clear.")
        return


# -- compare (A/B quality) --


def _format_metric_line(name: str, before: float, after: float, higher_is_better: bool) -> str:
    delta = after - before
    arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
    if delta == 0:
        direction = "unchanged"
    else:
        direction = "better" if (delta > 0) == higher_is_better else "worse"
    return f"  {name:<22} {before:.3f} {arrow} {after:.3f}  ({direction})"


def _print_comparison(comp: object) -> None:
    from vardoger.models import QualityComparison

    if not isinstance(comp, QualityComparison):
        raise TypeError(type(comp).__name__)
    print(f"platform: {comp.platform}")
    print(f"cutoff:   {comp.cutoff or '(none)'}")

    if comp.before is None or comp.after is None:
        for caveat in comp.caveats:
            print(f"  note: {caveat}")
        return

    print(
        f"  samples (before/after): "
        f"{comp.before.sample_conversations}/{comp.after.sample_conversations} conversations, "
        f"{comp.before.sample_messages}/{comp.after.sample_messages} messages"
    )
    print(
        _format_metric_line(
            "correction_rate",
            comp.before.correction_rate,
            comp.after.correction_rate,
            higher_is_better=False,
        )
    )
    print(
        _format_metric_line(
            "pushback_length",
            comp.before.pushback_length,
            comp.after.pushback_length,
            higher_is_better=False,
        )
    )
    print(
        _format_metric_line(
            "satisfaction_signal",
            comp.before.satisfaction_signal,
            comp.after.satisfaction_signal,
            higher_is_better=True,
        )
    )
    print(
        _format_metric_line(
            "restart_rate",
            comp.before.restart_rate,
            comp.after.restart_rate,
            higher_is_better=False,
        )
    )
    print(
        _format_metric_line(
            "emoji_rate",
            comp.before.emoji_rate,
            comp.after.emoji_rate,
            higher_is_better=False,
        )
    )
    for caveat in comp.caveats:
        print(f"  note: {caveat}")


def _run_compare(args: argparse.Namespace) -> None:
    platforms = PLATFORM_CHOICES if getattr(args, "all", False) else [args.platform]
    use_json = getattr(args, "json", False)
    window = getattr(args, "window", None)

    comparisons = [compare_quality(p, window_days=window) for p in platforms]

    if use_json:
        print(json.dumps([c.model_dump() for c in comparisons], indent=2))
        return

    for i, comp in enumerate(comparisons):
        if i > 0:
            print()
        _print_comparison(comp)


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

    # status
    status_parser = subparsers.add_parser(
        "status",
        help="Check whether personalizations are up to date.",
    )
    status_parser.add_argument(
        "--platform",
        choices=PLATFORM_CHOICES,
        default=None,
        help="Check a single platform (default: all).",
    )
    status_parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output machine-readable JSON.",
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

    # feedback
    feedback_parser = subparsers.add_parser(
        "feedback",
        help="Record accept/reject feedback for the last generation.",
    )
    feedback_parser.add_argument(
        "action",
        choices=["accept", "reject"],
        help="accept: keep the latest generation. reject: auto-revert to the previous one.",
    )
    _add_common_args(feedback_parser)
    feedback_parser.add_argument(
        "--scope",
        choices=["global", "project"],
        default="global",
        help="Scope used when reverting (defaults to global).",
    )
    feedback_parser.add_argument(
        "--project",
        default=None,
        help="Project directory path (used with --scope project).",
    )
    feedback_parser.add_argument(
        "--reason",
        default="",
        help="Optional free-text reason recorded on the feedback event.",
    )

    # compare
    compare_parser = subparsers.add_parser(
        "compare",
        help="Compare conversation quality before vs. after the latest personalization.",
    )
    compare_scope = compare_parser.add_mutually_exclusive_group(required=True)
    compare_scope.add_argument(
        "--platform",
        choices=PLATFORM_CHOICES,
        help="Compare a single platform.",
    )
    compare_scope.add_argument(
        "--all",
        action="store_true",
        default=False,
        help="Compare every supported platform.",
    )
    compare_parser.add_argument(
        "--window",
        type=int,
        default=None,
        metavar="DAYS",
        help="Restrict each bucket to a symmetric window (days) around the cutoff.",
    )
    compare_parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Emit machine-readable JSON.",
    )

    # hidden: _hook-session-start (invoked by plugin hooks, not user-facing)
    hook_parser = subparsers.add_parser("_hook-session-start")
    hook_parser.add_argument("platform", choices=PLATFORM_CHOICES)

    subparsers.add_parser(
        "mcp",
        help="Run the vardoger MCP server over stdio (used by the Cursor plugin).",
    )

    args = parser.parse_args(argv)

    verbose = getattr(args, "verbose", False)
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(name)s: %(message)s",
    )

    if args.command == "setup":
        _run_setup(args)
    elif args.command == "status":
        _run_status(args)
    elif args.command == "_hook-session-start":
        _run_hook_session_start(args)
    elif args.command == "analyze":
        _run_analyze(args)
    elif args.command == "prepare":
        _run_prepare(args)
    elif args.command == "write":
        _run_write(args)
    elif args.command == "feedback":
        _run_feedback(args)
    elif args.command == "compare":
        _run_compare(args)
    elif args.command == "mcp":
        _run_mcp()
    else:
        parser.print_help()
        sys.exit(1)


def _run_mcp() -> None:
    """Run the MCP server over stdio. Used by the Cursor plugin's mcp.json."""
    from vardoger.mcp_server import mcp

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
