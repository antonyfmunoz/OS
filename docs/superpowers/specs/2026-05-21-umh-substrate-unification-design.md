# UMH Substrate Unification — Architecture Contract

**Date:** 2026-05-21 (updated 2026-05-22)
**Status:** Draft v2.1 — re-audited against codebase as of 2026-05-22
**Approach:** Bottom-up substrate migration with aggressive pruning
**Timeline:** 4–6 weeks, 7 phases
**North Star:** Canonical UMH end-state spec (Google Drive doc, 8 tabs, 13,949 words)

---

## 1. Problem

The `/opt/OS` repository contains ~333,000 lines of Python across 1,194 files.
Only ~15,000 lines (~25 files) carry production traffic. The rest breaks down as:

| Category | Lines | Files | Production callers |
|----------|------:|------:|:------------------:|
| UMH substrate (`services/umh/`) | ~32,800 | 192 | **partial** (organism daemon, cockpit API, node mesh have callers) |
| Constitutional engines / workstation workers | ~20,000 | 45 | test-only |
| v1 contracts (superseded) | ~15,000 | 40+ | **0** |
| Duplicate implementations (2–4× for every core concept) | ~30,000 | 80+ | partial |
| Transport infrastructure (not wired to substrate) | ~25,000 | 60+ | partial |
| Production code (model routing, memory, governance, Discord) | ~15,000 | 25 | **all** |
| Organism runtime + node mesh + integrations | ~7,500 | 46 | test-only (built but not wired to production) |
| Windows daemon + desktop adapters | ~1,278 | 14 | VPS: no; Windows node: yes |
| Capability router + intent handler | ~1,020 | 2 | partial (intent_handler called by gateway) |

Two complete, incompatible type systems coexist:

- **Runtime dataclasses** — `str` IDs, no validation, no relationships. Used by everything running.
- **UMH Pydantic protocols** — `UUID` IDs, validated fields, typed enums. Used by organism runtime only (not production path).

Three parallel execution paths exist: `CognitiveLoop`, `ExecutionSpine`, and direct `AgentRuntime` calls. A fourth path — `ExecutionPipeline` in `services/umh/` — is wired to the organism daemon but has no production callers. The canonical spec requires exactly **one**.

Since v2 of this spec (2026-05-21), 67 commits have added:
- **Deterministic-first fallbacks** across model_router, cognitive_loop, gateway, agent_runtime, discord_bot, execution_spine, orchestrator
- **Fix-forever error recording** at every LLM call site
- **Organism runtime** — multi-agent society with advisor, worker cells, approval store (1,554 lines)
- **Node mesh** — WebSocket-based multi-device coordination (850 lines)
- **Integration framework** — CreatorOS + LyfeOS adapters with signal/handler/outcome pattern (5,148 lines)
- **Windows daemon** — desktop adapters for clipboard, shell, filesystem, tray UI (1,278 lines)
- **Capability router** — intent-driven tool selection (610 lines)
- **Intent handler** — centralized deterministic intent classification (410 lines)
- **Voice-first transport** — speak before text, acknowledge during generation (370 lines)
- **Cockpit API** — 40 live backend endpoints for governance UI (1,034 lines)
- **CLI agent adapters** — Codex, Hermes, OpenCode (616 lines total)
- **Domain bridges** — creator.py (515 lines) and life.py (568 lines)

---

## 2. Goal

Unify the codebase into a single coherent system aligned with the canonical end-state:

1. **One type system** — Pydantic BaseModel with UUID identifiers.
2. **One execution spine** — every signal, regardless of transport, follows one governed path.
3. **One public API** — projections (EOS) call `substrate.execute()`, never import internals.
4. **Zero dead code** — every surviving file is imported by at least one other surviving file.
5. **Full trace and feedback** — every execution produces a Neon-persisted trace and captures feedback.
6. **Substrate MVP hosts EOS** — the substrate is capable enough to run Initiate Arena outreach through it.

---

## 3. Binding Decisions

These are **locked**. They do not require further discussion.

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Pydantic `BaseModel` with `UUID` IDs is the sole type system | UMH protocols already define it; runtime dataclasses are weaker |
| 2 | `SignalEnvelope` is the universal input type for all transports | Every transport (Discord, API, WebSocket, cron) produces one shape |
| 3 | `PrimitiveType` (10 values) and `OntologicalCategory` (8 values) are orthogonal dimensions — both survive | PrimitiveType = what it is; OntologicalCategory = what kind of being it is |
| 4 | `model_router.call_with_fallback()` is the sole LLM adapter — wrapped, not replaced | 1,516 lines, circuit breaker, multi-provider, deterministic fallbacks, production-proven |
| 5 | No Neon schema destruction — new tables added alongside existing | 35,485 interactions, 35,277 embeddings, 27,851 events |
| 6 | `substrate/__init__.py` is the only public API for projections | Hard boundary: projections never import `substrate.control_plane.*` |
| 7 | Full rebuild window — Discord bot offline during migration | Founder-approved; no users to serve yet |
| 8 | Directory names are production-grade — no numbered folders, no internal jargon | `knowledge/` not `10_Wiki/`, `substrate/` not `services/umh/` |

---

## 4. Directory Structure

```
/opt/OS/
├── substrate/                     # Tier 0–2: The UMH kernel
│   ├── __init__.py                # Public API (Section 5)
│   ├── types.py                   # Shared type definitions (Section 6)
│   ├── ontology/                  # Tier 0: Primitives, laws, relationships
│   │   ├── __init__.py
│   │   ├── primitives.py          # PrimitiveType, OntologicalCategory, PrimitiveObservation
│   │   ├── laws.py                # Governing laws registry
│   │   └── relationships.py       # RelationshipType, typed edges
│   ├── control_plane/             # Tier 1: Identity, context, governance, memory, registry
│   │   ├── __init__.py
│   │   ├── identity.py            # IdentityResolver (Section 7.1)
│   │   ├── context.py             # ContextAssembler (Section 7.2)
│   │   ├── governance.py          # GovernanceEngine (Section 7.3)
│   │   ├── memory.py              # MemorySystem (Section 7.4)
│   │   ├── registry.py            # ComponentRegistry (Section 7.5)
│   │   └── router.py              # SignalRouter (Section 7.6)
│   ├── execution/                 # Tier 2: Spine, trace, feedback
│   │   ├── __init__.py
│   │   ├── spine.py               # ExecutionSpine (Section 7.7)
│   │   ├── trace.py               # TraceRecorder (Section 7.8)
│   │   ├── feedback.py            # FeedbackCapture (Section 7.9)
│   │   └── ingestion/             # Canonical ingestion pipeline
│   │       ├── __init__.py
│   │       ├── orchestrator.py    # GenericIngestionOrchestrator
│   │       ├── decomposer.py      # PrimitiveDecomposer
│   │       ├── sources.py         # LocalFileSource, GWSSource
│   │       └── domain_bridge.py   # Domain projection layer
│   ├── organism/                  # Organism runtime (from services/umh/organism/)
│   │   ├── daemon.py              # OrganismDaemon — agent lifecycle management
│   │   ├── advisor.py             # Advisor — multi-agent orchestration
│   │   ├── worker_cell.py         # WorkerCell — distributed execution units
│   │   ├── approval_store.py      # ApprovalStore — governance layer
│   │   ├── agents.py              # Agent definitions
│   │   ├── agent_runtime.py       # Organism-specific agent runtime (192 lines)
│   │   ├── store.py               # OrganismStore — state persistence
│   │   └── protocols.py           # Pydantic models: Deliverable, AgentMessage, WorkerSpec, CritiqueResult, LearningSignal
│   └── learning/                  # Cross-tier: Evolution (post-MVP)
│
├── adapters/                      # Tier 3: External system interfaces
│   ├── __init__.py
│   ├── protocol.py                # Adapter Protocol (Section 8)
│   ├── models/                    # LLM routing
│   │   ├── model_router.py        # Surviving 1,516-line router (deterministic-first)
│   │   ├── cc_sdk.py              # Claude Code CLI adapter (464 lines)
│   │   ├── codex_cli.py           # Codex CLI agent adapter (258 lines)
│   │   ├── hermes_cli.py          # Hermes CLI agent adapter (178 lines)
│   │   ├── opencode_cli.py        # OpenCode CLI agent adapter (180 lines)
│   │   └── llm_adapter.py         # Protocol wrapper around model_router
│   ├── google_workspace/          # GWS connector + scanner (3,531 lines)
│   ├── browser/                   # Browser automation adapter
│   ├── calendar/                  # Calendar adapter
│   ├── notion/                    # Notion sync adapter
│   └── capabilities/              # Voice, vision, media processing
│
├── world_model/                   # Tier 4 (post-MVP)
├── intelligence/                  # Tier 5 (post-MVP)
│
├── projections/                   # Application layers on substrate
│   └── eos/                       # EntrepreneurOS (Phase 7)
│       ├── __init__.py
│       ├── agents/                # Department agents (CEO, Sales, Marketing)
│       ├── workflows/             # Outreach, follow-up, content calendar
│       └── views/                 # CRM, pipeline, KPIs as memory queries
│
├── transports/                    # User-facing interfaces
│   ├── discord/                   # Discord bot
│   │   ├── bot.py                 # Refactored from services/discord_bot.py (5,481 lines)
│   │   ├── signal_factory.py      # Message → SignalEnvelope
│   │   └── voice_first.py         # Voice-first response path (370 lines)
│   ├── api/                       # REST + WebSocket operator API
│   │   ├── operator.py            # Refactored from services/operator_api.py
│   │   ├── cockpit.py             # Cockpit governance API (1,034 lines, 40 endpoints)
│   │   └── signal_factory.py
│   ├── cockpit/                   # React dashboard
│   └── node_mesh/                 # Multi-device WebSocket mesh (850 lines)
│       ├── server.py              # NodeMeshServer — device coordination
│       ├── registry.py            # ConnectedNode registry
│       ├── config.py              # MeshConfig
│       └── metrics_buffer.py      # MetricsBuffer
│
├── knowledge/                     # Curated knowledge (replaces 10_Wiki/)
│   ├── index.md
│   ├── concepts/
│   ├── entities/
│   ├── decisions/
│   ├── synthesis/
│   ├── sources/
│   └── palace/                    # Memory palace
│
├── state/                         # Persistence layer
│   ├── storage/                   # db.py (Neon connection pool)
│   │   └── db.py
│   ├── memory/                    # AgentMemory + ConversationMemory
│   │   └── memory.py
│   ├── context/                   # System context loader
│   │   └── context.py
│   ├── business/                  # BIS, venture config
│   │   └── business_instance.py
│   ├── registries/                # Backing stores for unified registry
│   │   └── skill_registry.py
│   ├── profiles/                  # User/human model data
│   └── preferences/               # Model preferences
│
├── integrations/                  # Platform integration adapters
│   ├── creatoros/                 # CreatorOS signal/handler/outcome pattern (7 files)
│   ├── lyfeos/                    # LyfeOS signal/handler/outcome pattern (7 files)
│   └── node_mesh/                 # Node mesh integration handlers
│
├── daemon/                        # Windows node daemon (1,278 lines)
│   ├── umh_node/                  # Node client, governance, metrics, workspace
│   │   └── adapters/              # Clipboard, desktop, filesystem, shell
│   └── umh_desktop/               # System tray UI
│
├── composition/                   # Tool Mastery Engine (operator tooling)
├── scripts/                       # Operator scripts, cron jobs
├── data/                          # Generated data, proofs, audits
├── docs/                          # Architecture specs, contracts
├── skills/                        # Claude Code tool skills
└── tests/                         # Unified test suite (mirrors source tree)
    ├── substrate/
    │   ├── test_ontology.py
    │   ├── test_control_plane.py
    │   ├── test_execution.py
    │   └── test_ingestion.py
    ├── adapters/
    │   └── test_llm_adapter.py
    ├── transports/
    │   └── test_discord_signal_factory.py
    ├── integration/
    │   ├── test_signal_to_trace.py
    │   ├── test_governance_blocks_critical.py
    │   └── test_memory_round_trip.py
    └── acceptance/
        ├── test_discord_message_flow.py
        └── test_eos_outreach_flow.py
```

---

## 5. Substrate Public API

`substrate/__init__.py` — the **only** import path projections may use.

```python
from __future__ import annotations

from typing import runtime_checkable, Protocol
from uuid import UUID

from substrate.types import (
    SignalEnvelope,
    ExecutionResult,
    MemoryQuery,
    MemoryEntry,
    Component,
    RegistrationResult,
    IngestionResult,
    SubstrateStatus,
)


class Substrate:
    """Public API for the UMH substrate.

    All projections (EOS, CreatorOS, LyfeOS) interact with UMH
    exclusively through this interface. No internal imports.
    """

    def __init__(self) -> None:
        # Wires internal subsystems. Details are private.
        ...

    async def execute(self, signal: SignalEnvelope) -> ExecutionResult:
        """Submit a signal for governed execution through the spine.

        Lifecycle: route → identify → contextualize → govern →
        interpret → recall → compose → execute → trace → feedback.

        Returns ExecutionResult regardless of outcome (success, failure,
        blocked by governance). Caller inspects result.outcome.
        """
        ...

    async def query(self, query: MemoryQuery) -> list[MemoryEntry]:
        """Search the substrate's memory system.

        Supports semantic search, tag filtering, authority tier
        filtering, and time-range queries.
        """
        ...

    async def register(self, component: Component) -> RegistrationResult:
        """Register a component (adapter, agent, skill, workflow).

        Registered components are discoverable by the spine during
        capability lookup. Unregistered components do not exist
        to the substrate.
        """
        ...

    async def ingest(self, source_uri: str, authority_tier: int = 5) -> IngestionResult:
        """Ingest a document or data source into the ontology layer.

        Pipeline: perceive → interpret → decompose → bridge → map →
        persist → query_back. Each stage produces trace events.
        """
        ...

    def status(self) -> SubstrateStatus:
        """Synchronous health check. Returns component status,
        adapter health, memory stats, and active signal count.
        """
        ...
```

**Hard invariant:** If `grep -rn "from substrate\." projections/ | grep -v "from substrate import\|from substrate.types"` produces any output, the build is broken.

---

## 6. Type System

All types are Pydantic `BaseModel` with `UUID` identifiers. All enums are `str, Enum` for JSON serialization. All timestamps are UTC `datetime`. Field validation uses Pydantic `Field()` constraints.

The authoritative definitions live in `substrate/types.py`. Protocols from `services/umh/protocols/` are migrated here.

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

class Attachment(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    filename: str = Field(max_length=255)
    mime_type: str = Field(max_length=120)
    data: bytes | None = None
    url: str | None = None


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

class MemoryQuery(BaseModel):
    query_text: str
    memory_types: list[MemoryType] | None = None
    tags: list[str] | None = None
    authority_tier_max: int = Field(default=9, ge=1, le=9)
    time_after: datetime | None = None
    time_before: datetime | None = None
    limit: int = Field(default=10, ge=1, le=100)

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
```

---

## 7. Subsystem Protocols

Each subsystem is a `@runtime_checkable Protocol`. The substrate wires concrete implementations at init time. Tests can substitute fakes.

### 7.1 IdentityResolver

```python
@runtime_checkable
class IdentityResolver(Protocol):
    async def resolve(self, signal: SignalEnvelope) -> Identity: ...
```

**Invariant:** Every `ExecutionResult` must contain the resolved identity's `organization_id`.

**Source mapping:**
- `control_plane/identity/ai_identity.py` → personality, name
- `state/context/context.py` → `load_context_from_env()` → org/venture config
- `state/business/business_instance.py` → `get_ai_name()`, business stage

**Concrete implementation:** ~120 lines. Loads from BIS + Neon `organizations` table.

### 7.2 ContextAssembler

```python
@runtime_checkable
class ContextAssembler(Protocol):
    async def assemble(self, signal: SignalEnvelope, identity: Identity) -> ExecutionContext: ...
```

**Invariant:** Context must include the last 10 conversation turns for the user+channel pair.

**Source mapping:**
- `control_plane/runtime/cognitive_loop.py` PERCEIVE + UNDERSTAND stages → conversation history assembly
- `state/memory/memory.py` → `ConversationMemory.get_session()` → recent messages
- `state/memory/memory.py` → `AgentMemory.semantic_search()` → relevant memories

**Concrete implementation:** ~200 lines. Merges conversation history + semantic recall + active goals + business context.

### 7.3 GovernanceEngine

```python
@runtime_checkable
class GovernanceEngine(Protocol):
    async def classify(self, signal: SignalEnvelope, context: ExecutionContext) -> GovernanceVerdict: ...
    async def check_execution(self, plan: ExecutionPlan, verdict: GovernanceVerdict) -> bool: ...
```

**Invariant:** `classify()` is called **before** any adapter invocation. If `verdict.decision == DENY`, no execution occurs. `check_execution()` is the final gate — it re-validates that the plan matches the verdict.

**Source mapping:**
- `governance/policy/authority_engine.py` → `RISK_CLASSES` dict, `classify_action()`, autonomy levels
- `services/umh/governance/policy_engine.py` → richer policy patterns
- `services/umh/protocols/governance.py` → Pydantic `GovernanceVerdict` model

**Risk classification (from production `authority_engine.py`):**

| Class | Actions | Auto-execute? |
|-------|---------|:-------------:|
| CRITICAL | send_message, send_email, execute_payment, delete_records, bulk_update, mass_outreach, publish_content | Never (level 999) |
| HIGH | send_dm, create_outreach, post_content, update_external_crm, book_call | Autonomy ≥ 3 |
| MEDIUM | draft_message, draft_content, create_task, create_document | Autonomy ≥ 1 |
| LOW | analyze, research, score, classify, summarize, read, query, report, draft_brief, generate_brief | Always (level 0) |

**Concrete implementation:** ~250 lines. Merges production risk classes with UMH governance protocol.

### 7.4 MemorySystem

```python
@runtime_checkable
class MemorySystem(Protocol):
    async def recall(self, query: MemoryQuery) -> list[MemoryEntry]: ...
    async def store(self, entry: MemoryEntry) -> UUID: ...
    async def log_interaction(self, signal_id: UUID, content: str, response: str, provider: str, **kwargs: Any) -> UUID: ...
```

**Invariant:** Every `store()` call produces a Neon row. Every `recall()` respects authority tier ordering.

**Source mapping:**
- `state/memory/memory.py` → `AgentMemory.log()`, `semantic_search()`, `log_outcome()`, `embed_and_store()`
- `state/memory/memory.py` → `ConversationMemory.store()`, `get_session()`
- `state/memory/contracts/canonical_memory_store_v1.py` → canonical interface pattern

**Neon tables used:** `interactions` (35,485 rows), `embeddings` (35,277 rows), `events` (27,851 rows), `entity_links` (30,717 rows), `memory_store` (63 entries).

**Concrete implementation:** ~350 lines. Wraps existing `AgentMemory` + `ConversationMemory` behind unified protocol. Adds authority tier to semantic search ranking (V2).

### 7.5 ComponentRegistry

```python
@runtime_checkable
class ComponentRegistry(Protocol):
    async def register(self, component: Component) -> RegistrationResult: ...
    async def lookup(self, component_type: ComponentType | None = None, capabilities: list[str] | None = None) -> list[Component]: ...
    async def get(self, component_id: UUID) -> Component | None: ...
    async def deregister(self, component_id: UUID) -> bool: ...
```

**Invariant:** If it's not registered, it doesn't exist to the substrate. The spine only routes to registered adapters.

**Source mapping:**
- `state/registries/skill_registry.py` → 140 skills in Neon
- Neon `agents` table → 16 agents
- Neon `skills` + `skill_versions` tables
- `services/umh/protocols/capability.py` → `Capability`, `CapabilityCategory`

**Neon backing:** New `component_registry` table (Section 10).

**Concrete implementation:** ~200 lines. Unified registry backed by Neon. Boot sequence loads existing agents + skills + adapters.

### 7.6 SignalRouter

```python
@runtime_checkable
class SignalRouter(Protocol):
    async def route(self, signal: SignalEnvelope) -> ExecutionResult: ...
```

**Invariant:** `route()` is the single entry point from transports. It orchestrates the full lifecycle: identity → context → governance → spine.

**Source mapping:**
- `control_plane/runtime/gateway.py` (2,063 lines) → `EntrepreneurOSGateway.handle()` flow: capability tagging → schema validation → approval gate → memory → route by type. Now includes deterministic-first intent classification and fix-forever error recording.
- `interface/presence/handlers/intent_handler.py` (410 lines) → centralized deterministic intent classification with pattern matching fallback
- `execution/runtime/capability_router.py` (610 lines) → intent-driven tool selection and dynamic routing
- `services/umh/control_plane/pipeline.py` → `ExecutionPipeline.submit_signal()` 10-stage pipeline

**Concrete implementation:** ~350 lines. This is the integration point that wires all subsystems together. Absorbs the deterministic intent classification from gateway + intent_handler.

### 7.7 ExecutionSpine

```python
@runtime_checkable
class ExecutionSpine(Protocol):
    async def execute(self, signal: SignalEnvelope, context: ExecutionContext, verdict: GovernanceVerdict) -> ExecutionResult: ...
```

**Invariant:** Every call to `execute()` produces exactly one `TraceRecord` and one `FeedbackRecord` in Neon. No exception.

**Source mapping:**
- `control_plane/runtime/cognitive_loop.py` (1,448 lines) → 8 stages: PERCEIVE, UNDERSTAND, PLAN, EXECUTE, VERIFY, REFLECT, LEARN, STORE. Now includes deterministic-first fallbacks and fix-forever error recording at every LLM call site.
- `execution/runtime/execution_spine.py` → thin execution path with deterministic intent-aware fallback responses
- `execution/runtime/agent_runtime.py` (628 lines) → multi-model dispatch with deterministic-first + fix-forever
- `services/umh/control_plane/pipeline.py` → 10-stage pipeline: signal → trace → govern → work_packet → execute → proof → outcome → trace_store → memory_candidate → memory_promote

**Merged spine stages:**

| # | Stage | What it does | Source |
|---|-------|-------------|--------|
| 1 | Interpret | Deterministic intent classification → LLM decomposition if needed | gateway intent_handler (deterministic-first) + CogLoop.PERCEIVE + UMH Interpretation |
| 2 | Recall | Semantic memory search for relevant context | CogLoop.UNDERSTAND + AgentMemory.semantic_search |
| 3 | Lookup | Registry query for capable adapters/agents + capability routing | capability_router + UMH pipeline + registry |
| 4 | Compose | Build execution plan (prompt + model selection + params) | CogLoop.PLAN + UMH WorkPacket |
| 5 | Route | Select adapter and dispatch | model_router.call_with_fallback() |
| 6 | Execute | Invoke adapter, get response; deterministic fallback if all LLMs fail | CogLoop.EXECUTE + UMH executor + deterministic spine fallback |
| 7 | Trace | Record full execution provenance + error recording | UMH TraceStore + fix-forever error log |
| 8 | Feedback | Capture outcome observation + quality signal | CogLoop.REFLECT/LEARN + UMH OutcomeClassifier |

**Deterministic-first principle in the spine:** Every LLM call site has a deterministic fallback path (regex/rules/templates) that produces a usable result when all providers are down. The spine never returns empty — it always has an intent-aware deterministic response available. This was applied across all production files in 67 commits since this spec was first written.

**Concrete implementation:** ~450 lines. The heart of the substrate.

### 7.8 TraceRecorder

```python
@runtime_checkable
class TraceRecorder(Protocol):
    async def start(self, signal_id: UUID) -> TraceRecord: ...
    async def add_event(self, trace_id: UUID, event_type: TraceEventType, description: str, **data: Any) -> TraceEvent: ...
    async def complete(self, trace_id: UUID, success: bool) -> None: ...
    async def persist(self, trace: TraceRecord) -> None: ...
```

**Invariant:** `persist()` writes to Neon `traces` table. Every completed trace has ≥2 events (SIGNAL_RECEIVED + EXECUTION_COMPLETED or ERROR).

**Source mapping:**
- `services/umh/observability/trace_store.py` → in-memory trace store with event logging
- `services/umh/protocols/trace.py` → `Trace`, `TraceEvent`, `TraceEventType` Pydantic models

**Concrete implementation:** ~150 lines. Wraps Pydantic models with Neon persistence.

### 7.9 FeedbackCapture

```python
@runtime_checkable
class FeedbackCapture(Protocol):
    async def capture(self, trace: TraceRecord, result: ExecutionResult) -> FeedbackRecord: ...
    async def persist(self, feedback: FeedbackRecord) -> None: ...
```

**Invariant:** Every completed execution produces exactly one `FeedbackRecord`. Implicit feedback is auto-generated; explicit feedback comes from user reactions.

**Source mapping:**
- `learning/feedback/feedback_loop.py` → feedback capture pattern
- `services/umh/observability/outcome_classifier.py` → outcome type classification
- `services/umh/protocols/outcome.py` → `Outcome`, `OutcomeType`

**Concrete implementation:** ~120 lines.

---

## 8. Adapter Protocol

```python
from typing import Protocol, runtime_checkable

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

**LLM Adapter (wraps model_router):**

```python
class LLMAdapter:
    """Wraps model_router.call_with_fallback() as a substrate Adapter.

    Does NOT modify model_router internals. The 1,516-line router,
    circuit breaker, multi-provider fallback, deterministic-first
    fallbacks, fix-forever error recording, and cc_sdk integration
    survive as-is. New CLI adapters (Codex, Hermes, OpenCode) are
    already integrated into the provider chain.
    """

    adapter_id: UUID = Field(default_factory=uuid4)
    adapter_type: str = "llm"
    name: str = "model_router"

    async def execute(self, request: AdapterRequest) -> AdapterResponse:
        # Extract from request.payload
        prompt = request.payload["prompt"]
        system = request.payload.get("system")
        task_type = request.payload.get("task_type", "conversation")
        agent_type = request.payload.get("agent_type")
        force_opus = request.payload.get("force_opus", False)
        images = request.payload.get("images")

        # Delegate to production router
        result: RoutingResult = call_with_fallback(
            prompt=prompt,
            system=system,
            task_type=task_type,
            agent_type=agent_type,
            force_opus=force_opus,
            images=images,
        )

        return AdapterResponse(
            adapter_id=self.adapter_id,
            success=bool(result.output),
            output=result.output,
            provider=result.provider,
            model=result.model,
            latency_ms=result.latency_ms,
            tokens_used=result.tokens_used,
            cost_usd=result.cost_usd,
        )

    async def health_check(self) -> bool:
        # Check if at least one provider is healthy
        return True  # model_router handles its own circuit breaker

    def capabilities(self) -> list[str]:
        return ["text_generation", "analysis", "code", "vision", "conversation"]
```

**call_with_fallback signature (production, 1,516 lines):**

```python
def call_with_fallback(
    prompt: str,
    system: str | None = None,
    task_type: TaskType | str = "fast_response",
    trigger_source: str = "conversational",
    agent_type: str | None = None,
    force_opus: bool = False,
    raw_input: str | None = None,
    images: list[tuple[bytes, str]] | None = None,
) -> RoutingResult:
    ...

@dataclass
class RoutingResult:
    output: str
    provider: str
    model: str
    task_type: str
    tokens_used: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
```

**TaskType enum (20 values):**
`CONVERSATION`, `ANALYSIS`, `WEB_SEARCH`, `MARKET_INTEL`, `FAST_RESPONSE`, `LONG_CONTEXT`, `AUTONOMOUS`, `MULTIMODAL`, `BROWSER_CONTROL`, `SCORE`, `CLASSIFY`, `ANALYZE`, `GENERATE`, `SUMMARIZE`, `STRATEGIC`, `CODE`, `RESEARCH`, `SELF_IMPROVE`, `PLAN`, `COORDINATE`

**Provider chain:** `cc_sdk (Opus 4.6 via Max)` → `Gemini 2.5 Flash` → `Groq` → `Ollama gemma3:4b`

---

## 9. Signal Lifecycle State Machine

```
                              ┌─────────┐
                              │ CREATED │
                              └────┬────┘
                                   │ transport produces SignalEnvelope
                                   ▼
                              ┌─────────┐
                              │ ROUTED  │
                              └────┬────┘
                                   │ SignalRouter.route()
                                   ▼
                         ┌──────────────────┐
                         │ IDENTITY_RESOLVED │
                         └────────┬─────────┘
                                  │ IdentityResolver.resolve()
                                  ▼
                         ┌──────────────────┐
                         │ CONTEXT_ASSEMBLED │
                         └────────┬─────────┘
                                  │ ContextAssembler.assemble()
                                  ▼
                              ┌──────────┐
                              │CLASSIFIED│
                              └────┬─────┘
                                   │ GovernanceEngine.classify()
                          ┌────────┼─────────┐
                          ▼        ▼         ▼
                     ┌────────┐ ┌───────┐ ┌────────┐
                     │APPROVED│ │BLOCKED│ │PENDING │
                     └───┬────┘ └───────┘ └────────┘
                         │                (human approval queue)
                         ▼
                    ┌──────────┐
                    │EXECUTING │
                    └────┬─────┘
                         │ ExecutionSpine.execute()
                    ┌────┼────┐
                    ▼         ▼
               ┌────────┐ ┌──────┐
               │SUCCESS │ │FAILED│
               └───┬────┘ └──┬───┘
                   │         │
                   ▼         ▼
               ┌──────────────┐
               │    TRACED    │
               └──────┬───────┘
                      │ TraceRecorder.persist()
                      ▼
            ┌───────────────────┐
            │ FEEDBACK_CAPTURED │
            └───────────────────┘
              FeedbackCapture.capture()
```

**Terminal states:** `BLOCKED`, `FEEDBACK_CAPTURED`.
**Error at any stage:** Transitions to `FAILED` → `TRACED` → `FEEDBACK_CAPTURED` (errors are still traced and fed back).

---

## 10. Neon Schema — New Tables

No existing tables are modified or dropped. Three new tables are added.

```sql
-- Execution traces
CREATE TABLE traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id UUID NOT NULL,
    events JSONB NOT NULL DEFAULT '[]',
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    success BOOLEAN,
    duration_ms DOUBLE PRECISION,
    org_id TEXT NOT NULL,
    CONSTRAINT fk_traces_org FOREIGN KEY (org_id) REFERENCES organizations(id)
);

CREATE INDEX idx_traces_signal_id ON traces (signal_id);
CREATE INDEX idx_traces_org_started ON traces (org_id, started_at DESC);

ALTER TABLE traces ENABLE ROW LEVEL SECURITY;
CREATE POLICY traces_org_isolation ON traces
    USING (org_id = current_setting('app.current_org_id', true));


-- Execution feedback
CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id UUID NOT NULL REFERENCES traces(id),
    signal_id UUID NOT NULL,
    feedback_type TEXT NOT NULL DEFAULT 'implicit',
    outcome_quality DOUBLE PRECISION CHECK (outcome_quality >= 0 AND outcome_quality <= 1),
    learning_signal TEXT DEFAULT '',
    adapter_reliability DOUBLE PRECISION CHECK (adapter_reliability >= 0 AND adapter_reliability <= 1),
    captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB DEFAULT '{}',
    org_id TEXT NOT NULL,
    CONSTRAINT fk_feedback_org FOREIGN KEY (org_id) REFERENCES organizations(id)
);

CREATE INDEX idx_feedback_trace_id ON feedback (trace_id);
CREATE INDEX idx_feedback_org_captured ON feedback (org_id, captured_at DESC);

ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;
CREATE POLICY feedback_org_isolation ON feedback
    USING (org_id = current_setting('app.current_org_id', true));


-- Unified component registry
CREATE TABLE component_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    component_type TEXT NOT NULL,
    name TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT '1.0.0',
    status TEXT NOT NULL DEFAULT 'active',
    capabilities JSONB DEFAULT '[]',
    adapter_id UUID,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB DEFAULT '{}',
    org_id TEXT NOT NULL,
    CONSTRAINT fk_component_org FOREIGN KEY (org_id) REFERENCES organizations(id),
    CONSTRAINT uq_component_name_type_org UNIQUE (name, component_type, org_id)
);

CREATE INDEX idx_component_type_status ON component_registry (component_type, status);

ALTER TABLE component_registry ENABLE ROW LEVEL SECURITY;
CREATE POLICY component_org_isolation ON component_registry
    USING (org_id = current_setting('app.current_org_id', true));
```

**Existing tables preserved (no changes):**

| Table | Rows | Purpose |
|-------|-----:|---------|
| `interactions` | 35,485 | Chat history |
| `embeddings` | 35,277 | Semantic vectors |
| `events` | 27,851 | System events |
| `entity_links` | 30,717 | Cross-references |
| `organizations` | 2 | Org config |
| `ventures` | 8 | Venture config |
| `agents` | 16 | Agent registry |
| `skills` | 140 | Skill registry |
| `skill_versions` | varies | Skill version history |
| `memory_store` | 63 | Canonical memory |
| `outcomes` | 4 | Legacy outcomes (link to new `feedback` via trace_id) |

---

## 11. Invariants as Assertions

Ten checkable statements. Each maps to a concrete verification command. If any fails, the substrate is broken.

```bash
# 1. Control plane exclusivity — no adapter call outside spine
assert $(grep -rn "call_with_fallback\|model_router\." substrate/ adapters/ \
    --include="*.py" | grep -v "adapters/models/" | grep -v "test_" | wc -l) -eq 0

# 2. Single execution spine — only spine.py calls adapters
assert $(grep -rn "adapter\.execute\|\.execute(.*AdapterRequest" substrate/ \
    --include="*.py" | grep -v "execution/spine.py" | grep -v "test_" | wc -l) -eq 0

# 3. Governance before execution — spine checks verdict before adapter call
# Verified by test_governance_blocks_critical.py

# 4. Trace everything — every execution path calls trace.persist()
# Verified by test_signal_to_trace.py

# 5. Memory discipline — no direct Neon writes outside state/
assert $(grep -rn "get_conn\|psycopg2" substrate/ adapters/ transports/ \
    --include="*.py" | wc -l) -eq 0

# 6. Registry as truth — spine only routes to registered components
# Verified by test: unregistered adapter raises ComponentNotFound

# 7. Feedback closes loops — every trace gets a feedback record
# Verified by test_signal_to_trace.py (checks feedback table row)

# 8. Public API boundary — projections never import substrate internals
assert $(grep -rn "from substrate\." projections/ --include="*.py" \
    | grep -v "from substrate import\|from substrate.types import" | wc -l) -eq 0

# 9. Zero dead code — every .py file under substrate/ is imported
# Verified by: python3 scripts/dead_code_check.py

# 10. Pydantic only — no runtime dataclasses in substrate/
assert $(grep -rn "@dataclass" substrate/ --include="*.py" | wc -l) -eq 0
```

---

## 12. Migration Phases

### Phase 0 — Archive and Scaffold (Day 1–2)

**Goal:** Preserve current state, create new directory structure, move files without logic changes.

**Actions:**
1. `git tag pre-unification` on current HEAD
2. Create all directories per Section 4
3. Move surviving files to new locations (Section 12.1)
4. Update all `sys.path` and imports
5. Rename `10_Wiki/` → `knowledge/`

**Verification gate:**
```bash
# Every moved file compiles
find substrate/ adapters/ transports/ state/ -name "*.py" \
    -exec python3 -m py_compile {} \;

# Substrate package is importable
python3 -c "import substrate; print('substrate importable')"

# No broken imports in moved files
python3 -c "
import importlib, pathlib
for p in pathlib.Path('substrate').rglob('*.py'):
    if p.name == '__init__.py': continue
    mod = str(p.with_suffix('')).replace('/', '.')
    importlib.import_module(mod)
print('all substrate modules importable')
"
```

**Estimated diff:** +2,000 lines (new `__init__.py` files, import rewrites), –0 logic lines.

### Phase 1 — Tier 0: Ontology (Day 3–4)

**Goal:** Single source of truth for primitives, laws, and relationships.

**Actions:**
1. Merge `understanding/ontology/primitives.py` (PrimitiveType, RelationshipType) with `services/umh/foundation/primitives.py` (OntologicalCategory, TemporalMode, Modality, CausalRole) into `substrate/ontology/primitives.py`
2. Migrate `services/umh/foundation/laws.py` → `substrate/ontology/laws.py`
3. Migrate `PrimitiveObservation` from dataclass to Pydantic BaseModel

**Verification gate:**
```bash
python3 -c "
from substrate.ontology.primitives import PrimitiveType, OntologicalCategory, RelationshipType
assert len(PrimitiveType) == 10
assert len(OntologicalCategory) == 8
assert len(RelationshipType) == 10
print('ontology: 10 primitives, 8 categories, 10 relationship types')
"

python3 -m pytest tests/substrate/test_ontology.py -v
```

**Estimated diff:** +300 lines (merged module), –600 lines (two source files deleted).

### Phase 2 — Tier 1: Control Plane (Day 5–10)

**Goal:** Unified identity, governance, memory, registry, and signal routing.

**Actions:**
1. Build `substrate/control_plane/identity.py` — merge `ai_identity.py` + `context.py` + `business_instance.py`
2. Build `substrate/control_plane/context.py` — merge context loader + BIS + conversation history
3. Build `substrate/control_plane/governance.py` — merge `authority_engine.py` risk classes + UMH `GovernanceVerdict` protocol
4. Build `substrate/control_plane/memory.py` — unified protocol over existing `state/memory/`
5. Build `substrate/control_plane/registry.py` — unified registry backed by new Neon table
6. Build `substrate/control_plane/router.py` — signal routing, replaces `gateway.py`

**Verification gate:**
```bash
python3 -c "
from substrate.control_plane.identity import ConcreteIdentityResolver
from substrate.control_plane.governance import ConcreteGovernanceEngine
from substrate.control_plane.memory import ConcreteMemorySystem
from substrate.control_plane.registry import ConcreteComponentRegistry
from substrate.control_plane.router import ConcreteSignalRouter
print('all control plane subsystems importable')
"

python3 -m pytest tests/substrate/test_control_plane.py -v
```

**Estimated diff:** +1,400 lines (6 new modules), –800 lines (replaced gateway + scattered identity logic).

### Phase 3 — Tier 2: Execution Spine + Trace + Feedback (Day 11–15)

**Goal:** Single execution path with Neon-persisted trace and feedback.

**Actions:**
1. Build `substrate/execution/spine.py` — the 8-stage merged spine (Section 7.7)
2. Build `substrate/execution/trace.py` — Neon persistence for traces
3. Build `substrate/execution/feedback.py` — auto-generated implicit feedback per execution
4. Migrate ingestion pipeline to `substrate/execution/ingestion/`
5. Build `substrate/__init__.py` — public API wiring all subsystems
6. Run Neon DDL from Section 10 to create `traces`, `feedback`, `component_registry` tables

**Verification gate:**
```bash
# End-to-end: signal in → trace out
python3 -c "
import asyncio
from substrate import Substrate
from substrate.types import SignalEnvelope, SignalSource

async def test():
    s = Substrate()
    result = await s.execute(SignalEnvelope(
        source=SignalSource.SYSTEM,
        content='test signal',
        user_id='test',
        organization_id='test-org',
    ))
    assert result.trace_id is not None
    print(f'execution: {result.outcome.value}, trace: {result.trace_id}')

asyncio.run(test())
"

python3 -m pytest tests/substrate/test_execution.py tests/integration/test_signal_to_trace.py -v
```

**Estimated diff:** +800 lines (spine + trace + feedback), –1,200 lines (cognitive_loop + execution_spine + gateway replaced).

### Phase 4 — Tier 3: Adapters (Day 16–18)

**Goal:** All external connections through formal adapter interface.

**Actions:**
1. Build `adapters/protocol.py` — `Adapter` runtime_checkable Protocol
2. Build `adapters/models/llm_adapter.py` — wrapper around `model_router.call_with_fallback()`
3. Wrap GWS connector as `GWSAdapter`
4. Wrap voice engine as `VoiceAdapter`
5. Register all adapters in component registry at boot

**Verification gate:**
```bash
python3 -c "
from adapters.models.llm_adapter import LLMAdapter
from adapters.protocol import Adapter
assert isinstance(LLMAdapter(), Adapter)
print('LLM adapter satisfies Adapter protocol')
"

python3 -m pytest tests/adapters/ -v
```

**Estimated diff:** +400 lines (protocol + wrappers), –0 lines (model_router untouched).

### Phase 5 — Transports (Day 19–22)

**Goal:** All user interfaces produce `SignalEnvelope` and route through `substrate.execute()`.

**Actions:**
1. Refactor `services/discord_bot.py` (5,481 lines) → `transports/discord/bot.py`
   - Strip direct gateway/cognitive_loop calls
   - Add `signal_factory.py` — every Discord message → `SignalEnvelope`
   - Call `substrate.execute(envelope)` for all responses
   - Preserve voice/vision attachment handling (multimodal envelopes)
   - Migrate `execution/transport/voice_first.py` (370 lines) → `transports/discord/voice_first.py`
2. Refactor `services/operator_api.py` → `transports/api/operator.py`
   - All REST and WebSocket endpoints → `SignalEnvelope` → `substrate.execute()`
3. Migrate `services/umh/control_plane/cockpit_api.py` (1,034 lines, 40 endpoints) → `transports/api/cockpit.py`
   - Already serves live UMH data; rewire to call substrate.execute() and substrate.query()
4. Migrate `services/umh/node_mesh/` (850 lines) → `transports/node_mesh/`
   - NodeMeshServer already uses WebSocket + SignalSocket pattern; rewire to substrate
5. Move `apps/cockpit/` → `transports/cockpit/` (React dashboard)
6. Rebuild Docker containers with new import paths

**Verification gate:**
```bash
# Discord bot starts and connects
docker restart os-discord && sleep 5
docker logs os-discord --tail 20 | grep -q "Ready"

# Send test message, verify trace appears in Neon
python3 -c "
from state.storage.db import get_conn
with get_conn('munoz-holdings') as cur:
    cur.execute('SELECT count(*) FROM traces')
    print(f'traces in Neon: {cur.fetchone()[0]}')
"
```

**Estimated diff:** +600 lines (signal factories, refactored bot), –800 lines (removed direct gateway calls).

### Phase 6 — Prune and Verify (Day 23–25)

**Goal:** Delete everything not wired. Verify the system is clean.

**Actions:**
1. Delete all empty/dead directories from old structure
2. Delete all files not imported by any surviving module
3. Full test suite pass
4. `python3 -m py_compile` on every `.py` file
5. `ruff format` on all surviving code
6. Rebuild codebase graph (`scripts/update-graph`)
7. Update memory palace rooms to reflect new structure
8. Update all CLAUDE.md files with new paths
9. Update all skill files with new paths

**Verification gate:**
```bash
# Zero dead code
python3 scripts/dead_code_check.py

# All invariants pass (Section 11)
bash scripts/invariant_check.sh

# Full test suite
python3 -m pytest tests/ -v --tb=short

# All files compile
find . -name "*.py" -not -path "./.claude/*" -not -path "./_archive/*" \
    -exec python3 -m py_compile {} \;

# Docker containers healthy
docker ps --format '{{.Names}} {{.Status}}' | grep -E "os-discord|os-bot"
```

**Estimated diff:** –250,000 lines deleted (see Section 14).

### Phase 7 — EOS Projection (Day 26–30)

**Goal:** First application layer on the substrate.

**Actions:**
1. Build `projections/eos/__init__.py` — EOS-specific signal handlers
2. Build department agents (CEO, Sales, Marketing) registered in component registry
3. Build outreach workflow as substrate execution plan
4. Build CRM views as memory queries
5. Wire EOS agents to respond via Discord transport

**Verification gate:**
```bash
# EOS agents registered
python3 -c "
import asyncio
from substrate import Substrate
from substrate.types import ComponentType

async def check():
    s = Substrate()
    agents = await s._registry.lookup(component_type=ComponentType.AGENT)
    eos_agents = [a for a in agents if 'eos' in a.name.lower()]
    print(f'EOS agents registered: {len(eos_agents)}')
    for a in eos_agents:
        print(f'  - {a.name}: {a.capabilities}')

asyncio.run(check())
"

# Outreach workflow executes through substrate
python3 -m pytest tests/acceptance/test_eos_outreach_flow.py -v
```

**Estimated diff:** +1,000 lines (projection layer). This is new code, not migration.

---

## 13. Test Contracts

### Unit Tests (15)

| # | Test | Asserts |
|---|------|---------|
| 1 | `test_signal_envelope_requires_content` | `SignalEnvelope(content="")` is valid; missing `content` raises `ValidationError` |
| 2 | `test_signal_envelope_authority_tier_range` | `authority_tier=0` raises; `authority_tier=10` raises; 1–9 valid |
| 3 | `test_governance_verdict_executable` | `APPROVE` → executable; `DENY` → not; `CONDITIONAL` with unmet conditions → not |
| 4 | `test_risk_classification_critical` | `classify("send_message")` → `RiskClass.CRITICAL` |
| 5 | `test_risk_classification_unknown_defaults_low` | `classify("unknown_action")` → `RiskClass.LOW` |
| 6 | `test_trace_record_add_event` | `trace.add_event()` appends to events list, sets trace_id |
| 7 | `test_trace_record_complete` | `trace.complete(True)` sets completed_at, duration_ms, success |
| 8 | `test_execution_result_is_success` | `SUCCESS` and `PARTIAL_SUCCESS` → True; `FAILURE`, `TIMEOUT`, `BLOCKED` → False |
| 9 | `test_primitive_type_has_10_values` | `len(PrimitiveType) == 10` |
| 10 | `test_ontological_category_has_8_values` | `len(OntologicalCategory) == 8` |
| 11 | `test_component_registry_lookup_by_type` | Register 3 components (2 adapters, 1 agent); lookup by ADAPTER returns 2 |
| 12 | `test_component_registry_deregister` | Deregistered component not found by lookup |
| 13 | `test_memory_query_limit_range` | `limit=0` raises; `limit=101` raises; 1–100 valid |
| 14 | `test_adapter_response_from_routing_result` | LLMAdapter converts RoutingResult → AdapterResponse with correct field mapping |
| 15 | `test_feedback_record_quality_range` | `outcome_quality=-0.1` raises; `outcome_quality=1.1` raises; 0–1 valid |

### Integration Tests (5)

| # | Test | Given / When / Then |
|---|------|---------------------|
| 1 | `test_signal_to_trace` | **Given** a configured Substrate with Neon connection. **When** `substrate.execute(signal)` completes. **Then** `traces` table has 1 new row with matching `signal_id`, ≥2 events, and `success` is not None. |
| 2 | `test_governance_blocks_critical` | **Given** a signal that maps to `send_email` action with autonomy level 1. **When** `substrate.execute(signal)`. **Then** result.outcome == `BLOCKED`, result.governance_decision == `DENY`, no adapter was called, trace still recorded. |
| 3 | `test_memory_round_trip` | **Given** a MemoryEntry. **When** `substrate.query(MemoryQuery(query_text=entry.content))`. **Then** returned list contains entry with matching id and content. |
| 4 | `test_registry_boot_loads_existing` | **Given** Neon `agents` table has 16 rows and `skills` has 140 rows. **When** Substrate initializes. **Then** `registry.lookup()` returns ≥156 components. |
| 5 | `test_feedback_persisted_per_execution` | **Given** a configured Substrate. **When** `substrate.execute(signal)` completes. **Then** `feedback` table has 1 new row with matching `trace_id`. |

### Acceptance Tests (10)

| # | Test | Given / When / Then |
|---|------|---------------------|
| 1 | `test_discord_message_produces_signal` | **Given** Discord message event. **When** signal_factory processes it. **Then** produces SignalEnvelope with source=USER, correct user_id, content matches message. |
| 2 | `test_discord_voice_produces_multimodal_signal` | **Given** Discord message with voice attachment. **When** signal_factory processes it. **Then** produces SignalEnvelope with modality=VOICE, attachment populated. |
| 3 | `test_api_request_produces_signal` | **Given** HTTP POST to operator API. **When** endpoint handler processes it. **Then** produces SignalEnvelope, calls substrate.execute(), returns ExecutionResult as JSON. |
| 4 | `test_eos_outreach_flow` | **Given** EOS projection registered. **When** user sends "draft outreach for lead X" via Discord. **Then** substrate executes through EOS agent, produces drafted message, trace shows EOS agent in adapter call. |
| 5 | `test_full_lifecycle_trace_has_all_events` | **Given** a successful execution. **When** trace is retrieved from Neon. **Then** events include: SIGNAL_RECEIVED, IDENTITY_RESOLVED, CONTEXT_ASSEMBLED, GOVERNANCE_DECIDED, ADAPTER_CALLED, ADAPTER_RESPONDED, EXECUTION_COMPLETED, FEEDBACK_CAPTURED. |
| 6 | `test_all_invariants_pass` | Run all 10 invariant assertions from Section 11. All pass. |
| 7 | `test_zero_dead_files` | **Given** complete substrate. **When** `dead_code_check.py` runs. **Then** exit code 0, no unreferenced files. |
| 8 | `test_no_dataclasses_in_substrate` | `grep -rn "@dataclass" substrate/` returns 0 matches. |
| 9 | `test_projection_isolation` | `grep -rn "from substrate\." projections/ | grep -v "from substrate import\|from substrate.types import"` returns 0 matches. |
| 10 | `test_docker_containers_healthy` | All containers in `docker ps` show status "Up" and health "healthy". |

---

## 14. What Gets Deleted (~230,000 lines)

| Category | Approx Lines | Files | Value Already Extracted? |
|----------|------------:|------:|:------------------------:|
| `execution/workers/workstation/` constitutional engines | ~20,000 | 45 | No — future organism runtime (post-MVP) |
| `execution/transport/` bulk transport infra (excluding voice_first.py) | ~19,600 | 59 | Partial — patterns inform `transports/` |
| `execution/runtime/` v1 contracts (excluding model_router, agent_runtime, capability_router) | ~12,000 | 37 | Yes — superseded by `substrate/types.py` |
| `services/umh/` remainder after extraction (protocols, pipeline, governance, observability, sockets, foundation, execution, memory, awareness, model_routing, launch, proofs, tests, workstation, data) | ~15,000 | 80 | Yes — protocols + pipeline + organism + node_mesh + integrations extracted |
| `control_plane/` non-core subdirs (actions, delegation, coordination, events, goals, strategy, onboarding, scheduling) | ~10,000 | 35 | No — premature, rebuild on substrate when needed |
| `core/` most files | ~4,000 | 20 | Partial — contracts superseded by substrate |
| `understanding/` non-ontology remainder (excluding domain bridges) | ~4,000 | 12 | Yes — ontology merged |
| `execution/environments/` work packet builders | ~3,000 | 10 | No — rebuild on adapter interface |
| `execution/workflows/` | ~1,000 | 5 | No — rebuild on substrate composition |
| `execution/agents/` browser agent | ~600 | 3 | No — rebuild as browser adapter |
| `execution/tasks/` task executor | ~300 | 2 | Yes — merged into spine |
| `execution/engine/` | ~300 | 2 | Yes — superseded by spine |
| `runtime/` (root-level stubs) | ~800 | 8 | Yes — everything useful already in state/ |
| `interface/` (after intent_handler extraction) | ~3,600 | 14 | Yes — intent_handler merged into router |
| `observability/` (after trace extraction) | ~900 | 5 | Yes — merged into substrate trace |
| `operations/` (after memory merge) | ~2,400 | 10 | Yes — merged into substrate memory |
| `archive/` legacy archive | ~23,000 | 93 | No — already archived, safe to delete |
| `.agents/` agent soul docs | ~9,000 | 35 | Partial — agent definitions migrate to registry |
| Dead test files (tests for deleted code) | ~20,000 | 100+ | No — tests for code that no longer exists |
| Miscellaneous duplicates and dead imports | ~5,000+ | 50+ | N/A |

**What survives extraction from `services/umh/` (migrated, not deleted):**
- `organism/` (1,554 lines, 9 files) → `substrate/organism/`
- `node_mesh/` (850 lines, 6 files) → `transports/node_mesh/`
- `integrations/` (5,148 lines, 21 files) → `integrations/`
- `control_plane/cockpit_api.py` (1,034 lines) → `transports/api/cockpit.py`
- `protocols/*.py` (14 files) → `substrate/types.py`
- `control_plane/pipeline.py` → patterns into `substrate/execution/spine.py`

**Total deleted: ~230,000 lines across ~600+ files.**
**Total surviving: ~100,000–110,000 lines across ~250 files.**

**Pre-deletion safeguard:** `git tag pre-unification` preserves full history. Every deleted directory is archived in git, not lost.

---

## 15. Post-MVP Subsystem Roadmap

After substrate MVP, the remaining 13 of 24 subsystems build on this foundation. Each uses the public API and adds new capabilities without architectural changes.

| Priority | Subsystem | Location | Dependencies | Unlocks |
|:--------:|-----------|----------|--------------|---------|
| 1 | Template System | `substrate/control_plane/templates.py` | Registry | Reusable execution patterns |
| 2 | Library System | `substrate/control_plane/library.py` | Templates, Memory | Knowledge reuse |
| 3 | Composition Engine | `substrate/execution/composition.py` | Templates, Registry | Multi-step workflows |
| 4 | Completeness Engine | `substrate/execution/completeness.py` | Composition | Validation before execution |
| 5 | Quality Engine | `substrate/execution/quality.py` | Feedback, Trace | Output scoring |
| 6 | Law Kernel (full) | `substrate/ontology/law_kernel.py` | Ontology | Domain-specific state transitions |
| 7 | Workstation Modes | `substrate/control_plane/workstation.py` | Identity, Context | Session continuity |
| 8 | World Model (core) | `world_model/core.py` | Memory, Ontology | User + system + environment models |
| 9 | Simulation | `intelligence/simulation/` | World Model, Law Kernel | Test actions before execution |
| 10 | Deliberation Council | `intelligence/deliberation/` | World Model, Quality | Multi-perspective reasoning |
| 11 | Self-Recursion | `substrate/learning/self_recursion.py` | Feedback, Quality, Trace | Self-improvement loop |
| 12 | Resource Allocation | `substrate/control_plane/resources.py` | Registry, Trace | Compute/attention budgeting |
| 13 | Homeostasis | `substrate/learning/homeostasis.py` | Resource Allocation, Feedback | Self-regulation |

---

## Appendix A: What Survives (Source Mapping)

### Production-proven code (relocate, do not modify logic)

| Current Location | New Location | Lines | Status |
|------------------|-------------|------:|--------|
| `execution/runtime/model_router.py` | `adapters/models/model_router.py` | 1,516 | CONFIRMED_RUNTIME |
| `adapters/model_adapters/cc_sdk.py` | `adapters/models/cc_sdk.py` | 464 | CONFIRMED_RUNTIME |
| `adapters/model_adapters/codex_cli.py` | `adapters/models/codex_cli.py` | 258 | CONFIRMED_RUNTIME |
| `adapters/model_adapters/hermes_cli.py` | `adapters/models/hermes_cli.py` | 178 | CONFIRMED_RUNTIME |
| `adapters/model_adapters/opencode_cli.py` | `adapters/models/opencode_cli.py` | 180 | CONFIRMED_RUNTIME |
| `execution/runtime/agent_runtime.py` | `adapters/models/agent_runtime.py` | 628 | CONFIRMED_RUNTIME |
| `state/memory/memory.py` | `state/memory/memory.py` | 1,039 | CONFIRMED_RUNTIME |
| `state/storage/db.py` | `state/storage/db.py` | ~100 | CONFIRMED_RUNTIME |
| `state/context/context.py` | `state/context/context.py` | ~200 | CONFIRMED_RUNTIME |
| `state/business/business_instance.py` | `state/business/business_instance.py` | ~200 | CONFIRMED_RUNTIME |
| `governance/policy/authority_engine.py` | → merged into `substrate/control_plane/governance.py` | 225 | CONFIRMED_RUNTIME |
| `control_plane/identity/ai_identity.py` | → merged into `substrate/control_plane/identity.py` | ~300 | CONFIRMED_RUNTIME |
| `services/discord_bot.py` | `transports/discord/bot.py` | 5,481 | CONFIRMED_RUNTIME |
| `services/operator_api.py` | `transports/api/operator.py` | 554 | CONFIRMED_RUNTIME |
| `adapters/google_workspace/` | `adapters/google_workspace/` | 3,531 | CONFIRMED_RUNTIME |
| `execution/voice/` | `adapters/capabilities/voice/` | ~1,000 | CONFIRMED_RUNTIME |
| `state/registries/skill_registry.py` | `state/registries/skill_registry.py` | ~200 | CONFIRMED_RUNTIME |
| `execution/transport/voice_first.py` | `transports/discord/voice_first.py` | 370 | NEW — voice-first response path |
| `execution/runtime/capability_router.py` | → merged into `substrate/control_plane/router.py` | 610 | NEW — intent-driven tool selection |
| `interface/presence/handlers/intent_handler.py` | → merged into `substrate/control_plane/router.py` | 410 | NEW — deterministic intent classification |

### New subsystems extracted from `services/umh/` (relocate intact)

| Current Location | New Location | Lines | Files | Status |
|------------------|-------------|------:|------:|--------|
| `services/umh/organism/` | `substrate/organism/` | 1,554 | 9 | Built, tested, not wired to production |
| `services/umh/node_mesh/` | `transports/node_mesh/` | 850 | 6 | Built, tested, not wired to production |
| `services/umh/integrations/creatoros/` | `integrations/creatoros/` | ~2,500 | 7 | Built, tested |
| `services/umh/integrations/lyfeos/` | `integrations/lyfeos/` | ~2,500 | 7 | Built, tested |
| `services/umh/control_plane/cockpit_api.py` | `transports/api/cockpit.py` | 1,034 | 1 | 40 live endpoints |
| `understanding/domains/creator.py` | `substrate/ontology/domains/creator.py` | 515 | 1 | NEW — creator domain bridge |
| `understanding/domains/life.py` | `substrate/ontology/domains/life.py` | 568 | 1 | NEW — life domain bridge |
| `daemon/` | `daemon/` (stays) | 1,278 | 14 | Windows node — runs on desktop, not VPS |

### Valuable code merged into substrate (extract patterns, delete originals)

| Current Location | Merges Into | Value Extracted |
|------------------|-------------|-----------------|
| `control_plane/runtime/cognitive_loop.py` (1,448 lines) | `substrate/execution/spine.py` | 8-stage execution pattern + deterministic fallbacks |
| `control_plane/runtime/gateway.py` (2,063 lines) | `substrate/control_plane/router.py` | Signal routing, deterministic intent classification, fix-forever error recording |
| `execution/runtime/execution_spine.py` | `substrate/execution/spine.py` | Thin execution structure + deterministic intent-aware fallback |
| `services/umh/foundation/primitives.py` | `substrate/ontology/primitives.py` | OntologicalCategory, TemporalMode |
| `services/umh/foundation/laws.py` | `substrate/ontology/laws.py` | Law definitions |
| `services/umh/protocols/*.py` | `substrate/types.py` | All Pydantic protocol models |
| `services/umh/governance/` | `substrate/control_plane/governance.py` | Policy engine patterns |
| `services/umh/observability/` | `substrate/execution/trace.py` | Trace store, outcome classifier |
| `services/umh/control_plane/pipeline.py` | `substrate/execution/spine.py` | 10-stage pipeline pattern |
| `services/umh/organism/protocols.py` | `substrate/types.py` | Deliverable, AgentMessage, WorkerSpec, CritiqueResult, LearningSignal |
| `understanding/ontology/primitives.py` | `substrate/ontology/primitives.py` | PrimitiveType enum |
| `understanding/ontology/primitive_decomposition_v1.py` | `substrate/execution/ingestion/decomposer.py` | LLM extraction logic |
| `learning/feedback/feedback_loop.py` | `substrate/execution/feedback.py` | Feedback capture |
| `state/memory/contracts/canonical_memory_store_v1.py` | `substrate/control_plane/memory.py` | Canonical memory interface |
| `runtime/ingestion/` | `substrate/execution/ingestion/` | Pipeline stages |
