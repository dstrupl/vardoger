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
