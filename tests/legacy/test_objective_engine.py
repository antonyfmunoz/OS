"""
Tests for runtime.objective_engine — Unified Value Function.

Verifies: deterministic outputs, bounded values [0,1],
stability under repeated runs, monotonic improvement behavior.

No LLM calls.  No randomness.  No external deps.  Deterministic.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.objective_engine import (
    NO_OBJECTIVE,
    WEIGHT_CONFIDENCE,
    WEIGHT_GOAL_PROGRESS,
    WEIGHT_PLAN_EXECUTION,
    WEIGHT_POLICY_COHERENCE,
    WEIGHT_STABILITY,
    ObjectiveResult,
    ObjectiveSnapshot,
    compute_objective,
)


# ---------------------------------------------------------------------------
# Section 1: NO_OBJECTIVE sentinel
# ---------------------------------------------------------------------------


def test_no_objective_value():
    assert NO_OBJECTIVE.value == 0.5


def test_no_objective_has_all_components():
    assert "goal_progress" in NO_OBJECTIVE.components
    assert "plan_execution" in NO_OBJECTIVE.components
    assert "stability" in NO_OBJECTIVE.components
    assert "confidence" in NO_OBJECTIVE.components
    assert "policy_coherence" in NO_OBJECTIVE.components


def test_no_objective_weights_sum_to_one():
    total = sum(NO_OBJECTIVE.weights.values())
    assert abs(total - 1.0) < 1e-9


def test_no_objective_to_dict():
    d = NO_OBJECTIVE.to_dict()
    assert "value" in d
    assert "components" in d
    assert "weights" in d
    assert "snapshot" in d


# ---------------------------------------------------------------------------
# Section 2: Default snapshot produces neutral value
# ---------------------------------------------------------------------------


def test_default_snapshot_value():
    snap = ObjectiveSnapshot()
    result = compute_objective(snap)
    assert 0.0 <= result.value <= 1.0


def test_default_snapshot_all_components_bounded():
    snap = ObjectiveSnapshot()
    result = compute_objective(snap)
    for name, val in result.components.items():
        assert 0.0 <= val <= 1.0, f"{name} out of bounds: {val}"


# ---------------------------------------------------------------------------
# Section 3: Weights sum to 1.0
# ---------------------------------------------------------------------------


def test_weights_sum():
    total = (
        WEIGHT_GOAL_PROGRESS
        + WEIGHT_PLAN_EXECUTION
        + WEIGHT_STABILITY
        + WEIGHT_CONFIDENCE
        + WEIGHT_POLICY_COHERENCE
    )
    assert abs(total - 1.0) < 1e-9


def test_computed_weights_sum():
    snap = ObjectiveSnapshot(goal_score=0.8, plan_confidence=0.7)
    result = compute_objective(snap)
    total = sum(result.weights.values())
    assert abs(total - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# Section 4: Bounded values [0, 1] under extreme inputs
# ---------------------------------------------------------------------------


def test_all_zeros_bounded():
    snap = ObjectiveSnapshot(
        goal_score=0.0,
        goal_delta=0.0,
        goal_confidence=0.0,
        plan_confidence=0.0,
        plan_steps_completed=0,
        plan_steps_total=0,
        failure_streak=0,
        quality_score=0.0,
        system_confidence=0.0,
        policy_changes=0,
    )
    result = compute_objective(snap)
    assert 0.0 <= result.value <= 1.0
    for v in result.components.values():
        assert 0.0 <= v <= 1.0


def test_all_max_bounded():
    snap = ObjectiveSnapshot(
        goal_score=1.0,
        goal_delta=1.0,
        goal_confidence=1.0,
        plan_confidence=1.0,
        plan_steps_completed=100,
        plan_steps_total=100,
        failure_streak=0,
        quality_score=1.0,
        system_confidence=1.0,
        policy_changes=0,
        current_policy="exploit",
        previous_policy="exploit",
    )
    result = compute_objective(snap)
    assert 0.0 <= result.value <= 1.0
    for v in result.components.values():
        assert 0.0 <= v <= 1.0


def test_extreme_negative_bounded():
    snap = ObjectiveSnapshot(
        goal_score=-999.0,
        goal_delta=-999.0,
        goal_confidence=-999.0,
        plan_confidence=-999.0,
        plan_steps_completed=-100,
        plan_steps_total=-100,
        failure_streak=999,
        quality_score=-999.0,
        system_confidence=-999.0,
        policy_changes=999,
    )
    result = compute_objective(snap)
    assert 0.0 <= result.value <= 1.0
    for v in result.components.values():
        assert 0.0 <= v <= 1.0


def test_extreme_positive_bounded():
    snap = ObjectiveSnapshot(
        goal_score=999.0,
        goal_delta=999.0,
        goal_confidence=999.0,
        plan_confidence=999.0,
        plan_steps_completed=99999,
        plan_steps_total=99999,
        failure_streak=0,
        quality_score=999.0,
        system_confidence=999.0,
        policy_changes=0,
    )
    result = compute_objective(snap)
    assert 0.0 <= result.value <= 1.0
    for v in result.components.values():
        assert 0.0 <= v <= 1.0


# ---------------------------------------------------------------------------
# Section 5: Deterministic behavior
# ---------------------------------------------------------------------------


def test_same_input_same_output():
    snap = ObjectiveSnapshot(
        goal_score=0.7,
        goal_delta=0.1,
        goal_confidence=0.8,
        plan_confidence=0.6,
        plan_steps_completed=3,
        plan_steps_total=5,
        failure_streak=1,
        quality_score=0.65,
        system_confidence=0.7,
        policy_changes=2,
        current_policy="exploit",
        previous_policy="explore",
    )
    r1 = compute_objective(snap)
    r2 = compute_objective(snap)
    assert r1.value == r2.value
    assert r1.components == r2.components


def test_deterministic_100_runs():
    snap = ObjectiveSnapshot(
        goal_score=0.5,
        plan_confidence=0.5,
        failure_streak=2,
        quality_score=0.4,
        system_confidence=0.6,
    )
    ref = compute_objective(snap)
    for _ in range(100):
        result = compute_objective(snap)
        assert result.value == ref.value


# ---------------------------------------------------------------------------
# Section 6: Stability under repeated runs (stress)
# ---------------------------------------------------------------------------


def test_stress_1000_runs():
    snap = ObjectiveSnapshot(
        goal_score=0.8,
        goal_delta=0.05,
        goal_confidence=0.9,
        plan_confidence=0.75,
        plan_steps_completed=7,
        plan_steps_total=10,
        failure_streak=0,
        quality_score=0.7,
        system_confidence=0.8,
        policy_changes=1,
        current_policy="commit",
        previous_policy="exploit",
    )
    ref = compute_objective(snap)
    for _ in range(1000):
        result = compute_objective(snap)
        assert result.value == ref.value
        assert 0.0 <= result.value <= 1.0


# ---------------------------------------------------------------------------
# Section 7: Monotonic improvement — goal progress
# ---------------------------------------------------------------------------


def test_higher_goal_score_higher_value():
    low = ObjectiveSnapshot(goal_score=0.2, goal_confidence=0.8)
    high = ObjectiveSnapshot(goal_score=0.8, goal_confidence=0.8)
    r_low = compute_objective(low)
    r_high = compute_objective(high)
    assert r_high.value > r_low.value


def test_positive_delta_better_than_negative():
    pos = ObjectiveSnapshot(goal_score=0.5, goal_delta=0.3, goal_confidence=0.8)
    neg = ObjectiveSnapshot(goal_score=0.5, goal_delta=-0.3, goal_confidence=0.8)
    r_pos = compute_objective(pos)
    r_neg = compute_objective(neg)
    assert r_pos.value > r_neg.value


# ---------------------------------------------------------------------------
# Section 8: Monotonic improvement — plan execution
# ---------------------------------------------------------------------------


def test_higher_plan_confidence_higher_value():
    low = ObjectiveSnapshot(plan_confidence=0.2)
    high = ObjectiveSnapshot(plan_confidence=0.9)
    r_low = compute_objective(low)
    r_high = compute_objective(high)
    assert r_high.value > r_low.value


def test_more_steps_completed_higher_value():
    low = ObjectiveSnapshot(
        plan_steps_completed=1, plan_steps_total=10, plan_confidence=0.5
    )
    high = ObjectiveSnapshot(
        plan_steps_completed=8, plan_steps_total=10, plan_confidence=0.5
    )
    r_low = compute_objective(low)
    r_high = compute_objective(high)
    assert r_high.value > r_low.value


# ---------------------------------------------------------------------------
# Section 9: Monotonic improvement — stability
# ---------------------------------------------------------------------------


def test_no_failures_better_than_many():
    stable = ObjectiveSnapshot(failure_streak=0, quality_score=0.7)
    unstable = ObjectiveSnapshot(failure_streak=5, quality_score=0.7)
    r_stable = compute_objective(stable)
    r_unstable = compute_objective(unstable)
    assert r_stable.value > r_unstable.value


def test_higher_quality_better():
    low = ObjectiveSnapshot(quality_score=0.2)
    high = ObjectiveSnapshot(quality_score=0.9)
    r_low = compute_objective(low)
    r_high = compute_objective(high)
    assert r_high.value > r_low.value


# ---------------------------------------------------------------------------
# Section 10: Monotonic improvement — confidence
# ---------------------------------------------------------------------------


def test_higher_system_confidence_higher_value():
    low = ObjectiveSnapshot(system_confidence=0.1)
    high = ObjectiveSnapshot(system_confidence=0.9)
    r_low = compute_objective(low)
    r_high = compute_objective(high)
    assert r_high.value > r_low.value


# ---------------------------------------------------------------------------
# Section 11: Monotonic improvement — policy coherence
# ---------------------------------------------------------------------------


def test_fewer_policy_changes_higher_value():
    stable = ObjectiveSnapshot(policy_changes=0, current_policy="exploit")
    unstable = ObjectiveSnapshot(policy_changes=8, current_policy="exploit")
    r_stable = compute_objective(stable)
    r_unstable = compute_objective(unstable)
    assert r_stable.value > r_unstable.value


def test_same_policy_bonus():
    same = ObjectiveSnapshot(
        current_policy="exploit", previous_policy="exploit", policy_changes=1
    )
    diff = ObjectiveSnapshot(
        current_policy="exploit", previous_policy="explore", policy_changes=1
    )
    r_same = compute_objective(same)
    r_diff = compute_objective(diff)
    assert r_same.value >= r_diff.value


# ---------------------------------------------------------------------------
# Section 12: Component isolation
# ---------------------------------------------------------------------------


def test_only_goal_changes_affect_goal_component():
    base = ObjectiveSnapshot(goal_score=0.3, goal_confidence=0.8)
    better = ObjectiveSnapshot(goal_score=0.7, goal_confidence=0.8)
    r_base = compute_objective(base)
    r_better = compute_objective(better)
    assert r_better.components["goal_progress"] > r_base.components["goal_progress"]
    assert r_better.components["stability"] == r_base.components["stability"]
    assert r_better.components["confidence"] == r_base.components["confidence"]
    assert (
        r_better.components["policy_coherence"] == r_base.components["policy_coherence"]
    )


def test_only_failure_changes_affect_stability():
    base = ObjectiveSnapshot(failure_streak=0, quality_score=0.5)
    worse = ObjectiveSnapshot(failure_streak=5, quality_score=0.5)
    r_base = compute_objective(base)
    r_worse = compute_objective(worse)
    assert r_worse.components["stability"] < r_base.components["stability"]
    assert r_worse.components["confidence"] == r_base.components["confidence"]


# ---------------------------------------------------------------------------
# Section 13: ObjectiveSnapshot serialization
# ---------------------------------------------------------------------------


def test_snapshot_to_dict_has_all_fields():
    snap = ObjectiveSnapshot(
        goal_score=0.5,
        goal_delta=0.1,
        goal_confidence=0.8,
        plan_confidence=0.6,
        plan_steps_completed=3,
        plan_steps_total=5,
        failure_streak=1,
        quality_score=0.65,
        system_confidence=0.7,
        policy_changes=2,
        current_policy="exploit",
        previous_policy="explore",
    )
    d = snap.to_dict()
    assert d["goal_score"] == 0.5
    assert d["plan_steps_completed"] == 3
    assert d["current_policy"] == "exploit"
    assert d["previous_policy"] == "explore"


# ---------------------------------------------------------------------------
# Section 14: ObjectiveResult serialization
# ---------------------------------------------------------------------------


def test_result_to_dict_rounds():
    snap = ObjectiveSnapshot(goal_score=0.123456789)
    result = compute_objective(snap)
    d = result.to_dict()
    assert isinstance(d["value"], float)
    for comp_val in d["components"].values():
        parts = str(comp_val).split(".")
        if len(parts) == 2:
            assert len(parts[1]) <= 4


def test_result_to_dict_structure():
    snap = ObjectiveSnapshot()
    result = compute_objective(snap)
    d = result.to_dict()
    assert set(d.keys()) == {"value", "components", "weights", "snapshot"}
    assert set(d["components"].keys()) == {
        "goal_progress",
        "plan_execution",
        "stability",
        "confidence",
        "policy_coherence",
    }


# ---------------------------------------------------------------------------
# Section 15: Frozen dataclass immutability
# ---------------------------------------------------------------------------


def test_snapshot_frozen():
    snap = ObjectiveSnapshot()
    try:
        snap.goal_score = 0.9  # type: ignore[misc]
        raise AssertionError("Should have raised")
    except AttributeError:
        pass


def test_result_frozen():
    snap = ObjectiveSnapshot()
    result = compute_objective(snap)
    try:
        result.value = 0.9  # type: ignore[misc]
        raise AssertionError("Should have raised")
    except AttributeError:
        pass


# ---------------------------------------------------------------------------
# Section 16: Edge cases
# ---------------------------------------------------------------------------


def test_zero_plan_total_uses_default():
    snap = ObjectiveSnapshot(plan_steps_completed=0, plan_steps_total=0)
    result = compute_objective(snap)
    assert (
        result.components["plan_execution"]
        == compute_objective(
            ObjectiveSnapshot(plan_steps_completed=0, plan_steps_total=0)
        ).components["plan_execution"]
    )


def test_completed_exceeds_total_clamped():
    snap = ObjectiveSnapshot(plan_steps_completed=100, plan_steps_total=10)
    result = compute_objective(snap)
    assert 0.0 <= result.components["plan_execution"] <= 1.0


def test_empty_policy_strings():
    snap = ObjectiveSnapshot(current_policy="", previous_policy="")
    result = compute_objective(snap)
    assert 0.0 <= result.components["policy_coherence"] <= 1.0


def test_matching_empty_policies_no_bonus():
    snap = ObjectiveSnapshot(current_policy="", previous_policy="")
    result = compute_objective(snap)
    snap2 = ObjectiveSnapshot(current_policy="exploit", previous_policy="exploit")
    result2 = compute_objective(snap2)
    assert (
        result2.components["policy_coherence"] >= result.components["policy_coherence"]
    )


# ---------------------------------------------------------------------------
# Section 17: Composite scenarios
# ---------------------------------------------------------------------------


def test_perfect_system():
    snap = ObjectiveSnapshot(
        goal_score=1.0,
        goal_delta=0.1,
        goal_confidence=1.0,
        plan_confidence=1.0,
        plan_steps_completed=10,
        plan_steps_total=10,
        failure_streak=0,
        quality_score=1.0,
        system_confidence=1.0,
        policy_changes=0,
        current_policy="exploit",
        previous_policy="exploit",
    )
    result = compute_objective(snap)
    assert result.value > 0.85


def test_failing_system():
    snap = ObjectiveSnapshot(
        goal_score=0.0,
        goal_delta=-0.3,
        goal_confidence=0.2,
        plan_confidence=0.1,
        plan_steps_completed=0,
        plan_steps_total=10,
        failure_streak=8,
        quality_score=0.1,
        system_confidence=0.1,
        policy_changes=7,
        current_policy="recover",
        previous_policy="pivot",
    )
    result = compute_objective(snap)
    assert result.value < 0.25


def test_mediocre_system():
    snap = ObjectiveSnapshot(
        goal_score=0.5,
        goal_delta=0.0,
        goal_confidence=0.5,
        plan_confidence=0.5,
        plan_steps_completed=5,
        plan_steps_total=10,
        failure_streak=1,
        quality_score=0.5,
        system_confidence=0.5,
        policy_changes=2,
        current_policy="exploit",
        previous_policy="exploit",
    )
    result = compute_objective(snap)
    assert 0.3 <= result.value <= 0.7


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
