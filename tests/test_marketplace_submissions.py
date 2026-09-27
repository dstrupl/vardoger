# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Regression checks for locally prepared marketplace submission artifacts."""

from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).parents[1]


def _load_script(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cline_marketplace_entry_keeps_safe_install_contract() -> None:
    """The prepared Cline entry must retain its validated install semantics."""
    entry_path = REPO_ROOT / "plugins/cline/submission/registry/mcps/vardoger/entry.json"
    entry = json.loads(entry_path.read_text(encoding="utf-8"))

    selected = {
        key: entry[key]
        for key in (
            "$schema",
            "id",
            "type",
            "tags",
            "license",
            "verified",
            "featured",
            "install",
        )
    }
    assert selected == {
        "$schema": "../../../schemas/mcp.schema.json",
        "id": "vardoger",
        "type": "mcp",
        "tags": ["memory", "productivity", "software"],
        "license": "Apache-2.0",
        "verified": False,
        "featured": False,
        "install": {
            "args": ["vardoger", "--", "uvx", "vardoger", "mcp"],
            "env": [
                {
                    "name": "VARDOGER_MCP_PLATFORM",
                    "required": True,
                    "description": (
                        "Set this value to cline so platform-optional Vardoger tools use "
                        "Cline history and Cline rules by default."
                    ),
                }
            ],
            "notes": (
                "When prompted for VARDOGER_MCP_PLATFORM, enter cline. Python 3.11 or "
                "newer and uvx are required. Vardoger proposes personalization for review "
                "before writing it."
            ),
        },
    }


def test_cursor_submission_references_package_files() -> None:
    """Every Cursor package path named in the recovery artifact must exist."""
    plugin_root = REPO_ROOT / "plugins/cursor"

    assert {
        path.relative_to(plugin_root).as_posix()
        for path in (
            plugin_root / "plugin.json",
            plugin_root / ".cursor-plugin/plugin.json",
            plugin_root / "mcp.json",
            plugin_root / "assets/logo.svg",
        )
        if path.is_file()
    } == {
        "plugin.json",
        ".cursor-plugin/plugin.json",
        "mcp.json",
        "assets/logo.svg",
    }


def test_codex_submission_builder_creates_only_reviewed_files(tmp_path: Path) -> None:
    """The public upload must be reproducible and exclude reviewer fixtures."""
    builder = _load_script(REPO_ROOT / "scripts/build-codex-submission.py")
    output = tmp_path / "vardoger.zip"

    version = builder.validate_submission()
    first_digest = builder.build_archive(output)
    first_bytes = output.read_bytes()
    second_digest = builder.build_archive(output)

    assert version
    assert first_digest == second_digest
    assert output.read_bytes() == first_bytes
    with zipfile.ZipFile(output) as archive:
        assert archive.namelist() == [
            "plugin.json",
            ".codex-plugin/plugin.json",
            "skills/analyze/SKILL.md",
            "assets/logo.png",
        ]


def test_copilot_upstream_entry_matches_portable_package() -> None:
    """The prepared upstream entry must track the externally hosted package."""
    entry = json.loads(
        (REPO_ROOT / "plugins/copilot/submission/marketplace-entry.json").read_text(
            encoding="utf-8"
        )
    )
    portable = json.loads((REPO_ROOT / "plugins/copilot/plugin.json").read_text(encoding="utf-8"))
    compatibility = json.loads(
        (REPO_ROOT / "plugins/copilot/.github/plugin/plugin.json").read_text(encoding="utf-8")
    )

    assert {
        key: entry[key] for key in ("name", "description", "version", "repository", "license")
    } == {
        key: portable[key] for key in ("name", "description", "version", "repository", "license")
    }
    assert entry["homepage"] == "https://github.com/dstrupl/vardoger/tree/main/plugins/copilot"
    assert compatibility["version"] == portable["version"]
    assert entry["source"] == {
        "source": "github",
        "repo": "dstrupl/vardoger",
        "path": "plugins/copilot",
    }
