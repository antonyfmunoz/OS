"""Tests for adaptive plan selection — deterministic strategy scoring.

Validates:
1. Single plan → always selected.
2. Multiple plans → higher success rate wins.
3. Failure penalty reduces score.
4. Tie → deterministic selection (lexicographic variant_id).
5. No memory → default plan selected (first, lexicographic).
6. Memory updates per plan correctly.
7. Replay determinism (multiple runs, same result).
8. Different goals → separate memory keys.
9. Plan switch after repeated failures.

Exploration policy (structured, no randomness):
10. Untried plan always selected first.
11. Multiple untried → lexicographic variant_id order.
12. Under-sampled plans selected before scored ones.
13. After MIN_EXECUTIONS reached → scoring takes over.
14. Deterministic exploration across runs.
15. No regression in existing scoring behavior.
16. Plan switching still occurs after poor performance with exploration.
17. Edge: high-score plan A (10 runs) vs plan B (1 run) → B selected.

Staleness-based re-exploration (deterministic, periodic re-evaluation):
18. Stale plan selected over higher-scoring fresh plan.
19. Multiple stale plans → most stale selected.
20. No stale plans → fallback to scoring.
21. Timestamp missing → staleness disabled.
22. Deterministic staleness selection across runs.
23. Replay produces identical staleness selection.
24. Stale plan re-evaluated and score updated correctly.
25. Edge: high-score stale plan A vs medium-score recent plan B.

Also:
- score_plan correctness for edge cases.
- get_execution_count helper.
- is_stale / staleness_seconds pure functions.
- last_executed_at in plan memory schema.
- PlanRegistry multi-variant registration and selection.
- Existing single-variant behavior unchanged.
"""

from __future__ import annotations

import sys
import unittest
from typing import Any

sys.path.insert(0, "/opt/OS")

from umh.substrate.intent_models import (
    Intent,
    IntentType,
    PlanStep,
    compute_intent_id,
)
from umh.substrate.plan_registry import PlanRegistry
from umh.substrate.plan_scoring import (
    MIN_EXECUTIONS_PER_PLAN,
    STALE_WINDOW_SECONDS,
    build_plan_memory_update_mutations,
    compute_plan_memory_key,
    compute_state_signature,
    get_execution_count,
    is_stale,
    lookup_plan_memory,
    score_plan,
    select_best_plan,
    staleness_seconds,
)
from umh.substrate.runtime_state_store import RuntimeStateStore


# ── Helpers ──────────────────────────────────────────────────────────


def _make_intent(
    intent_type: IntentType = IntentType.LIFECYCLE_FINALIZE,
    goal: dict | None = None,
    session_name: str = "test_session",
) -> Intent:
    goal = goal or {"session_name": session_name}
    return Intent(
        intent_id=compute_intent_id(intent_type, goal),
        intent_type=intent_type,
        goal=goal,
        session_name=session_name,
        created_at="2026-04-17T00:00:00+00:00",
    )


def _make_store(state: dict | None = None) -> RuntimeStateStore:
    store = RuntimeStateStore()
    if state:
        for k, v in state.items():
            store.set(k, v)
    return store


GOAL_A = {"session_name": "s1", "task": "finalize"}
GOAL_B = {"session_name": "s2", "task": "publish"}
INTENT_TYPE = "lifecycle_finalize"
TIMESTAMP = "2026-04-17T00:00:00+00:00"


# ── Plan generators for testing ──────────────────────────────────────


def _fast_finalize(intent: Intent, state: dict) -> tuple[PlanStep, ...]:
    """Fast finalize: 1 step."""
    return (PlanStep(step_index=0, event_type="finalization_succeeded", payload={}),)


def _safe_finalize(intent: Intent, state: dict) -> tuple[PlanStep, ...]:
    """Safe finalize: 2 steps (check + finalize)."""
    return (
        PlanStep(step_index=0, event_type="pre_check", payload={}),
        PlanStep(step_index=1, event_type="finalization_succeeded", payload={}),
    )


def _slow_finalize(intent: Intent, state: dict) -> tuple[PlanStep, ...]:
    """Slow finalize: 3 steps."""
    return (
        PlanStep(step_index=0, event_type="pre_check", payload={}),
        PlanStep(step_index=1, event_type="validation", payload={}),
        PlanStep(step_index=2, event_type="finalization_succeeded", payload={}),
    )


# ── A. Plan Scoring Function Tests ──────────────────────────────────


class TestScorePlan(unittest.TestCase):
    def test_no_memory_scores_zero(self):
        assert score_plan(None) == 0.0

    def test_zero_executions_scores_zero(self):
        mem = {"success_count": 0, "failure_count": 0, "execution_count": 0}
        assert score_plan(mem) == 0.0

    def test_all_success(self):
        mem = {"success_count": 5, "failure_count": 0, "execution_count": 5}
        # score = 5/5 - 0*0.1 = 1.0
        assert score_plan(mem) == 1.0

    def test_all_failure(self):
        mem = {"success_count": 0, "failure_count": 5, "execution_count": 5}
        # score = 0/5 - 5*0.1 = -0.5
        assert score_plan(mem) == -0.5

    def test_mixed(self):
        mem = {"success_count": 3, "failure_count": 2, "execution_count": 5}
        # score = 3/5 - 2*0.1 = 0.6 - 0.2 = 0.4
        assert abs(score_plan(mem) - 0.4) < 1e-9

    def test_single_success(self):
        mem = {"success_count": 1, "failure_count": 0, "execution_count": 1}
        assert score_plan(mem) == 1.0

    def test_penalty_can_go_negative(self):
        mem = {"success_count": 1, "failure_count": 20, "execution_count": 21}
        # score = 1/21 - 20*0.1 ≈ 0.048 - 2.0 ≈ -1.952
        assert score_plan(mem) < 0


# ── B. Plan Memory Key Tests ────────────────────────────────────────


class TestPlanMemoryKey(unittest.TestCase):
    def test_key_format(self):
        key = compute_plan_memory_key(INTENT_TYPE, GOAL_A, "variant_fast")
        assert key.startswith("plan_memory.lifecycle_finalize.")
        assert key.endswith(".variant_fast")

    def test_same_inputs_same_key(self):
        k1 = compute_plan_memory_key(INTENT_TYPE, GOAL_A, "v1")
        k2 = compute_plan_memory_key(INTENT_TYPE, GOAL_A, "v1")
        assert k1 == k2

    def test_different_goals_different_keys(self):
        k1 = compute_plan_memory_key(INTENT_TYPE, GOAL_A, "v1")
        k2 = compute_plan_memory_key(INTENT_TYPE, GOAL_B, "v1")
        assert k1 != k2

    def test_different_plans_different_keys(self):
        k1 = compute_plan_memory_key(INTENT_TYPE, GOAL_A, "v1")
        k2 = compute_plan_memory_key(INTENT_TYPE, GOAL_A, "v2")
        assert k1 != k2


# ── C. Plan Memory Mutation Tests ───────────────────────────────────


class TestPlanMemoryMutations(unittest.TestCase):
    def test_creates_memory_on_first_completion(self):
        mutations = build_plan_memory_update_mutations(
            INTENT_TYPE,
            GOAL_A,
            "v_fast",
            "completed",
            TIMESTAMP,
            {},
        )
        assert len(mutations) == 1
        m = mutations[0]
        assert m["op"] == "SET"
        record = m["value"]
        assert record["plan_id"] == "v_fast"
        assert record["success_count"] == 1
        assert record["failure_count"] == 0
        assert record["execution_count"] == 1
        assert record["last_outcome"] == "completed"

    def test_failure_increments(self):
        key = compute_plan_memory_key(INTENT_TYPE, GOAL_A, "v_fast")
        state = {
            key: {
                "plan_id": "v_fast",
                "success_count": 1,
                "failure_count": 0,
                "execution_count": 1,
                "last_outcome": "completed",
            }
        }
        mutations = build_plan_memory_update_mutations(
            INTENT_TYPE,
            GOAL_A,
            "v_fast",
            "failed",
            TIMESTAMP,
            state,
        )
        record = mutations[0]["value"]
        assert record["success_count"] == 1
        assert record["failure_count"] == 1
        assert record["execution_count"] == 2
        assert record["last_outcome"] == "failed"

    def test_memory_updates_per_plan_correctly(self):
        """Test 6: memory updates per plan correctly."""
        state: dict = {}
        key_fast = compute_plan_memory_key(INTENT_TYPE, GOAL_A, "v_fast")
        key_safe = compute_plan_memory_key(INTENT_TYPE, GOAL_A, "v_safe")

        # v_fast: 2 successes
        for ts in ["t1", "t2"]:
            m = build_plan_memory_update_mutations(
                INTENT_TYPE,
                GOAL_A,
                "v_fast",
                "completed",
                ts,
                state,
            )
            state[key_fast] = m[0]["value"]

        # v_safe: 1 success, 1 failure
        m = build_plan_memory_update_mutations(
            INTENT_TYPE,
            GOAL_A,
            "v_safe",
            "completed",
            "t3",
            state,
        )
        state[key_safe] = m[0]["value"]
        m = build_plan_memory_update_mutations(
            INTENT_TYPE,
            GOAL_A,
            "v_safe",
            "failed",
            "t4",
            state,
        )
        state[key_safe] = m[0]["value"]

        # Verify independence
        fast_rec = state[key_fast]
        assert fast_rec["success_count"] == 2
        assert fast_rec["failure_count"] == 0
        assert fast_rec["execution_count"] == 2

        safe_rec = state[key_safe]
        assert safe_rec["success_count"] == 1
        assert safe_rec["failure_count"] == 1
        assert safe_rec["execution_count"] == 2

    def test_mutation_is_set_only(self):
        mutations = build_plan_memory_update_mutations(
            INTENT_TYPE,
            GOAL_A,
            "v1",
            "completed",
            TIMESTAMP,
            {},
        )
        for m in mutations:
            assert m["op"] == "SET"


# ── D. Plan Selection Tests ─────────────────────────────────────────


class TestSelectBestPlan(unittest.TestCase):
    def test_single_plan_always_selected(self):
        """Test 1: single plan → always selected."""
        result = select_best_plan(["v_only"], INTENT_TYPE, GOAL_A, {})
        assert result == "v_only"

    def test_higher_success_rate_wins(self):
        """Test 2: multiple plans → higher success rate wins."""
        key_fast = compute_plan_memory_key(INTENT_TYPE, GOAL_A, "v_fast")
        key_safe = compute_plan_memory_key(INTENT_TYPE, GOAL_A, "v_safe")
        state = {
            key_fast: {
                "plan_id": "v_fast",
                "success_count": 3,
                "failure_count": 2,
                "execution_count": 5,
                "last_outcome": "completed",
            },
            key_safe: {
                "plan_id": "v_safe",
                "success_count": 4,
                "failure_count": 1,
                "execution_count": 5,
                "last_outcome": "completed",
            },
        }
        # v_fast: 3/5 - 2*0.1 = 0.4
        # v_safe: 4/5 - 1*0.1 = 0.7
        result = select_best_plan(
            ["v_fast", "v_safe"],
            INTENT_TYPE,
            GOAL_A,
            state,
        )
        assert result == "v_safe"

    def test_failure_penalty_reduces_score(self):
        """Test 3: failure penalty reduces score."""
        key = compute_plan_memory_key(INTENT_TYPE, GOAL_A, "v1")
        state = {
            key: {
                "plan_id": "v1",
                "success_count": 5,
                "failure_count": 10,
                "execution_count": 15,
                "last_outcome": "failed",
            },
        }
        # v1: 5/15 - 10*0.1 = 0.333 - 1.0 = -0.667 (negative)
        # v2: no memory → 0.0 (wins)
        result = select_best_plan(
            ["v1", "v2"],
            INTENT_TYPE,
            GOAL_A,
            state,
        )
        assert result == "v2"

    def test_tie_deterministic_selection(self):
        """Test 4: tie → deterministic selection (lexicographic variant_id)."""
        # Both have no memory → both score 0.0 → "v_alpha" < "v_beta"
        result = select_best_plan(
            ["v_beta", "v_alpha"],
            INTENT_TYPE,
            GOAL_A,
            {},
        )
        assert result == "v_alpha"

    def test_tie_with_equal_scores(self):
        """Tie with equal non-zero scores → lexicographic."""
        key_a = compute_plan_memory_key(INTENT_TYPE, GOAL_A, "plan_a")
        key_b = compute_plan_memory_key(INTENT_TYPE, GOAL_A, "plan_b")
        state = {
            key_a: {
                "plan_id": "plan_a",
                "success_count": 3,
                "failure_count": 1,
                "execution_count": 4,
                "last_outcome": "completed",
            },
            key_b: {
                "plan_id": "plan_b",
                "success_count": 3,
                "failure_count": 1,
                "execution_count": 4,
                "last_outcome": "completed",
            },
        }
        result = select_best_plan(
            ["plan_b", "plan_a"],
            INTENT_TYPE,
            GOAL_A,
            state,
        )
        assert result == "plan_a"

    def test_no_memory_default_plan(self):
        """Test 5: no memory → default plan selected (first lexicographic)."""
        result = select_best_plan(
            ["z_plan", "a_plan", "m_plan"],
            INTENT_TYPE,
            GOAL_A,
            {},
        )
        assert result == "a_plan"

    def test_empty_candidates_returns_none(self):
        result = select_best_plan([], INTENT_TYPE, GOAL_A, {})
        assert result is None

    def test_different_goals_separate_keys(self):
        """Test 8: different goals → separate memory keys."""
        key_a = compute_plan_memory_key(INTENT_TYPE, GOAL_A, "v1")
        key_b = compute_plan_memory_key(INTENT_TYPE, GOAL_B, "v1")
        assert key_a != key_b

        # v1 has good score for GOAL_A but no score for GOAL_B
        state = {
            key_a: {
                "plan_id": "v1",
                "success_count": 10,
                "failure_count": 0,
                "execution_count": 10,
                "last_outcome": "completed",
            },
        }
        # For GOAL_A: v1 scores 1.0
        result_a = select_best_plan(["v1", "v2"], INTENT_TYPE, GOAL_A, state)
        assert result_a == "v1"

        # For GOAL_B: v1 has no memory (scores 0.0), same as v2 → lexicographic
        result_b = select_best_plan(["v1", "v2"], INTENT_TYPE, GOAL_B, state)
        assert result_b == "v1"  # "v1" < "v2" lexicographically

    def test_plan_switch_after_repeated_failures(self):
        """Test 9: plan switch after repeated failures."""
        key_fast = compute_plan_memory_key(INTENT_TYPE, GOAL_A, "v_fast")
        state: dict = {}

        # Accumulate failures for v_fast
        for i in range(5):
            m = build_plan_memory_update_mutations(
                INTENT_TYPE,
                GOAL_A,
                "v_fast",
                "failed",
                f"t{i}",
                state,
            )
            state[key_fast] = m[0]["value"]

        # v_fast: 0/5 - 5*0.1 = -0.5
        # v_safe: no memory → 0.0 (wins)
        result = select_best_plan(
            ["v_fast", "v_safe"],
            INTENT_TYPE,
            GOAL_A,
            state,
        )
        assert result == "v_safe"


# ── E. PlanRegistry Multi-Variant Tests ──────────────────────────────


class TestPlanRegistryMultiVariant(unittest.TestCase):
    def test_register_variant_creates_multiple(self):
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)
        ids = reg.get_variant_ids(IntentType.LIFECYCLE_FINALIZE)
        assert ids == ["v_fast", "v_safe"]

    def test_single_variant_derive(self):
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        intent = _make_intent()
        plan = reg.derive_plan(intent, {})
        assert plan is not None
        assert plan.step_count == 1
        assert plan.variant_id == "v_fast"

    def test_multi_variant_selects_by_score(self):
        """Multi-variant: higher-scoring plan selected."""
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)

        intent = _make_intent()

        # Seed plan memory: v_safe has better record
        key_fast = compute_plan_memory_key(
            INTENT_TYPE,
            intent.goal,
            "v_fast",
        )
        key_safe = compute_plan_memory_key(
            INTENT_TYPE,
            intent.goal,
            "v_safe",
        )
        state = {
            key_fast: {
                "plan_id": "v_fast",
                "success_count": 1,
                "failure_count": 4,
                "execution_count": 5,
                "last_outcome": "failed",
            },
            key_safe: {
                "plan_id": "v_safe",
                "success_count": 4,
                "failure_count": 1,
                "execution_count": 5,
                "last_outcome": "completed",
            },
        }

        plan = reg.derive_plan(intent, state)
        assert plan is not None
        assert plan.variant_id == "v_safe"
        assert plan.step_count == 2  # safe has 2 steps

    def test_multi_variant_no_memory_lexicographic(self):
        """No memory → lexicographic variant_id wins."""
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)

        intent = _make_intent()
        plan = reg.derive_plan(intent, {})
        assert plan is not None
        assert plan.variant_id == "v_fast"  # "v_fast" < "v_safe"

    def test_register_overwrites_register_variant(self):
        """register() replaces all variants with single default."""
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v1", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v2", _safe_finalize)
        assert len(reg.get_variant_ids(IntentType.LIFECYCLE_FINALIZE)) == 2

        # register() replaces with single default
        reg.register(IntentType.LIFECYCLE_FINALIZE, _slow_finalize)
        ids = reg.get_variant_ids(IntentType.LIFECYCLE_FINALIZE)
        assert len(ids) == 1
        assert ids[0] == "lifecycle_finalize:default"

    def test_variant_id_dedup(self):
        """Re-registering same variant_id replaces, doesn't duplicate."""
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v1", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v1", _safe_finalize)
        ids = reg.get_variant_ids(IntentType.LIFECYCLE_FINALIZE)
        assert len(ids) == 1
        # Should use the latest generator (safe, 2 steps)
        intent = _make_intent()
        plan = reg.derive_plan(intent, {})
        assert plan is not None
        assert plan.step_count == 2

    def test_plan_carries_variant_id(self):
        """Derived Plan carries the variant_id field."""
        reg = PlanRegistry()
        reg.register(IntentType.LIFECYCLE_FINALIZE, _fast_finalize)
        intent = _make_intent()
        plan = reg.derive_plan(intent, {})
        assert plan is not None
        assert plan.variant_id == "lifecycle_finalize:default"


# ── F. Replay Determinism Tests ──────────────────────────────────────


class TestReplayDeterminism(unittest.TestCase):
    def test_same_state_same_selection(self):
        """Test 7: same state produces same plan choice across runs."""
        key_fast = compute_plan_memory_key(INTENT_TYPE, GOAL_A, "v_fast")
        key_safe = compute_plan_memory_key(INTENT_TYPE, GOAL_A, "v_safe")
        state = {
            key_fast: {
                "plan_id": "v_fast",
                "success_count": 2,
                "failure_count": 3,
                "execution_count": 5,
                "last_outcome": "failed",
            },
            key_safe: {
                "plan_id": "v_safe",
                "success_count": 4,
                "failure_count": 1,
                "execution_count": 5,
                "last_outcome": "completed",
            },
        }

        results = [
            select_best_plan(["v_fast", "v_safe"], INTENT_TYPE, GOAL_A, state)
            for _ in range(100)
        ]
        assert all(r == "v_safe" for r in results)

    def test_same_mutations_same_memory(self):
        """Same mutation sequence → identical plan memory state."""
        events = [
            ("v1", "completed", "t1"),
            ("v1", "failed", "t2"),
            ("v2", "completed", "t3"),
            ("v2", "completed", "t4"),
        ]

        # Run 1
        state1: dict = {}
        for pid, outcome, ts in events:
            key = compute_plan_memory_key(INTENT_TYPE, GOAL_A, pid)
            m = build_plan_memory_update_mutations(
                INTENT_TYPE,
                GOAL_A,
                pid,
                outcome,
                ts,
                state1,
            )
            state1[key] = m[0]["value"]

        # Run 2 (replay)
        state2: dict = {}
        for pid, outcome, ts in events:
            key = compute_plan_memory_key(INTENT_TYPE, GOAL_A, pid)
            m = build_plan_memory_update_mutations(
                INTENT_TYPE,
                GOAL_A,
                pid,
                outcome,
                ts,
                state2,
            )
            state2[key] = m[0]["value"]

        # Identical state
        for pid in ["v1", "v2"]:
            key = compute_plan_memory_key(INTENT_TYPE, GOAL_A, pid)
            assert state1[key] == state2[key]

    def test_registry_selection_deterministic(self):
        """Full registry path: same state → same Plan selection."""
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_slow", _slow_finalize)

        intent = _make_intent()
        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")
        state = {
            key_fast: {
                "plan_id": "v_fast",
                "success_count": 0,
                "failure_count": 5,
                "execution_count": 5,
                "last_outcome": "failed",
            },
        }

        plans = [reg.derive_plan(intent, state) for _ in range(50)]
        # All should select the same variant (determinism)
        variant_ids = {p.variant_id for p in plans if p is not None}
        assert len(variant_ids) == 1
        # v_fast has 5 failures, 0 successes → triggers mutation.
        # Mutated variant v_fast::mut_0 is untried → selected by Phase 1.
        assert plans[0].variant_id == "v_fast::mut_0"


# ── G. Exploration Helper Tests ─────────────────────────────────────


class TestGetExecutionCount(unittest.TestCase):
    def test_none_memory_returns_zero(self):
        assert get_execution_count(None) == 0

    def test_missing_key_returns_zero(self):
        assert get_execution_count({"success_count": 3}) == 0

    def test_returns_count(self):
        assert get_execution_count({"execution_count": 7}) == 7

    def test_zero_count(self):
        assert get_execution_count({"execution_count": 0}) == 0


# ── H. Exploration Policy Tests (PlanRegistry) ─────────────────────


class TestExplorationPolicy(unittest.TestCase):
    """Tests for structured exploration in PlanRegistry._select_best_variant.

    Validates the 3-tier selection priority:
    1. Untried plans (execution_count == 0)
    2. Under-sampled plans (execution_count < MIN_EXECUTIONS_PER_PLAN)
    3. Score-based selection (existing logic)
    """

    def _registry_with_three_variants(self) -> PlanRegistry:
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_slow", _slow_finalize)
        return reg

    def test_untried_plan_selected_first(self):
        """Test 10: untried plan is always selected first."""
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)

        intent = _make_intent()
        # v_fast has 10 runs with perfect score; v_safe has 0 runs
        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")
        state = {
            key_fast: {
                "plan_id": "v_fast",
                "success_count": 10,
                "failure_count": 0,
                "execution_count": 10,
                "last_outcome": "completed",
            },
        }

        plan = reg.derive_plan(intent, state)
        assert plan is not None
        # v_safe is untried → selected despite v_fast having score 1.0
        assert plan.variant_id == "v_safe"

    def test_multiple_untried_lexicographic_order(self):
        """Test 11: multiple untried → lexicographic variant_id order."""
        reg = self._registry_with_three_variants()
        intent = _make_intent()

        # All untried (empty state) → "v_fast" < "v_safe" < "v_slow"
        plan = reg.derive_plan(intent, {})
        assert plan is not None
        assert plan.variant_id == "v_fast"

    def test_under_sampled_before_scored(self):
        """Test 12: under-sampled plans selected before scored ones."""
        reg = self._registry_with_three_variants()
        intent = _make_intent()

        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")
        key_safe = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_safe")
        key_slow = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_slow")

        state = {
            # v_fast: fully sampled (>= MIN_EXECUTIONS), high score
            key_fast: {
                "plan_id": "v_fast",
                "success_count": 5,
                "failure_count": 0,
                "execution_count": 5,
                "last_outcome": "completed",
            },
            # v_safe: under-sampled (1 run)
            key_safe: {
                "plan_id": "v_safe",
                "success_count": 0,
                "failure_count": 1,
                "execution_count": 1,
                "last_outcome": "failed",
            },
            # v_slow: fully sampled, lower score
            key_slow: {
                "plan_id": "v_slow",
                "success_count": 2,
                "failure_count": 3,
                "execution_count": 5,
                "last_outcome": "failed",
            },
        }

        plan = reg.derive_plan(intent, state)
        assert plan is not None
        # v_safe has only 1 run (< MIN_EXECUTIONS_PER_PLAN) → selected
        assert plan.variant_id == "v_safe"

    def test_scoring_takes_over_after_min_executions(self):
        """Test 13: after MIN_EXECUTIONS reached → scoring takes over."""
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)

        intent = _make_intent()

        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")
        key_safe = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_safe")

        # Both have >= MIN_EXECUTIONS_PER_PLAN runs
        state = {
            key_fast: {
                "plan_id": "v_fast",
                "success_count": 1,
                "failure_count": 1,
                "execution_count": 2,
                "last_outcome": "failed",
            },
            key_safe: {
                "plan_id": "v_safe",
                "success_count": 2,
                "failure_count": 0,
                "execution_count": 2,
                "last_outcome": "completed",
            },
        }

        plan = reg.derive_plan(intent, state)
        assert plan is not None
        # v_fast: 1/2 - 1*0.1 = 0.4
        # v_safe: 2/2 - 0*0.1 = 1.0
        assert plan.variant_id == "v_safe"

    def test_deterministic_exploration_across_runs(self):
        """Test 14: exploration selection is deterministic across runs."""
        reg = self._registry_with_three_variants()
        intent = _make_intent()

        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")
        state = {
            key_fast: {
                "plan_id": "v_fast",
                "success_count": 3,
                "failure_count": 0,
                "execution_count": 3,
                "last_outcome": "completed",
            },
        }
        # v_safe and v_slow are untried → "v_safe" < "v_slow"
        plans = [reg.derive_plan(intent, state) for _ in range(100)]
        variant_ids = {p.variant_id for p in plans if p is not None}
        assert len(variant_ids) == 1
        assert plans[0].variant_id == "v_safe"

    def test_no_regression_in_scoring_behavior(self):
        """Test 15: when all plans are fully sampled, scoring works as before."""
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)

        intent = _make_intent()

        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")
        key_safe = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_safe")

        state = {
            key_fast: {
                "plan_id": "v_fast",
                "success_count": 4,
                "failure_count": 1,
                "execution_count": 5,
                "last_outcome": "completed",
            },
            key_safe: {
                "plan_id": "v_safe",
                "success_count": 1,
                "failure_count": 4,
                "execution_count": 5,
                "last_outcome": "failed",
            },
        }
        # v_fast: 4/5 - 1*0.1 = 0.7
        # v_safe: 1/5 - 4*0.1 = -0.2
        plan = reg.derive_plan(intent, state)
        assert plan is not None
        assert plan.variant_id == "v_fast"

    def test_plan_switching_after_poor_performance(self):
        """Test 16: plan switching still occurs after poor performance.

        When v_fast has 5 failures and 0 successes, mutation triggers and
        generates v_fast::mut_0 (untried).  Phase 1 selects the untried
        mutation over the scored v_safe.  This proves the system moves
        away from the failing plan — via mutation, not just scoring.
        """
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)

        intent = _make_intent()

        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")
        key_safe = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_safe")

        # Both fully sampled; v_fast collapses, v_safe stable
        state = {
            key_fast: {
                "plan_id": "v_fast",
                "success_count": 0,
                "failure_count": 5,
                "execution_count": 5,
                "last_outcome": "failed",
            },
            key_safe: {
                "plan_id": "v_safe",
                "success_count": 3,
                "failure_count": 2,
                "execution_count": 5,
                "last_outcome": "completed",
            },
        }
        # v_fast triggers mutation → v_fast::mut_0 is untried → selected
        plan = reg.derive_plan(intent, state)
        assert plan is not None
        assert plan.variant_id == "v_fast::mut_0"

    def test_edge_case_high_score_vs_under_sampled(self):
        """Test 17: plan A (10 runs, high score) vs plan B (1 run) → B selected.

        This is the critical edge case that proves exploration prevents
        premature convergence. A plan with perfect score MUST still yield
        to an under-sampled competitor.
        """
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)

        intent = _make_intent()

        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")
        key_safe = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_safe")

        state = {
            key_fast: {
                "plan_id": "v_fast",
                "success_count": 10,
                "failure_count": 0,
                "execution_count": 10,
                "last_outcome": "completed",
            },
            key_safe: {
                "plan_id": "v_safe",
                "success_count": 1,
                "failure_count": 0,
                "execution_count": 1,
                "last_outcome": "completed",
            },
        }
        # v_fast: score = 1.0, execution_count = 10 (fully sampled)
        # v_safe: score = 1.0, execution_count = 1 (under-sampled)
        # → v_safe MUST be selected (under-sampled takes priority)
        plan = reg.derive_plan(intent, state)
        assert plan is not None
        assert plan.variant_id == "v_safe"

    def test_min_executions_constant_is_two(self):
        """Verify MIN_EXECUTIONS_PER_PLAN is 2 as specified."""
        assert MIN_EXECUTIONS_PER_PLAN == 2

    def test_single_variant_bypasses_exploration(self):
        """Single variant → fast path, no exploration overhead."""
        reg = PlanRegistry()
        reg.register(IntentType.LIFECYCLE_FINALIZE, _fast_finalize)
        intent = _make_intent()
        # Even with no memory, single variant is returned directly
        plan = reg.derive_plan(intent, {})
        assert plan is not None
        assert plan.variant_id == "lifecycle_finalize:default"


# ── I. Staleness Pure Function Tests ───────────────────────────────


class TestIsStalePureFunction(unittest.TestCase):
    """Tests for is_stale() and staleness_seconds() pure functions."""

    def test_none_memory_not_stale(self):
        assert is_stale(None, "2026-04-17T12:00:00+00:00") is False

    def test_empty_timestamp_not_stale(self):
        mem = {"last_executed_at": "2026-04-17T10:00:00+00:00", "execution_count": 3}
        assert is_stale(mem, "") is False

    def test_missing_last_executed_at_not_stale(self):
        mem = {"execution_count": 3}
        assert is_stale(mem, "2026-04-17T12:00:00+00:00") is False

    def test_empty_last_executed_at_not_stale(self):
        mem = {"last_executed_at": "", "execution_count": 3}
        assert is_stale(mem, "2026-04-17T12:00:00+00:00") is False

    def test_stale_after_window(self):
        # 2 hours elapsed > 1 hour window
        mem = {"last_executed_at": "2026-04-17T10:00:00+00:00", "execution_count": 3}
        assert is_stale(mem, "2026-04-17T12:00:00+00:00") is True

    def test_fresh_within_window(self):
        # 30 minutes elapsed < 1 hour window
        mem = {"last_executed_at": "2026-04-17T11:30:00+00:00", "execution_count": 3}
        assert is_stale(mem, "2026-04-17T12:00:00+00:00") is False

    def test_exactly_at_boundary_not_stale(self):
        # Exactly 3600 seconds is NOT stale (> not >=)
        mem = {"last_executed_at": "2026-04-17T11:00:00+00:00", "execution_count": 3}
        assert is_stale(mem, "2026-04-17T12:00:00+00:00") is False

    def test_one_second_past_boundary_is_stale(self):
        mem = {"last_executed_at": "2026-04-17T11:00:00+00:00", "execution_count": 3}
        assert is_stale(mem, "2026-04-17T12:00:01+00:00") is True

    def test_staleness_seconds_returns_elapsed(self):
        mem = {"last_executed_at": "2026-04-17T10:00:00+00:00"}
        # 2 hours = 7200 seconds
        assert staleness_seconds(mem, "2026-04-17T12:00:00+00:00") == 7200.0

    def test_staleness_seconds_none_memory(self):
        assert staleness_seconds(None, "2026-04-17T12:00:00+00:00") == 0.0

    def test_staleness_seconds_empty_timestamp(self):
        mem = {"last_executed_at": "2026-04-17T10:00:00+00:00"}
        assert staleness_seconds(mem, "") == 0.0

    def test_stale_window_constant_is_3600(self):
        assert STALE_WINDOW_SECONDS == 3600


class TestLastExecutedAtInMutations(unittest.TestCase):
    """Tests that last_executed_at is written by mutation builder."""

    def test_first_execution_writes_timestamp(self):
        mutations = build_plan_memory_update_mutations(
            INTENT_TYPE, GOAL_A, "v1", "completed", TIMESTAMP, {}
        )
        record = mutations[0]["value"]
        assert record["last_executed_at"] == TIMESTAMP

    def test_subsequent_execution_updates_timestamp(self):
        key = compute_plan_memory_key(INTENT_TYPE, GOAL_A, "v1")
        state = {
            key: {
                "plan_id": "v1",
                "success_count": 1,
                "failure_count": 0,
                "execution_count": 1,
                "last_outcome": "completed",
                "last_executed_at": "2026-04-17T00:00:00+00:00",
            }
        }
        new_ts = "2026-04-17T02:00:00+00:00"
        mutations = build_plan_memory_update_mutations(
            INTENT_TYPE, GOAL_A, "v1", "completed", new_ts, state
        )
        record = mutations[0]["value"]
        assert record["last_executed_at"] == new_ts

    def test_empty_plan_memory_has_last_executed_at(self):
        """Fresh plan memory record includes last_executed_at field."""
        mutations = build_plan_memory_update_mutations(
            INTENT_TYPE, GOAL_A, "v_new", "completed", TIMESTAMP, {}
        )
        record = mutations[0]["value"]
        assert "last_executed_at" in record


# ── J. Staleness Re-Exploration Policy Tests (PlanRegistry) ────────


class TestStalenessPolicy(unittest.TestCase):
    """Tests for staleness-based re-exploration in PlanRegistry.

    Validates Phase 3 in the 4-tier selection priority:
    1. Untried (execution_count == 0)
    2. Under-sampled (execution_count < MIN_EXECUTIONS_PER_PLAN)
    3. Stale (is_stale == True) — re-exploration
    4. Score-based selection
    """

    def _make_memory(
        self,
        plan_id: str,
        success: int,
        failure: int,
        last_ts: str,
    ) -> dict[str, Any]:
        """Build a plan memory record with all fields."""
        return {
            "plan_id": plan_id,
            "success_count": success,
            "failure_count": failure,
            "execution_count": success + failure,
            "last_outcome": "completed" if success > failure else "failed",
            "last_executed_at": last_ts,
        }

    def test_stale_plan_over_higher_scoring_fresh(self):
        """Test 18: stale plan selected over higher-scoring fresh plan."""
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)

        intent = _make_intent()
        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")
        key_safe = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_safe")

        now = "2026-04-17T14:00:00+00:00"
        state = {
            # v_fast: high score, fresh (30 min ago)
            key_fast: self._make_memory("v_fast", 8, 2, "2026-04-17T13:30:00+00:00"),
            # v_safe: medium score, stale (3 hours ago)
            key_safe: self._make_memory("v_safe", 3, 2, "2026-04-17T11:00:00+00:00"),
        }

        plan = reg.derive_plan(intent, state, current_timestamp=now)
        assert plan is not None
        # v_safe is stale -> selected for re-check
        assert plan.variant_id == "v_safe"

    def test_multiple_stale_most_stale_selected(self):
        """Test 19: multiple stale plans -> most stale selected."""
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_slow", _slow_finalize)

        intent = _make_intent()
        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")
        key_safe = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_safe")
        key_slow = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_slow")

        now = "2026-04-17T14:00:00+00:00"
        state = {
            # v_fast: stale 2 hours
            key_fast: self._make_memory("v_fast", 5, 0, "2026-04-17T12:00:00+00:00"),
            # v_safe: stale 5 hours (most stale)
            key_safe: self._make_memory("v_safe", 3, 2, "2026-04-17T09:00:00+00:00"),
            # v_slow: stale 3 hours
            key_slow: self._make_memory("v_slow", 2, 3, "2026-04-17T11:00:00+00:00"),
        }

        plan = reg.derive_plan(intent, state, current_timestamp=now)
        assert plan is not None
        # v_safe is most stale (5 hours) -> selected
        assert plan.variant_id == "v_safe"

    def test_no_stale_fallback_to_scoring(self):
        """Test 20: no stale plans -> fallback to scoring."""
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)

        intent = _make_intent()
        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")
        key_safe = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_safe")

        now = "2026-04-17T14:00:00+00:00"
        state = {
            # Both fresh (within last 30 minutes)
            key_fast: self._make_memory("v_fast", 5, 0, "2026-04-17T13:30:00+00:00"),
            key_safe: self._make_memory("v_safe", 2, 3, "2026-04-17T13:45:00+00:00"),
        }

        plan = reg.derive_plan(intent, state, current_timestamp=now)
        assert plan is not None
        # v_fast: 5/5 - 0*0.1 = 1.0 > v_safe: 2/5 - 3*0.1 = 0.1
        assert plan.variant_id == "v_fast"

    def test_timestamp_missing_disables_staleness(self):
        """Test 21: timestamp missing -> staleness disabled, falls to scoring."""
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)

        intent = _make_intent()
        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")
        key_safe = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_safe")

        state = {
            # v_fast: high score, would be stale if timestamp provided
            key_fast: self._make_memory("v_fast", 8, 2, "2026-04-17T08:00:00+00:00"),
            # v_safe: low score, very stale
            key_safe: self._make_memory("v_safe", 1, 4, "2026-04-17T06:00:00+00:00"),
        }

        # No timestamp -> staleness disabled -> scoring takes over
        plan = reg.derive_plan(intent, state, current_timestamp="")
        assert plan is not None
        # v_fast: 8/10 - 2*0.1 = 0.6; v_safe: 1/5 - 4*0.1 = -0.2
        assert plan.variant_id == "v_fast"

    def test_deterministic_staleness_across_runs(self):
        """Test 22: staleness selection is deterministic across runs."""
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)

        intent = _make_intent()
        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")
        key_safe = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_safe")

        now = "2026-04-17T14:00:00+00:00"
        state = {
            key_fast: self._make_memory("v_fast", 5, 0, "2026-04-17T13:30:00+00:00"),
            key_safe: self._make_memory("v_safe", 3, 2, "2026-04-17T11:00:00+00:00"),
        }

        plans = [
            reg.derive_plan(intent, state, current_timestamp=now) for _ in range(100)
        ]
        variant_ids = {p.variant_id for p in plans if p is not None}
        assert len(variant_ids) == 1
        assert plans[0].variant_id == "v_safe"

    def test_replay_identical_staleness_selection(self):
        """Test 23: replay produces identical staleness selection."""
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_slow", _slow_finalize)

        intent = _make_intent()
        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")
        key_safe = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_safe")
        key_slow = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_slow")

        now = "2026-04-17T14:00:00+00:00"
        state = {
            key_fast: self._make_memory("v_fast", 5, 0, "2026-04-17T12:00:00+00:00"),
            key_safe: self._make_memory("v_safe", 3, 2, "2026-04-17T09:00:00+00:00"),
            key_slow: self._make_memory("v_slow", 2, 3, "2026-04-17T11:00:00+00:00"),
        }

        # Run 1
        plan_1 = reg.derive_plan(intent, state, current_timestamp=now)
        # Simulate "replay" -- fresh registry, same state
        reg2 = PlanRegistry()
        reg2.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg2.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)
        reg2.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_slow", _slow_finalize)
        plan_2 = reg2.derive_plan(intent, state, current_timestamp=now)

        assert plan_1 is not None and plan_2 is not None
        assert plan_1.variant_id == plan_2.variant_id
        assert plan_1.plan_id == plan_2.plan_id

    def test_stale_plan_score_updated_after_reeval(self):
        """Test 24: stale plan re-evaluated and score updated correctly.

        Simulates: stale plan selected -> executed -> memory updated ->
        next selection uses new score.
        """
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)

        intent = _make_intent()
        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")
        key_safe = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_safe")

        t1 = "2026-04-17T14:00:00+00:00"
        state = {
            key_fast: self._make_memory("v_fast", 5, 0, "2026-04-17T13:30:00+00:00"),
            key_safe: self._make_memory("v_safe", 2, 3, "2026-04-17T11:00:00+00:00"),
        }

        # First selection: v_safe is stale -> selected
        plan = reg.derive_plan(intent, state, current_timestamp=t1)
        assert plan is not None
        assert plan.variant_id == "v_safe"

        # Simulate execution: v_safe completes, memory updated
        mutations = build_plan_memory_update_mutations(
            INTENT_TYPE, intent.goal, "v_safe", "completed", t1, state
        )
        state[key_safe] = mutations[0]["value"]

        # Second selection: v_safe no longer stale -> scoring takes over
        t2 = "2026-04-17T14:01:00+00:00"
        plan2 = reg.derive_plan(intent, state, current_timestamp=t2)
        assert plan2 is not None
        # v_fast: 5/5 - 0 = 1.0; v_safe: 3/6 - 3*0.1 = 0.2
        assert plan2.variant_id == "v_fast"

    def test_edge_high_score_stale_vs_medium_fresh(self):
        """Test 25: high-score plan A (stale 2h) vs medium-score B (fresh).

        Plan A must be selected for re-check.
        """
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)

        intent = _make_intent()
        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")
        key_safe = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_safe")

        now = "2026-04-17T14:00:00+00:00"
        state = {
            # v_fast: score 1.0, stale (2 hours ago)
            key_fast: self._make_memory("v_fast", 10, 0, "2026-04-17T12:00:00+00:00"),
            # v_safe: score 0.4, fresh (10 min ago)
            key_safe: self._make_memory("v_safe", 3, 2, "2026-04-17T13:50:00+00:00"),
        }

        plan = reg.derive_plan(intent, state, current_timestamp=now)
        assert plan is not None
        # v_fast is stale -> selected for re-check
        assert plan.variant_id == "v_fast"

    def test_stale_tiebreak_lexicographic(self):
        """Stale plans with identical staleness -> lexicographic tiebreak."""
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_alpha", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_beta", _safe_finalize)

        intent = _make_intent()
        key_a = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_alpha")
        key_b = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_beta")

        now = "2026-04-17T14:00:00+00:00"
        # Both stale by exactly 2 hours
        state = {
            key_a: self._make_memory("v_alpha", 3, 2, "2026-04-17T12:00:00+00:00"),
            key_b: self._make_memory("v_beta", 3, 2, "2026-04-17T12:00:00+00:00"),
        }

        plan = reg.derive_plan(intent, state, current_timestamp=now)
        assert plan is not None
        assert plan.variant_id == "v_alpha"  # "v_alpha" < "v_beta"

    def test_untried_still_beats_stale(self):
        """Untried (Phase 1) takes priority over stale (Phase 3)."""
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)

        intent = _make_intent()
        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")

        now = "2026-04-17T14:00:00+00:00"
        state = {
            # v_fast: stale (2 hours ago)
            key_fast: self._make_memory("v_fast", 5, 0, "2026-04-17T12:00:00+00:00"),
            # v_safe: no memory (untried)
        }

        plan = reg.derive_plan(intent, state, current_timestamp=now)
        assert plan is not None
        # Untried beats stale
        assert plan.variant_id == "v_safe"

    def test_default_timestamp_does_not_break_existing_callers(self):
        """Existing callers without timestamp continue to work."""
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)

        intent = _make_intent()
        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")
        key_safe = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_safe")

        state = {
            key_fast: self._make_memory("v_fast", 5, 0, "2026-04-17T12:00:00+00:00"),
            key_safe: self._make_memory("v_safe", 2, 3, "2026-04-17T11:00:00+00:00"),
        }

        # No current_timestamp arg -> staleness disabled -> scoring
        plan = reg.derive_plan(intent, state)
        assert plan is not None
        # v_fast: 1.0; v_safe: 0.1
        assert plan.variant_id == "v_fast"


# ── H. Context-Aware Staleness Tests ────────────────────────────────


class TestContextAwareStaleness(unittest.TestCase):
    """Context-aware staleness: re-evaluate only when time-stale AND state changed.

    Tests:
    26. Stale + same state signature → NOT stale (environment unchanged).
    27. Stale + changed state signature → stale (environment changed).
    28. Fresh + changed state → NOT stale (time threshold not met).
    29. Missing last_state_signature → fallback to time-only staleness.
    30. Missing current_state_signature → fallback to time-only staleness.
    31. Deterministic signature: same state → same hash across calls.
    32. Replay produces identical staleness decisions.
    33. State signature stored in plan memory on mutation.
    34. Empty state → empty signature.
    35. Signature ignores irrelevant keys.
    36. End-to-end: registry skips stale re-exploration when state unchanged.
    37. End-to-end: registry triggers stale re-exploration when state changed.
    38. Backward compat: old memory records (no signature) still work.
    """

    def _make_memory(
        self,
        plan_id: str,
        success: int,
        failure: int,
        last_ts: str,
        last_sig: str = "",
    ) -> dict[str, Any]:
        """Build a plan memory record with state signature."""
        return {
            "plan_id": plan_id,
            "success_count": success,
            "failure_count": failure,
            "execution_count": success + failure,
            "last_outcome": "completed" if success > failure else "failed",
            "last_executed_at": last_ts,
            "last_state_signature": last_sig,
        }

    # ── compute_state_signature ─────────────────────────────────────

    def test_deterministic_signature(self):
        """Test 31: same state produces same signature across calls."""
        from umh.substrate.plan_scoring import compute_state_signature

        state = {
            "intent:abc": {"status": "active"},
            "active_intent.abc": True,
            "lifecycle.phase": "running",
        }
        sig1 = compute_state_signature(state)
        sig2 = compute_state_signature(state)
        assert sig1 == sig2
        assert len(sig1) == 16  # truncated SHA-256

    def test_empty_state_empty_signature(self):
        """Test 34: state with no relevant keys → empty string."""
        from umh.substrate.plan_scoring import compute_state_signature

        assert compute_state_signature({}) == ""
        assert compute_state_signature({"unrelated_key": 42}) == ""

    def test_signature_ignores_irrelevant_keys(self):
        """Test 35: only plan-relevant prefixes contribute to signature."""
        from umh.substrate.plan_scoring import compute_state_signature

        base = {"intent:x": {"status": "active"}}
        with_noise = {**base, "log_entry": "some noise", "counter": 99}
        assert compute_state_signature(base) == compute_state_signature(with_noise)

    def test_signature_changes_on_relevant_state_change(self):
        """Relevant state change → different signature."""
        from umh.substrate.plan_scoring import compute_state_signature

        state_a = {"intent:x": {"status": "active"}}
        state_b = {"intent:x": {"status": "completed"}}
        assert compute_state_signature(state_a) != compute_state_signature(state_b)

    def test_signature_stable_for_equivalent_state(self):
        """Same keys/values in different insertion order → same signature."""
        from umh.substrate.plan_scoring import compute_state_signature

        state_a = {"intent:b": 2, "intent:a": 1}
        state_b = {"intent:a": 1, "intent:b": 2}
        assert compute_state_signature(state_a) == compute_state_signature(state_b)

    # ── is_stale with context-aware logic ───────────────────────────

    def test_stale_time_same_state_not_stale(self):
        """Test 26: time-stale + same signature → NOT stale."""
        sig = "abcdef1234567890"
        mem = self._make_memory(
            "plan_a",
            3,
            0,
            "2026-04-17T12:00:00+00:00",
            last_sig=sig,
        )
        now = "2026-04-17T14:00:00+00:00"  # 2 hours later
        assert not is_stale(mem, now, current_state_signature=sig)

    def test_stale_time_changed_state_is_stale(self):
        """Test 27: time-stale + different signature → stale."""
        mem = self._make_memory(
            "plan_a",
            3,
            0,
            "2026-04-17T12:00:00+00:00",
            last_sig="old_sig_1234567",
        )
        now = "2026-04-17T14:00:00+00:00"
        assert is_stale(mem, now, current_state_signature="new_sig_9876543")

    def test_fresh_changed_state_not_stale(self):
        """Test 28: fresh time + changed state → NOT stale."""
        mem = self._make_memory(
            "plan_a",
            3,
            0,
            "2026-04-17T13:50:00+00:00",
            last_sig="old_sig_1234567",
        )
        now = "2026-04-17T14:00:00+00:00"  # only 10 min
        assert not is_stale(mem, now, current_state_signature="new_sig_9876543")

    def test_missing_last_signature_fallback(self):
        """Test 29: no last_state_signature in memory → time-only (stale)."""
        mem = self._make_memory("plan_a", 3, 0, "2026-04-17T12:00:00+00:00")
        # No last_state_signature field at all
        mem.pop("last_state_signature", None)
        now = "2026-04-17T14:00:00+00:00"
        # Falls back to time-only → stale
        assert is_stale(mem, now, current_state_signature="any_sig_12345")

    def test_missing_current_signature_fallback(self):
        """Test 30: empty current_state_signature → time-only (stale)."""
        mem = self._make_memory(
            "plan_a",
            3,
            0,
            "2026-04-17T12:00:00+00:00",
            last_sig="stored_sig",
        )
        now = "2026-04-17T14:00:00+00:00"
        # current_state_signature="" → fallback to time-only → stale
        assert is_stale(mem, now, current_state_signature="")

    def test_empty_last_sig_fallback(self):
        """last_state_signature="" in memory → time-only fallback."""
        mem = self._make_memory(
            "plan_a",
            3,
            0,
            "2026-04-17T12:00:00+00:00",
            last_sig="",
        )
        now = "2026-04-17T14:00:00+00:00"
        assert is_stale(mem, now, current_state_signature="some_sig_1234")

    # ── Replay determinism ──────────────────────────────────────────

    def test_replay_identical_results(self):
        """Test 32: replay produces identical staleness decisions."""
        sig = "abcdef1234567890"
        mem = self._make_memory(
            "plan_a",
            3,
            0,
            "2026-04-17T12:00:00+00:00",
            last_sig=sig,
        )
        now = "2026-04-17T14:00:00+00:00"

        results = [is_stale(mem, now, current_state_signature=sig) for _ in range(100)]
        assert all(r is False for r in results)

        results_changed = [
            is_stale(mem, now, current_state_signature="changed_sig_123")
            for _ in range(100)
        ]
        assert all(r is True for r in results_changed)

    # ── Plan memory mutation stores signature ───────────────────────

    def test_mutation_stores_state_signature(self):
        """Test 33: build_plan_memory_update_mutations stores signature."""
        state: dict[str, Any] = {}
        mutations = build_plan_memory_update_mutations(
            intent_type=INTENT_TYPE,
            goal=GOAL_A,
            plan_id="plan_x",
            outcome="completed",
            timestamp="2026-04-17T14:00:00+00:00",
            state=state,
            state_signature="sig_from_execution",
        )
        assert len(mutations) == 1
        record = mutations[0]["value"]
        assert record["last_state_signature"] == "sig_from_execution"

    def test_mutation_preserves_existing_signature_when_empty(self):
        """When state_signature="" is passed, preserve existing."""
        key = compute_plan_memory_key(INTENT_TYPE, GOAL_A, "plan_x")
        state = {
            key: self._make_memory(
                "plan_x",
                1,
                0,
                "2026-04-17T12:00:00+00:00",
                last_sig="old_sig",
            )
        }
        mutations = build_plan_memory_update_mutations(
            intent_type=INTENT_TYPE,
            goal=GOAL_A,
            plan_id="plan_x",
            outcome="completed",
            timestamp="2026-04-17T14:00:00+00:00",
            state=state,
            state_signature="",
        )
        record = mutations[0]["value"]
        assert record["last_state_signature"] == "old_sig"

    def test_mutation_backward_compat_no_sig_arg(self):
        """Calling without state_signature arg still works (default "")."""
        state: dict[str, Any] = {}
        mutations = build_plan_memory_update_mutations(
            intent_type=INTENT_TYPE,
            goal=GOAL_A,
            plan_id="plan_x",
            outcome="completed",
            timestamp="2026-04-17T14:00:00+00:00",
            state=state,
        )
        record = mutations[0]["value"]
        assert record["last_state_signature"] == ""

    # ── End-to-end: registry integration ────────────────────────────

    def test_registry_skips_stale_when_state_unchanged(self):
        """Test 36: stale by time but state unchanged → scoring, not re-exploration."""
        from umh.substrate.plan_scoring import compute_state_signature

        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)

        intent = _make_intent()
        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")
        key_safe = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_safe")

        # Build state with plan-relevant keys so signature is non-empty
        base_state = {
            "intent:test123": {"status": "active"},
            "lifecycle.phase": "running",
        }
        sig = compute_state_signature(base_state)

        now = "2026-04-17T14:00:00+00:00"
        state = {
            **base_state,
            # v_fast: score 1.0, stale (2 hours), but SAME state signature
            key_fast: self._make_memory(
                "v_fast",
                10,
                0,
                "2026-04-17T12:00:00+00:00",
                last_sig=sig,
            ),
            # v_safe: score 0.4, fresh
            key_safe: self._make_memory(
                "v_safe",
                3,
                2,
                "2026-04-17T13:50:00+00:00",
                last_sig=sig,
            ),
        }

        plan = reg.derive_plan(intent, state, current_timestamp=now)
        assert plan is not None
        # v_fast is time-stale but state unchanged → NOT re-explored.
        # Falls through to scoring: v_fast=1.0 > v_safe=0.2 → v_fast wins.
        assert plan.variant_id == "v_fast"

    def test_registry_triggers_stale_when_state_changed(self):
        """Test 37: stale by time AND state changed → re-exploration fires."""
        from umh.substrate.plan_scoring import compute_state_signature

        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)

        intent = _make_intent()
        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")
        key_safe = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_safe")

        now = "2026-04-17T14:00:00+00:00"
        # State has CHANGED since plans were last executed
        current_state = {
            "intent:test123": {"status": "completed"},  # changed!
            "lifecycle.phase": "finalizing",
        }
        old_sig = "old_signature_abcd"

        state = {
            **current_state,
            # v_safe: lower score, but stale AND state changed
            key_safe: self._make_memory(
                "v_safe",
                2,
                3,
                "2026-04-17T11:00:00+00:00",
                last_sig=old_sig,
            ),
            # v_fast: higher score, fresh
            key_fast: self._make_memory(
                "v_fast",
                8,
                2,
                "2026-04-17T13:50:00+00:00",
                last_sig=old_sig,
            ),
        }

        plan = reg.derive_plan(intent, state, current_timestamp=now)
        assert plan is not None
        # v_safe is time-stale AND state changed → re-explored
        assert plan.variant_id == "v_safe"

    def test_backward_compat_old_records_no_signature(self):
        """Test 38: old records without last_state_signature → time-only fallback."""
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)

        intent = _make_intent()
        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")
        key_safe = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_safe")

        now = "2026-04-17T14:00:00+00:00"
        # Old-style records without last_state_signature field
        state = {
            "intent:test": {"status": "active"},
            key_safe: {
                "plan_id": "v_safe",
                "success_count": 2,
                "failure_count": 3,
                "execution_count": 5,
                "last_outcome": "failed",
                "last_executed_at": "2026-04-17T11:00:00+00:00",
                # No last_state_signature key at all
            },
            key_fast: {
                "plan_id": "v_fast",
                "success_count": 8,
                "failure_count": 2,
                "execution_count": 10,
                "last_outcome": "completed",
                "last_executed_at": "2026-04-17T13:50:00+00:00",
                # No last_state_signature key at all
            },
        }

        plan = reg.derive_plan(intent, state, current_timestamp=now)
        assert plan is not None
        # v_safe has no stored signature → fallback to time-only → stale
        assert plan.variant_id == "v_safe"


# ── I. Deterministic Plan Mutation Tests ────────────────────────────


class TestPlanMutation(unittest.TestCase):
    """Deterministic plan mutation: structured strategy space search.

    Tests:
    39. Mutation triggers only on repeated failure (>= threshold, 0 successes).
    40. Mutated variant_id follows format {parent}::mut_{n}.
    41. Same inputs → same mutation (deterministic transform selection).
    42. Mutated plan enters exploration phase (untried, execution_count 0).
    43. Mutation limit enforced (MAX_MUTATIONS_PER_PLAN = 2).
    44. Original plan steps not modified by mutation.
    45. Replay produces identical mutated variants.
    46. No mutation when success_count > 0 (even with high failure_count).
    47. No mutation when failure_count < threshold.
    48. Mutation transforms produce valid step sequences.
    49. No mutation chains (mutated variants don't spawn further mutations).
    50. End-to-end: mutation → exploration → scoring lifecycle.
    """

    # ── Unit tests: plan_mutation module ────────────────────────────

    def test_should_mutate_threshold(self):
        """Test 39: mutation triggers only on repeated failure."""
        from umh.substrate.plan_mutation import MUTATION_THRESHOLD, should_mutate

        # Below threshold → no mutation
        mem = {"failure_count": MUTATION_THRESHOLD - 1, "success_count": 0}
        assert not should_mutate(mem)

        # At threshold → mutation
        mem = {"failure_count": MUTATION_THRESHOLD, "success_count": 0}
        assert should_mutate(mem)

        # Above threshold → mutation
        mem = {"failure_count": MUTATION_THRESHOLD + 5, "success_count": 0}
        assert should_mutate(mem)

    def test_no_mutation_with_successes(self):
        """Test 46: no mutation when success_count > 0."""
        from umh.substrate.plan_mutation import should_mutate

        mem = {"failure_count": 10, "success_count": 1}
        assert not should_mutate(mem)

    def test_no_mutation_below_threshold(self):
        """Test 47: no mutation when failure_count < threshold."""
        from umh.substrate.plan_mutation import should_mutate

        mem = {"failure_count": 2, "success_count": 0}
        assert not should_mutate(mem)

    def test_no_mutation_none_memory(self):
        """Untried plans (None memory) do not trigger mutation."""
        from umh.substrate.plan_mutation import should_mutate

        assert not should_mutate(None)

    def test_variant_id_format(self):
        """Test 40: mutated variant_id follows format."""
        from umh.substrate.plan_mutation import build_mutated_variant_id

        assert build_mutated_variant_id("v_fast", 0) == "v_fast::mut_0"
        assert build_mutated_variant_id("v_fast", 1) == "v_fast::mut_1"
        assert build_mutated_variant_id("a:default", 0) == "a:default::mut_0"

    def test_is_mutated_variant(self):
        """Detect mutated variants correctly."""
        from umh.substrate.plan_mutation import is_mutated_variant

        assert not is_mutated_variant("v_fast")
        assert not is_mutated_variant("lifecycle_finalize:default")
        assert is_mutated_variant("v_fast::mut_0")
        assert is_mutated_variant("v_fast::mut_1")

    def test_get_parent_variant_id(self):
        """Extract parent from mutated variant_id."""
        from umh.substrate.plan_mutation import get_parent_variant_id

        assert get_parent_variant_id("v_fast::mut_0") == "v_fast"
        assert get_parent_variant_id("v_fast") == "v_fast"
        assert get_parent_variant_id("a:b::mut_1") == "a:b"

    def test_count_existing_mutations(self):
        """Count mutations for a given parent."""
        from umh.substrate.plan_mutation import count_existing_mutations

        vids = ["v_fast", "v_safe", "v_fast::mut_0", "v_fast::mut_1", "v_safe::mut_0"]
        assert count_existing_mutations(vids, "v_fast") == 2
        assert count_existing_mutations(vids, "v_safe") == 1
        assert count_existing_mutations(vids, "v_slow") == 0

    def test_deterministic_mutation(self):
        """Test 41: same inputs → same mutation across calls."""
        from umh.substrate.plan_mutation import mutate_plan_steps

        steps = (
            PlanStep(step_index=0, event_type="pre_check", payload={}),
            PlanStep(step_index=1, event_type="validate", payload={}),
            PlanStep(step_index=2, event_type="finalize", payload={}),
        )
        goal = {"session_name": "s1"}

        # Same call 100 times → same result
        results = [
            mutate_plan_steps(steps, "lifecycle_finalize", goal, 0) for _ in range(100)
        ]
        first = results[0]
        assert all(r == first for r in results)

    def test_different_mutation_indices_differ(self):
        """Different mutation_index values may produce different transforms."""
        from umh.substrate.plan_mutation import mutate_plan_steps

        steps = (
            PlanStep(step_index=0, event_type="pre_check", payload={}),
            PlanStep(step_index=1, event_type="validate", payload={}),
            PlanStep(step_index=2, event_type="finalize", payload={}),
        )
        goal = {"session_name": "s1"}

        mut_0 = mutate_plan_steps(steps, "lifecycle_finalize", goal, 0)
        mut_1 = mutate_plan_steps(steps, "lifecycle_finalize", goal, 1)
        # They should be valid step sequences regardless
        assert len(mut_0) > 0
        assert len(mut_1) > 0
        # step_index values are correct
        for i, s in enumerate(mut_0):
            assert s.step_index == i
        for i, s in enumerate(mut_1):
            assert s.step_index == i

    def test_original_steps_not_modified(self):
        """Test 44: original plan steps are not modified by mutation."""
        from umh.substrate.plan_mutation import mutate_plan_steps

        original = (
            PlanStep(step_index=0, event_type="pre_check", payload={}),
            PlanStep(step_index=1, event_type="validate", payload={}),
            PlanStep(step_index=2, event_type="finalize", payload={}),
        )
        # Save copies of original event_types
        original_events = [s.event_type for s in original]

        _ = mutate_plan_steps(original, "lifecycle_finalize", {"s": "1"}, 0)
        _ = mutate_plan_steps(original, "lifecycle_finalize", {"s": "1"}, 1)

        # Original unchanged
        assert [s.event_type for s in original] == original_events
        assert [s.step_index for s in original] == [0, 1, 2]

    def test_transforms_produce_valid_sequences(self):
        """Test 48: all 4 transforms produce valid step sequences."""
        from umh.substrate.plan_mutation import (
            _transform_drop_last,
            _transform_duplicate_first,
            _transform_reverse,
            _transform_rotate,
        )

        steps = (
            PlanStep(step_index=0, event_type="a", payload={}),
            PlanStep(step_index=1, event_type="b", payload={}),
            PlanStep(step_index=2, event_type="c", payload={}),
        )

        for transform in [
            _transform_reverse,
            _transform_rotate,
            _transform_drop_last,
            _transform_duplicate_first,
        ]:
            result = transform(steps)
            assert len(result) > 0
            # step_index values are contiguous 0..n
            for i, s in enumerate(result):
                assert s.step_index == i

    def test_transform_reverse(self):
        """Reverse: a,b,c → c,b,a."""
        from umh.substrate.plan_mutation import _transform_reverse

        steps = (
            PlanStep(step_index=0, event_type="a", payload={}),
            PlanStep(step_index=1, event_type="b", payload={}),
            PlanStep(step_index=2, event_type="c", payload={}),
        )
        result = _transform_reverse(steps)
        assert [s.event_type for s in result] == ["c", "b", "a"]
        assert [s.step_index for s in result] == [0, 1, 2]

    def test_transform_rotate(self):
        """Rotate: a,b,c → b,c,a."""
        from umh.substrate.plan_mutation import _transform_rotate

        steps = (
            PlanStep(step_index=0, event_type="a", payload={}),
            PlanStep(step_index=1, event_type="b", payload={}),
            PlanStep(step_index=2, event_type="c", payload={}),
        )
        result = _transform_rotate(steps)
        assert [s.event_type for s in result] == ["b", "c", "a"]

    def test_transform_drop_last(self):
        """Drop last: a,b,c → a,b."""
        from umh.substrate.plan_mutation import _transform_drop_last

        steps = (
            PlanStep(step_index=0, event_type="a", payload={}),
            PlanStep(step_index=1, event_type="b", payload={}),
            PlanStep(step_index=2, event_type="c", payload={}),
        )
        result = _transform_drop_last(steps)
        assert [s.event_type for s in result] == ["a", "b"]

    def test_transform_drop_last_single_step_noop(self):
        """Drop last on 1 step → unchanged (cannot remove only step)."""
        from umh.substrate.plan_mutation import _transform_drop_last

        steps = (PlanStep(step_index=0, event_type="a", payload={}),)
        result = _transform_drop_last(steps)
        assert len(result) == 1
        assert result[0].event_type == "a"

    def test_transform_duplicate_first(self):
        """Duplicate first: a,b,c → a,a,b,c."""
        from umh.substrate.plan_mutation import _transform_duplicate_first

        steps = (
            PlanStep(step_index=0, event_type="a", payload={}),
            PlanStep(step_index=1, event_type="b", payload={}),
            PlanStep(step_index=2, event_type="c", payload={}),
        )
        result = _transform_duplicate_first(steps)
        assert [s.event_type for s in result] == ["a", "a", "b", "c"]
        assert [s.step_index for s in result] == [0, 1, 2, 3]

    # ── Integration tests: registry + mutation ──────────────────────

    def test_mutation_enters_exploration_phase(self):
        """Test 42: mutated plan enters Phase 1 (untried, execution_count 0)."""
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)

        intent = _make_intent()
        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")
        key_safe = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_safe")

        state = {
            key_fast: {
                "plan_id": "v_fast",
                "success_count": 0,
                "failure_count": 5,
                "execution_count": 5,
                "last_outcome": "failed",
            },
            key_safe: {
                "plan_id": "v_safe",
                "success_count": 3,
                "failure_count": 2,
                "execution_count": 5,
                "last_outcome": "completed",
            },
        }

        plan = reg.derive_plan(intent, state)
        assert plan is not None
        # Mutated variant is untried → selected by Phase 1 (exploration)
        assert plan.variant_id == "v_fast::mut_0"

    def test_mutation_limit_enforced(self):
        """Test 43: MAX_MUTATIONS_PER_PLAN = 2 prevents variant explosion.

        Mutation runs inside the multi-variant selection path, so at least
        2 variants must be registered to activate it.
        """
        from umh.substrate.plan_mutation import MAX_MUTATIONS_PER_PLAN

        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)

        intent = _make_intent()
        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")
        key_safe = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_safe")
        key_mut0 = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast::mut_0")
        key_mut1 = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast::mut_1")

        # First call: v_fast has enough failures → generates mut_0 and mut_1
        state = {
            key_fast: {
                "plan_id": "v_fast",
                "success_count": 0,
                "failure_count": 5,
                "execution_count": 5,
                "last_outcome": "failed",
            },
            key_safe: {
                "plan_id": "v_safe",
                "success_count": 3,
                "failure_count": 2,
                "execution_count": 5,
                "last_outcome": "completed",
            },
        }
        plan = reg.derive_plan(intent, state)
        assert plan is not None

        # Verify exactly MAX_MUTATIONS_PER_PLAN mutations were generated
        variant_ids = reg.get_variant_ids(IntentType.LIFECYCLE_FINALIZE)
        mutation_ids = [v for v in variant_ids if "::mut_" in v]
        assert len(mutation_ids) == MAX_MUTATIONS_PER_PLAN

        # Second call with mutations also failed: no more mutations generated
        state_with_mut_failures = {
            key_fast: {
                "plan_id": "v_fast",
                "success_count": 0,
                "failure_count": 10,
                "execution_count": 10,
                "last_outcome": "failed",
            },
            key_safe: {
                "plan_id": "v_safe",
                "success_count": 3,
                "failure_count": 2,
                "execution_count": 5,
                "last_outcome": "completed",
            },
            key_mut0: {
                "plan_id": "v_fast::mut_0",
                "success_count": 0,
                "failure_count": 5,
                "execution_count": 5,
                "last_outcome": "failed",
            },
            key_mut1: {
                "plan_id": "v_fast::mut_1",
                "success_count": 0,
                "failure_count": 5,
                "execution_count": 5,
                "last_outcome": "failed",
            },
        }
        plan2 = reg.derive_plan(intent, state_with_mut_failures)
        assert plan2 is not None
        # Still only MAX_MUTATIONS_PER_PLAN mutations (no new ones)
        variant_ids2 = reg.get_variant_ids(IntentType.LIFECYCLE_FINALIZE)
        mutation_ids2 = [v for v in variant_ids2 if "::mut_" in v]
        assert len(mutation_ids2) == MAX_MUTATIONS_PER_PLAN

    def test_no_mutation_chains(self):
        """Test 49: mutated variants do not spawn further mutations."""
        from umh.substrate.plan_mutation import MAX_MUTATIONS_PER_PLAN

        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)

        intent = _make_intent()
        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")
        key_mut0 = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast::mut_0")

        # v_fast triggers mutation
        state = {
            key_fast: {
                "plan_id": "v_fast",
                "success_count": 0,
                "failure_count": 5,
                "execution_count": 5,
                "last_outcome": "failed",
            },
            # v_fast::mut_0 also fails repeatedly — should NOT spawn mut_0::mut_0
            key_mut0: {
                "plan_id": "v_fast::mut_0",
                "success_count": 0,
                "failure_count": 5,
                "execution_count": 5,
                "last_outcome": "failed",
            },
        }
        plan = reg.derive_plan(intent, state)
        assert plan is not None

        variant_ids = reg.get_variant_ids(IntentType.LIFECYCLE_FINALIZE)
        # No double-mutation IDs like v_fast::mut_0::mut_0
        chain_mutations = [v for v in variant_ids if v.count("::mut_") > 1]
        assert len(chain_mutations) == 0

    def test_replay_identical_mutations(self):
        """Test 45: replay produces identical mutated variants."""
        results = []
        for _ in range(20):
            reg = PlanRegistry()
            reg.register_variant(
                IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize
            )

            intent = _make_intent()
            key = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_safe")
            state = {
                key: {
                    "plan_id": "v_safe",
                    "success_count": 0,
                    "failure_count": 5,
                    "execution_count": 5,
                    "last_outcome": "failed",
                },
            }
            plan = reg.derive_plan(intent, state)
            assert plan is not None
            results.append((plan.variant_id, plan.plan_id))

        # All 20 runs produce identical results
        assert len(set(results)) == 1

    def test_end_to_end_mutation_lifecycle(self):
        """Test 50: mutation → exploration → scoring lifecycle.

        Simulates: parent fails → mutation generated → mutation tried →
        mutation fails → scoring falls back to remaining options.
        """
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)

        intent = _make_intent()
        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")
        key_safe = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_safe")
        key_mut0 = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast::mut_0")
        key_mut1 = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast::mut_1")

        # Step 1: v_fast fails repeatedly → mutation triggers
        state_step1 = {
            key_fast: {
                "plan_id": "v_fast",
                "success_count": 0,
                "failure_count": 5,
                "execution_count": 5,
                "last_outcome": "failed",
            },
            key_safe: {
                "plan_id": "v_safe",
                "success_count": 4,
                "failure_count": 1,
                "execution_count": 5,
                "last_outcome": "completed",
            },
        }
        plan1 = reg.derive_plan(intent, state_step1)
        assert plan1 is not None
        assert plan1.variant_id == "v_fast::mut_0"  # untried mutation

        # Step 2: mut_0 tried but also fails → mut_1 is next untried
        state_step2 = {
            **state_step1,
            key_mut0: {
                "plan_id": "v_fast::mut_0",
                "success_count": 0,
                "failure_count": 2,
                "execution_count": 2,
                "last_outcome": "failed",
            },
        }
        plan2 = reg.derive_plan(intent, state_step2)
        assert plan2 is not None
        assert plan2.variant_id == "v_fast::mut_1"  # next untried mutation

        # Step 3: both mutations fully tried and failed → scoring takes over
        state_step3 = {
            **state_step1,
            key_mut0: {
                "plan_id": "v_fast::mut_0",
                "success_count": 0,
                "failure_count": 3,
                "execution_count": 3,
                "last_outcome": "failed",
            },
            key_mut1: {
                "plan_id": "v_fast::mut_1",
                "success_count": 0,
                "failure_count": 3,
                "execution_count": 3,
                "last_outcome": "failed",
            },
        }
        plan3 = reg.derive_plan(intent, state_step3)
        assert plan3 is not None
        # v_safe has highest score: 4/5 - 1*0.1 = 0.7
        assert plan3.variant_id == "v_safe"

    def test_no_mutation_on_success(self):
        """Plans with at least one success do not trigger mutation."""
        reg = PlanRegistry()
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_fast", _fast_finalize)
        reg.register_variant(IntentType.LIFECYCLE_FINALIZE, "v_safe", _safe_finalize)

        intent = _make_intent()
        key_fast = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_fast")
        key_safe = compute_plan_memory_key(INTENT_TYPE, intent.goal, "v_safe")

        state = {
            key_fast: {
                "plan_id": "v_fast",
                "success_count": 1,
                "failure_count": 10,
                "execution_count": 11,
                "last_outcome": "failed",
            },
            key_safe: {
                "plan_id": "v_safe",
                "success_count": 5,
                "failure_count": 0,
                "execution_count": 5,
                "last_outcome": "completed",
            },
        }
        plan = reg.derive_plan(intent, state)
        assert plan is not None
        # No mutations generated — both have successes
        variant_ids = reg.get_variant_ids(IntentType.LIFECYCLE_FINALIZE)
        assert not any("::mut_" in v for v in variant_ids)
        # v_safe wins by score: 5/5 - 0 = 1.0 vs v_fast: 1/11 - 10*0.1 ≈ -0.91
        assert plan.variant_id == "v_safe"


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
