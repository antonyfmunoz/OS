"""UMH Protocol — State Layer (Layer 4).

Covers world model (§10.1) and memory system (§10.2).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from .common import (
    CapabilityRef,
    Constraint,
    EnvironmentRef,
    EvidenceRef,
    MemoryRef,
    MemoryType,
    PromotionStatus,
    RelationshipRef,
)


# ---------------------------------------------------------------------------
# §10.1 — World Model
# ---------------------------------------------------------------------------


class WorldEntity(BaseModel):
    """An entity in the world model. Defined in canonical synthesis §10.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    entity_id: str
    type: str
    name: str
    attributes: dict[str, Any] = {}
    relationships: list[RelationshipRef] = []
    state: dict[str, Any] = {}
    confidence: float
    source: str
    timestamp: int


class Fact(BaseModel):
    """A source-attributed fact. Defined in canonical synthesis §10.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    value: Any
    confidence: float
    source: str
    timestamp: int
    scope: str
    expiry: int | None = None
    evidence: list[EvidenceRef] = []


class TemporalState(BaseModel):
    """Time-aware state tracking. Referenced in §10.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    current_timestamp: int
    last_updated: int
    temporal_horizon: str = ""


class UncertaintyModel(BaseModel):
    """Uncertainty tracking for the world model. Referenced in §10.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    overall_confidence: float
    stale_entity_count: int = 0
    unverified_fact_count: int = 0


class Resource(BaseModel):
    """A tracked resource. Referenced in §10.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    resource_id: str
    name: str
    type: str = ""
    quantity: float | None = None
    unit: str = ""


class Risk(BaseModel):
    """A tracked risk. Referenced in §10.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    risk_id: str
    name: str
    description: str = ""
    probability: float = 0.0
    impact: float = 0.0


class Task(BaseModel):
    """An active task in the world model. Referenced in §10.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    task_id: str
    name: str
    status: str = "active"
    priority: float = 0.5


class Goal(BaseModel):
    """An active goal. Referenced in §10.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    goal_id: str
    description: str
    priority: float = 0.5
    domain: str = ""


class WorldRelationship(BaseModel):
    """A relationship in the world model. Referenced in §10.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    relationship_id: str
    type: str
    source_entity_id: str
    target_entity_id: str
    confidence: float = 1.0


class WorldState(BaseModel):
    """Full world model state. Defined in canonical synthesis §10.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    entities: list[WorldEntity] = []
    relationships: list[WorldRelationship] = []
    state_values: dict[str, Any] = {}
    temporal_state: TemporalState | None = None
    uncertainty: UncertaintyModel | None = None
    active_goals: list[Goal] = []
    active_tasks: list[Task] = []
    constraints: list[Constraint] = []
    environments: list[EnvironmentRef] = []
    resources: list[Resource] = []
    capabilities: list[CapabilityRef] = []
    risks: list[Risk] = []


# ---------------------------------------------------------------------------
# §10.2 — Memory System
# ---------------------------------------------------------------------------


class MemoryRecord(BaseModel):
    """A typed, governed memory entry. Defined in canonical synthesis §10.2."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    memory_id: str
    type: MemoryType
    content: Any
    source: str
    confidence: float
    timestamp: int
    scope: str
    tags: list[str] = []
    links: list[MemoryRef] = []
    expiry: int | None = None
    promotion_status: PromotionStatus
    reason: str
