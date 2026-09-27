# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Read OpenClaw history through supported stores and accessors.

OpenClaw versions before 2.0 stored session transcripts at:
  ~/.openclaw/agents/<agentId>/sessions/<channel>_<id>.jsonl

OpenClaw 2.0 stores canonical sessions in per-agent SQLite databases. Vardoger
detects that layout but deliberately does not query OpenClaw's private tables.
Current history is available through explicit opt-in calls to the official
``openclaw gateway call`` CLI, using only ``sessions.list`` and
``chat.history``.

Each line is a JSON object with:
  - id: unique message identifier
  - parentId: parent message ID (tree structure)
  - role: "user", "assistant", "system", or "tool"
  - content: message text (plain string)
  - timestamp: Unix timestamp in seconds
  - metadata: userId, platform, model, token counts, etc.
"""

from __future__ import annotations

import logging

# This adapter invokes a fixed OpenClaw CLI argv and never enables a shell.
import subprocess  # nosec B404
from collections.abc import Callable
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import BaseModel, ValidationError

from vardoger.config import OpenClawConfig
from vardoger.history.models import Conversation, Message, extract_text
from vardoger.models import (
    OpenClawEntry,
    OpenClawGatewayHistoryParams,
    OpenClawGatewayHistoryResult,
    OpenClawGatewaySession,
    OpenClawGatewaySessionsParams,
    OpenClawGatewaySessionsResult,
)

logger = logging.getLogger(__name__)

DEFAULT_OPENCLAW_DIR = Path.home() / ".openclaw" / "agents"
GATEWAY_SESSION_PAGE_SIZE = 100
GATEWAY_HISTORY_PAGE_SIZE = 1000
GATEWAY_HISTORY_MAX_CHARS = 500_000
GATEWAY_TIMEOUT_MS = 10_000
GATEWAY_FULL_READ_REQUIRED = (
    "OpenClaw Gateway history currently requires a full read because Vardoger "
    "has not yet migrated file checkpoints to stable Gateway message anchors. "
    "Re-run with --full."
)
GATEWAY_BROKEN_PAGINATION = (
    "OpenClaw chat.history reported more pages without nextOffset; update OpenClaw and retry."
)
GATEWAY_REPEATED_OFFSET = (
    "OpenClaw chat.history repeated a pagination offset; update OpenClaw and retry."
)
GATEWAY_CLI_MISSING = (
    "OpenClaw Gateway access is enabled, but the 'openclaw' CLI is not available "
    "on PATH. Install a current OpenClaw CLI or unset VARDOGER_OPENCLAW_GATEWAY."
)
_ModelT = TypeVar("_ModelT", bound=BaseModel)

OpenClawHistoryBackend = Literal["sqlite", "legacy-jsonl", "none"]


class UnsupportedOpenClawHistoryError(RuntimeError):
    """Raised when current OpenClaw history needs its supported accessor."""


def detect_openclaw_history_backend(
    openclaw_dir: Path | None = None,
) -> OpenClawHistoryBackend:
    """Identify current SQLite, legacy JSONL, or absent OpenClaw history."""
    base = openclaw_dir or DEFAULT_OPENCLAW_DIR
    if not base.is_dir():
        return "none"
    if _discover_sqlite_stores(base):
        return "sqlite"
    if _discover_legacy_jsonl_files(base):
        return "legacy-jsonl"
    return "none"


def discover_openclaw_files(
    openclaw_dir: Path | None = None,
) -> list[tuple[Path, str]]:
    """Return legacy JSONL session files, rejecting current SQLite history."""
    base = openclaw_dir or DEFAULT_OPENCLAW_DIR
    if not base.is_dir():
        return []
    sqlite_stores = _discover_sqlite_stores(base)
    if sqlite_stores:
        raise UnsupportedOpenClawHistoryError(_sqlite_unsupported_message(sqlite_stores[0]))
    return _discover_legacy_jsonl_files(base)


def _parse_session(path: Path, agent_id: str, rel_path: str) -> Conversation | None:
    """Parse a single OpenClaw session JSONL file into a Conversation."""
    messages: list[Message] = []
    session_id = path.stem

    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    entry = OpenClawEntry.model_validate_json(stripped)
                except ValidationError:
                    continue

                if entry.role not in ("user", "assistant"):
                    continue

                if entry.content.strip():
                    messages.append(Message(role=entry.role, content=entry.content))
    except OSError as exc:
        logger.warning("Could not read %s: %s", path, exc)
        return None

    if not messages:
        return None

    return Conversation(
        messages=messages,
        platform="openclaw",
        project=agent_id,
        session_id=session_id,
        source_path=rel_path,
    )


def read_openclaw_history(
    openclaw_dir: Path | None = None,
    file_filter: Callable[[Path, str], bool] | None = None,
) -> list[Conversation]:
    """Discover and parse OpenClaw session transcripts.

    If file_filter is provided, it is called with (abs_path, rel_path) for
    each discovered file. Only files where the filter returns True are parsed.
    """
    if OpenClawConfig.from_env().gateway_enabled:
        if file_filter is not None:
            raise UnsupportedOpenClawHistoryError(GATEWAY_FULL_READ_REQUIRED)
        return read_openclaw_gateway_history()

    base = openclaw_dir or DEFAULT_OPENCLAW_DIR
    all_files = discover_openclaw_files(openclaw_dir)

    conversations: list[Conversation] = []
    skipped = 0

    for abs_path, rel_path in all_files:
        if file_filter and not file_filter(abs_path, rel_path):
            skipped += 1
            continue

        agent_id = abs_path.relative_to(base).parts[0]
        conv = _parse_session(abs_path, agent_id, rel_path)
        if conv is not None:
            conversations.append(conv)

    logger.info(
        "OpenClaw: found %d conversations (%d skipped) across %s",
        len(conversations),
        skipped,
        base,
    )
    return conversations


def read_openclaw_gateway_history(
    gateway_call: Callable[[str, BaseModel], str] | None = None,
) -> list[Conversation]:
    """Read current history through OpenClaw's documented Gateway CLI.

    The caller must opt in before reaching this function.  The command never
    supplies a URL, token, or password: the official CLI resolves its configured
    target and authentication.  Only the two read RPCs named below are
    invoked.
    """
    call = gateway_call or _gateway_call
    sessions = _read_gateway_sessions(call)
    conversations: list[Conversation] = []
    for session in sessions:
        messages = _read_gateway_messages(call, session.key, session.agentId)
        if not messages:
            continue
        conversations.append(
            Conversation(
                messages=messages,
                platform="openclaw",
                project=session.agentId or "gateway",
                session_id=session.sessionId or session.key,
                source_path=None,
            )
        )
    logger.info("OpenClaw Gateway: found %d conversations", len(conversations))
    return conversations


def _discover_sqlite_stores(base: Path) -> list[Path]:
    """Return documented per-agent OpenClaw 2.0 stores."""
    return sorted(path for path in base.glob("*/agent/openclaw-agent.sqlite") if path.is_file())


def _discover_legacy_jsonl_files(base: Path) -> list[tuple[Path, str]]:
    """Return legacy/archive JSONL artifacts under per-agent session dirs."""
    results: list[tuple[Path, str]] = []
    for agent_dir in sorted(base.iterdir()):
        if not agent_dir.is_dir():
            continue
        sessions_dir = agent_dir / "sessions"
        if not sessions_dir.is_dir():
            continue
        for jsonl_file in sorted(sessions_dir.glob("*.jsonl")):
            rel = str(jsonl_file.relative_to(base))
            results.append((jsonl_file, rel))
    return results


def _read_gateway_sessions(
    call: Callable[[str, BaseModel], str],
) -> list[OpenClawGatewaySession]:
    sessions: list[OpenClawGatewaySession] = []
    offset = 0
    while True:
        params = OpenClawGatewaySessionsParams(
            limit=GATEWAY_SESSION_PAGE_SIZE,
            offset=offset,
        )
        result = _validate_gateway_result(
            OpenClawGatewaySessionsResult,
            call("sessions.list", params),
            "sessions.list",
        )
        sessions.extend(result.sessions)
        count = len(result.sessions)
        offset += count
        if count == 0 or count < GATEWAY_SESSION_PAGE_SIZE:
            break
        if result.total is not None and offset >= result.total:
            break
    return sessions


def _read_gateway_messages(
    call: Callable[[str, BaseModel], str],
    session_key: str,
    agent_id: str,
) -> list[Message]:
    pages: list[list[Message]] = []
    offset = 0
    seen_offsets: set[int] = set()
    while True:
        if offset in seen_offsets:
            raise UnsupportedOpenClawHistoryError(GATEWAY_REPEATED_OFFSET)
        seen_offsets.add(offset)
        params = OpenClawGatewayHistoryParams(
            sessionKey=session_key,
            agentId=agent_id or None,
            limit=GATEWAY_HISTORY_PAGE_SIZE,
            offset=offset,
            maxChars=GATEWAY_HISTORY_MAX_CHARS,
        )
        result = _validate_gateway_result(
            OpenClawGatewayHistoryResult,
            call("chat.history", params),
            "chat.history",
        )
        page: list[Message] = []
        for row in result.messages:
            if row.role not in ("user", "assistant") or row.openclaw.kind:
                continue
            content = extract_text(
                row.content,
                text_types=("text", "input_text", "output_text"),
            ).strip()
            if content:
                page.append(Message(role=row.role, content=content))
        pages.insert(0, page)
        if not result.hasMore:
            break
        if result.nextOffset is None:
            raise UnsupportedOpenClawHistoryError(GATEWAY_BROKEN_PAGINATION)
        offset = result.nextOffset
    return [message for page in pages for message in page]


def _gateway_call(method: str, params: BaseModel) -> str:
    command = [
        "openclaw",
        "gateway",
        "call",
        method,
        "--params",
        params.model_dump_json(exclude_none=True),
        "--timeout",
        str(GATEWAY_TIMEOUT_MS),
        "--json",
    ]
    try:
        # The executable and argument shape are internal; user data is passed as
        # one JSON argv element and shell=False remains in effect.
        result = subprocess.run(  # nosec B603
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise UnsupportedOpenClawHistoryError(GATEWAY_CLI_MISSING) from exc
    if result.returncode != 0:
        raise UnsupportedOpenClawHistoryError(
            _gateway_call_failed_message(method, result.returncode)
        )
    return result.stdout


def _validate_gateway_result(model_type: type[_ModelT], raw: str, method: str) -> _ModelT:
    try:
        return model_type.model_validate_json(raw)
    except ValidationError as exc:
        raise UnsupportedOpenClawHistoryError(_gateway_invalid_response_message(method)) from exc


def _gateway_call_failed_message(method: str, returncode: int) -> str:
    return (
        f"OpenClaw Gateway read method {method} failed with exit code {returncode}. "
        f"Run 'openclaw gateway call {method} --json' directly for the "
        "authenticated CLI diagnostic."
    )


def _gateway_invalid_response_message(method: str) -> str:
    return (
        f"OpenClaw Gateway method {method} returned an incompatible response. "
        "Update Vardoger or disable VARDOGER_OPENCLAW_GATEWAY."
    )


def _sqlite_unsupported_message(sqlite_store: Path) -> str:
    return (
        f"OpenClaw 2.0 SQLite history detected at {sqlite_store}. "
        "Vardoger supports only legacy OpenClaw JSONL transcripts and will not "
        "query OpenClaw's private SQLite tables. Current history must be read "
        "through OpenClaw's supported transcript accessor. To opt in to the "
        "official Gateway CLI reader, set VARDOGER_OPENCLAW_GATEWAY=1 "
        "and run vardoger with --full. Otherwise use OpenClaw's native USER.md "
        "and memory features for OpenClaw-only personalization."
    )
