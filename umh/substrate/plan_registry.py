"""
Plan registry — deterministic mapping from IntentType to plan derivation.

Supports multiple plan variants per intent_type.  When multiple variants
are registered, the registry uses plan memory (stored outcomes) to score
each candidate and select the best one deterministically.

Single-plan registration (via ``register``) is the common case and
backward-compatible with all existing code.  Multi-plan registration
(via ``register_variant``) enables adaptive plan selection.

When a plan variant has failed repeatedly (failure_count >= MUTATION_THRESHOLD,
success_count == 0), the registry generates new plan variants by applying
deterministic transformations to the original steps.  This extends the
strategy space without randomness — same failures always produce the
same mutations.

Wraps the existing planner.py plan generators into a registry object
that the orchestration layer can hold as a dependency.  This is NOT
a replacement for planner.py — it delegates to the same generator
functions.

Usage:
    from umh.substrate.plan_registry import PlanRegistry

    registry = PlanRegistry.with_defaults()
    plan = registry.derive_plan(intent, state)
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any, Callable

from umh.substrate.intent_models import (
    Intent,
    IntentType,
    Plan,
    PlanStep,
    compute_plan_id,
)

_LOG_PREFIX = "[substrate.plan_registry]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


PlanDeriveFn = Callable[[Intent, dict[str, Any]], tuple[PlanStep, ...]]


@dataclass(frozen=True)
class PlanVariant:
    """A named plan generator variant.

    Attributes:
        variant_id: Stable identifier for this variant (used as plan_id
            prefix and as the plan memory key).  Must be unique within
            an intent_type.  Convention: ``{intent_type}:{short_name}``.
        generator: Deterministic function producing plan steps.
    """

    variant_id: str
    generator: PlanDeriveFn


class PlanRegistry:
    """Deterministic mapping from IntentType to plan derivation functions.

    Supports two registration modes:

    1. **Single-plan** (``register``): one generator per intent_type.
       Backward-compatible — existing callers are unchanged.

    2. **Multi-plan** (``register_variant``): multiple named variants per
       intent_type.  On ``derive_plan``, the registry scores each variant
       using plan memory from the state snapshot and selects the best.

    Selection is deterministic: same state → same plan choice.
    """

    def __init__(self) -> None:
        self._variants: dict[IntentType, list[PlanVariant]] = {}

    # ── Registration ─────────────────────────────────────────────────

    def register(self, intent_type: IntentType, fn: PlanDeriveFn) -> None:
        """Register a single plan generator for an intent type.

        Backward-compatible: replaces any existing variants for this
        intent_type with a single default variant.
        """
        variant = PlanVariant(
            variant_id=f"{intent_type.value}:default",
            generator=fn,
        )
        self._variants[intent_type] = [variant]
        _log(f"registered plan generator: {intent_type.value}")

    def register_variant(
        self,
        intent_type: IntentType,
        variant_id: str,
        fn: PlanDeriveFn,
    ) -> None:
        """Register an additional plan variant for an intent type.

        Multiple variants enable adaptive selection based on plan memory.
        variant_id must be unique within the intent_type.
        """
        variant = PlanVariant(variant_id=variant_id, generator=fn)
        existing = self._variants.get(intent_type, [])
        # Replace if same variant_id, otherwise append
        updated = [v for v in existing if v.variant_id != variant_id]
        updated.append(variant)
        self._variants[intent_type] = updated
        _log(f"registered plan variant: {intent_type.value}:{variant_id}")

    # ── Derivation ───────────────────────────────────────────────────

    def derive_plan(
        self,
        intent: Intent,
        state: dict[str, Any],
        current_timestamp: str = "",
    ) -> Plan | None:
        """Derive the best plan for the given intent.

        When multiple variants are registered:
        1. Derive steps from each variant.
        2. Score each using plan memory from state.
        3. Select the highest-scoring plan (tie-break: lexicographic variant_id).

        When only one variant exists: no scoring overhead, direct derivation.

        Args:
            intent: The intent to derive a plan for.
            state: Current state snapshot for reading plan memory.
            current_timestamp: ISO timestamp for staleness evaluation.
                If empty, staleness-based re-exploration is disabled.

        Returns None if no generator registered for the intent type
        or if all generators produce zero steps.
        Deterministic: same intent + state + timestamp always returns
        the same Plan.
        """
        variants = self._variants.get(intent.intent_type)
        if not variants:
            _log(f"no plan generator for: {intent.intent_type.value}")
            return None

        # Fast path: single variant (common case, no scoring needed)
        if len(variants) == 1:
            return self._derive_from_variant(variants[0], intent, state)

        # Multi-variant: derive all candidates, score, select best
        return self._select_best_variant(variants, intent, state, current_timestamp)

    def _derive_from_variant(
        self,
        variant: PlanVariant,
        intent: Intent,
        state: dict[str, Any],
    ) -> Plan | None:
        """Derive a plan from a single variant."""
        try:
            steps = variant.generator(intent, state)
        except Exception as exc:
            _log(
                f"plan generator error for "
                f"{intent.intent_type.value}:{variant.variant_id}: {exc}"
            )
            return None

        if not steps:
            return None

        plan_id = compute_plan_id(intent.intent_id, steps)
        return Plan(
            plan_id=plan_id,
            intent_id=intent.intent_id,
            steps=steps,
            variant_id=variant.variant_id,
        )

    def _select_best_variant(
        self,
        variants: list[PlanVariant],
        intent: Intent,
        state: dict[str, Any],
        current_timestamp: str = "",
    ) -> Plan | None:
        """Select the best variant using structured exploration policy.

        Selection priority (deterministic, no randomness):
        1. Untried plans (execution_count == 0) — lexicographic variant_id.
        2. Under-sampled plans (execution_count < MIN_EXECUTIONS_PER_PLAN)
           — lowest execution_count first, then lexicographic variant_id.
        3. Stale plans (not executed within STALE_WINDOW_SECONDS)
           — most stale first, then lexicographic variant_id.
           Disabled when current_timestamp is empty.
        4. Scored plans — highest score first, then lexicographic variant_id.

        This ensures every plan variant gets fair evaluation before
        score-based selection takes over, and stale plans are periodically
        re-evaluated.  Fully replay-safe.
        """
        from umh.substrate.plan_scoring import (
            MIN_EXECUTIONS_PER_PLAN,
            compute_state_signature,
            get_execution_count,
            is_stale,
            lookup_plan_memory,
            score_plan,
            staleness_seconds,
        )

        # Build candidate list: (memory, variant_id, plan)
        candidates: list[tuple[dict[str, Any] | None, str, Plan]] = []

        for variant in variants:
            plan = self._derive_from_variant(variant, intent, state)
            if plan is None:
                continue

            memory = lookup_plan_memory(
                state,
                intent.intent_type.value,
                intent.goal,
                variant.variant_id,
            )
            candidates.append((memory, variant.variant_id, plan))

        if not candidates:
            return None

        # ── Phase 0: deterministic mutation ──────────────────────────
        # Check if any candidate's failure record warrants generating
        # a mutated variant.  Mutations are registered permanently
        # (idempotent via variant_id dedup) and enter Phase 1 as
        # untried candidates.
        self._maybe_generate_mutations(candidates, intent, state)

        # Re-scan for newly registered variants that aren't yet in
        # the candidate list.
        existing_vids = {vid for _, vid, _ in candidates}
        for variant in self._variants.get(intent.intent_type, []):
            if variant.variant_id in existing_vids:
                continue
            plan = self._derive_from_variant(variant, intent, state)
            if plan is None:
                continue
            memory = lookup_plan_memory(
                state,
                intent.intent_type.value,
                intent.goal,
                variant.variant_id,
            )
            candidates.append((memory, variant.variant_id, plan))

        # ── Phase 1: untried plans (execution_count == 0) ────────────
        untried = [
            (vid, plan)
            for mem, vid, plan in candidates
            if get_execution_count(mem) == 0
        ]
        if untried:
            untried.sort(key=lambda c: c[0])  # lexicographic variant_id
            selected_vid, selected_plan = untried[0]
            _log(
                f"exploration: untried variant {selected_vid} selected "
                f"from {len(candidates)} candidates for "
                f"{intent.intent_type.value}"
            )
            return selected_plan

        # ── Phase 2: under-sampled (execution_count < MIN) ───────────
        under_sampled = [
            (get_execution_count(mem), vid, plan)
            for mem, vid, plan in candidates
            if get_execution_count(mem) < MIN_EXECUTIONS_PER_PLAN
        ]
        if under_sampled:
            # Lowest execution_count first, then lexicographic variant_id
            under_sampled.sort(key=lambda c: (c[0], c[1]))
            _, selected_vid, selected_plan = under_sampled[0]
            _log(
                f"exploration: under-sampled variant {selected_vid} selected "
                f"from {len(candidates)} candidates for "
                f"{intent.intent_type.value}"
            )
            return selected_plan

        # ── Phase 3: stale re-exploration ────────────────────────────
        # Only active when current_timestamp is provided.
        # Context-aware: computes state signature once and passes it
        # to is_stale so plans in an unchanged environment stay fresh.
        if current_timestamp:
            current_sig = compute_state_signature(state)
            stale_candidates = [
                (staleness_seconds(mem, current_timestamp), vid, plan)
                for mem, vid, plan in candidates
                if is_stale(mem, current_timestamp, current_sig)
            ]
            if stale_candidates:
                # Most stale first (largest gap), then lexicographic
                stale_candidates.sort(key=lambda c: (-c[0], c[1]))
                elapsed, selected_vid, selected_plan = stale_candidates[0]
                _log(
                    f"re-exploration: stale variant {selected_vid} "
                    f"(stale {elapsed:.0f}s) selected from "
                    f"{len(candidates)} candidates for "
                    f"{intent.intent_type.value}"
                )
                return selected_plan

        # ── Phase 4: score-based selection ────────────────────────────
        scored: list[tuple[float, str, Plan]] = []
        for mem, vid, plan in candidates:
            s = score_plan(mem)
            scored.append((s, vid, plan))

        scored.sort(key=lambda c: (-c[0], c[1]))
        selected = scored[0]

        _log(
            f"selected variant {selected[1]} (score={selected[0]:.3f}) "
            f"from {len(candidates)} candidates for {intent.intent_type.value}"
        )
        return selected[2]

    # ── Mutation ─────────────────────────────────────────────────────

    def _maybe_generate_mutations(
        self,
        candidates: list[tuple[dict[str, Any] | None, str, Plan]],
        intent: Intent,
        state: dict[str, Any],
    ) -> None:
        """Check candidates for mutation eligibility and register mutations.

        For each candidate whose plan memory meets the mutation trigger
        (failure_count >= MUTATION_THRESHOLD, success_count == 0), generate
        up to MAX_MUTATIONS_PER_PLAN new variants via deterministic
        transforms.

        Two-tier mutation strategy:
        - Tier 1 (causal): when plan memory has failure context
          (last_failure_step_index + last_failure_type), mutations
          target the specific step that failed.
        - Tier 2 (structural): when no failure context is available,
          falls back to structural transforms (reverse, rotate, etc.).

        Mutations are registered via register_variant (idempotent — same
        variant_id replaces existing).  They enter the candidate pool as
        untried variants (execution_count == 0) and are picked up by
        Phase 1 (exploration).

        Skips variants that are themselves mutations (no mutation chains).
        """
        from umh.substrate.plan_mutation import (
            MAX_MUTATIONS_PER_PLAN,
            build_mutated_variant_id,
            count_existing_mutations,
            extract_failure_context_from_memory,
            is_mutated_variant,
            mutate_plan_steps,
            should_mutate,
        )

        current_vids = self.get_variant_ids(intent.intent_type)

        for memory, variant_id, plan in candidates:
            # Skip variants that are themselves mutations — no chains.
            if is_mutated_variant(variant_id):
                continue

            if not should_mutate(memory):
                continue

            existing_count = count_existing_mutations(current_vids, variant_id)
            if existing_count >= MAX_MUTATIONS_PER_PLAN:
                continue

            # Extract failure context from plan memory for causal mutation.
            failure_context = extract_failure_context_from_memory(memory)

            # Generate mutations from existing_count up to MAX.
            for mut_idx in range(existing_count, MAX_MUTATIONS_PER_PLAN):
                mutated_steps = mutate_plan_steps(
                    original_steps=plan.steps,
                    intent_type=intent.intent_type.value,
                    goal=intent.goal,
                    mutation_index=mut_idx,
                    failure_context=failure_context,
                )
                mutated_vid = build_mutated_variant_id(
                    variant_id, mut_idx, failure_context
                )

                # Build a generator closure that captures the mutated steps.
                # The closure ignores intent/state args — steps are fixed.
                def _make_gen(
                    steps: tuple[PlanStep, ...],
                ) -> PlanDeriveFn:
                    def gen(
                        _intent: Intent, _state: dict[str, Any]
                    ) -> tuple[PlanStep, ...]:
                        return steps

                    return gen

                self.register_variant(
                    intent.intent_type,
                    mutated_vid,
                    _make_gen(mutated_steps),
                )
                _log(
                    f"mutation: generated {mutated_vid} from "
                    f"{variant_id} (transform applied to "
                    f"{len(plan.steps)} steps)"
                )

    # ── Query ────────────────────────────────────────────────────────

    def has_generator(self, intent_type: IntentType) -> bool:
        """Check if any generator is registered for the given type."""
        return bool(self._variants.get(intent_type))

    def get_variant_ids(self, intent_type: IntentType) -> list[str]:
        """Return variant IDs registered for an intent type (sorted)."""
        variants = self._variants.get(intent_type, [])
        return sorted(v.variant_id for v in variants)

    # ── Factory ──────────────────────────────────────────────────────

    @classmethod
    def with_defaults(cls) -> PlanRegistry:
        """Create a registry pre-loaded with the built-in planner.py generators.

        Delegates to the existing registered generators in planner.py
        so lifecycle plans are defined in one place only.
        """
        from umh.substrate.planner import get_plan_generator

        registry = cls()
        for intent_type in IntentType:
            gen = get_plan_generator(intent_type)
            if gen is not None:
                registry.register(intent_type, gen)
        return registry
