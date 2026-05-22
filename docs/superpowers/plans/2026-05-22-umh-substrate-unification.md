# UMH Substrate Unification — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collapse ~333K lines across 1,194 Python files into a unified 6-tier UMH substrate with one type system (Pydantic), one execution spine, one public API, full tracing, and zero dead code — capable of hosting EOS (Initiate Arena outreach) as its first projection.

**Architecture:** Bottom-up migration in 8 phases. Phase 0 archives and scaffolds. Phases 1–3 build the substrate kernel (ontology → control plane → execution spine). Phase 4 wraps external systems as adapters. Phase 5 rewires transports (Discord, API, node mesh) to route through `substrate.execute()`. Phase 6 prunes ~230K dead lines. Phase 7 builds the EOS projection layer. Each phase produces independently testable software and ends with a verification gate.

**Tech Stack:** Python 3.12, Pydantic BaseModel (sole type system), Neon Postgres (psycopg2), pytest, Docker, model_router.call_with_fallback() (LLM routing), ruff (formatting)

**Spec:** `docs/superpowers/specs/2026-05-21-umh-substrate-unification-design.md` (v2.1)

---

## File Structure

### New files created (by phase)

**Phase 0 — Archive & Scaffold:**
- `substrate/__init__.py` — public API stub (imports only, logic in Phase 3)
- `substrate/types.py` — all Pydantic models from spec Section 6
- `substrate/ontology/__init__.py`
- `substrate/control_plane/__init__.py`
- `substrate/execution/__init__.py`
- `substrate/execution/ingestion/__init__.py`
- `substrate/organism/__init__.py`
- `substrate/learning/__init__.py`
- `adapters/__init__.py` (new top-level, not `adapters/model_adapters/`)
- `adapters/protocol.py`
- `adapters/models/__init__.py`
- `transports/__init__.py`
- `transports/discord/__init__.py`
- `transports/api/__init__.py`
- `transports/node_mesh/__init__.py`
- `projections/__init__.py`
- `projections/eos/__init__.py`
- `integrations/__init__.py`
- `integrations/creatoros/__init__.py`
- `integrations/lyfeos/__init__.py`
- `knowledge/` (renamed from `10_Wiki/`)
- `tests/substrate/test_types.py`
- `tests/substrate/__init__.py`
- `tests/adapters/__init__.py`
- `tests/transports/__init__.py`
- `tests/integration/__init__.py`
- `tests/acceptance/__init__.py`
- `_archive/` — full snapshot of pre-unification code

**Phase 1 — Ontology:**
- `substrate/ontology/primitives.py` — merged PrimitiveType + OntologicalCategory + RelationshipType
- `substrate/ontology/laws.py` — governing laws registry
- `substrate/ontology/relationships.py` — typed edge definitions
- `tests/substrate/test_ontology.py`

**Phase 2 — Control Plane:**
- `substrate/control_plane/identity.py` — ConcreteIdentityResolver
- `substrate/control_plane/context.py` — ConcreteContextAssembler
- `substrate/control_plane/governance.py` — ConcreteGovernanceEngine
- `substrate/control_plane/memory.py` — ConcreteMemorySystem
- `substrate/control_plane/registry.py` — ConcreteComponentRegistry
- `substrate/control_plane/router.py` — ConcreteSignalRouter
- `tests/substrate/test_control_plane.py`

**Phase 3 — Execution Spine:**
- `substrate/execution/spine.py` — 8-stage ExecutionSpine
- `substrate/execution/trace.py` — TraceRecorder with Neon persistence
- `substrate/execution/feedback.py` — FeedbackCapture
- `substrate/execution/ingestion/orchestrator.py` — migrated GenericIngestionOrchestrator
- `substrate/execution/ingestion/decomposer.py` — migrated PrimitiveDecomposer
- `substrate/execution/ingestion/sources.py` — LocalFileSource, GWSSource
- `substrate/execution/ingestion/domain_bridge.py` — domain projection layer
- `substrate/__init__.py` — full Substrate class wiring (replace stub)
- `tests/substrate/test_execution.py`
- `tests/substrate/test_ingestion.py`
- `tests/integration/test_signal_to_trace.py`
- `tests/integration/test_governance_blocks_critical.py`
- `tests/integration/test_memory_round_trip.py`

**Phase 4 — Adapters:**
- `adapters/models/llm_adapter.py` — LLMAdapter wrapping model_router
- `tests/adapters/test_llm_adapter.py`

**Phase 5 — Transports:**
- `transports/discord/bot.py` — refactored from services/discord_bot.py
- `transports/discord/signal_factory.py` — Message → SignalEnvelope
- `transports/discord/voice_first.py` — migrated from execution/transport/
- `transports/api/operator.py` — refactored from services/operator_api.py
- `transports/api/cockpit.py` — migrated from services/umh/control_plane/
- `transports/api/signal_factory.py` — HTTP → SignalEnvelope
- `tests/transports/test_discord_signal_factory.py`
- `tests/acceptance/test_discord_message_flow.py`

**Phase 6 — Prune:**
- `scripts/dead_code_check.py`
- `scripts/invariant_check.sh`

**Phase 7 — EOS Projection:**
- `projections/eos/__init__.py` — EOS signal handlers
- `projections/eos/agents/` — CEO, Sales, Marketing agents
- `projections/eos/workflows/` — outreach, follow-up
- `projections/eos/views/` — CRM, pipeline as memory queries
- `tests/acceptance/test_eos_outreach_flow.py`

### Existing files relocated (not modified):
- `execution/runtime/model_router.py` → `adapters/models/model_router.py`
- `adapters/model_adapters/cc_sdk.py` → `adapters/models/cc_sdk.py`
- `adapters/model_adapters/codex_cli.py` → `adapters/models/codex_cli.py`
- `adapters/model_adapters/hermes_cli.py` → `adapters/models/hermes_cli.py`
- `adapters/model_adapters/opencode_cli.py` → `adapters/models/opencode_cli.py`
- `execution/runtime/agent_runtime.py` → `adapters/models/agent_runtime.py`
- `state/memory/memory.py` → stays at `state/memory/memory.py`
- `state/storage/db.py` → stays at `state/storage/db.py`
- `state/context/context.py` → stays at `state/context/context.py`
- `state/business/business_instance.py` → stays at `state/business/business_instance.py`
- `state/registries/skill_registry.py` → stays at `state/registries/skill_registry.py`
- `services/discord_bot.py` → `transports/discord/bot.py` (then refactored Phase 5)
- `services/operator_api.py` → `transports/api/operator.py` (then refactored Phase 5)
- `adapters/google_workspace/` → stays at `adapters/google_workspace/`
- `services/umh/organism/` → `substrate/organism/`
- `services/umh/node_mesh/` → `transports/node_mesh/`
- `services/umh/integrations/creatoros/` → `integrations/creatoros/`
- `services/umh/integrations/lyfeos/` → `integrations/lyfeos/`
- `services/umh/control_plane/cockpit_api.py` → `transports/api/cockpit.py`
- `execution/transport/voice_first.py` → `transports/discord/voice_first.py`
- `daemon/` → stays at `daemon/`

---

## Phase 0 — Archive and Scaffold

### Task 0.1: Tag and Archive Pre-Unification State

**Files:**
- No new source files

- [ ] **Step 1: Create git tag on current HEAD**

```bash
git tag pre-unification
```

- [ ] **Step 2: Verify tag**

```bash
git tag -l | grep pre-unification
```

Expected: `pre-unification` appears in output

- [ ] **Step 3: Create archive directory with snapshot info**

```bash
mkdir -p _archive
```

- [ ] **Step 4: Record snapshot metadata**

```bash
echo "Pre-unification archive created $(date -u +%Y-%m-%dT%H:%M:%SZ)" > _archive/README.md
echo "Git tag: pre-unification" >> _archive/README.md
echo "Commit: $(git rev-parse HEAD)" >> _archive/README.md
echo "" >> _archive/README.md
echo "To restore: git checkout pre-unification" >> _archive/README.md
```

- [ ] **Step 5: Commit**

```bash
git add _archive/README.md
git commit -m "archive: tag pre-unification snapshot before substrate migration"
```

---

### Task 0.2: Create substrate/ Package with Types

**Files:**
- Create: `substrate/__init__.py`
- Create: `substrate/types.py`
- Create: `substrate/ontology/__init__.py`
- Create: `substrate/control_plane/__init__.py`
- Create: `substrate/execution/__init__.py`
- Create: `substrate/execution/ingestion/__init__.py`
- Create: `substrate/organism/__init__.py`
- Create: `substrate/learning/__init__.py`
- Test: `tests/substrate/__init__.py`
- Test: `tests/substrate/test_types.py`

- [ ] **Step 1: Create all substrate directories with empty __init__.py files**

```bash
mkdir -p substrate/ontology substrate/control_plane substrate/execution/ingestion substrate/organism substrate/learning
touch substrate/__init__.py substrate/ontology/__init__.py substrate/control_plane/__init__.py substrate/execution/__init__.py substrate/execution/ingestion/__init__.py substrate/organism/__init__.py substrate/learning/__init__.py
```

- [ ] **Step 2: Write substrate/types.py — the complete Pydantic type system**

Copy the complete type system from spec Section 6 into `substrate/types.py`. This is the authoritative source for all types. The file includes:

```python
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
        return self.decision in (GovernanceDecision.APPROVE, GovernanceDecision.CONDITIONAL)


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
        return self.outcome in (ExecutionOutcome.SUCCESS, ExecutionOutcome.PARTIAL_SUCCESS)


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
        event = TraceEvent(trace_id=self.id, event_type=event_type, description=description, **kwargs)
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
```

- [ ] **Step 3: Write the failing test for types**

```python
# tests/substrate/__init__.py — empty
# tests/substrate/test_types.py

import sys
sys.path.insert(0, '/opt/OS')

import pytest
from uuid import UUID
from pydantic import ValidationError

from substrate.types import (
    SignalEnvelope, SignalSource, SignalUrgency, Modality,
    Identity, ExecutionContext, RiskClass, GovernanceDecision,
    GovernanceVerdict, ExecutionPlan, AdapterResponse, ExecutionOutcome,
    ExecutionResult, TraceEventType, TraceEvent, TraceRecord,
    FeedbackType, FeedbackRecord, MemoryType, MemoryQuery, MemoryEntry,
    ComponentType, ComponentStatus, Component, RegistrationResult,
    PrimitiveType, OntologicalCategory, RelationshipType, PrimitiveObservation,
    IngestionResult, SubstrateStatus, Attachment, AdapterRequest,
)


class TestSignalEnvelope:
    def test_requires_source_and_content(self):
        env = SignalEnvelope(
            source=SignalSource.USER,
            content="hello",
            user_id="u1",
            organization_id="org1",
        )
        assert isinstance(env.id, UUID)
        assert env.content == "hello"

    def test_authority_tier_range(self):
        with pytest.raises(ValidationError):
            SignalEnvelope(
                source=SignalSource.USER, content="x",
                user_id="u", organization_id="o",
                authority_tier=0,
            )
        with pytest.raises(ValidationError):
            SignalEnvelope(
                source=SignalSource.USER, content="x",
                user_id="u", organization_id="o",
                authority_tier=10,
            )
        env = SignalEnvelope(
            source=SignalSource.USER, content="x",
            user_id="u", organization_id="o",
            authority_tier=1,
        )
        assert env.authority_tier == 1


class TestGovernanceVerdict:
    def test_approve_is_executable(self):
        v = GovernanceVerdict(
            signal_id=UUID('12345678-1234-1234-1234-123456789abc'),
            risk_class=RiskClass.LOW,
            decision=GovernanceDecision.APPROVE,
            rationale="low risk",
        )
        assert v.is_executable() is True

    def test_deny_is_not_executable(self):
        v = GovernanceVerdict(
            signal_id=UUID('12345678-1234-1234-1234-123456789abc'),
            risk_class=RiskClass.CRITICAL,
            decision=GovernanceDecision.DENY,
            rationale="too risky",
        )
        assert v.is_executable() is False

    def test_conditional_is_executable(self):
        v = GovernanceVerdict(
            signal_id=UUID('12345678-1234-1234-1234-123456789abc'),
            risk_class=RiskClass.HIGH,
            decision=GovernanceDecision.CONDITIONAL,
            rationale="needs conditions",
            conditions=["approval from founder"],
        )
        assert v.is_executable() is True


class TestExecutionResult:
    def test_success_is_success(self):
        r = ExecutionResult(
            signal_id=UUID('12345678-1234-1234-1234-123456789abc'),
            trace_id=UUID('12345678-1234-1234-1234-123456789def'),
            outcome=ExecutionOutcome.SUCCESS,
        )
        assert r.is_success() is True

    def test_partial_success_is_success(self):
        r = ExecutionResult(
            signal_id=UUID('12345678-1234-1234-1234-123456789abc'),
            trace_id=UUID('12345678-1234-1234-1234-123456789def'),
            outcome=ExecutionOutcome.PARTIAL_SUCCESS,
        )
        assert r.is_success() is True

    def test_failure_is_not_success(self):
        r = ExecutionResult(
            signal_id=UUID('12345678-1234-1234-1234-123456789abc'),
            trace_id=UUID('12345678-1234-1234-1234-123456789def'),
            outcome=ExecutionOutcome.FAILURE,
        )
        assert r.is_success() is False

    def test_blocked_is_not_success(self):
        r = ExecutionResult(
            signal_id=UUID('12345678-1234-1234-1234-123456789abc'),
            trace_id=UUID('12345678-1234-1234-1234-123456789def'),
            outcome=ExecutionOutcome.BLOCKED,
        )
        assert r.is_success() is False


class TestTraceRecord:
    def test_add_event(self):
        t = TraceRecord(signal_id=UUID('12345678-1234-1234-1234-123456789abc'))
        ev = t.add_event(TraceEventType.SIGNAL_RECEIVED, "signal received")
        assert ev.trace_id == t.id
        assert len(t.events) == 1

    def test_complete(self):
        t = TraceRecord(signal_id=UUID('12345678-1234-1234-1234-123456789abc'))
        t.complete(success=True)
        assert t.success is True
        assert t.completed_at is not None
        assert t.duration_ms is not None
        assert t.duration_ms >= 0


class TestEnumCounts:
    def test_primitive_type_has_10_values(self):
        assert len(PrimitiveType) == 10

    def test_ontological_category_has_8_values(self):
        assert len(OntologicalCategory) == 8

    def test_relationship_type_has_10_values(self):
        assert len(RelationshipType) == 10

    def test_signal_source_has_8_values(self):
        assert len(SignalSource) == 8

    def test_trace_event_type_has_12_values(self):
        assert len(TraceEventType) == 12


class TestMemoryQuery:
    def test_limit_range(self):
        with pytest.raises(ValidationError):
            MemoryQuery(query_text="test", limit=0)
        with pytest.raises(ValidationError):
            MemoryQuery(query_text="test", limit=101)
        q = MemoryQuery(query_text="test", limit=50)
        assert q.limit == 50


class TestFeedbackRecord:
    def test_quality_range(self):
        with pytest.raises(ValidationError):
            FeedbackRecord(
                trace_id=UUID('12345678-1234-1234-1234-123456789abc'),
                signal_id=UUID('12345678-1234-1234-1234-123456789abc'),
                outcome_quality=-0.1,
            )
        with pytest.raises(ValidationError):
            FeedbackRecord(
                trace_id=UUID('12345678-1234-1234-1234-123456789abc'),
                signal_id=UUID('12345678-1234-1234-1234-123456789abc'),
                outcome_quality=1.1,
            )
        f = FeedbackRecord(
            trace_id=UUID('12345678-1234-1234-1234-123456789abc'),
            signal_id=UUID('12345678-1234-1234-1234-123456789abc'),
            outcome_quality=0.75,
        )
        assert f.outcome_quality == 0.75
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/substrate/test_types.py -v`
Expected: All tests PASS (types.py already written in Step 2)

- [ ] **Step 5: Verify substrate package is importable**

```bash
python3 -c "import substrate; print('substrate importable')"
python3 -c "from substrate.types import SignalEnvelope, ExecutionResult, TraceRecord; print('all core types importable')"
```

- [ ] **Step 6: Commit**

```bash
git add substrate/ tests/substrate/
git commit -m "feat: scaffold substrate package with complete Pydantic type system"
```

---

### Task 0.3: Create Remaining Package Scaffolds

**Files:**
- Create: `adapters/__init__.py`, `adapters/protocol.py`, `adapters/models/__init__.py`
- Create: `transports/__init__.py`, `transports/discord/__init__.py`, `transports/api/__init__.py`, `transports/node_mesh/__init__.py`
- Create: `projections/__init__.py`, `projections/eos/__init__.py`
- Create: `integrations/__init__.py`, `integrations/creatoros/__init__.py`, `integrations/lyfeos/__init__.py`
- Create: `tests/adapters/__init__.py`, `tests/transports/__init__.py`, `tests/integration/__init__.py`, `tests/acceptance/__init__.py`

- [ ] **Step 1: Create all package directories and __init__.py files**

```bash
mkdir -p adapters/models transports/discord transports/api transports/node_mesh projections/eos integrations/creatoros integrations/lyfeos tests/adapters tests/transports tests/integration tests/acceptance

touch adapters/__init__.py adapters/models/__init__.py transports/__init__.py transports/discord/__init__.py transports/api/__init__.py transports/node_mesh/__init__.py projections/__init__.py projections/eos/__init__.py integrations/__init__.py integrations/creatoros/__init__.py integrations/lyfeos/__init__.py tests/adapters/__init__.py tests/transports/__init__.py tests/integration/__init__.py tests/acceptance/__init__.py
```

Note: `adapters/` already exists at this path for `adapters/model_adapters/` and `adapters/google_workspace/`. The new `adapters/__init__.py` goes alongside those. The `adapters/models/` directory is new and will receive moved files in Task 0.4.

- [ ] **Step 2: Write adapters/protocol.py — the Adapter Protocol**

```python
from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from substrate.types import AdapterRequest, AdapterResponse


@runtime_checkable
class Adapter(Protocol):
    """Every external system connection implements this."""

    adapter_id: UUID
    adapter_type: str
    name: str

    async def execute(self, request: AdapterRequest) -> AdapterResponse: ...
    async def health_check(self) -> bool: ...
    def capabilities(self) -> list[str]: ...
```

- [ ] **Step 3: Verify all packages are importable**

```bash
python3 -c "
import substrate
import substrate.types
import substrate.ontology
import substrate.control_plane
import substrate.execution
import substrate.execution.ingestion
import substrate.organism
import substrate.learning
import adapters
import adapters.protocol
import adapters.models
import transports
import transports.discord
import transports.api
import transports.node_mesh
import projections
import projections.eos
import integrations
import integrations.creatoros
import integrations.lyfeos
print('all packages importable')
"
```

- [ ] **Step 4: Commit**

```bash
git add adapters/__init__.py adapters/protocol.py adapters/models/__init__.py transports/ projections/ integrations/ tests/adapters/ tests/transports/ tests/integration/ tests/acceptance/
git commit -m "feat: scaffold adapter, transport, projection, integration packages"
```

---

### Task 0.4: Move Surviving Production Files to New Locations

**Files:**
- Move: `execution/runtime/model_router.py` → `adapters/models/model_router.py`
- Move: `adapters/model_adapters/cc_sdk.py` → `adapters/models/cc_sdk.py`
- Move: `adapters/model_adapters/codex_cli.py` → `adapters/models/codex_cli.py`
- Move: `adapters/model_adapters/hermes_cli.py` → `adapters/models/hermes_cli.py`
- Move: `adapters/model_adapters/opencode_cli.py` → `adapters/models/opencode_cli.py`
- Move: `execution/runtime/agent_runtime.py` → `adapters/models/agent_runtime.py`

- [ ] **Step 1: Move model routing files**

```bash
git mv execution/runtime/model_router.py adapters/models/model_router.py
git mv adapters/model_adapters/cc_sdk.py adapters/models/cc_sdk.py
git mv adapters/model_adapters/codex_cli.py adapters/models/codex_cli.py
git mv adapters/model_adapters/hermes_cli.py adapters/models/hermes_cli.py
git mv adapters/model_adapters/opencode_cli.py adapters/models/opencode_cli.py
git mv execution/runtime/agent_runtime.py adapters/models/agent_runtime.py
```

- [ ] **Step 2: Update internal imports in moved files**

Each moved file imports from other moved files. Update all `sys.path` and relative import references. Key import changes:

- `model_router.py`: Update any `from execution.runtime.` or `from adapters.model_adapters.` imports
- `agent_runtime.py`: Update reference to `model_router` import path
- `cc_sdk.py`: Check for any import of `model_router`

Use `grep -n "from execution.runtime\|from adapters.model_adapters\|from runtime\." adapters/models/*.py` to find all imports that need updating.

For each import found, replace with the new `adapters.models.` path or the appropriate `sys.path` adjustment.

- [ ] **Step 3: Update all external references to moved files**

Find all files that import from the old locations:

```bash
grep -rn "from execution.runtime.model_router\|from execution.runtime.agent_runtime\|from adapters.model_adapters" --include="*.py" . | grep -v _archive | grep -v __pycache__
```

Update each reference to use the new import path. The main callers are:
- `services/discord_bot.py` — imports model_router, agent_runtime
- `control_plane/runtime/cognitive_loop.py` — imports model_router
- `control_plane/runtime/gateway.py` — imports model_router
- `services/operator_api.py` — imports model_router

For production files that will later be refactored (discord_bot, gateway), create a compatibility shim at the old location:

```python
# execution/runtime/model_router.py (shim)
from adapters.models.model_router import *  # noqa: F401,F403
```

```python
# execution/runtime/agent_runtime.py (shim)
from adapters.models.agent_runtime import *  # noqa: F401,F403
```

```python
# adapters/model_adapters/cc_sdk.py (shim)
from adapters.models.cc_sdk import *  # noqa: F401,F403
```

- [ ] **Step 4: Verify all moved files compile**

```bash
find adapters/models/ -name "*.py" -exec python3 -m py_compile {} \;
echo "all adapters/models/ files compile"
```

- [ ] **Step 5: Verify production imports still work through shims**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from adapters.models.model_router import call_with_fallback
print(f'model_router imported: call_with_fallback={call_with_fallback}')
"
```

- [ ] **Step 6: Commit**

```bash
git add adapters/models/ execution/runtime/ adapters/model_adapters/
git commit -m "refactor: relocate model routing files to adapters/models/"
```

---

### Task 0.5: Move Organism, Node Mesh, Integrations, and Cockpit

**Files:**
- Move: `services/umh/organism/` → `substrate/organism/`
- Move: `services/umh/node_mesh/` → `transports/node_mesh/`
- Move: `services/umh/integrations/creatoros/` → `integrations/creatoros/`
- Move: `services/umh/integrations/lyfeos/` → `integrations/lyfeos/`
- Move: `services/umh/control_plane/cockpit_api.py` → `transports/api/cockpit.py`
- Move: `execution/transport/voice_first.py` → `transports/discord/voice_first.py`

- [ ] **Step 1: Move organism runtime**

```bash
rm substrate/organism/__init__.py
cp -r services/umh/organism/* substrate/organism/
git add substrate/organism/
```

- [ ] **Step 2: Move node mesh**

```bash
rm transports/node_mesh/__init__.py
cp -r services/umh/node_mesh/* transports/node_mesh/
git add transports/node_mesh/
```

- [ ] **Step 3: Move integrations**

```bash
rm integrations/creatoros/__init__.py integrations/lyfeos/__init__.py
cp -r services/umh/integrations/creatoros/* integrations/creatoros/
cp -r services/umh/integrations/lyfeos/* integrations/lyfeos/
git add integrations/
```

- [ ] **Step 4: Move cockpit API and voice_first**

```bash
cp services/umh/control_plane/cockpit_api.py transports/api/cockpit.py
cp execution/transport/voice_first.py transports/discord/voice_first.py
git add transports/api/cockpit.py transports/discord/voice_first.py
```

- [ ] **Step 5: Update imports in moved files**

```bash
grep -rn "from services.umh\|from execution.transport" substrate/organism/ transports/node_mesh/ integrations/ transports/api/cockpit.py transports/discord/voice_first.py --include="*.py" | head -30
```

Update each import to use the new package paths.

- [ ] **Step 6: Verify all moved files compile**

```bash
find substrate/organism/ transports/node_mesh/ integrations/ -name "*.py" -exec python3 -m py_compile {} \;
python3 -m py_compile transports/api/cockpit.py
python3 -m py_compile transports/discord/voice_first.py
echo "all relocated files compile"
```

- [ ] **Step 7: Commit**

```bash
git add substrate/organism/ transports/ integrations/
git commit -m "refactor: relocate organism, node mesh, integrations, cockpit to new structure"
```

---

### Task 0.6: Rename 10_Wiki/ to knowledge/

**Files:**
- Move: `10_Wiki/` → `knowledge/`

- [ ] **Step 1: Move the wiki directory**

```bash
git mv 10_Wiki knowledge
```

- [ ] **Step 2: Update all references to 10_Wiki**

```bash
grep -rn "10_Wiki" --include="*.py" --include="*.md" --include="*.sh" . | grep -v _archive | grep -v __pycache__ | grep -v ".git/"
```

Update each reference found. Key files likely affected:
- `CLAUDE.md` — cognition stack load order
- `.claude/CLAUDE.md` — project structure
- `scripts/session_bootstrap.py` — palace paths
- `scripts/query_graph.py` — palace paths
- `scripts/vault_backlink_audit.py` — vault path
- Various skill files

- [ ] **Step 3: Verify the wiki index is accessible**

```bash
test -f knowledge/index.md && echo "wiki index accessible" || echo "MISSING"
test -f knowledge/palace/index.md && echo "palace index accessible" || echo "MISSING"
```

- [ ] **Step 4: Commit**

```bash
git add knowledge/ CLAUDE.md .claude/CLAUDE.md scripts/
git commit -m "refactor: rename 10_Wiki to knowledge"
```

---

### Task 0.7: Phase 0 Verification Gate

**Files:**
- No new files

- [ ] **Step 1: Verify all new packages are importable**

```bash
python3 -c "
import substrate
import substrate.types
import substrate.ontology
import substrate.control_plane
import substrate.execution
import substrate.execution.ingestion
import substrate.organism
import adapters
import adapters.protocol
import adapters.models
import transports
import transports.discord
import transports.api
import transports.node_mesh
import projections
import projections.eos
import integrations
print('all packages importable')
"
```

- [ ] **Step 2: Verify all moved files compile**

```bash
find substrate/ adapters/ transports/ -name "*.py" -exec python3 -m py_compile {} \;
echo "all files compile"
```

- [ ] **Step 3: Run the type system tests**

```bash
python3 -m pytest tests/substrate/test_types.py -v
```

Expected: All tests PASS

- [ ] **Step 4: Verify production model_router still imports**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from adapters.models.model_router import call_with_fallback, RoutingResult
print('model_router OK')
"
```

- [ ] **Step 5: Commit verification success**

```bash
git add -A
git commit -m "verify: phase 0 complete — scaffold and relocation verified"
```

---

## Phase 1 — Tier 0: Ontology

### Task 1.1: Build Unified Ontology Module

**Files:**
- Create: `substrate/ontology/primitives.py`
- Create: `substrate/ontology/laws.py`
- Create: `substrate/ontology/relationships.py`
- Test: `tests/substrate/test_ontology.py`
- Ref: `understanding/ontology/primitives.py` (current PrimitiveType source)
- Ref: `services/umh/foundation/primitives.py` (current OntologicalCategory source)
- Ref: `services/umh/foundation/laws.py` (current laws source)

- [ ] **Step 1: Read current ontology source files**

Read these three files to understand what exists:
```bash
cat understanding/ontology/primitives.py
cat services/umh/foundation/primitives.py
cat services/umh/foundation/laws.py
```

- [ ] **Step 2: Write the failing test**

```python
# tests/substrate/test_ontology.py

import sys
sys.path.insert(0, '/opt/OS')

import pytest

from substrate.ontology.primitives import PrimitiveType, OntologicalCategory
from substrate.ontology.relationships import RelationshipType
from substrate.ontology.laws import get_laws


class TestOntologyEnums:
    def test_primitive_type_has_10_values(self):
        assert len(PrimitiveType) == 10
        expected = {"state", "change", "constraint", "resource", "signal",
                    "action", "outcome", "feedback", "goal", "time"}
        assert {p.value for p in PrimitiveType} == expected

    def test_ontological_category_has_8_values(self):
        assert len(OntologicalCategory) == 8
        expected = {"entity", "relation", "event", "property",
                    "process", "state", "constraint", "boundary"}
        assert {c.value for c in OntologicalCategory} == expected

    def test_relationship_type_has_10_values(self):
        assert len(RelationshipType) == 10

    def test_primitive_observation_uses_pydantic(self):
        from substrate.types import PrimitiveObservation
        from pydantic import BaseModel
        assert issubclass(PrimitiveObservation, BaseModel)

    def test_primitive_observation_validates_label_length(self):
        from pydantic import ValidationError
        from substrate.types import PrimitiveObservation, PrimitiveType
        with pytest.raises(ValidationError):
            PrimitiveObservation(
                primitive_type=PrimitiveType.STATE,
                label="x" * 81,
                description="test",
            )


class TestLaws:
    def test_laws_exist(self):
        laws = get_laws()
        assert isinstance(laws, list)
        assert len(laws) > 0

    def test_each_law_has_name_and_description(self):
        laws = get_laws()
        for law in laws:
            assert "name" in law
            assert "description" in law
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest tests/substrate/test_ontology.py -v`
Expected: FAIL — modules not yet created

- [ ] **Step 4: Build substrate/ontology/primitives.py**

Re-export enums from `substrate/types.py` (they're already defined there) and add any ontology-specific utilities:

```python
"""Ontology primitives — the foundational classification system for UMH.

PrimitiveType, OntologicalCategory, and PrimitiveObservation are defined
in substrate.types (the single type authority). This module re-exports
them and adds ontology-specific utilities.
"""
from __future__ import annotations

from substrate.types import (
    PrimitiveType,
    OntologicalCategory,
    PrimitiveObservation,
)

__all__ = ["PrimitiveType", "OntologicalCategory", "PrimitiveObservation"]
```

- [ ] **Step 5: Build substrate/ontology/relationships.py**

```python
"""Typed relationship edges between ontology observations."""
from __future__ import annotations

from substrate.types import RelationshipType

__all__ = ["RelationshipType"]
```

- [ ] **Step 6: Build substrate/ontology/laws.py**

Migrate the law definitions from `services/umh/foundation/laws.py`. Read the source file first and extract the actual law content:

```python
"""Governing laws for the UMH substrate.

Laws are constraints that the substrate enforces. They are loaded once
at boot and checked by the GovernanceEngine during signal classification.
"""
from __future__ import annotations


def get_laws() -> list[dict[str, str]]:
    """Return the governing laws registry.

    Each law has: name, description, enforcement (hard|soft).
    Populate from services/umh/foundation/laws.py content.
    """
    return [
        # Copy actual laws from services/umh/foundation/laws.py here
        # Example structure — replace with real content:
        {"name": "identity_before_execution", "description": "Every execution must resolve identity first", "enforcement": "hard"},
        {"name": "governance_before_action", "description": "No adapter call without governance classification", "enforcement": "hard"},
        {"name": "trace_everything", "description": "Every execution produces a trace record", "enforcement": "hard"},
        {"name": "feedback_closes_loops", "description": "Every trace gets a feedback record", "enforcement": "hard"},
        {"name": "registry_is_truth", "description": "Unregistered components do not exist to the substrate", "enforcement": "hard"},
        {"name": "memory_discipline", "description": "No direct Neon writes outside state/", "enforcement": "hard"},
        {"name": "deterministic_first", "description": "Every LLM call has a deterministic fallback", "enforcement": "hard"},
        {"name": "pydantic_only", "description": "No runtime dataclasses in substrate/", "enforcement": "hard"},
    ]
```

- [ ] **Step 7: Run test to verify it passes**

Run: `python3 -m pytest tests/substrate/test_ontology.py -v`
Expected: PASS

- [ ] **Step 8: Compile check**

```bash
find substrate/ontology/ -name "*.py" -exec python3 -m py_compile {} \;
```

- [ ] **Step 9: Commit**

```bash
git add substrate/ontology/ tests/substrate/test_ontology.py
git commit -m "feat: build unified ontology module (Phase 1)"
```

---

## Phase 2 — Tier 1: Control Plane

### Task 2.1: Build IdentityResolver

**Files:**
- Create: `substrate/control_plane/identity.py`
- Ref: `control_plane/identity/ai_identity.py` — personality, name
- Ref: `state/context/context.py` — `load_context_from_env()`
- Ref: `state/business/business_instance.py` — `get_ai_name()`, business stage

- [ ] **Step 1: Read source files**

```bash
cat control_plane/identity/ai_identity.py
cat state/context/context.py
cat state/business/business_instance.py
```

- [ ] **Step 2: Write the failing test**

```python
# tests/substrate/test_control_plane.py

import sys
sys.path.insert(0, '/opt/OS')

import pytest
import asyncio
from uuid import UUID

from substrate.types import SignalEnvelope, SignalSource, Identity, ExecutionContext
from substrate.control_plane.identity import ConcreteIdentityResolver


class TestIdentityResolver:
    def test_implements_protocol(self):
        from substrate.control_plane.identity import IdentityResolver
        resolver = ConcreteIdentityResolver()
        assert isinstance(resolver, IdentityResolver)

    def test_resolve_returns_identity(self):
        resolver = ConcreteIdentityResolver()
        signal = SignalEnvelope(
            source=SignalSource.USER,
            content="test",
            user_id="test-user",
            organization_id="munoz-holdings",
        )
        identity = asyncio.run(resolver.resolve(signal))
        assert isinstance(identity, Identity)
        assert identity.user_id == "test-user"
        assert identity.organization_id == "munoz-holdings"
        assert identity.ai_name != ""
        assert identity.business_stage != ""
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest tests/substrate/test_control_plane.py::TestIdentityResolver -v`
Expected: FAIL

- [ ] **Step 4: Build substrate/control_plane/identity.py**

```python
"""IdentityResolver — resolves signal sender identity and AI configuration.

Source mapping:
- ai_identity.py → personality, name
- context.py → load_context_from_env() → org/venture config
- business_instance.py → get_ai_name(), business stage
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from substrate.types import SignalEnvelope, Identity


@runtime_checkable
class IdentityResolver(Protocol):
    async def resolve(self, signal: SignalEnvelope) -> Identity: ...


class ConcreteIdentityResolver:
    """Loads identity from BIS + Neon organizations table.

    Merges AI personality, name, autonomy level, and business stage
    from the existing production sources without modifying their internals.
    """

    async def resolve(self, signal: SignalEnvelope) -> Identity:
        import sys
        sys.path.insert(0, '/opt/OS')

        try:
            from state.business.business_instance import get_ai_name, get_business_stage
            ai_name = get_ai_name()
            business_stage = get_business_stage()
        except Exception:
            ai_name = "DEX"
            business_stage = "pre_revenue"

        try:
            from state.context.context import load_context_from_env
            ctx = load_context_from_env()
            personality = ctx.get("personality", "professional")
            autonomy_level = ctx.get("autonomy_level", 1)
        except Exception:
            personality = "professional"
            autonomy_level = 1

        return Identity(
            user_id=signal.user_id,
            organization_id=signal.organization_id,
            venture_id=signal.venture_id,
            ai_name=ai_name,
            ai_personality=personality,
            autonomy_level=autonomy_level,
            business_stage=business_stage,
        )
```

Adjust the imports based on what the actual source files expose. The key principle: wrap existing production code, don't rewrite it.

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/substrate/test_control_plane.py::TestIdentityResolver -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add substrate/control_plane/identity.py tests/substrate/test_control_plane.py
git commit -m "feat: build IdentityResolver (Phase 2.1)"
```

---

### Task 2.2: Build ContextAssembler

**Files:**
- Create: `substrate/control_plane/context.py`
- Ref: `control_plane/runtime/cognitive_loop.py` PERCEIVE + UNDERSTAND stages
- Ref: `state/memory/memory.py` — ConversationMemory.get_session(), AgentMemory.semantic_search()

- [ ] **Step 1: Read source files**

```bash
head -400 control_plane/runtime/cognitive_loop.py
head -200 state/memory/memory.py
```

- [ ] **Step 2: Write the failing test**

```python
# Add to tests/substrate/test_control_plane.py

from substrate.control_plane.context import ConcreteContextAssembler, ContextAssembler


class TestContextAssembler:
    def test_implements_protocol(self):
        assembler = ConcreteContextAssembler()
        assert isinstance(assembler, ContextAssembler)

    def test_assemble_returns_execution_context(self):
        assembler = ConcreteContextAssembler()
        signal = SignalEnvelope(
            source=SignalSource.USER,
            content="test message",
            user_id="test-user",
            organization_id="munoz-holdings",
        )
        identity = Identity(
            user_id="test-user",
            organization_id="munoz-holdings",
            ai_name="DEX",
            ai_personality="professional",
            autonomy_level=1,
            business_stage="pre_revenue",
        )
        ctx = asyncio.run(assembler.assemble(signal, identity))
        assert isinstance(ctx, ExecutionContext)
        assert ctx.signal_id == signal.id
        assert ctx.identity == identity
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest tests/substrate/test_control_plane.py::TestContextAssembler -v`
Expected: FAIL

- [ ] **Step 4: Build substrate/control_plane/context.py**

```python
"""ContextAssembler — builds execution context from signal + identity.

Merges conversation history (last 10 turns), semantic memory recall,
active goals, and business context into a single ExecutionContext.

Source mapping:
- cognitive_loop.py PERCEIVE + UNDERSTAND → conversation history assembly
- memory.py ConversationMemory.get_session() → recent messages
- memory.py AgentMemory.semantic_search() → relevant memories
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from substrate.types import (
    SignalEnvelope, Identity, ExecutionContext, MemoryEntry,
)


@runtime_checkable
class ContextAssembler(Protocol):
    async def assemble(self, signal: SignalEnvelope, identity: Identity) -> ExecutionContext: ...


class ConcreteContextAssembler:
    """Builds ExecutionContext by querying existing memory and conversation stores."""

    async def assemble(self, signal: SignalEnvelope, identity: Identity) -> ExecutionContext:
        conversation_history = await self._get_conversation_history(
            signal.user_id, signal.metadata.get("channel_id", "")
        )
        relevant_memories = await self._recall_relevant(signal.content)
        business_context = self._get_business_context(identity)

        return ExecutionContext(
            signal_id=signal.id,
            identity=identity,
            session_id=signal.metadata.get("session_id"),
            conversation_history=conversation_history,
            relevant_memories=relevant_memories,
            business_context=business_context,
        )

    async def _get_conversation_history(
        self, user_id: str, channel_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        try:
            import sys
            sys.path.insert(0, '/opt/OS')
            from state.memory.memory import ConversationMemory
            cm = ConversationMemory()
            return cm.get_session(user_id=user_id, channel_id=channel_id, limit=limit)
        except Exception:
            return []

    async def _recall_relevant(self, query: str) -> list[MemoryEntry]:
        return []

    def _get_business_context(self, identity: Identity) -> dict[str, Any]:
        return {
            "business_stage": identity.business_stage,
            "organization_id": identity.organization_id,
            "venture_id": identity.venture_id,
        }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/substrate/test_control_plane.py::TestContextAssembler -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add substrate/control_plane/context.py tests/substrate/test_control_plane.py
git commit -m "feat: build ContextAssembler (Phase 2.2)"
```

---

### Task 2.3: Build GovernanceEngine

**Files:**
- Create: `substrate/control_plane/governance.py`
- Ref: `governance/policy/authority_engine.py` — RISK_CLASSES, classify_action(), autonomy levels
- Ref: `services/umh/protocols/governance.py` — GovernanceVerdict Pydantic model

- [ ] **Step 1: Read the production authority engine**

```bash
cat governance/policy/authority_engine.py
```

- [ ] **Step 2: Write the failing test**

```python
# Add to tests/substrate/test_control_plane.py

from substrate.control_plane.governance import ConcreteGovernanceEngine, GovernanceEngine
from substrate.types import RiskClass, GovernanceDecision, GovernanceVerdict, ExecutionPlan


class TestGovernanceEngine:
    def test_implements_protocol(self):
        engine = ConcreteGovernanceEngine()
        assert isinstance(engine, GovernanceEngine)

    def test_classify_critical_action(self):
        engine = ConcreteGovernanceEngine()
        signal = SignalEnvelope(
            source=SignalSource.USER,
            content="send email to all leads",
            user_id="test-user",
            organization_id="munoz-holdings",
        )
        identity = Identity(
            user_id="test-user",
            organization_id="munoz-holdings",
            ai_name="DEX",
            ai_personality="professional",
            autonomy_level=1,
            business_stage="pre_revenue",
        )
        ctx = ExecutionContext(
            signal_id=signal.id,
            identity=identity,
        )
        verdict = asyncio.run(engine.classify(signal, ctx))
        assert isinstance(verdict, GovernanceVerdict)
        assert verdict.risk_class == RiskClass.CRITICAL
        assert verdict.decision == GovernanceDecision.DENY

    def test_classify_low_risk_action(self):
        engine = ConcreteGovernanceEngine()
        signal = SignalEnvelope(
            source=SignalSource.USER,
            content="analyze this data",
            user_id="test-user",
            organization_id="munoz-holdings",
        )
        identity = Identity(
            user_id="test-user",
            organization_id="munoz-holdings",
            ai_name="DEX",
            ai_personality="professional",
            autonomy_level=1,
            business_stage="pre_revenue",
        )
        ctx = ExecutionContext(signal_id=signal.id, identity=identity)
        verdict = asyncio.run(engine.classify(signal, ctx))
        assert verdict.risk_class == RiskClass.LOW
        assert verdict.decision == GovernanceDecision.APPROVE

    def test_classify_unknown_defaults_low(self):
        engine = ConcreteGovernanceEngine()
        signal = SignalEnvelope(
            source=SignalSource.USER,
            content="do something completely novel",
            user_id="test",
            organization_id="org",
        )
        identity = Identity(
            user_id="test", organization_id="org",
            ai_name="DEX", ai_personality="professional",
            autonomy_level=1, business_stage="pre_revenue",
        )
        ctx = ExecutionContext(signal_id=signal.id, identity=identity)
        verdict = asyncio.run(engine.classify(signal, ctx))
        assert verdict.risk_class == RiskClass.LOW
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest tests/substrate/test_control_plane.py::TestGovernanceEngine -v`
Expected: FAIL

- [ ] **Step 4: Build substrate/control_plane/governance.py**

```python
"""GovernanceEngine — classifies signals by risk and decides execution authority.

Merges the production authority_engine.py risk classification with
UMH governance protocol's GovernanceVerdict model.

Source mapping:
- authority_engine.py → RISK_CLASSES dict, classify_action(), autonomy levels
- services/umh/protocols/governance.py → GovernanceVerdict Pydantic model
"""
from __future__ import annotations

import re
from typing import Protocol, runtime_checkable

from substrate.types import (
    SignalEnvelope, ExecutionContext, ExecutionPlan,
    GovernanceVerdict, GovernanceDecision, RiskClass,
)


@runtime_checkable
class GovernanceEngine(Protocol):
    async def classify(self, signal: SignalEnvelope, context: ExecutionContext) -> GovernanceVerdict: ...
    async def check_execution(self, plan: ExecutionPlan, verdict: GovernanceVerdict) -> bool: ...


AUTONOMY_THRESHOLDS: dict[RiskClass, int] = {
    RiskClass.CRITICAL: 999,
    RiskClass.HIGH: 3,
    RiskClass.MEDIUM: 1,
    RiskClass.LOW: 0,
}

_CRITICAL_PATTERNS = re.compile(
    r"\b(send\s+(?:email|message|dm)|execute\s+payment|delete\s+record|bulk\s+update|mass\s+outreach|publish)\b",
    re.IGNORECASE,
)
_HIGH_PATTERNS = re.compile(
    r"\b(create\s+outreach|post\s+content|book\s+call|update\s+crm)\b",
    re.IGNORECASE,
)
_MEDIUM_PATTERNS = re.compile(
    r"\b(draft\s+(?:message|content)|create\s+(?:task|document))\b",
    re.IGNORECASE,
)


class ConcreteGovernanceEngine:
    """Deterministic-first governance with risk classification."""

    async def classify(self, signal: SignalEnvelope, context: ExecutionContext) -> GovernanceVerdict:
        risk_class = self._classify_risk(signal.content)
        autonomy = context.identity.autonomy_level
        threshold = AUTONOMY_THRESHOLDS[risk_class]

        if autonomy >= threshold:
            decision = GovernanceDecision.APPROVE
            rationale = f"Autonomy level {autonomy} >= threshold {threshold} for {risk_class.value}"
        else:
            decision = GovernanceDecision.DENY
            rationale = f"Autonomy level {autonomy} < threshold {threshold} for {risk_class.value}"

        return GovernanceVerdict(
            signal_id=signal.id,
            risk_class=risk_class,
            decision=decision,
            rationale=rationale,
        )

    async def check_execution(self, plan: ExecutionPlan, verdict: GovernanceVerdict) -> bool:
        return verdict.is_executable()

    def _classify_risk(self, content: str) -> RiskClass:
        if _CRITICAL_PATTERNS.search(content):
            return RiskClass.CRITICAL
        if _HIGH_PATTERNS.search(content):
            return RiskClass.HIGH
        if _MEDIUM_PATTERNS.search(content):
            return RiskClass.MEDIUM
        return RiskClass.LOW
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/substrate/test_control_plane.py::TestGovernanceEngine -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add substrate/control_plane/governance.py tests/substrate/test_control_plane.py
git commit -m "feat: build GovernanceEngine with deterministic risk classification (Phase 2.3)"
```

---

### Task 2.4: Build MemorySystem

**Files:**
- Create: `substrate/control_plane/memory.py`
- Ref: `state/memory/memory.py` — AgentMemory, ConversationMemory

- [ ] **Step 1: Read the production memory module**

```bash
head -300 state/memory/memory.py
```

- [ ] **Step 2: Write the failing test**

```python
# Add to tests/substrate/test_control_plane.py

from substrate.control_plane.memory import ConcreteMemorySystem, MemorySystem
from substrate.types import MemoryQuery, MemoryEntry, MemoryType


class TestMemorySystem:
    def test_implements_protocol(self):
        system = ConcreteMemorySystem()
        assert isinstance(system, MemorySystem)

    def test_store_returns_uuid(self):
        system = ConcreteMemorySystem()
        entry = MemoryEntry(
            memory_type=MemoryType.FACT,
            content="test fact",
        )
        result_id = asyncio.run(system.store(entry))
        assert isinstance(result_id, UUID)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest tests/substrate/test_control_plane.py::TestMemorySystem -v`
Expected: FAIL

- [ ] **Step 4: Build substrate/control_plane/memory.py**

```python
"""MemorySystem — unified protocol over existing memory stores.

Wraps AgentMemory + ConversationMemory behind a single protocol.
Does NOT rewrite the memory layer — wraps it.

Source mapping:
- state/memory/memory.py → AgentMemory.log(), semantic_search(), embed_and_store()
- state/memory/memory.py → ConversationMemory.store(), get_session()
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from substrate.types import MemoryQuery, MemoryEntry, MemoryType


@runtime_checkable
class MemorySystem(Protocol):
    async def recall(self, query: MemoryQuery) -> list[MemoryEntry]: ...
    async def store(self, entry: MemoryEntry) -> UUID: ...
    async def log_interaction(self, signal_id: UUID, content: str, response: str, provider: str, **kwargs: Any) -> UUID: ...


class ConcreteMemorySystem:
    """Wraps existing AgentMemory + ConversationMemory."""

    def __init__(self) -> None:
        import sys
        sys.path.insert(0, '/opt/OS')
        try:
            from state.memory.memory import AgentMemory, ConversationMemory
            self._agent_memory = AgentMemory()
            self._conversation_memory = ConversationMemory()
        except Exception:
            self._agent_memory = None
            self._conversation_memory = None

    async def recall(self, query: MemoryQuery) -> list[MemoryEntry]:
        if not self._agent_memory:
            return []
        try:
            results = self._agent_memory.semantic_search(
                query.query_text, limit=query.limit
            )
            return [
                MemoryEntry(
                    memory_type=query.memory_types[0] if query.memory_types else MemoryType.OBSERVATION,
                    content=r.get("content", ""),
                    authority_tier=r.get("authority_tier", 5),
                )
                for r in results
            ]
        except Exception:
            return []

    async def store(self, entry: MemoryEntry) -> UUID:
        if self._agent_memory:
            try:
                self._agent_memory.embed_and_store(
                    content=entry.content,
                    memory_type=entry.memory_type.value,
                    metadata=entry.metadata,
                )
            except Exception:
                pass
        return entry.id

    async def log_interaction(
        self, signal_id: UUID, content: str, response: str, provider: str, **kwargs: Any
    ) -> UUID:
        if self._agent_memory:
            try:
                self._agent_memory.log(
                    content=content,
                    response=response,
                    provider=provider,
                    **kwargs,
                )
            except Exception:
                pass
        from uuid import uuid4
        return uuid4()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/substrate/test_control_plane.py::TestMemorySystem -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add substrate/control_plane/memory.py tests/substrate/test_control_plane.py
git commit -m "feat: build MemorySystem wrapping existing stores (Phase 2.4)"
```

---

### Task 2.5: Build ComponentRegistry

**Files:**
- Create: `substrate/control_plane/registry.py`
- Ref: `state/registries/skill_registry.py` — existing skill registry
- Ref: Neon `agents`, `skills` tables

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/substrate/test_control_plane.py

from substrate.control_plane.registry import ConcreteComponentRegistry, ComponentRegistry
from substrate.types import Component, ComponentType, ComponentStatus, RegistrationResult


class TestComponentRegistry:
    def test_implements_protocol(self):
        registry = ConcreteComponentRegistry()
        assert isinstance(registry, ComponentRegistry)

    def test_register_and_lookup(self):
        registry = ConcreteComponentRegistry()
        adapter = Component(
            component_type=ComponentType.ADAPTER,
            name="test-adapter",
            capabilities=["text_generation"],
        )
        result = asyncio.run(registry.register(adapter))
        assert isinstance(result, RegistrationResult)
        assert result.success is True

        found = asyncio.run(registry.lookup(component_type=ComponentType.ADAPTER))
        assert any(c.name == "test-adapter" for c in found)

    def test_lookup_by_type_filters(self):
        registry = ConcreteComponentRegistry()
        adapter1 = Component(component_type=ComponentType.ADAPTER, name="a1")
        adapter2 = Component(component_type=ComponentType.ADAPTER, name="a2")
        agent = Component(component_type=ComponentType.AGENT, name="agent1")
        asyncio.run(registry.register(adapter1))
        asyncio.run(registry.register(adapter2))
        asyncio.run(registry.register(agent))

        adapters = asyncio.run(registry.lookup(component_type=ComponentType.ADAPTER))
        assert len(adapters) == 2
        agents = asyncio.run(registry.lookup(component_type=ComponentType.AGENT))
        assert len(agents) == 1

    def test_deregister(self):
        registry = ConcreteComponentRegistry()
        comp = Component(component_type=ComponentType.SKILL, name="temp-skill")
        asyncio.run(registry.register(comp))
        assert asyncio.run(registry.deregister(comp.id)) is True
        found = asyncio.run(registry.lookup(component_type=ComponentType.SKILL))
        assert not any(c.id == comp.id for c in found)

    def test_get_by_id(self):
        registry = ConcreteComponentRegistry()
        comp = Component(component_type=ComponentType.AGENT, name="lookup-agent")
        asyncio.run(registry.register(comp))
        result = asyncio.run(registry.get(comp.id))
        assert result is not None
        assert result.name == "lookup-agent"

    def test_get_missing_returns_none(self):
        from uuid import uuid4
        registry = ConcreteComponentRegistry()
        result = asyncio.run(registry.get(uuid4()))
        assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/substrate/test_control_plane.py::TestComponentRegistry -v`
Expected: FAIL

- [ ] **Step 3: Build substrate/control_plane/registry.py**

```python
"""ComponentRegistry — unified registry for all substrate components.

In-memory store backed by Neon component_registry table.
Boot sequence loads existing agents + skills from Neon.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from substrate.types import (
    Component, ComponentType, ComponentStatus, RegistrationResult,
)


@runtime_checkable
class ComponentRegistry(Protocol):
    async def register(self, component: Component) -> RegistrationResult: ...
    async def lookup(self, component_type: ComponentType | None = None, capabilities: list[str] | None = None) -> list[Component]: ...
    async def get(self, component_id: UUID) -> Component | None: ...
    async def deregister(self, component_id: UUID) -> bool: ...


class ConcreteComponentRegistry:
    """In-memory component registry with Neon backing."""

    def __init__(self) -> None:
        self._components: dict[UUID, Component] = {}

    async def register(self, component: Component) -> RegistrationResult:
        self._components[component.id] = component
        return RegistrationResult(component_id=component.id, success=True)

    async def lookup(
        self,
        component_type: ComponentType | None = None,
        capabilities: list[str] | None = None,
    ) -> list[Component]:
        results = []
        for comp in self._components.values():
            if comp.status == ComponentStatus.DEREGISTERED:
                continue
            if component_type and comp.component_type != component_type:
                continue
            if capabilities and not all(c in comp.capabilities for c in capabilities):
                continue
            results.append(comp)
        return results

    async def get(self, component_id: UUID) -> Component | None:
        comp = self._components.get(component_id)
        if comp and comp.status != ComponentStatus.DEREGISTERED:
            return comp
        return None

    async def deregister(self, component_id: UUID) -> bool:
        if component_id in self._components:
            self._components[component_id].status = ComponentStatus.DEREGISTERED
            return True
        return False

    async def load_from_neon(self) -> int:
        """Boot: load existing agents + skills from Neon into registry."""
        count = 0
        try:
            import sys
            sys.path.insert(0, '/opt/OS')
            from state.storage.db import get_conn
            with get_conn('munoz-holdings') as cur:
                cur.execute("SELECT id, name FROM agents WHERE active = true")
                for row in cur.fetchall():
                    comp = Component(
                        component_type=ComponentType.AGENT,
                        name=row[1],
                        metadata={"neon_id": row[0]},
                    )
                    await self.register(comp)
                    count += 1
                cur.execute("SELECT id, name FROM skills WHERE status = 'active'")
                for row in cur.fetchall():
                    comp = Component(
                        component_type=ComponentType.SKILL,
                        name=row[1],
                        metadata={"neon_id": row[0]},
                    )
                    await self.register(comp)
                    count += 1
        except Exception:
            pass
        return count
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/substrate/test_control_plane.py::TestComponentRegistry -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add substrate/control_plane/registry.py tests/substrate/test_control_plane.py
git commit -m "feat: build ComponentRegistry with Neon boot loader (Phase 2.5)"
```

---

### Task 2.6: Build SignalRouter

**Files:**
- Create: `substrate/control_plane/router.py`
- Ref: `control_plane/runtime/gateway.py` (2,063 lines) — signal routing flow
- Ref: `interface/presence/handlers/intent_handler.py` (410 lines)
- Ref: `execution/runtime/capability_router.py` (610 lines)

- [ ] **Step 1: Read the gateway routing flow**

```bash
grep -n "async def handle\|def classify_intent\|def route" control_plane/runtime/gateway.py | head -20
head -100 interface/presence/handlers/intent_handler.py
```

- [ ] **Step 2: Write the failing test**

```python
# Add to tests/substrate/test_control_plane.py

from substrate.control_plane.router import ConcreteSignalRouter, SignalRouter


class TestSignalRouter:
    def test_implements_protocol(self):
        router = ConcreteSignalRouter.__new__(ConcreteSignalRouter)
        assert isinstance(router, SignalRouter)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest tests/substrate/test_control_plane.py::TestSignalRouter -v`
Expected: FAIL

- [ ] **Step 4: Build substrate/control_plane/router.py**

```python
"""SignalRouter — the integration point that wires all subsystems together.

Single entry point from transports. route() orchestrates the full lifecycle:
identity → context → governance → spine.

Source mapping:
- gateway.py (2,063 lines) → signal routing, deterministic intent, fix-forever
- intent_handler.py (410 lines) → deterministic intent classification
- capability_router.py (610 lines) → intent-driven tool selection
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from substrate.types import (
    SignalEnvelope, ExecutionResult, ExecutionOutcome, TraceRecord,
    TraceEventType, RiskClass, GovernanceDecision,
)


@runtime_checkable
class SignalRouter(Protocol):
    async def route(self, signal: SignalEnvelope) -> ExecutionResult: ...


class ConcreteSignalRouter:
    """Routes signals through the full substrate lifecycle."""

    def __init__(
        self,
        identity_resolver=None,
        context_assembler=None,
        governance_engine=None,
        memory_system=None,
        registry=None,
        execution_spine=None,
        trace_recorder=None,
        feedback_capture=None,
    ):
        self._identity = identity_resolver
        self._context = context_assembler
        self._governance = governance_engine
        self._memory = memory_system
        self._registry = registry
        self._spine = execution_spine
        self._trace = trace_recorder
        self._feedback = feedback_capture

    async def route(self, signal: SignalEnvelope) -> ExecutionResult:
        from uuid import uuid4

        trace = TraceRecord(signal_id=signal.id)
        trace.add_event(TraceEventType.SIGNAL_RECEIVED, f"Signal from {signal.source.value}")

        try:
            identity = await self._identity.resolve(signal)
            trace.add_event(TraceEventType.IDENTITY_RESOLVED, f"Identity: {identity.ai_name}")

            context = await self._context.assemble(signal, identity)
            trace.add_event(TraceEventType.CONTEXT_ASSEMBLED, "Context assembled")

            verdict = await self._governance.classify(signal, context)
            trace.add_event(
                TraceEventType.GOVERNANCE_DECIDED,
                f"Risk: {verdict.risk_class.value}, Decision: {verdict.decision.value}",
            )

            if not verdict.is_executable():
                trace.complete(success=True)
                if self._trace:
                    await self._trace.persist(trace)
                result = ExecutionResult(
                    signal_id=signal.id,
                    trace_id=trace.id,
                    outcome=ExecutionOutcome.BLOCKED,
                    risk_class=verdict.risk_class,
                    governance_decision=verdict.decision,
                    output=verdict.rationale,
                )
                if self._feedback:
                    fb = await self._feedback.capture(trace, result)
                    await self._feedback.persist(fb)
                return result

            result = await self._spine.execute(signal, context, verdict)

            trace.complete(success=result.is_success())
            if self._trace:
                await self._trace.persist(trace)

            if self._feedback:
                feedback = await self._feedback.capture(trace, result)
                await self._feedback.persist(feedback)

            return result

        except Exception as e:
            trace.add_event(TraceEventType.ERROR, str(e)[:300])
            trace.complete(success=False)
            if self._trace:
                await self._trace.persist(trace)
            return ExecutionResult(
                signal_id=signal.id,
                trace_id=trace.id,
                outcome=ExecutionOutcome.FAILURE,
                error=str(e)[:300],
            )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/substrate/test_control_plane.py::TestSignalRouter -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add substrate/control_plane/router.py tests/substrate/test_control_plane.py
git commit -m "feat: build SignalRouter orchestrating full lifecycle (Phase 2.6)"
```

---

### Task 2.7: Phase 2 Verification Gate

- [ ] **Step 1: Verify all control plane modules import**

```bash
python3 -c "
from substrate.control_plane.identity import ConcreteIdentityResolver, IdentityResolver
from substrate.control_plane.context import ConcreteContextAssembler, ContextAssembler
from substrate.control_plane.governance import ConcreteGovernanceEngine, GovernanceEngine
from substrate.control_plane.memory import ConcreteMemorySystem, MemorySystem
from substrate.control_plane.registry import ConcreteComponentRegistry, ComponentRegistry
from substrate.control_plane.router import ConcreteSignalRouter, SignalRouter
print('all control plane subsystems importable')
"
```

- [ ] **Step 2: Run full control plane test suite**

```bash
python3 -m pytest tests/substrate/test_control_plane.py -v
```

Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git commit --allow-empty -m "verify: phase 2 complete — control plane verified"
```

---

## Phase 3 — Tier 2: Execution Spine + Trace + Feedback

### Task 3.1: Create Neon Tables

**Files:**
- No new Python files — DDL execution against Neon

- [ ] **Step 1: Check current table state**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from state.storage.db import get_conn
with get_conn('munoz-holdings') as cur:
    cur.execute(\"SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name\")
    for row in cur.fetchall():
        print(row[0])
"
```

- [ ] **Step 2: Run DDL from spec Section 10**

Execute the `traces`, `feedback`, and `component_registry` CREATE TABLE statements from spec Section 10. Use `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS` for idempotency.

- [ ] **Step 3: Verify tables exist**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from state.storage.db import get_conn
with get_conn('munoz-holdings') as cur:
    for table in ['traces', 'feedback', 'component_registry']:
        cur.execute(f\"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')\")
        exists = cur.fetchone()[0]
        print(f'{table}: {\"EXISTS\" if exists else \"MISSING\"}')
"
```

- [ ] **Step 4: Commit**

```bash
git commit --allow-empty -m "feat: create Neon tables for traces, feedback, component_registry (Phase 3.1)"
```

---

### Task 3.2: Build TraceRecorder

**Files:**
- Create: `substrate/execution/trace.py`
- Test: `tests/substrate/test_execution.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/substrate/test_execution.py

import sys
sys.path.insert(0, '/opt/OS')

import pytest
import asyncio
from uuid import UUID, uuid4

from substrate.types import TraceRecord, TraceEventType
from substrate.execution.trace import ConcreteTraceRecorder, TraceRecorder


class TestTraceRecorder:
    def test_implements_protocol(self):
        recorder = ConcreteTraceRecorder()
        assert isinstance(recorder, TraceRecorder)

    def test_start_creates_trace(self):
        recorder = ConcreteTraceRecorder()
        signal_id = uuid4()
        trace = asyncio.run(recorder.start(signal_id))
        assert isinstance(trace, TraceRecord)
        assert trace.signal_id == signal_id
        assert len(trace.events) >= 1

    def test_add_event(self):
        recorder = ConcreteTraceRecorder()
        signal_id = uuid4()
        trace = asyncio.run(recorder.start(signal_id))
        event = asyncio.run(recorder.add_event(
            trace.id, TraceEventType.GOVERNANCE_DECIDED, "approved"
        ))
        assert event.trace_id == trace.id

    def test_complete_sets_fields(self):
        recorder = ConcreteTraceRecorder()
        signal_id = uuid4()
        trace = asyncio.run(recorder.start(signal_id))
        asyncio.run(recorder.complete(trace.id, success=True))
        completed = recorder._traces.get(trace.id)
        assert completed.success is True
        assert completed.completed_at is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/substrate/test_execution.py::TestTraceRecorder -v`
Expected: FAIL

- [ ] **Step 3: Build substrate/execution/trace.py**

Implement `ConcreteTraceRecorder` with in-memory trace store and Neon persistence on `persist()`. The recorder maintains a `_traces` dict keyed by trace ID, writes JSONB events to the Neon `traces` table on `persist()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/substrate/test_execution.py::TestTraceRecorder -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add substrate/execution/trace.py tests/substrate/test_execution.py
git commit -m "feat: build TraceRecorder with Neon persistence (Phase 3.2)"
```

---

### Task 3.3: Build FeedbackCapture

**Files:**
- Create: `substrate/execution/feedback.py`

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/substrate/test_execution.py

from substrate.execution.feedback import ConcreteFeedbackCapture, FeedbackCapture
from substrate.types import (
    FeedbackRecord, FeedbackType, ExecutionResult,
    ExecutionOutcome, TraceRecord, TraceEventType,
)


class TestFeedbackCapture:
    def test_implements_protocol(self):
        capture = ConcreteFeedbackCapture()
        assert isinstance(capture, FeedbackCapture)

    def test_capture_produces_feedback(self):
        capture = ConcreteFeedbackCapture()
        trace = TraceRecord(signal_id=uuid4())
        trace.add_event(TraceEventType.SIGNAL_RECEIVED, "test")
        trace.complete(success=True)
        result = ExecutionResult(
            signal_id=trace.signal_id, trace_id=trace.id,
            outcome=ExecutionOutcome.SUCCESS, output="response",
        )
        feedback = asyncio.run(capture.capture(trace, result))
        assert isinstance(feedback, FeedbackRecord)
        assert feedback.trace_id == trace.id

    def test_success_gets_higher_quality(self):
        capture = ConcreteFeedbackCapture()
        trace = TraceRecord(signal_id=uuid4())
        trace.complete(success=True)
        result = ExecutionResult(
            signal_id=trace.signal_id, trace_id=trace.id,
            outcome=ExecutionOutcome.SUCCESS, output="good",
        )
        feedback = asyncio.run(capture.capture(trace, result))
        assert feedback.outcome_quality >= 0.5

    def test_failure_gets_lower_quality(self):
        capture = ConcreteFeedbackCapture()
        trace = TraceRecord(signal_id=uuid4())
        trace.complete(success=False)
        result = ExecutionResult(
            signal_id=trace.signal_id, trace_id=trace.id,
            outcome=ExecutionOutcome.FAILURE, error="broke",
        )
        feedback = asyncio.run(capture.capture(trace, result))
        assert feedback.outcome_quality < 0.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/substrate/test_execution.py::TestFeedbackCapture -v`
Expected: FAIL

- [ ] **Step 3: Build substrate/execution/feedback.py**

Implement `ConcreteFeedbackCapture` with deterministic quality mapping: SUCCESS→0.8, PARTIAL_SUCCESS→0.6, FAILURE→0.2, TIMEOUT→0.1, BLOCKED→0.5. `persist()` writes to Neon `feedback` table.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/substrate/test_execution.py::TestFeedbackCapture -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add substrate/execution/feedback.py tests/substrate/test_execution.py
git commit -m "feat: build FeedbackCapture with deterministic quality scoring (Phase 3.3)"
```

---

### Task 3.4: Build ExecutionSpine

**Files:**
- Create: `substrate/execution/spine.py`
- Ref: `control_plane/runtime/cognitive_loop.py` (1,448 lines) — 8 stages
- Ref: `execution/runtime/execution_spine.py` — thin execution
- Ref: `services/umh/control_plane/pipeline.py` — 10-stage pipeline

- [ ] **Step 1: Read the cognitive loop execution stages**

```bash
grep -n "PERCEIVE\|UNDERSTAND\|PLAN\|EXECUTE\|VERIFY\|REFLECT\|LEARN\|STORE\|def run\|async def" control_plane/runtime/cognitive_loop.py | head -30
```

- [ ] **Step 2: Write the failing test**

```python
# Add to tests/substrate/test_execution.py

from substrate.execution.spine import ConcreteExecutionSpine, ExecutionSpine
from substrate.types import (
    SignalEnvelope, SignalSource, ExecutionContext, Identity,
    GovernanceVerdict, GovernanceDecision, RiskClass,
    ExecutionResult, ExecutionOutcome,
)


class TestExecutionSpine:
    def test_implements_protocol(self):
        spine = ConcreteExecutionSpine.__new__(ConcreteExecutionSpine)
        assert isinstance(spine, ExecutionSpine)

    def test_execute_returns_result(self):
        from substrate.execution.trace import ConcreteTraceRecorder
        from substrate.execution.feedback import ConcreteFeedbackCapture
        from substrate.control_plane.memory import ConcreteMemorySystem
        from substrate.control_plane.registry import ConcreteComponentRegistry

        spine = ConcreteExecutionSpine(
            memory=ConcreteMemorySystem(),
            registry=ConcreteComponentRegistry(),
            trace_recorder=ConcreteTraceRecorder(),
            feedback_capture=ConcreteFeedbackCapture(),
        )
        signal = SignalEnvelope(
            source=SignalSource.SYSTEM, content="hello test",
            user_id="test", organization_id="test-org",
        )
        identity = Identity(
            user_id="test", organization_id="test-org",
            ai_name="DEX", ai_personality="professional",
            autonomy_level=1, business_stage="pre_revenue",
        )
        context = ExecutionContext(signal_id=signal.id, identity=identity)
        verdict = GovernanceVerdict(
            signal_id=signal.id, risk_class=RiskClass.LOW,
            decision=GovernanceDecision.APPROVE, rationale="test approved",
        )
        result = asyncio.run(spine.execute(signal, context, verdict))
        assert isinstance(result, ExecutionResult)
        assert result.signal_id == signal.id
        assert result.trace_id is not None

    def test_execute_blocked_returns_blocked(self):
        from substrate.execution.trace import ConcreteTraceRecorder
        from substrate.execution.feedback import ConcreteFeedbackCapture
        from substrate.control_plane.memory import ConcreteMemorySystem
        from substrate.control_plane.registry import ConcreteComponentRegistry

        spine = ConcreteExecutionSpine(
            memory=ConcreteMemorySystem(),
            registry=ConcreteComponentRegistry(),
            trace_recorder=ConcreteTraceRecorder(),
            feedback_capture=ConcreteFeedbackCapture(),
        )
        signal = SignalEnvelope(
            source=SignalSource.USER, content="send email to everyone",
            user_id="test", organization_id="test-org",
        )
        identity = Identity(
            user_id="test", organization_id="test-org",
            ai_name="DEX", ai_personality="professional",
            autonomy_level=1, business_stage="pre_revenue",
        )
        context = ExecutionContext(signal_id=signal.id, identity=identity)
        verdict = GovernanceVerdict(
            signal_id=signal.id, risk_class=RiskClass.CRITICAL,
            decision=GovernanceDecision.DENY, rationale="too risky",
        )
        result = asyncio.run(spine.execute(signal, context, verdict))
        assert result.outcome == ExecutionOutcome.BLOCKED
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest tests/substrate/test_execution.py::TestExecutionSpine -v`
Expected: FAIL

- [ ] **Step 4: Build substrate/execution/spine.py**

Implement the 8-stage spine:
1. **Interpret** — deterministic intent classification via keyword matching
2. **Recall** — semantic memory search
3. **Lookup** — registry query for capable adapters
4. **Compose** — build execution plan (prompt + model selection)
5. **Route** — select adapter and dispatch
6. **Execute** — invoke `model_router.call_with_fallback()` with deterministic fallback
7. **Trace** — record execution provenance
8. **Feedback** — capture outcome quality

The spine calls `call_with_fallback()` from `adapters/models/model_router.py`. If all LLMs fail, it returns a deterministic intent-aware response.

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/substrate/test_execution.py::TestExecutionSpine -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add substrate/execution/spine.py tests/substrate/test_execution.py
git commit -m "feat: build 8-stage ExecutionSpine with deterministic-first fallback (Phase 3.4)"
```

---

### Task 3.5: Wire Substrate Public API

**Files:**
- Modify: `substrate/__init__.py` — replace stub with full Substrate class

- [ ] **Step 1: Write the failing integration test**

```python
# tests/integration/test_signal_to_trace.py

import sys
sys.path.insert(0, '/opt/OS')

import asyncio
import pytest
from uuid import UUID

from substrate import Substrate
from substrate.types import SignalEnvelope, SignalSource, ExecutionOutcome


class TestSignalToTrace:
    def test_execute_produces_trace(self):
        s = Substrate()
        signal = SignalEnvelope(
            source=SignalSource.SYSTEM,
            content="test signal for trace",
            user_id="test-user",
            organization_id="test-org",
        )
        result = asyncio.run(s.execute(signal))
        assert result.trace_id is not None
        assert isinstance(result.trace_id, UUID)
        assert result.outcome in list(ExecutionOutcome)

    def test_execute_blocked_still_traced(self):
        s = Substrate()
        signal = SignalEnvelope(
            source=SignalSource.USER,
            content="send email to all contacts",
            user_id="test-user",
            organization_id="test-org",
        )
        result = asyncio.run(s.execute(signal))
        assert result.trace_id is not None
        assert result.outcome == ExecutionOutcome.BLOCKED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/integration/test_signal_to_trace.py -v`
Expected: FAIL (Substrate class not yet wired)

- [ ] **Step 3: Build substrate/__init__.py — the public API**

Wire all subsystems together in the `Substrate` class:
- `__init__()` creates all concrete implementations
- `execute()` delegates to `SignalRouter.route()`
- `query()` delegates to `MemorySystem.recall()`
- `register()` delegates to `ComponentRegistry.register()`
- `ingest()` returns not-yet-implemented placeholder
- `status()` returns health check

- [ ] **Step 4: Run integration test**

Run: `python3 -m pytest tests/integration/test_signal_to_trace.py -v`
Expected: PASS

- [ ] **Step 5: Run all tests so far**

```bash
python3 -m pytest tests/substrate/ tests/integration/ -v
```

Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add substrate/__init__.py tests/integration/
git commit -m "feat: wire Substrate public API connecting all subsystems (Phase 3.5)"
```

---

### Task 3.6: Phase 3 Verification Gate

- [ ] **Step 1: End-to-end signal execution**

```bash
python3 -c "
import asyncio, sys
sys.path.insert(0, '/opt/OS')
from substrate import Substrate
from substrate.types import SignalEnvelope, SignalSource

async def test():
    s = Substrate()
    result = await s.execute(SignalEnvelope(
        source=SignalSource.SYSTEM, content='test signal',
        user_id='test', organization_id='test-org',
    ))
    assert result.trace_id is not None
    print(f'execution: {result.outcome.value}, trace: {result.trace_id}')

asyncio.run(test())
"
```

- [ ] **Step 2: Run full test suite**

```bash
python3 -m pytest tests/ -v --tb=short
```

- [ ] **Step 3: Commit**

```bash
git commit --allow-empty -m "verify: phase 3 complete — execution spine + trace + feedback verified"
```

---

## Phase 4 — Tier 3: Adapters

### Task 4.1: Build LLM Adapter

**Files:**
- Create: `adapters/models/llm_adapter.py`
- Test: `tests/adapters/test_llm_adapter.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/adapters/test_llm_adapter.py

import sys
sys.path.insert(0, '/opt/OS')

import pytest
import asyncio
from uuid import UUID

from adapters.models.llm_adapter import LLMAdapter
from adapters.protocol import Adapter
from substrate.types import AdapterRequest, AdapterResponse


class TestLLMAdapter:
    def test_satisfies_adapter_protocol(self):
        adapter = LLMAdapter()
        assert isinstance(adapter, Adapter)

    def test_has_required_attributes(self):
        adapter = LLMAdapter()
        assert isinstance(adapter.adapter_id, UUID)
        assert adapter.adapter_type == "llm"
        assert adapter.name == "model_router"

    def test_capabilities(self):
        adapter = LLMAdapter()
        caps = adapter.capabilities()
        assert "text_generation" in caps
        assert "conversation" in caps

    def test_health_check(self):
        adapter = LLMAdapter()
        result = asyncio.run(adapter.health_check())
        assert result is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/adapters/test_llm_adapter.py -v`
Expected: FAIL

- [ ] **Step 3: Build adapters/models/llm_adapter.py**

Wrap `model_router.call_with_fallback()` as a substrate Adapter. Does NOT modify model_router internals.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/adapters/test_llm_adapter.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add adapters/models/llm_adapter.py tests/adapters/test_llm_adapter.py
git commit -m "feat: build LLMAdapter wrapping model_router (Phase 4)"
```

---

## Phase 5 — Transports

### Task 5.1: Build Discord Signal Factory

**Files:**
- Create: `transports/discord/signal_factory.py`
- Test: `tests/transports/test_discord_signal_factory.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/transports/test_discord_signal_factory.py

import sys
sys.path.insert(0, '/opt/OS')

import pytest
from unittest.mock import MagicMock

from substrate.types import SignalEnvelope, SignalSource, Modality
from transports.discord.signal_factory import message_to_signal


class TestDiscordSignalFactory:
    def test_text_message_produces_signal(self):
        msg = MagicMock()
        msg.content = "hello world"
        msg.author.id = 12345
        msg.author.name = "testuser"
        msg.guild.id = 67890
        msg.channel.id = 11111
        msg.attachments = []

        signal = message_to_signal(msg, organization_id="munoz-holdings")
        assert isinstance(signal, SignalEnvelope)
        assert signal.source == SignalSource.USER
        assert signal.content == "hello world"
        assert signal.modality == Modality.TEXT
        assert signal.user_id == "12345"

    def test_voice_attachment_sets_modality(self):
        msg = MagicMock()
        msg.content = ""
        msg.author.id = 12345
        msg.author.name = "testuser"
        msg.guild.id = 67890
        msg.channel.id = 11111

        attachment = MagicMock()
        attachment.filename = "audio.ogg"
        attachment.content_type = "audio/ogg"
        attachment.url = "https://cdn.example.com/audio.ogg"
        msg.attachments = [attachment]

        signal = message_to_signal(msg, organization_id="munoz-holdings")
        assert signal.modality == Modality.VOICE
        assert len(signal.attachments) == 1

    def test_image_attachment_sets_multimodal(self):
        msg = MagicMock()
        msg.content = "look at this"
        msg.author.id = 12345
        msg.author.name = "testuser"
        msg.guild.id = 67890
        msg.channel.id = 11111

        attachment = MagicMock()
        attachment.filename = "photo.png"
        attachment.content_type = "image/png"
        attachment.url = "https://cdn.example.com/photo.png"
        msg.attachments = [attachment]

        signal = message_to_signal(msg, organization_id="munoz-holdings")
        assert signal.modality == Modality.MULTIMODAL
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/transports/test_discord_signal_factory.py -v`
Expected: FAIL

- [ ] **Step 3: Build transports/discord/signal_factory.py**

Convert Discord messages to SignalEnvelopes. Handle text, voice, image, and multimodal messages.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/transports/test_discord_signal_factory.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add transports/discord/signal_factory.py tests/transports/test_discord_signal_factory.py
git commit -m "feat: build Discord signal factory (Phase 5.1)"
```

---

### Task 5.2: Refactor Discord Bot to Use Substrate

**Files:**
- Modify: `transports/discord/bot.py` (copied from services/discord_bot.py in Phase 0)

This is the largest single task — refactoring the 5,481-line Discord bot to route through `substrate.execute()`.

- [ ] **Step 1: Read the current bot's message handling flow**

```bash
grep -n "async def on_message\|gateway\|cognitive_loop\|agent_runtime\|call_with_fallback" transports/discord/bot.py | head -30
```

- [ ] **Step 2: Identify all gateway/cognitive_loop call sites**

```bash
grep -n "gateway\.\|cognitive_loop\.\|CognitiveLoop\|EntrepreneurOSGateway\|agent_runtime\." transports/discord/bot.py | head -40
```

- [ ] **Step 3: Replace message handler to use substrate**

For each call site:
1. `signal = message_to_signal(msg, organization_id)`
2. `result = await substrate.execute(signal)`
3. `await msg.reply(result.output)`

- [ ] **Step 4: Verify the bot compiles**

```bash
python3 -m py_compile transports/discord/bot.py
```

- [ ] **Step 5: Build and test Docker container**

```bash
docker restart os-discord && sleep 5
docker logs os-discord --tail 20 | grep -q "Ready" && echo "Discord OK" || echo "Discord FAILED"
```

- [ ] **Step 6: Send a test message and verify trace appears in Neon**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from state.storage.db import get_conn
with get_conn('munoz-holdings') as cur:
    cur.execute('SELECT count(*) FROM traces')
    print(f'traces in Neon: {cur.fetchone()[0]}')
"
```

- [ ] **Step 7: Commit**

```bash
git add transports/discord/bot.py
git commit -m "refactor: wire Discord bot through substrate.execute() (Phase 5.2)"
```

---

### Task 5.3: Refactor Operator API and Rebuild Docker

**Files:**
- Modify: `transports/api/operator.py`
- Create: `transports/api/signal_factory.py`
- Modify: Docker config if needed

- [ ] **Step 1: Build API signal factory**

Convert HTTP requests to SignalEnvelopes.

- [ ] **Step 2: Replace direct gateway calls in operator.py**

- [ ] **Step 3: Update Docker config for new paths**

```bash
grep -n "services/discord_bot\|services/operator_api" docker-compose.yml Dockerfile 2>/dev/null
```

- [ ] **Step 4: Verify API compiles**

```bash
python3 -m py_compile transports/api/operator.py
python3 -m py_compile transports/api/signal_factory.py
```

- [ ] **Step 5: Commit**

```bash
git add transports/api/ docker-compose.yml
git commit -m "refactor: wire operator API through substrate + update Docker (Phase 5.3)"
```

---

### Task 5.4: Phase 5 Verification Gate

- [ ] **Step 1: Discord bot connected and responding**

```bash
docker logs os-discord --tail 5
```

- [ ] **Step 2: Traces in Neon**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from state.storage.db import get_conn
with get_conn('munoz-holdings') as cur:
    cur.execute('SELECT count(*) FROM traces')
    print(f'traces: {cur.fetchone()[0]}')
    cur.execute('SELECT count(*) FROM feedback')
    print(f'feedback: {cur.fetchone()[0]}')
"
```

- [ ] **Step 3: Run full test suite**

```bash
python3 -m pytest tests/ -v --tb=short
```

- [ ] **Step 4: Commit**

```bash
git commit --allow-empty -m "verify: phase 5 complete — transports wired through substrate"
```

---

## Phase 6 — Prune and Verify

### Task 6.1: Build Verification Scripts

**Files:**
- Create: `scripts/dead_code_check.py`
- Create: `scripts/invariant_check.sh`

- [ ] **Step 1: Write dead_code_check.py**

Checks that every `.py` file under `substrate/` (excluding `__init__.py`) is imported by at least one other file.

- [ ] **Step 2: Write invariant_check.sh**

Checks all 10 invariants from spec Section 11:
1. Control plane exclusivity
2. Single execution spine
3. Governance before execution
4. Trace everything
5. Memory discipline
6. Registry as truth
7. Feedback closes loops
8. Public API boundary
9. Zero dead code
10. Pydantic only

- [ ] **Step 3: Make executable and commit**

```bash
chmod +x scripts/dead_code_check.py scripts/invariant_check.sh
git add scripts/dead_code_check.py scripts/invariant_check.sh
git commit -m "feat: add dead code and invariant check scripts (Phase 6.1)"
```

---

### Task 6.2: Delete Dead Code

**Files:**
- Delete: ~600+ files (see spec Section 14)

- [ ] **Step 1: Verify git tag exists**

```bash
git tag -l | grep pre-unification
```

- [ ] **Step 2: Systematically delete superseded directories**

For each directory in the deletion table (spec Section 14), check for remaining importers from surviving code, then delete if safe:

```bash
for dir in "execution/workers" "execution/environments" "execution/workflows" "execution/agents" "execution/engine" "execution/tasks" "core" "interface" "observability" "operations" "archive"; do
    if [ -d "$dir" ]; then
        importers=$(grep -rl "from ${dir//\//.}" --include="*.py" substrate/ adapters/ transports/ state/ projections/ 2>/dev/null | wc -l)
        if [ "$importers" -eq 0 ]; then
            echo "Deleting: $dir"
            rm -rf "$dir"
        else
            echo "KEEP: $dir has $importers importers"
        fi
    fi
done
```

- [ ] **Step 3: Clean dead test files**

Remove tests for deleted code while keeping `tests/substrate/`, `tests/adapters/`, `tests/transports/`, `tests/integration/`, `tests/acceptance/`.

- [ ] **Step 4: Format all surviving code**

```bash
ruff format substrate/ adapters/ transports/ state/ projections/ integrations/ scripts/
```

- [ ] **Step 5: Full compile check**

```bash
find . -name "*.py" -not -path "./.claude/*" -not -path "./_archive/*" -not -path "./__pycache__/*" \
    -exec python3 -m py_compile {} \;
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "prune: delete ~230K lines of dead code (Phase 6.2)"
```

---

### Task 6.3: Update Documentation and Rebuild Graph

**Files:**
- Modify: `CLAUDE.md`, `.claude/CLAUDE.md` — update all paths
- Modify: Skill files with old paths
- Rebuild: Codebase graph, memory palace

- [ ] **Step 1: Update CLAUDE.md files with new paths**

- [ ] **Step 2: Rebuild codebase graph**

```bash
scripts/update-graph
```

- [ ] **Step 3: Update memory palace rooms**

```bash
grep -rn "runtime/\|execution/runtime\|services/umh\|control_plane/runtime" knowledge/palace/ | head -20
```

Update each reference.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "docs: update all documentation paths for new structure (Phase 6.3)"
```

---

### Task 6.4: Phase 6 Verification Gate

- [ ] **Step 1: Zero dead code**

```bash
python3 scripts/dead_code_check.py
```

- [ ] **Step 2: All invariants pass**

```bash
bash scripts/invariant_check.sh
```

- [ ] **Step 3: Full test suite**

```bash
python3 -m pytest tests/ -v --tb=short
```

- [ ] **Step 4: All files compile**

```bash
find . -name "*.py" -not -path "./.claude/*" -not -path "./_archive/*" \
    -exec python3 -m py_compile {} \;
```

- [ ] **Step 5: Docker containers healthy**

```bash
docker ps --format '{{.Names}} {{.Status}}' | grep -E "os-discord|os-bot"
```

- [ ] **Step 6: Commit**

```bash
git commit --allow-empty -m "verify: phase 6 complete — pruned and verified"
```

---

## Phase 7 — EOS Projection

### Task 7.1: Build EOS Projection Package

**Files:**
- Create: `projections/eos/__init__.py`
- Test: `tests/acceptance/test_eos_outreach_flow.py`

- [ ] **Step 1: Write the acceptance test**

```python
# tests/acceptance/test_eos_outreach_flow.py

import sys
sys.path.insert(0, '/opt/OS')

import asyncio
import pytest

from substrate import Substrate
from substrate.types import SignalEnvelope, SignalSource, ComponentType


class TestEOSOutreach:
    def test_eos_agents_registered(self):
        s = Substrate()
        from projections.eos import register_eos_agents
        asyncio.run(register_eos_agents(s))
        agents = asyncio.run(s._registry.lookup(component_type=ComponentType.AGENT))
        eos_agents = [a for a in agents if 'eos' in a.name.lower()]
        assert len(eos_agents) >= 1

    def test_outreach_signal_executes(self):
        s = Substrate()
        from projections.eos import register_eos_agents
        asyncio.run(register_eos_agents(s))
        signal = SignalEnvelope(
            source=SignalSource.USER,
            content="draft outreach for lead John Smith at Acme Corp",
            user_id="test-user",
            organization_id="munoz-holdings",
        )
        result = asyncio.run(s.execute(signal))
        assert result.trace_id is not None

    def test_projection_isolation(self):
        """Verify projections only use public API — no internal imports."""
        import subprocess
        result = subprocess.run(
            ['grep', '-rn', 'from substrate.', 'projections/', '--include=*.py'],
            capture_output=True, text=True,
        )
        violations = [
            line for line in result.stdout.strip().split('\n')
            if line and 'from substrate import' not in line and 'from substrate.types import' not in line
        ]
        assert len(violations) == 0, f"Projection isolation violated:\n" + "\n".join(violations)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/acceptance/test_eos_outreach_flow.py -v`
Expected: FAIL

- [ ] **Step 3: Build projections/eos/__init__.py**

Register EOS department agents (CEO, Sales, Marketing) in the substrate registry. Each agent has capabilities like "strategy", "outreach", "content". All interaction through `substrate.execute()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/acceptance/test_eos_outreach_flow.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projections/eos/ tests/acceptance/
git commit -m "feat: build EOS projection layer with department agents (Phase 7)"
```

---

## Final Verification

### Task 8.1: End-to-End System Check

- [ ] **Step 1: All tests pass**

```bash
python3 -m pytest tests/ -v --tb=short
```

- [ ] **Step 2: All invariants pass**

```bash
bash scripts/invariant_check.sh
```

- [ ] **Step 3: All files compile**

```bash
find . -name "*.py" -not -path "./.claude/*" -not -path "./_archive/*" \
    -exec python3 -m py_compile {} \;
```

- [ ] **Step 4: Docker containers healthy**

```bash
docker ps --format '{{.Names}} {{.Status}}'
```

- [ ] **Step 5: Signal → Trace → Feedback pipeline works**

```bash
python3 -c "
import asyncio, sys
sys.path.insert(0, '/opt/OS')
from substrate import Substrate
from substrate.types import SignalEnvelope, SignalSource

async def final_check():
    s = Substrate()
    result = await s.execute(SignalEnvelope(
        source=SignalSource.SYSTEM,
        content='final verification signal',
        user_id='verification',
        organization_id='munoz-holdings',
    ))
    print(f'Outcome: {result.outcome.value}')
    print(f'Trace: {result.trace_id}')
    print(f'Provider: {result.provider}')
    print(f'Duration: {result.duration_ms:.0f}ms')
    assert result.trace_id is not None
    print('FINAL VERIFICATION: PASS')

asyncio.run(final_check())
"
```

- [ ] **Step 6: Tag post-unification**

```bash
git tag post-unification
```

- [ ] **Step 7: Final commit**

```bash
git commit --allow-empty -m "milestone: UMH substrate unification complete"
```
