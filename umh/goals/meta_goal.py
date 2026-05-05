"""
MetaGoal — deterministic goal generation, mutation, and lifecycle management.

Previous behavior: goals are externally provided via GoalRegistry.
The system optimizes across them but cannot propose, evolve, or retire
goals based on what it learns during a session.

This module adds a closed-loop goal evolution layer:
    - Generate new goals when performance patterns demand it
    - Split goals (specialization) when entropy is high
    - Merge goals (abstraction) when success clusters emerge
    - Retire goals that decay below confidence threshold
    - Cap total goals to prevent uncontrolled growth

MetaGoalEngine observes GoalTracker signals and DecisionTrace history.
It proposes MetaGoal candidates that feed into GoalRegistry as normal
GoalState objects. The arbitrator and all downstream layers remain
unchanged — they see goals, not meta-goals.

Key design:
    - MetaGoal is frozen (immutable snapshot of a generated goal).
    - All generation logic is deterministic: same signals → same goals.
    - Confidence threshold gates activation (candidate → active).
    - Decay removes unused generated goals.
    - MAX_GOALS hard cap prevents explosion.
    - No LLM calls. No randomness. Pure function of trackers + traces.

Usage::

    from umh.goals.meta_goal import MetaGoalEngine, MetaGoal

    engine = MetaGoalEngine()
    result = engine.evaluate(registry, traces)
    # result.generated → new MetaGoal objects to add
    # result.retired → goal_ids to remove
    # result.mutations → list of GoalMutation records
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from umh.decision.trace import DecisionTrace
    from umh.goals.state import GoalRegistry

_log = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

MAX_GOALS = 10
MIN_CONFIDENCE_TO_ACTIVATE = 0.4
DECAY_RATE = 0.05
DECAY_FLOOR = 0.05

LOW_PERFORMANCE_THRESHOLD = 0.35
LOW_PERFORMANCE_WINDOW = 5
HIGH_ENTROPY_THRESHOLD = 0.6
SUCCESS_CLUSTER_THRESHOLD = 0.75
SUCCESS_CLUSTER_WINDOW = 5
MERGE_SIMILARITY_THRESHOLD = 0.8

GENERATED_PRIORITY_BASE = 0.5
SPLIT_PRIORITY_SCALE = 0.9
MERGE_PRIORITY_SCALE = 1.1
PRIORITY_CAP = 0.95

COOLDOWN_TURNS = 5


# ─── Data models ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MetaGoal:
    """Immutable snapshot of a generated or mutated goal."""

    goal_id: str
    origin: str  # "external" | "generated"
    parent_goals: tuple[str, ...]
    confidence: float
    utility_estimate: float
    lifecycle_state: str  # "active" | "candidate" | "retired"
    description: str = ""
    success_criteria: dict = field(default_factory=dict)
    priority: float = GENERATED_PRIORITY_BASE
    generation_turn: int = 0
    generation_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "goal_id": self.goal_id,
            "origin": self.origin,
            "parent_goals": list(self.parent_goals),
            "confidence": round(self.confidence, 4),
            "utility_estimate": round(self.utility_estimate, 4),
            "lifecycle_state": self.lifecycle_state,
            "description": self.description,
            "priority": round(self.priority, 4),
            "generation_turn": self.generation_turn,
            "generation_reason": self.generation_reason,
        }


@dataclass(frozen=True)
class GoalMutation:
    """Record of a goal mutation event."""

    mutation_type: str  # "split" | "merge" | "priority_adjust" | "retire"
    source_goals: tuple[str, ...]
    result_goals: tuple[str, ...]
    reason: str
    turn: int

    def to_dict(self) -> dict:
        return {
            "mutation_type": self.mutation_type,
            "source_goals": list(self.source_goals),
            "result_goals": list(self.result_goals),
            "reason": self.reason,
            "turn": self.turn,
        }


@dataclass(frozen=True)
class MetaGoalResult:
    """Output of a single MetaGoalEngine evaluation."""

    generated: tuple[MetaGoal, ...]
    retired: tuple[str, ...]
    mutations: tuple[GoalMutation, ...]
    reason: str

    def to_dict(self) -> dict:
        return {
            "generated": [g.to_dict() for g in self.generated],
            "retired": list(self.retired),
            "mutations": [m.to_dict() for m in self.mutations],
            "reason": self.reason,
        }

    @property
    def has_changes(self) -> bool:
        return bool(self.generated or self.retired or self.mutations)


NO_META_RESULT = MetaGoalResult(
    generated=(),
    retired=(),
    mutations=(),
    reason="no_action",
)


# ─── Engine ───────────────────────────────────────────────────────────────────


class MetaGoalEngine:
    """Deterministic goal generation and lifecycle manager.

    Observes GoalTracker signals from the GoalRegistry and
    DecisionTrace history. Proposes new goals, mutations, and
    retirements based on deterministic trigger conditions.

    State: tracks which goals were generated (vs external),
    their confidence, and cooldown timers.
    """

    def __init__(self) -> None:
        self._generated_goals: dict[str, MetaGoal] = {}
        self._last_generation_turn: int = -COOLDOWN_TURNS
        self._generation_counter: int = 0

    def evaluate(
        self,
        registry: GoalRegistry,
        traces: list[DecisionTrace] | None = None,
        current_turn: int = 0,
    ) -> MetaGoalResult:
        """Evaluate whether to generate, mutate, or retire goals.

        Runs all trigger checks in priority order:
            1. Decay unused generated goals
            2. Retire low-confidence generated goals
            3. Check for generation triggers (low perf, high entropy, success cluster)
            4. Check for mutation triggers (split, merge, priority adjust)
            5. Enforce MAX_GOALS cap

        Returns MetaGoalResult with all proposed changes.
        """
        traces = traces or []
        generated: list[MetaGoal] = []
        retired: list[str] = []
        mutations: list[GoalMutation] = []
        reasons: list[str] = []

        # ── 1. Decay unused generated goals ─────────────────────────
        self._decay_generated(registry, current_turn)

        # ── 2. Retire low-confidence generated goals ────────────────
        retire_ids = self._check_retirements(registry)
        retired.extend(retire_ids)
        if retire_ids:
            reasons.append("retired_low_confidence")

        # ── 3. Generation triggers ──────────────────────────────────
        if self._can_generate(registry, current_turn):
            new_goals, gen_mutations, gen_reasons = self._check_triggers(
                registry, traces, current_turn
            )
            generated.extend(new_goals)
            mutations.extend(gen_mutations)
            reasons.extend(gen_reasons)

        # ── 4. Priority adjustments for existing generated goals ────
        adj_mutations = self._adjust_priorities(registry, traces, current_turn)
        mutations.extend(adj_mutations)
        if adj_mutations:
            reasons.append("priority_adjusted")

        # ── 5. Enforce MAX_GOALS cap ────────────────────────────────
        cap_retired = self._enforce_cap(registry)
        retired.extend(cap_retired)
        if cap_retired:
            reasons.append("cap_enforced")

        reason = "_".join(reasons) if reasons else "no_action"

        if generated:
            self._last_generation_turn = current_turn

        return MetaGoalResult(
            generated=tuple(generated),
            retired=tuple(retired),
            mutations=tuple(mutations),
            reason=reason,
        )

    def register_generated(self, meta_goal: MetaGoal) -> None:
        """Track a generated goal in the engine's internal state."""
        self._generated_goals[meta_goal.goal_id] = meta_goal

    def get_generated(self, goal_id: str) -> MetaGoal | None:
        """Return a generated MetaGoal by ID, or None."""
        return self._generated_goals.get(goal_id)

    def is_generated(self, goal_id: str) -> bool:
        """Check if a goal was generated by this engine."""
        return goal_id in self._generated_goals

    @property
    def generated_count(self) -> int:
        return len(self._generated_goals)

    @property
    def generation_counter(self) -> int:
        return self._generation_counter

    # ── Internal: decay ─────────────────────────────────────────────────────

    def _decay_generated(self, registry: GoalRegistry, current_turn: int) -> None:
        """Decay confidence of generated goals not recently active."""
        for gid, mg in list(self._generated_goals.items()):
            if mg.lifecycle_state == "retired":
                continue

            tracker = registry.get_tracker(gid)
            staleness = current_turn - (tracker.last_active_turn if tracker else mg.generation_turn)

            if staleness <= 0:
                continue

            decayed_confidence = max(
                mg.confidence - (DECAY_RATE * staleness),
                DECAY_FLOOR,
            )

            if decayed_confidence != mg.confidence:
                self._generated_goals[gid] = MetaGoal(
                    goal_id=mg.goal_id,
                    origin=mg.origin,
                    parent_goals=mg.parent_goals,
                    confidence=decayed_confidence,
                    utility_estimate=mg.utility_estimate,
                    lifecycle_state=mg.lifecycle_state,
                    description=mg.description,
                    success_criteria=mg.success_criteria,
                    priority=mg.priority,
                    generation_turn=mg.generation_turn,
                    generation_reason=mg.generation_reason,
                )

    # ── Internal: retirement ────────────────────────────────────────────────

    def _check_retirements(self, registry: GoalRegistry) -> list[str]:
        """Retire generated goals below confidence threshold."""
        to_retire: list[str] = []
        for gid, mg in list(self._generated_goals.items()):
            if mg.lifecycle_state == "retired":
                continue
            if mg.confidence <= DECAY_FLOOR:
                to_retire.append(gid)
                self._generated_goals[gid] = MetaGoal(
                    goal_id=mg.goal_id,
                    origin=mg.origin,
                    parent_goals=mg.parent_goals,
                    confidence=mg.confidence,
                    utility_estimate=mg.utility_estimate,
                    lifecycle_state="retired",
                    description=mg.description,
                    success_criteria=mg.success_criteria,
                    priority=mg.priority,
                    generation_turn=mg.generation_turn,
                    generation_reason=mg.generation_reason,
                )
        return to_retire

    # ── Internal: can generate? ─────────────────────────────────────────────

    def _can_generate(self, registry: GoalRegistry, current_turn: int) -> bool:
        """Check if generation is allowed (cooldown + cap)."""
        if current_turn - self._last_generation_turn < COOLDOWN_TURNS:
            return False

        active_count = len(registry.get_all_goals())
        generated_active = sum(
            1 for mg in self._generated_goals.values() if mg.lifecycle_state != "retired"
        )
        total = active_count + generated_active
        if total >= MAX_GOALS:
            return False

        return True

    # ── Internal: trigger checks ────────────────────────────────────────────

    def _check_triggers(
        self,
        registry: GoalRegistry,
        traces: list,
        current_turn: int,
    ) -> tuple[list[MetaGoal], list[GoalMutation], list[str]]:
        """Check all generation triggers and return proposed goals + mutations."""
        generated: list[MetaGoal] = []
        mutations: list[GoalMutation] = []
        reasons: list[str] = []

        # Trigger 1: Persistent low performance → alternative goal
        low_perf = self._detect_low_performance(registry, traces)
        if low_perf:
            goal_id, parent_id = low_perf
            new_goal = self._generate_alternative(parent_id, registry, current_turn)
            if new_goal is not None:
                generated.append(new_goal)
                mutations.append(
                    GoalMutation(
                        mutation_type="split",
                        source_goals=(parent_id,),
                        result_goals=(new_goal.goal_id,),
                        reason="persistent_low_performance",
                        turn=current_turn,
                    )
                )
                reasons.append("low_performance_split")

        # Trigger 2: High entropy → specialization
        if not generated:
            high_ent = self._detect_high_entropy(traces)
            if high_ent:
                split_goals = self._generate_specializations(registry, traces, current_turn)
                for sg in split_goals:
                    generated.append(sg)
                if split_goals:
                    parent_ids = tuple(g.goal_id for g in registry.get_all_goals())
                    mutations.append(
                        GoalMutation(
                            mutation_type="split",
                            source_goals=parent_ids,
                            result_goals=tuple(g.goal_id for g in split_goals),
                            reason="high_entropy_specialization",
                            turn=current_turn,
                        )
                    )
                    reasons.append("high_entropy_split")

        # Trigger 3: Success cluster → abstraction
        if not generated:
            cluster = self._detect_success_cluster(registry)
            if cluster:
                merged = self._generate_abstraction(cluster, registry, current_turn)
                if merged is not None:
                    generated.append(merged)
                    mutations.append(
                        GoalMutation(
                            mutation_type="merge",
                            source_goals=tuple(cluster),
                            result_goals=(merged.goal_id,),
                            reason="success_cluster_abstraction",
                            turn=current_turn,
                        )
                    )
                    reasons.append("success_cluster_merge")

        return generated, mutations, reasons

    # ── Internal: trigger detection ─────────────────────────────────────────

    def _detect_low_performance(
        self,
        registry: GoalRegistry,
        traces: list,
    ) -> tuple[str, str] | None:
        """Detect persistent low performance on any active goal.

        Returns (generated_goal_id_prefix, parent_goal_id) or None.
        Uses recent trace window to check if goal_score is consistently
        below threshold.
        """
        if not traces or len(traces) < LOW_PERFORMANCE_WINDOW:
            return None

        recent = traces[-LOW_PERFORMANCE_WINDOW:]

        goal_scores: dict[str, list[float]] = {}
        for t in recent:
            gid = getattr(t, "active_goal_id", None)
            gs = getattr(t, "goal_score", None)
            if gid and gs is not None:
                goal_scores.setdefault(gid, []).append(gs)

        for gid, scores in sorted(goal_scores.items()):
            if len(scores) < LOW_PERFORMANCE_WINDOW:
                continue
            avg = sum(scores) / len(scores)
            if avg < LOW_PERFORMANCE_THRESHOLD:
                alt_id = f"meta_alt_{gid}"
                if alt_id not in self._generated_goals:
                    return (alt_id, gid)

        return None

    def _detect_high_entropy(self, traces: list) -> bool:
        """Detect high blended entropy in recent traces."""
        if not traces or len(traces) < 3:
            return False

        recent = traces[-3:]
        entropies = []
        for t in recent:
            e = getattr(t, "blended_entropy", None)
            if e is not None:
                entropies.append(e)

        if len(entropies) < 3:
            return False

        avg = sum(entropies) / len(entropies)
        return avg > HIGH_ENTROPY_THRESHOLD

    def _detect_success_cluster(
        self,
        registry: GoalRegistry,
    ) -> list[str] | None:
        """Detect goals with consistently high success that could be merged.

        Returns a list of goal_ids forming the cluster, or None.
        Requires at least 2 goals above SUCCESS_CLUSTER_THRESHOLD.
        """
        goals = registry.get_all_goals()
        if len(goals) < 2:
            return None

        high_performers: list[str] = []
        for g in goals:
            tracker = registry.get_tracker(g.goal_id)
            if tracker is None:
                continue
            if (
                tracker.success_score >= SUCCESS_CLUSTER_THRESHOLD
                and tracker.uses >= SUCCESS_CLUSTER_WINDOW
            ):
                high_performers.append(g.goal_id)

        if len(high_performers) >= 2:
            high_performers.sort()
            return high_performers[:2]

        return None

    # ── Internal: goal generation ───────────────────────────────────────────

    def _generate_alternative(
        self,
        parent_id: str,
        registry: GoalRegistry,
        current_turn: int,
    ) -> MetaGoal | None:
        """Generate an alternative goal when parent has low performance."""
        parent = registry.get_goal(parent_id)
        if parent is None:
            return None

        tracker = registry.get_tracker(parent_id)
        parent_score = tracker.success_score if tracker else 0.5

        self._generation_counter += 1
        goal_id = f"meta_alt_{parent_id}"

        new_criteria = dict(parent.success_criteria)
        new_criteria["_meta_origin"] = "alternative"

        priority = min(parent.priority * SPLIT_PRIORITY_SCALE, PRIORITY_CAP)

        return MetaGoal(
            goal_id=goal_id,
            origin="generated",
            parent_goals=(parent_id,),
            confidence=max(0.5, 1.0 - parent_score),
            utility_estimate=parent.priority * 0.8,
            lifecycle_state="candidate",
            description=f"Alternative approach to: {parent.description}",
            success_criteria=new_criteria,
            priority=priority,
            generation_turn=current_turn,
            generation_reason="persistent_low_performance",
        )

    def _generate_specializations(
        self,
        registry: GoalRegistry,
        traces: list,
        current_turn: int,
    ) -> list[MetaGoal]:
        """Generate specialized sub-goals when entropy is high."""
        goals = registry.get_all_goals()
        if not goals:
            return []

        primary_id = None
        if traces:
            last = traces[-1]
            primary_id = getattr(last, "blended_primary_goal_id", None)

        if primary_id is None and goals:
            primary_id = goals[0].goal_id

        parent = registry.get_goal(primary_id) if primary_id else None
        if parent is None:
            return []

        spec_id = f"meta_spec_{primary_id}"
        if spec_id in self._generated_goals:
            return []

        self._generation_counter += 1
        new_criteria = dict(parent.success_criteria)
        new_criteria["_meta_origin"] = "specialization"

        return [
            MetaGoal(
                goal_id=spec_id,
                origin="generated",
                parent_goals=(primary_id,),
                confidence=0.5,
                utility_estimate=parent.priority * 0.7,
                lifecycle_state="candidate",
                description=f"Specialized focus within: {parent.description}",
                success_criteria=new_criteria,
                priority=min(parent.priority * SPLIT_PRIORITY_SCALE, PRIORITY_CAP),
                generation_turn=current_turn,
                generation_reason="high_entropy_specialization",
            )
        ]

    def _generate_abstraction(
        self,
        cluster_ids: list[str],
        registry: GoalRegistry,
        current_turn: int,
    ) -> MetaGoal | None:
        """Generate an abstraction goal merging a success cluster."""
        if len(cluster_ids) < 2:
            return None

        merged_id = "meta_merge_" + "_".join(sorted(cluster_ids))
        if merged_id in self._generated_goals:
            return None

        merged_criteria: dict = {}
        priorities: list[float] = []
        descriptions: list[str] = []
        scores: list[float] = []

        for gid in cluster_ids:
            goal = registry.get_goal(gid)
            if goal is None:
                continue
            merged_criteria.update(goal.success_criteria)
            priorities.append(goal.priority)
            descriptions.append(goal.description)
            tracker = registry.get_tracker(gid)
            if tracker:
                scores.append(tracker.success_score)

        if not priorities:
            return None

        merged_criteria["_meta_origin"] = "abstraction"
        avg_priority = sum(priorities) / len(priorities)
        avg_score = sum(scores) / len(scores) if scores else 0.5

        self._generation_counter += 1

        return MetaGoal(
            goal_id=merged_id,
            origin="generated",
            parent_goals=tuple(sorted(cluster_ids)),
            confidence=min(avg_score, 0.9),
            utility_estimate=avg_priority * 1.1,
            lifecycle_state="candidate",
            description=f"Unified goal from: {', '.join(descriptions)}",
            success_criteria=merged_criteria,
            priority=min(avg_priority * MERGE_PRIORITY_SCALE, PRIORITY_CAP),
            generation_turn=current_turn,
            generation_reason="success_cluster_abstraction",
        )

    # ── Internal: priority adjustment ───────────────────────────────────────

    def _adjust_priorities(
        self,
        registry: GoalRegistry,
        traces: list,
        current_turn: int,
    ) -> list[GoalMutation]:
        """Adjust priorities of generated goals based on tracker performance."""
        mutations: list[GoalMutation] = []

        for gid, mg in list(self._generated_goals.items()):
            if mg.lifecycle_state == "retired":
                continue

            tracker = registry.get_tracker(gid)
            if tracker is None or tracker.uses < 3:
                continue

            if tracker.success_score > SUCCESS_CLUSTER_THRESHOLD:
                new_priority = min(mg.priority * 1.1, PRIORITY_CAP)
                if new_priority != mg.priority:
                    self._generated_goals[gid] = MetaGoal(
                        goal_id=mg.goal_id,
                        origin=mg.origin,
                        parent_goals=mg.parent_goals,
                        confidence=min(mg.confidence + 0.05, 0.95),
                        utility_estimate=mg.utility_estimate,
                        lifecycle_state=mg.lifecycle_state,
                        description=mg.description,
                        success_criteria=mg.success_criteria,
                        priority=new_priority,
                        generation_turn=mg.generation_turn,
                        generation_reason=mg.generation_reason,
                    )
                    mutations.append(
                        GoalMutation(
                            mutation_type="priority_adjust",
                            source_goals=(gid,),
                            result_goals=(gid,),
                            reason="high_performance_boost",
                            turn=current_turn,
                        )
                    )

            elif tracker.success_score < LOW_PERFORMANCE_THRESHOLD:
                new_priority = max(mg.priority * 0.9, 0.1)
                if new_priority != mg.priority:
                    self._generated_goals[gid] = MetaGoal(
                        goal_id=mg.goal_id,
                        origin=mg.origin,
                        parent_goals=mg.parent_goals,
                        confidence=max(mg.confidence - 0.05, DECAY_FLOOR),
                        utility_estimate=mg.utility_estimate,
                        lifecycle_state=mg.lifecycle_state,
                        description=mg.description,
                        success_criteria=mg.success_criteria,
                        priority=new_priority,
                        generation_turn=mg.generation_turn,
                        generation_reason=mg.generation_reason,
                    )
                    mutations.append(
                        GoalMutation(
                            mutation_type="priority_adjust",
                            source_goals=(gid,),
                            result_goals=(gid,),
                            reason="low_performance_reduction",
                            turn=current_turn,
                        )
                    )

        return mutations

    # ── Internal: cap enforcement ───────────────────────────────────────────

    def _enforce_cap(self, registry: GoalRegistry) -> list[str]:
        """Remove lowest-confidence generated goals if over MAX_GOALS."""
        total = len(registry.get_all_goals())
        if total <= MAX_GOALS:
            return []

        overflow = total - MAX_GOALS
        candidates = [
            (gid, mg)
            for gid, mg in self._generated_goals.items()
            if mg.lifecycle_state != "retired"
        ]
        candidates.sort(key=lambda x: (x[1].confidence, x[0]))

        to_remove: list[str] = []
        for gid, mg in candidates[:overflow]:
            to_remove.append(gid)
            self._generated_goals[gid] = MetaGoal(
                goal_id=mg.goal_id,
                origin=mg.origin,
                parent_goals=mg.parent_goals,
                confidence=mg.confidence,
                utility_estimate=mg.utility_estimate,
                lifecycle_state="retired",
                description=mg.description,
                success_criteria=mg.success_criteria,
                priority=mg.priority,
                generation_turn=mg.generation_turn,
                generation_reason=mg.generation_reason,
            )

        return to_remove

    # ── Confidence update from learning feedback ────────────────────────────

    def update_confidence(
        self,
        goal_id: str,
        goal_score: float,
        convergence_stable: bool = False,
    ) -> None:
        """Update a generated goal's confidence from performance feedback.

        Called after goal evaluation each turn. Nudges confidence toward
        observed performance.
        """
        mg = self._generated_goals.get(goal_id)
        if mg is None or mg.lifecycle_state == "retired":
            return

        delta = (goal_score - mg.confidence) * 0.2
        if convergence_stable:
            delta *= 1.5

        new_confidence = max(DECAY_FLOOR, min(0.95, mg.confidence + delta))

        self._generated_goals[goal_id] = MetaGoal(
            goal_id=mg.goal_id,
            origin=mg.origin,
            parent_goals=mg.parent_goals,
            confidence=new_confidence,
            utility_estimate=mg.utility_estimate,
            lifecycle_state=mg.lifecycle_state,
            description=mg.description,
            success_criteria=mg.success_criteria,
            priority=mg.priority,
            generation_turn=mg.generation_turn,
            generation_reason=mg.generation_reason,
        )

    def activate_candidate(self, goal_id: str) -> bool:
        """Promote a candidate goal to active if confidence is sufficient."""
        mg = self._generated_goals.get(goal_id)
        if mg is None:
            return False
        if mg.lifecycle_state != "candidate":
            return False
        if mg.confidence < MIN_CONFIDENCE_TO_ACTIVATE:
            return False

        self._generated_goals[goal_id] = MetaGoal(
            goal_id=mg.goal_id,
            origin=mg.origin,
            parent_goals=mg.parent_goals,
            confidence=mg.confidence,
            utility_estimate=mg.utility_estimate,
            lifecycle_state="active",
            description=mg.description,
            success_criteria=mg.success_criteria,
            priority=mg.priority,
            generation_turn=mg.generation_turn,
            generation_reason=mg.generation_reason,
        )
        return True

    def to_meta_goal_state(self, meta_goal: MetaGoal) -> object:
        """Convert a MetaGoal to a GoalState for registry insertion."""
        from umh.goals.state import GoalState

        return GoalState(
            goal_id=meta_goal.goal_id,
            description=meta_goal.description,
            success_criteria=meta_goal.success_criteria,
            priority=meta_goal.priority,
            active=meta_goal.lifecycle_state == "active",
        )

    def snapshot(self) -> dict:
        """Return a snapshot of the meta-goal engine state."""
        return {
            "generated_goals": {gid: mg.to_dict() for gid, mg in self._generated_goals.items()},
            "generation_counter": self._generation_counter,
            "last_generation_turn": self._last_generation_turn,
            "active_generated": sum(
                1 for mg in self._generated_goals.values() if mg.lifecycle_state == "active"
            ),
            "candidates": sum(
                1 for mg in self._generated_goals.values() if mg.lifecycle_state == "candidate"
            ),
            "retired": sum(
                1 for mg in self._generated_goals.values() if mg.lifecycle_state == "retired"
            ),
        }
