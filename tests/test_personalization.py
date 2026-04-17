# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for personalization YAML-frontmatter parsing and tentative annotation."""

from __future__ import annotations

import logging

from vardoger.personalization import (
    TENTATIVE_SUFFIX,
    annotate_tentative,
    parse_personalization,
)

VALID_DOC = """---
confidence:
  - id: c1
    text: "Prefer Python with uv for package management."
    category: "Technical Stack"
    level: high
    supporting_batches: [1, 2, 3]
  - id: c2
    text: "Avoid emojis in assistant responses."
    category: "Things to Avoid"
    level: medium
    supporting_batches: [2]
  - id: c3
    text: "Likes inline code snippets."
    category: "Communication"
    level: low
    supporting_batches: [1]
---

# Personalization

## Technical Stack
- Prefer Python with uv for package management.

## Things to Avoid
- Avoid emojis in assistant responses.

## Communication
- Likes inline code snippets.
"""


def test_parse_valid_frontmatter():
    doc = parse_personalization(VALID_DOC)
    assert len(doc.confidence) == 3
    assert [r.id for r in doc.confidence] == ["c1", "c2", "c3"]
    assert [r.level for r in doc.confidence] == ["high", "medium", "low"]
    assert doc.confidence[0].supporting_batches == [1, 2, 3]
    assert doc.body.startswith("# Personalization")


def test_annotate_tentative_marks_low_confidence_bullets():
    doc = parse_personalization(VALID_DOC)
    rendered = annotate_tentative(doc)

    # High / medium are untouched
    assert "- Prefer Python with uv for package management." in rendered
    assert f"- Prefer Python with uv for package management. {TENTATIVE_SUFFIX}" not in rendered
    assert "- Avoid emojis in assistant responses." in rendered
    assert f"- Avoid emojis in assistant responses. {TENTATIVE_SUFFIX}" not in rendered

    # Low gets tagged
    assert f"- Likes inline code snippets. {TENTATIVE_SUFFIX}" in rendered


def test_annotate_tentative_is_idempotent():
    doc = parse_personalization(VALID_DOC)
    once = annotate_tentative(doc)
    # Re-parse the annotated body; low-confidence rule text now differs
    # (ends with tentative) so annotate_tentative should make no further
    # change when applied to the same doc.
    twice = annotate_tentative(doc)
    assert once == twice

    # Applying the annotator to a hand-built doc where the bullet is
    # already tagged must not double-tag.
    pre_tagged_body = f"## X\n- foo {TENTATIVE_SUFFIX}\n"
    from vardoger.models import PersonalizationDoc, RuleConfidence

    rule = RuleConfidence(id="c", text=f"foo {TENTATIVE_SUFFIX}", category="X", level="low")
    doc2 = PersonalizationDoc(confidence=[rule], body=pre_tagged_body)
    assert annotate_tentative(doc2) == pre_tagged_body


def test_missing_frontmatter_falls_back_gracefully(caplog):
    raw = "# Personalization\n\n## Tech\n- Use pytest.\n"
    with caplog.at_level(logging.WARNING, logger="vardoger.personalization"):
        doc = parse_personalization(raw)
    assert doc.confidence == []
    assert doc.body == raw
    assert any("frontmatter missing" in rec.message for rec in caplog.records)


def test_invalid_yaml_falls_back_gracefully(caplog):
    raw = "---\nconfidence: [unterminated\n---\n\n# Body\n- ok\n"
    with caplog.at_level(logging.WARNING, logger="vardoger.personalization"):
        doc = parse_personalization(raw)
    assert doc.confidence == []
    assert doc.body.startswith("# Body")


def test_non_mapping_yaml_ignored():
    raw = "---\n- just\n- a\n- list\n---\n\n# Body\n- ok\n"
    doc = parse_personalization(raw)
    assert doc.confidence == []
    assert doc.body.startswith("# Body")


def test_confidence_not_a_list_ignored():
    raw = '---\nconfidence: "not a list"\n---\n\n# Body\n- ok\n'
    doc = parse_personalization(raw)
    assert doc.confidence == []


def test_invalid_entry_skipped_but_others_preserved(caplog):
    raw = """---
confidence:
  - id: c1
    text: "ok rule"
    category: "A"
    level: high
  - not_a_mapping
  - id: c2
    text: "bad rule"
    category: "B"
    level: "not-a-valid-level"
---

# Body
- ok rule
- bad rule
"""
    with caplog.at_level(logging.WARNING, logger="vardoger.personalization"):
        doc = parse_personalization(raw)
    assert len(doc.confidence) == 1
    assert doc.confidence[0].id == "c1"


def test_annotate_with_no_low_confidence_returns_body_unchanged():
    doc = parse_personalization(
        """---
confidence:
  - id: c1
    text: "rule"
    category: "A"
    level: high
---

# Body
- rule
"""
    )
    assert annotate_tentative(doc) == doc.body


def test_annotate_handles_asterisk_bullets():
    raw = """---
confidence:
  - id: c1
    text: "star bullet"
    category: "A"
    level: low
---

# Body
* star bullet
"""
    doc = parse_personalization(raw)
    rendered = annotate_tentative(doc)
    assert f"* star bullet {TENTATIVE_SUFFIX}" in rendered


def test_annotate_preserves_indented_bullets():
    raw = (
        "---\n"
        "confidence:\n"
        "  - id: c1\n"
        '    text: "nested rule"\n'
        '    category: "A"\n'
        "    level: low\n"
        "---\n\n"
        "# Body\n"
        "- top\n"
        "  - nested rule\n"
    )
    doc = parse_personalization(raw)
    rendered = annotate_tentative(doc)
    assert f"  - nested rule {TENTATIVE_SUFFIX}" in rendered
