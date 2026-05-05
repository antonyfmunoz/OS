"""UMH Plan Quality Scoring — usefulness/readiness gate for execution plans.

Quality scoring is orthogonal to validation:
- Validation = hard correctness gate (is the plan structurally valid?)
- Quality = usefulness gate (is this plan worth executing?)

A plan can be valid but low-quality (vague objective, unnecessary steps).
Quality blocks execution at the API layer, not the validator layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from umh.planning.models import (
    ExecutionPlan,
    PlanObjective,
    PlanSource,
    PlanValidationResult,
)
from umh.planning.validator import (
    _APPROVAL_GATED_OPS,
    _KNOWN_OPERATIONS,
    _SHELL_ALLOWLIST,
    _UNSUPPORTED_OPS,
)


class QualityVerdict:
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class PlanQualityScore:
    score: float = 0.0
    verdict: str = QualityVerdict.FAIL
    reasons: list[str] = field(default_factory=list)
    dimensions: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 3),
            "verdict": self.verdict,
            "reasons": self.reasons,
            "dimensions": {k: round(v, 3) for k, v in self.dimensions.items()},
        }


def score_plan(
    plan: ExecutionPlan,
    validation: PlanValidationResult | None = None,
) -> PlanQualityScore:
    """Score a plan's quality across multiple dimensions.

    Pure function — no I/O, no LLM, no execution.
    """
    reasons: list[str] = []
    dims: dict[str, float] = {
        "completeness": 0.0,
        "safety": 0.0,
        "specificity": 0.0,
        "executability": 0.0,
        "minimality": 0.0,
        "constraint_alignment": 0.0,
    }

    if not plan.steps:
        return PlanQualityScore(
            score=0.0,
            verdict=QualityVerdict.FAIL,
            reasons=["Plan has no steps"],
            dimensions=dims,
        )

    if validation and not validation.valid:
        reasons.append("Plan failed validation")
        return PlanQualityScore(
            score=0.0,
            verdict=QualityVerdict.FAIL,
            reasons=reasons + validation.errors,
            dimensions=dims,
        )

    dims["completeness"] = _score_completeness(plan, reasons)
    dims["safety"] = _score_safety(plan, reasons)
    dims["specificity"] = _score_specificity(plan, reasons)
    dims["executability"] = _score_executability(plan, validation, reasons)
    dims["minimality"] = _score_minimality(plan, reasons)
    dims["constraint_alignment"] = _score_constraint_alignment(plan, reasons)

    total = sum(dims.values()) / len(dims)

    if total >= 0.7:
        verdict = QualityVerdict.PASS
    elif total >= 0.4:
        verdict = QualityVerdict.WARN
    else:
        verdict = QualityVerdict.FAIL

    has_fail_reason = any(r.startswith("[FAIL]") for r in reasons)
    if has_fail_reason:
        verdict = QualityVerdict.FAIL

    return PlanQualityScore(
        score=total,
        verdict=verdict,
        reasons=reasons,
        dimensions=dims,
    )


def _score_completeness(plan: ExecutionPlan, reasons: list[str]) -> float:
    """Does the plan have enough information to achieve its objective?"""
    obj = plan.objective
    score = 0.5

    if obj.title and obj.title.strip():
        score += 0.2
    else:
        reasons.append("[FAIL] Objective has no title")
        return 0.0

    if obj.description and obj.description.strip():
        score += 0.15

    if plan.steps:
        score += 0.15

    return min(score, 1.0)


def _score_safety(plan: ExecutionPlan, reasons: list[str]) -> float:
    """Are all operations safe and properly gated?"""
    score = 1.0

    for step in plan.steps:
        if step.operation in _UNSUPPORTED_OPS:
            reasons.append(
                f"[FAIL] Step '{step.name}' uses unsupported operation '{step.operation}'"
            )
            return 0.0

        if step.operation not in _KNOWN_OPERATIONS:
            reasons.append(f"[FAIL] Step '{step.name}' uses unknown operation '{step.operation}'")
            return 0.0

        if step.operation in _APPROVAL_GATED_OPS:
            if step.execution_class == "side_effect":
                reasons.append(
                    f"Step '{step.name}' is approval-gated ('{step.operation}') — risk acknowledged"
                )
                score = min(score, 0.7)
            else:
                reasons.append(
                    f"[FAIL] Approval-gated '{step.operation}' missing side_effect class"
                )
                return 0.0

        if step.operation == "shell_command":
            cmd = step.inputs.get("command", "")
            if cmd not in _SHELL_ALLOWLIST:
                reasons.append(f"[FAIL] Shell command '{cmd}' not in allowlist")
                return 0.0

    return score


def _score_specificity(plan: ExecutionPlan, reasons: list[str]) -> float:
    """Is the objective specific enough to produce a useful plan?"""
    obj = plan.objective
    score = 0.5

    if obj.description and len(obj.description) > 10:
        score += 0.2

    has_context = bool(obj.context)
    if has_context:
        score += 0.2

    uncertainty = getattr(obj, "uncertainty", ())
    if uncertainty:
        penalty = min(len(uncertainty) * 0.15, 0.4)
        score -= penalty
        for u in uncertainty:
            reasons.append(f"Uncertainty: {u}")

    if not obj.title or len(obj.title.strip()) < 3:
        reasons.append("Objective title too short or vague")
        score -= 0.3

    return max(score, 0.0)


def _score_executability(
    plan: ExecutionPlan,
    validation: PlanValidationResult | None,
    reasons: list[str],
) -> float:
    """Can this plan actually execute successfully?"""
    score = 0.8

    if validation and validation.warnings:
        score -= min(len(validation.warnings) * 0.1, 0.3)
        for w in validation.warnings:
            reasons.append(f"Validation warning: {w}")

    for step in plan.steps:
        if not isinstance(step.inputs, dict):
            reasons.append(f"[FAIL] Step '{step.name}' has non-dict inputs")
            return 0.0

        if step.operation == "file_read" and not step.inputs.get("path"):
            reasons.append(f"Step '{step.name}' missing required 'path' input")
            score -= 0.3

        if step.operation == "file_list" and not step.inputs.get("path"):
            reasons.append(f"Step '{step.name}' missing required 'path' input")
            score -= 0.2

        if step.operation == "shell_command" and not step.inputs.get("command"):
            reasons.append(f"[FAIL] Step '{step.name}' has empty shell command")
            return 0.0

        if step.operation == "summarize" and not step.inputs.get("prompt"):
            reasons.append(f"Step '{step.name}' missing 'prompt' input for summarize")
            score -= 0.2

    if plan.source == PlanSource.LLM:
        score -= 0.1
        reasons.append("LLM-generated plan — lower confidence")

    return max(score, 0.0)


def _score_minimality(plan: ExecutionPlan, reasons: list[str]) -> float:
    """Is the plan as small as it needs to be?"""
    step_count = len(plan.steps)

    if step_count == 0:
        return 0.0

    if step_count <= 3:
        return 1.0

    if step_count <= 5:
        return 0.8

    if step_count <= 8:
        reasons.append(f"Plan has {step_count} steps — consider reducing")
        return 0.6

    reasons.append(f"Plan has {step_count} steps — excessive")
    return 0.3


def _score_constraint_alignment(plan: ExecutionPlan, reasons: list[str]) -> float:
    """Does the plan respect its objective constraints?"""
    obj = plan.objective
    score = 1.0

    if obj.allowed_capabilities:
        for step in plan.steps:
            if step.operation not in obj.allowed_capabilities:
                reasons.append(
                    f"[FAIL] Step '{step.name}' operation '{step.operation}' "
                    f"not in allowed_capabilities"
                )
                return 0.0

    if len(plan.steps) > obj.max_steps:
        reasons.append(f"Plan has {len(plan.steps)} steps, objective max is {obj.max_steps}")
        score -= 0.3

    return max(score, 0.0)
