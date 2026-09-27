#!/usr/bin/env python3
# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Validate and build the OpenAI skills-only submission archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
import tomllib
import zipfile
from pathlib import Path
from typing import Any, Never

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = REPO_ROOT / "plugins" / "codex"
PORTABLE_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
PACKAGE_MEMBERS = (
    Path("plugin.json"),
    Path(".codex-plugin/plugin.json"),
    Path("skills/analyze/SKILL.md"),
    Path("assets/logo.png"),
)
FINAL_DISPLAY_NAME_MAX = 30
FINAL_SHORT_DESCRIPTION_MAX = 30
FINAL_DEVELOPER_NAME_MAX = 80
DETERMINISTIC_TIMESTAMP = (2026, 1, 1, 0, 0, 0)
PNG_HEADER_BYTES = 24
POSITIVE_TEST_COUNT = 5
NEGATIVE_TEST_COUNT = 3


class SubmissionError(ValueError):
    """The prepared Codex submission does not meet its local contract."""


def _fail(message: str) -> Never:
    raise SubmissionError(message)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        _fail(f"expected a JSON object: {path}")
    return value


def _project_version() -> str:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:PNG_HEADER_BYTES]
    if len(data) != PNG_HEADER_BYTES or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        _fail(f"not a valid PNG header: {path}")
    return struct.unpack(">II", data[16:PNG_HEADER_BYTES])


def _validate_manifests(
    portable: dict[str, Any], overlay: dict[str, Any], version: str
) -> dict[str, Any]:
    if portable.get("$schema") != PORTABLE_SCHEMA:
        _fail("plugin.json does not declare the Agent Plugins 1.0 schema")
    if portable.get("name") != "vardoger" or overlay.get("name") != "vardoger":
        _fail("portable and OpenAI manifests must both identify vardoger")
    if portable.get("version") != version or overlay.get("version") != version:
        _fail("Codex manifest versions must match pyproject.toml")

    interface = overlay.get("interface")
    if not isinstance(interface, dict):
        _fail(".codex-plugin/plugin.json must contain an interface object")
    return interface


def _validate_interface(interface: dict[str, Any]) -> None:
    text_limits = {
        "displayName": FINAL_DISPLAY_NAME_MAX,
        "shortDescription": FINAL_SHORT_DESCRIPTION_MAX,
        "developerName": FINAL_DEVELOPER_NAME_MAX,
    }
    for field, limit in text_limits.items():
        value = interface.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            _fail(f"interface.{field} must contain 1-{limit} characters")

    required_urls = {
        "websiteURL": "https://github.com/dstrupl/vardoger",
        "supportURL": "https://github.com/dstrupl/vardoger/issues",
        "privacyPolicyURL": "https://github.com/dstrupl/vardoger/blob/main/PRIVACY.md",
        "termsOfServiceURL": "https://github.com/dstrupl/vardoger/blob/main/TERMS.md",
    }
    for field, expected in required_urls.items():
        if interface.get(field) != expected:
            _fail(f"interface.{field} must equal {expected}")

    if interface.get("composerIcon") != "./assets/logo.png":
        _fail("interface.composerIcon must reference ./assets/logo.png")
    if interface.get("logo") != "./assets/logo.png":
        _fail("interface.logo must reference ./assets/logo.png")


def _validate_assets_skill_and_tests() -> None:
    if _png_dimensions(PLUGIN_ROOT / "assets/logo.png") != (400, 400):
        _fail("assets/logo.png must be a 400x400 PNG")

    skill = (PLUGIN_ROOT / "skills/analyze/SKILL.md").read_text(encoding="utf-8")
    if not skill.startswith("---\nname: analyze\ndescription:"):
        _fail("the analyze skill must have name and description frontmatter")

    tests = (PLUGIN_ROOT / "submission/TEST_CASES.md").read_text(encoding="utf-8")
    positive = re.findall(r"^### Positive \d+", tests, flags=re.MULTILINE)
    negative = re.findall(r"^### Negative \d+", tests, flags=re.MULTILINE)
    if len(positive) != POSITIVE_TEST_COUNT or len(negative) != NEGATIVE_TEST_COUNT:
        _fail("review materials must contain five positive and three negative tests")


def validate_submission() -> str:
    """Validate package identity, OpenAI listing metadata, assets, and tests."""
    missing = [
        member.as_posix() for member in PACKAGE_MEMBERS if not (PLUGIN_ROOT / member).is_file()
    ]
    if missing:
        _fail(f"missing package members: {', '.join(missing)}")

    portable = _read_json(PLUGIN_ROOT / "plugin.json")
    overlay = _read_json(PLUGIN_ROOT / ".codex-plugin/plugin.json")
    version = _project_version()

    interface = _validate_manifests(portable, overlay, version)
    _validate_interface(interface)
    _validate_assets_skill_and_tests()

    return version


def build_archive(output: Path) -> str:
    """Write a deterministic archive and return its SHA-256 digest."""
    validate_submission()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for member in PACKAGE_MEMBERS:
            info = zipfile.ZipInfo(member.as_posix(), DETERMINISTIC_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (PLUGIN_ROOT / member).read_bytes())
    return hashlib.sha256(output.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate the package without writing an archive.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Archive path; defaults to dist/vardoger-codex-submission-<version>.zip.",
    )
    args = parser.parse_args(argv)

    try:
        version = validate_submission()
        if args.check:
            print(f"Codex submission package is valid for Vardoger {version}.")
            return 0

        output = args.output or REPO_ROOT / "dist" / f"vardoger-codex-submission-{version}.zip"
        digest = build_archive(output)
    except (KeyError, OSError, ValueError, json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
        sys.stderr.write(f"Codex submission validation failed: {exc}\n")
        return 1

    print(f"Wrote {output} (sha256: {digest})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
