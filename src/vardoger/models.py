# Copyright 2026 David Strupl
# SPDX-License-Identifier: Apache-2.0
"""Pydantic models for all JSON I/O in vardoger.

Organised by domain:
  - Checkpoint / state.json
  - JSONL transcript entries (per platform)
  - Setup / config files
  - Staleness reporting
  - Hook output (Claude Code SessionStart)
"""

from __future__ import annotations

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Group 1: Checkpoint / state.json
# ---------------------------------------------------------------------------


class FileCheckpoint(BaseModel):
    sha256: str
    processed_at: str


class GenerationRecord(BaseModel):
    generated_at: str
    conversations_analyzed: int
    output_path: str


class CheckpointState(BaseModel):
    version: int = 2
    checkpoints: dict[str, dict[str, FileCheckpoint]] = {}
    generations: dict[str, GenerationRecord] = {}


# ---------------------------------------------------------------------------
# Group 2: JSONL transcript entries
# ---------------------------------------------------------------------------


class ContentBlock(BaseModel, extra="ignore"):
    type: str = ""
    text: str = ""


class CursorEntry(BaseModel, extra="ignore"):
    role: str = ""
    message: dict[str, list[ContentBlock | str] | str] = {}


class ClaudeCodeEntry(BaseModel, extra="ignore"):
    type: str = ""
    message: dict[str, list[ContentBlock | str] | str] = {}


class CodexEntry(BaseModel, extra="ignore"):
    """Covers both the header line (id + timestamp) and message lines."""

    id: str | None = None
    timestamp: str | None = None
    type: str = ""
    role: str = ""
    content: list[ContentBlock | str] = []


class SessionIndexEntry(BaseModel, extra="ignore"):
    fullPath: str | None = None
    sessionId: str = ""


class SessionIndex(BaseModel, extra="ignore"):
    entries: list[SessionIndexEntry] = []


# ---------------------------------------------------------------------------
# Group 3: Setup / config models
# ---------------------------------------------------------------------------


class McpServerConfig(BaseModel, extra="allow"):
    command: str
    args: list[str] = []


class CursorMcpConfig(BaseModel, extra="allow"):
    mcpServers: dict[str, McpServerConfig] = {}


class PluginAuthor(BaseModel):
    name: str


class ClaudePluginManifest(BaseModel):
    name: str
    description: str
    author: PluginAuthor


class CodexPluginManifest(BaseModel):
    name: str
    version: str
    description: str
    author: PluginAuthor
    skills: str = "./skills/"


class MarketplacePluginSource(BaseModel):
    source: str
    path: str


class MarketplacePlugin(BaseModel, extra="ignore"):
    name: str
    source: MarketplacePluginSource | None = None


class CodexMarketplace(BaseModel, extra="allow"):
    name: str = "local"
    plugins: list[MarketplacePlugin] = []


# ---------------------------------------------------------------------------
# Group 4: Staleness reporting
# ---------------------------------------------------------------------------


class StalenessReport(BaseModel):
    platform: str
    is_stale: bool
    days_since_generation: int | None
    new_conversations: int
    changed_conversations: int
    reason: str


# ---------------------------------------------------------------------------
# Group 5: Hook output (Claude Code SessionStart)
# ---------------------------------------------------------------------------


class SessionStartContext(BaseModel):
    hookEventName: str = "SessionStart"
    additionalContext: str


class HookOutput(BaseModel):
    hookSpecificOutput: SessionStartContext
