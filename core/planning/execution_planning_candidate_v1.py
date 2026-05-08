"""Execution Planning Candidate v1 for the UMH substrate layer.

Governed execution planning candidates that model proposed actions
WITHOUT allowing autonomous execution. Plans are hypotheses about
action. Plans are not actions.

Plans consume canonical truth (governed memory, world models,
governance receipts). Plans may NOT consume candidate hypotheses,
ungoverned interpretations, or recursive self-generated plans.

The planning layer is purely epistemic.

UMH substrate subsystem. Phase 96.8Z.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class PlanStatus(str, Enum):
    DRAFT = "draft"
    ASSEMBLED = "assembled"
    AWAITING_GOVERNANCE = "awaiting_governance"
    GOVERNANCE_APPROVED = "governance_approved"
    GOVERNANCE_REJECTED = "governance_rejected"


class RiskLevel(str, Enum):
    NEGLIGIBLE = "negligible"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EscalationTier(str, Enum):
    NONE = "none"
    REVIEW = "review"
    APPROVAL = "approval"
    FOUNDER_APPROVAL = "founder_approval"
    BLOCKED = "blocked"


FORBIDDEN_PLANNING_ACTIONS = frozenset(
    {
        "runtime_invocation",
        "wallet_usage",
        "api_execution",
        "shell_execution",
        "browser_execution",
        "financial_execution",
        "credential_access",
        "memory_mutation",
        "canonical_mutation",
        "adapter_invocation",
        "trade_placement",
        "money_allocation",
        "autonomous_execution",
        "recursive_plan_consumption",
    }
)

FORBIDDEN_PLAN_INPUTS = frozenset(
    {
        "candidate_hypothesis",
        "ungoverned_interpretation",
        "recursive_self_generated_plan",
        "hidden_runtime_state",
    }
)

ALLOWED_PLAN_INPUTS = frozenset(
    {
        "canonical_memory",
        "canonical_world_model",
        "governance_receipt",
        "deterministic_observation",
        "constraint_system",
    }
)

RISK_ESCALATION_THRESHOLDS: dict[str, float] = {
    "financial_risk": 0.3,
    "execution_risk": 0.5,
    "uncertainty_risk": 0.6,
    "trust_boundary_risk": 0.3,
    "external_dependency_risk": 0.5,
    "recursive_autonomy_risk": 0.1,
}


@dataclass
class PlanningLineageReference:
    """Full lineage chain for an execution planning candidate."""

    source_canonical_model_id: str = ""
    source_canonical_memory_ids: list[str] = field(default_factory=list)
    source_governance_receipt_ids: list[str] = field(default_factory=list)
    source_world_model_hash: str = ""
    planning_trace_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_canonical_model_id": self.source_canonical_model_id,
            "source_canonical_memory_ids": self.source_canonical_memory_ids,
            "source_governance_receipt_ids": self.source_governance_receipt_ids,
            "source_world_model_hash": self.source_world_model_hash,
            "planning_trace_id": self.planning_trace_id,
        }


@dataclass
class ResourceRequirement:
    """A resource needed by a proposed action."""

    resource_id: str
    resource_type: str
    description: str
    quantity: float = 0.0
    unit: str = ""
    is_financial: bool = False
    estimated_cost: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "description": self.description,
            "quantity": self.quantity,
            "unit": self.unit,
            "is_financial": self.is_financial,
            "estimated_cost": self.estimated_cost,
        }


@dataclass
class ConstraintEvaluation:
    """Evaluation of a constraint against a proposed action."""

    constraint_id: str
    constraint_type: str
    description: str
    satisfied: bool = False
    violation_risk: float = 0.0
    mitigation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "constraint_type": self.constraint_type,
            "description": self.description,
            "satisfied": self.satisfied,
            "violation_risk": self.violation_risk,
            "mitigation": self.mitigation,
        }


@dataclass
class RiskEnvelope:
    """Multi-dimensional risk assessment for a plan."""

    financial_risk: float = 0.0
    execution_risk: float = 0.0
    uncertainty_risk: float = 0.0
    trust_boundary_risk: float = 0.0
    external_dependency_risk: float = 0.0
    recursive_autonomy_risk: float = 0.0
    overall_risk: float = 0.0
    escalation_tier: EscalationTier = EscalationTier.NONE
    escalation_reasons: list[str] = field(default_factory=list)

    def compute_overall_risk(self) -> float:
        dimensions = [
            self.financial_risk,
            self.execution_risk,
            self.uncertainty_risk,
            self.trust_boundary_risk,
            self.external_dependency_risk,
            self.recursive_autonomy_risk,
        ]
        return max(dimensions) if dimensions else 0.0

    def compute_escalation(self) -> tuple[EscalationTier, list[str]]:
        reasons: list[str] = []
        max_tier = EscalationTier.NONE

        checks = [
            ("financial_risk", self.financial_risk),
            ("execution_risk", self.execution_risk),
            ("uncertainty_risk", self.uncertainty_risk),
            ("trust_boundary_risk", self.trust_boundary_risk),
            ("external_dependency_risk", self.external_dependency_risk),
            ("recursive_autonomy_risk", self.recursive_autonomy_risk),
        ]

        for name, value in checks:
            threshold = RISK_ESCALATION_THRESHOLDS.get(name, 0.5)
            if value >= threshold:
                reasons.append(f"{name} ({value:.2f}) exceeds threshold ({threshold:.2f})")
                if name in ("financial_risk", "trust_boundary_risk"):
                    tier = EscalationTier.FOUNDER_APPROVAL
                elif name == "recursive_autonomy_risk":
                    tier = EscalationTier.BLOCKED
                else:
                    tier = EscalationTier.APPROVAL
                if _tier_rank(tier) > _tier_rank(max_tier):
                    max_tier = tier

        return max_tier, reasons

    def to_dict(self) -> dict[str, Any]:
        return {
            "financial_risk": self.financial_risk,
            "execution_risk": self.execution_risk,
            "uncertainty_risk": self.uncertainty_risk,
            "trust_boundary_risk": self.trust_boundary_risk,
            "external_dependency_risk": self.external_dependency_risk,
            "recursive_autonomy_risk": self.recursive_autonomy_risk,
            "overall_risk": self.overall_risk,
            "escalation_tier": self.escalation_tier.value,
            "escalation_reasons": self.escalation_reasons,
        }


def _tier_rank(tier: EscalationTier) -> int:
    return {
        EscalationTier.NONE: 0,
        EscalationTier.REVIEW: 1,
        EscalationTier.APPROVAL: 2,
        EscalationTier.FOUNDER_APPROVAL: 3,
        EscalationTier.BLOCKED: 4,
    }[tier]


@dataclass
class ExpectedOutcome:
    """An expected outcome of a proposed action."""

    outcome_id: str
    description: str
    probability: float = 0.0
    impact_type: str = ""
    impact_magnitude: float = 0.0
    supporting_truth_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "description": self.description,
            "probability": self.probability,
            "impact_type": self.impact_type,
            "impact_magnitude": self.impact_magnitude,
            "supporting_truth_ids": self.supporting_truth_ids,
        }


@dataclass
class ExecutionDependency:
    """A dependency between two proposed actions."""

    dependency_id: str
    from_action_id: str
    to_action_id: str
    dependency_type: str = "requires"
    is_blocking: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "dependency_id": self.dependency_id,
            "from_action_id": self.from_action_id,
            "to_action_id": self.to_action_id,
            "dependency_type": self.dependency_type,
            "is_blocking": self.is_blocking,
        }


@dataclass
class ProposedAction:
    """A single proposed action within an execution plan."""

    action_id: str
    action_type: str
    description: str
    rationale: str = ""
    supporting_truth_ids: list[str] = field(default_factory=list)
    supporting_entity_ids: list[str] = field(default_factory=list)
    resource_requirements: list[ResourceRequirement] = field(default_factory=list)
    constraint_evaluations: list[ConstraintEvaluation] = field(default_factory=list)
    expected_outcomes: list[ExpectedOutcome] = field(default_factory=list)
    risk_envelope: RiskEnvelope = field(default_factory=RiskEnvelope)
    dependencies: list[str] = field(default_factory=list)
    rollback_reference: str = ""
    sequence_order: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "description": self.description,
            "rationale": self.rationale,
            "supporting_truth_ids": self.supporting_truth_ids,
            "supporting_entity_ids": self.supporting_entity_ids,
            "resource_requirements": [r.to_dict() for r in self.resource_requirements],
            "constraint_evaluations": [c.to_dict() for c in self.constraint_evaluations],
            "expected_outcomes": [o.to_dict() for o in self.expected_outcomes],
            "risk_envelope": self.risk_envelope.to_dict(),
            "dependencies": self.dependencies,
            "rollback_reference": self.rollback_reference,
            "sequence_order": self.sequence_order,
        }


@dataclass
class ActionSequence:
    """An ordered sequence of proposed actions."""

    sequence_id: str
    actions: list[ProposedAction] = field(default_factory=list)
    total_estimated_cost: float = 0.0
    total_risk: float = 0.0

    def compute_total_cost(self) -> float:
        return sum(
            r.estimated_cost
            for a in self.actions
            for r in a.resource_requirements
            if r.is_financial
        )

    def compute_total_risk(self) -> float:
        if not self.actions:
            return 0.0
        return max(a.risk_envelope.overall_risk for a in self.actions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence_id": self.sequence_id,
            "actions": [a.to_dict() for a in self.actions],
            "total_estimated_cost": self.total_estimated_cost,
            "total_risk": self.total_risk,
        }


@dataclass
class ActionGraph:
    """DAG execution structure for proposed actions."""

    graph_id: str
    nodes: list[ProposedAction] = field(default_factory=list)
    edges: list[ExecutionDependency] = field(default_factory=list)
    topological_order: list[str] = field(default_factory=list)
    rollback_chain: list[str] = field(default_factory=list)

    def compute_topological_order(self) -> list[str]:
        adjacency: dict[str, list[str]] = {}
        in_degree: dict[str, int] = {}
        for node in self.nodes:
            adjacency.setdefault(node.action_id, [])
            in_degree.setdefault(node.action_id, 0)

        for edge in self.edges:
            adjacency.setdefault(edge.from_action_id, []).append(edge.to_action_id)
            in_degree.setdefault(edge.to_action_id, 0)
            in_degree[edge.to_action_id] += 1
            in_degree.setdefault(edge.from_action_id, 0)

        queue = sorted([nid for nid, deg in in_degree.items() if deg == 0])
        order: list[str] = []

        while queue:
            current = queue.pop(0)
            order.append(current)
            for neighbor in sorted(adjacency.get(current, [])):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
            queue.sort()

        return order

    def has_cycle(self) -> bool:
        order = self.compute_topological_order()
        return len(order) != len(self.nodes)

    def get_execution_roots(self) -> list[str]:
        targets = {e.to_action_id for e in self.edges}
        return sorted(n.action_id for n in self.nodes if n.action_id not in targets)

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "topological_order": self.topological_order,
            "rollback_chain": self.rollback_chain,
        }


@dataclass
class PlanningGovernanceBoundary:
    """Structural enforcement of what execution planning candidates may do."""

    may_propose_actions: bool = True
    may_sequence_actions: bool = True
    may_model_dependencies: bool = True
    may_estimate_resources: bool = True
    may_estimate_risk: bool = True
    may_estimate_outcomes: bool = True
    may_attach_canonical_truths: bool = True
    may_invoke_runtime: bool = False
    may_use_wallet: bool = False
    may_execute_api: bool = False
    may_execute_shell: bool = False
    may_execute_browser: bool = False
    may_execute_financial: bool = False
    may_access_credentials: bool = False
    may_mutate_memory: bool = False
    may_mutate_canonical: bool = False

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.may_invoke_runtime:
            errors.append("planning candidate may not invoke runtime")
        if self.may_use_wallet:
            errors.append("planning candidate may not use wallet")
        if self.may_execute_api:
            errors.append("planning candidate may not execute API calls")
        if self.may_execute_shell:
            errors.append("planning candidate may not execute shell commands")
        if self.may_execute_browser:
            errors.append("planning candidate may not execute browser actions")
        if self.may_execute_financial:
            errors.append("planning candidate may not execute financial transactions")
        if self.may_access_credentials:
            errors.append("planning candidate may not access credentials")
        if self.may_mutate_memory:
            errors.append("planning candidate may not mutate memory")
        if self.may_mutate_canonical:
            errors.append("planning candidate may not mutate canonical truth")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "may_propose_actions": self.may_propose_actions,
            "may_sequence_actions": self.may_sequence_actions,
            "may_model_dependencies": self.may_model_dependencies,
            "may_estimate_resources": self.may_estimate_resources,
            "may_estimate_risk": self.may_estimate_risk,
            "may_estimate_outcomes": self.may_estimate_outcomes,
            "may_attach_canonical_truths": self.may_attach_canonical_truths,
            "may_invoke_runtime": self.may_invoke_runtime,
            "may_use_wallet": self.may_use_wallet,
            "may_execute_api": self.may_execute_api,
            "may_execute_shell": self.may_execute_shell,
            "may_execute_browser": self.may_execute_browser,
            "may_execute_financial": self.may_execute_financial,
            "may_access_credentials": self.may_access_credentials,
            "may_mutate_memory": self.may_mutate_memory,
            "may_mutate_canonical": self.may_mutate_canonical,
        }


@dataclass
class ExecutionPlanningCandidate:
    """An execution planning candidate — a governed hypothesis about action."""

    plan_id: str
    plan_type: str
    description: str
    action_sequence: ActionSequence | None = None
    action_graph: ActionGraph | None = None
    risk_envelope: RiskEnvelope = field(default_factory=RiskEnvelope)
    lineage: PlanningLineageReference = field(default_factory=PlanningLineageReference)
    boundary: PlanningGovernanceBoundary = field(default_factory=PlanningGovernanceBoundary)
    status: PlanStatus = PlanStatus.DRAFT
    governance_status: str = ""
    governance_receipt_id: str = ""
    source_canonical_model_id: str = ""
    source_truth_ids: list[str] = field(default_factory=list)
    input_sources: list[str] = field(default_factory=list)
    blocked_actions: list[str] = field(default_factory=list)
    allowed_actions: list[str] = field(default_factory=list)
    forbidden_inputs: list[str] = field(default_factory=list)
    rollback_reference: str = ""
    output_hash: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def compute_output_hash(self) -> str:
        serializable: dict[str, Any] = {
            "plan_id": self.plan_id,
            "plan_type": self.plan_type,
            "description": self.description,
            "action_sequence": self.action_sequence.to_dict() if self.action_sequence else None,
            "action_graph": self.action_graph.to_dict() if self.action_graph else None,
            "risk_envelope": {
                "financial_risk": self.risk_envelope.financial_risk,
                "execution_risk": self.risk_envelope.execution_risk,
                "uncertainty_risk": self.risk_envelope.uncertainty_risk,
                "trust_boundary_risk": self.risk_envelope.trust_boundary_risk,
                "external_dependency_risk": self.risk_envelope.external_dependency_risk,
                "recursive_autonomy_risk": self.risk_envelope.recursive_autonomy_risk,
            },
            "source_canonical_model_id": self.source_canonical_model_id,
            "source_truth_ids": self.source_truth_ids,
            "input_sources": self.input_sources,
        }
        content = json.dumps(serializable, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def validate(self) -> list[str]:
        errors = self.boundary.validate()
        if not self.plan_id:
            errors.append("plan_id required")
        if not self.plan_type:
            errors.append("plan_type required")
        if not self.blocked_actions:
            errors.append("blocked_actions must be populated")
        if self.action_graph and self.action_graph.has_cycle():
            errors.append("action graph contains a cycle")
        for src in self.input_sources:
            if src in FORBIDDEN_PLAN_INPUTS:
                errors.append(f"forbidden input source: {src}")
        for act in self.allowed_actions:
            if act in FORBIDDEN_PLANNING_ACTIONS:
                errors.append(f"forbidden action in allowed_actions: {act}")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "plan_type": self.plan_type,
            "description": self.description,
            "action_sequence": self.action_sequence.to_dict() if self.action_sequence else None,
            "action_graph": self.action_graph.to_dict() if self.action_graph else None,
            "risk_envelope": self.risk_envelope.to_dict(),
            "lineage": self.lineage.to_dict(),
            "boundary": self.boundary.to_dict(),
            "status": self.status.value,
            "governance_status": self.governance_status,
            "governance_receipt_id": self.governance_receipt_id,
            "source_canonical_model_id": self.source_canonical_model_id,
            "source_truth_ids": self.source_truth_ids,
            "input_sources": self.input_sources,
            "blocked_actions": self.blocked_actions,
            "allowed_actions": self.allowed_actions,
            "forbidden_inputs": self.forbidden_inputs,
            "rollback_reference": self.rollback_reference,
            "output_hash": self.output_hash,
            "timestamp": self.timestamp,
        }


class _DeterministicIdGenerator:
    """Generates reproducible IDs from a seed hash + counter."""

    def __init__(self, seed: str) -> None:
        self._seed = seed
        self._counter = 0

    def next_id(self, prefix: str) -> str:
        self._counter += 1
        raw = hashlib.sha256(f"{self._seed}:{prefix}:{self._counter}".encode("utf-8")).hexdigest()[
            :8
        ]
        return f"{prefix}-{raw}"


class ExecutionPlanningAssembler:
    """Assembles execution planning candidates from canonical truth inputs.

    Consumes canonical world models and governance receipts.
    Produces deterministic planning candidates with action graphs,
    risk envelopes, and governance escalation requirements.

    The assembler is purely epistemic — it models actions but never
    executes them.
    """

    def __init__(self) -> None:
        self.boundary = PlanningGovernanceBoundary()

    def assemble(
        self,
        canonical_model_id: str,
        canonical_model_hash: str,
        entities: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
        truth_ids: list[str],
        governance_receipt_ids: list[str],
        plan_type: str = "operational",
        description: str = "",
    ) -> ExecutionPlanningCandidate:
        boundary_errors = self.boundary.validate()
        if boundary_errors:
            raise ValueError(f"Boundary violation: {boundary_errors}")

        if not canonical_model_id:
            raise ValueError("canonical_model_id required")
        if not canonical_model_hash:
            raise ValueError("canonical_model_hash required")
        if not entities and not truth_ids:
            raise ValueError("at least one entity or truth_id required")

        ids = _DeterministicIdGenerator(canonical_model_hash)

        proposed_actions: list[ProposedAction] = []
        for i, entity in enumerate(entities):
            action = ProposedAction(
                action_id=ids.next_id("ACT"),
                action_type=f"process_{entity.get('entity_type', 'unknown')}",
                description=f"Process entity: {entity.get('label', 'unknown')}",
                rationale=f"Derived from canonical entity {entity.get('entity_id', '')}",
                supporting_truth_ids=truth_ids,
                supporting_entity_ids=[entity.get("entity_id", "")],
                risk_envelope=RiskEnvelope(
                    execution_risk=0.1 + (i * 0.05),
                    uncertainty_risk=1.0 - entity.get("confidence", 0.5),
                ),
                rollback_reference=ids.next_id("ROLLBACK"),
                sequence_order=i,
            )
            action.risk_envelope.overall_risk = action.risk_envelope.compute_overall_risk()
            tier, reasons = action.risk_envelope.compute_escalation()
            action.risk_envelope.escalation_tier = tier
            action.risk_envelope.escalation_reasons = reasons
            proposed_actions.append(action)

        dependencies: list[ExecutionDependency] = []
        for rel in relationships:
            from_act = self._find_action_for_entity(
                proposed_actions, rel.get("from_entity_id", ""), entities
            )
            to_act = self._find_action_for_entity(
                proposed_actions, rel.get("to_entity_id", ""), entities
            )
            if from_act and to_act and from_act != to_act:
                dep = ExecutionDependency(
                    dependency_id=ids.next_id("DEP"),
                    from_action_id=from_act,
                    to_action_id=to_act,
                    dependency_type=rel.get("relationship_type", "requires"),
                    is_blocking=True,
                )
                dependencies.append(dep)

        action_graph = ActionGraph(
            graph_id=ids.next_id("AGRAPH"),
            nodes=proposed_actions,
            edges=dependencies,
        )
        action_graph.topological_order = action_graph.compute_topological_order()
        action_graph.rollback_chain = [
            a.rollback_reference for a in proposed_actions if a.rollback_reference
        ]

        sequence = ActionSequence(
            sequence_id=ids.next_id("ASEQ"),
            actions=sorted(proposed_actions, key=lambda a: a.sequence_order),
        )
        sequence.total_estimated_cost = sequence.compute_total_cost()
        sequence.total_risk = sequence.compute_total_risk()

        plan_risk = RiskEnvelope(
            financial_risk=sum(
                r.estimated_cost
                for a in proposed_actions
                for r in a.resource_requirements
                if r.is_financial
            )
            / max(len(proposed_actions), 1),
            execution_risk=max(
                (a.risk_envelope.execution_risk for a in proposed_actions), default=0.0
            ),
            uncertainty_risk=max(
                (a.risk_envelope.uncertainty_risk for a in proposed_actions), default=0.0
            ),
            trust_boundary_risk=0.0,
            external_dependency_risk=len(dependencies) * 0.05,
            recursive_autonomy_risk=0.0,
        )
        plan_risk.overall_risk = plan_risk.compute_overall_risk()
        tier, reasons = plan_risk.compute_escalation()
        plan_risk.escalation_tier = tier
        plan_risk.escalation_reasons = reasons

        lineage = PlanningLineageReference(
            source_canonical_model_id=canonical_model_id,
            source_governance_receipt_ids=governance_receipt_ids,
            source_world_model_hash=canonical_model_hash,
            planning_trace_id=ids.next_id("PTRACE"),
        )

        candidate = ExecutionPlanningCandidate(
            plan_id=ids.next_id("EPLAN"),
            plan_type=plan_type,
            description=description or f"Execution plan for canonical model {canonical_model_id}",
            action_sequence=sequence,
            action_graph=action_graph,
            risk_envelope=plan_risk,
            lineage=lineage,
            boundary=self.boundary,
            status=PlanStatus.ASSEMBLED,
            source_canonical_model_id=canonical_model_id,
            source_truth_ids=truth_ids,
            input_sources=list(ALLOWED_PLAN_INPUTS),
            blocked_actions=list(FORBIDDEN_PLANNING_ACTIONS),
            allowed_actions=[
                "propose_action",
                "sequence_actions",
                "model_dependencies",
                "estimate_resources",
                "estimate_risk",
                "estimate_outcomes",
                "submit_for_governance",
            ],
            forbidden_inputs=list(FORBIDDEN_PLAN_INPUTS),
            rollback_reference=ids.next_id("ROLLBACK"),
        )
        candidate.output_hash = candidate.compute_output_hash()

        validation_errors = candidate.validate()
        if validation_errors:
            raise ValueError(f"Planning candidate validation failed: {validation_errors}")

        return candidate

    def _find_action_for_entity(
        self,
        actions: list[ProposedAction],
        entity_id: str,
        entities: list[dict[str, Any]],
    ) -> str | None:
        for i, ent in enumerate(entities):
            if ent.get("entity_id") == entity_id and i < len(actions):
                return actions[i].action_id
        return None
