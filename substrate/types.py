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
    autonomy_level: int = Field(ge=0, le=5)
    business_stage: str
    permission_tier: str = Field(default="execute", max_length=20)


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


class PermissionTier(str, Enum):
    """4-tier permission model from ARCHITECTURE.md §4.

    Tiers are cumulative — each higher tier includes all lower capabilities.
    READ < DRAFT < EXECUTE < COMMIT.
    """

    READ = "read"
    DRAFT = "draft"
    EXECUTE = "execute"
    COMMIT = "commit"

    @property
    def rank(self) -> int:
        return _PERMISSION_TIER_RANK[self]

    def permits(self, required: PermissionTier) -> bool:
        return self.rank >= required.rank


_PERMISSION_TIER_RANK: dict[PermissionTier, int] = {
    PermissionTier.READ: 0,
    PermissionTier.DRAFT: 1,
    PermissionTier.EXECUTE: 2,
    PermissionTier.COMMIT: 3,
}

TIER_ACTION_MAP: dict[PermissionTier, frozenset[str]] = {
    PermissionTier.READ: frozenset(
        {
            "analyze",
            "research",
            "score",
            "classify",
            "summarize",
            "read",
            "query",
            "report",
            "draft_brief",
            "generate_brief",
            "research_prospect",
            "extract_profile",
            "read_only_query",
            "metadata_read",
            "status_check",
            "health_check",
            "inventory_read",
            "configuration_read",
            "browser_research",
        }
    ),
    PermissionTier.DRAFT: frozenset(
        {
            "draft_message",
            "draft_content",
            "create_task",
            "create_document",
            "safe_doc_extraction",
            "safe_doc_normalization",
            "ingestion_candidate_creation",
            "memory_candidate_creation",
        }
    ),
    PermissionTier.EXECUTE: frozenset(
        {
            "send_dm",
            "create_outreach",
            "post_content",
            "update_external_crm",
            "book_call",
            "send_message",
            "send_email",
            "publish_content",
            "bulk_update",
            "mass_outreach",
            "browser_execution",
            "browser_act",
            "desktop_automation",
            "container_execution",
            "container_spawn",
        }
    ),
    PermissionTier.COMMIT: frozenset(
        {
            "execute_payment",
            "delete_records",
            "financial_execution",
            "wallet_execution",
            "trade_placement",
            "money_allocation",
            "payment_processing",
            "production_deployment",
            "credential_access",
            "permission_escalation",
        }
    ),
}


def required_tier_for_action(action_type: str) -> PermissionTier:
    """Determine the minimum permission tier required for an action type."""
    for tier in (
        PermissionTier.COMMIT,
        PermissionTier.EXECUTE,
        PermissionTier.DRAFT,
        PermissionTier.READ,
    ):
        if action_type in TIER_ACTION_MAP[tier]:
            return tier
    return PermissionTier.READ


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
    permission_tier: str = Field(default="execute", max_length=20)
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    decided_by: str = Field(default="substrate", max_length=80)

    def is_executable(self) -> bool:
        # CONDITIONAL excluded until condition enforcement is implemented
        return self.decision == GovernanceDecision.APPROVE


class PipelineGovernanceVerdict(BaseModel):
    """Governance verdict used by the services/umh pipeline (request-scoped).

    Distinct from GovernanceVerdict which is signal-scoped for the substrate spine.
    """

    id: UUID = Field(default_factory=uuid4)
    request_id: UUID
    decision: GovernanceDecision
    risk_level: "RiskLevel"  # Forward ref resolved after RiskLevel defined below
    rationale: str = Field(max_length=300)
    conditions: list["GovernanceCondition"] = Field(default_factory=list)
    expires_at: datetime | None = None
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    decided_by: str = Field(default="substrate", max_length=80)

    def is_executable(self) -> bool:
        if self.decision == GovernanceDecision.APPROVE:
            return True
        if self.decision == GovernanceDecision.CONDITIONAL:
            return all(c.verified for c in self.conditions)
        return False


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
    REJECTED = "rejected"


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


class PipelineExecutionResult(BaseModel):
    """Execution result from the services/umh pipeline (work-packet-scoped)."""

    id: UUID = Field(default_factory=uuid4)
    work_packet_id: UUID
    trace_id: UUID
    outcome: ExecutionOutcome
    output_data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    duration_ms: float = 0.0
    resources_consumed: dict[str, float] = Field(default_factory=dict)
    side_effects: list[str] = Field(default_factory=list)
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_success(self) -> bool:
        return self.outcome in (ExecutionOutcome.SUCCESS, ExecutionOutcome.PARTIAL_SUCCESS)


# ─── Trace ───────────────────────────────────────────────────────────────────


class TraceEventType(str, Enum):
    SIGNAL_RECEIVED = "signal_received"
    IDENTITY_RESOLVED = "identity_resolved"
    CONTEXT_ASSEMBLED = "context_assembled"
    GOVERNANCE_DECIDED = "governance_decided"
    GOVERNANCE_REQUESTED = "governance_requested"
    MEMORY_RECALLED = "memory_recalled"
    PLAN_COMPOSED = "plan_composed"
    ADAPTER_CALLED = "adapter_called"
    ADAPTER_RESPONDED = "adapter_responded"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    FEEDBACK_CAPTURED = "feedback_captured"
    MEMORY_WRITTEN = "memory_written"
    MEMORY_WRITE = "memory_write"
    INTERPRETATION_COMPLETE = "interpretation_complete"
    DECOMPOSITION_COMPLETE = "decomposition_complete"
    WORK_PACKET_CREATED = "work_packet_created"
    CUSTOM = "custom"
    ERROR = "error"


class TraceEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    trace_id: UUID
    event_type: TraceEventType
    description: str = Field(max_length=300)
    entity_id: UUID | None = None
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


# Alias: the protocol-layer Trace is identical to TraceRecord in structure
# (both have signal_id, events, add_event). Pipeline code imports Trace.
Trace = TraceRecord


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


class TemporalMode(str, Enum):
    INSTANTANEOUS = "instantaneous"
    DURATIVE = "durative"
    ATEMPORAL = "atemporal"
    PERIODIC = "periodic"


class CausalRole(str, Enum):
    CAUSE = "cause"
    EFFECT = "effect"
    CONDITION = "condition"
    PREVENTION = "prevention"
    MAINTENANCE = "maintenance"


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


# ─── Capability ─────────────────────────────────────────────────────────────


class CapabilityStatus(str, Enum):
    """Current availability of a capability."""

    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"


class CapabilityCategory(str, Enum):
    """Broad category of capability."""

    COMPUTE = "compute"
    COMMUNICATE = "communicate"
    STORE = "store"
    RETRIEVE = "retrieve"
    TRANSFORM = "transform"
    OBSERVE = "observe"
    DECIDE = "decide"


class Capability(BaseModel):
    """A registered capability the substrate can invoke."""

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(max_length=120)
    category: CapabilityCategory
    status: CapabilityStatus = CapabilityStatus.AVAILABLE
    adapter_id: UUID | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    cost_per_invocation: float = 0.0
    rate_limit: int | None = None
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_usable(self) -> bool:
        return self.status in (CapabilityStatus.AVAILABLE, CapabilityStatus.DEGRADED)


class CapabilityInvocation(BaseModel):
    """A request to use a specific capability."""

    id: UUID = Field(default_factory=uuid4)
    capability_id: UUID
    governance_verdict_id: UUID
    input_data: dict[str, Any] = Field(default_factory=dict)
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trace_id: UUID | None = None


# ─── Environment ────────────────────────────────────────────────────────────


class EnvironmentDomain(str, Enum):
    """Which aspect of the environment is being tracked."""

    COMPUTE = "compute"
    NETWORK = "network"
    STORAGE = "storage"
    TIME = "time"
    USER_CONTEXT = "user_context"
    SYSTEM_STATE = "system_state"


class ResourceStatus(str, Enum):
    """Status of an environmental resource."""

    NOMINAL = "nominal"
    CONSTRAINED = "constrained"
    CRITICAL = "critical"
    UNAVAILABLE = "unavailable"


class EnvironmentFact(BaseModel):
    """A single observation about the current environment."""

    domain: EnvironmentDomain
    key: str = Field(max_length=120)
    value: Any
    status: ResourceStatus = ResourceStatus.NOMINAL
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EnvironmentSnapshot(BaseModel):
    """A point-in-time view of the operating environment."""

    id: UUID = Field(default_factory=uuid4)
    facts: list[EnvironmentFact] = Field(default_factory=list)
    constraints_active: list[str] = Field(default_factory=list)
    taken_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def is_healthy(self) -> bool:
        return all(
            f.status in (ResourceStatus.NOMINAL, ResourceStatus.CONSTRAINED) for f in self.facts
        )

    def critical_resources(self) -> list[EnvironmentFact]:
        return [f for f in self.facts if f.status == ResourceStatus.CRITICAL]


# ─── Interpretation ─────────────────────────────────────────────────────────


class InterpretationType(str, Enum):
    """What kind of meaning was extracted."""

    REQUEST = "request"
    INFORMATION = "information"
    FEEDBACK = "feedback"
    QUESTION = "question"
    COMMAND = "command"
    NOTIFICATION = "notification"
    CONSTRAINT = "constraint"


class Intent(BaseModel):
    """A recognized intent within the interpretation."""

    action: str = Field(max_length=120)
    target: str | None = Field(default=None, max_length=120)
    parameters: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)


class Interpretation(BaseModel):
    """The structured meaning derived from a Signal."""

    id: UUID = Field(default_factory=uuid4)
    signal_id: UUID
    interpretation_type: InterpretationType
    summary: str = Field(max_length=300)
    intents: list[Intent] = Field(default_factory=list)
    entities_referenced: list[str] = Field(default_factory=list)
    requires_action: bool = False
    requires_response: bool = False
    context_dependencies: list[UUID] = Field(default_factory=list)
    interpreted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def primary_intent(self) -> Intent | None:
        if not self.intents:
            return None
        return max(self.intents, key=lambda i: i.confidence)


# ─── Memory Candidate ───────────────────────────────────────────────────────


class MemoryCandidate(BaseModel):
    """A proposed write to durable memory — must pass governance."""

    id: UUID = Field(default_factory=uuid4)
    memory_type: MemoryType
    content: str = Field(max_length=1000)
    source_signal_id: UUID | None = None
    source_trace_id: UUID | None = None
    governance_verdict_id: UUID | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    tags: list[str] = Field(default_factory=list)
    supersedes: list[UUID] = Field(default_factory=list)
    proposed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryUpdate(BaseModel):
    """A modification to an existing memory entry."""

    id: UUID = Field(default_factory=uuid4)
    target_memory_id: UUID
    update_type: str = Field(max_length=60)
    previous_value: Any = None
    new_value: Any = None
    reason: str = Field(max_length=300)
    governance_verdict_id: UUID | None = None
    applied_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryWriteResult(BaseModel):
    """Confirmation that a memory candidate was persisted."""

    candidate_id: UUID
    memory_id: UUID
    written_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool = True
    error: str | None = None


# ─── Outcome ────────────────────────────────────────────────────────────────


class OutcomeType(str, Enum):
    """Category of outcome."""

    ACTION_COMPLETED = "action_completed"
    INFORMATION_DELIVERED = "information_delivered"
    STATE_CHANGED = "state_changed"
    NO_ACTION_NEEDED = "no_action_needed"
    ESCALATED = "escalated"
    FAILED = "failed"


class Outcome(BaseModel):
    """The final result of processing a signal through the full pipeline."""

    id: UUID = Field(default_factory=uuid4)
    signal_id: UUID
    trace_id: UUID
    outcome_type: OutcomeType
    summary: str = Field(max_length=300)
    results: list[UUID] = Field(default_factory=list)
    goals_affected: list[UUID] = Field(default_factory=list)
    beliefs_updated: list[UUID] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_successful(self) -> bool:
        return self.outcome_type not in (OutcomeType.FAILED, OutcomeType.ESCALATED)


# ─── Proof ──────────────────────────────────────────────────────────────────


class ProofType(str, Enum):
    """What is being proven."""

    EXECUTION = "execution"
    GOVERNANCE = "governance"
    INVARIANT = "invariant"
    STATE_TRANSITION = "state_transition"
    CAPABILITY_USE = "capability_use"


class ProofStatus(str, Enum):
    """Verification status of the proof."""

    VERIFIED = "verified"
    PENDING = "pending"
    FAILED = "failed"
    EXPIRED = "expired"


class Proof(BaseModel):
    """Verifiable evidence that an operation occurred correctly."""

    id: UUID = Field(default_factory=uuid4)
    proof_type: ProofType
    status: ProofStatus = ProofStatus.PENDING
    claim: str = Field(max_length=300)
    evidence: dict[str, Any] = Field(default_factory=dict)
    trace_id: UUID | None = None
    verified_by: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    verified_at: datetime | None = None
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_valid(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        if self.status != ProofStatus.VERIFIED:
            return False
        if self.expires_at and self.expires_at < now:
            return False
        return True


# ─── Work Packet ────────────────────────────────────────────────────────────


class WorkPacketStatus(str, Enum):
    """Lifecycle of a work packet."""

    PENDING = "pending"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkPacketPriority(str, Enum):
    """Execution priority."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class WorkPacket(BaseModel):
    """The fundamental unit of execution — carries governance approval and trace context."""

    id: UUID = Field(default_factory=uuid4)
    governance_verdict_id: UUID
    capability_id: UUID
    trace_id: UUID
    description: str = Field(max_length=300)
    status: WorkPacketStatus = WorkPacketStatus.PENDING
    priority: WorkPacketPriority = WorkPacketPriority.NORMAL
    input_data: dict[str, Any] = Field(default_factory=dict)
    assigned_adapter_id: UUID | None = None
    max_retries: int = 1
    attempt: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_terminal(self) -> bool:
        return self.status in (
            WorkPacketStatus.COMPLETED,
            WorkPacketStatus.FAILED,
            WorkPacketStatus.CANCELLED,
        )

    def can_retry(self) -> bool:
        return self.status == WorkPacketStatus.FAILED and self.attempt < self.max_retries


# ─── Governance (extended) ──────────────────────────────────────────────────


class RiskLevel(str, Enum):
    """Assessed risk of a proposed action (finer-grained than RiskClass)."""

    NEGLIGIBLE = "negligible"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GovernanceCondition(BaseModel):
    """A condition that must be met for conditional approval."""

    condition: str = Field(max_length=200)
    verified: bool = False
    verified_at: datetime | None = None


class GovernanceRequest(BaseModel):
    """A request for governance decision on a proposed action."""

    id: UUID = Field(default_factory=uuid4)
    decomposition_id: UUID
    component_id: UUID
    proposed_action: str = Field(max_length=300)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    reversible: bool = True
    affects_external: bool = False
    requires_resources: list[str] = Field(default_factory=list)
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ─── Signal (protocol version) ─────────────────────────────────────────────


class Signal(BaseModel):
    """The universal intake type — all external input enters as a Signal."""

    id: UUID = Field(default_factory=uuid4)
    source: SignalSource
    urgency: SignalUrgency = SignalUrgency.NORMAL
    content_type: str = Field(max_length=80)
    payload: dict[str, Any] = Field(default_factory=dict)
    raw_content: str | None = None
    source_identifier: str | None = Field(default=None, max_length=200)
    correlation_id: UUID | None = None
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_user_initiated(self) -> bool:
        return self.source == SignalSource.USER


# ─── Decomposition ──────────────────────────────────────────────────────────


class DecompositionComponentType(str, Enum):
    """Type of decomposed component (distinct from registry ComponentType)."""

    TASK = "task"
    QUERY = "query"
    CONSTRAINT = "constraint"
    DEPENDENCY = "dependency"
    ASSUMPTION = "assumption"
    RISK = "risk"


class DecomposedComponent(BaseModel):
    """A single atomic component from decomposition."""

    id: UUID = Field(default_factory=uuid4)
    component_type: DecompositionComponentType
    description: str = Field(max_length=300)
    ordering: int = 0
    dependencies: list[UUID] = Field(default_factory=list)
    capability_required: str | None = None
    estimated_complexity: float = Field(default=0.5, ge=0.0, le=1.0)


class Decomposition(BaseModel):
    """The result of breaking an interpretation into actionable pieces."""

    id: UUID = Field(default_factory=uuid4)
    interpretation_id: UUID
    components: list[DecomposedComponent] = Field(default_factory=list)
    total_complexity: float = Field(default=0.0, ge=0.0)
    parallelizable: bool = False
    decomposed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def tasks(self) -> list[DecomposedComponent]:
        return [c for c in self.components if c.component_type == DecompositionComponentType.TASK]

    def constraints(self) -> list[DecomposedComponent]:
        return [
            c for c in self.components if c.component_type == DecompositionComponentType.CONSTRAINT
        ]

    def critical_path(self) -> list[DecomposedComponent]:
        """Components with no dependencies — they must execute first."""
        return [c for c in self.components if not c.dependencies]


# ─── Adapter (extended) ────────────────────────────────────────────────────


class AdapterType(str, Enum):
    """What kind of external system the adapter connects to."""

    LLM = "llm"
    DATABASE = "database"
    API = "api"
    FILESYSTEM = "filesystem"
    MESSAGING = "messaging"
    BROWSER = "browser"
    TOOL = "tool"


class AdapterStatus(str, Enum):
    """Adapter health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    DISCONNECTED = "disconnected"


class AdapterConfig(BaseModel):
    """Configuration for an adapter instance."""

    id: UUID = Field(default_factory=uuid4)
    adapter_type: AdapterType
    name: str = Field(max_length=120)
    endpoint: str | None = None
    status: AdapterStatus = AdapterStatus.DISCONNECTED
    timeout_seconds: float = 30.0
    retry_count: int = 3
    auth_required: bool = False
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


# ─── Entity Model ─────────────────────────────────────────────────────────


class OperatorType(str, Enum):
    """Who operates a role."""

    HUMAN = "human"
    AI = "ai"
    HYBRID = "hybrid"


class Role(BaseModel):
    """The atomic operating unit — ARCHITECTURE.md §3.

    Everything in the system attaches to a role. A role can be operated by
    human, AI, or both. The role is the unit of authority, delegation, and
    performance measurement.
    """

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(max_length=120)
    department: str = Field(max_length=80)
    organization_id: str
    venture_id: str | None = None
    operator: OperatorType = OperatorType.HYBRID
    agent_name: str | None = None
    permission_tier: str = Field(default="execute", max_length=20)
    responsibilities: list[str] = Field(default_factory=list)
    workflows: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)
    dashboard_id: str | None = None
    autonomy_level: int = Field(ge=0, le=5, default=2)
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class Department(BaseModel):
    """A department within a company — groups roles and has its own agent.

    Departments are data entities, not just prompt context. Each has metrics,
    approval queues, and an AI agent that coordinates the roles within it.
    """

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(max_length=80)
    slug: str = Field(max_length=40)
    organization_id: str
    venture_id: str | None = None
    agent_name: str | None = None
    permission_tier: str = Field(default="execute", max_length=20)
    roles: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    workflows: list[str] = Field(default_factory=list)
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class Portfolio(BaseModel):
    """A founder's portfolio of companies."""

    id: UUID = Field(default_factory=uuid4)
    user_id: str
    companies: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class User(BaseModel):
    """A human user of the system — ARCHITECTURE.md §3 top of entity hierarchy."""

    id: UUID = Field(default_factory=uuid4)
    email: str = Field(max_length=255)
    display_name: str = Field(max_length=120, default="")
    auth_provider: str = Field(default="local", max_length=40)
    auth_provider_id: str = ""
    portfolio_id: str | None = None
    preferences: dict[str, Any] = Field(default_factory=dict)
    role_scope: str = Field(default="founder", max_length=40)
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Company(BaseModel):
    """A business instance within a portfolio — ARCHITECTURE.md §3.

    Parent entity owning departments, BIS, knowledge graph, interactions.
    Maps to a venture in the database.
    """

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(max_length=200)
    organization_id: str
    venture_id: str = ""
    portfolio_id: str | None = None
    stage: int = Field(ge=1, le=6, default=1)
    stage_name: str = Field(default="validation", max_length=40)
    bis_id: str | None = None
    departments: list[str] = Field(default_factory=list)
    north_star: str = ""
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowStepType(str, Enum):
    """Types of steps in a workflow."""

    ACTION = "action"
    DECISION = "decision"
    APPROVAL_GATE = "approval_gate"
    WAIT = "wait"
    PARALLEL = "parallel"
    NOTIFICATION = "notification"


class WorkflowExecutionMode(str, Enum):
    """How a workflow step is executed."""

    HUMAN = "human"
    AI = "ai"
    AUTOMATED = "automated"
    HYBRID = "hybrid"


class WorkflowStep(BaseModel):
    """A single step in a workflow."""

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(max_length=120)
    step_type: WorkflowStepType = WorkflowStepType.ACTION
    execution_mode: WorkflowExecutionMode = WorkflowExecutionMode.HYBRID
    description: str = ""
    action_type: str = ""
    next_step: str | None = None
    branch_conditions: dict[str, str] = Field(default_factory=dict)
    approval_required: bool = False
    timeout_seconds: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowTriggerType(str, Enum):
    """What initiates a workflow."""

    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EVENT = "event"
    SIGNAL = "signal"
    WEBHOOK = "webhook"
    APPROVAL = "approval"


class Workflow(BaseModel):
    """A repeatable process — ARCHITECTURE.md §3.

    Supports human, AI-assisted, or fully automated execution.
    Has triggers, ordered steps, branching logic, approval gates, and output artifacts.
    """

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(max_length=200)
    slug: str = Field(max_length=80)
    department: str = Field(max_length=80, default="")
    organization_id: str = ""
    trigger_type: WorkflowTriggerType = WorkflowTriggerType.MANUAL
    trigger_config: dict[str, Any] = Field(default_factory=dict)
    steps: list[WorkflowStep] = Field(default_factory=list)
    output_artifacts: list[str] = Field(default_factory=list)
    permission_tier: str = Field(default="execute", max_length=20)
    active: bool = True
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class DashboardWidgetType(str, Enum):
    """Types of widgets on a role dashboard."""

    TASK_BOARD = "task_board"
    METRIC_CARD = "metric_card"
    WORKFLOW_LIST = "workflow_list"
    DOCUMENT_LIST = "document_list"
    CRM_TABLE = "crm_table"
    APPROVAL_QUEUE = "approval_queue"
    AI_CHAT = "ai_chat"
    TOOL_PANEL = "tool_panel"
    COMMUNICATION = "communication"
    TIMELINE = "timeline"


class DashboardWidget(BaseModel):
    """A widget on a role's dashboard."""

    id: UUID = Field(default_factory=uuid4)
    widget_type: DashboardWidgetType
    title: str = Field(max_length=120)
    config: dict[str, Any] = Field(default_factory=dict)
    position: int = 0
    width: int = Field(ge=1, le=12, default=6)
    visible: bool = True


class Dashboard(BaseModel):
    """The complete UI surface for a role — ARCHITECTURE.md §3.

    Contains task board, tools, CRM records, documents, workflows,
    metrics, communications, AI interaction panel, and approval queue.
    """

    id: UUID = Field(default_factory=uuid4)
    role_id: str | None = None
    department: str = Field(max_length=80, default="")
    organization_id: str = ""
    widgets: list[DashboardWidget] = Field(default_factory=list)
    layout: str = Field(default="grid", max_length=20)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class AutonomyLevel(int, Enum):
    """6 autonomy levels — ARCHITECTURE.md §4."""

    DRAFT_ONLY = 0
    LOW_RISK_AUTO = 1
    MEDIUM_RISK_LOG = 2
    HIGH_RISK_DELAY = 3
    ALL_EXCEPT_COMMIT = 4
    FULL_AUTONOMY = 5


# ─── World Model ────────────────────────────────────────────────────────────


class WorldModelUpdateType(str, Enum):
    PATTERN_DISCOVERED = "pattern_discovered"
    PATTERN_INVALIDATED = "pattern_invalidated"
    RELATIONSHIP_CHANGED = "relationship_changed"
    CONFIDENCE_ADJUSTED = "confidence_adjusted"
    CONSTRAINT_ACTIVATED = "constraint_activated"
    CONSTRAINT_LIFTED = "constraint_lifted"


class WorldModelUpdate(BaseModel):
    """A discrete change to the substrate's understanding of reality."""

    id: UUID = Field(default_factory=uuid4)
    update_type: WorldModelUpdateType
    domain: str = Field(max_length=80)
    subject: str = Field(max_length=120)
    description: str = Field(max_length=300)
    evidence_signal_id: UUID | None = None
    evidence_trace_id: UUID | None = None
    old_value: Any = None
    new_value: Any = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ─── Projection ─────────────────────────────────────────────────────────────


class ProjectionContract(BaseModel):
    """Declaration a projection provides to register with the substrate.

    Every application-layer projection (EOS, CreatorOS, LyfeOS) must
    produce one of these to plug into the substrate runtime.
    """

    projection_id: str = Field(max_length=60)
    name: str = Field(max_length=80)
    version: str = Field(default="0.1.0", max_length=20)
    domains: list[str] = Field(default_factory=list)
    entity_types: list[str] = Field(default_factory=list)
    required_adapters: list[str] = Field(default_factory=list)
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ─── Deferred model resolution ──────────────────────────────────────────────
# PipelineGovernanceVerdict references RiskLevel and GovernanceCondition which
# are defined after it. Rebuild to resolve the forward references.
PipelineGovernanceVerdict.model_rebuild()
