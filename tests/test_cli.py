# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Tests for the vardoger command-line interface.

Covers every subcommand in :mod:`vardoger.cli` by driving :func:`main` end
to end. Platform history readers and the platform setup paths are isolated
via fixtures in ``conftest.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vardoger import __version__
from vardoger.checkpoint import CheckpointStore, content_hash
from vardoger.cli import _save_checkpoint, main
from vardoger.history.models import Conversation, Message
from vardoger.models import (
    CodexMarketplace,
    CodexPluginManifest,
    MarketplaceInterface,
    MarketplacePlugin,
    MarketplacePluginPolicy,
    MarketplacePluginSource,
)
from vardoger.setup import CODEX_PLUGIN_MANIFEST


def test_main_with_no_command_prints_help_and_exits(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "vardoger" in captured.out


# ---------------------------------------------------------------------------
# setup
# ---------------------------------------------------------------------------


def test_setup_cursor_writes_mcp_config(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["setup", "cursor"])
    mcp_config = fake_home / ".cursor" / "mcp.json"
    assert mcp_config.is_file()
    config = json.loads(mcp_config.read_text())
    assert "vardoger" in config["mcpServers"]
    output = capsys.readouterr().out
    assert "Registered vardoger" in output
    assert ".cursor/rules/vardoger.mdc" in output


def test_setup_claude_code_creates_plugin_dir(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["setup", "claude-code"])
    plugin_dir = fake_home / ".vardoger" / "plugins" / "claude-code"
    assert (plugin_dir / ".claude-plugin" / "plugin.json").is_file()
    assert (plugin_dir / "skills" / "analyze" / "SKILL.md").is_file()
    assert "Created Claude Code plugin" in capsys.readouterr().out


def test_setup_codex_creates_plugin_and_marketplace(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["setup", "codex"])
    plugin_dir = fake_home / ".codex" / "plugins" / "vardoger"
    marketplace = fake_home / ".agents" / "plugins" / "marketplace.json"
    manifest_path = plugin_dir / ".codex-plugin" / "plugin.json"
    assert manifest_path.is_file()
    assert marketplace.is_file()

    manifest = json.loads(manifest_path.read_text())
    assert manifest["name"] == "vardoger"
    assert manifest["version"]
    interface = manifest["interface"]
    assert interface["displayName"] == "Vardoger"
    assert interface["shortDescription"]
    assert interface["longDescription"]
    assert interface["developerName"]
    assert interface["category"]
    assert interface["privacyPolicyURL"].endswith("/PRIVACY.md")
    assert interface["defaultPrompt"] == [
        "Analyze my Codex history and personalize how you work with me.",
        "Show what you have learned about my working preferences.",
        "Refresh my Vardoger personalization from recent conversations.",
    ]

    data = json.loads(marketplace.read_text())
    assert data.get("interface", {}).get("displayName")
    entry = next(p for p in data["plugins"] if p["name"] == "vardoger")
    assert entry["source"]["path"] == "./.codex/plugins/vardoger"
    assert entry["source"]["source"] == "local"
    assert entry["policy"]["installation"] == "AVAILABLE"
    assert entry["policy"]["authentication"] == "ON_INSTALL"
    assert entry["category"]
    assert "Created Codex plugin" in capsys.readouterr().out


def test_tracked_codex_plugin_matches_setup_template() -> None:
    repo_root = Path(__file__).parents[1]
    manifest_path = repo_root / "plugins" / "codex" / ".codex-plugin" / "plugin.json"

    assert CodexPluginManifest.model_validate_json(manifest_path.read_text()) == (
        CODEX_PLUGIN_MANIFEST
    )


def test_tracked_codex_marketplace_points_to_plugin() -> None:
    repo_root = Path(__file__).parents[1]
    marketplace_path = repo_root / ".agents" / "plugins" / "marketplace.json"
    marketplace = CodexMarketplace.model_validate_json(marketplace_path.read_text())

    assert marketplace == CodexMarketplace(
        name="vardoger",
        interface=MarketplaceInterface(displayName="Vardoger"),
        plugins=[
            MarketplacePlugin(
                name="vardoger",
                source=MarketplacePluginSource(source="local", path="./plugins/codex"),
                policy=MarketplacePluginPolicy(
                    installation="AVAILABLE",
                    authentication="ON_INSTALL",
                ),
                category="Productivity",
            )
        ],
    )
    assert (repo_root / "plugins" / "codex" / ".codex-plugin" / "plugin.json").is_file()


def test_setup_openclaw_installs_skill(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["setup", "openclaw"])
    skill = fake_home / ".openclaw" / "skills" / "vardoger" / "skills" / "analyze" / "SKILL.md"
    assert skill.is_file()
    assert "Installed vardoger skill" in capsys.readouterr().out


def test_setup_copilot_prepares_instructions(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["setup", "copilot"])
    instructions = fake_home / ".copilot" / "copilot-instructions.md"
    assert instructions.is_file()
    assert "vardoger" in instructions.read_text()
    assert "Prepared Copilot instructions" in capsys.readouterr().out


def test_setup_copilot_preserves_existing_instructions(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    instructions = fake_home / ".copilot" / "copilot-instructions.md"
    instructions.parent.mkdir(parents=True)
    instructions.write_text("# Team rules\n\nKeep.\n")
    main(["setup", "copilot"])
    assert "Keep." in instructions.read_text()


def test_setup_copilot_honors_copilot_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    configured_home = tmp_path / "custom-copilot"
    monkeypatch.setenv("COPILOT_HOME", str(configured_home))

    main(["setup", "copilot"])

    instructions = configured_home / "copilot-instructions.md"
    assert instructions.is_file()
    assert str(instructions) in capsys.readouterr().out


def test_setup_windsurf_prepares_rules(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["setup", "windsurf"])
    rules = fake_home / ".codeium" / "windsurf" / "memories" / "global_rules.md"
    skill = fake_home / ".codeium" / "windsurf" / "skills" / "vardoger-analyze" / "SKILL.md"
    assert rules.is_file()
    assert skill.is_file()
    assert "name: vardoger-analyze" in skill.read_text(encoding="utf-8")
    out = capsys.readouterr().out
    assert "Prepared Windsurf global rules" in out
    assert "Installed Windsurf skill" in out


def test_setup_cline_prepares_global_rules(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["setup", "cline"])
    assert (fake_home / "Documents" / "Cline" / "Rules").is_dir()
    out = capsys.readouterr().out
    assert "Prepared Cline global rules" in out
    assert ".clinerules" in out


def test_setup_devin_prepares_supported_surfaces(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["setup", "devin"])

    assert (fake_home / ".vardoger" / "imports" / "devin").is_dir()
    assert (fake_home / ".config" / "devin" / "AGENTS.md").is_file()
    skill = fake_home / ".config" / "devin" / "skills" / "analyze" / "SKILL.md"
    assert skill.is_file()
    assert "--export ~/.vardoger/imports/devin/" in skill.read_text(encoding="utf-8")
    assert "devin --export" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("platform", "skill_path_parts"),
    [
        ("claude-code", (".vardoger", "plugins", "claude-code", "skills", "analyze", "SKILL.md")),
        ("codex", (".codex", "plugins", "vardoger", "skills", "analyze", "SKILL.md")),
        (
            "openclaw",
            (".openclaw", "skills", "vardoger", "skills", "analyze", "SKILL.md"),
        ),
        (
            "windsurf",
            (
                ".codeium",
                "windsurf",
                "skills",
                "vardoger-analyze",
                "SKILL.md",
            ),
        ),
        ("devin", (".config", "devin", "skills", "analyze", "SKILL.md")),
    ],
)
def test_setup_skill_has_valid_frontmatter(
    platform: str,
    skill_path_parts: tuple[str, ...],
    fake_home: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Generated skills need frontmatter so each host can discover them."""
    main(["setup", platform])
    capsys.readouterr()
    skill = fake_home.joinpath(*skill_path_parts)
    text = skill.read_text(encoding="utf-8")

    lines = text.splitlines()
    assert lines[0] == "---", f"expected frontmatter fence, got: {lines[0]!r}"
    closing_idx = lines.index("---", 1)
    frontmatter = "\n".join(lines[1:closing_idx])

    expected_skill_name = "vardoger-analyze" if platform == "windsurf" else "analyze"
    assert f"name: {expected_skill_name}" in frontmatter
    assert "description:" in frontmatter
    assert "personalize" in frontmatter
    assert "vardoger" in frontmatter
    if platform == "openclaw":
        assert f'version: "{__version__}"' in frontmatter
        assert "license: Apache-2.0" in frontmatter
        assert "openclaw:" in frontmatter
        assert "- vardoger" in frontmatter

    # The "vardoger CLI not installed" guard must give the user actionable
    # install instructions, not just "install with pipx install vardoger".
    # Marketplace users may not have pipx on PATH, so document uvx too.
    assert "pipx install vardoger" in text
    assert "uvx vardoger" in text
    assert "pipx.pypa.io" in text
    assert "github.com/dstrupl/vardoger" in text

    # The skill must warn hosts up-front that vardoger writes outside the
    # workspace. Otherwise sandboxed shells (Codex, Claude Code) surface a
    # scary mid-flow PermissionError on ~/.vardoger/state.tmp before
    # prompting the user for the right permission.
    assert "Sandbox note" in text
    assert "outside" in text
    assert "~/.vardoger/state.json" in text


# ---------------------------------------------------------------------------
# status & hook
# ---------------------------------------------------------------------------


def test_status_default_covers_all_platforms(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["status"])
    out = capsys.readouterr().out
    for platform in (
        "cursor",
        "claude-code",
        "codex",
        "openclaw",
        "copilot",
        "windsurf",
        "cline",
        "devin",
    ):
        assert platform in out
    assert out.count("never generated") >= 8


def test_status_single_platform_json(fake_home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(["status", "--platform", "cursor", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert len(payload) == 1
    assert payload[0]["platform"] == "cursor"
    assert payload[0]["is_stale"] is True


def test_hook_session_start_emits_json_when_stale(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["_hook-session-start", "cursor"])
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert "hookSpecificOutput" in payload
    assert "vardoger" in payload["hookSpecificOutput"]["additionalContext"]


def test_hook_session_start_silent_when_fresh(
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = CheckpointStore()
    store.record_generation("cursor", conversations_analyzed=1, output_path="/tmp/out")
    store.save()
    monkeypatch.setattr("vardoger.staleness._discover_files", lambda _p: [])
    main(["_hook-session-start", "cursor"])
    assert capsys.readouterr().out == ""


# ---------------------------------------------------------------------------
# analyze (legacy)
# ---------------------------------------------------------------------------


def test_analyze_writes_personalization(
    fake_home: Path,
    project_cwd: Path,
    patch_history_readers: object,
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["analyze", "--platform", "cursor", "--full"])
    rules = project_cwd / ".cursor" / "rules" / "vardoger.mdc"
    assert rules.is_file()
    out = capsys.readouterr().out
    assert "wrote personalization" in out
    assert "conversations" in out


def test_analyze_writes_copilot_personalization(
    fake_home: Path,
    project_cwd: Path,
    monkeypatch: pytest.MonkeyPatch,
    make_conversations,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "vardoger.history.copilot.read_copilot_history",
        lambda **_: make_conversations(),
    )
    main(["analyze", "--platform", "copilot", "--scope", "project", "--full"])
    rules = project_cwd / ".github" / "copilot-instructions.md"
    assert rules.is_file()
    assert "<!-- vardoger:start -->" in rules.read_text()
    assert "wrote personalization" in capsys.readouterr().out


def test_copilot_checkpoint_uses_copilot_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configured_home = tmp_path / "custom-copilot"
    event_log = configured_home / "session-state" / "session" / "events.jsonl"
    event_log.parent.mkdir(parents=True)
    event_log.write_text('{"type":"user.message","data":{"content":"Hi"}}\n')
    monkeypatch.setenv("COPILOT_HOME", str(configured_home))
    store = CheckpointStore(state_dir=tmp_path / "state")
    conversation = Conversation(
        messages=[Message(role="user", content="Hi")],
        platform="copilot",
        session_id="session",
        source_path="session/events.jsonl",
    )

    _save_checkpoint(store, [conversation], "copilot")

    assert store.get_checkpoint("copilot", "session/events.jsonl") is not None


def test_analyze_writes_windsurf_personalization(
    fake_home: Path,
    project_cwd: Path,
    monkeypatch: pytest.MonkeyPatch,
    make_conversations,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "vardoger.history.windsurf.read_windsurf_history",
        lambda **_: make_conversations(),
    )
    main(["analyze", "--platform", "windsurf", "--scope", "project", "--full"])
    rules = project_cwd / ".windsurf" / "rules" / "vardoger.md"
    assert rules.is_file()


def test_analyze_writes_cline_personalization(
    fake_home: Path,
    project_cwd: Path,
    monkeypatch: pytest.MonkeyPatch,
    make_conversations,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "vardoger.history.cline.read_cline_history",
        lambda **_: make_conversations(),
    )
    main(["analyze", "--platform", "cline", "--scope", "project", "--full"])
    rules = project_cwd / ".clinerules"
    assert rules.is_file()
    assert "<!-- vardoger:start -->" in rules.read_text()


def test_analyze_writes_global_cline_personalization_by_default(
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    make_conversations,
) -> None:
    monkeypatch.setattr(
        "vardoger.history.cline.read_cline_history",
        lambda **_: make_conversations(),
    )

    main(["analyze", "--platform", "cline", "--full"])

    rules = fake_home / "Documents" / "Cline" / "Rules" / "vardoger.md"
    assert rules.is_file()


def test_analyze_no_conversations(
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("vardoger.cli.read_cursor_history", lambda **_: [])
    main(["analyze", "--platform", "cursor", "--full"])
    assert "No conversation history" in capsys.readouterr().out


def test_prepare_openclaw_sqlite_backend_exits_cleanly(
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from vardoger.history.openclaw import UnsupportedOpenClawHistoryError

    def _unsupported(**_kwargs: object) -> list:
        message = "OpenClaw 2.0 SQLite history detected."
        raise UnsupportedOpenClawHistoryError(message)

    monkeypatch.setattr("vardoger.history.openclaw.read_openclaw_history", _unsupported)

    with pytest.raises(SystemExit) as exc:
        main(["prepare", "--platform", "openclaw", "--full"])

    assert exc.value.code == 2
    assert capsys.readouterr().err == ("vardoger: OpenClaw 2.0 SQLite history detected.\n")


# ---------------------------------------------------------------------------
# prepare
# ---------------------------------------------------------------------------


def test_prepare_metadata_only(
    fake_home: Path,
    patch_history_readers: object,
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["prepare", "--platform", "cursor", "--full"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["batches"] == 1
    assert payload["total_conversations"] == 2


def test_prepare_returns_batch_text(
    fake_home: Path,
    patch_history_readers: object,
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["prepare", "--platform", "cursor", "--batch", "1", "--full"])
    out = capsys.readouterr().out
    assert "Conversation Batch 1 of 1" in out
    assert "---" in out


def test_prepare_batch_out_of_range(
    fake_home: Path,
    patch_history_readers: object,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["prepare", "--platform", "cursor", "--batch", "99", "--full"])
    assert exc.value.code == 1
    assert "out of range" in capsys.readouterr().err


def test_prepare_synthesize_without_feedback(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["prepare", "--platform", "cursor", "--synthesize"])
    out = capsys.readouterr().out
    assert "synthesize" in out.lower() or "synthesis" in out.lower()


def test_prepare_synthesize_with_feedback_prepends_context(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    store = CheckpointStore()
    record = store.get_feedback("cursor")
    record.kept_rules = ["keep this"]
    record.removed_rules = ["drop this"]
    record.added_rules = ["new thing"]
    store.save()

    main(["prepare", "--platform", "cursor", "--synthesize"])
    out = capsys.readouterr().out
    assert "keep this" in out
    assert "drop this" in out
    assert "new thing" in out


def test_prepare_no_conversations_prints_json_zero(
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("vardoger.cli.read_cursor_history", lambda **_: [])
    main(["prepare", "--platform", "cursor", "--full"])
    captured = capsys.readouterr()
    assert '"batches": 0' in captured.out
    assert "No conversation history" in captured.err


def test_prepare_only_checkpoints_after_final_batch(
    fake_home: Path,
    make_conversations: object,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Iterating through batches must not checkpoint mid-way.

    Historical bug: saving the checkpoint on every ``--batch N`` meant the next
    ``prepare --batch N+1`` call saw a smaller (filtered) history and reported
    a different total batch count, rejecting later batches as out-of-range.
    Only the final batch in the iteration should trigger the checkpoint save.
    """
    import vardoger.cli as cli_mod

    convs = make_conversations(count=15)  # type: ignore[operator]
    monkeypatch.setattr("vardoger.cli.read_cursor_history", lambda **_: convs)

    calls: list[int] = []
    original = cli_mod._save_checkpoint

    def spy(ckpt: object, convos: list, platform: str) -> None:
        calls.append(len(convos) if convos else 0)
        original(ckpt, convos, platform)

    monkeypatch.setattr("vardoger.cli._save_checkpoint", spy)

    main(["prepare", "--platform", "cursor"])
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"batches": 2, "total_conversations": 15}
    assert calls == []

    main(["prepare", "--platform", "cursor", "--batch", "1"])
    capsys.readouterr()
    assert calls == []

    main(["prepare", "--platform", "cursor", "--batch", "2"])
    capsys.readouterr()
    assert calls == [15]


# ---------------------------------------------------------------------------
# write
# ---------------------------------------------------------------------------


def test_write_persists_stdin_content(
    fake_home: Path,
    project_cwd: Path,
    stdin_feeder,
    capsys: pytest.CaptureFixture[str],
) -> None:
    stdin_feeder("# Personalization\n\n- do things well\n")
    main(["write", "--platform", "cursor"])
    rules = project_cwd / ".cursor" / "rules" / "vardoger.mdc"
    assert rules.is_file()
    assert "- do things well" in rules.read_text()
    assert "wrote personalization" in capsys.readouterr().out

    store = CheckpointStore()
    record = store.get_generation("cursor")
    assert record is not None
    assert record.output_hash == content_hash(rules.read_text().split("---\n")[-1].lstrip("\n"))


def test_write_requires_stdin(
    fake_home: Path,
    project_cwd: Path,
    stdin_feeder,
    capsys: pytest.CaptureFixture[str],
) -> None:
    stdin_feeder("   \n\n")
    with pytest.raises(SystemExit) as exc:
        main(["write", "--platform", "cursor"])
    assert exc.value.code == 1
    assert "No content" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# feedback
# ---------------------------------------------------------------------------


def test_feedback_accept_records_event(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["feedback", "accept", "--platform", "cursor", "--reason", "looks good"])
    assert "recorded accept" in capsys.readouterr().out

    store = CheckpointStore()
    record = store.get_feedback("cursor")
    assert any(e.kind == "accept" and e.summary == "looks good" for e in record.events)


def test_feedback_reject_reverts_to_previous(
    fake_home: Path,
    project_cwd: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from vardoger.writers.cursor import write_cursor_rules

    first_body = "- prior rule\n"
    second_body = "- later rule\n"
    write_cursor_rules(first_body, project_path=project_cwd)
    store = CheckpointStore()
    store.record_generation(
        "cursor",
        conversations_analyzed=1,
        output_path=str(project_cwd / ".cursor" / "rules" / "vardoger.mdc"),
        content=first_body,
    )
    store.record_generation(
        "cursor",
        conversations_analyzed=1,
        output_path=str(project_cwd / ".cursor" / "rules" / "vardoger.mdc"),
        content=second_body,
    )
    store.save()

    main(["feedback", "reject", "--platform", "cursor", "--project", str(project_cwd)])
    out = capsys.readouterr().out
    assert "reverted cursor" in out

    rules = (project_cwd / ".cursor" / "rules" / "vardoger.mdc").read_text()
    assert "prior rule" in rules
    assert "later rule" not in rules


def test_feedback_reject_clears_when_no_prior_generation(
    fake_home: Path,
    project_cwd: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from vardoger.writers.cursor import write_cursor_rules

    write_cursor_rules("- only rule\n", project_path=project_cwd)
    store = CheckpointStore()
    store.record_generation(
        "cursor",
        conversations_analyzed=1,
        output_path=str(project_cwd / ".cursor" / "rules" / "vardoger.mdc"),
        content="- only rule\n",
    )
    store.save()

    main(["feedback", "reject", "--platform", "cursor", "--project", str(project_cwd)])
    out = capsys.readouterr().out
    assert "cleared cursor personalization" in out
    assert not (project_cwd / ".cursor" / "rules" / "vardoger.mdc").is_file()


def test_feedback_reject_without_any_history(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["feedback", "reject", "--platform", "cursor"])
    err = capsys.readouterr().err
    assert "nothing to revert" in err


# ---------------------------------------------------------------------------
# compare
# ---------------------------------------------------------------------------


def test_compare_never_personalized_prints_caveat(
    fake_home: Path,
    patch_history_readers: object,
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["compare", "--platform", "cursor"])
    out = capsys.readouterr().out
    assert "platform: cursor" in out
    assert "never personalized" in out


def test_compare_all_json_lists_every_platform(
    fake_home: Path,
    patch_history_readers: object,
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["compare", "--all", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert {c["platform"] for c in payload} == {
        "cursor",
        "claude-code",
        "codex",
        "openclaw",
        "copilot",
        "windsurf",
        "cline",
        "devin",
    }


def test_compare_emits_metric_rows_when_personalized(
    fake_home: Path,
    patch_history_readers: object,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Record a generation with a cutoff far in the past so the fake
    # conversations (no timestamps) all fall into the "after" bucket.
    from datetime import UTC, datetime, timedelta

    store = CheckpointStore()
    store._state.generations["cursor"] = []
    store.record_generation(
        "cursor",
        conversations_analyzed=1,
        output_path="/tmp/out",
        content="- rule\n",
    )
    store._state.generations["cursor"][-1].generated_at = (
        datetime.now(UTC) - timedelta(days=365)
    ).isoformat()
    store.save()

    main(["compare", "--platform", "cursor"])
    out = capsys.readouterr().out
    assert "cutoff" in out
    # With no messages in the before bucket we expect a caveat but the
    # comparison itself should still print platform + cutoff lines.
    assert "platform: cursor" in out


# ---------------------------------------------------------------------------
# profile
# ---------------------------------------------------------------------------


def test_profile_sources_lists_stable_generation_ids(
    fake_home: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = CheckpointStore()
    store.record_generation(
        "codex",
        conversations_analyzed=3,
        output_path="/tmp/generated",
        content="- Use pytest\n",
    )
    store.save()

    main(["profile", "sources", "--platform", "codex", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["platform"] == "codex"
    assert payload[0]["generation"] == 1
    assert payload[0]["conversations_analyzed"] == 3


def test_profile_preview_is_read_only_and_shows_diff(
    fake_home: Path,
    project_cwd: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = CheckpointStore()
    store.record_generation(
        "codex",
        conversations_analyzed=1,
        output_path="/tmp/generated",
        content="## Testing\n- Use pytest\n",
    )
    store.save()
    target = project_cwd / "AGENTS.md"
    target.write_text("# Existing\n\nKeep this.\n")

    main(
        [
            "profile",
            "preview",
            "--source",
            "codex:latest",
            "--target",
            str(target),
        ]
    )

    output = capsys.readouterr().out
    assert "- Use pytest" in output
    assert "Proposed diff" in output
    assert target.read_text() == "# Existing\n\nKeep this.\n"


def test_profile_write_requires_apply_and_preserves_existing_content(
    fake_home: Path,
    project_cwd: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = CheckpointStore()
    store.record_generation(
        "claude_code",
        conversations_analyzed=1,
        output_path="/tmp/generated",
        content="## Workflow\n- Keep commits focused\n",
    )
    store.save()
    target = project_cwd / "AGENTS.md"
    target.write_text("# Repository rules\n\nPreserve me.\n")
    base_args = [
        "profile",
        "write",
        "--source",
        "claude-code:1",
        "--target",
        str(target),
    ]

    main(base_args)
    captured = capsys.readouterr()
    assert "preview only" in captured.err
    assert "Keep commits focused" not in target.read_text()

    main([*base_args, "--apply"])
    assert "Preserve me." in target.read_text()
    assert "Keep commits focused" in target.read_text()
    assert "vardoger-profile:start" in target.read_text()


def test_profile_preview_json_includes_provenance(
    fake_home: Path,
    project_cwd: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = CheckpointStore()
    store.record_generation(
        "cursor",
        conversations_analyzed=1,
        output_path="/tmp/generated",
        content="- Prefer concise answers\n",
    )
    store.save()

    main(
        [
            "profile",
            "preview",
            "--source",
            "cursor:1",
            "--target",
            str(project_cwd / "AGENTS.md"),
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["sources"] == [{"platform": "cursor", "generation": 1}]
    assert payload["preferences"][0]["evidence"][0]["platform"] == "cursor"
