"""Feedback → Primitive Learning Loop.

Converts execution results (PipelineResult) into primitive-level
feedback signals, then applies that feedback to produce improved
primitive compositions.

The loop:
    execute → evaluate_result → FeedbackSignal → apply_feedback → improved primitives

Every step is traceable to specific primitives.  No black boxes.

Usage:
    from core.feedback import evaluate_result, apply_feedback

    signal = evaluate_result(pipeline_result, context)
    improved = apply_feedback(current_primitives, signal)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.orchestrator.pipeline import PipelineResult, StepOutcome
from core.primitives import L0, PrimitiveTag
from core.transformer import TransformationResult, transform


# ---------------------------------------------------------------------------
# Feedback signal
# ---------------------------------------------------------------------------


@dataclass
class PrimitiveEffectiveness:
    """How effective a single primitive was in the execution."""

    tag: PrimitiveTag
    contribution_score: float  # 0.0 = no contribution, 1.0 = critical
    failure_contributor: bool  # did this primitive's area cause failure?
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tag": self.tag.value,
            "contribution_score": round(self.contribution_score, 3),
            "failure_contributor": self.failure_contributor,
            "notes": self.notes,
        }


@dataclass
class FeedbackSignal:
    """The output of evaluate_result — a primitive-level diagnosis.

    Maps execution outcomes back to the primitives that drove them,
    identifying what worked, what failed, and what was missing.
    """

    success_score: float  # 0.0 = total failure, 1.0 = perfect
    failure_points: list[PrimitiveEffectiveness]
    inefficiencies: list[PrimitiveEffectiveness]
    suggested_transformations: list[str]
    primitive_scores: dict[str, float]  # tag.value -> effectiveness 0-1
    missing_primitives: list[PrimitiveTag]  # primitives that should have been present
    raw_evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success_score": round(self.success_score, 3),
            "failure_points": [fp.to_dict() for fp in self.failure_points],
            "inefficiencies": [ie.to_dict() for ie in self.inefficiencies],
            "suggested_transformations": self.suggested_transformations,
            "primitive_scores": {
                k: round(v, 3) for k, v in self.primitive_scores.items()
            },
            "missing_primitives": [p.value for p in self.missing_primitives],
            "raw_evidence": self.raw_evidence,
        }


# ---------------------------------------------------------------------------
# Evaluation logic
# ---------------------------------------------------------------------------


# Maps action types/names to which primitives they exercise.
# When a step fails, the primitives it exercises are marked as failure contributors.
_STEP_PRIMITIVE_MAP: dict[str, set[PrimitiveTag]] = {
    "generate_outreach": {
        PrimitiveTag.STATE,
        PrimitiveTag.GOAL,
        PrimitiveTag.SIGNAL,
        PrimitiveTag.ACTION,
    },
    "compose_offer": {
        PrimitiveTag.GOAL,
        PrimitiveTag.ACTION,
        PrimitiveTag.OUTCOME,
        PrimitiveTag.RESOURCE,
    },
    "execute_workflow": {
        PrimitiveTag.ACTION,
        PrimitiveTag.STATE,
        PrimitiveTag.CHANGE,
        PrimitiveTag.GOAL,
    },
    "activate_channel": {
        PrimitiveTag.SIGNAL,
        PrimitiveTag.ACTION,
        PrimitiveTag.RESOURCE,
    },
    "track_kpi": {
        PrimitiveTag.OUTCOME,
        PrimitiveTag.FEEDBACK,
        PrimitiveTag.SIGNAL,
        PrimitiveTag.GOAL,
    },
    "assign_role": {
        PrimitiveTag.ACTION,
        PrimitiveTag.CONSTRAINT,
        PrimitiveTag.RESOURCE,
        PrimitiveTag.GOAL,
    },
    # LyfeOS steps
    "build_habit": {
        PrimitiveTag.ACTION,
        PrimitiveTag.STATE,
        PrimitiveTag.CHANGE,
        PrimitiveTag.TIME,
        PrimitiveTag.GOAL,
    },
    "assess_energy": {
        PrimitiveTag.STATE,
        PrimitiveTag.RESOURCE,
        PrimitiveTag.SIGNAL,
        PrimitiveTag.CONSTRAINT,
    },
    "set_focus": {
        PrimitiveTag.STATE,
        PrimitiveTag.ACTION,
        PrimitiveTag.GOAL,
        PrimitiveTag.TIME,
        PrimitiveTag.CONSTRAINT,
    },
    "assess_identity": {
        PrimitiveTag.STATE,
        PrimitiveTag.GOAL,
        PrimitiveTag.CHANGE,
        PrimitiveTag.FEEDBACK,
    },
    # CreatorOS steps
    "create_content": {
        PrimitiveTag.ACTION,
        PrimitiveTag.GOAL,
        PrimitiveTag.RESOURCE,
        PrimitiveTag.SIGNAL,
        PrimitiveTag.OUTCOME,
    },
    "analyse_audience": {
        PrimitiveTag.STATE,
        PrimitiveTag.SIGNAL,
        PrimitiveTag.GOAL,
        PrimitiveTag.CONSTRAINT,
        PrimitiveTag.FEEDBACK,
    },
    "evaluate_platform": {
        PrimitiveTag.RESOURCE,
        PrimitiveTag.CONSTRAINT,
        PrimitiveTag.SIGNAL,
        PrimitiveTag.ACTION,
    },
    "measure_engagement": {
        PrimitiveTag.OUTCOME,
        PrimitiveTag.FEEDBACK,
        PrimitiveTag.SIGNAL,
        PrimitiveTag.STATE,
        PrimitiveTag.CHANGE,
    },
}


def _get_step_primitives(step: StepOutcome) -> set[PrimitiveTag]:
    """Determine which primitives a step exercises based on its name."""
    for key, tags in _STEP_PRIMITIVE_MAP.items():
        if key in step.name:
            return tags
    # Fallback: if the step result contains primitive_tags, use those
    result_tags = step.result.get("primitive_tags", [])
    if result_tags:
        found = set()
        for tv in result_tags:
            try:
                found.add(PrimitiveTag(tv))
            except ValueError:
                pass
        return found
    return {PrimitiveTag.ACTION}  # minimum assumption


def _compute_step_score(step: StepOutcome) -> float:
    """Score a single step outcome (0.0–1.0)."""
    status_scores = {
        "ok": 1.0,
        "deferred": 0.6,  # not failed, but not complete
        "skipped": 0.3,  # downstream casualty
        "rejected": 0.1,  # actively rejected
        "failed": 0.0,
    }
    return status_scores.get(step.status, 0.0)


def evaluate_result(
    result: PipelineResult,
    context: dict[str, Any] | None = None,
) -> FeedbackSignal:
    """Convert a PipelineResult into a primitive-level FeedbackSignal.

    Analyses each step's outcome and maps it back to the primitives
    that step exercises.  The result is a diagnosis at the primitive level.
    """
    context = context or {}
    primitive_tags_raw: list[str] = context.get("_primitive_tags", [])

    # Reconstruct the primitive set from context
    active_primitives: set[PrimitiveTag] = set()
    for tv in primitive_tags_raw:
        try:
            active_primitives.add(PrimitiveTag(tv))
        except ValueError:
            pass

    # Score each step and map to primitives
    step_scores: dict[str, float] = {}
    primitive_hit_count: dict[PrimitiveTag, int] = {}
    primitive_success_sum: dict[PrimitiveTag, float] = {}
    failure_points: list[PrimitiveEffectiveness] = []
    inefficiencies: list[PrimitiveEffectiveness] = []

    for step in result.steps:
        score = _compute_step_score(step)
        step_scores[step.name] = score
        step_prims = _get_step_primitives(step)

        for prim in step_prims:
            primitive_hit_count[prim] = primitive_hit_count.get(prim, 0) + 1
            primitive_success_sum[prim] = primitive_success_sum.get(prim, 0.0) + score

        # Identify failure contributors
        if score < 0.5:
            for prim in step_prims:
                failure_points.append(
                    PrimitiveEffectiveness(
                        tag=prim,
                        contribution_score=score,
                        failure_contributor=True,
                        notes=f"step '{step.name}' {step.status} — "
                        f"primitive {prim.value} in failure path",
                    )
                )

    # Calculate per-primitive effectiveness scores
    primitive_scores: dict[str, float] = {}
    for prim in PrimitiveTag:
        hits = primitive_hit_count.get(prim, 0)
        if hits > 0:
            primitive_scores[prim.value] = primitive_success_sum[prim] / hits
        elif prim in active_primitives:
            # Present in composition but never exercised — inefficiency
            primitive_scores[prim.value] = 0.5  # neutral
            inefficiencies.append(
                PrimitiveEffectiveness(
                    tag=prim,
                    contribution_score=0.5,
                    failure_contributor=False,
                    notes=f"primitive {prim.value} declared but never exercised by any step",
                )
            )

    # Detect missing primitives that should have been present
    missing: list[PrimitiveTag] = []
    suggested_transforms: list[str] = []

    # If we have ACTION + GOAL but no OUTCOME, we can't measure success
    if (
        PrimitiveTag.ACTION in active_primitives
        and PrimitiveTag.GOAL in active_primitives
        and PrimitiveTag.OUTCOME not in active_primitives
    ):
        missing.append(PrimitiveTag.OUTCOME)
        suggested_transforms.append(
            "add OUTCOME primitive — acting toward a goal without measuring results"
        )

    # If we have OUTCOME but no FEEDBACK, results aren't looped back
    if (
        PrimitiveTag.OUTCOME in active_primitives
        and PrimitiveTag.FEEDBACK not in active_primitives
    ):
        missing.append(PrimitiveTag.FEEDBACK)
        suggested_transforms.append(
            "add FEEDBACK primitive — outcomes exist but aren't being evaluated"
        )

    # If overall score is low, suggest broader transformation
    overall_score = sum(step_scores.values()) / len(step_scores) if step_scores else 0.0

    if overall_score < 0.5:
        # Check relationship closure
        for prim in active_primitives:
            defn = L0[prim]
            for rel in defn.relationships:
                try:
                    rel_tag = PrimitiveTag(rel)
                    if rel_tag not in active_primitives:
                        missing.append(rel_tag)
                        suggested_transforms.append(
                            f"add {rel} — required by {prim.value}'s relationships "
                            f"for structural completeness"
                        )
                except ValueError:
                    pass

    return FeedbackSignal(
        success_score=overall_score,
        failure_points=failure_points,
        inefficiencies=inefficiencies,
        suggested_transformations=suggested_transforms,
        primitive_scores=primitive_scores,
        missing_primitives=list(dict.fromkeys(missing)),  # dedupe preserving order
        raw_evidence={
            "step_scores": step_scores,
            "pipeline_ok": result.ok,
            "pipeline_name": result.name,
            "duration_s": round(result.finished_at - result.started_at, 4),
            "active_primitives": sorted(t.value for t in active_primitives),
        },
    )


# ---------------------------------------------------------------------------
# Feedback application
# ---------------------------------------------------------------------------


def apply_feedback(
    primitives: set[PrimitiveTag],
    feedback: FeedbackSignal,
    objective: str = "",
) -> tuple[set[PrimitiveTag], TransformationResult]:
    """Apply a feedback signal to produce an improved primitive set.

    Uses the transformer engine with constraints derived from the feedback.
    Returns both the improved set and the full transformation trace.
    """
    # Build constraints from feedback
    constraints: dict[str, Any] = {}

    # Force-include missing primitives
    for missing in feedback.missing_primitives:
        constraints[f"must_include_{missing.value}"] = True

    # If specific primitives failed, note them for the transformer
    failed_prims = {fp.tag.value for fp in feedback.failure_points}
    if failed_prims:
        constraints["failure_primitives"] = sorted(failed_prims)

    # Pass feedback score as context
    constraints["success_score"] = feedback.success_score

    result = transform(
        primitives=primitives,
        objective=objective or "improve based on execution feedback",
        constraints=constraints,
    )

    return set(result.transformed_primitives), result


__all__ = [
    "FeedbackSignal",
    "PrimitiveEffectiveness",
    "evaluate_result",
    "apply_feedback",
]
