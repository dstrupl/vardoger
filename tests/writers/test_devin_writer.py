# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for Devin's global and project rule writer."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from vardoger.writers.devin import clear_devin_rules, read_devin_rules, write_devin_rules


def test_global_rules_preserve_user_content(tmp_path: Path) -> None:
    agents = tmp_path / ".config" / "devin" / "AGENTS.md"
    agents.parent.mkdir(parents=True)
    agents.write_text("# Personal rules\n\nKeep me.\n", encoding="utf-8")

    with patch("vardoger.writers.devin.Path.home", return_value=tmp_path):
        output = write_devin_rules("- Prefer focused tests")
        write_devin_rules("- Prefer complete-object assertions")
        content = read_devin_rules()

    assert output == agents
    assert "Keep me." in agents.read_text(encoding="utf-8")
    assert agents.read_text(encoding="utf-8").count("<!-- vardoger:start -->") == 1
    assert content == "- Prefer complete-object assertions"


def test_project_rules_use_documented_devin_surface(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / ".git").mkdir(parents=True)

    output = write_devin_rules("- Run tests", scope="project", project_path=project)

    assert output == project / ".devin" / "rules" / "vardoger.md"
    assert "trigger: always_on" in output.read_text(encoding="utf-8")
    assert read_devin_rules(scope="project", project_path=project) == "- Run tests"
    assert clear_devin_rules(scope="project", project_path=project) is True
    assert not output.exists()


def test_clear_global_removes_only_managed_section(tmp_path: Path) -> None:
    with patch("vardoger.writers.devin.Path.home", return_value=tmp_path):
        write_devin_rules("- Generated")
        agents = tmp_path / ".config" / "devin" / "AGENTS.md"
        agents.write_text("# User\n\nKeep.\n\n" + agents.read_text(encoding="utf-8"))
        assert clear_devin_rules() is True

    assert agents.read_text(encoding="utf-8") == "# User\n\nKeep.\n"
