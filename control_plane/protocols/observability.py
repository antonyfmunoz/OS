"""UMH Protocol — Observability + Proof Layer (Layer 9).

Covers trace (§15.1) and proof artifacts (§15.2).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from .common import (
    AdapterRef,
    AuthorityLevel,
    ConfirmationStatus,
    EnvironmentRef,
    EvidenceType,
    RiskLevel,
)


# ---------------------------------------------------------------------------
# Supporting types for Trace
# ---------------------------------------------------------------------------


class TimestampSet(BaseModel):
    """Collection of timestamps for a trace. Referenced in §15.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    received_at: int
    interpretation_completed_at: int | None = None
    composition_completed_at: int | None = None
    governance_decided_at: int | None = None
    execution_started_at: int | None = None
    execution_completed_at: int | None = None
    proof_validated_at: int | None = None


class ExecutionResult(BaseModel):
    """Result of an execution. Referenced in §15.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    success: bool
    output: Any = None
    error: str | None = None
    duration_ms: int | None = None


class Outcome(BaseModel):
    """Whether the action achieved its goal. Referenced in §15.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    outcome_id: str
    achieved: bool
    score: float = 0.0
    explanation: str = ""


class FeedbackEvent(BaseModel):
    """Feedback signal for learning. Referenced in §15.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    feedback_id: str
    type: str
    content: Any = None
    source: str = ""
    timestamp: int = 0


class GovernanceDecision(BaseModel):
    """Governance decision record. Referenced in §15.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    decision_id: str
    authority_level: AuthorityLevel
    risk_level: RiskLevel
    approved: bool
    reason: str = ""
    rules_applied: list[str] = []


class WorldStateSnapshot(BaseModel):
    """Snapshot of world state at trace time. Referenced in §15.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    snapshot_id: str
    timestamp: int
    entity_count: int = 0
    active_goal_count: int = 0
    summary: str = ""


# ---------------------------------------------------------------------------
# §15.1 — Trace
# ---------------------------------------------------------------------------


class Trace(BaseModel):
    """Full inspectable execution record. Defined in canonical synthesis §15.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    trace_id: str
    user_id: str
    input: dict[str, Any]
    interpretation: dict[str, Any] | None = None
    world_context: WorldStateSnapshot | None = None
    memory_context: list[dict[str, Any]] = []
    composition: dict[str, Any] | None = None
    governance: GovernanceDecision | None = None
    work_packet: dict[str, Any] | None = None
    adapter_boundary: AdapterRef | None = None
    environment: EnvironmentRef | None = None
    execution: ExecutionResult | None = None
    result: Any = None
    proof: dict[str, Any] | None = None
    outcome: Outcome | None = None
    feedback: FeedbackEvent | None = None
    timestamps: TimestampSet


# ---------------------------------------------------------------------------
# §15.2 — Proof Artifact
# ---------------------------------------------------------------------------


class ParityResult(BaseModel):
    """Result of a parity check between access paths. Referenced in §15.2."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    parity_id: str
    path_a: str
    path_b: str
    match: bool
    discrepancies: list[str] = []


class ProofArtifact(BaseModel):
    """Evidence that an action happened correctly. Defined in canonical synthesis §15.2."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    proof_id: str
    action_id: str
    packet_id: str
    environment_id: str
    worker_id: str
    evidence_type: EvidenceType
    evidence_summary: str
    source: str
    timestamp: int
    governance_compliance: bool
    no_secret_confirmed: bool
    no_mutation_confirmed: bool
    parity_result: ParityResult | None = None
    founder_confirmation_status: ConfirmationStatus
    confidence: float
