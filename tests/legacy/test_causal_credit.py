"""
Test suite: Causal Credit Assignment Layer.

Validates:
    A. Normalized credit allocation across present contributors
    B. Absent contributors handled correctly (zero weight, no crash)
    C. Immediate vs delayed vs structural splits
    D. Delayed credit buffer: add, resolve, expire
    E. Weighted outcome integration into strategy memory
    F. Weighted outcome integration into goal learning
    G. Plan/step credit assignment correctness
    H. Deterministic repeated runs
    I. No ExecutionSpine modifications / no LLM imports
    J. Backward compatibility when no credit data exists

No LLM calls. No randomness. Deterministic assertions only.
"""

import sys

sys.path.insert(0, "/opt/OS")

_pass = 0
_fail = 0
_total = 0


def _section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def _test(label: str, condition: bool, detail: str = "") -> None:
    global _pass, _fail, _total
    _total += 1
    if condition:
        _pass += 1
        extra = f" -- {detail}" if detail else ""
        print(f"  [PASS] {label}{extra}")
    else:
        _fail += 1
        extra = f" -- {detail}" if detail else ""
        print(f"  [FAIL] {label}{extra}")


# ═══════════════════════════════════════════════════════════════════════════════
# 0. Imports
# ═══════════════════════════════════════════════════════════════════════════════

_section("0. Imports")

try:
    from umh.runtime_engine.causal_credit import (
        CreditComponent,
        CreditAllocation,
        CreditSnapshot,
        NO_CREDIT,
        PendingCredit,
        DelayedCreditBuffer,
        compute_credit_allocation,
        compute_credit_horizons,
        compute_credit_snapshot,
        apply_weighted_credit_to_strategy,
        apply_weighted_credit_to_goal,
        apply_weighted_credit_to_plan,
        get_delayed_credit_buffer,
        reset_delayed_credit_buffer,
        _extract_step_signal,
        _extract_plan_signal,
        _extract_strategy_signal,
        _extract_goal_signal,
        _extract_world_state_signal,
        CREDIT_FLOOR,
        DELAYED_HORIZON_WINDOW,
        MAX_PENDING_CREDITS,
        DELAYED_DECAY,
        STRUCTURAL_WEIGHT,
    )
    from umh.runtime_engine.decision_trace import DecisionTrace, build_trace

    _test("all imports succeed", True)
except Exception as e:
    _test("all imports succeed", False, str(e))
    print(f"\nFATAL: Import failed — cannot continue.\n{e}")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


class _FakeTrace:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def _make_trace(**kwargs) -> _FakeTrace:
    defaults = {
        "turn_id": 1,
        "selected_strategy": "clarity",
        "strategy_scores": {"clarity": 0.8, "structured": 0.6},
        "quality_score": 0.75,
        "active_plan_id": "plan_1",
        "plan_confidence": 0.7,
        "plan_step_goal_id": "g1",
        "plan_step_attributed_score": 0.6,
        "active_goal_id": "goal_a",
        "goal_score": 0.8,
        "blended_goals": (("goal_a", 0.7), ("goal_b", 0.3)),
        "world_state_id": "ws_1",
        "world_state_cluster": "cluster_0",
        "world_state_similarity": 0.85,
        "conditioning_bias": {"strategy_bias": {"clarity": 0.1, "structured": -0.05}},
        "strategy_conditioned_scores": None,
    }
    defaults.update(kwargs)
    return _FakeTrace(**defaults)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CreditComponent
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. CreditComponent data model")

cc = CreditComponent(
    name="strategy", raw_signal=0.5, normalized_weight=0.3, reason="strategy:clarity"
)
_test("name correct", cc.name == "strategy")
_test("to_dict has name", cc.to_dict()["name"] == "strategy")
_test("to_dict has reason", cc.to_dict().get("reason") == "strategy:clarity")

cc_no_reason = CreditComponent(name="step", raw_signal=0.2, normalized_weight=0.1)
_test("no reason omitted from to_dict", "reason" not in cc_no_reason.to_dict())


# ═══════════════════════════════════════════════════════════════════════════════
# 2. CreditAllocation
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. CreditAllocation data model")

alloc = CreditAllocation(
    turn_id=1,
    components=(
        CreditComponent(name="strategy", raw_signal=0.5, normalized_weight=0.5),
        CreditComponent(name="goal", raw_signal=0.3, normalized_weight=0.3),
        CreditComponent(name="step", raw_signal=0.2, normalized_weight=0.2),
    ),
    total_signal=1.0,
)
_test("weight_for strategy", abs(alloc.weight_for("strategy") - 0.5) < 1e-9)
_test("weight_for missing", alloc.weight_for("world_state") == 0.0)
_test("to_dict has components", len(alloc.to_dict()["components"]) == 3)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Signal extraction — step
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Signal extraction: step")

t1 = _make_trace(plan_step_attributed_score=0.6, plan_step_goal_id="g1")
sig, entity = _extract_step_signal(t1)
_test("step signal extracted", sig == 0.6, f"signal={sig}")
_test("step entity set", entity == "step:g1")

t2 = _make_trace(plan_step_attributed_score=None)
sig2, entity2 = _extract_step_signal(t2)
_test("no step score → 0", sig2 == 0.0)
_test("no step entity", entity2 == "")

t3 = _make_trace(plan_step_attributed_score=0.0)
sig3, _ = _extract_step_signal(t3)
_test("zero step score → 0", sig3 == 0.0)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Signal extraction — plan
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Signal extraction: plan")

t4 = _make_trace(active_plan_id="plan_1", plan_confidence=0.7)
sig4, entity4 = _extract_plan_signal(t4)
_test("plan signal extracted", sig4 == 0.7, f"signal={sig4}")
_test("plan entity set", entity4 == "plan:plan_1")

t5 = _make_trace(active_plan_id=None)
sig5, entity5 = _extract_plan_signal(t5)
_test("no plan → 0", sig5 == 0.0)

t6 = _make_trace(active_plan_id="plan_1", plan_confidence=None)
sig6, _ = _extract_plan_signal(t6)
_test("plan without confidence → floor", sig6 == CREDIT_FLOOR)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Signal extraction — strategy
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Signal extraction: strategy")

t7 = _make_trace(selected_strategy="clarity", strategy_scores={"clarity": 0.8})
sig7, entity7 = _extract_strategy_signal(t7)
_test("strategy signal extracted", sig7 == 0.8, f"signal={sig7}")
_test("strategy entity set", entity7 == "strategy:clarity")

t8 = _make_trace(selected_strategy="", strategy_scores={})
sig8, _ = _extract_strategy_signal(t8)
_test("no strategy → 0", sig8 == 0.0)

t9 = _make_trace(
    selected_strategy="clarity",
    strategy_scores={"clarity": 0.8},
    strategy_conditioned_scores={"clarity": 0.9},
)
sig9, _ = _extract_strategy_signal(t9)
_test("conditioned score used when present", sig9 == 0.9, f"signal={sig9}")


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Signal extraction — goal
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. Signal extraction: goal")

t10 = _make_trace(
    active_goal_id="goal_a",
    blended_goals=(("goal_a", 0.7), ("goal_b", 0.3)),
    goal_score=0.8,
)
sig10, entity10 = _extract_goal_signal(t10)
expected_goal = (0.7 + 0.8) / 2.0
_test("goal signal is blend avg", abs(sig10 - expected_goal) < 1e-9, f"signal={sig10}")
_test("goal entity set", entity10 == "goal:goal_a")

t11 = _make_trace(active_goal_id=None, blended_goals=None, goal_score=None)
sig11, _ = _extract_goal_signal(t11)
_test("no goal → 0", sig11 == 0.0)

t12 = _make_trace(active_goal_id="goal_a", blended_goals=None, goal_score=0.6)
sig12, _ = _extract_goal_signal(t12)
_test("goal score fallback", sig12 == 0.6, f"signal={sig12}")


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Signal extraction — world state
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Signal extraction: world state")

t13 = _make_trace(
    world_state_id="ws_1",
    world_state_cluster="cluster_0",
    world_state_similarity=0.85,
    conditioning_bias={"strategy_bias": {"clarity": 0.1, "structured": -0.05}},
)
sig13, entity13 = _extract_world_state_signal(t13)
_test("world signal > 0", sig13 > 0, f"signal={sig13}")
_test("world entity has cluster", "cluster_0" in entity13)

t14 = _make_trace(
    world_state_id=None, world_state_similarity=None, conditioning_bias=None
)
sig14, _ = _extract_world_state_signal(t14)
_test("no world state → 0", sig14 == 0.0)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Credit allocation — all contributors present
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Credit allocation: all contributors")

t_full = _make_trace()
alloc_full = compute_credit_allocation(t_full, turn_id=1)
_test("5 components present", len(alloc_full.components) == 5)

weight_sum = sum(c.normalized_weight for c in alloc_full.components)
_test("weights sum to 1.0", abs(weight_sum - 1.0) < 1e-9, f"sum={weight_sum}")

_test("total_signal > 0", alloc_full.total_signal > 0)

for comp in alloc_full.components:
    _test(f"{comp.name} weight > 0", comp.normalized_weight > 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Credit allocation — absent contributors
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Credit allocation: absent contributors")

t_minimal = _make_trace(
    active_plan_id=None,
    plan_confidence=None,
    plan_step_attributed_score=None,
    world_state_id=None,
    world_state_similarity=None,
    conditioning_bias=None,
)
alloc_min = compute_credit_allocation(t_minimal, turn_id=2)
_test("only strategy + goal present", len(alloc_min.components) == 2)

weight_sum_min = sum(c.normalized_weight for c in alloc_min.components)
_test(
    "weights still sum to 1.0",
    abs(weight_sum_min - 1.0) < 1e-9,
    f"sum={weight_sum_min}",
)

names = {c.name for c in alloc_min.components}
_test("strategy in allocation", "strategy" in names)
_test("goal in allocation", "goal" in names)
_test("step not in allocation", "step" not in names)
_test("plan not in allocation", "plan" not in names)
_test("world_state not in allocation", "world_state" not in names)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Credit allocation — no contributors at all
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. Credit allocation: no contributors")

t_empty = _FakeTrace()
alloc_empty = compute_credit_allocation(t_empty, turn_id=3)
_test("no components", len(alloc_empty.components) == 0)
_test("total signal 0", alloc_empty.total_signal == 0.0)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Horizon computation — immediate / delayed / structural
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. Horizon computation")

alloc_h = compute_credit_allocation(_make_trace(), turn_id=5)
immediate, delayed, structural = compute_credit_horizons(alloc_h, [], turn_id=5)

_test("immediate has entries", len(immediate) > 0)
_test("world_state has structural portion", "world_state" in structural)
_test(
    "world_state immediate reduced by structural weight",
    immediate.get("world_state", 0) < alloc_h.weight_for("world_state"),
)

# With prior traces providing delayed signals
prior_traces = [
    _make_trace(
        plan_step_attributed_score=0.7,
        plan_step_goal_id="g_prev",
        plan_confidence=0.6,
        active_plan_id="plan_1",
    ),
    _make_trace(
        plan_step_attributed_score=0.8,
        plan_step_goal_id="g_prev2",
        plan_confidence=0.7,
        active_plan_id="plan_1",
    ),
]
_, delayed_with_prior, _ = compute_credit_horizons(alloc_h, prior_traces, turn_id=5)
_test("delayed credit from prior traces", len(delayed_with_prior) > 0)

# Delayed values should be normalized
if delayed_with_prior:
    d_sum = sum(delayed_with_prior.values())
    _test("delayed normalized to 1.0", abs(d_sum - 1.0) < 1e-6, f"sum={d_sum}")


# ═══════════════════════════════════════════════════════════════════════════════
# 12. CreditSnapshot — full computation
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. CreditSnapshot: full computation")

snap = compute_credit_snapshot(_make_trace(), turn_id=5)
_test("snapshot has allocation", snap.allocation.total_signal > 0)
_test("snapshot has immediate", len(snap.immediate) > 0)
_test("snapshot has credit_reason", snap.credit_reason != "")
_test("snapshot has credited_entities", len(snap.credited_entities) > 0)

snap_dict = snap.to_dict()
_test("to_dict has allocation", "allocation" in snap_dict)
_test("to_dict has immediate", "immediate" in snap_dict)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. CreditSnapshot — no active contributors
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. CreditSnapshot: no contributors")

snap_empty = compute_credit_snapshot(_FakeTrace(), turn_id=10)
_test("no contributors reason", snap_empty.credit_reason == "no_active_contributors")
_test("empty immediate", snap_empty.immediate == {})
_test("empty delayed", snap_empty.delayed == {})


# ═══════════════════════════════════════════════════════════════════════════════
# 14. NO_CREDIT sentinel
# ═══════════════════════════════════════════════════════════════════════════════

_section("14. NO_CREDIT sentinel")

_test("NO_CREDIT turn_id is -1", NO_CREDIT.turn_id == -1)
_test("NO_CREDIT reason is no_data", NO_CREDIT.credit_reason == "no_data")
_test("NO_CREDIT has empty allocation", len(NO_CREDIT.allocation.components) == 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 15. DelayedCreditBuffer — add and expire
# ═══════════════════════════════════════════════════════════════════════════════

_section("15. DelayedCreditBuffer: add + expire")

reset_delayed_credit_buffer()
buf = DelayedCreditBuffer()
buf.add(source_turn=1, contributor="step", credit_weight=0.3, entity="step:g1")
buf.add(source_turn=2, contributor="plan", credit_weight=0.5, entity="plan:p1")
_test("2 pending", buf.pending_count == 2)

# Below floor — should not be added
buf.add(source_turn=3, contributor="step", credit_weight=0.001, entity="step:g2")
_test("below floor ignored", buf.pending_count == 2)

# Expire turn 1 entry (expiry = 1 + 3 = 4, so at turn 5 it's expired)
expired = buf.expire(current_turn=5)
_test("1 expired", expired == 1, f"expired={expired}")
_test("1 remaining", buf.pending_count == 1)


# ═══════════════════════════════════════════════════════════════════════════════
# 16. DelayedCreditBuffer — resolve
# ═══════════════════════════════════════════════════════════════════════════════

_section("16. DelayedCreditBuffer: resolve")

buf2 = DelayedCreditBuffer()
buf2.add(source_turn=5, contributor="step", credit_weight=0.4, entity="step:g1")
buf2.add(source_turn=5, contributor="plan", credit_weight=0.3, entity="plan:p1")

# Resolve with good outcome (> 0.3)
resolved = buf2.resolve(current_turn=7, outcome_score=0.8)
_test("2 resolved", len(resolved) == 2)
_test("buffer empty after resolve", buf2.pending_count == 0)

# Resolve with poor outcome — entries stay
buf3 = DelayedCreditBuffer()
buf3.add(source_turn=5, contributor="step", credit_weight=0.4, entity="step:g1")
resolved_poor = buf3.resolve(current_turn=6, outcome_score=0.1)
_test("0 resolved on poor outcome", len(resolved_poor) == 0)
_test("entry stays on poor outcome", buf3.pending_count == 1)


# ═══════════════════════════════════════════════════════════════════════════════
# 17. DelayedCreditBuffer — max capacity
# ═══════════════════════════════════════════════════════════════════════════════

_section("17. DelayedCreditBuffer: capacity")

buf4 = DelayedCreditBuffer()
for i in range(MAX_PENDING_CREDITS + 5):
    buf4.add(source_turn=i, contributor="step", credit_weight=0.1, entity=f"step:g{i}")
_test("capped at MAX_PENDING_CREDITS", buf4.pending_count == MAX_PENDING_CREDITS)


# ═══════════════════════════════════════════════════════════════════════════════
# 18. DelayedCreditBuffer — deterministic expiration
# ═══════════════════════════════════════════════════════════════════════════════

_section("18. DelayedCreditBuffer: deterministic expiration")

buf5 = DelayedCreditBuffer()
buf5.add(source_turn=10, contributor="step", credit_weight=0.5, entity="step:g1")
# expiry_turn = 10 + 3 = 13
_test("not expired at turn 13", buf5.expire(current_turn=13) == 0)
_test("expired at turn 14", buf5.expire(current_turn=14) == 1)


# ═══════════════════════════════════════════════════════════════════════════════
# 19. Singleton pattern
# ═══════════════════════════════════════════════════════════════════════════════

_section("19. Singleton pattern")

reset_delayed_credit_buffer()
b1 = get_delayed_credit_buffer()
b2 = get_delayed_credit_buffer()
_test("singleton returns same instance", b1 is b2)

reset_delayed_credit_buffer()
b3 = get_delayed_credit_buffer()
_test("reset creates new instance", b3 is not b1)


# ═══════════════════════════════════════════════════════════════════════════════
# 20. Weighted credit: strategy memory
# ═══════════════════════════════════════════════════════════════════════════════

_section("20. Weighted credit: strategy memory")

from umh.strategy.memory import get_strategy_memory, reset_strategy_memory

reset_strategy_memory()
sm = get_strategy_memory()
sm.record_win("clarity", 0.7, confidence=0.8)

ema_before = sm._stats["clarity"].ema_score
apply_weighted_credit_to_strategy("clarity", 0.9, 0.4)
ema_after = sm._stats["clarity"].ema_score
_test(
    "strategy EMA nudged",
    ema_after != ema_before,
    f"before={ema_before:.4f} after={ema_after:.4f}",
)
_test("uses unchanged (correction not observation)", sm._stats["clarity"].uses == 1)

# Below floor — no effect
ema_before2 = sm._stats["clarity"].ema_score
apply_weighted_credit_to_strategy("clarity", 0.9, 0.005)
ema_after2 = sm._stats["clarity"].ema_score
_test("below floor: no change", ema_before2 == ema_after2)


# ═══════════════════════════════════════════════════════════════════════════════
# 21. Weighted credit: goal tracker
# ═══════════════════════════════════════════════════════════════════════════════

_section("21. Weighted credit: goal tracker")

from umh.goals.state import GoalState, GoalRegistry

registry = GoalRegistry()
g = GoalState(
    goal_id="goal_a", description="Test", success_criteria={"m": 0.8}, priority=0.7
)
registry.add_goal(g)
tracker = registry.get_tracker("goal_a")
tracker.update_success(0.5)

score_before = tracker.success_score
apply_weighted_credit_to_goal("goal_a", 0.9, 0.3, registry)
score_after = tracker.success_score
_test(
    "goal score nudged",
    score_after != score_before,
    f"before={score_before:.4f} after={score_after:.4f}",
)
_test("goal uses unchanged (correction)", tracker.uses == 1)


# ═══════════════════════════════════════════════════════════════════════════════
# 22. Weighted credit: plan
# ═══════════════════════════════════════════════════════════════════════════════

_section("22. Weighted credit: plan")

from umh.runtime_engine.hierarchical_planning import (
    Plan,
    PlanStep,
    PlanProgress,
    PlanEngine,
    get_plan_engine,
    reset_plan_engine,
)

reset_plan_engine()
pe = get_plan_engine()
plan = Plan(
    plan_id="plan_test",
    root_goal_id="g1",
    steps=(PlanStep(goal_id="g1", position=0),),
    dependencies=(),
    expected_value=0.6,
    confidence=0.7,
    horizon=1,
    creation_turn=0,
    generation_reason="test",
)
pe._plans["plan_test"] = plan
pe._progress["plan_test"] = PlanProgress(plan_id="plan_test", confidence=0.5)

conf_before = pe._progress["plan_test"].confidence
apply_weighted_credit_to_plan("plan_test", "g1", 0.3, 0.4)
conf_after = pe._progress["plan_test"].confidence
_test(
    "plan confidence nudged",
    conf_after > conf_before,
    f"before={conf_before:.4f} after={conf_after:.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 23. DecisionTrace: credit fields present
# ═══════════════════════════════════════════════════════════════════════════════

_section("23. DecisionTrace: credit fields present")

reset_strategy_memory()
sm2 = get_strategy_memory()
sm2.record_win("clarity", 0.7)

trace_credit = build_trace(
    turn_id=1,
    causal_credit={"total_signal": 1.5, "components": []},
    immediate_credit={"strategy": 0.4, "goal": 0.3},
    delayed_credit={"step:g1": 0.5, "plan:p1": 0.5},
    structural_credit={"world_state": 0.15},
    credit_reason="strategy_dominant",
    credited_entities={"strategy": "strategy:clarity", "goal": "goal:goal_a"},
)
_test("causal_credit set", trace_credit.causal_credit is not None)
_test("immediate_credit set", trace_credit.immediate_credit is not None)
_test("delayed_credit set", trace_credit.delayed_credit is not None)
_test("structural_credit set", trace_credit.structural_credit is not None)
_test("credit_reason set", trace_credit.credit_reason == "strategy_dominant")
_test("credited_entities set", trace_credit.credited_entities is not None)


# ═══════════════════════════════════════════════════════════════════════════════
# 24. DecisionTrace: to_dict serialization
# ═══════════════════════════════════════════════════════════════════════════════

_section("24. DecisionTrace: to_dict serialization")

td = trace_credit.to_dict()
_test("causal_credit in dict", "causal_credit" in td)
_test("immediate_credit in dict", "immediate_credit" in td)
_test("delayed_credit in dict", "delayed_credit" in td)
_test("structural_credit in dict", "structural_credit" in td)
_test("credit_reason in dict", "credit_reason" in td)
_test("credited_entities in dict", "credited_entities" in td)


# ═══════════════════════════════════════════════════════════════════════════════
# 25. DecisionTrace: None fields omitted
# ═══════════════════════════════════════════════════════════════════════════════

_section("25. DecisionTrace: None fields omitted")

reset_strategy_memory()
sm3 = get_strategy_memory()
sm3.record_win("clarity", 0.7)

trace_no_credit = build_trace(turn_id=2)
td_nc = trace_no_credit.to_dict()
_test("causal_credit absent when None", "causal_credit" not in td_nc)
_test("immediate_credit absent when None", "immediate_credit" not in td_nc)
_test("delayed_credit absent when None", "delayed_credit" not in td_nc)
_test("structural_credit absent when None", "structural_credit" not in td_nc)
_test("credit_reason absent when None", "credit_reason" not in td_nc)
_test("credited_entities absent when None", "credited_entities" not in td_nc)


# ═══════════════════════════════════════════════════════════════════════════════
# 26. Determinism: credit allocation
# ═══════════════════════════════════════════════════════════════════════════════

_section("26. Determinism: credit allocation")

t_det = _make_trace()
a1 = compute_credit_allocation(t_det, turn_id=1)
a2 = compute_credit_allocation(t_det, turn_id=1)
_test("allocation deterministic", a1.to_dict() == a2.to_dict())


# ═══════════════════════════════════════════════════════════════════════════════
# 27. Determinism: credit snapshot
# ═══════════════════════════════════════════════════════════════════════════════

_section("27. Determinism: credit snapshot")

s1 = compute_credit_snapshot(t_det, turn_id=1)
s2 = compute_credit_snapshot(t_det, turn_id=1)
_test("snapshot deterministic", s1.to_dict() == s2.to_dict())


# ═══════════════════════════════════════════════════════════════════════════════
# 28. Determinism: horizon computation
# ═══════════════════════════════════════════════════════════════════════════════

_section("28. Determinism: horizon computation")

_priors = [_make_trace(plan_step_attributed_score=0.7, plan_step_goal_id="g_p")]
i1, d1, s1h = compute_credit_horizons(a1, _priors, turn_id=1)
i2, d2, s2h = compute_credit_horizons(a1, _priors, turn_id=1)
_test("immediate deterministic", i1 == i2)
_test("delayed deterministic", d1 == d2)
_test("structural deterministic", s1h == s2h)


# ═══════════════════════════════════════════════════════════════════════════════
# 29. PendingCredit data model
# ═══════════════════════════════════════════════════════════════════════════════

_section("29. PendingCredit data model")

pc = PendingCredit(
    source_turn=5,
    contributor="step",
    credit_weight=0.4,
    entity="step:g1",
    expiry_turn=8,
)
pc_dict = pc.to_dict()
_test("to_dict has source_turn", pc_dict["source_turn"] == 5)
_test("to_dict has contributor", pc_dict["contributor"] == "step")
_test("to_dict has credit_weight", pc_dict["credit_weight"] == 0.4)
_test("to_dict has entity", pc_dict["entity"] == "step:g1")
_test("to_dict has expiry_turn", pc_dict["expiry_turn"] == 8)


# ═══════════════════════════════════════════════════════════════════════════════
# 30. DelayedCreditBuffer: to_dict
# ═══════════════════════════════════════════════════════════════════════════════

_section("30. DelayedCreditBuffer: to_dict")

buf_td = DelayedCreditBuffer()
buf_td.add(source_turn=1, contributor="step", credit_weight=0.3, entity="step:g1")
d = buf_td.to_dict()
_test("to_dict has pending_count", d["pending_count"] == 1)
_test("to_dict has entries", len(d["entries"]) == 1)


# ═══════════════════════════════════════════════════════════════════════════════
# 31. No LLM calls / no randomness / no new deps
# ═══════════════════════════════════════════════════════════════════════════════

_section("31. No LLM / no randomness / no new deps")

with open("/opt/OS/eos/causal_credit.py") as f:
    src = f.read()
_test("no random import in causal_credit", "import random" not in src)
_test("no LLM call in causal_credit", "call_with_fallback" not in src)
_test("no anthropic in causal_credit", "import anthropic" not in src)
_test("no uuid in causal_credit", "import uuid" not in src)


# ═══════════════════════════════════════════════════════════════════════════════
# 32. ExecutionSpine not modified
# ═══════════════════════════════════════════════════════════════════════════════

_section("32. ExecutionSpine not modified")

with open("/opt/OS/eos/execution_spine.py") as f:
    spine_src = f.read()
_test("no causal_credit in spine", "causal_credit" not in spine_src)
_test("no credit_reason in spine", "credit_reason" not in spine_src)


# ═══════════════════════════════════════════════════════════════════════════════
# 33. Backward compat: no credit data produces None fields
# ═══════════════════════════════════════════════════════════════════════════════

_section("33. Backward compat: no credit data")

reset_strategy_memory()
get_strategy_memory().record_win("clarity", 0.7)

trace_bc = build_trace(turn_id=99)
_test("causal_credit is None", trace_bc.causal_credit is None)
_test("credit_reason is None", trace_bc.credit_reason is None)
_test("to_dict has no credit keys", "causal_credit" not in trace_bc.to_dict())


# ═══════════════════════════════════════════════════════════════════════════════
# 34. Horizon window constant
# ═══════════════════════════════════════════════════════════════════════════════

_section("34. Horizon window constant")

_test("DELAYED_HORIZON_WINDOW is 3", DELAYED_HORIZON_WINDOW == 3)
_test("STRUCTURAL_WEIGHT is 0.15", STRUCTURAL_WEIGHT == 0.15)
_test("CREDIT_FLOOR is 0.01", CREDIT_FLOOR == 0.01)
_test("DELAYED_DECAY is 0.7", DELAYED_DECAY == 0.7)


# ═══════════════════════════════════════════════════════════════════════════════
# 35. Credit allocation weight_for on absent name
# ═══════════════════════════════════════════════════════════════════════════════

_section("35. Credit allocation: weight_for edge cases")

empty_alloc = CreditAllocation(turn_id=0, components=(), total_signal=0.0)
_test(
    "empty allocation weight_for returns 0", empty_alloc.weight_for("anything") == 0.0
)


# ═══════════════════════════════════════════════════════════════════════════════
# TOTALS
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  TOTAL: {_total} assertions | PASS: {_pass} | FAIL: {_fail}")
print(f"{'═' * 60}")

if _fail > 0:
    sys.exit(1)
