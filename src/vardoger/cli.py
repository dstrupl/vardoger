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
from vardoger.models import CompiledProfile, FeedbackEvent, HookOutput, SessionStartContext
from vardoger.personalization import annotate_tentative, parse_personalization
from vardoger.prompts import feedback_context_prompt, summarize_prompt, synthesize_prompt
from vardoger.quality import compare as compare_quality
from vardoger.staleness import check_staleness
from vardoger.writers.claude_code import clear_claude_code_rules, write_claude_code_rules
from vardoger.writers.cline import clear_cline_rules, write_cline_rules
from vardoger.writers.codex import clear_codex_rules, write_codex_rules
from vardoger.writers.copilot import clear_copilot_rules, write_copilot_rules
from vardoger.writers.cursor import clear_cursor_rules, write_cursor_rules
from vardoger.writers.devin import clear_devin_rules, write_devin_rules
from vardoger.writers.openclaw import clear_openclaw_rules, write_openclaw_rules
from vardoger.writers.windsurf import clear_windsurf_rules, write_windsurf_rules

logger = logging.getLogger(__name__)

PLATFORM_KEY = {
    "cursor": "cursor",
    "claude-code": "claude_code",
    "codex": "codex",
    "openclaw": "openclaw",
    "copilot": "copilot",
    "windsurf": "windsurf",
    "cline": "cline",
    "devin": "devin",
}

PLATFORM_CHOICES = [
    "cursor",
    "claude-code",
    "codex",
    "openclaw",
    "copilot",
    "windsurf",
    "cline",
    "devin",
]


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


_FileFilter = Callable[[Path, str], bool]


def _cursor_reader(file_filter: _FileFilter | None = None) -> list[Conversation]:
    return read_cursor_history(file_filter=file_filter)


def _claude_code_reader(file_filter: _FileFilter | None = None) -> list[Conversation]:
    return read_claude_code_history(file_filter=file_filter)


def _codex_reader(file_filter: _FileFilter | None = None) -> list[Conversation]:
    return read_codex_history(file_filter=file_filter)


def _openclaw_reader(file_filter: _FileFilter | None = None) -> list[Conversation]:
    from vardoger.history.openclaw import read_openclaw_history

    return read_openclaw_history(file_filter=file_filter)


def _copilot_reader(file_filter: _FileFilter | None = None) -> list[Conversation]:
    from vardoger.history.copilot import read_copilot_history

    return read_copilot_history(file_filter=file_filter)


def _windsurf_reader(file_filter: _FileFilter | None = None) -> list[Conversation]:
    from vardoger.history.windsurf import read_windsurf_history

    return read_windsurf_history(file_filter=file_filter)


def _cline_reader(file_filter: _FileFilter | None = None) -> list[Conversation]:
    from vardoger.history.cline import read_cline_history

    return read_cline_history(file_filter=file_filter)


def _devin_reader(file_filter: _FileFilter | None = None) -> list[Conversation]:
    from vardoger.history.devin import read_devin_history

    return read_devin_history(file_filter=file_filter)


_HISTORY_DISPATCH: dict[str, Callable[..., list[Conversation]]] = {
    "cursor": _cursor_reader,
    "claude-code": _claude_code_reader,
    "codex": _codex_reader,
    "openclaw": _openclaw_reader,
    "copilot": _copilot_reader,
    "windsurf": _windsurf_reader,
    "cline": _cline_reader,
    "devin": _devin_reader,
}


def _history_reader(platform: str) -> Callable[..., list[Conversation]]:
    """Return the platform-specific ``read_<platform>_history`` callable."""
    reader = _HISTORY_DISPATCH.get(platform)
    if reader is None:
        print(f"Unknown platform: {platform}", file=sys.stderr)
        sys.exit(1)
    return reader


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

    reader = _history_reader(platform)
    conversations = reader(file_filter=filter_fn)
    return conversations, checkpoint, stats


_WRITE_DISPATCH: dict[str, Callable[..., Path]] = {
    "cursor": lambda content, scope, project_path: write_cursor_rules(
        content, project_path=project_path
    ),
    "claude-code": lambda content, scope, project_path: write_claude_code_rules(
        content, scope=scope, project_path=project_path
    ),
    "codex": lambda content, scope, project_path: write_codex_rules(
        content, scope=scope, project_path=project_path
    ),
    "openclaw": lambda content, scope, project_path: write_openclaw_rules(
        content, scope=scope, project_path=project_path
    ),
    "copilot": lambda content, scope, project_path: write_copilot_rules(
        content, scope=scope, project_path=project_path
    ),
    "windsurf": lambda content, scope, project_path: write_windsurf_rules(
        content, scope=scope, project_path=project_path
    ),
    "cline": lambda content, scope, project_path: write_cline_rules(
        content, scope=scope, project_path=project_path
    ),
    "devin": lambda content, scope, project_path: write_devin_rules(
        content, scope=scope, project_path=project_path
    ),
}

_CLEAR_DISPATCH: dict[str, Callable[..., bool]] = {
    "cursor": lambda scope, project_path: clear_cursor_rules(project_path=project_path),
    "claude-code": lambda scope, project_path: clear_claude_code_rules(
        scope=scope, project_path=project_path
    ),
    "codex": lambda scope, project_path: clear_codex_rules(scope=scope, project_path=project_path),
    "openclaw": lambda scope, project_path: clear_openclaw_rules(
        scope=scope, project_path=project_path
    ),
    "copilot": lambda scope, project_path: clear_copilot_rules(
        scope=scope, project_path=project_path
    ),
    "windsurf": lambda scope, project_path: clear_windsurf_rules(
        scope=scope, project_path=project_path
    ),
    "cline": lambda scope, project_path: clear_cline_rules(scope=scope, project_path=project_path),
    "devin": lambda scope, project_path: clear_devin_rules(scope=scope, project_path=project_path),
}


def _write_platform(platform: str, content: str, scope: str, project_path: Path | None) -> Path:
    """Write content to the appropriate platform rules location."""
    handler = _WRITE_DISPATCH.get(platform)
    if handler is None:
        print(f"Unknown platform: {platform}", file=sys.stderr)
        sys.exit(1)
    return handler(content, scope, project_path)


def _clear_platform(platform: str, scope: str, project_path: Path | None) -> bool:
    """Remove the vardoger-managed rules for a platform. Returns True if removed."""
    handler = _CLEAR_DISPATCH.get(platform)
    if handler is None:
        print(f"Unknown platform: {platform}", file=sys.stderr)
        sys.exit(1)
    return handler(scope, project_path)


def _get_reader_base(platform: str) -> Path:
    """Return the base directory for a platform's history files."""
    from vardoger.config import CopilotConfig
    from vardoger.history.claude_code import DEFAULT_CLAUDE_DIR
    from vardoger.history.cline import DEFAULT_CLINE_DIR
    from vardoger.history.codex import DEFAULT_CODEX_DIR
    from vardoger.history.cursor import DEFAULT_CURSOR_DIR
    from vardoger.history.devin import DEFAULT_DEVIN_DIR
    from vardoger.history.openclaw import DEFAULT_OPENCLAW_DIR
    from vardoger.history.windsurf import DEFAULT_WINDSURF_DIR

    return {
        "cursor": DEFAULT_CURSOR_DIR,
        "claude-code": DEFAULT_CLAUDE_DIR,
        "codex": DEFAULT_CODEX_DIR,
        "openclaw": DEFAULT_OPENCLAW_DIR,
        "copilot": CopilotConfig.from_env().session_state_dir,
        "windsurf": DEFAULT_WINDSURF_DIR,
        "cline": DEFAULT_CLINE_DIR,
        "devin": DEFAULT_DEVIN_DIR,
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
    from vardoger.setup import (
        setup_claude_code,
        setup_cline,
        setup_codex,
        setup_copilot,
        setup_cursor,
        setup_devin,
        setup_openclaw,
        setup_windsurf,
    )

    platform = args.platform
    if platform == "cursor":
        setup_cursor()
    elif platform == "claude-code":
        setup_claude_code()
    elif platform == "codex":
        setup_codex()
    elif platform == "openclaw":
        setup_openclaw()
    elif platform == "copilot":
        setup_copilot()
    elif platform == "windsurf":
        setup_windsurf()
    elif platform == "cline":
        setup_cline()
    elif platform == "devin":
        setup_devin()


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
        print(synthesize_prompt(platform))
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


# -- profile (cross-host compiler) --


def _run_profile_sources(args: argparse.Namespace) -> None:
    from vardoger.models import ProfileGenerationSummary
    from vardoger.profile import parse_generation_time

    store = CheckpointStore()
    platforms = (
        [PLATFORM_KEY[args.platform]] if args.platform else sorted(set(PLATFORM_KEY.values()))
    )
    summaries = [
        ProfileGenerationSummary(
            platform=platform,
            generation=index,
            generated_at=parse_generation_time(record.generated_at),
            conversations_analyzed=record.conversations_analyzed,
            output_path=record.output_path,
            output_hash=record.output_hash,
            rule_count=len(record.confidence),
        )
        for platform in platforms
        for index, record in enumerate(store.get_generation_history(platform), start=1)
    ]
    if args.json:
        print(json.dumps([item.model_dump(mode="json") for item in summaries], indent=2))
        return
    if not summaries:
        print("No Vardoger generations are available for profile compilation.")
        return
    for item in summaries:
        print(
            f"{item.platform}:{item.generation}  {item.generated_at.isoformat()}  "
            f"{item.rule_count} confidence rule(s)  {item.output_path}"
        )


def _compile_profile_args(args: argparse.Namespace) -> tuple[CompiledProfile, str, Path, str]:
    from vardoger.models import ProfileCompileOptions
    from vardoger.profile import (
        ProfileSelectionError,
        compile_profile,
        load_selected_generations,
        parse_source_selection,
        preview_agents_diff,
        render_agents_profile,
    )

    selections = []
    for value in args.source:
        selection = parse_source_selection(value)
        selection.platform = PLATFORM_KEY.get(selection.platform, selection.platform)
        if selection.platform not in set(PLATFORM_KEY.values()):
            message = f"Unsupported generation platform {selection.platform!r}."
            raise ProfileSelectionError(message)
        selections.append(selection)
    options = ProfileCompileOptions(
        min_confidence=args.min_confidence,
        max_age_days=args.max_age,
        redact_patterns=args.redact,
        redaction_policy=args.redaction_policy,
    )
    selected = load_selected_generations(CheckpointStore(), selections)
    profile = compile_profile(selected, options)
    rendered = render_agents_profile(profile)
    target = Path(args.target).expanduser().resolve()
    if target.name != "AGENTS.md":
        message = "The portable profile target must be named AGENTS.md."
        raise ProfileSelectionError(message)
    return profile, rendered, target, preview_agents_diff(target, rendered)


def _run_profile_preview(args: argparse.Namespace) -> None:
    profile, rendered, target, diff = _compile_profile_args(args)
    if args.json:
        print(profile.model_dump_json(indent=2))
        return
    _print_profile_review(profile, rendered, target, diff)


def _print_profile_review(
    profile: CompiledProfile, rendered: str, target: Path, diff: str
) -> None:
    """Print the rendered instructions, audit decisions, and exact write diff."""
    active = sum(rule.state == "active" for rule in profile.preferences)
    print(rendered, end="")
    print(
        f"\nReview summary: {active} active, {len(profile.conflicts)} conflict(s) withheld, "
        f"{len(profile.exclusions)} excluded."
    )
    by_id = {rule.id: rule for rule in profile.preferences}
    for conflict in profile.conflicts:
        texts = " versus ".join(repr(by_id[item].text) for item in conflict.preference_ids)
        print(f"  conflict [{conflict.key}]: {texts}")
    for exclusion in profile.exclusions:
        print(f"  excluded [{exclusion.reason}]: {exclusion.source}")
    print(f"\nProposed diff for {target}:")
    print(diff or "(no changes)", end="" if diff.endswith("\n") else "\n")


def _run_profile_write(args: argparse.Namespace) -> None:
    from vardoger.profile import write_agents_profile

    profile, rendered, target, diff = _compile_profile_args(args)
    if not args.apply:
        _print_profile_review(profile, rendered, target, diff)
        print(
            "vardoger: preview only; rerun with --apply after reviewing this diff.",
            file=sys.stderr,
        )
        return
    write_agents_profile(target, rendered)
    print(f"vardoger: wrote reviewed cross-host profile to {target}")


def _add_profile_compile_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--source",
        action="append",
        required=True,
        metavar="PLATFORM:GENERATION",
        help="Explicit generation selection; GENERATION is one-based or 'latest'. Repeatable.",
    )
    parser.add_argument(
        "--target",
        default="AGENTS.md",
        help="Portable AGENTS.md to preview or update (default: ./AGENTS.md).",
    )
    parser.add_argument(
        "--min-confidence",
        choices=["low", "medium", "high"],
        default="low",
        help="Exclude rules below this confidence level.",
    )
    parser.add_argument(
        "--max-age",
        type=_non_negative_int,
        default=None,
        metavar="DAYS",
        help="Exclude rules older than DAYS relative to the newest selected generation.",
    )
    parser.add_argument(
        "--redact",
        action="append",
        default=[],
        metavar="REGEX",
        help="Drop or mask rules matching this case-insensitive regular expression. Repeatable.",
    )
    parser.add_argument(
        "--redaction-policy",
        choices=["drop", "mask"],
        default="drop",
        help="How matching rules are handled (default: drop).",
    )


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        message = "must be zero or greater"
        raise argparse.ArgumentTypeError(message)
    return parsed


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
        help=(
            "Limit to files modified in the last N days. Default: no limit "
            "(first run sees full history; subsequent runs are bounded by "
            "the checkpoint store at ~/.vardoger/state.json)."
        ),
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
        help=(
            "Limit to files modified in the last N days. Default: no limit "
            "(first run sees full history; subsequent runs are bounded by "
            "the checkpoint store at ~/.vardoger/state.json)."
        ),
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

    # profile
    profile_parser = subparsers.add_parser(
        "profile",
        help="Compile selected reviewed generations into a portable AGENTS.md profile.",
    )
    profile_subparsers = profile_parser.add_subparsers(dest="profile_command", required=True)
    profile_sources = profile_subparsers.add_parser(
        "sources",
        help="List existing Vardoger generations available for explicit selection.",
    )
    profile_sources.add_argument(
        "--platform",
        choices=PLATFORM_CHOICES,
        default=None,
        help="Limit the list to one platform.",
    )
    profile_sources.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Emit machine-readable generation metadata.",
    )
    profile_preview = profile_subparsers.add_parser(
        "preview",
        help="Render and diff a profile without writing anything.",
    )
    _add_profile_compile_args(profile_preview)
    profile_preview.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Emit the normalized profile and provenance as JSON.",
    )
    profile_write = profile_subparsers.add_parser(
        "write",
        help="Preview by default; update only a fenced AGENTS.md block with --apply.",
    )
    _add_profile_compile_args(profile_write)
    profile_write.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Apply the displayed profile to the target's Vardoger-owned block.",
    )

    # hidden: _hook-session-start (invoked by plugin hooks, not user-facing)
    hook_parser = subparsers.add_parser("_hook-session-start")
    hook_parser.add_argument("platform", choices=PLATFORM_CHOICES)

    subparsers.add_parser(
        "mcp",
        help=(
            "Run the vardoger MCP server over stdio. Works with any MCP-capable "
            "client (Cursor, Cline, Windsurf, ...). Set VARDOGER_MCP_PLATFORM to "
            "the target platform so tool calls default to the right history."
        ),
    )

    args = parser.parse_args(argv)

    verbose = getattr(args, "verbose", False)
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(name)s: %(message)s",
    )

    from vardoger.history.openclaw import UnsupportedOpenClawHistoryError
    from vardoger.profile import ProfileSelectionError

    try:
        _dispatch_command(args, parser)
    except (UnsupportedOpenClawHistoryError, ProfileSelectionError) as exc:
        print(f"vardoger: {exc}", file=sys.stderr)
        sys.exit(2)


def _dispatch_command(  # noqa: C901, PLR0912
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> None:
    """Run the parsed command."""
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
    elif args.command == "profile" and args.profile_command == "preview":
        _run_profile_preview(args)
    elif args.command == "profile" and args.profile_command == "write":
        _run_profile_write(args)
    elif args.command == "profile" and args.profile_command == "sources":
        _run_profile_sources(args)
    elif args.command == "mcp":
        _run_mcp()
    else:
        parser.print_help()
        sys.exit(1)


def _run_mcp() -> None:
    """Run the vardoger MCP server over stdio.

    Registered by each platform's MCP config (Cursor's ``mcp.json``,
    Cline's ``cline_mcp_settings.json``, Windsurf's ``mcp_config.json``,
    etc.). Set ``VARDOGER_MCP_PLATFORM`` in the server's environment so
    non-Cursor clients default to the correct platform.
    """
    from vardoger.mcp_server import mcp

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
