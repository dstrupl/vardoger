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

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

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
# Group 0b: Cross-host profile compilation
# ---------------------------------------------------------------------------

PreferenceState = Literal["active", "conflict", "superseded"]
RedactionPolicy = Literal["drop", "mask"]


class ProfileSourceSelection(BaseModel):
    """One explicitly selected generation from the checkpoint store."""

    platform: str
    generation: int | Literal["latest"] = "latest"


class ProfileGenerationSummary(BaseModel):
    """One available reviewed generation exposed for explicit selection."""

    platform: str
    generation: int
    generated_at: datetime
    conversations_analyzed: int
    output_path: str
    output_hash: str
    rule_count: int


class PreferenceEvidence(BaseModel):
    """Auditable provenance for one normalized preference."""

    platform: str
    generation: int
    generated_at: datetime
    output_path: str
    output_hash: str
    rule_id: str | None = None


class NormalizedPreference(BaseModel):
    """A deterministic preference derived from a reviewed generation."""

    id: str
    text: str
    category: str
    confidence: ConfidenceLevel
    observed_at: datetime
    age_days: int
    state: PreferenceState = "active"
    superseded_by: str | None = None
    evidence: list[PreferenceEvidence]


class ProfileConflict(BaseModel):
    """Opposing preferences withheld from active instructions."""

    key: str
    preference_ids: list[str]


class ProfileExclusion(BaseModel):
    """A rule removed by a user-selected retention or redaction control."""

    source: str
    reason: str


class ProfileCompileOptions(BaseModel):
    """Controls that affect deterministic profile compilation."""

    min_confidence: ConfidenceLevel = "low"
    max_age_days: int | None = Field(default=None, ge=0)
    redact_patterns: list[str] = []
    redaction_policy: RedactionPolicy = "drop"


class CompiledProfile(BaseModel):
    """Reviewable cross-host profile and its full decision record."""

    schema_version: int = 1
    reference_time: datetime
    sources: list[ProfileSourceSelection]
    preferences: list[NormalizedPreference]
    conflicts: list[ProfileConflict] = []
    exclusions: list[ProfileExclusion] = []


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


class CodexPayload(BaseModel, extra="ignore"):
    """Nested payload used by current Codex rollout entries."""

    id: str | None = None
    session_id: str | None = None
    type: str = ""
    role: str = ""
    content: list[ContentBlock | str] | str = []


class CodexEntry(BaseModel, extra="ignore"):
    """A legacy flat or current payload-wrapped Codex rollout entry."""

    id: str | None = None
    timestamp: str | None = None
    type: str = ""
    role: str = ""
    content: list[ContentBlock | str] | str = []
    payload: CodexPayload = CodexPayload()


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


class OpenClawGatewaySessionsParams(BaseModel):
    """Read-only ``sessions.list`` parameters used by Vardoger."""

    limit: int
    offset: int
    archived: str = "all"
    includeGlobal: bool = True
    includeUnknown: bool = False


class OpenClawGatewaySession(BaseModel, extra="ignore"):
    """Session identity returned by the supported Gateway projection."""

    key: str
    sessionId: str = ""
    agentId: str = ""


class OpenClawGatewaySessionsResult(BaseModel, extra="ignore"):
    """Page returned by ``sessions.list``."""

    sessions: list[OpenClawGatewaySession] = []
    total: int | None = None


class OpenClawGatewayHistoryParams(BaseModel):
    """Read-only ``chat.history`` parameters used by Vardoger."""

    sessionKey: str
    agentId: str | None = None
    limit: int
    offset: int
    maxChars: int


class OpenClawGatewayHistoryMetadata(BaseModel, extra="ignore"):
    """Stable metadata projected onto a Gateway history row."""

    id: str = ""
    seq: int | None = None
    kind: str = ""


class OpenClawGatewayMessage(BaseModel, extra="ignore"):
    """Display-normalized history message returned by ``chat.history``."""

    role: str = ""
    content: list[ContentBlock | str] | str = ""
    openclaw: OpenClawGatewayHistoryMetadata = Field(
        default_factory=OpenClawGatewayHistoryMetadata,
        alias="__openclaw",
    )


class OpenClawGatewayHistoryResult(BaseModel, extra="ignore"):
    """Normal paginated response from ``chat.history``."""

    messages: list[OpenClawGatewayMessage] = []
    hasMore: bool = False
    nextOffset: int | None = None


class CopilotEntryData(BaseModel, extra="ignore"):
    """Payload carried by a Copilot CLI session entry."""

    content: str = ""


class CopilotEntry(BaseModel, extra="ignore"):
    """One line of a Copilot CLI session ``events.jsonl`` file.

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


class AtifContentPart(BaseModel, extra="ignore"):
    """One text/image/audio part from an ATIF trajectory message."""

    type: str = ""
    text: str = ""


class AtifStep(BaseModel, extra="ignore"):
    """One user, agent, or system step in an exported ATIF trajectory."""

    step_id: int
    timestamp: str | None = None
    source: Literal["system", "user", "agent"]
    message: list[AtifContentPart] | str
    is_copied_context: bool = False


class AtifAgent(BaseModel, extra="ignore"):
    """Agent identity required by the ATIF interchange format."""

    name: str
    version: str


class AtifTrajectory(BaseModel, extra="ignore"):
    """Supported Devin CLI ``--export`` conversation representation."""

    schema_version: str
    session_id: str | None = None
    trajectory_id: str | None = None
    agent: AtifAgent
    steps: list[AtifStep]


# ---------------------------------------------------------------------------
# Group 3: Setup / config models
# ---------------------------------------------------------------------------


class McpServerConfig(BaseModel, extra="allow"):
    command: str
    args: list[str] = []
    env: dict[str, str] = {}


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
    privacyPolicyURL: str | None = None
    termsOfServiceURL: str | None = None
    defaultPrompt: list[str] = []


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
