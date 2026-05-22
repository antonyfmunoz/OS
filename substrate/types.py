from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ─── Signal ──────────────────────────────────────────────────────────────────


class SignalSource(str, Enum):
    USER = "user"
    SYSTEM = "system"
    EXTERNAL_API = "external_api"
    SCHEDULED = "scheduled"
    INTERNAL_EVENT = "internal_event"
    ADAPTER = "adapter"
    NODE_MESH = "node_mesh"
    ORGANISM = "organism"


class SignalUrgency(str, Enum):
    IMMEDIATE = "immediate"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class Modality(str, Enum):
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    MULTIMODAL = "multimodal"


class Attachment(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    filename: str = Field(max_length=255)
    mime_type: str = Field(max_length=120)
    data: bytes | None = None
    url: str | None = None


class SignalEnvelope(BaseModel):
    """The universal input type. Everything enters the substrate as a SignalEnvelope."""

    id: UUID = Field(default_factory=uuid4)
    source: SignalSource
    urgency: SignalUrgency = SignalUrgency.NORMAL
    modality: Modality = Modality.TEXT
    content: str
    raw_content: str | None = None
    user_id: str
    organization_id: str
    venture_id: str | None = None
    correlation_id: UUID | None = None
    authority_tier: int = Field(default=5, ge=1, le=9)
    attachments: list[Attachment] = Field(default_factory=list)
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


# ─── Identity ────────────────────────────────────────────────────────────────


class Identity(BaseModel):
    """Resolved identity for an execution context."""

    user_id: str
    organization_id: str
    venture_id: str | None = None
    ai_name: str
    ai_personality: str
    autonomy_level: int = Field(ge=0, le=4)
    business_stage: str


# ─── Memory ──────────────────────────────────────────────────────────────────


class MemoryType(str, Enum):
    FACT = "fact"
    BELIEF = "belief"
    DECISION = "decision"
    OBSERVATION = "observation"
    COMMITMENT = "commitment"
    FEEDBACK = "feedback"
    RELATIONSHIP = "relationship"
    DOMAIN_PROJECTION = "domain_projection"


class MemoryEntry(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    memory_type: MemoryType
    content: str
    source_signal_id: UUID | None = None
    source_trace_id: UUID | None = None
    authority_tier: int = Field(default=5, ge=1, le=9)
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryQuery(BaseModel):
    query_text: str
    memory_types: list[MemoryType] | None = None
    tags: list[str] | None = None
    authority_tier_max: int = Field(default=9, ge=1, le=9)
    time_after: datetime | None = None
    time_before: datetime | None = None
    limit: int = Field(default=10, ge=1, le=100)


# ─── Execution Context ───────────────────────────────────────────────────────


class ExecutionContext(BaseModel):
    """Assembled context for spine execution."""

    id: UUID = Field(default_factory=uuid4)
    signal_id: UUID
    identity: Identity
    session_id: str | None = None
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)
    relevant_memories: list[MemoryEntry] = Field(default_factory=list)
    active_goals: list[dict[str, Any]] = Field(default_factory=list)
    business_context: dict[str, Any] = Field(default_factory=dict)
    assembled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ─── Governance ──────────────────────────────────────────────────────────────


class RiskClass(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class GovernanceDecision(str, Enum):
    APPROVE = "approve"
    DENY = "deny"
    DEFER = "defer"
    ESCALATE = "escalate"
    CONDITIONAL = "conditional"


class GovernanceVerdict(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    signal_id: UUID
    risk_class: RiskClass
    decision: GovernanceDecision
    rationale: str = Field(max_length=300)
    conditions: list[str] = Field(default_factory=list)
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    decided_by: str = Field(default="substrate", max_length=80)

    def is_executable(self) -> bool:
        return self.decision in (
            GovernanceDecision.APPROVE,
            GovernanceDecision.CONDITIONAL,
        )


# ─── Execution ───────────────────────────────────────────────────────────────


class ExecutionPlan(BaseModel):
    """What the spine intends to do — generated after governance approval."""

    id: UUID = Field(default_factory=uuid4)
    signal_id: UUID
    governance_verdict_id: UUID
    intent: str = Field(max_length=300)
    adapter_id: UUID | None = None
    model_task_type: str = "conversation"
    prompt: str
    system_prompt: str | None = None
    images: list[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AdapterResponse(BaseModel):
    """Response from any adapter (LLM, API, browser, etc.)."""

    id: UUID = Field(default_factory=uuid4)
    adapter_id: UUID
    success: bool
    output: str = ""
    provider: str = ""
    model: str = ""
    latency_ms: float = 0.0
    tokens_used: int = 0
    cost_usd: float = 0.0
    error: str | None = None
    responded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExecutionOutcome(str, Enum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"


class ExecutionResult(BaseModel):
    """The complete result of processing a signal through the spine."""

    id: UUID = Field(default_factory=uuid4)
    signal_id: UUID
    trace_id: UUID
    outcome: ExecutionOutcome
    output: str = ""
    provider: str = ""
    model: str = ""
    duration_ms: float = 0.0
    risk_class: RiskClass = RiskClass.LOW
    governance_decision: GovernanceDecision = GovernanceDecision.APPROVE
    memory_candidates: list[UUID] = Field(default_factory=list)
    feedback_id: UUID | None = None
    error: str | None = None
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_success(self) -> bool:
        return self.outcome in (
            ExecutionOutcome.SUCCESS,
            ExecutionOutcome.PARTIAL_SUCCESS,
        )


# ─── Trace ───────────────────────────────────────────────────────────────────


class TraceEventType(str, Enum):
    SIGNAL_RECEIVED = "signal_received"
    IDENTITY_RESOLVED = "identity_resolved"
    CONTEXT_ASSEMBLED = "context_assembled"
    GOVERNANCE_DECIDED = "governance_decided"
    MEMORY_RECALLED = "memory_recalled"
    PLAN_COMPOSED = "plan_composed"
    ADAPTER_CALLED = "adapter_called"
    ADAPTER_RESPONDED = "adapter_responded"
    EXECUTION_COMPLETED = "execution_completed"
    FEEDBACK_CAPTURED = "feedback_captured"
    MEMORY_WRITTEN = "memory_written"
    ERROR = "error"


class TraceEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    trace_id: UUID
    event_type: TraceEventType
    description: str = Field(max_length=300)
    data: dict[str, Any] = Field(default_factory=dict)
    parent_event_id: UUID | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TraceRecord(BaseModel):
    """A complete execution trace — from signal intake to outcome."""

    id: UUID = Field(default_factory=uuid4)
    signal_id: UUID
    events: list[TraceEvent] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    success: bool | None = None
    duration_ms: float | None = None

    def add_event(self, event_type: TraceEventType, description: str, **kwargs: Any) -> TraceEvent:
        event = TraceEvent(
            trace_id=self.id,
            event_type=event_type,
            description=description,
            **kwargs,
        )
        self.events.append(event)
        return event

    def complete(self, success: bool) -> None:
        self.completed_at = datetime.now(timezone.utc)
        self.success = success
        self.duration_ms = (self.completed_at - self.started_at).total_seconds() * 1000


# ─── Feedback ────────────────────────────────────────────────────────────────


class FeedbackType(str, Enum):
    IMPLICIT = "implicit"
    EXPLICIT = "explicit"
    SYSTEM = "system"


class FeedbackRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    trace_id: UUID
    signal_id: UUID
    feedback_type: FeedbackType = FeedbackType.IMPLICIT
    outcome_quality: float = Field(ge=0.0, le=1.0, default=0.5)
    learning_signal: str = Field(default="", max_length=500)
    adapter_reliability: float | None = Field(default=None, ge=0.0, le=1.0)
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


# ─── Registry ────────────────────────────────────────────────────────────────


class ComponentType(str, Enum):
    ADAPTER = "adapter"
    AGENT = "agent"
    SKILL = "skill"
    WORKFLOW = "workflow"
    TRANSPORT = "transport"
    NODE = "node"
    INTEGRATION = "integration"


class ComponentStatus(str, Enum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    INACTIVE = "inactive"
    DEREGISTERED = "deregistered"


class Component(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    component_type: ComponentType
    name: str = Field(max_length=120)
    version: str = Field(default="1.0.0", max_length=20)
    status: ComponentStatus = ComponentStatus.ACTIVE
    capabilities: list[str] = Field(default_factory=list)
    adapter_id: UUID | None = None
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class RegistrationResult(BaseModel):
    component_id: UUID
    success: bool
    error: str | None = None
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ─── Ontology ────────────────────────────────────────────────────────────────


class PrimitiveType(str, Enum):
    STATE = "state"
    CHANGE = "change"
    CONSTRAINT = "constraint"
    RESOURCE = "resource"
    SIGNAL = "signal"
    ACTION = "action"
    OUTCOME = "outcome"
    FEEDBACK = "feedback"
    GOAL = "goal"
    TIME = "time"


class OntologicalCategory(str, Enum):
    ENTITY = "entity"
    RELATION = "relation"
    EVENT = "event"
    PROPERTY = "property"
    PROCESS = "process"
    STATE = "state"
    CONSTRAINT = "constraint"
    BOUNDARY = "boundary"


class RelationshipType(str, Enum):
    CAUSES = "causes"
    CONSTRAINS = "constrains"
    ENABLES = "enables"
    REQUIRES = "requires"
    PRECEDES = "precedes"
    FOLLOWS = "follows"
    PRODUCES = "produces"
    CONSUMES = "consumes"
    MEASURES = "measures"
    CONFLICTS_WITH = "conflicts_with"


class PrimitiveObservation(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    primitive_type: PrimitiveType
    category: OntologicalCategory | None = None
    label: str = Field(max_length=80)
    description: str = Field(max_length=300)
    evidence: str = ""
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    authority_tier: int = Field(default=5, ge=1, le=9)
    relationships: list[tuple[RelationshipType, UUID]] = Field(default_factory=list)
    source_document_id: str | None = None
    source_decomposition_id: str | None = None


# ─── Ingestion ───────────────────────────────────────────────────────────────


class IngestionResult(BaseModel):
    source_uri: str
    observations_count: int = 0
    projections_count: int = 0
    memory_ids_written: list[UUID] = Field(default_factory=list)
    trace_id: UUID | None = None
    success: bool = True
    error: str | None = None


# ─── Substrate Status ────────────────────────────────────────────────────────


class SubstrateStatus(BaseModel):
    healthy: bool
    subsystems: dict[str, str] = Field(default_factory=dict)
    adapter_count: int = 0
    active_signals: int = 0
    memory_entry_count: int = 0
    trace_count: int = 0
    uptime_seconds: float = 0.0
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ─── Adapter Request ─────────────────────────────────────────────────────────


class AdapterRequest(BaseModel):
    """Request payload for any adapter."""

    id: UUID = Field(default_factory=uuid4)
    adapter_id: UUID
    payload: dict[str, Any] = Field(default_factory=dict)
    timeout_ms: int = Field(default=120_000, ge=1000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
