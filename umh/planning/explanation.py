"""UMH Plan Explainability — structured explanation of plan decisions.

Pure projection: takes existing plan, validation, and quality data and
produces a structured summary for API consumers. No new computation,
just reshaping for human consumption.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from umh.planning.models import (
    ExecutionPlan,
    PlanValidationResult,
)
from umh.planning.quality import PlanQualityScore
from umh.planning.validator import _APPROVAL_GATED_OPS


@dataclass
class PlanExplanation:
    objective_summary: str = ""
    steps_summary: list[dict] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    approval_requirements: list[str] = field(default_factory=list)
    plan_selection_reason: str = ""
    safety_assessment: str = ""
    quality_summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "objective_summary": self.objective_summary,
            "steps_summary": self.steps_summary,
            "assumptions": self.assumptions,
            "risks": self.risks,
            "approval_requirements": self.approval_requirements,
            "plan_selection_reason": self.plan_selection_reason,
            "safety_assessment": self.safety_assessment,
            "quality_summary": self.quality_summary,
        }


def explain_plan(
    plan: ExecutionPlan,
    validation: PlanValidationResult | None = None,
    quality: PlanQualityScore | None = None,
) -> PlanExplanation:
    """Generate a structured explanation for a plan.

    Pure function — no I/O, no LLM, no execution.
    """
    obj = plan.objective

    objective_summary = f"{obj.title}"
    if obj.description and obj.description != obj.title:
        objective_summary += f": {obj.description}"

    steps_summary = []
    for i, step in enumerate(plan.steps):
        steps_summary.append(
            {
                "index": i,
                "name": step.name,
                "operation": step.operation,
                "execution_class": step.execution_class,
                "rationale": step.rationale,
            }
        )

    assumptions = list(plan.assumptions)
    obj_assumptions = getattr(obj, "assumptions", ())
    for a in obj_assumptions:
        if a not in assumptions:
            assumptions.append(a)

    risks: list[str] = []
    approval_requirements: list[str] = []

    for step in plan.steps:
        if step.operation in _APPROVAL_GATED_OPS:
            approval_requirements.append(
                f"Step '{step.name}' ({step.operation}) requires approval before execution"
            )
            risks.append(f"Computer action '{step.operation}' in step '{step.name}'")

        if step.operation == "shell_command":
            cmd = step.inputs.get("command", "")
            risks.append(f"Shell command execution: '{cmd}'")

    if validation and not validation.valid:
        for err in validation.errors:
            risks.append(f"Validation error: {err}")

    if validation and validation.warnings:
        for w in validation.warnings:
            risks.append(f"Validation warning: {w}")

    obj_uncertainty = getattr(obj, "uncertainty", ())
    for u in obj_uncertainty:
        risks.append(f"Uncertainty: {u}")

    plan_selection_reason = _derive_selection_reason(plan)

    safety_assessment = _derive_safety_assessment(plan, validation, quality)

    quality_summary = {}
    if quality:
        quality_summary = {
            "score": round(quality.score, 3),
            "verdict": quality.verdict,
            "dimensions": {k: round(v, 3) for k, v in quality.dimensions.items()},
        }

    return PlanExplanation(
        objective_summary=objective_summary,
        steps_summary=steps_summary,
        assumptions=assumptions,
        risks=risks,
        approval_requirements=approval_requirements,
        plan_selection_reason=plan_selection_reason,
        safety_assessment=safety_assessment,
        quality_summary=quality_summary,
    )


def _derive_selection_reason(plan: ExecutionPlan) -> str:
    """Explain why this plan was selected."""
    source = plan.source.value

    if source == "template":
        return (
            f"Deterministic template selected — "
            f"confidence {plan.confidence}, {len(plan.steps)} steps"
        )
    elif source == "llm":
        return (
            f"LLM-generated plan — treated as untrusted, "
            f"confidence {plan.confidence}, {len(plan.steps)} steps"
        )
    else:
        return f"Manual plan — {len(plan.steps)} steps"


def _derive_safety_assessment(
    plan: ExecutionPlan,
    validation: PlanValidationResult | None,
    quality: PlanQualityScore | None,
) -> str:
    """Produce a safety assessment string."""
    if validation and not validation.valid:
        return "UNSAFE — plan failed validation"

    if quality and quality.verdict == "fail":
        return "UNSAFE — plan failed quality scoring"

    has_approval_gated = any(s.operation in _APPROVAL_GATED_OPS for s in plan.steps)
    has_shell = any(s.operation == "shell_command" for s in plan.steps)

    if has_approval_gated and has_shell:
        return "CONDITIONAL — contains approval-gated operations and shell commands"
    elif has_approval_gated:
        return "CONDITIONAL — contains approval-gated operations"
    elif has_shell:
        return "SAFE — shell commands are allowlisted"
    else:
        return "SAFE — all operations are deterministic and allowlisted"
