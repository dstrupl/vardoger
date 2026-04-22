# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""MCP server for vardoger — usable from any MCP-capable client.

Exposes vardoger's analysis pipeline as MCP tools that operate on any
supported platform (Cursor, Claude Code, Codex, OpenClaw, Copilot CLI,
Windsurf, or Cline). Each tool takes an optional ``platform`` argument; if
omitted, the server resolves the default platform in this order:

1. the ``VARDOGER_MCP_PLATFORM`` environment variable, or
2. ``"cursor"`` (preserved for backwards compatibility with clients
   installed before this became configurable).

Tools exposed:
  - vardoger_personalize() — entry point: returns orchestration instructions
  - vardoger_status()       — reports staleness of the target platform
  - vardoger_prepare()      — returns batch metadata or batch content
  - vardoger_synthesize_prompt() — returns the synthesis prompt
  - vardoger_write()        — writes the final personalization
  - vardoger_preview()      — shows a unified diff without touching files
  - vardoger_feedback()     — records accept/reject and can revert
  - vardoger_compare()      — A/B conversation quality around last generation

The host AI model performs the actual analysis between prepare and write;
the server only handles file I/O and state bookkeeping.

Usage (direct):
    python -m vardoger.mcp_server
"""

from __future__ import annotations

import functools
import importlib
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from vardoger import __version__ as _VARDOGER_VERSION
from vardoger.digest import batch_conversations, format_batch
from vardoger.feedback import detect_edits
from vardoger.history.cursor import read_cursor_history
from vardoger.history.models import Conversation
from vardoger.personalization import annotate_tentative, parse_personalization
from vardoger.prompts import feedback_context_prompt, summarize_prompt, synthesize_prompt
from vardoger.staleness import check_staleness

mcp = FastMCP("vardoger")
# FastMCP (as of mcp SDK 1.27) does not expose a ``version`` kwarg, but the
# underlying low-level ``Server`` reads ``self.version`` when building the
# ``initialize`` response. Propagate vardoger's own version so clients see
# "vardoger X.Y.Z" in their MCP panel instead of the bundled SDK version.
# Regression for https://github.com/dstrupl/vardoger/issues/13.
mcp._mcp_server.version = _VARDOGER_VERSION

# ---------------------------------------------------------------------------
# Platform registry
# ---------------------------------------------------------------------------

PLATFORM_CHOICES: tuple[str, ...] = (
    "cursor",
    "claude-code",
    "codex",
    "openclaw",
    "copilot",
    "windsurf",
    "cline",
)

PLATFORM_LABELS: dict[str, str] = {
    "cursor": "Cursor",
    "claude-code": "Claude Code",
    "codex": "Codex",
    "openclaw": "OpenClaw",
    "copilot": "GitHub Copilot CLI",
    "windsurf": "Windsurf",
    "cline": "Cline",
}

# ``CheckpointStore`` keys its platform dicts on the underscore variant so
# that JSON state files stay valid Python attribute-shaped strings. The CLI
# name (``claude-code``) and state key (``claude_code``) only diverge for
# Claude Code today, but we keep a full mapping for symmetry.
_STATE_KEY: dict[str, str] = {
    "cursor": "cursor",
    "claude-code": "claude_code",
    "codex": "codex",
    "openclaw": "openclaw",
    "copilot": "copilot",
    "windsurf": "windsurf",
    "cline": "cline",
}

# Cline has no user-global rules location; default to project scope so that
# ``vardoger_write(platform="cline")`` writes somewhere sensible without
# forcing every caller to pass ``scope``.
_DEFAULT_SCOPE: dict[str, str] = {
    "cursor": "global",
    "claude-code": "global",
    "codex": "global",
    "openclaw": "global",
    "copilot": "global",
    "windsurf": "global",
    "cline": "project",
}

_DEFAULT_PLATFORM_ENV = "VARDOGER_MCP_PLATFORM"


def _env_default_platform() -> str:
    """Resolve the default platform from the environment (evaluated per call).

    We look this up per invocation rather than caching at import time so
    test suites that patch ``os.environ`` mid-session see their new value.
    """
    candidate = os.environ.get(_DEFAULT_PLATFORM_ENV, "").strip()
    if candidate in PLATFORM_CHOICES:
        return candidate
    return "cursor"


def _resolve_platform(platform: str) -> tuple[str | None, str | None]:
    """Return (platform, None) on success or (None, error_message) on failure.

    An empty string resolves to the configured default. Unknown names are
    reported back to the caller rather than raised so the MCP client can
    surface the message to the user.
    """
    if not platform:
        return _env_default_platform(), None
    if platform in PLATFORM_CHOICES:
        return platform, None
    choices = ", ".join(PLATFORM_CHOICES)
    return None, (f"vardoger: unknown platform {platform!r}; expected one of {choices}.")


def _resolve_scope(platform: str, scope: str) -> str:
    return scope if scope else _DEFAULT_SCOPE[platform]


def _label(platform: str) -> str:
    return PLATFORM_LABELS.get(platform, platform)


# ---------------------------------------------------------------------------
# Per-platform dispatch. A single registry maps each CLI-style platform name
# to the fully qualified names of its reader/writer helpers; ``_resolve`` does
# the lazy import so we never drag a non-target platform's history code into
# memory just because the MCP server starts up.
# ---------------------------------------------------------------------------


class _PlatformLookupError(KeyError):
    """Raised when internal dispatch can't find a known platform."""


_HISTORY_READER_QUALNAMES: dict[str, str] = {
    "cursor": "vardoger.history.cursor:read_cursor_history",
    "claude-code": "vardoger.history.claude_code:read_claude_code_history",
    "codex": "vardoger.history.codex:read_codex_history",
    "openclaw": "vardoger.history.openclaw:read_openclaw_history",
    "copilot": "vardoger.history.copilot:read_copilot_history",
    "windsurf": "vardoger.history.windsurf:read_windsurf_history",
    "cline": "vardoger.history.cline:read_cline_history",
}


def _qualnames(prefix: str, suffix: str) -> dict[str, str]:
    """Build a qualname map for writers/readers/clearers.

    Writer functions share a naming convention: ``<prefix>_<platform>_<suffix>``
    living in ``vardoger.writers.<platform>``. ``claude-code`` uses an
    underscore in Python identifiers, hence the small normalization.
    """
    out: dict[str, str] = {}
    for platform in PLATFORM_CHOICES:
        module_slug = platform.replace("-", "_")
        out[platform] = f"vardoger.writers.{module_slug}:{prefix}_{module_slug}_{suffix}"
    return out


_WRITER_QUALNAMES: dict[str, str] = _qualnames("write", "rules")
_READER_QUALNAMES: dict[str, str] = _qualnames("read", "rules")
_CLEARER_QUALNAMES: dict[str, str] = _qualnames("clear", "rules")

# Cursor's writer predates the shared ``scope`` argument and doesn't accept
# it; these platforms need the scope keyword forwarded.
_WRITERS_TAKING_SCOPE: frozenset[str] = frozenset(
    {"claude-code", "codex", "openclaw", "copilot", "windsurf", "cline"}
)


@functools.cache
def _resolve_qualname(qualname: str) -> Any:
    """Import ``module:attr`` lazily and return the attribute."""
    module_name, attr = qualname.split(":", 1)
    return getattr(importlib.import_module(module_name), attr)


def _history_reader(platform: str) -> Callable[..., list[Conversation]]:
    """Return the ``read_<platform>_history`` callable for ``platform``."""
    if platform == "cursor":
        return read_cursor_history
    qualname = _HISTORY_READER_QUALNAMES.get(platform)
    if qualname is None:
        raise _PlatformLookupError(platform)
    reader: Callable[..., list[Conversation]] = _resolve_qualname(qualname)
    return reader


def _writer_kwargs(platform: str, scope: str, project_path: Path | None) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"project_path": project_path}
    if platform in _WRITERS_TAKING_SCOPE:
        kwargs["scope"] = scope
    return kwargs


def _write_rules(
    platform: str,
    content: str,
    scope: str,
    project_path: Path | None,
) -> Path:
    qualname = _WRITER_QUALNAMES.get(platform)
    if qualname is None:
        raise _PlatformLookupError(platform)
    writer = _resolve_qualname(qualname)
    result: Path = writer(content, **_writer_kwargs(platform, scope, project_path))
    return result


def _read_rules(
    platform: str,
    scope: str,
    project_path: Path | None,
) -> str | None:
    qualname = _READER_QUALNAMES.get(platform)
    if qualname is None:
        raise _PlatformLookupError(platform)
    reader = _resolve_qualname(qualname)
    kwargs: dict[str, Any] = {"project_path": project_path}
    if platform in _WRITERS_TAKING_SCOPE:
        kwargs["scope"] = scope
    result: str | None = reader(**kwargs)
    return result


def _clear_rules(
    platform: str,
    scope: str,
    project_path: Path | None,
) -> bool:
    qualname = _CLEARER_QUALNAMES.get(platform)
    if qualname is None:
        raise _PlatformLookupError(platform)
    clearer = _resolve_qualname(qualname)
    kwargs: dict[str, Any] = {"project_path": project_path}
    if platform in _WRITERS_TAKING_SCOPE:
        kwargs["scope"] = scope
    result: bool = clearer(**kwargs)
    return result


# ---------------------------------------------------------------------------
# Orchestration instructions
# ---------------------------------------------------------------------------

_ORCHESTRATION_TEMPLATE = """\
# vardoger — Personalize Your Assistant ({label})

Follow these steps to analyze the user's {label} conversation history and \
generate a personalization. Report progress to the user after each step.

Every tool below accepts an optional `platform` argument. Pass \
`platform="{platform}"` on every call in this session so the server keeps \
reading and writing {label} state consistently, even if its default is \
something else.

## Step 1: Check status

Call `vardoger_status(platform="{platform}")`.

If the personalization is fresh (not stale), tell the user their \
personalization is up to date and ask if they want to re-run anyway. \
If stale or never generated, continue.

## Step 2: Check for existing personalizations in other workspaces (Cursor only)

The personalization vardoger produces is derived from the user's *global* \
conversation history, not from the current project. A user who has already \
run vardoger in a different workspace may have a ready-made \
`.cursor/rules/vardoger.md` you can reuse instead of regenerating from \
scratch.

If the platform is Cursor and you know (from your session context, open \
editors, recent files, etc.) of other workspaces the user has, call \
`vardoger_import(paths=["/path/a", "/path/b", ...])` with them. The tool \
returns the content of any `vardoger.md` it finds. If it finds one, offer \
the user:
  (a) reuse that content as-is,
  (b) regenerate and merge with the existing content, or
  (c) discard and regenerate from history.

Otherwise continue with generation below.

## Step 3: Get batch metadata

Call `vardoger_prepare(platform="{platform}", batch=0)`.

This returns JSON like `{{"batches": 3, "total_conversations": 29}}`. \
Note the number of batches. Tell the user: "Found N conversations in M \
batches. Analyzing..."

## Step 4: Summarize each batch

For each batch from 1 to M, call \
`vardoger_prepare(platform="{platform}", batch=N)`.

The output contains a summarization prompt and conversation data. Read it \
carefully and produce a concise bullet-point summary of the behavioral \
signals you observe. Keep each summary for later.

Tell the user: "Analyzing batch N of M..."

## Step 5: Get the synthesis prompt

Call `vardoger_synthesize_prompt(platform="{platform}")`.

## Step 6: Synthesize

Following the synthesis prompt, combine all your batch summaries into a \
single personalization. The output should be clean markdown with actionable \
instructions.

## Step 7: Deliver the result

Because the personalization is derived from *global* conversation history, \
its natural home is Cursor's **User Rules** (Settings → Rules → User \
Rules), which apply across every project. The `vardoger_write` tool \
reflects this:

- Default — User Rules: call \
  `vardoger_write(platform="{platform}", content="YOUR_PERSONALIZATION_HERE")` \
  *without* a `project_path`. vardoger returns a copy-paste block the user \
  can drop into Settings → Rules → User Rules. No files are written. \
  Surface the returned block verbatim and encourage the user to edit it.
- Opt-in — project-scoped file: if (and only if) the user explicitly asks \
  for a project-specific rules file, call the same tool again with \
  `project_path="<workspace root>"`. vardoger will refuse to write outside \
  a directory that looks like a project, which is intentional — don't \
  fabricate paths.

## Step 8: Report to the user

Tell the user what was produced and which delivery mode was used. Mention \
they can ask you to re-run vardoger any time to update the personalization.
"""


def _orchestration_instructions(platform: str) -> str:
    return _ORCHESTRATION_TEMPLATE.format(platform=platform, label=_label(platform))


# Sentinel we stash in ``CheckpointStore.output_path`` when we generated a
# personalization without writing it into a Cursor-loaded location (the User
# Rules default). Keeps downstream code — staleness, feedback, compare — able
# to tell "generated for User Rules" from "generated and written to
# .cursor/rules". The deterministic helper-file copy (see
# ``_user_rules_copy_path``) is a convenience copy source, not where Cursor
# loads rules from, so we deliberately do NOT promote it to ``output_path``.
_USER_RULES_OUTPUT_SENTINEL = "(user-rules: no cursor-loaded file written)"


_USER_RULES_WRITE_TEMPLATE = """\
vardoger_write: personalization ready.

Saved a copy-source file to:
{copy_path}

To apply: cmd+click the path above to open it in an editor tab, copy the \
whole file, and paste it into Cursor → Settings → Rules → User Rules. \
Edit freely once pasted — the rules are starting points derived from your \
global conversation history, not commandments.

Why a copy-source file and not a .cursor/rules/ file? Cursor's User Rules \
apply across every project and live in Cursor's settings database, not on \
disk. The file above is just a convenience so you don't have to hunt for \
this block in the collapsed tool-call card; deleting it does not \
unpersonalize Cursor. Running ``vardoger_write`` again overwrites it with \
the latest generation.

If you'd rather also drop a project-scoped copy into a specific workspace's \
.cursor/rules/vardoger.md, re-run ``vardoger_write`` with \
``project_path="<your workspace root>"``. vardoger refuses to write into \
directories that don't look like projects (no .git, manifest, AGENTS.md, \
or .cursor/).

The same block is inlined below if you prefer copying it from here:

--- BEGIN vardoger personalization ---
{content}
--- END vardoger personalization ---
"""


_USER_RULES_PREVIEW_TEMPLATE = """\
vardoger_preview: no project_path given — vardoger_write would deliver this \
as a User Rules copy-paste block (nothing in ``.cursor/rules/`` would be \
touched).

It would save a copy-source file to:
{copy_path}
(that file is not read by Cursor — it only exists so the block is easy to \
open and copy.)

--- BEGIN vardoger personalization ---
{content}
--- END vardoger personalization ---
"""


_USER_RULES_COPY_FILENAME = "cursor-user-rules.md"


def _user_rules_copy_path() -> Path:
    """Return the deterministic path of the User Rules copy-source file.

    Resolved at call time (not at import time) so tests that monkeypatch
    ``vardoger.checkpoint.DEFAULT_STATE_DIR`` via the ``fake_home`` fixture
    get the redirected location.
    """
    from vardoger.checkpoint import DEFAULT_STATE_DIR

    return DEFAULT_STATE_DIR / _USER_RULES_COPY_FILENAME


def _write_user_rules_copy(content: str) -> Path | None:
    """Write the rendered block to the copy-source file; return the path.

    Best-effort: on ``OSError`` (sandboxed shell with no write access outside
    the workspace, read-only filesystem, etc.) we log a warning and return
    ``None``. Callers fall back to the inline block in the response.
    """
    import logging

    copy_path = _user_rules_copy_path()
    try:
        copy_path.parent.mkdir(parents=True, exist_ok=True)
        copy_path.write_text(content, encoding="utf-8")
    except OSError as exc:
        logging.getLogger(__name__).warning(
            "Could not write User Rules copy-source file to %s: %s. "
            "Users can still copy the inline block from the tool output.",
            copy_path,
            exc,
        )
        return None
    return copy_path


def _delete_user_rules_copy() -> Path | None:
    """Best-effort delete of the copy-source file; return the path if it existed."""
    import logging

    copy_path = _user_rules_copy_path()
    try:
        if copy_path.is_file():
            copy_path.unlink()
            return copy_path
    except OSError as exc:
        logging.getLogger(__name__).warning(
            "Could not remove stale User Rules copy-source file %s: %s",
            copy_path,
            exc,
        )
    return None


def _user_rules_response(content: str, copy_path: Path | None) -> str:
    """Render the ``vardoger_write`` response for a User Rules delivery.

    ``copy_path`` is ``None`` when :func:`_write_user_rules_copy` failed; in
    that case we fall back to a location-free message so the user still gets
    the inline block.
    """
    rendered = content.rstrip() + "\n"
    if copy_path is None:
        return (
            "vardoger_write: personalization ready (could not save a copy-source "
            "file; see warnings above). Paste the block between the BEGIN/END "
            "markers below into Cursor → Settings → Rules → User Rules.\n\n"
            "--- BEGIN vardoger personalization ---\n"
            f"{rendered}"
            "--- END vardoger personalization ---\n"
        )
    return _USER_RULES_WRITE_TEMPLATE.format(copy_path=copy_path, content=rendered)


def _user_rules_preview_response(content: str, copy_path: Path) -> str:
    """Render the ``vardoger_preview`` response for the User Rules scenario."""
    return _USER_RULES_PREVIEW_TEMPLATE.format(
        copy_path=copy_path,
        content=content.rstrip() + "\n",
    )


# ---------------------------------------------------------------------------
# Not-a-project error messaging
# ---------------------------------------------------------------------------

# Each writer refuses to land a rules file in a directory that lacks a
# project marker (see https://github.com/dstrupl/vardoger/issues/18 for
# the Cursor case and https://github.com/dstrupl/vardoger/issues/21 for
# the generalisation). The platforms differ in what the fix should look
# like to the user, so we render a tailored hint rather than bubble the
# raw exception text up through the MCP response.

# Cline has no user-global scope, so "switch to global" is never valid
# advice for it. For Cursor we prefer the User Rules copy-paste block
# over writing a file.
_NOT_A_PROJECT_HINTS: dict[str, str] = {
    "cursor": (
        "Omit project_path to get the User Rules copy-paste block instead, "
        "or pass project_path=<workspace root>."
    ),
    "claude-code": (
        "Pass project_path=<workspace root>, or use scope=global to write into ~/.claude/rules/."
    ),
    "codex": (
        "Pass project_path=<workspace root>, or use scope=global to write into ~/.codex/AGENTS.md."
    ),
    "openclaw": (
        "Pass project_path=<workspace root>, or use scope=global to write "
        "into ~/.openclaw/skills/."
    ),
    "copilot": (
        "Pass project_path=<workspace root>, or use scope=global to write "
        "into ~/.copilot/copilot-instructions.md."
    ),
    "windsurf": (
        "Pass project_path=<workspace root>, or use scope=global to write "
        "into ~/.codeium/windsurf/memories/."
    ),
    # Cline has no documented user-level rules path, so "switch to global"
    # is not available; the only remedy is to supply a real project_path.
    "cline": "Pass project_path=<workspace root> — Cline has no global scope.",
}


def _format_not_a_project_message(platform: str, scope: str, exc: Exception) -> str:
    """Render a platform-appropriate ``NotAProjectError`` response."""
    hint = _NOT_A_PROJECT_HINTS.get(platform, "Pass project_path=<workspace root>.")
    return f"vardoger: refused to write — {exc} {hint}"


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def vardoger_status(platform: str = "") -> str:
    """Check whether the personalization for a platform is up to date.

    Args:
        platform: One of cursor, claude-code, codex, openclaw, copilot,
            windsurf, cline. Empty uses the server default (env var
            ``VARDOGER_MCP_PLATFORM`` or ``cursor``).

    Returns:
        JSON ``StalenessReport`` indicating whether the personalization
        needs refreshing, how many days since the last update, and how
        many new or changed conversations exist.
    """
    resolved, err = _resolve_platform(platform)
    if resolved is None or err is not None:
        return err or "vardoger: unknown platform."
    report = check_staleness(resolved)
    return report.model_dump_json(indent=2)


@mcp.tool()
def vardoger_personalize(platform: str = "") -> str:
    """Personalize the AI assistant from its conversation history.

    Call this tool when the user asks to personalize their assistant, to
    analyze their conversation history, or mentions "vardoger". Returns
    step-by-step instructions for the calling model to follow using the
    other vardoger tools.

    Args:
        platform: One of cursor, claude-code, codex, openclaw, copilot,
            windsurf, cline. Empty uses the server default (env var
            ``VARDOGER_MCP_PLATFORM`` or ``cursor``).

    Returns:
        A markdown walkthrough of the remaining vardoger calls.
    """
    from vardoger.checkpoint import CheckpointStore

    resolved, err = _resolve_platform(platform)
    if resolved is None or err is not None:
        return err or "vardoger: unknown platform."

    store = CheckpointStore()
    event = detect_edits(resolved, store)
    if event is not None:
        store.save()
    return _orchestration_instructions(resolved)


@functools.lru_cache(maxsize=len(PLATFORM_CHOICES))
def _get_batches(platform: str = "cursor") -> list:
    """Return the current history for ``platform`` split into batches.

    Wrapped in ``lru_cache`` so the (relatively expensive) history read runs
    once per platform per process; tests can clear the cache via
    ``_get_batches.cache_clear()``.
    """
    reader = _history_reader(platform)
    conversations = reader()
    return batch_conversations(conversations)


@mcp.tool()
def vardoger_prepare(batch: int = 0, platform: str = "") -> str:
    """Prepare conversation history for analysis.

    Call without ``batch`` (or with ``batch=0``) to get metadata about how
    many batches are available. Then call with ``batch=1``, ``batch=2``,
    etc. to get each batch of conversations along with the summarization
    prompt.

    Args:
        batch: Batch number (1-based). 0 or omitted returns metadata only.
        platform: One of cursor, claude-code, codex, openclaw, copilot,
            windsurf, cline. Empty uses the server default.

    Returns:
        JSON metadata for ``batch=0``, otherwise the summarize prompt
        concatenated with the batch's conversation content.
    """
    import json

    resolved, err = _resolve_platform(platform)
    if resolved is None or err is not None:
        return err or "vardoger: unknown platform."

    batches = _get_batches(resolved)
    total_convos = sum(len(b) for b in batches)

    if batch == 0:
        return json.dumps(
            {
                "platform": resolved,
                "batches": len(batches),
                "total_conversations": total_convos,
            }
        )

    if batch < 1 or batch > len(batches):
        return f"Batch {batch} out of range (1-{len(batches)})."

    batch_text = format_batch(batches[batch - 1], batch, len(batches))
    prompt = summarize_prompt()
    return f"{prompt}\n\n---\n\n{batch_text}"


@mcp.tool()
def vardoger_synthesize_prompt(platform: str = "") -> str:
    """Get the synthesis prompt for combining batch summaries.

    Call this after you have summarized all batches. Use the returned
    prompt to guide the synthesis of those batch summaries into a final
    personalization. If the user has previously edited the generated
    rules, a feedback-context block is prepended so the synthesis respects
    those edits.

    Args:
        platform: One of cursor, claude-code, codex, openclaw, copilot,
            windsurf, cline. Empty uses the server default.

    Returns:
        The synthesis prompt text (optionally prefixed with feedback
        context).
    """
    from vardoger.checkpoint import CheckpointStore

    resolved, err = _resolve_platform(platform)
    if resolved is None or err is not None:
        return err or "vardoger: unknown platform."

    store = CheckpointStore()
    record = store.get_feedback(_STATE_KEY[resolved])
    context = feedback_context_prompt(record.kept_rules, record.removed_rules, record.added_rules)
    prompt = synthesize_prompt()
    if context is None:
        return prompt
    return f"{context}\n\n---\n\n{prompt}"


@mcp.tool()
def vardoger_write(
    content: str,
    platform: str = "",
    scope: str = "",
    project_path: str = "",
) -> str:
    """Deliver the final personalization — copy-paste by default, file opt-in.

    Call this after synthesizing all batch summaries. If ``content`` begins
    with a YAML frontmatter block (as produced by the synthesis prompt),
    low-confidence rules are annotated with "(tentative)" before delivery.

    Delivery modes (Cursor):
      - ``project_path`` empty → default, **no disk write**. Returns a
        copy-paste block the user pastes into *Cursor Settings → Rules →
        User Rules*. This is the correct default because vardoger's output
        is derived from global conversation history, not from any one
        project.
      - ``project_path`` set → project-scoped write to
        ``<project>/.cursor/rules/vardoger.md``. The target is validated
        to actually be a project (``.git``, language manifest,
        ``AGENTS.md``, or ``.cursor/`` in the directory or an ancestor).
        Non-project paths are refused rather than written silently. Fixes
        https://github.com/dstrupl/vardoger/issues/18.

    For other platforms, ``project_path`` empty still falls back to the
    platform's usual default (user-global rules directory under ``~``);
    those platforms don't have Cursor's "$HOME-masquerading-as-workspace"
    problem.

    Args:
        content: The personalization markdown to write (with optional YAML
            frontmatter).
        platform: One of cursor, claude-code, codex, openclaw, copilot,
            windsurf, cline. Empty uses the server default.
        scope: "global" or "project". Empty selects the platform's default
            (project for cline, global otherwise). Ignored for Cursor.
        project_path: Optional project directory. For Cursor, leaving this
            empty switches delivery to the User Rules copy-paste block.
            For other platforms, it's passed through to their writer.

    Returns:
        Human-readable confirmation (file written) or a copy-paste block
        (User Rules delivery).
    """
    from vardoger.checkpoint import CheckpointStore, content_hash
    from vardoger.writers import NotAProjectError

    resolved, err = _resolve_platform(platform)
    if resolved is None or err is not None:
        return err or "vardoger: unknown platform."
    resolved_scope = _resolve_scope(resolved, scope)

    doc = parse_personalization(content)
    rendered = annotate_tentative(doc)

    store = CheckpointStore()

    # Cursor + no project_path → User Rules delivery. We write a convenience
    # copy-source file under ~/.vardoger/ (NOT a Cursor-loaded location) so
    # the user gets a clickable path instead of having to dig for the block
    # inside a collapsed "Ran Vardoger Write in vardoger" card. The
    # ``output_path`` in state stays the sentinel because this file is not
    # where Cursor reads rules from.
    if resolved == "cursor" and not project_path:
        copy_path = _write_user_rules_copy(rendered)
        store.record_generation(
            _STATE_KEY[resolved],
            conversations_analyzed=0,
            output_path=_USER_RULES_OUTPUT_SENTINEL,
            content=rendered,
            output_hash=content_hash(rendered),
            confidence=doc.confidence,
        )
        store.save()
        return _user_rules_response(rendered, copy_path)

    target = Path(project_path) if project_path else None
    try:
        output = _write_rules(resolved, rendered, resolved_scope, target)
    except NotAProjectError as exc:
        return _format_not_a_project_message(resolved, resolved_scope, exc)

    store.record_generation(
        _STATE_KEY[resolved],
        conversations_analyzed=0,
        output_path=str(output),
        content=rendered,
        output_hash=content_hash(rendered),
        confidence=doc.confidence,
    )
    store.save()

    return f"vardoger: wrote personalization to {output}"


@mcp.tool()
def vardoger_preview(
    content: str,
    platform: str = "",
    scope: str = "",
    project_path: str = "",
) -> str:
    """Show a unified diff between a proposed personalization and the current file.

    Applies the same frontmatter parsing + tentative annotation as
    ``vardoger_write`` so the preview matches what would be written. Does
    not modify any files.

    Args:
        content: The proposed personalization (with optional YAML frontmatter).
        platform: One of cursor, claude-code, codex, openclaw, copilot,
            windsurf, cline. Empty uses the server default.
        scope: "global" or "project". Empty selects the platform's default.
        project_path: Optional project directory. Empty uses the current
            working directory.

    Returns:
        A unified diff, or a note if the file is identical / absent.
    """
    import difflib

    resolved, err = _resolve_platform(platform)
    if resolved is None or err is not None:
        return err or "vardoger: unknown platform."
    resolved_scope = _resolve_scope(resolved, scope)

    doc = parse_personalization(content)
    rendered = annotate_tentative(doc)

    # Cursor + no project_path: no file to diff against — show the
    # User Rules copy-paste block that ``vardoger_write`` would deliver,
    # including the deterministic path of the copy-source file it would
    # create. Preview itself never writes.
    if resolved == "cursor" and not project_path:
        return _user_rules_preview_response(rendered, _user_rules_copy_path())

    target = Path(project_path) if project_path else None
    current = _read_rules(resolved, resolved_scope, target) or ""

    if current == rendered:
        return "vardoger: proposed content matches the current file — no changes."

    diff = "\n".join(
        difflib.unified_diff(
            current.splitlines(),
            rendered.splitlines(),
            fromfile="current",
            tofile="proposed",
            lineterm="",
        )
    )
    return diff or "vardoger: no textual diff produced."


@mcp.tool()
def vardoger_feedback(
    kind: str,
    platform: str = "",
    reason: str = "",
    scope: str = "",
    project_path: str = "",
) -> str:
    """Record accept/reject feedback for the latest personalization.

    - ``accept`` simply records that the user confirmed the generation.
    - ``reject`` also auto-reverts the rules file to the previous generation,
      or clears it entirely when no prior generation exists.

    Args:
        kind: "accept" or "reject".
        platform: One of cursor, claude-code, codex, openclaw, copilot,
            windsurf, cline. Empty uses the server default.
        reason: Optional free-text reason recorded on the feedback event.
        scope: "global" or "project". Empty selects the platform's default.
        project_path: Optional project directory. Empty uses the current
            working directory.

    Returns:
        Human-readable confirmation.
    """
    from datetime import UTC, datetime

    from vardoger.checkpoint import CheckpointStore
    from vardoger.models import FeedbackEvent

    if kind not in {"accept", "reject"}:
        return f"vardoger: unknown feedback kind {kind!r} (expected 'accept' or 'reject')."

    resolved, err = _resolve_platform(platform)
    if resolved is None or err is not None:
        return err or "vardoger: unknown platform."
    resolved_scope = _resolve_scope(resolved, scope)
    state_key = _STATE_KEY[resolved]

    target = Path(project_path) if project_path else None
    store = CheckpointStore()
    event = FeedbackEvent(
        recorded_at=datetime.now(UTC).isoformat(),
        kind=kind,  # type: ignore[arg-type]
        summary=reason,
    )
    store.record_feedback_event(state_key, event)

    if kind == "accept":
        store.save()
        return f"vardoger: recorded accept for {resolved}."

    message = _apply_reject(store, resolved, resolved_scope, target, state_key)
    store.save()
    return message


def _apply_reject(
    store: Any,
    platform: str,
    scope: str,
    project_path: Path | None,
    state_key: str,
) -> str:
    """Pop the latest generation and either revert to the prior one or clear the file.

    The rejected generation may have been a "User Rules copy-paste"
    delivery (``output_path=_USER_RULES_OUTPUT_SENTINEL``) backed by a
    convenience copy-source file at ``_user_rules_copy_path()``. That file is
    not where Cursor loads rules from, so removing it does not unpersonalize
    Cursor — but it IS stale after a reject, so we delete it best-effort and
    surface manual-removal guidance for the Cursor settings block.
    """
    rejected = store.pop_generation(state_key)
    if rejected is None:
        return f"vardoger: nothing to revert for {platform}."

    rejected_was_user_rules = rejected.output_path == _USER_RULES_OUTPUT_SENTINEL

    previous = store.get_generation(state_key)
    if previous is not None and previous.content:
        if previous.output_path == _USER_RULES_OUTPUT_SENTINEL:
            # Previous was also a User-Rules delivery: re-render the
            # copy-source file with the previous content so cmd+clicking the
            # path in the response opens the correct block, not the
            # just-rejected one.
            restored = _write_user_rules_copy(previous.content)
            return (
                f"vardoger: reverted {platform} to the previous (User Rules) "
                "personalization. Re-paste the following block if you removed "
                "the old one from Settings → Rules → User Rules:\n\n"
                + _user_rules_response(previous.content, restored)
            )
        from vardoger.writers import NotAProjectError

        try:
            output = _write_rules(platform, previous.content, scope, project_path)
        except NotAProjectError as exc:
            # The previous generation was a project-scoped file write, but
            # the caller did not give us a project_path that still looks
            # like one. Don't silently land the rules somewhere Cline/etc.
            # will never read; surface the same actionable hint the write
            # path uses.
            return _format_not_a_project_message(platform, scope, exc)
        return f"vardoger: reverted {platform} to previous generation ({output})."

    if rejected_was_user_rules:
        removed = _delete_user_rules_copy()
        removed_note = (
            f" Also removed the stale copy-source file {removed}." if removed is not None else ""
        )
        return (
            f"vardoger: rejected the latest {platform} personalization."
            f"{removed_note} "
            "Nothing was written to a Cursor-loaded location (delivery was "
            "User Rules copy-paste); remove the pasted block manually from "
            "Settings → Rules → User Rules if you already added it."
        )

    cleared = _clear_rules(platform, scope, project_path)
    return (
        f"vardoger: cleared {platform} personalization (no prior generation)."
        if cleared
        else f"vardoger: no {platform} personalization file to clear."
    )


@mcp.tool()
def vardoger_import(paths: list[str]) -> str:
    """Look for existing ``.cursor/rules/vardoger.md`` files in given workspaces.

    vardoger's output is derived from *global* conversation history, so a
    user with multiple Cursor projects may already have a curated
    ``vardoger.md`` in one of them that's worth reusing (perhaps with
    edits) instead of regenerating from scratch. This tool gives the
    orchestrating model a way to look one up without blindly scanning the
    filesystem.

    The caller (the agent) is expected to supply a short list of candidate
    workspace roots it already knows about — from the user's open editors,
    recent-workspaces list, explicit mentions, etc. vardoger deliberately
    does not walk ``$HOME`` on its own: that would be slow and
    privacy-sensitive, and the exact same class of blind-filesystem
    behaviour is what caused https://github.com/dstrupl/vardoger/issues/18.

    Args:
        paths: Candidate workspace root paths (strings; tilde expansion
            applied). Non-strings and empty entries are skipped.

    Returns:
        JSON list of ``{"path": "<file>", "content": "<text>"}`` for each
        workspace where ``<root>/.cursor/rules/vardoger.md`` exists and
        was readable. Unreadable or missing entries are omitted silently.
        Empty list (``"[]"``) if nothing was found.
    """
    import json

    results: list[dict[str, str]] = []
    for entry in paths or []:
        if not isinstance(entry, str) or not entry.strip():
            continue
        try:
            root = Path(entry).expanduser()
        except (OSError, RuntimeError):
            continue
        candidate = root / ".cursor" / "rules" / "vardoger.md"
        if not candidate.is_file():
            continue
        try:
            results.append(
                {
                    "path": str(candidate),
                    "content": candidate.read_text(encoding="utf-8"),
                }
            )
        except OSError:
            # File exists but is unreadable (permissions, etc.). Skip
            # quietly; the orchestrator shouldn't halt because one
            # candidate was broken.
            continue

    return json.dumps(results, indent=2)


@mcp.tool()
def vardoger_compare(window_days: int = 0, platform: str = "") -> str:
    """Compare conversation quality before vs. after the latest personalization.

    Metrics are heuristic signals (correction rate, pushback length,
    satisfaction tokens, restart rate, emoji rate) bucketed around the
    most recent generation's timestamp.

    Args:
        window_days: Optional symmetric window in days around the cutoff.
            Use 0 (default) to include all history.
        platform: One of cursor, claude-code, codex, openclaw, copilot,
            windsurf, cline. Empty uses the server default.

    Returns:
        ``QualityComparison.model_dump_json()`` — a JSON object with
        ``before``, ``after``, ``delta_notes``, and ``caveats``.
    """
    from vardoger.quality import compare as compare_quality

    resolved, err = _resolve_platform(platform)
    if resolved is None or err is not None:
        return err or "vardoger: unknown platform."

    window: int | None = window_days if window_days and window_days > 0 else None
    comp = compare_quality(resolved, window_days=window)
    return comp.model_dump_json(indent=2)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
