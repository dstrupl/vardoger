# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for deterministic cross-host profile compilation."""

from __future__ import annotations

from pathlib import Path

import pytest

from vardoger.checkpoint import CheckpointStore
from vardoger.models import (
    GenerationRecord,
    ProfileCompileOptions,
    ProfileSourceSelection,
    RuleConfidence,
)
from vardoger.profile import (
    END_MARKER,
    START_MARKER,
    ProfileSelectionError,
    compile_profile,
    load_selected_generations,
    merge_agents_profile,
    parse_source_selection,
    preview_agents_diff,
    render_agents_profile,
    write_agents_profile,
)


def _record(
    when: str,
    rules: list[tuple[str, str, str, str]],
    *,
    content: str = "",
) -> GenerationRecord:
    return GenerationRecord(
        generated_at=when,
        conversations_analyzed=2,
        output_path="/generated/rules.md",
        output_hash="abc123",
        content=content,
        confidence=[
            RuleConfidence(id=rule_id, text=text, category=category, level=level)
            for rule_id, text, category, level in rules
        ],
    )


def _selected(
    platform: str, index: int, record: GenerationRecord
) -> tuple[ProfileSourceSelection, int, GenerationRecord]:
    return ProfileSourceSelection(platform=platform, generation=index), index, record


def test_parse_source_selection_requires_explicit_generation() -> None:
    assert parse_source_selection("codex:latest") == ProfileSourceSelection(
        platform="codex", generation="latest"
    )
    assert parse_source_selection("cursor:2").generation == 2
    with pytest.raises(ProfileSelectionError, match="expected PLATFORM"):
        parse_source_selection("cursor")
    with pytest.raises(ProfileSelectionError, match="at least 1"):
        parse_source_selection("cursor:0")


def test_load_selected_generations_resolves_indexes_and_rejects_duplicates(
    tmp_path: Path,
) -> None:
    store = CheckpointStore(state_dir=tmp_path)
    store.record_generation("codex", 1, "/one", content="- one")
    store.record_generation("codex", 1, "/two", content="- two")

    selected = load_selected_generations(
        store,
        [ProfileSourceSelection(platform="codex", generation="latest")],
    )
    assert selected[0][1] == 2
    assert selected[0][2].content == "- two"
    with pytest.raises(ProfileSelectionError, match="selected more than once"):
        load_selected_generations(
            store,
            [
                ProfileSourceSelection(platform="codex", generation=2),
                ProfileSourceSelection(platform="codex", generation="latest"),
            ],
        )


def test_compile_tracks_provenance_supersession_conflicts_and_recency() -> None:
    old = _record(
        "2026-01-01T00:00:00+00:00",
        [("a", "Prefer tabs", "Formatting", "medium")],
    )
    new = _record(
        "2026-01-11T00:00:00+00:00",
        [
            ("b", "Prefer tabs", "Formatting", "high"),
            ("c", "Avoid tabs", "Formatting", "high"),
            ("d", "Use pytest", "Testing", "high"),
        ],
    )

    profile = compile_profile([_selected("cursor", 1, old), _selected("codex", 2, new)])

    by_text = {rule.text: rule for rule in profile.preferences if rule.state != "superseded"}
    assert by_text["Prefer tabs"].state == "conflict"
    assert by_text["Avoid tabs"].state == "conflict"
    assert by_text["Use pytest"].state == "active"
    assert len(by_text["Prefer tabs"].evidence) == 2
    assert {event.platform for event in by_text["Prefer tabs"].evidence} == {"cursor", "codex"}
    superseded = next(rule for rule in profile.preferences if rule.state == "superseded")
    assert superseded.superseded_by == by_text["Prefer tabs"].id
    assert superseded.age_days == 10
    assert profile.conflicts[0].key == "tabs"


def test_compile_is_deterministic_for_same_selected_records() -> None:
    first_record = _record(
        "2026-01-01T00:00:00+00:00",
        [("a", "Use uv", "Tools", "high")],
    )
    second_record = _record(
        "2026-01-02T00:00:00+00:00",
        [("b", "Use pytest", "Testing", "high")],
    )
    selected = [_selected("codex", 1, first_record), _selected("cursor", 2, second_record)]
    first = compile_profile(selected).model_dump_json()
    second = compile_profile(list(reversed(selected))).model_dump_json()
    assert first == second


def test_retention_confidence_and_redaction_controls_are_auditable() -> None:
    old = _record(
        "2026-01-01T00:00:00+00:00",
        [("old", "Use make", "Tools", "high")],
    )
    new = _record(
        "2026-02-01T00:00:00+00:00",
        [
            ("low", "Use tox", "Tools", "low"),
            ("secret", "Email alice@example.com", "Contact", "high"),
            ("keep", "Use pytest", "Testing", "high"),
        ],
    )
    options = ProfileCompileOptions(
        min_confidence="medium",
        max_age_days=10,
        redact_patterns=[r"\S+@example\.com"],
        redaction_policy="drop",
    )

    profile = compile_profile([_selected("cursor", 1, old), _selected("codex", 1, new)], options)

    assert [rule.text for rule in profile.preferences] == ["Use pytest"]
    assert {item.reason for item in profile.exclusions} == {
        "below-confidence",
        "outside-retention",
        "redacted",
    }


def test_mask_redaction_replaces_only_matching_text() -> None:
    record = _record(
        "2026-01-01T00:00:00+00:00",
        [("secret", "Email alice@example.com", "Contact", "high")],
    )
    profile = compile_profile(
        [_selected("codex", 1, record)],
        ProfileCompileOptions(redact_patterns=[r"\S+@example\.com"], redaction_policy="mask"),
    )
    assert profile.preferences[0].text == "Email [REDACTED]"
    assert profile.exclusions == []


def test_fallback_bullet_extraction_uses_markdown_categories() -> None:
    record = _record(
        "2026-01-01T00:00:00+00:00",
        [],
        content="# Personalization\n\n## Testing\n- Use pytest\n- Try tox (tentative)\n",
    )
    profile = compile_profile([_selected("codex", 1, record)])
    assert [(rule.category, rule.text) for rule in profile.preferences] == [
        ("Testing", "Try tox"),
        ("Testing", "Use pytest"),
    ]


def test_render_and_merge_preserve_non_vardoger_content(tmp_path: Path) -> None:
    record = _record(
        "2026-01-01T00:00:00+00:00",
        [
            ("a", "Use pytest", "Testing", "high"),
            ("b", "Prefer tabs", "Formatting", "high"),
            ("c", "Avoid tabs", "Formatting", "high"),
        ],
    )
    rendered = render_agents_profile(compile_profile([_selected("codex", 1, record)]))
    assert "- Use pytest" in rendered
    assert "Prefer tabs" not in rendered
    assert "conflict(s) omitted" in rendered

    existing = "# Team instructions\n\nKeep this.\n"
    merged = merge_agents_profile(existing, rendered)
    assert merged.startswith(existing.rstrip())
    assert START_MARKER in merged and END_MARKER in merged

    target = tmp_path / "AGENTS.md"
    target.write_text(existing)
    diff = preview_agents_diff(target, rendered)
    assert "+<!-- vardoger-profile:start -->" in diff
    assert " Keep this." in diff
    write_agents_profile(target, rendered)
    assert "Keep this." in target.read_text()
    assert target.read_text().count(START_MARKER) == 1

    updated = rendered.replace("Use pytest", "Use uv")
    write_agents_profile(target, updated)
    assert "Keep this." in target.read_text()
    assert "Use pytest" not in target.read_text()
    assert target.read_text().count(START_MARKER) == 1
