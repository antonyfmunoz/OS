"""
Plan mutation — deterministic strategy generation from failed plans.

When a plan variant has failed repeatedly (failure_count >= MUTATION_THRESHOLD,
success_count == 0), the system generates new plan variants by applying
deterministic transformations to the original plan's step sequence.

This is NOT machine learning.  This is structured search in strategy space:
same inputs always produce the same mutations.

Two-tier mutation strategy:

Tier 1 — Causal transforms (when failure context available):
    Applied when the plan memory contains failure_step_index and
    failure_type from the last execution.  These transforms target
    the specific step that failed:
        0. remove_failing   — remove the step at failure index
        1. retry_earlier    — move failing step to position 0
        2. duplicate_failing — insert duplicate at failure index
        3. truncate_before  — keep only steps before failure index

Tier 2 — Structural transforms (fallback, no failure context):
    Applied when no failure context is available (backward compat,
    first-time failures, or non-step failures):
        0. reverse — reverse step order
        1. rotate  — move first step to the end
        2. drop_last — remove the final step (if >1 step)
        3. duplicate_first — repeat the first step at the start

Which transform to apply is selected via:
    Tier 1: hash(intent_type + goal_hash + mutation_index
                 + failure_type + failed_step_index) % len(causal_transforms)
    Tier 2: hash(intent_type + goal_hash + mutation_index) % len(structural_transforms)

Safety:
    MAX_MUTATIONS_PER_PLAN = 2  — prevents infinite variant explosion.

Design constraints:
- Pure functions: no side effects, no hidden state.
- Deterministic: same inputs always produce same outputs.
- Replay-safe: replaying the event log produces identical mutations.
- Read-only checks: mutation eligibility is determined from state,
  never mutates state during checks.
- Bounded: at most MAX_MUTATIONS_PER_PLAN mutations per parent variant.

Usage:
    from umh.substrate.plan_mutation import (
        should_mutate,
        mutate_plan_steps,
        build_mutated_variant_id,
        count_existing_mutations,
        MAX_MUTATIONS_PER_PLAN,
        MUTATION_THRESHOLD,
    )
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, TypedDict

from umh.substrate.intent_models import PlanStep


# ─── Failure context ──────────────────────────────────────────────


class FailureContext(TypedDict, total=False):
    """Failure signal extracted from execution result + plan memory.

    Both fields must be present for causal mutation to activate.
    Derived from existing events — no new scans required.
    """

    failed_step_index: int
    failure_type: str  # execution_failed | timed_out | rejected | driver_failure


# ─── Constants ──────────────────────────────────────────────────────

# Minimum failure count (with zero successes) before mutation triggers.
MUTATION_THRESHOLD: int = 3

# Maximum number of mutated variants derived from a single parent.
MAX_MUTATIONS_PER_PLAN: int = 2


# ─── Mutation trigger ──────────────────────────────────────────────


def should_mutate(memory: dict[str, Any] | None) -> bool:
    """Check if a plan's memory record qualifies it for mutation.

    Mutation triggers when:
        failure_count >= MUTATION_THRESHOLD AND success_count == 0

    This is the same condition as intent memory blocking — the plan
    has failed enough times with no success to justify trying a
    structural alternative.

    Returns False for None memory (untried plans).
    Pure function.  No side effects.
    """
    if memory is None:
        return False

    failure_count = memory.get("failure_count", 0)
    success_count = memory.get("success_count", 0)

    return failure_count >= MUTATION_THRESHOLD and success_count == 0


# ─── Variant ID helpers ────────────────────────────────────────────


def build_mutated_variant_id(
    parent_variant_id: str,
    mutation_index: int,
    failure_context: FailureContext | None = None,
) -> str:
    """Build a deterministic variant_id for a mutated plan.

    Format without failure context:
        {parent_variant_id}::mut_{n}

    Format with failure context:
        {parent_variant_id}::mut_{n}::f{step}_{type}

    The failure suffix enables traceability — you can see in the
    variant_id exactly which step and failure type drove the mutation.

    The parent_variant_id is the variant that was mutated.
    mutation_index is 0-based (0 = first mutation, 1 = second).
    """
    base = f"{parent_variant_id}::mut_{mutation_index}"
    if _has_valid_failure_context(failure_context):
        assert failure_context is not None
        step = failure_context["failed_step_index"]
        ftype = failure_context["failure_type"]
        return f"{base}::f{step}_{ftype}"
    return base


def is_mutated_variant(variant_id: str) -> bool:
    """Check if a variant_id represents a mutated plan."""
    return "::mut_" in variant_id


def get_parent_variant_id(variant_id: str) -> str:
    """Extract the parent variant_id from a mutated variant_id.

    Handles both formats:
        v_fast::mut_0           → v_fast
        v_fast::mut_0::f2_execution_failed → v_fast

    Returns the original variant_id if not a mutation.
    """
    if "::mut_" in variant_id:
        return variant_id.split("::mut_")[0]
    return variant_id


def extract_failure_context_from_memory(
    plan_memory: dict[str, Any] | None,
) -> FailureContext | None:
    """Extract failure context from a plan memory record.

    Returns a FailureContext if the record contains both
    last_failure_step_index and last_failure_type with valid values.
    Returns None otherwise (backward compat, no failure recorded).

    Pure function.  No side effects.
    """
    if plan_memory is None:
        return None

    step_idx = plan_memory.get("last_failure_step_index")
    ftype = plan_memory.get("last_failure_type", "")

    if step_idx is None or not isinstance(step_idx, int):
        return None
    if not ftype:
        return None

    return FailureContext(
        failed_step_index=step_idx,
        failure_type=ftype,
    )


def count_existing_mutations(variant_ids: list[str], parent_variant_id: str) -> int:
    """Count how many mutations already exist for a parent variant.

    Scans the variant_ids list (not the state store — this is O(n_variants),
    not a state scan) for IDs matching the pattern:
        {parent_variant_id}::mut_{n}

    Pure function.  No side effects.
    """
    prefix = f"{parent_variant_id}::mut_"
    return sum(1 for vid in variant_ids if vid.startswith(prefix))


# ─── Mutation transforms ───────────────────────────────────────────

# Each transform is a pure function: tuple[PlanStep, ...] → tuple[PlanStep, ...]
# All transforms must be deterministic and produce valid step sequences.


def _reindex_steps(steps: tuple[PlanStep, ...]) -> tuple[PlanStep, ...]:
    """Re-assign step_index values to match position in tuple."""
    return tuple(
        PlanStep(
            step_index=i,
            event_type=s.event_type,
            payload=s.payload,
            description=s.description,
        )
        for i, s in enumerate(steps)
    )


def _transform_reverse(steps: tuple[PlanStep, ...]) -> tuple[PlanStep, ...]:
    """Reverse step order.  Deterministic."""
    if len(steps) <= 1:
        return steps
    return _reindex_steps(tuple(reversed(steps)))


def _transform_rotate(steps: tuple[PlanStep, ...]) -> tuple[PlanStep, ...]:
    """Move first step to the end.  Deterministic."""
    if len(steps) <= 1:
        return steps
    return _reindex_steps(steps[1:] + steps[:1])


def _transform_drop_last(steps: tuple[PlanStep, ...]) -> tuple[PlanStep, ...]:
    """Remove the final step.  Only if >1 step remains.  Deterministic."""
    if len(steps) <= 1:
        return steps  # Cannot drop the only step
    return _reindex_steps(steps[:-1])


def _transform_duplicate_first(steps: tuple[PlanStep, ...]) -> tuple[PlanStep, ...]:
    """Duplicate the first step at position 0.  Deterministic."""
    if not steps:
        return steps
    return _reindex_steps(steps[:1] + steps)


# Ordered list of structural mutation transforms (Tier 2 — fallback).
# The index into this list is determined by hash, not by randomness.
_STRUCTURAL_TRANSFORMS = [
    _transform_reverse,
    _transform_rotate,
    _transform_drop_last,
    _transform_duplicate_first,
]

# Back-compat alias used nowhere externally but kept for safety.
_MUTATION_TRANSFORMS = _STRUCTURAL_TRANSFORMS


# ─── Causal mutation transforms (Tier 1) ──────────────────────────

# These transforms target the specific step that failed.
# Each takes (steps, failed_step_index) and returns a new step tuple.


def _causal_remove_failing(steps: tuple[PlanStep, ...], k: int) -> tuple[PlanStep, ...]:
    """Remove the step at failure index k.  Deterministic.

    If k is out of range or removing would leave zero steps,
    returns steps unchanged (safe fallback).
    """
    if k < 0 or k >= len(steps) or len(steps) <= 1:
        return steps
    return _reindex_steps(steps[:k] + steps[k + 1 :])


def _causal_retry_earlier(steps: tuple[PlanStep, ...], k: int) -> tuple[PlanStep, ...]:
    """Move the failing step at index k to position 0.  Deterministic.

    If k is 0 or out of range, returns steps unchanged.
    """
    if k <= 0 or k >= len(steps):
        return steps
    moved = (steps[k],) + steps[:k] + steps[k + 1 :]
    return _reindex_steps(moved)


def _causal_duplicate_failing(
    steps: tuple[PlanStep, ...], k: int
) -> tuple[PlanStep, ...]:
    """Insert a duplicate of step k at position k.  Deterministic.

    If k is out of range, returns steps unchanged.
    """
    if k < 0 or k >= len(steps):
        return steps
    return _reindex_steps(steps[:k] + (steps[k],) + steps[k:])


def _causal_truncate_before(
    steps: tuple[PlanStep, ...], k: int
) -> tuple[PlanStep, ...]:
    """Keep only steps before failure index k.  Deterministic.

    If k <= 0 or k >= len(steps), returns steps unchanged.
    k == 0 would produce empty → not allowed.
    """
    if k <= 0 or k >= len(steps):
        return steps
    return _reindex_steps(steps[:k])


# Ordered list of causal mutation transforms (Tier 1).
_CAUSAL_TRANSFORMS = [
    _causal_remove_failing,
    _causal_retry_earlier,
    _causal_duplicate_failing,
    _causal_truncate_before,
]


# ─── Mutation selection ────────────────────────────────────────────


def _select_structural_transform_index(
    intent_type: str,
    goal: dict[str, Any],
    mutation_index: int,
) -> int:
    """Deterministically select which structural transform to apply.

    Uses hash(intent_type + goal_hash + mutation_index) to pick
    a transform index.  Same inputs always select the same transform.

    Pure function.  No randomness.
    """
    goal_canonical = json.dumps(
        goal, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    seed = f"{intent_type}:{goal_canonical}:{mutation_index}"
    h = hashlib.sha256(seed.encode()).hexdigest()
    return int(h[:8], 16) % len(_STRUCTURAL_TRANSFORMS)


# Back-compat alias.
_select_transform_index = _select_structural_transform_index


def _select_causal_transform_index(
    intent_type: str,
    goal: dict[str, Any],
    mutation_index: int,
    failure_type: str,
    failed_step_index: int,
) -> int:
    """Deterministically select which causal transform to apply.

    Uses hash(intent_type + goal_hash + mutation_index + failure_type
    + failed_step_index) to pick a transform index.

    The inclusion of failure_type and failed_step_index means:
    - Different failures → different mutations.
    - Same failure → same mutation.

    Pure function.  No randomness.
    """
    goal_canonical = json.dumps(
        goal, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    seed = (
        f"{intent_type}:{goal_canonical}:{mutation_index}"
        f"::{failure_type}:{failed_step_index}"
    )
    h = hashlib.sha256(seed.encode()).hexdigest()
    return int(h[:8], 16) % len(_CAUSAL_TRANSFORMS)


def _has_valid_failure_context(failure_context: FailureContext | None) -> bool:
    """Check if failure context has both required fields with valid values.

    Pure function.  No side effects.
    """
    if failure_context is None:
        return False
    if "failed_step_index" not in failure_context:
        return False
    if "failure_type" not in failure_context:
        return False
    if not isinstance(failure_context["failed_step_index"], int):
        return False
    if not failure_context["failure_type"]:
        return False
    return True


# ─── Core mutation function ────────────────────────────────────────


def mutate_plan_steps(
    original_steps: tuple[PlanStep, ...],
    intent_type: str,
    goal: dict[str, Any],
    mutation_index: int,
    failure_context: FailureContext | None = None,
) -> tuple[PlanStep, ...]:
    """Apply a deterministic mutation to plan steps.

    Two-tier strategy:
    - Tier 1 (causal): if failure_context has valid failed_step_index
      and failure_type, use causal transforms that target the failing step.
    - Tier 2 (structural): fallback when no failure context is available.

    The mutation transform is selected based on:
        Tier 1: hash(intent_type + goal + mutation_index
                     + failure_type + failed_step_index)
        Tier 2: hash(intent_type + goal + mutation_index)

    This ensures:
    - Same original steps + same intent context → same mutation.
    - Same failure context → same causal mutation.
    - Different failure_type or step → different mutation.
    - Different mutation_index values explore different transforms.
    - No randomness.  Fully replay-safe.

    Args:
        original_steps: The parent plan's step sequence.
        intent_type: The intent type string.
        goal: The intent goal dict.
        mutation_index: 0-based index of this mutation (0 = first, 1 = second).
        failure_context: Optional failure signal from last execution.
            If present with valid fields, causal transforms are used.
            If None or incomplete, structural transforms are used.

    Returns:
        A new tuple of PlanSteps with the mutation applied.
        If the transform is a no-op (e.g., single-step plan + reverse),
        returns a copy of the original steps (still valid for registration).
    """
    if not original_steps:
        return original_steps

    # Tier 1: causal transforms (failure-aware)
    if _has_valid_failure_context(failure_context):
        assert failure_context is not None  # for type checker
        failed_step = failure_context["failed_step_index"]
        failure_type = failure_context["failure_type"]
        transform_idx = _select_causal_transform_index(
            intent_type, goal, mutation_index, failure_type, failed_step
        )
        transform = _CAUSAL_TRANSFORMS[transform_idx]
        return transform(original_steps, failed_step)

    # Tier 2: structural transforms (fallback)
    transform_idx = _select_structural_transform_index(
        intent_type, goal, mutation_index
    )
    transform = _STRUCTURAL_TRANSFORMS[transform_idx]
    return transform(original_steps)
