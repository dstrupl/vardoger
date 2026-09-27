# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Compile reviewed Vardoger generations into a portable user profile.

This module deliberately consumes only generation records already selected by
the user.  It never reads conversation transcripts and never writes host rules.
"""

from __future__ import annotations

import difflib
import hashlib
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from vardoger.checkpoint import CheckpointStore
from vardoger.models import (
    CompiledProfile,
    ConfidenceLevel,
    GenerationRecord,
    NormalizedPreference,
    PreferenceEvidence,
    ProfileCompileOptions,
    ProfileConflict,
    ProfileExclusion,
    ProfileSourceSelection,
)

START_MARKER = "<!-- vardoger-profile:start -->"
END_MARKER = "<!-- vardoger-profile:end -->"
_SECTION_RE = re.compile(
    re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
    re.DOTALL,
)
_BULLET_RE = re.compile(r"^\s*[-*]\s+(?P<text>.+?)\s*$")
_HEADING_RE = re.compile(r"^#{2,}\s+(?P<category>.+?)\s*$")
_SPACE_RE = re.compile(r"\s+")
_EDGE_PUNCTUATION_RE = re.compile(r"^[\s\W_]+|[\s\W_]+$")
_NEGATIVE_PREFIXES = ("do not ", "don't ", "avoid ", "never ", "no ")
_POSITIVE_PREFIXES = ("prefer ", "use ", "always ", "keep ", "include ")
_CONFIDENCE_RANK: dict[ConfidenceLevel, int] = {"low": 0, "medium": 1, "high": 2}
_MIN_DUPLICATES = 2


class ProfileSelectionError(ValueError):
    """Raised when an explicitly requested generation cannot be selected."""


def parse_source_selection(value: str) -> ProfileSourceSelection:
    """Parse ``PLATFORM:latest`` or ``PLATFORM:N`` (one-based)."""
    platform, separator, raw_generation = value.partition(":")
    if not separator or not platform or not raw_generation:
        message = f"Invalid source {value!r}; expected PLATFORM:latest or PLATFORM:N."
        raise ProfileSelectionError(message)
    if raw_generation == "latest":
        generation: int | Literal["latest"] = "latest"
    else:
        try:
            generation = int(raw_generation)
        except ValueError as exc:
            message = f"Invalid generation in {value!r}; use 'latest' or a positive integer."
            raise ProfileSelectionError(message) from exc
        if generation < 1:
            message = f"Generation in {value!r} must be at least 1."
            raise ProfileSelectionError(message)
    return ProfileSourceSelection(platform=platform, generation=generation)


def load_selected_generations(
    store: CheckpointStore,
    selections: list[ProfileSourceSelection],
) -> list[tuple[ProfileSourceSelection, int, GenerationRecord]]:
    """Resolve explicit selections while retaining their stable one-based indexes."""
    resolved: list[tuple[ProfileSourceSelection, int, GenerationRecord]] = []
    seen: set[tuple[str, int]] = set()
    for selection in selections:
        history = store.get_generation_history(selection.platform)
        if not history:
            message = f"No Vardoger generations exist for {selection.platform!r}."
            raise ProfileSelectionError(message)
        index = len(history) if selection.generation == "latest" else selection.generation
        if index > len(history):
            message = (
                f"Generation {index} for {selection.platform!r} does not exist "
                f"(available: 1-{len(history)})."
            )
            raise ProfileSelectionError(message)
        identity = (selection.platform, index)
        if identity in seen:
            message = f"Generation {selection.platform}:{index} was selected more than once."
            raise ProfileSelectionError(message)
        seen.add(identity)
        resolved.append((selection, index, history[index - 1]))
    return resolved


def compile_profile(
    selected: list[tuple[ProfileSourceSelection, int, GenerationRecord]],
    options: ProfileCompileOptions | None = None,
) -> CompiledProfile:
    """Compile selected generation records into a deterministic profile."""
    if not selected:
        message = "Select at least one Vardoger generation."
        raise ProfileSelectionError(message)
    controls = options or ProfileCompileOptions()
    patterns = _compile_redactions(controls.redact_patterns)
    parsed_times = [parse_generation_time(record.generated_at) for _, _, record in selected]
    reference_time = max(parsed_times)
    exclusions: list[ProfileExclusion] = []
    preferences: list[NormalizedPreference] = []

    ordered = sorted(
        zip(selected, parsed_times, strict=True),
        key=lambda item: (item[1], item[0][0].platform, item[0][1]),
    )
    for (selection, index, record), generated_at in ordered:
        age_days = max(0, (reference_time - generated_at).days)
        for text, category, confidence, rule_id in _rules_from_generation(record):
            source_rule = rule_id or hashlib.sha256(text.encode()).hexdigest()[:12]
            source_name = f"{selection.platform}:{index}:{source_rule}"
            if _CONFIDENCE_RANK[confidence] < _CONFIDENCE_RANK[controls.min_confidence]:
                exclusions.append(ProfileExclusion(source=source_name, reason="below-confidence"))
                continue
            if controls.max_age_days is not None and age_days > controls.max_age_days:
                exclusions.append(ProfileExclusion(source=source_name, reason="outside-retention"))
                continue
            redacted, matched = _redact(text, patterns)
            if matched and controls.redaction_policy == "drop":
                exclusions.append(ProfileExclusion(source=source_name, reason="redacted"))
                continue
            evidence = PreferenceEvidence(
                platform=selection.platform,
                generation=index,
                generated_at=generated_at,
                output_path=record.output_path,
                output_hash=record.output_hash,
                rule_id=rule_id,
            )
            preference_id = _preference_id(selection.platform, index, rule_id, text)
            preferences.append(
                NormalizedPreference(
                    id=preference_id,
                    text=redacted,
                    category=category,
                    confidence=confidence,
                    observed_at=generated_at,
                    age_days=age_days,
                    evidence=[evidence],
                )
            )

    _mark_superseded(preferences)
    conflicts = _mark_conflicts(preferences)
    preferences.sort(key=lambda rule: (rule.category.casefold(), rule.text.casefold(), rule.id))
    exclusions.sort(key=lambda item: (item.reason, item.source))
    return CompiledProfile(
        reference_time=reference_time,
        sources=sorted(
            [
                ProfileSourceSelection(platform=selection.platform, generation=index)
                for selection, index, _record in selected
            ],
            key=lambda item: (item.platform, item.generation),
        ),
        preferences=preferences,
        conflicts=conflicts,
        exclusions=exclusions,
    )


def render_agents_profile(profile: CompiledProfile) -> str:
    """Render active preferences as a portable, fenced ``AGENTS.md`` section."""
    lines = [START_MARKER, "## Vardoger cross-host profile", ""]
    active = [rule for rule in profile.preferences if rule.state == "active"]
    by_category: dict[str, list[NormalizedPreference]] = defaultdict(list)
    for rule in active:
        by_category[rule.category].append(rule)
    if not active:
        lines.append("No unambiguous preferences are currently active.")
    else:
        for category in sorted(by_category, key=str.casefold):
            lines.extend([f"### {category}", ""])
            for rule in sorted(by_category[category], key=lambda item: item.text.casefold()):
                lines.append(f"- {rule.text}")
            lines.append("")
    if profile.conflicts:
        lines.append(f"<!-- {len(profile.conflicts)} conflict(s) omitted pending review. -->")
    lines.append(END_MARKER)
    return "\n".join(lines).rstrip() + "\n"


def merge_agents_profile(existing: str, rendered: str) -> str:
    """Replace only Vardoger's profile block, preserving all other content."""
    if _SECTION_RE.search(existing):
        return _SECTION_RE.sub(rendered.rstrip(), existing).rstrip() + "\n"
    if not existing.strip():
        return rendered
    return existing.rstrip() + "\n\n" + rendered


def preview_agents_diff(target: Path, rendered: str) -> str:
    """Return the exact unified diff an explicit write would apply."""
    existing = target.read_text(encoding="utf-8") if target.is_file() else ""
    updated = merge_agents_profile(existing, rendered)
    return "".join(
        difflib.unified_diff(
            existing.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=str(target),
            tofile=str(target),
        )
    )


def write_agents_profile(target: Path, rendered: str) -> None:
    """Apply a reviewed profile while preserving non-Vardoger content."""
    if target.is_symlink():
        message = f"Refusing to write through symlinked AGENTS.md: {target}."
        raise ProfileSelectionError(message)
    existing = target.read_text(encoding="utf-8") if target.is_file() else ""
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(merge_agents_profile(existing, rendered), encoding="utf-8")


def _rules_from_generation(
    record: GenerationRecord,
) -> list[tuple[str, str, ConfidenceLevel, str | None]]:
    if record.confidence:
        return [
            (rule.text.strip(), rule.category.strip() or "Preferences", rule.level, rule.id)
            for rule in record.confidence
            if rule.text.strip()
        ]
    rules: list[tuple[str, str, ConfidenceLevel, str | None]] = []
    category = "Preferences"
    for line in record.content.splitlines():
        heading = _HEADING_RE.match(line)
        if heading:
            category = heading.group("category").strip()
            continue
        bullet = _BULLET_RE.match(line)
        if bullet:
            text = re.sub(r"\s+\(tentative\)$", "", bullet.group("text")).strip()
            if text:
                rules.append((text, category, record.min_confidence_written, None))
    return rules


def parse_generation_time(value: str) -> datetime:
    """Parse a stored generation timestamp and normalize legacy naive values to UTC."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        message = f"Invalid generation timestamp {value!r}."
        raise ProfileSelectionError(message) from exc
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _compile_redactions(patterns: list[str]) -> list[re.Pattern[str]]:
    compiled: list[re.Pattern[str]] = []
    for pattern in patterns:
        try:
            compiled.append(re.compile(pattern, re.IGNORECASE))
        except re.error as exc:
            message = f"Invalid redaction pattern {pattern!r}: {exc}."
            raise ProfileSelectionError(message) from exc
    return compiled


def _redact(text: str, patterns: list[re.Pattern[str]]) -> tuple[str, bool]:
    matched = any(pattern.search(text) for pattern in patterns)
    if not matched:
        return text, False
    result = text
    for pattern in patterns:
        result = pattern.sub("[REDACTED]", result)
    return result, True


def _preference_id(platform: str, index: int, rule_id: str | None, text: str) -> str:
    raw = f"{platform}\0{index}\0{rule_id or ''}\0{_normalize(text)}"
    return "pref-" + hashlib.sha256(raw.encode()).hexdigest()[:12]


def _normalize(text: str) -> str:
    return _SPACE_RE.sub(" ", _EDGE_PUNCTUATION_RE.sub("", text.casefold())).strip()


def _polarity_key(text: str) -> tuple[str, int]:
    normalized = _normalize(text)
    for prefix in _NEGATIVE_PREFIXES:
        if normalized.startswith(prefix):
            return _normalize(normalized[len(prefix) :]), -1
    for prefix in _POSITIVE_PREFIXES:
        if normalized.startswith(prefix):
            return _normalize(normalized[len(prefix) :]), 1
    return normalized, 0


def _mark_superseded(preferences: list[NormalizedPreference]) -> None:
    grouped: dict[str, list[NormalizedPreference]] = defaultdict(list)
    for preference in preferences:
        grouped[_normalize(preference.text)].append(preference)
    for duplicates in grouped.values():
        if len(duplicates) < _MIN_DUPLICATES:
            continue
        winner = max(duplicates, key=lambda item: (item.observed_at, item.id))
        for duplicate in duplicates:
            if duplicate.id != winner.id:
                duplicate.state = "superseded"
                duplicate.superseded_by = winner.id
                winner.evidence.extend(duplicate.evidence)
        winner.evidence.sort(
            key=lambda item: (
                item.generated_at,
                item.platform,
                item.generation,
                item.rule_id or "",
            )
        )


def _mark_conflicts(preferences: list[NormalizedPreference]) -> list[ProfileConflict]:
    grouped: dict[str, list[tuple[NormalizedPreference, int]]] = defaultdict(list)
    for preference in preferences:
        if preference.state == "active":
            key, polarity = _polarity_key(preference.text)
            if key and polarity:
                grouped[key].append((preference, polarity))
    conflicts: list[ProfileConflict] = []
    for key, candidates in grouped.items():
        if {polarity for _, polarity in candidates} != {-1, 1}:
            continue
        ids = sorted(preference.id for preference, _ in candidates)
        for preference, _ in candidates:
            preference.state = "conflict"
        conflicts.append(ProfileConflict(key=key, preference_ids=ids))
    return sorted(conflicts, key=lambda item: item.key)
