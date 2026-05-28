"""Composition Engine — deterministic intent → plan from observed capabilities.

Turns:
  Intent + Context + Constraints → Available capabilities → Dependencies
  → Risks → Executable plan

This is NOT freeform LLM planning. It composes from observed reality.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")

from substrate.types import RiskClass


class GovernanceMode(str, Enum):
    AUTONOMOUS = "autonomous"
    ASSISTED = "assisted"
    OPERATOR_REQUIRED = "operator_required"


class StepStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    SKIPPED = "skipped"


@dataclass
class CompositionIntent:
    description: str
    category: str = "general"
    priority: str = "normal"
    source: str = "operator"

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "category": self.category,
            "priority": self.priority,
            "source": self.source,
        }


@dataclass
class CompositionContext:
    readiness_score: float = 0.0
    active_contradictions: int = 0
    top_bottleneck: str = ""
    execution_mode: str = "observe"

    def to_dict(self) -> dict[str, Any]:
        return {
            "readiness_score": self.readiness_score,
            "active_contradictions": self.active_contradictions,
            "top_bottleneck": self.top_bottleneck,
            "execution_mode": self.execution_mode,
        }


@dataclass
class CompositionConstraint:
    name: str
    description: str
    hard: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "hard": self.hard}


@dataclass
class CapabilityMatch:
    capability_name: str
    entity_id: str
    status: str = "available"
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability": self.capability_name,
            "entity_id": self.entity_id,
            "status": self.status,
            "confidence": self.confidence,
        }


@dataclass
class CompositionRisk:
    description: str
    risk_class: RiskClass = RiskClass.LOW
    mitigation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "risk_class": self.risk_class.value,
            "mitigation": self.mitigation,
        }


@dataclass
class CompositionStep:
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    description: str = ""
    action: str = ""
    depends_on: list[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    risk_class: RiskClass = RiskClass.LOW
    governance_mode: GovernanceMode = GovernanceMode.AUTONOMOUS
    requires_capability: str = ""
    verification: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "action": self.action,
            "depends_on": self.depends_on,
            "status": self.status.value,
            "risk_class": self.risk_class.value,
            "governance_mode": self.governance_mode.value,
            "requires_capability": self.requires_capability,
            "verification": self.verification,
        }


@dataclass
class CompositionPlan:
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    intent: CompositionIntent | None = None
    context: CompositionContext | None = None
    constraints: list[CompositionConstraint] = field(default_factory=list)
    capabilities_matched: list[CapabilityMatch] = field(default_factory=list)
    steps: list[CompositionStep] = field(default_factory=list)
    risks: list[CompositionRisk] = field(default_factory=list)
    missing_prerequisites: list[str] = field(default_factory=list)
    overall_risk: RiskClass = RiskClass.LOW
    governance_required: GovernanceMode = GovernanceMode.AUTONOMOUS
    validation_strategy: str = ""
    rollback_plan: str = ""
    evidence: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def ready_steps(self) -> list[CompositionStep]:
        completed_ids = {s.id for s in self.steps if s.status == StepStatus.COMPLETED}
        ready = []
        for step in self.steps:
            if step.status != StepStatus.PENDING:
                continue
            if all(dep in completed_ids for dep in step.depends_on):
                ready.append(step)
        return ready

    def summary(self) -> dict[str, Any]:
        status_counts: dict[str, int] = {}
        for s in self.steps:
            status_counts[s.status.value] = status_counts.get(s.status.value, 0) + 1
        return {
            "plan_id": self.id,
            "intent": self.intent.description if self.intent else "",
            "total_steps": len(self.steps),
            "step_status": status_counts,
            "overall_risk": self.overall_risk.value,
            "governance_required": self.governance_required.value,
            "missing_prerequisites": len(self.missing_prerequisites),
            "risks": len(self.risks),
            "created_at": self.created_at,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "intent": self.intent.to_dict() if self.intent else None,
            "context": self.context.to_dict() if self.context else None,
            "constraints": [c.to_dict() for c in self.constraints],
            "capabilities_matched": [c.to_dict() for c in self.capabilities_matched],
            "steps": [s.to_dict() for s in self.steps],
            "risks": [r.to_dict() for r in self.risks],
            "missing_prerequisites": self.missing_prerequisites,
            "overall_risk": self.overall_risk.value,
            "governance_required": self.governance_required.value,
            "validation_strategy": self.validation_strategy,
            "rollback_plan": self.rollback_plan,
            "evidence": self.evidence,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Intent → Plan composition logic
# ---------------------------------------------------------------------------

_INTENT_PATTERNS: dict[str, list[dict[str, Any]]] = {
    "fix_contradictions": [
        {"action": "run_contradiction_engine", "desc": "Detect current contradictions",
         "risk": "low", "gov": "autonomous", "verify": "Check contradiction count"},
        {"action": "resolve_missing_files", "desc": "Create or locate missing files",
         "risk": "medium", "gov": "assisted", "verify": "File existence check"},
        {"action": "fix_deployment_state", "desc": "Align deployment with declared state",
         "risk": "high", "gov": "operator_required", "verify": "Deploy hash matches"},
        {"action": "verify_resolution", "desc": "Re-run contradiction engine to confirm fixes",
         "risk": "low", "gov": "autonomous", "verify": "Zero critical contradictions"},
    ],
    "improve_readiness": [
        {"action": "assess_readiness", "desc": "Compute current readiness scores",
         "risk": "low", "gov": "autonomous", "verify": "All 6 dimensions scored"},
        {"action": "identify_weakest_dimension", "desc": "Find lowest-scoring dimension",
         "risk": "low", "gov": "autonomous", "verify": "Dimension identified with factors"},
        {"action": "execute_improvement", "desc": "Run targeted improvement for weakest dimension",
         "risk": "medium", "gov": "assisted", "verify": "Score improved by ≥5 points"},
    ],
    "wire_missing_panel": [
        {"action": "identify_panel", "desc": "Find cockpit panel without backend",
         "risk": "low", "gov": "autonomous", "verify": "Panel identified"},
        {"action": "create_api_route", "desc": "Add API route for panel",
         "risk": "medium", "gov": "assisted", "verify": "Route responds 200"},
        {"action": "wire_bridge", "desc": "Add bridge handler for route",
         "risk": "medium", "gov": "assisted", "verify": "Bridge handler registered"},
        {"action": "verify_panel", "desc": "Confirm panel loads data",
         "risk": "low", "gov": "autonomous", "verify": "Panel renders without error"},
    ],
    "safe_maintenance": [
        {"action": "check_readiness", "desc": "Verify system readiness for maintenance",
         "risk": "low", "gov": "autonomous", "verify": "Readiness ≥ 50"},
        {"action": "run_probes", "desc": "Execute workload probes",
         "risk": "low", "gov": "autonomous", "verify": "All probes return"},
        {"action": "execute_maintenance", "desc": "Run low-risk maintenance tasks",
         "risk": "medium", "gov": "assisted", "verify": "Tasks complete without error"},
        {"action": "verify_health", "desc": "Post-maintenance health check",
         "risk": "low", "gov": "autonomous", "verify": "Health check passes"},
    ],
    "general": [
        {"action": "assess_state", "desc": "Assess current system state",
         "risk": "low", "gov": "autonomous", "verify": "State assessed"},
        {"action": "plan_execution", "desc": "Determine execution approach",
         "risk": "low", "gov": "autonomous", "verify": "Approach determined"},
        {"action": "execute", "desc": "Execute the planned approach",
         "risk": "medium", "gov": "assisted", "verify": "Execution completes"},
        {"action": "verify", "desc": "Verify execution outcome",
         "risk": "low", "gov": "autonomous", "verify": "Outcome verified"},
    ],
}

_RISK_MAP = {"low": RiskClass.LOW, "medium": RiskClass.MEDIUM, "high": RiskClass.HIGH, "critical": RiskClass.CRITICAL}
_GOV_MAP = {"autonomous": GovernanceMode.AUTONOMOUS, "assisted": GovernanceMode.ASSISTED, "operator_required": GovernanceMode.OPERATOR_REQUIRED}


def _classify_intent(description: str) -> str:
    desc_lower = description.lower()
    if any(w in desc_lower for w in ["contradiction", "mismatch", "discrepancy", "truth"]):
        return "fix_contradictions"
    if any(w in desc_lower for w in ["readiness", "improve", "strengthen"]):
        return "improve_readiness"
    if any(w in desc_lower for w in ["panel", "wire", "cockpit surface"]):
        return "wire_missing_panel"
    if any(w in desc_lower for w in ["maintenance", "cleanup", "health check", "rotate"]):
        return "safe_maintenance"
    return "general"


class CompositionEngine:
    """Deterministic composition from observed capabilities."""

    def __init__(self, world_model=None, dependency_graph=None, contradiction_report=None):
        self._world_model = world_model
        self._dep_graph = dependency_graph
        self._contradictions = contradiction_report

    def _ensure_models(self) -> None:
        if self._world_model is None:
            from substrate.organism.world_model import extract_world_model
            self._world_model = extract_world_model()
        if self._dep_graph is None:
            from substrate.organism.dependency_graph import build_dependency_graph
            self._dep_graph = build_dependency_graph(self._world_model)
        if self._contradictions is None:
            from substrate.organism.contradiction_engine import detect_contradictions
            self._contradictions = detect_contradictions(self._world_model, self._dep_graph)

    def compose(
        self,
        intent: CompositionIntent,
        constraints: list[CompositionConstraint] | None = None,
        custom_steps: list[dict[str, Any]] | None = None,
    ) -> CompositionPlan:
        self._ensure_models()

        category = _classify_intent(intent.description)
        intent.category = category
        pattern = custom_steps or _INTENT_PATTERNS.get(category, _INTENT_PATTERNS["general"])

        context = CompositionContext(
            active_contradictions=len(self._contradictions.contradictions),
        )

        plan = CompositionPlan(
            intent=intent,
            context=context,
            constraints=constraints or [],
        )

        prev_id: str | None = None
        max_risk = RiskClass.LOW
        max_gov = GovernanceMode.AUTONOMOUS

        for step_def in pattern:
            risk = _RISK_MAP.get(step_def["risk"], RiskClass.MEDIUM)
            gov = _GOV_MAP.get(step_def["gov"], GovernanceMode.ASSISTED)
            step = CompositionStep(
                description=step_def["desc"],
                action=step_def["action"],
                depends_on=[prev_id] if prev_id else [],
                risk_class=risk,
                governance_mode=gov,
                verification=step_def.get("verify", ""),
            )
            plan.steps.append(step)
            prev_id = step.id

            if list(RiskClass).index(risk) > list(RiskClass).index(max_risk):
                max_risk = risk
            if list(GovernanceMode).index(gov) > list(GovernanceMode).index(max_gov):
                max_gov = gov

        plan.overall_risk = max_risk
        plan.governance_required = max_gov

        if max_risk in (RiskClass.HIGH, RiskClass.CRITICAL):
            plan.risks.append(CompositionRisk(
                description=f"Plan contains {max_risk.value}-risk steps",
                risk_class=max_risk,
                mitigation="Operator review required before execution",
            ))
        if context.active_contradictions > 0:
            plan.risks.append(CompositionRisk(
                description=f"{context.active_contradictions} active contradictions may affect execution",
                risk_class=RiskClass.MEDIUM,
                mitigation="Resolve contradictions before proceeding",
            ))

        plan.validation_strategy = "Re-run verification step after each action"
        plan.rollback_plan = "Revert to pre-execution state if any step fails verification"
        plan.evidence.append(f"Composed from {len(self._world_model.entities)} entities")
        plan.evidence.append(f"Dependency graph: {len(self._dep_graph.edges)} edges")
        plan.evidence.append(f"Active contradictions: {context.active_contradictions}")

        return plan


def compose_plan(intent_description: str, **kwargs) -> CompositionPlan:
    """Convenience — compose a plan from a text description."""
    engine = CompositionEngine(**kwargs)
    intent = CompositionIntent(description=intent_description)
    return engine.compose(intent)


def persist_plan(plan: CompositionPlan, path: str | None = None) -> str:
    """Persist composition plan to JSONL."""
    if path is None:
        path = os.path.join(_REPO_ROOT, "data", "umh", "composition", "plans.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(plan.to_dict(), default=str) + "\n")
    return path


if __name__ == "__main__":
    import sys
    sys.path.insert(0, _REPO_ROOT)

    intents = [
        "fix deployment truth",
        "improve readiness",
        "wire missing panel",
        "run safe maintenance",
        "prepare autonomous low-risk execution",
    ]
    for desc in intents:
        plan = compose_plan(desc)
        print(f"\n{'='*60}")
        print(f"Intent: {desc}")
        print(f"Category: {plan.intent.category}")
        print(f"Steps: {len(plan.steps)}, Risk: {plan.overall_risk.value}, Gov: {plan.governance_required.value}")
        for step in plan.steps:
            print(f"  [{step.risk_class.value:6s}] {step.description}")
