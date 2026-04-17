# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Parse and annotate personalization markdown produced by the host AI model.

The synthesis prompt instructs the model to emit a YAML frontmatter block
listing every rule's confidence metadata, followed by the markdown body.

This module provides:
  - ``parse_personalization(text)`` — extracts the frontmatter into
    ``RuleConfidence`` objects, returns a ``PersonalizationDoc``. Falls back
    gracefully to ``confidence=[], body=text`` when the frontmatter is
    missing or invalid (logged as a warning, never raises).
  - ``annotate_tentative(doc)`` — returns a rendered body where every bullet
    whose ``text`` matches a ``low``-confidence rule has ``(tentative)``
    appended once. Idempotent.

YAML parsing uses ``yaml.safe_load`` only per the repo's XML/serialization
security rules.
"""

from __future__ import annotations

import logging
import re

import yaml
from pydantic import ValidationError

from vardoger.models import PersonalizationDoc, RuleConfidence

logger = logging.getLogger(__name__)

TENTATIVE_SUFFIX = "(tentative)"

_FRONTMATTER_RE = re.compile(
    r"\A\s*---\s*\n(?P<yaml>.*?)\n---\s*(?:\n|$)(?P<body>.*)\Z",
    re.DOTALL,
)


def parse_personalization(text: str) -> PersonalizationDoc:
    """Parse model output into a ``PersonalizationDoc``.

    Expected shape:

        ---
        confidence:
          - id: c1
            text: "..."
            category: "..."
            level: high
            supporting_batches: [1, 2]
        ---

        # Personalization
        ...

    If the frontmatter is missing or invalid, returns a doc with
    ``confidence=[]`` and ``body=text``, logging a warning.
    """
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        logger.warning(
            "Personalization frontmatter missing; falling back to raw body (no confidence data).",
        )
        return PersonalizationDoc(confidence=[], body=text)

    yaml_text = match.group("yaml")
    body = match.group("body").lstrip("\n")

    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        logger.warning("Could not parse personalization YAML frontmatter: %s", exc)
        return PersonalizationDoc(confidence=[], body=body)

    if not isinstance(data, dict):
        logger.warning(
            "Personalization frontmatter is not a mapping; ignoring confidence data.",
        )
        return PersonalizationDoc(confidence=[], body=body)

    raw_confidence = data.get("confidence", [])
    if not isinstance(raw_confidence, list):
        logger.warning(
            "Personalization frontmatter 'confidence' is not a list; ignoring.",
        )
        return PersonalizationDoc(confidence=[], body=body)

    confidence: list[RuleConfidence] = []
    for idx, entry in enumerate(raw_confidence):
        if not isinstance(entry, dict):
            logger.warning("Skipping non-mapping confidence entry at index %d.", idx)
            continue
        try:
            confidence.append(RuleConfidence.model_validate(entry))
        except ValidationError as exc:
            logger.warning("Skipping invalid confidence entry at index %d: %s", idx, exc)

    return PersonalizationDoc(confidence=confidence, body=body)


def annotate_tentative(doc: PersonalizationDoc) -> str:
    """Render the body with ``(tentative)`` appended to bullets marked ``low``.

    The annotation is appended only once per matching bullet (idempotent).
    Bullets are matched by exact text equality with ``RuleConfidence.text``
    (ignoring leading ``-`` / ``*`` and surrounding whitespace).

    If no low-confidence rules are present, the body is returned unchanged.
    """
    low_texts = {r.text.strip() for r in doc.confidence if r.level == "low"}
    if not low_texts:
        return doc.body

    lines = doc.body.splitlines()
    out: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        bullet_match = re.match(r"^([-*])\s+(.*)$", stripped)
        if bullet_match is None:
            out.append(line)
            continue
        marker, content = bullet_match.group(1), bullet_match.group(2).rstrip()
        if content in low_texts and not content.endswith(TENTATIVE_SUFFIX):
            indent = line[: len(line) - len(stripped)]
            out.append(f"{indent}{marker} {content} {TENTATIVE_SUFFIX}")
        else:
            out.append(line)

    result = "\n".join(out)
    if doc.body.endswith("\n") and not result.endswith("\n"):
        result += "\n"
    return result
