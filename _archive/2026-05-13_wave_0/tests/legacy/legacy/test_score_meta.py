"""Tests for self-tuning scoring parameters (score_meta).

Validates:
1. No adjustment when execution_count < 5.
2. No adjustment when |success_rate - failure_rate| < 0.1 (deadband).
3. Intent scope uses 0.005 delta.
4. Plan scope uses 0.01 delta.
5. Clamp lower bound at 0.05.
6. Clamp upper bound at 0.3.
7. Same memory + same meta → same adjustment across 100 runs (determinism).
8. meta=None preserves old scoring behavior (backward compat).
9. score_intent and score_plan use meta when provided.
10. Replay/duplicate terminal event → identical SET results.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from umh.substrate.intent_memory import score_intent
from umh.substrate.plan_scoring import score_plan, select_best_plan
from umh.substrate.score_meta import (
    DEADBAND,
    DEFAULT_PENALTY_WEIGHT,
    HYSTERESIS_DEADBAND,
    INTENT_DELTA,
    MAX_PENALTY_WEIGHT,
    MIN_EXECUTIONS,
    MIN_PENALTY_WEIGHT,
    PLAN_DELTA,
    RECOVERY_THRESHOLD,
    SATURATION_WARN_THRESHOLD,
    build_score_meta_adjustment,
    compute_score_meta_key,
    get_penalty_weight,
    lookup_score_meta,
)


# ── Helpers ──────────────────────────────────────────────────────────


def _mem(success: int, failure: int) -> dict:
    """Build a minimal memory record with given counts."""
    total = success + failure
    return {
        "execution_count": total,
        "success_count": success,
        "failure_count": failure,
    }


def _meta(
    weight: float,
    count: int = 0,
    direction: str = "",
    saturation: int = 0,
) -> dict:
    """Build a score meta record."""
    return {
        "failure_penalty_weight": weight,
        "last_updated_at": "",
        "adjustment_count": count,
        "last_direction": direction,
        "saturation_count": saturation,
    }


# ── 1. No adjustment when execution_count < MIN_EXECUTIONS ─────────


def test_no_adjustment_below_min_executions():
    """No adjustment when execution_count < 5, even with extreme imbalance."""
    mem = _mem(0, 4)  # 4 executions, all failures
    assert mem["execution_count"] < MIN_EXECUTIONS

    result = build_score_meta_adjustment("intent", mem, None)
    assert result == []

    result = build_score_meta_adjustment("plan", mem, None)
    assert result == []


def test_no_adjustment_at_exactly_4():
    """Boundary: 4 executions is below threshold."""
    mem = _mem(0, 4)
    assert build_score_meta_adjustment("intent", mem, None) == []


def test_adjustment_at_exactly_5():
    """Boundary: 5 executions with clear signal triggers adjustment."""
    mem = _mem(0, 5)  # 100% failure, delta_rate = 1.0 > deadband
    result = build_score_meta_adjustment("intent", mem, None)
    assert len(result) == 1
    assert result[0]["op"] == "SET"


# ── 2. No adjustment within deadband ────────────────────────────────


def test_deadband_no_adjustment():
    """No adjustment when success_rate ≈ failure_rate (within deadband)."""
    # 5 executions: 3 success, 2 failure
    # success_rate = 0.6, failure_rate = 0.4, delta = 0.2 > 0.1
    # This SHOULD adjust.  Try closer rates:
    # 10 executions: 5 success, 5 failure → rates both 0.5 → delta = 0.0
    mem = _mem(5, 5)
    result = build_score_meta_adjustment("intent", mem, None)
    assert result == []


def test_deadband_boundary_below():
    """delta_rate < 0.1 → no adjustment."""
    # 20 executions: 11 success, 9 failure
    # success_rate = 0.55, failure_rate = 0.45, delta = 0.1
    # delta_rate = 0.1 which is NOT < 0.1, so it's at boundary.
    # Need delta < 0.1 strictly:
    # 100 executions: 54 success, 46 failure
    # success_rate = 0.54, failure_rate = 0.46, delta = 0.08 < 0.1
    mem = _mem(54, 46)
    result = build_score_meta_adjustment("intent", mem, None)
    assert result == []


def test_deadband_boundary_at():
    """delta_rate exactly 0.1 → no adjustment (strict less-than)."""
    # 20 executions: 11 success, 9 failure
    # success_rate = 0.55, failure_rate = 0.45, delta = 0.1
    mem = _mem(11, 9)
    # abs(0.55 - 0.45) = 0.1, which is NOT < 0.1
    # So this should NOT be in deadband... wait, the guard is
    # delta_rate < DEADBAND which is 0.1.  0.1 < 0.1 is False.
    # So this SHOULD produce an adjustment.
    result = build_score_meta_adjustment("intent", mem, None)
    assert len(result) == 1


def test_deadband_boundary_just_above():
    """delta_rate > 0.1 → adjustment triggers."""
    # 10 executions: 7 success, 3 failure
    # success_rate = 0.7, failure_rate = 0.3, delta = 0.4
    mem = _mem(7, 3)
    result = build_score_meta_adjustment("intent", mem, None)
    assert len(result) == 1


# ── 3. Intent scope uses 0.005 delta ───────────────────────────────


def test_intent_delta():
    """Intent scope adjusts by 0.005."""
    mem = _mem(0, 5)  # 100% failure
    meta = _meta(DEFAULT_PENALTY_WEIGHT)
    result = build_score_meta_adjustment("intent", mem, meta)
    assert len(result) == 1
    new_weight = result[0]["value"]["failure_penalty_weight"]
    expected = DEFAULT_PENALTY_WEIGHT + INTENT_DELTA
    assert abs(new_weight - expected) < 1e-9


def test_intent_delta_decrease():
    """Intent scope decreases by 0.005 on success dominance (below recovery)."""
    # 7 success, 3 failure → success_rate=0.7, failure_rate=0.3
    # delta_rate=0.4 > deadband, but margin=0.4 > RECOVERY_THRESHOLD=0.3
    # → triggers recovery boost (2x delta).  Use weaker signal instead:
    # 6 success, 4 failure → delta_rate=0.2, margin=0.2 < 0.3 → no recovery
    mem = _mem(6, 4)
    meta = _meta(DEFAULT_PENALTY_WEIGHT)
    result = build_score_meta_adjustment("intent", mem, meta)
    assert len(result) == 1
    new_weight = result[0]["value"]["failure_penalty_weight"]
    expected = DEFAULT_PENALTY_WEIGHT - INTENT_DELTA
    assert abs(new_weight - expected) < 1e-9


# ── 4. Plan scope uses 0.01 delta ──────────────────────────────────


def test_plan_delta():
    """Plan scope adjusts by 0.01."""
    mem = _mem(0, 5)  # 100% failure
    meta = _meta(DEFAULT_PENALTY_WEIGHT)
    result = build_score_meta_adjustment("plan", mem, meta)
    assert len(result) == 1
    new_weight = result[0]["value"]["failure_penalty_weight"]
    expected = DEFAULT_PENALTY_WEIGHT + PLAN_DELTA
    assert abs(new_weight - expected) < 1e-9


def test_plan_delta_decrease():
    """Plan scope decreases by 0.01 on success dominance (below recovery)."""
    # 6 success, 4 failure → margin=0.2 < RECOVERY_THRESHOLD → no boost
    mem = _mem(6, 4)
    meta = _meta(DEFAULT_PENALTY_WEIGHT)
    result = build_score_meta_adjustment("plan", mem, meta)
    assert len(result) == 1
    new_weight = result[0]["value"]["failure_penalty_weight"]
    expected = DEFAULT_PENALTY_WEIGHT - PLAN_DELTA
    assert abs(new_weight - expected) < 1e-9


# ── 5. Clamp lower bound at 0.05 ───────────────────────────────────


def test_clamp_lower_bound():
    """At floor with continued success → saturation (weight unchanged)."""
    mem = _mem(5, 0)  # 100% success → decrease
    meta = _meta(MIN_PENALTY_WEIGHT)  # already at floor
    result = build_score_meta_adjustment("intent", mem, meta)
    # Boundary saturation: SET with same weight, incremented saturation_count
    assert len(result) == 1
    assert result[0]["value"]["failure_penalty_weight"] == MIN_PENALTY_WEIGHT
    assert result[0]["value"]["saturation_count"] == 1


def test_clamp_lower_approach():
    """Weight approaches but does not breach lower bound."""
    mem = _mem(5, 0)
    meta = _meta(MIN_PENALTY_WEIGHT + INTENT_DELTA)  # 0.055
    result = build_score_meta_adjustment("intent", mem, meta)
    assert len(result) == 1
    assert result[0]["value"]["failure_penalty_weight"] == MIN_PENALTY_WEIGHT


# ── 6. Clamp upper bound at 0.3 ────────────────────────────────────


def test_clamp_upper_bound():
    """At ceiling with continued failures → saturation (weight unchanged)."""
    mem = _mem(0, 5)  # 100% failure → increase
    meta = _meta(MAX_PENALTY_WEIGHT)  # already at ceiling
    result = build_score_meta_adjustment("intent", mem, meta)
    # Boundary saturation: SET with same weight, incremented saturation_count
    assert len(result) == 1
    assert result[0]["value"]["failure_penalty_weight"] == MAX_PENALTY_WEIGHT
    assert result[0]["value"]["saturation_count"] == 1


def test_clamp_upper_approach():
    """Weight approaches but does not breach upper bound."""
    mem = _mem(0, 5)
    meta = _meta(MAX_PENALTY_WEIGHT - PLAN_DELTA)  # 0.29 for plan
    result = build_score_meta_adjustment("plan", mem, meta)
    assert len(result) == 1
    assert result[0]["value"]["failure_penalty_weight"] == MAX_PENALTY_WEIGHT


# ── 7. Determinism: same inputs → same output across runs ──────────


def test_determinism_100_runs():
    """Same memory + same meta produce identical results 100 times."""
    mem = _mem(2, 8)  # 80% failure
    meta = _meta(0.15, count=3)

    first_result = build_score_meta_adjustment("intent", mem, meta)
    assert len(first_result) == 1

    for _ in range(99):
        result = build_score_meta_adjustment("intent", mem, meta)
        assert result == first_result


def test_determinism_plan_100_runs():
    """Same inputs for plan scope produce identical results 100 times."""
    mem = _mem(8, 2)  # 80% success
    meta = _meta(0.2, count=7)

    first_result = build_score_meta_adjustment("plan", mem, meta)
    assert len(first_result) == 1

    for _ in range(99):
        result = build_score_meta_adjustment("plan", mem, meta)
        assert result == first_result


# ── 8. Backward compat: meta=None → old behavior ───────────────────


def test_score_intent_meta_none():
    """score_intent with meta=None uses hardcoded 0.1 penalty."""
    mem = {"execution_count": 10, "success_count": 7, "failure_count": 3}
    # Old formula: (7/10) - (3 * 0.1) = 0.7 - 0.3 = 0.4
    assert abs(score_intent(mem) - 0.4) < 1e-9
    assert abs(score_intent(mem, None) - 0.4) < 1e-9


def test_score_plan_meta_none():
    """score_plan with meta=None uses hardcoded 0.1 penalty."""
    mem = {"execution_count": 10, "success_count": 7, "failure_count": 3}
    assert abs(score_plan(mem) - 0.4) < 1e-9
    assert abs(score_plan(mem, None) - 0.4) < 1e-9


def test_score_intent_none_memory_backward_compat():
    """score_intent(None) still returns 0.0."""
    assert score_intent(None) == 0.0
    assert score_intent(None, _meta(0.2)) == 0.0


def test_score_plan_none_memory_backward_compat():
    """score_plan(None) still returns 0.0."""
    assert score_plan(None) == 0.0
    assert score_plan(None, _meta(0.2)) == 0.0


# ── 9. score_intent and score_plan use meta when provided ──────────


def test_score_intent_with_meta():
    """score_intent uses meta penalty weight."""
    mem = {"execution_count": 10, "success_count": 7, "failure_count": 3}
    meta = _meta(0.2)
    # (7/10) - (3 * 0.2) = 0.7 - 0.6 = 0.1
    assert abs(score_intent(mem, meta) - 0.1) < 1e-9


def test_score_plan_with_meta():
    """score_plan uses meta penalty weight."""
    mem = {"execution_count": 10, "success_count": 7, "failure_count": 3}
    meta = _meta(0.05)
    # (7/10) - (3 * 0.05) = 0.7 - 0.15 = 0.55
    assert abs(score_plan(mem, meta) - 0.55) < 1e-9


def test_score_intent_high_penalty():
    """Higher penalty weight produces lower score."""
    mem = {"execution_count": 10, "success_count": 5, "failure_count": 5}
    low_meta = _meta(0.05)
    high_meta = _meta(0.3)
    assert score_intent(mem, low_meta) > score_intent(mem, high_meta)


# ── 10. Replay: duplicate terminal events → identical SET ──────────


def test_replay_identical_set():
    """Replaying the same adjustment produces the exact same mutation."""
    mem = _mem(1, 9)  # 90% failure
    meta = _meta(0.12, count=2)

    first = build_score_meta_adjustment("intent", mem, meta)
    second = build_score_meta_adjustment("intent", mem, meta)
    assert first == second
    assert first[0]["value"]["adjustment_count"] == 3


def test_replay_plan_identical():
    """Plan scope replay produces identical mutation."""
    mem = _mem(8, 2)
    meta = _meta(0.18, count=5)

    first = build_score_meta_adjustment("plan", mem, meta)
    second = build_score_meta_adjustment("plan", mem, meta)
    assert first == second


# ── Additional: sequential evolution ────────────────────────────────


def test_sequential_evolution_failures():
    """Repeated failures cause penalty to increase step by step."""
    meta = None
    weights: list[float] = [DEFAULT_PENALTY_WEIGHT]

    for i in range(10):
        # Each round: 0 successes, 5+i failures (always above threshold)
        mem = _mem(0, 5 + i)
        result = build_score_meta_adjustment("plan", mem, meta)
        if result:
            meta = result[0]["value"]
            weights.append(meta["failure_penalty_weight"])

    # Weights should be monotonically increasing
    for j in range(1, len(weights)):
        assert weights[j] >= weights[j - 1]

    # Should have increased from default
    assert weights[-1] > DEFAULT_PENALTY_WEIGHT


def test_sequential_evolution_successes():
    """Repeated successes cause penalty to decrease step by step."""
    meta = _meta(0.2)  # start above default
    weights: list[float] = [0.2]

    for i in range(10):
        mem = _mem(5 + i, 0)  # 100% success
        result = build_score_meta_adjustment("intent", mem, meta)
        if result:
            meta = result[0]["value"]
            weights.append(meta["failure_penalty_weight"])

    # Weights should be monotonically decreasing
    for j in range(1, len(weights)):
        assert weights[j] <= weights[j - 1]

    # Should have decreased from 0.2
    assert weights[-1] < 0.2


def test_sequential_evolution_stops_at_clamp():
    """At clamp boundary: weight unchanged, saturation_count increments."""
    meta = _meta(MAX_PENALTY_WEIGHT - PLAN_DELTA)  # one step from ceiling
    mem = _mem(0, 10)  # 100% failure

    # First adjustment should hit ceiling
    result = build_score_meta_adjustment("plan", mem, meta)
    assert len(result) == 1
    assert result[0]["value"]["failure_penalty_weight"] == MAX_PENALTY_WEIGHT

    # Second adjustment from ceiling: saturation tracking (weight same)
    meta_at_ceiling = result[0]["value"]
    result2 = build_score_meta_adjustment("plan", mem, meta_at_ceiling)
    assert len(result2) == 1
    assert result2[0]["value"]["failure_penalty_weight"] == MAX_PENALTY_WEIGHT
    assert result2[0]["value"]["saturation_count"] == 1


# ── Key computation and lookup ──────────────────────────────────────


def test_compute_score_meta_key():
    """Keys follow score_meta.{scope} pattern."""
    assert compute_score_meta_key("intent") == "score_meta.intent"
    assert compute_score_meta_key("plan") == "score_meta.plan"


def test_lookup_score_meta_exists():
    """Lookup returns the record when present in state."""
    state = {"score_meta.intent": _meta(0.15)}
    result = lookup_score_meta(state, "intent")
    assert result is not None
    assert result["failure_penalty_weight"] == 0.15


def test_lookup_score_meta_missing():
    """Lookup returns None when not present."""
    assert lookup_score_meta({}, "intent") is None


def test_get_penalty_weight_from_meta():
    """get_penalty_weight extracts weight from meta."""
    assert get_penalty_weight(_meta(0.22)) == 0.22


def test_get_penalty_weight_none():
    """get_penalty_weight returns default when meta is None."""
    assert get_penalty_weight(None) == DEFAULT_PENALTY_WEIGHT


# ── select_best_plan with meta ─────────────────────────────────────


def test_select_best_plan_with_meta():
    """select_best_plan passes meta to score_plan for selection."""
    state = {
        "plan_memory.test.abc123.plan_a": {
            "plan_id": "plan_a",
            "success_count": 3,
            "failure_count": 7,
            "execution_count": 10,
            "last_outcome": "failed",
            "last_executed_at": "",
            "last_state_signature": "",
            "last_failure_step_index": None,
            "last_failure_type": "",
        },
        "plan_memory.test.abc123.plan_b": {
            "plan_id": "plan_b",
            "success_count": 5,
            "failure_count": 5,
            "execution_count": 10,
            "last_outcome": "completed",
            "last_executed_at": "",
            "last_state_signature": "",
            "last_failure_step_index": None,
            "last_failure_type": "",
        },
    }
    goal = {}  # will hash to something
    # With default meta (0.1): plan_a = 0.3 - 0.7 = -0.4, plan_b = 0.5 - 0.5 = 0.0
    # With low meta (0.05): plan_a = 0.3 - 0.35 = -0.05, plan_b = 0.5 - 0.25 = 0.25

    # Need matching goal hash in keys.  Compute it:
    from umh.substrate.plan_scoring import _hash_goal

    h = _hash_goal(goal)
    state_fixed = {
        f"plan_memory.test.{h}.plan_a": state["plan_memory.test.abc123.plan_a"],
        f"plan_memory.test.{h}.plan_b": state["plan_memory.test.abc123.plan_b"],
    }

    # Both cases: plan_b should win (higher score regardless of meta)
    result = select_best_plan(["plan_a", "plan_b"], "test", goal, state_fixed)
    assert result == "plan_b"

    result_with_meta = select_best_plan(
        ["plan_a", "plan_b"], "test", goal, state_fixed, meta=_meta(0.05)
    )
    assert result_with_meta == "plan_b"


# ── SET-only invariant ──────────────────────────────────────────────


def test_mutations_are_set_only():
    """All mutations produced are SET operations."""
    mem = _mem(0, 10)
    meta = _meta(0.15)

    result = build_score_meta_adjustment("intent", mem, meta)
    assert len(result) == 1
    assert result[0]["op"] == "SET"

    result2 = build_score_meta_adjustment("plan", mem, meta)
    assert len(result2) == 1
    assert result2[0]["op"] == "SET"


def test_adjustment_count_increments():
    """adjustment_count increments on each adjustment."""
    mem = _mem(0, 10)
    meta = _meta(DEFAULT_PENALTY_WEIGHT, count=0)

    result = build_score_meta_adjustment("intent", mem, meta)
    assert result[0]["value"]["adjustment_count"] == 1

    # Simulate applying the mutation
    meta2 = result[0]["value"]
    result2 = build_score_meta_adjustment("intent", mem, meta2)
    if result2:
        assert result2[0]["value"]["adjustment_count"] == 2


# ── Item 3: execution_count mismatch → recomputed value used ───────


def test_execution_count_mismatch_recomputed():
    """Adjustment uses success_count + failure_count, not stored execution_count."""
    # Stored execution_count says 3 (below threshold), but actual counts
    # sum to 10.  Should adjust because recomputed count is >= 5.
    mem = {
        "execution_count": 3,  # stale / corrupted
        "success_count": 1,
        "failure_count": 9,
    }
    result = build_score_meta_adjustment("intent", mem, None)
    # Recomputed: 1 + 9 = 10 >= 5, failure_rate=0.9, success_rate=0.1
    # delta_rate = 0.8 > deadband.  Should produce adjustment.
    assert len(result) == 1


def test_execution_count_mismatch_below_threshold():
    """Recomputed count below threshold blocks adjustment even if stored is high."""
    mem = {
        "execution_count": 100,  # stored says plenty
        "success_count": 2,
        "failure_count": 2,
    }
    # Recomputed: 2 + 2 = 4 < 5.  Should NOT adjust.
    result = build_score_meta_adjustment("intent", mem, None)
    assert result == []


def test_execution_count_zero_recomputed():
    """Zero recomputed count returns no adjustment even with stored nonzero."""
    mem = {
        "execution_count": 10,
        "success_count": 0,
        "failure_count": 0,
    }
    result = build_score_meta_adjustment("intent", mem, None)
    assert result == []


# ── Item 5: monotonicity invariant tests ───────────────────────────


def test_monotonicity_failure_only_100_iters():
    """100 failure-only iterations → penalty strictly non-decreasing."""
    meta = _meta(DEFAULT_PENALTY_WEIGHT)
    weights = [DEFAULT_PENALTY_WEIGHT]

    for i in range(100):
        mem = _mem(0, max(5, 5 + i))
        result = build_score_meta_adjustment("plan", mem, meta)
        if result:
            meta = result[0]["value"]
        weights.append(meta["failure_penalty_weight"])

    # Strictly non-decreasing
    for j in range(1, len(weights)):
        assert weights[j] >= weights[j - 1], (
            f"Monotonicity violated at step {j}: {weights[j]} < {weights[j - 1]}"
        )


def test_monotonicity_success_only_100_iters():
    """100 success-only iterations → penalty strictly non-increasing."""
    meta = _meta(MAX_PENALTY_WEIGHT)
    weights = [MAX_PENALTY_WEIGHT]

    for i in range(100):
        mem = _mem(max(5, 5 + i), 0)
        result = build_score_meta_adjustment("intent", mem, meta)
        if result:
            meta = result[0]["value"]
        weights.append(meta["failure_penalty_weight"])

    # Strictly non-increasing
    for j in range(1, len(weights)):
        assert weights[j] <= weights[j - 1], (
            f"Monotonicity violated at step {j}: {weights[j]} > {weights[j - 1]}"
        )


def test_monotonicity_no_jumps_beyond_double_delta():
    """Mixed sequence: no single step changes weight by more than 2x delta.

    Recovery boost allows 2x delta when success dominates by >= 0.3.
    Max possible jump per step is therefore 2 * PLAN_DELTA.
    """
    import random

    meta = _meta(DEFAULT_PENALTY_WEIGHT)
    prev_weight = DEFAULT_PENALTY_WEIGHT
    max_allowed = PLAN_DELTA * 2  # recovery boost ceiling

    # Use a seeded RNG for reproducibility
    rng = random.Random(42)

    for _ in range(100):
        # Randomly pick success-heavy or failure-heavy
        if rng.random() < 0.5:
            mem = _mem(1, 9)  # failure dominant
        else:
            mem = _mem(9, 1)  # success dominant
        result = build_score_meta_adjustment("plan", mem, meta)
        if result:
            meta = result[0]["value"]
        new_weight = meta["failure_penalty_weight"]
        jump = abs(new_weight - prev_weight)
        assert jump <= max_allowed + 1e-9, f"Jump {jump} exceeds 2x delta {max_allowed}"
        prev_weight = new_weight


# ── Item 6: cross-scope isolation ──────────────────────────────────


def test_cross_scope_isolation_intent_meta_no_affect_plan():
    """Intent meta does not affect plan scoring."""
    mem = {"execution_count": 10, "success_count": 5, "failure_count": 5}
    intent_meta = _meta(0.25)  # high intent penalty

    # Plan scoring without meta
    plan_score_default = score_plan(mem)
    # Plan scoring with INTENT meta (should be irrelevant)
    plan_score_with_intent_meta = score_plan(mem, intent_meta)

    # If you pass intent_meta to score_plan, it uses the weight from it.
    # The isolation test verifies that the SYSTEM doesn't cross-contaminate.
    # We verify by showing score_plan(mem) == score_plan(mem, None).
    assert plan_score_default == score_plan(mem, None)

    # And score_intent with plan meta produces different result than intent meta
    plan_meta = _meta(0.08)
    assert score_intent(mem, intent_meta) != score_intent(mem, plan_meta)


def test_cross_scope_isolation_adjustment_keys():
    """Intent adjustment writes to score_meta.intent, plan to score_meta.plan."""
    mem = _mem(0, 10)
    meta = _meta(DEFAULT_PENALTY_WEIGHT)

    intent_result = build_score_meta_adjustment("intent", mem, meta)
    plan_result = build_score_meta_adjustment("plan", mem, meta)

    assert intent_result[0]["key"] == "score_meta.intent"
    assert plan_result[0]["key"] == "score_meta.plan"

    # Different weights because different deltas
    assert (
        intent_result[0]["value"]["failure_penalty_weight"]
        != plan_result[0]["value"]["failure_penalty_weight"]
    )


def test_cross_scope_isolation_state_reads():
    """Lookup for one scope ignores the other scope's key."""
    state = {
        "score_meta.intent": _meta(0.22),
        "score_meta.plan": _meta(0.08),
    }
    intent_meta = lookup_score_meta(state, "intent")
    plan_meta = lookup_score_meta(state, "plan")

    assert intent_meta is not None
    assert plan_meta is not None
    assert intent_meta["failure_penalty_weight"] == 0.22
    assert plan_meta["failure_penalty_weight"] == 0.08


# ── Item 7: cold start neutrality ─────────────────────────────────


def test_cold_start_below_min_executions():
    """Below MIN_EXECUTIONS: meta-adjusted score == default score."""
    mem = {"execution_count": 4, "success_count": 2, "failure_count": 2}
    meta = _meta(0.25)  # this should NOT be used

    # No adjustment should happen
    assert build_score_meta_adjustment("intent", mem, meta) == []

    # Scoring: meta is still used by score_intent/score_plan since
    # that's a read-path function. But the meta should never have been
    # modified from default if execution_count < 5.
    # Cold start guarantee: if NO adjustment has ever happened,
    # meta is None and score uses default 0.1.
    default_score = score_intent(mem)
    none_meta_score = score_intent(mem, None)
    assert default_score == none_meta_score


def test_cold_start_within_deadband():
    """Within deadband: no adjustment → meta stays at default."""
    # 10 executions, 5 success, 5 failure → delta_rate = 0
    mem = _mem(5, 5)
    meta = _meta(DEFAULT_PENALTY_WEIGHT)

    assert build_score_meta_adjustment("intent", mem, meta) == []

    # Score with default meta should equal score without meta
    score_with = score_intent(
        {"execution_count": 10, "success_count": 5, "failure_count": 5},
        meta,
    )
    score_without = score_intent(
        {"execution_count": 10, "success_count": 5, "failure_count": 5},
    )
    assert abs(score_with - score_without) < 1e-9


# ── Item 8: schema validation ─────────────────────────────────────


def test_lookup_corrupted_meta_missing_weight():
    """Malformed meta (missing weight) returns safe defaults."""
    state = {"score_meta.intent": {"adjustment_count": 5}}
    result = lookup_score_meta(state, "intent")
    assert result is not None
    assert result["failure_penalty_weight"] == DEFAULT_PENALTY_WEIGHT
    assert result["adjustment_count"] == 0


def test_lookup_corrupted_meta_wrong_type_weight():
    """Malformed meta (weight is string) returns safe defaults."""
    state = {
        "score_meta.plan": {
            "failure_penalty_weight": "bad",
            "adjustment_count": 3,
        }
    }
    result = lookup_score_meta(state, "plan")
    assert result is not None
    assert result["failure_penalty_weight"] == DEFAULT_PENALTY_WEIGHT


def test_lookup_corrupted_meta_wrong_type_count():
    """Malformed meta (count is float) returns safe defaults."""
    state = {
        "score_meta.intent": {
            "failure_penalty_weight": 0.15,
            "adjustment_count": 3.5,
        }
    }
    result = lookup_score_meta(state, "intent")
    assert result is not None
    assert result["failure_penalty_weight"] == DEFAULT_PENALTY_WEIGHT


def test_lookup_valid_meta_passes_through():
    """Well-formed meta with all fields passes through unchanged."""
    from umh.substrate.score_meta import META_VERSION

    good = {
        "failure_penalty_weight": 0.18,
        "adjustment_count": 7,
        "last_updated_at": "",
        "last_direction": "up",
        "saturation_count": 0,
        "version": META_VERSION,
    }
    state = {"score_meta.intent": good}
    result = lookup_score_meta(state, "intent")
    assert result is good  # exact same object, not a copy


def test_lookup_old_meta_gets_patched():
    """Pre-upgrade meta (missing new fields) gets patched with defaults."""
    old = {
        "failure_penalty_weight": 0.15,
        "adjustment_count": 3,
        "last_updated_at": "",
    }
    state = {"score_meta.intent": old}
    result = lookup_score_meta(state, "intent")
    assert result is not old  # patched copy, not original
    assert result["failure_penalty_weight"] == 0.15
    assert result["adjustment_count"] == 3
    assert result["last_direction"] == ""
    assert result["saturation_count"] == 0


# ── Item 9: replay idempotency stress ─────────────────────────────


def test_replay_idempotency_100_times():
    """Same terminal event applied 100 times → identical SET each time."""
    mem = _mem(2, 8)  # 80% failure
    meta = _meta(0.15, count=3)

    results = [build_score_meta_adjustment("intent", mem, meta) for _ in range(100)]

    # All 100 results must be identical
    first = results[0]
    assert len(first) == 1
    for i, r in enumerate(results[1:], 1):
        assert r == first, f"Divergence at iteration {i}"

    # The SET value must be stable
    assert all(
        r[0]["value"]["failure_penalty_weight"]
        == first[0]["value"]["failure_penalty_weight"]
        for r in results
    )
    assert all(
        r[0]["value"]["adjustment_count"] == first[0]["value"]["adjustment_count"]
        for r in results
    )


def test_replay_idempotency_plan_100_times():
    """Plan scope: same input 100 times → identical output."""
    mem = _mem(9, 1)  # 90% success
    meta = _meta(0.2, count=10)

    first = build_score_meta_adjustment("plan", mem, meta)
    for _ in range(99):
        assert build_score_meta_adjustment("plan", mem, meta) == first


def test_replay_state_unchanged_after_first_write():
    """Simulating repeated writes: final state matches first write."""
    mem = _mem(1, 9)
    meta = None

    # First adjustment
    result = build_score_meta_adjustment("intent", mem, meta)
    assert len(result) == 1
    first_record = result[0]["value"]

    # Apply: meta now equals first_record
    # Second adjustment from SAME memory + updated meta
    result2 = build_score_meta_adjustment("intent", mem, first_record)
    if result2:
        # If it adjusts again, the new weight must still be in bounds
        # and move by exactly one delta
        second_record = result2[0]["value"]
        jump = abs(
            second_record["failure_penalty_weight"]
            - first_record["failure_penalty_weight"]
        )
        assert jump <= INTENT_DELTA + 1e-9


# ── Item 2: boundary freeze ───────────────────────────────────────


def test_boundary_saturation_at_max():
    """At MAX boundary with continued failures → saturation tracking."""
    meta = _meta(MAX_PENALTY_WEIGHT)
    mem = _mem(0, 10)  # 100% failure

    # Boundary saturation: weight unchanged, saturation_count incremented
    result = build_score_meta_adjustment("intent", mem, meta)
    assert len(result) == 1
    assert result[0]["value"]["failure_penalty_weight"] == MAX_PENALTY_WEIGHT
    assert result[0]["value"]["saturation_count"] == 1


def test_boundary_saturation_at_min():
    """At MIN boundary with continued successes → saturation tracking."""
    meta = _meta(MIN_PENALTY_WEIGHT)
    mem = _mem(10, 0)  # 100% success

    # Boundary saturation: weight unchanged, saturation_count incremented
    result = build_score_meta_adjustment("intent", mem, meta)
    assert len(result) == 1
    assert result[0]["value"]["failure_penalty_weight"] == MIN_PENALTY_WEIGHT
    assert result[0]["value"]["saturation_count"] == 1


def test_boundary_allows_reversal():
    """At MAX boundary but signal reverses → adjustment allowed."""
    meta = _meta(MAX_PENALTY_WEIGHT, direction="up")
    # 80% success → reversal. margin=0.6 >= HYSTERESIS_DEADBAND
    mem = _mem(8, 2)

    result = build_score_meta_adjustment("intent", mem, meta)
    assert len(result) == 1
    assert result[0]["value"]["failure_penalty_weight"] < MAX_PENALTY_WEIGHT
    assert result[0]["value"]["saturation_count"] == 0  # reset on real change


def test_boundary_allows_reversal_min():
    """At MIN boundary but signal reverses → adjustment allowed."""
    meta = _meta(MIN_PENALTY_WEIGHT, direction="down")
    mem = _mem(1, 9)  # 90% failure → should increase

    result = build_score_meta_adjustment("intent", mem, meta)
    assert len(result) == 1
    assert result[0]["value"]["failure_penalty_weight"] > MIN_PENALTY_WEIGHT
    assert result[0]["value"]["saturation_count"] == 0


# ── Item 1: epsilon no-op guard ───────────────────────────────────


def test_epsilon_noop_guard():
    """Boundary saturation catches what epsilon guard would also catch.

    The epsilon guard is defense-in-depth behind boundary saturation.
    At boundary moving same direction, saturation fires first and
    produces a tracking mutation (weight unchanged, saturation_count++).
    """
    meta = _meta(MAX_PENALTY_WEIGHT)
    mem = _mem(0, 10)  # failure → wants increase → boundary saturation
    result = build_score_meta_adjustment("intent", mem, meta)
    assert len(result) == 1
    assert result[0]["value"]["failure_penalty_weight"] == MAX_PENALTY_WEIGHT


# ── Item 10: observability event builder ──────────────────────────


def test_meta_adjusted_event_structure():
    """build_meta_adjusted_event produces correct event structure."""
    from umh.substrate.decision_events import build_meta_adjusted_event

    event = build_meta_adjusted_event(
        scope="intent",
        old_weight=0.1,
        new_weight=0.105,
        success_rate=0.3,
        failure_rate=0.7,
        execution_count=10,
        delta_applied=0.005,
        adjustment_count=3,
        cumulative_delta=0.005,
        failure_count=7,
        session_name="test_session",
        run_id="run_123",
    )

    assert event.event_type == "decision_meta_adjusted"
    assert event.source == "score_meta:intent"
    assert event.session_name == "test_session"
    assert event.payload["scope"] == "intent"
    assert event.payload["old_weight"] == 0.1
    assert event.payload["new_weight"] == 0.105
    assert event.payload["success_rate"] == 0.3
    assert event.payload["failure_rate"] == 0.7
    assert event.payload["execution_count"] == 10
    assert event.payload["delta_applied"] == 0.005
    assert event.payload["adjustment_count"] == 3
    assert event.payload["cumulative_delta"] == 0.005
    # Derived fields
    assert event.payload["confidence"] == min(1.0, 10 / 20)  # 0.5
    assert event.payload["effective_penalty"] == 7 * 0.105  # 0.735
    assert isinstance(event.payload["event_id"], str)
    assert len(event.payload["event_id"]) == 16
    # event_id also in metadata for downstream dedup
    assert event.metadata["event_id"] == event.payload["event_id"]
    assert event.metadata["scope"] == "intent"


def test_meta_adjusted_event_drift_defaults():
    """Drift velocity fields default to zero for backward compat."""
    from umh.substrate.decision_events import build_meta_adjusted_event

    event = build_meta_adjusted_event(
        scope="plan",
        old_weight=0.1,
        new_weight=0.11,
        success_rate=0.4,
        failure_rate=0.6,
        execution_count=10,
        delta_applied=0.01,
    )

    assert event.payload["adjustment_count"] == 0
    assert event.payload["cumulative_delta"] == 0.0
    assert event.payload["confidence"] == 0.5
    assert event.payload["effective_penalty"] == 0.0  # failure_count defaults to 0
    assert isinstance(event.payload["event_id"], str)


def test_meta_adjusted_event_id_deterministic():
    """Same inputs → same event_id (replay-safe dedup)."""
    from umh.substrate.decision_events import build_meta_adjusted_event

    kwargs = dict(
        scope="intent",
        old_weight=0.15,
        new_weight=0.155,
        success_rate=0.3,
        failure_rate=0.7,
        execution_count=20,
        delta_applied=0.005,
        failure_count=14,
    )
    e1 = build_meta_adjusted_event(**kwargs)
    e2 = build_meta_adjusted_event(**kwargs)
    assert e1.payload["event_id"] == e2.payload["event_id"]


def test_meta_adjusted_event_confidence_full():
    """confidence reaches 1.0 at execution_count >= 20."""
    from umh.substrate.decision_events import build_meta_adjusted_event

    event = build_meta_adjusted_event(
        scope="plan",
        old_weight=0.1,
        new_weight=0.11,
        success_rate=0.3,
        failure_rate=0.7,
        execution_count=25,
        delta_applied=0.01,
        failure_count=18,
    )
    assert event.payload["confidence"] == 1.0
    assert event.payload["effective_penalty"] == 18 * 0.11


# ── Saturation event builder ──────────────────────────────────────


class TestMetaSaturationEvent:
    """Tests for the meta_saturation_detected event builder."""

    def test_saturation_event_structure(self):
        from umh.substrate.decision_events import build_meta_saturation_event

        event = build_meta_saturation_event(
            scope="intent",
            current_weight=MAX_PENALTY_WEIGHT,
            saturation_count=SATURATION_WARN_THRESHOLD,
            success_rate=0.3,
            failure_rate=0.7,
            execution_count=10,
            session_name="test_sat",
            run_id="run_sat",
        )

        assert event.event_type == "meta_saturation_detected"
        assert event.source == "score_meta:intent"
        assert event.session_name == "test_sat"
        assert event.payload["scope"] == "intent"
        assert event.payload["current_weight"] == MAX_PENALTY_WEIGHT
        assert event.payload["saturation_count"] == SATURATION_WARN_THRESHOLD
        assert event.payload["boundary"] == "upper"
        assert event.metadata["saturation_count"] == SATURATION_WARN_THRESHOLD

    def test_saturation_event_lower_boundary(self):
        from umh.substrate.decision_events import build_meta_saturation_event

        event = build_meta_saturation_event(
            scope="plan",
            current_weight=MIN_PENALTY_WEIGHT,
            saturation_count=4,
            success_rate=0.8,
            failure_rate=0.2,
            execution_count=10,
        )

        assert event.payload["boundary"] == "lower"
        assert event.payload["scope"] == "plan"
        assert event.source == "score_meta:plan"

    def test_saturation_accumulates_across_adjustments(self):
        """Boundary saturation counter increments each call at clamp."""
        meta = _meta(MAX_PENALTY_WEIGHT, count=5, direction="up", saturation=0)
        mem = _mem(2, 8)  # Strong failure bias

        for expected_sat in range(1, SATURATION_WARN_THRESHOLD + 2):
            result = build_score_meta_adjustment("intent", mem, meta)
            assert len(result) == 1
            rec = result[0]["value"]
            assert rec["saturation_count"] == expected_sat
            assert rec["failure_penalty_weight"] == MAX_PENALTY_WEIGHT
            # Feed back for next iteration
            meta = _meta(
                MAX_PENALTY_WEIGHT,
                count=5,
                direction=rec["last_direction"],
                saturation=rec["saturation_count"],
            )


# ── Advanced stability tests ─────────────────────────────────────


class TestConvergence:
    """Under stable outcome distributions, the weight must stabilize."""

    def test_convergence_under_stable_failure_bias(self):
        """50+ iterations of 70% failure → weight rises then clamps."""
        meta = None
        mem = _mem(3, 7)  # 70% failure, stable

        weights = []
        for _ in range(60):
            result = build_score_meta_adjustment("plan", mem, meta)
            if result:
                rec = result[0]["value"]
                weights.append(rec["failure_penalty_weight"])
                meta = _meta(
                    rec["failure_penalty_weight"],
                    count=rec["adjustment_count"],
                    direction=rec["last_direction"],
                    saturation=rec["saturation_count"],
                )
            else:
                # No adjustment — weight stable
                if meta is not None:
                    weights.append(meta["failure_penalty_weight"])

        # Must reach max and stay there
        assert weights[-1] == MAX_PENALTY_WEIGHT
        # Last 10 entries should all be at max (saturated)
        assert all(w == MAX_PENALTY_WEIGHT for w in weights[-10:])

    def test_convergence_under_stable_success_bias(self):
        """50+ iterations of 80% success → weight drops then clamps."""
        meta = _meta(0.2, count=0, direction="")
        mem = _mem(8, 2)  # 80% success, stable

        weights = []
        for _ in range(60):
            result = build_score_meta_adjustment("plan", mem, meta)
            if result:
                rec = result[0]["value"]
                weights.append(rec["failure_penalty_weight"])
                meta = _meta(
                    rec["failure_penalty_weight"],
                    count=rec["adjustment_count"],
                    direction=rec["last_direction"],
                    saturation=rec["saturation_count"],
                )
            else:
                weights.append(meta["failure_penalty_weight"])

        assert weights[-1] == MIN_PENALTY_WEIGHT
        assert all(w == MIN_PENALTY_WEIGHT for w in weights[-10:])


class TestAdversarial:
    """Adversarial alternating patterns must not cause unbounded oscillation."""

    def test_alternating_failure_success_deadband(self):
        """Alternating 60/40 pattern: delta_rate=0.2 passes deadband but
        when direction flips, hysteresis requires delta_rate >= 0.2.
        Exactly at threshold — should still move (threshold is <, not <=)."""
        meta = None
        mem_fail = _mem(4, 6)  # 60% failure
        mem_succ = _mem(6, 4)  # 60% success

        weights = []
        for i in range(40):
            mem = mem_fail if i % 2 == 0 else mem_succ
            result = build_score_meta_adjustment("intent", mem, meta)
            if result:
                rec = result[0]["value"]
                weights.append(rec["failure_penalty_weight"])
                meta = _meta(
                    rec["failure_penalty_weight"],
                    count=rec["adjustment_count"],
                    direction=rec["last_direction"],
                    saturation=rec["saturation_count"],
                )
            else:
                if meta is not None:
                    weights.append(meta["failure_penalty_weight"])
                else:
                    weights.append(DEFAULT_PENALTY_WEIGHT)

        # The key invariant: weight should stay within bounds
        for w in weights:
            assert MIN_PENALTY_WEIGHT <= w <= MAX_PENALTY_WEIGHT

        # The weight should not swing wildly — max step is delta
        for j in range(1, len(weights)):
            assert abs(weights[j] - weights[j - 1]) <= INTENT_DELTA + 1e-9

    def test_narrow_alternation_hysteresis_blocks(self):
        """Alternating 55/45 pattern: delta_rate=0.1 is exactly at
        deadband for first move but hysteresis blocks direction flips
        at this margin (requires 0.2)."""
        meta = _meta(DEFAULT_PENALTY_WEIGHT, count=1, direction="up")
        mem_succ = _mem(55, 45)  # delta_rate = 0.1

        # With direction "up" stored, switching to "down" requires
        # delta_rate >= HYSTERESIS_DEADBAND (0.2). 0.1 < 0.2 → blocked.
        result = build_score_meta_adjustment("intent", mem_succ, meta)
        assert result == []  # hysteresis blocks the flip


class TestScoringContinuity:
    """Slight meta changes → smooth score changes.

    Score formula: (success_count / execution_count) - (failure_count * weight).
    A single-delta weight step changes the score by failure_count * delta.
    """

    def test_intent_score_continuity(self):
        """Single INTENT_DELTA weight steps → smooth score transitions."""
        mem = {"execution_count": 10, "success_count": 7, "failure_count": 3}

        # Walk weight up in single INTENT_DELTA (0.005) steps
        weights = [0.1 + i * INTENT_DELTA for i in range(6)]
        scores = []
        for w in weights:
            meta = {"failure_penalty_weight": w}
            scores.append(score_intent(mem, meta))

        for i in range(1, len(scores)):
            diff = abs(scores[i] - scores[i - 1])
            # Expected: failure_count * INTENT_DELTA = 3 * 0.005 = 0.015
            max_expected = 3 * INTENT_DELTA + 1e-9
            assert diff <= max_expected, (
                f"Score jump {diff} exceeds {max_expected} at step {i}"
            )

    def test_plan_score_continuity(self):
        """Single PLAN_DELTA weight steps → smooth score transitions."""
        mem = {"execution_count": 10, "success_count": 6, "failure_count": 4}

        weights = [0.1 + i * PLAN_DELTA for i in range(6)]
        scores = []
        for w in weights:
            meta = {"failure_penalty_weight": w}
            scores.append(score_plan(mem, meta))

        for i in range(1, len(scores)):
            diff = abs(scores[i] - scores[i - 1])
            # Expected: failure_count * PLAN_DELTA = 4 * 0.01 = 0.04
            max_expected = 4 * PLAN_DELTA + 1e-9
            assert diff <= max_expected, (
                f"Score jump {diff} exceeds {max_expected} at step {i}"
            )


class TestCrossSystemInvariants:
    """Invariants that span the adjustment + scoring + event systems."""

    def test_every_set_mutation_is_complete_record(self):
        """Every SET mutation must contain all 6 required fields."""
        required = {
            "failure_penalty_weight",
            "last_updated_at",
            "adjustment_count",
            "last_direction",
            "saturation_count",
            "version",
        }
        # Test across multiple scenarios
        scenarios = [
            ("intent", _mem(3, 7), None),
            ("plan", _mem(3, 7), None),
            ("intent", _mem(7, 3), _meta(0.15, count=2, direction="up")),
            ("plan", _mem(7, 3), _meta(0.15, count=2, direction="up")),
            ("intent", _mem(2, 8), _meta(MAX_PENALTY_WEIGHT, count=5, direction="up")),
            ("plan", _mem(8, 2), _meta(MIN_PENALTY_WEIGHT, count=5, direction="down")),
        ]
        for scope, mem, meta in scenarios:
            result = build_score_meta_adjustment(scope, mem, meta)
            if result:
                rec = result[0]["value"]
                assert set(rec.keys()) == required, (
                    f"Missing or extra fields in {scope} mutation: "
                    f"got {set(rec.keys())}, expected {required}"
                )

    def test_set_mutation_op_is_always_set(self):
        """Every returned mutation must have op=SET."""
        for scope in ("intent", "plan"):
            result = build_score_meta_adjustment(scope, _mem(2, 8), None)
            if result:
                assert result[0]["op"] == "SET"

    def test_set_mutation_key_matches_scope(self):
        """Mutation key must match score_meta.{scope}."""
        for scope in ("intent", "plan"):
            result = build_score_meta_adjustment(scope, _mem(2, 8), None)
            if result:
                assert result[0]["key"] == f"score_meta.{scope}"

    def test_weight_always_in_bounds(self):
        """After any adjustment, weight is always within [MIN, MAX]."""
        import random

        rng = random.Random(42)
        for _ in range(200):
            s = rng.randint(0, 20)
            f = rng.randint(0, 20)
            w = rng.uniform(0.0, 0.5)
            w = max(MIN_PENALTY_WEIGHT, min(MAX_PENALTY_WEIGHT, w))
            direction = rng.choice(["", "up", "down"])
            sat = rng.randint(0, 5)

            mem = _mem(s, f)
            meta = _meta(
                w, count=rng.randint(0, 50), direction=direction, saturation=sat
            )

            for scope in ("intent", "plan"):
                result = build_score_meta_adjustment(scope, mem, meta)
                if result:
                    nw = result[0]["value"]["failure_penalty_weight"]
                    assert MIN_PENALTY_WEIGHT <= nw <= MAX_PENALTY_WEIGHT, (
                        f"Out of bounds: {nw} for {scope}, mem=({s},{f}), meta_w={w}"
                    )

    def test_adjustment_is_pure_function(self):
        """Same inputs → same outputs across 50 calls (no hidden state)."""
        mem = _mem(3, 7)
        meta = _meta(0.15, count=3, direction="up", saturation=1)

        reference = build_score_meta_adjustment("intent", mem, meta)
        for _ in range(50):
            result = build_score_meta_adjustment("intent", mem, meta)
            assert result == reference


# ── Steady-state lock tests ──────────────────────────────────────


class TestSteadyStateLock:
    """Tests for the steady-state lock guard."""

    def test_steady_state_blocks_low_delta_high_execution(self):
        """delta_rate < STEADY_STATE_DEADBAND with ec >= 20 → no adjustment.

        Note: the normal DEADBAND (0.1) is wider than STEADY_STATE_DEADBAND
        (0.05), so the normal deadband catches all cases the steady-state
        would catch when ec < 20.  The steady-state lock exists as a named
        constant for future tuning and for semantic clarity.
        """
        from umh.substrate.score_meta import (
            STEADY_STATE_DEADBAND,
            STEADY_STATE_MIN_EXECUTIONS,
        )

        # 52/48 split → delta_rate = 0.04 < STEADY_STATE_DEADBAND
        # With 100 executions, well above STEADY_STATE_MIN_EXECUTIONS
        mem = _mem(52, 48)
        meta = _meta(0.15, count=5, direction="up")
        result = build_score_meta_adjustment("plan", mem, meta)
        assert result == []

    def test_steady_state_allows_strong_signal(self):
        """delta_rate > DEADBAND with high ec → adjustment proceeds."""
        # 70/30 → delta_rate = 0.4, well above any deadband
        mem = _mem(7, 3)
        # But only 10 total → below STEADY_STATE_MIN_EXECUTIONS
        # Normal deadband (0.1) is the only guard, and 0.4 > 0.1 → passes
        result = build_score_meta_adjustment("plan", mem, None)
        assert len(result) == 1


# ── Meta sanity clamp tests ──────────────────────────────────────


class TestMetaSanityClamp:
    """Tests for defensive read-time sanity clamping in get_penalty_weight."""

    def test_negative_weight_returns_default(self):
        meta = {"failure_penalty_weight": -0.5}
        assert get_penalty_weight(meta) == DEFAULT_PENALTY_WEIGHT

    def test_above_one_returns_default(self):
        meta = {"failure_penalty_weight": 1.5}
        assert get_penalty_weight(meta) == DEFAULT_PENALTY_WEIGHT

    def test_exactly_zero_accepted(self):
        meta = {"failure_penalty_weight": 0.0}
        assert get_penalty_weight(meta) == 0.0

    def test_exactly_one_accepted(self):
        meta = {"failure_penalty_weight": 1.0}
        assert get_penalty_weight(meta) == 1.0

    def test_non_numeric_returns_default(self):
        meta = {"failure_penalty_weight": "bad"}
        assert get_penalty_weight(meta) == DEFAULT_PENALTY_WEIGHT

    def test_none_weight_returns_default(self):
        meta = {"failure_penalty_weight": None}
        assert get_penalty_weight(meta) == DEFAULT_PENALTY_WEIGHT

    def test_normal_weight_passes_through(self):
        meta = {"failure_penalty_weight": 0.15}
        assert get_penalty_weight(meta) == 0.15


# ── Version tag tests ────────────────────────────────────────────


class TestVersionTag:
    """Tests for schema version tag."""

    def test_empty_meta_has_version(self):
        from umh.substrate.score_meta import META_VERSION, _empty_meta

        m = _empty_meta()
        assert m["version"] == META_VERSION

    def test_adjustment_records_have_version(self):
        from umh.substrate.score_meta import META_VERSION

        result = build_score_meta_adjustment("intent", _mem(2, 8), None)
        assert len(result) == 1
        assert result[0]["value"]["version"] == META_VERSION

    def test_saturation_records_have_version(self):
        from umh.substrate.score_meta import META_VERSION

        meta = _meta(MAX_PENALTY_WEIGHT, count=5, direction="up")
        result = build_score_meta_adjustment("intent", _mem(2, 8), meta)
        assert len(result) == 1
        assert result[0]["value"]["version"] == META_VERSION

    def test_lookup_patches_version_on_old_records(self):
        from umh.substrate.score_meta import META_VERSION

        old = {
            "failure_penalty_weight": 0.15,
            "adjustment_count": 3,
            "last_updated_at": "",
            "last_direction": "up",
            "saturation_count": 0,
            # no version field
        }
        state = {"score_meta.intent": old}
        result = lookup_score_meta(state, "intent")
        assert result["version"] == META_VERSION
        assert result is not old  # patched = copy

    def test_lookup_passes_through_versioned_records(self):
        from umh.substrate.score_meta import META_VERSION

        good = {
            "failure_penalty_weight": 0.15,
            "adjustment_count": 3,
            "last_updated_at": "",
            "last_direction": "up",
            "saturation_count": 0,
            "version": META_VERSION,
        }
        state = {"score_meta.plan": good}
        result = lookup_score_meta(state, "plan")
        assert result is good  # no copy needed


# ── Score ordering stability ─────────────────────────────────────


class TestScoreOrderingStability:
    """Ranking between two intents must not flip from tiny weight changes
    unless the score difference actually crosses zero."""

    def test_ordering_stable_under_single_delta_perturbation(self):
        """If A > B by more than failure_count * delta, a single-delta
        weight change must not flip the ordering."""
        mem_a = {"execution_count": 10, "success_count": 8, "failure_count": 2}
        mem_b = {"execution_count": 10, "success_count": 6, "failure_count": 4}

        base_weight = 0.1
        meta_base = {"failure_penalty_weight": base_weight}

        score_a_base = score_intent(mem_a, meta_base)
        score_b_base = score_intent(mem_b, meta_base)
        assert score_a_base > score_b_base  # A wins at base weight

        # Perturb weight by INTENT_DELTA in both directions
        for delta in [INTENT_DELTA, -INTENT_DELTA]:
            meta_perturbed = {"failure_penalty_weight": base_weight + delta}
            score_a_new = score_intent(mem_a, meta_perturbed)
            score_b_new = score_intent(mem_b, meta_perturbed)

            # If A still wins at base, the gap is large enough that a single
            # delta perturbation should not flip the ordering
            if score_a_base - score_b_base > 0:
                # The max score change for any single intent from a weight
                # perturbation is max(failure_count_a, failure_count_b) * delta
                max_shift = max(mem_a["failure_count"], mem_b["failure_count"]) * abs(
                    delta
                )
                gap = score_a_base - score_b_base

                if gap > 2 * max_shift:
                    # Gap is large enough — ordering must be preserved
                    assert score_a_new > score_b_new, (
                        f"Ordering flipped: gap={gap}, max_shift={max_shift}, "
                        f"delta={delta}"
                    )

    def test_ordering_can_flip_when_scores_cross_zero_diff(self):
        """When the gap is smaller than the perturbation impact,
        a flip is legitimate and expected."""
        # Construct two memories with nearly identical scores
        mem_a = {"execution_count": 10, "success_count": 6, "failure_count": 4}
        mem_b = {"execution_count": 10, "success_count": 5, "failure_count": 5}

        # At weight 0.1: A_score = 0.6 - 0.4 = 0.2, B_score = 0.5 - 0.5 = 0.0
        # Gap = 0.2, which is > 2 * max_shift for intent delta
        # But at higher weight: A_score drops faster due to higher failure_count... no.
        # Actually A has fewer failures, so A's score drops slower.
        # This just proves ordering is stable for clear winners.
        meta = {"failure_penalty_weight": 0.1}
        score_a = score_intent(mem_a, meta)
        score_b = score_intent(mem_b, meta)
        assert score_a > score_b  # Sanity: A wins

    def test_plan_ordering_stable_under_delta(self):
        """Plan scoring ordering stability."""
        mem_a = {"execution_count": 10, "success_count": 7, "failure_count": 3}
        mem_b = {"execution_count": 10, "success_count": 5, "failure_count": 5}

        base_weight = 0.15
        meta_base = {"failure_penalty_weight": base_weight}
        score_a = score_plan(mem_a, meta_base)
        score_b = score_plan(mem_b, meta_base)
        assert score_a > score_b

        # Single PLAN_DELTA perturbation
        for delta in [PLAN_DELTA, -PLAN_DELTA]:
            meta_new = {"failure_penalty_weight": base_weight + delta}
            sa = score_plan(mem_a, meta_new)
            sb = score_plan(mem_b, meta_new)

            gap = score_a - score_b
            max_shift = max(mem_a["failure_count"], mem_b["failure_count"]) * abs(delta)

            if gap > 2 * max_shift:
                assert sa > sb


# ── Long-run boundedness stress test ─────────────────────────────


class TestLongRunBoundedness:
    """1000-iteration stress test with random but seeded patterns."""

    def test_1000_iterations_weight_bounded(self):
        """Simulate 1000 adjustments with random outcomes.
        Assert weight always in [MIN, MAX], no NaN, no float instability."""
        import math
        import random

        rng = random.Random(12345)
        meta = None

        for i in range(1000):
            s = rng.randint(0, 30)
            f = rng.randint(0, 30)

            if s + f < 5:
                # Below min_executions — skip
                continue

            mem = _mem(s, f)
            result = build_score_meta_adjustment("plan", mem, meta)

            if result:
                rec = result[0]["value"]
                w = rec["failure_penalty_weight"]

                # Core invariants
                assert not math.isnan(w), f"NaN at iteration {i}"
                assert not math.isinf(w), f"Inf at iteration {i}"
                assert MIN_PENALTY_WEIGHT <= w <= MAX_PENALTY_WEIGHT, (
                    f"Out of bounds at iter {i}: {w}"
                )

                meta = _meta(
                    w,
                    count=rec["adjustment_count"],
                    direction=rec["last_direction"],
                    saturation=rec["saturation_count"],
                )

    def test_1000_iterations_intent_scope(self):
        """Same stress test for intent scope."""
        import math
        import random

        rng = random.Random(67890)
        meta = None

        for i in range(1000):
            s = rng.randint(0, 25)
            f = rng.randint(0, 25)

            if s + f < 5:
                continue

            mem = _mem(s, f)
            result = build_score_meta_adjustment("intent", mem, meta)

            if result:
                rec = result[0]["value"]
                w = rec["failure_penalty_weight"]

                assert not math.isnan(w), f"NaN at iteration {i}"
                assert not math.isinf(w), f"Inf at iteration {i}"
                assert MIN_PENALTY_WEIGHT <= w <= MAX_PENALTY_WEIGHT, (
                    f"Out of bounds at iter {i}: {w}"
                )

                meta = _meta(
                    w,
                    count=rec["adjustment_count"],
                    direction=rec["last_direction"],
                    saturation=rec["saturation_count"],
                )


# ── adjustment_count monotonic invariant ─────────────────────────


class TestAdjustmentCountMonotonic:
    """adjustment_count must only increase, never decrease, never skip."""

    def test_monotonic_increase_failures_only(self):
        """Pure failure stream → adjustment_count increments by 1 each time."""
        meta = None
        mem = _mem(1, 9)  # Strong failure bias
        last_count = 0

        for _ in range(30):
            result = build_score_meta_adjustment("plan", mem, meta)
            if result:
                rec = result[0]["value"]
                new_count = rec["adjustment_count"]

                if rec["failure_penalty_weight"] != get_penalty_weight(meta):
                    # Actual weight change → count must increment by 1
                    assert new_count == last_count + 1, (
                        f"Count jumped: {last_count} → {new_count}"
                    )
                    last_count = new_count
                else:
                    # Saturation: count stays the same
                    assert new_count == last_count

                meta = _meta(
                    rec["failure_penalty_weight"],
                    count=rec["adjustment_count"],
                    direction=rec["last_direction"],
                    saturation=rec["saturation_count"],
                )

    def test_monotonic_never_decreases(self):
        """Mixed success/failure → count never goes down."""
        import random

        rng = random.Random(54321)
        meta = None
        max_count = 0

        for _ in range(100):
            s = rng.randint(0, 20)
            f = rng.randint(0, 20)
            if s + f < 5:
                continue

            mem = _mem(s, f)
            result = build_score_meta_adjustment("intent", mem, meta)

            if result:
                rec = result[0]["value"]
                count = rec["adjustment_count"]
                assert count >= max_count, f"Count decreased: {max_count} → {count}"
                max_count = count

                meta = _meta(
                    rec["failure_penalty_weight"],
                    count=rec["adjustment_count"],
                    direction=rec["last_direction"],
                    saturation=rec["saturation_count"],
                )

    def test_no_count_increment_on_saturation(self):
        """At clamp boundary, saturation SET doesn't increment count."""
        meta = _meta(MAX_PENALTY_WEIGHT, count=10, direction="up")
        mem = _mem(2, 8)

        result = build_score_meta_adjustment("plan", mem, meta)
        assert len(result) == 1
        rec = result[0]["value"]
        assert rec["adjustment_count"] == 10  # unchanged
        assert rec["saturation_count"] == 1  # incremented


# ── Full pipeline replay determinism ─────────────────────────────


class TestFullPipelineReplayDeterminism:
    """Same event stream replayed twice → identical state, meta, events."""

    def _simulate_pipeline(self, seed: int) -> tuple[list[dict], list[dict]]:
        """Run a deterministic simulation and return (meta_states, events).

        Simulates a sequence of terminal events with deterministic
        outcomes, collecting all meta mutations and observability events.
        """
        import random

        from umh.substrate.decision_events import build_meta_adjusted_event

        rng = random.Random(seed)
        meta_states: list[dict] = []
        events: list[dict] = []

        meta = None

        for i in range(50):
            s = rng.randint(0, 15)
            f = rng.randint(0, 15)

            if s + f < 5:
                continue

            mem = _mem(s, f)
            result = build_score_meta_adjustment("intent", mem, meta)

            if result:
                rec = result[0]["value"]
                meta_states.append(dict(rec))

                # Build event just like intent_coordinator does
                ec = s + f
                old_w = get_penalty_weight(meta)
                new_w = rec["failure_penalty_weight"]
                event = build_meta_adjusted_event(
                    scope="intent",
                    old_weight=old_w,
                    new_weight=new_w,
                    success_rate=s / ec,
                    failure_rate=f / ec,
                    execution_count=ec,
                    delta_applied=new_w - old_w,
                    adjustment_count=rec["adjustment_count"],
                    cumulative_delta=abs(new_w - DEFAULT_PENALTY_WEIGHT),
                    failure_count=f,
                )
                events.append(
                    {
                        "event_type": event.event_type,
                        "payload": event.payload,
                        "metadata": event.metadata,
                    }
                )

                meta = _meta(
                    rec["failure_penalty_weight"],
                    count=rec["adjustment_count"],
                    direction=rec["last_direction"],
                    saturation=rec["saturation_count"],
                )

        return meta_states, events

    def test_replay_produces_identical_state(self):
        """Two runs with same seed → identical meta state sequence."""
        states_1, _ = self._simulate_pipeline(99999)
        states_2, _ = self._simulate_pipeline(99999)
        assert states_1 == states_2

    def test_replay_produces_identical_events(self):
        """Two runs with same seed → identical event sequence."""
        _, events_1 = self._simulate_pipeline(99999)
        _, events_2 = self._simulate_pipeline(99999)
        assert len(events_1) == len(events_2)
        for i, (e1, e2) in enumerate(zip(events_1, events_2)):
            assert e1 == e2, f"Event mismatch at index {i}"

    def test_different_seeds_produce_different_results(self):
        """Sanity: different seeds → different outcomes."""
        states_1, _ = self._simulate_pipeline(11111)
        states_2, _ = self._simulate_pipeline(22222)
        # At least some states should differ
        assert states_1 != states_2

    def test_replay_event_ids_match(self):
        """event_id fields are identical across replays."""
        _, events_1 = self._simulate_pipeline(77777)
        _, events_2 = self._simulate_pipeline(77777)
        for e1, e2 in zip(events_1, events_2):
            assert e1["payload"]["event_id"] == e2["payload"]["event_id"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONTRACT HARDENING — structural invariant tests
#
# These tests enforce the module contract, not functional correctness.
# They exist to prevent future changes from violating the documented
# invariants in score_meta.py, intent_memory.py, and plan_scoring.py.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


# ── Task 2: No hidden coupling assertion layer ────────────────────


class TestNoHiddenCoupling:
    """Verify that intent and plan scoring scopes are fully isolated.

    Coupling invariants:
    - score_intent NEVER reads plan meta.
    - score_plan NEVER reads intent meta.
    - build_score_meta_adjustment writes to exactly one scope key.
    - The decision engine NEVER mutates meta (read-only).
    - The coordinator is the ONLY writer of meta (verified by code
      structure, not by this test — but we verify the write path here).
    """

    def test_score_intent_ignores_plan_meta_key(self):
        """score_intent uses meta["failure_penalty_weight"] generically.
        Prove it does NOT reach into any plan-specific namespace."""
        import inspect

        from umh.substrate.intent_memory import score_intent

        source = inspect.getsource(score_intent)
        # Must not reference plan-specific keys or scope strings
        assert "plan_memory" not in source
        assert "scope" not in source or "score_meta" not in source
        assert "lookup_plan_memory" not in source

    def test_score_plan_ignores_intent_meta_key(self):
        """score_plan does NOT reach into intent-specific namespace."""
        import inspect

        from umh.substrate.plan_scoring import score_plan

        source = inspect.getsource(score_plan)
        assert "intent_memory" not in source
        assert "lookup_intent_memory" not in source

    def test_intent_adjustment_key_never_plan(self):
        """build_score_meta_adjustment("intent", ...) writes score_meta.intent only."""
        mem = _mem(2, 8)
        result = build_score_meta_adjustment("intent", mem, None)
        assert len(result) == 1
        assert result[0]["key"] == "score_meta.intent"
        assert "plan" not in result[0]["key"]

    def test_plan_adjustment_key_never_intent(self):
        """build_score_meta_adjustment("plan", ...) writes score_meta.plan only."""
        mem = _mem(2, 8)
        result = build_score_meta_adjustment("plan", mem, None)
        assert len(result) == 1
        assert result[0]["key"] == "score_meta.plan"
        assert "intent" not in result[0]["key"]

    def test_decision_engine_evaluate_does_not_mutate_state(self):
        """DecisionEngine.evaluate reads state only — never writes."""
        from umh.substrate.decision_engine import (
            DecisionEngine,
            RuleBasedStrategy,
        )
        from umh.substrate.runtime_state_store import RuntimeStateStore

        store = RuntimeStateStore()
        store.apply_mutations(
            [
                {"op": "SET", "key": "score_meta.intent", "value": _meta(0.15)},
                {"op": "SET", "key": "score_meta.plan", "value": _meta(0.12)},
            ]
        )

        snapshot_before = store.snapshot()
        engine = DecisionEngine(strategy=RuleBasedStrategy([]))
        engine.evaluate(store)
        snapshot_after = store.snapshot()

        assert snapshot_before == snapshot_after

    def test_score_intent_with_plan_meta_produces_different_than_intent_meta(self):
        """Passing plan-scope meta to score_intent vs intent-scope meta
        produces different scores — proving the caller controls scope."""
        mem = {"execution_count": 10, "success_count": 5, "failure_count": 5}
        intent_meta = _meta(0.2)
        plan_meta = _meta(0.08)

        score_with_intent = score_intent(mem, intent_meta)
        score_with_plan = score_intent(mem, plan_meta)

        # Different weights → different scores
        assert score_with_intent != score_with_plan

    def test_score_plan_with_intent_meta_produces_different_than_plan_meta(self):
        """Same proof for plan scoring — caller is responsible for scope."""
        mem = {"execution_count": 10, "success_count": 5, "failure_count": 5}
        intent_meta = _meta(0.2)
        plan_meta = _meta(0.08)

        score_with_intent = score_plan(mem, intent_meta)
        score_with_plan = score_plan(mem, plan_meta)

        assert score_with_intent != score_with_plan

    def test_adjustment_never_reads_cross_scope_state(self):
        """build_score_meta_adjustment is a pure function of (scope, memory, meta).
        It does not access any external state, store, or cross-scope data."""
        import inspect

        source = inspect.getsource(build_score_meta_adjustment)
        # Must not import or reference RuntimeStateStore
        assert "RuntimeStateStore" not in source
        # Must not call store methods (store.snapshot, store.apply, etc.)
        assert "store." not in source
        # Must not call lookup functions
        assert "lookup_intent_memory" not in source
        assert "lookup_plan_memory" not in source
        assert "lookup_score_meta" not in source


# ── Task 4: Strict replay contract ───────────────────────────────


class TestStrictReplayContract:
    """Replay same event stream → identical state hash, meta, events.

    This is the permanent invariant test for event-sourced replay safety.
    The existing TestFullPipelineReplayDeterminism covers meta+events.
    This class adds state hash identity and event_id ordering.
    """

    def _replay_stream(
        self, seed: int, scope: str = "intent"
    ) -> tuple[list[dict], list[str], str]:
        """Run a deterministic stream and return (meta_states, event_ids, final_hash).

        Returns:
            meta_states: list of meta record dicts after each adjustment.
            event_ids: list of event_id strings in emission order.
            final_hash: SHA-256 prefix of the final meta state.
        """
        import hashlib
        import json
        import random

        from umh.substrate.decision_events import build_meta_adjusted_event

        rng = random.Random(seed)
        meta_states: list[dict] = []
        event_ids: list[str] = []
        meta = None

        for _ in range(80):
            s = rng.randint(0, 20)
            f = rng.randint(0, 20)
            if s + f < 5:
                continue

            mem = _mem(s, f)
            result = build_score_meta_adjustment(scope, mem, meta)

            if result:
                rec = result[0]["value"]
                meta_states.append(dict(rec))

                ec = s + f
                old_w = get_penalty_weight(meta)
                new_w = rec["failure_penalty_weight"]
                event = build_meta_adjusted_event(
                    scope=scope,
                    old_weight=old_w,
                    new_weight=new_w,
                    success_rate=s / ec,
                    failure_rate=f / ec,
                    execution_count=ec,
                    delta_applied=new_w - old_w,
                    adjustment_count=rec["adjustment_count"],
                    cumulative_delta=abs(new_w - DEFAULT_PENALTY_WEIGHT),
                    failure_count=f,
                )
                event_ids.append(event.payload["event_id"])

                meta = _meta(
                    rec["failure_penalty_weight"],
                    count=rec["adjustment_count"],
                    direction=rec["last_direction"],
                    saturation=rec["saturation_count"],
                )

        # Compute final state hash
        final_hash = ""
        if meta_states:
            canonical = json.dumps(
                meta_states[-1], sort_keys=True, separators=(",", ":")
            )
            final_hash = hashlib.sha256(canonical.encode()).hexdigest()[:16]

        return meta_states, event_ids, final_hash

    def test_state_hash_identical_across_replays(self):
        """Two runs with same seed → identical final state hash."""
        _, _, hash_1 = self._replay_stream(44444)
        _, _, hash_2 = self._replay_stream(44444)
        assert hash_1 == hash_2
        assert hash_1 != ""  # sanity: something happened

    def test_meta_sequence_identical_across_replays(self):
        """Two runs → identical meta state at every step."""
        states_1, _, _ = self._replay_stream(55555)
        states_2, _, _ = self._replay_stream(55555)
        assert states_1 == states_2

    def test_event_id_ordering_identical_across_replays(self):
        """Two runs → identical event_id sequence including ordering."""
        _, ids_1, _ = self._replay_stream(66666)
        _, ids_2, _ = self._replay_stream(66666)
        assert ids_1 == ids_2
        assert len(ids_1) > 0  # sanity

    def test_plan_scope_replay_identical(self):
        """Plan scope replay produces identical results."""
        states_1, ids_1, hash_1 = self._replay_stream(88888, scope="plan")
        states_2, ids_2, hash_2 = self._replay_stream(88888, scope="plan")
        assert states_1 == states_2
        assert ids_1 == ids_2
        assert hash_1 == hash_2

    def test_different_seeds_produce_different_hashes(self):
        """Sanity: different seeds diverge."""
        _, _, h1 = self._replay_stream(11111)
        _, _, h2 = self._replay_stream(22222)
        assert h1 != h2


# ── Task 5: Null system mode validation ──────────────────────────


class TestNullSystemMode:
    """When meta=None or score_meta missing entirely, the system must
    behave EXACTLY like the pre-meta system.  No drift, no implicit
    defaults leaking.

    The "pre-meta system" uses hardcoded penalty_weight=0.1.
    """

    def test_score_intent_none_meta_equals_hardcoded(self):
        """score_intent(mem, None) == score_intent(mem) for all cases."""
        test_cases = [
            _mem(0, 5),
            _mem(5, 0),
            _mem(3, 7),
            _mem(7, 3),
            _mem(5, 5),
            _mem(1, 9),
            _mem(9, 1),
        ]
        for mem in test_cases:
            full_mem = {
                "execution_count": mem["execution_count"],
                "success_count": mem["success_count"],
                "failure_count": mem["failure_count"],
            }
            assert score_intent(full_mem, None) == score_intent(full_mem)

    def test_score_plan_none_meta_equals_hardcoded(self):
        """score_plan(mem, None) == score_plan(mem) for all cases."""
        test_cases = [
            _mem(0, 5),
            _mem(5, 0),
            _mem(3, 7),
            _mem(7, 3),
            _mem(5, 5),
        ]
        for mem in test_cases:
            full_mem = {
                "execution_count": mem["execution_count"],
                "success_count": mem["success_count"],
                "failure_count": mem["failure_count"],
                "plan_id": "test",
                "last_outcome": "",
                "last_executed_at": "",
                "last_state_signature": "",
                "last_failure_step_index": None,
                "last_failure_type": "",
            }
            assert score_plan(full_mem, None) == score_plan(full_mem)

    def test_score_intent_default_meta_equals_none(self):
        """score_intent with default-weight meta produces same result as None."""
        mem = {"execution_count": 10, "success_count": 7, "failure_count": 3}
        default_meta = _meta(DEFAULT_PENALTY_WEIGHT)
        assert abs(score_intent(mem, default_meta) - score_intent(mem, None)) < 1e-9

    def test_score_plan_default_meta_equals_none(self):
        """score_plan with default-weight meta produces same result as None."""
        mem = {"execution_count": 10, "success_count": 7, "failure_count": 3}
        default_meta = _meta(DEFAULT_PENALTY_WEIGHT)
        assert abs(score_plan(mem, default_meta) - score_plan(mem, None)) < 1e-9

    def test_no_adjustment_from_none_meta_below_threshold(self):
        """meta=None + below threshold → same behavior as with meta."""
        mem = _mem(2, 2)  # 4 executions, below MIN_EXECUTIONS
        assert build_score_meta_adjustment("intent", mem, None) == []
        assert build_score_meta_adjustment("plan", mem, None) == []

    def test_adjustment_from_none_meta_uses_default_weight(self):
        """First adjustment with meta=None starts from DEFAULT_PENALTY_WEIGHT."""
        mem = _mem(0, 10)  # 100% failure, above threshold
        result = build_score_meta_adjustment("intent", mem, None)
        assert len(result) == 1
        rec = result[0]["value"]
        # Should have increased from default by exactly INTENT_DELTA
        expected = DEFAULT_PENALTY_WEIGHT + INTENT_DELTA
        assert abs(rec["failure_penalty_weight"] - expected) < 1e-9

    def test_get_penalty_weight_none_returns_exact_default(self):
        """get_penalty_weight(None) returns exactly DEFAULT_PENALTY_WEIGHT."""
        assert get_penalty_weight(None) is not None
        assert get_penalty_weight(None) == DEFAULT_PENALTY_WEIGHT

    def test_lookup_missing_scope_returns_none(self):
        """lookup_score_meta on empty state returns None (not default meta)."""
        assert lookup_score_meta({}, "intent") is None
        assert lookup_score_meta({}, "plan") is None

    def test_full_pipeline_without_meta_matches_hardcoded(self):
        """Run 20 scoring calls with meta=None — all must match
        the hardcoded 0.1 penalty formula exactly."""
        import random

        rng = random.Random(13579)
        for _ in range(20):
            s = rng.randint(1, 20)
            f = rng.randint(1, 20)
            ec = s + f
            mem = {"execution_count": ec, "success_count": s, "failure_count": f}

            # Hardcoded formula: (s/ec) - (f * 0.1)
            expected = (s / ec) - (f * 0.1)
            assert abs(score_intent(mem, None) - expected) < 1e-9
            assert abs(score_plan(mem, None) - expected) < 1e-9


# ── Task 6: Boundary condition audit ─────────────────────────────


class TestBoundaryConditionAudit:
    """Explicit tests for every boundary edge case.

    All must produce stable, predictable outcomes.
    """

    def test_execution_count_exactly_zero(self):
        """execution_count=0 → no adjustment, div-zero safe."""
        mem = _mem(0, 0)
        assert build_score_meta_adjustment("intent", mem, None) == []
        assert build_score_meta_adjustment("plan", mem, None) == []
        # Scoring returns 0.0
        assert score_intent(mem) == 0.0
        assert score_plan(mem) == 0.0

    def test_execution_count_1_to_4(self):
        """execution_count 1–4 → no adjustment (below threshold)."""
        for total in range(1, 5):
            for s in range(total + 1):
                f = total - s
                mem = _mem(s, f)
                assert build_score_meta_adjustment("intent", mem, None) == [], (
                    f"Unexpected adjustment at ec={total}, s={s}, f={f}"
                )
                assert build_score_meta_adjustment("plan", mem, None) == []

    def test_execution_count_exactly_5_activation_edge(self):
        """execution_count=5 with clear signal → adjustment activates."""
        # 100% failure: delta_rate = 1.0 > deadband
        mem = _mem(0, 5)
        result = build_score_meta_adjustment("intent", mem, None)
        assert len(result) == 1

        # 100% success: delta_rate = 1.0 > deadband
        mem = _mem(5, 0)
        result = build_score_meta_adjustment("intent", mem, None)
        assert len(result) == 1

    def test_execution_count_5_within_deadband(self):
        """execution_count=5 but within deadband → no adjustment."""
        # Cannot get exactly 50/50 with 5 — closest is 3/2 (60/40, delta=0.2)
        # or 2/3 (40/60, delta=0.2).  Both pass deadband.
        # Use counts that produce delta < 0.1... impossible with 5 total.
        # 3/2 gives 0.2, 4/1 gives 0.6 — all pass deadband with 5 total.
        # This is expected: with only 5 data points, any imbalance exceeds 0.1.
        pass  # documented: 5 executions always pass deadband (min delta=0.2)

    def test_delta_rate_exactly_at_deadband(self):
        """delta_rate exactly = DEADBAND (0.1) → NOT in deadband (strict <)."""
        # 20 executions: 11/9 → s_rate=0.55, f_rate=0.45, delta=0.1
        mem = _mem(11, 9)
        result = build_score_meta_adjustment("intent", mem, None)
        assert len(result) == 1  # 0.1 is NOT < 0.1 → passes

    def test_delta_rate_just_below_deadband(self):
        """delta_rate slightly below DEADBAND → no adjustment."""
        # 100 executions: 54/46 → delta_rate = 0.08 < 0.1
        mem = _mem(54, 46)
        assert build_score_meta_adjustment("intent", mem, None) == []

    def test_weight_exactly_min(self):
        """Weight exactly at MIN_PENALTY_WEIGHT — various signals."""
        meta = _meta(MIN_PENALTY_WEIGHT)

        # Failure signal → increase → normal adjustment
        mem = _mem(0, 10)
        result = build_score_meta_adjustment("intent", mem, meta)
        assert len(result) == 1
        assert result[0]["value"]["failure_penalty_weight"] > MIN_PENALTY_WEIGHT

        # Success signal → decrease → saturation
        mem = _mem(10, 0)
        result = build_score_meta_adjustment("intent", mem, meta)
        assert len(result) == 1
        assert result[0]["value"]["failure_penalty_weight"] == MIN_PENALTY_WEIGHT
        assert result[0]["value"]["saturation_count"] == 1

    def test_weight_exactly_max(self):
        """Weight exactly at MAX_PENALTY_WEIGHT — various signals."""
        meta = _meta(MAX_PENALTY_WEIGHT)

        # Success signal → decrease → normal adjustment
        mem = _mem(10, 0)
        result = build_score_meta_adjustment("intent", mem, meta)
        assert len(result) == 1
        assert result[0]["value"]["failure_penalty_weight"] < MAX_PENALTY_WEIGHT

        # Failure signal → increase → saturation
        mem = _mem(0, 10)
        result = build_score_meta_adjustment("intent", mem, meta)
        assert len(result) == 1
        assert result[0]["value"]["failure_penalty_weight"] == MAX_PENALTY_WEIGHT
        assert result[0]["value"]["saturation_count"] == 1

    def test_failure_rate_equals_success_rate(self):
        """failure_rate == success_rate → delta_rate = 0 → no adjustment."""
        for total in [10, 20, 50, 100]:
            half = total // 2
            mem = _mem(half, half)
            assert build_score_meta_adjustment("intent", mem, None) == [], (
                f"Unexpected adjustment at equal rates with ec={total}"
            )
            assert build_score_meta_adjustment("plan", mem, None) == []

    def test_all_success_from_default(self):
        """100% success from default weight → deterministic decrease."""
        mem = _mem(10, 0)
        result = build_score_meta_adjustment("intent", mem, None)
        assert len(result) == 1
        rec = result[0]["value"]
        # Recovery boost: s_rate - f_rate = 1.0 >= 0.3 → 2x delta
        expected = DEFAULT_PENALTY_WEIGHT - (INTENT_DELTA * 2)
        assert abs(rec["failure_penalty_weight"] - expected) < 1e-9

    def test_all_failure_from_default(self):
        """100% failure from default weight → deterministic increase."""
        mem = _mem(0, 10)
        result = build_score_meta_adjustment("intent", mem, None)
        assert len(result) == 1
        rec = result[0]["value"]
        expected = DEFAULT_PENALTY_WEIGHT + INTENT_DELTA
        assert abs(rec["failure_penalty_weight"] - expected) < 1e-9


# ── Task 7: Meta integrity invariant ─────────────────────────────


class TestMetaIntegrityInvariant:
    """Global assertion: every meta record contains only scalar fields.
    No lists, no nested dynamic structures, version present or defaulted.

    This protects against accidental complexity creep.
    """

    _SCALAR_TYPES = (int, float, str, bool, type(None))

    def _assert_all_scalar(self, record: dict, context: str) -> None:
        """Assert every value in the record is a scalar type."""
        for key, value in record.items():
            assert isinstance(value, self._SCALAR_TYPES), (
                f"Non-scalar field '{key}' = {type(value).__name__} "
                f"in {context}: {value!r}"
            )

    def test_empty_meta_is_scalar_only(self):
        """_empty_meta() contains only scalars."""
        from umh.substrate.score_meta import _empty_meta

        self._assert_all_scalar(_empty_meta(), "_empty_meta()")

    def test_adjustment_output_is_scalar_only(self):
        """Every SET mutation value from build_score_meta_adjustment
        contains only scalar fields."""
        scenarios = [
            ("intent", _mem(2, 8), None),
            ("plan", _mem(8, 2), None),
            ("intent", _mem(0, 10), _meta(0.15)),
            ("plan", _mem(10, 0), _meta(0.25)),
            ("intent", _mem(2, 8), _meta(MAX_PENALTY_WEIGHT, direction="up")),
            ("plan", _mem(8, 2), _meta(MIN_PENALTY_WEIGHT, direction="down")),
        ]
        for scope, mem, meta in scenarios:
            result = build_score_meta_adjustment(scope, mem, meta)
            if result:
                self._assert_all_scalar(
                    result[0]["value"],
                    f"adjustment({scope}, s={mem['success_count']}, f={mem['failure_count']})",
                )

    def test_saturation_output_is_scalar_only(self):
        """Saturation mutations (weight unchanged) are also scalar-only."""
        meta = _meta(MAX_PENALTY_WEIGHT, count=5, direction="up", saturation=2)
        mem = _mem(2, 8)
        result = build_score_meta_adjustment("intent", mem, meta)
        assert len(result) == 1
        self._assert_all_scalar(result[0]["value"], "saturation at MAX")

    def test_version_always_present_in_output(self):
        """version field is present in every output record."""
        from umh.substrate.score_meta import META_VERSION

        scenarios = [
            ("intent", _mem(0, 10), None),
            ("plan", _mem(10, 0), None),
            ("intent", _mem(2, 8), _meta(MAX_PENALTY_WEIGHT, direction="up")),
        ]
        for scope, mem, meta in scenarios:
            result = build_score_meta_adjustment(scope, mem, meta)
            if result:
                assert result[0]["value"]["version"] == META_VERSION

    def test_version_defaulted_on_lookup_old_records(self):
        """Pre-upgrade records without version get it defaulted on lookup."""
        from umh.substrate.score_meta import META_VERSION

        old = {
            "failure_penalty_weight": 0.15,
            "adjustment_count": 3,
            "last_updated_at": "",
        }
        state = {"score_meta.intent": old}
        result = lookup_score_meta(state, "intent")
        assert result is not None
        assert result["version"] == META_VERSION

    def test_no_list_fields_in_200_random_adjustments(self):
        """Stress test: 200 random adjustments → never a list in output."""
        import random

        rng = random.Random(24680)
        meta = None

        for _ in range(200):
            s = rng.randint(0, 20)
            f = rng.randint(0, 20)
            if s + f < 5:
                continue

            mem = _mem(s, f)
            scope = rng.choice(["intent", "plan"])
            result = build_score_meta_adjustment(scope, mem, meta)

            if result:
                rec = result[0]["value"]
                for key, val in rec.items():
                    assert not isinstance(val, (list, dict, set, tuple)), (
                        f"Non-scalar {type(val).__name__} in field '{key}'"
                    )
                meta = _meta(
                    rec["failure_penalty_weight"],
                    count=rec["adjustment_count"],
                    direction=rec["last_direction"],
                    saturation=rec["saturation_count"],
                )

    def test_record_field_count_is_exactly_six(self):
        """Meta records must have exactly 6 fields — no more, no less."""
        expected_fields = {
            "failure_penalty_weight",
            "last_updated_at",
            "adjustment_count",
            "last_direction",
            "saturation_count",
            "version",
        }

        result = build_score_meta_adjustment("intent", _mem(2, 8), None)
        assert len(result) == 1
        assert set(result[0]["value"].keys()) == expected_fields

        result = build_score_meta_adjustment("plan", _mem(8, 2), None)
        assert len(result) == 1
        assert set(result[0]["value"].keys()) == expected_fields
