"""UMH Execution Planning — models for objective-to-task planning.

Converts structured user objectives into validated, deterministic plans
that execute through the existing Task system. Separate from the
goal-level hierarchical planning layer.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum

from umh.core.clock import iso_now as _iso_now


class PlanStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class PlanSource(str, Enum):
    TEMPLATE = "template"
    LLM = "llm"
    MANUAL = "manual"


@dataclass
class PlanObjective:
    title: str
    description: str = ""
    constraints: list[str] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    requested_by: str = ""
    max_steps: int = 10
    allowed_capabilities: list[str] = field(default_factory=list)
    dry_run: bool = False
    objective_id: str = ""
    raw_input: str = ""
    intent_category: str = ""
    inferred_constraints: dict = field(default_factory=dict)
    uncertainty: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.objective_id:
            self.objective_id = f"obj_{uuid.uuid4().hex[:12]}"

    def to_dict(self) -> dict:
        d = {
            "objective_id": self.objective_id,
            "title": self.title,
            "description": self.description,
            "constraints": self.constraints,
            "context": self.context,
            "requested_by": self.requested_by,
            "max_steps": self.max_steps,
            "allowed_capabilities": self.allowed_capabilities,
            "dry_run": self.dry_run,
        }
        if self.raw_input:
            d["raw_input"] = self.raw_input
        if self.intent_category:
            d["intent_category"] = self.intent_category
        if self.inferred_constraints:
            d["inferred_constraints"] = self.inferred_constraints
        if self.uncertainty:
            d["uncertainty"] = list(self.uncertainty)
        if self.assumptions:
            d["assumptions_obj"] = list(self.assumptions)
        return d


@dataclass
class ExecutionPlanStep:
    name: str
    operation: str
    inputs: dict = field(default_factory=dict)
    execution_class: str = "llm_call"
    constraints: dict = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    rationale: str = ""
    step_id: str = ""

    def __post_init__(self):
        if not self.step_id:
            self.step_id = f"pstep_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "name": self.name,
            "operation": self.operation,
            "inputs": self.inputs,
            "execution_class": self.execution_class,
            "constraints": self.constraints,
            "depends_on": self.depends_on,
            "rationale": self.rationale,
        }


@dataclass
class ExecutionPlan:
    objective: PlanObjective
    steps: list[ExecutionPlanStep] = field(default_factory=list)
    source: PlanSource = PlanSource.TEMPLATE
    confidence: float = 1.0
    assumptions: list[str] = field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    plan_id: str = ""
    created_at: str = ""
    task_id: str = ""
    validation_errors: list[str] = field(default_factory=list)
    quality_score: dict | None = None
    explanation: dict | None = None
    review: dict | None = None
    debug_analysis: dict | None = None
    decision_trace: list[dict] = field(default_factory=list)

    def __post_init__(self):
        if not self.plan_id:
            self.plan_id = f"eplan_{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = _iso_now()

    def to_dict(self) -> dict:
        d = {
            "plan_id": self.plan_id,
            "objective": self.objective.to_dict(),
            "steps": [s.to_dict() for s in self.steps],
            "source": self.source.value,
            "confidence": self.confidence,
            "assumptions": self.assumptions,
            "status": self.status.value,
            "created_at": self.created_at,
            "task_id": self.task_id,
            "validation_errors": self.validation_errors,
        }
        if self.quality_score is not None:
            d["quality"] = self.quality_score
        if self.explanation is not None:
            d["explanation"] = self.explanation
        if self.review is not None:
            d["review"] = self.review
        if self.debug_analysis is not None:
            d["debug_analysis"] = self.debug_analysis
        if self.decision_trace:
            d["decision_trace"] = self.decision_trace
        return d


@dataclass
class PlanValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }
