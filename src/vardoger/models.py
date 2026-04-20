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

from typing import Literal

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Group 0: Personalization output (confidence-scored rules)
# ---------------------------------------------------------------------------

ConfidenceLevel = Literal["high", "medium", "low"]


class RuleConfidence(BaseModel):
    id: str
    text: str
    category: str
    level: ConfidenceLevel
    supporting_batches: list[int] = []


class PersonalizationDoc(BaseModel):
    confidence: list[RuleConfidence] = []
    body: str


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
    output_hash: str = ""
    content: str = ""
    confidence: list[RuleConfidence] = []
    min_confidence_written: ConfidenceLevel = "low"


class FeedbackEvent(BaseModel):
    recorded_at: str
    kind: Literal["accept", "reject", "edit"]
    summary: str = ""


class FeedbackRecord(BaseModel):
    events: list[FeedbackEvent] = []
    kept_rules: list[str] = []
    removed_rules: list[str] = []
    added_rules: list[str] = []


class CheckpointState(BaseModel):
    version: int = 3
    checkpoints: dict[str, dict[str, FileCheckpoint]] = {}
    generations: dict[str, list[GenerationRecord]] = {}
    feedback: dict[str, FeedbackRecord] = {}


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


class OpenClawMessageMetadata(BaseModel, extra="ignore"):
    userId: str = ""
    platform: str = ""
    model: str = ""


class OpenClawEntry(BaseModel, extra="ignore"):
    id: str = ""
    parentId: str | None = None
    role: str = ""
    content: str = ""
    timestamp: float = 0.0
    metadata: OpenClawMessageMetadata = OpenClawMessageMetadata()


class CopilotEntryData(BaseModel, extra="ignore"):
    """Payload carried by a Copilot CLI session entry."""

    content: str = ""


class CopilotEntry(BaseModel, extra="ignore"):
    """One line of a Copilot CLI ``~/.copilot/session-state/*.jsonl`` file.

    Each line wraps a ``type`` (``user.message``, ``assistant.message``,
    ``session.start``, ``session.info``, etc.) with a nested ``data`` object.
    Only message types carry content we want to analyze.
    """

    type: str = ""
    id: str = ""
    timestamp: str = ""
    parentId: str | None = None
    data: CopilotEntryData = CopilotEntryData()


class WindsurfEntry(BaseModel, extra="ignore"):
    """One line of a Windsurf cascade conversation JSONL file.

    Windsurf stores turns under ``~/.codeium/windsurf/`` with a per-workspace
    layout. Schemas have shifted across releases, so we parse defensively:
    only ``role`` and ``content`` are required, and ``content`` may be either
    a plain string or a list of content blocks (Anthropic/OpenAI-style).
    """

    role: str = ""
    content: list[ContentBlock | str] | str = ""
    timestamp: str | float | None = None


class ClineMessage(BaseModel, extra="ignore"):
    """One entry of Cline's ``api_conversation_history.json``.

    Cline persists Anthropic-format message arrays per task. ``content`` is
    either a plain string or a list of content blocks.
    """

    role: str = ""
    content: list[ContentBlock | str] | str = ""


class ClineConversation(BaseModel, extra="ignore"):
    """The top-level JSON array of a Cline task's api_conversation_history file."""

    messages: list[ClineMessage] = []


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
    version: str | None = None
    homepage: str | None = None
    repository: str | None = None
    license: str | None = None
    keywords: list[str] = []
    skills: str | None = None
    hooks: str | None = None


class CodexPluginInterface(BaseModel):
    displayName: str
    shortDescription: str
    longDescription: str
    developerName: str
    category: str = "Productivity"
    capabilities: list[str] = []
    websiteURL: str | None = None


class CodexPluginManifest(BaseModel):
    name: str
    version: str
    description: str
    author: PluginAuthor
    homepage: str | None = None
    repository: str | None = None
    license: str | None = None
    keywords: list[str] = []
    skills: str = "./skills/"
    interface: CodexPluginInterface | None = None


class MarketplacePluginSource(BaseModel):
    source: str
    path: str


class MarketplacePluginPolicy(BaseModel):
    installation: str = "AVAILABLE"
    authentication: str = "ON_INSTALL"


class MarketplacePlugin(BaseModel, extra="ignore"):
    name: str
    source: MarketplacePluginSource | None = None
    policy: MarketplacePluginPolicy | None = None
    category: str | None = None


class MarketplaceInterface(BaseModel):
    displayName: str


class CodexMarketplace(BaseModel, extra="allow"):
    name: str = "local"
    interface: MarketplaceInterface | None = None
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
# Group 4b: Quality comparison (A/B before/after personalization)
# ---------------------------------------------------------------------------


class QualityMetrics(BaseModel):
    correction_rate: float
    pushback_length: float
    satisfaction_signal: float
    restart_rate: float
    emoji_rate: float
    sample_conversations: int
    sample_messages: int


class QualityComparison(BaseModel):
    platform: str
    cutoff: str | None
    before: QualityMetrics | None
    after: QualityMetrics | None
    delta_notes: list[str] = []
    caveats: list[str] = []


# ---------------------------------------------------------------------------
# Group 5: Hook output (Claude Code SessionStart)
# ---------------------------------------------------------------------------


class SessionStartContext(BaseModel):
    hookEventName: str = "SessionStart"
    additionalContext: str


class HookOutput(BaseModel):
    hookSpecificOutput: SessionStartContext
