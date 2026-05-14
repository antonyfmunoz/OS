"""UMH Protocol — Composition Layer (Layer 5).

Covers registries (§11.1), templates (§11.3), capabilities (§11.4),
composition engine (§11.6), and mastery (§11.10).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict

from .common import (
    AdapterRef,
    AuthorityLevel,
    Benchmark,
    CapabilityRef,
    Constraint,
    CostModel,
    EnvironmentRef,
    EnvironmentType,
    FailureMode,
    GovernancePolicyRef,
    ItemStatus,
    LatencyModel,
    MasteryCategory,
    MasteryRef,
    MasteryStatus,
    ProofRequirement,
    RiskLevel,
    Slot,
    Step,
    TemplateRef,
    TestRef,
    WorkerRef,
)


# ---------------------------------------------------------------------------
# §11.1 — Registry
# ---------------------------------------------------------------------------


class RegistryItem(BaseModel):
    """A selectable component in a registry. Defined in canonical synthesis §11.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    type: str
    version: str
    inputs: dict[str, Any] = {}
    outputs: dict[str, Any] = {}
    constraints: list[Constraint] = []
    environment: EnvironmentRef | None = None
    cost: CostModel | None = None
    latency: LatencyModel | None = None
    reliability: float = 1.0
    authority_required: AuthorityLevel = AuthorityLevel.AUTONOMOUS
    dependencies: list[str] = []
    owner: str = ""
    status: ItemStatus = ItemStatus.ACTIVE
    metadata: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# §11.3 — Templates
# ---------------------------------------------------------------------------


class ImmutablePrimitive(BaseModel):
    """Structural element that does not change per user. Referenced in §11.3."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    primitive_id: str
    name: str
    type: str
    description: str = ""


class FeedbackLoopSpec(BaseModel):
    """Feedback loop specification for a template or composition. Referenced in §11.3."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    loop_id: str
    name: str
    trigger: str = ""
    description: str = ""


class GovernanceSpec(BaseModel):
    """Governance requirements for a template or composition. Referenced in §11.3."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    authority_required: AuthorityLevel = AuthorityLevel.AUTONOMOUS
    risk_level: RiskLevel = RiskLevel.READ_ONLY
    approval_required: bool = False
    description: str = ""


class MemoryUpdateRule(BaseModel):
    """Rule for memory updates after execution. Referenced in §11.3."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    condition: str
    action: str
    description: str = ""


class QualityCriterion(BaseModel):
    """A quality criterion for composition output. Referenced in §11.6."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    criterion_id: str
    name: str
    description: str = ""
    threshold: float | None = None


class Template(BaseModel):
    """Typed, instantiable blueprint. Defined in canonical synthesis §11.3."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    domain: str
    purpose: str
    immutable_primitives: list[ImmutablePrimitive] = []
    customizable_slots: list[Slot] = []
    required_slots: list[Slot] = []
    optional_slots: list[Slot] = []
    inputs: dict[str, Any] = {}
    outputs: dict[str, Any] = {}
    constraints: list[Constraint] = []
    default_steps: list[Step] = []
    feedback_loop: FeedbackLoopSpec | None = None
    failure_modes: list[FailureMode] = []
    governance_requirements: GovernanceSpec | None = None
    quality_benchmarks: list[Benchmark] = []
    compatible_capabilities: list[CapabilityRef] = []
    compatible_adapters: list[AdapterRef] = []
    memory_update_rules: list[MemoryUpdateRule] = []


# ---------------------------------------------------------------------------
# §11.4 — Capabilities
# ---------------------------------------------------------------------------


class ObservabilitySpec(BaseModel):
    """Observability requirements for a capability. Referenced in §11.4."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    trace_required: bool = True
    proof_required: bool = False
    metrics_required: bool = False
    description: str = ""


class Capability(BaseModel):
    """An abstract ability. Defined in canonical synthesis §11.4."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    capability_id: str
    name: str
    inputs: dict[str, Any] = {}
    outputs: dict[str, Any] = {}
    cost: CostModel | None = None
    latency: LatencyModel | None = None
    reliability: float = 1.0
    required_environment: list[EnvironmentType] = []
    required_adapter: list[AdapterRef] = []
    required_worker: list[str] = []
    authority_required: AuthorityLevel = AuthorityLevel.AUTONOMOUS
    constraints: list[Constraint] = []
    failure_modes: list[FailureMode] = []
    observability: ObservabilitySpec | None = None
    proof_requirements: list[ProofRequirement] = []


# ---------------------------------------------------------------------------
# §11.6 — Composition Engine
# ---------------------------------------------------------------------------


class Dependency(BaseModel):
    """A dependency between steps in a composition. Referenced in §11.6."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    dependency_id: str
    source_step_id: str
    target_step_id: str
    type: str = "sequential"


class ExecutableComposition(BaseModel):
    """Complete executable composition. Defined in canonical synthesis §11.6."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    composition_id: str
    goal: str
    selected_template: TemplateRef | None = None
    filled_slots: dict[str, Any] = {}
    selected_capabilities: list[CapabilityRef] = []
    required_adapters: list[AdapterRef] = []
    required_environments: list[EnvironmentRef] = []
    required_workers: list[WorkerRef] = []
    steps: list[Step] = []
    dependencies: list[Dependency] = []
    constraints: list[Constraint] = []
    failure_modes: list[FailureMode] = []
    feedback_loop: FeedbackLoopSpec | None = None
    governance_requirements: GovernanceSpec | None = None
    mastery_requirements: list[MasteryRef] = []
    quality_criteria: list[QualityCriterion] = []
    memory_update_rules: list[MemoryUpdateRule] = []


# ---------------------------------------------------------------------------
# §11.10 — Mastery
# ---------------------------------------------------------------------------


class MasteryGap(BaseModel):
    """A specific gap in mastery. Referenced in §11.10."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    gap_id: str
    description: str
    severity: str = "medium"
    remediation: str = ""


class MasteryRequirement(BaseModel):
    """Mastery requirement before execution. Defined in canonical synthesis §11.10."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    mastery_id: str
    category: MasteryCategory
    target: str
    capability_scope: list[str] = []
    risk_level: RiskLevel = RiskLevel.READ_ONLY
    required_freshness: timedelta = timedelta(days=30)
    required_tests: list[TestRef] = []
    required_proof: list[ProofRequirement] = []
    current_status: MasteryStatus = MasteryStatus.NOT_ASSESSED
    gaps: list[MasteryGap] = []
