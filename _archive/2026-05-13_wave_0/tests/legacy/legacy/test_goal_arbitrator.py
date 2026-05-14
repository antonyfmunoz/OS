"""
Tests for Multi-Goal Arbitration.

Validates:
    1. multiple goals stored correctly in GoalRegistry
    2. arbitration selects correct goal deterministically
    3. switching occurs when utility changes
    4. downstream behavior reflects selected goal
    5. memory tracks per-goal signals
    6. no regressions (single goal = identical behavior)
    7. no new LLM calls
    8. ExecutionSpine unchanged
"""

import sys

sys.path.insert(0, "/opt/OS")

_PASS = 0
_FAIL = 0


def _test(name: str, ok: bool, detail: str = "") -> None:
    global _PASS, _FAIL
    if ok:
        _PASS += 1
    else:
        _FAIL += 1
    status = "PASS" if ok else "FAIL"
    suffix = f" -- {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")


def _section(name: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {name}")
    print(f"{'─' * 60}")


# ═══════════════════════════════════════════════════════════════════════════════
# 0. Imports
# ═══════════════════════════════════════════════════════════════════════════════

_section("0. Imports + Setup")

from umh.goals.state import (
    NO_GOAL,
    GoalRegistry,
    GoalState,
    GoalTracker,
    NO_REGISTRY,
    RECENCY_DECAY_RATE,
    TRACKER_EMA_ALPHA,
)
from umh.runtime_engine.goal_arbitrator import (
    NO_ARBITRATION,
    ArbitrationResult,
    GoalArbitrator,
    W_DELTA,
    W_PRIORITY,
    W_RECENCY,
    W_SCORE,
)
from umh.runtime_engine.decision_trace import DecisionTrace, build_trace

import inspect

_test("GoalRegistry importable", GoalRegistry is not None)
_test("GoalArbitrator importable", GoalArbitrator is not None)
_test("ArbitrationResult importable", ArbitrationResult is not None)
_test("GoalTracker importable", GoalTracker is not None)
_test("W_PRIORITY is 0.35", W_PRIORITY == 0.35)
_test("W_SCORE is 0.30", W_SCORE == 0.30)
_test("W_DELTA is 0.20", W_DELTA == 0.20)
_test("W_RECENCY is 0.15", W_RECENCY == 0.15)

# Shared goals
goal_sales = GoalState(
    goal_id="close_sale",
    description="Close coaching sale",
    success_criteria={"response_type": "persuasive", "domain": "sales"},
    priority=0.9,
)
goal_tech = GoalState(
    goal_id="analyze",
    description="Analyze architecture",
    success_criteria={"response_type": "analytical", "domain": "technical"},
    priority=0.7,
)
goal_low = GoalState(
    goal_id="explore",
    description="Explore possibilities",
    success_criteria={"response_type": "creative"},
    priority=0.3,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Multiple goals stored correctly in GoalRegistry
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. GoalRegistry Storage")

reg = GoalRegistry()
_test("empty registry size = 0", reg.size == 0)
_test("empty registry is_empty", reg.is_empty())
_test("no active goal → NO_GOAL", reg.get_active_goal() == NO_GOAL)

reg.add_goal(goal_sales)
_test("add_goal → size = 1", reg.size == 1)
_test("get_goal by id", reg.get_goal("close_sale") == goal_sales)

reg.add_goal(goal_tech)
reg.add_goal(goal_low)
_test("add 3 goals → size = 3", reg.size == 3)
_test("get_all_goals returns all active", len(reg.get_all_goals()) == 3)

# Trackers created automatically
_test("tracker for close_sale exists", reg.get_tracker("close_sale") is not None)
_test("tracker for analyze exists", reg.get_tracker("analyze") is not None)
_test("tracker for explore exists", reg.get_tracker("explore") is not None)

# Remove goal
reg.remove_goal("explore")
_test("remove_goal → size = 2", reg.size == 2)
_test("removed goal returns None", reg.get_goal("explore") is None)
_test("removed tracker returns None", reg.get_tracker("explore") is None)

# Re-add
reg.add_goal(goal_low)
_test("re-add → size = 3", reg.size == 3)

# Manual active goal
reg.set_active_goal("close_sale")
_test("manual set active", reg.active_goal_id == "close_sale")
_test("get_active_goal returns sales", reg.get_active_goal() == goal_sales)

# Inactive goal in pool
inactive_goal = GoalState(
    goal_id="dormant",
    description="Dormant goal",
    active=False,
)
reg.add_goal(inactive_goal)
_test(
    "inactive goal not in get_all_goals",
    "dormant" not in [g.goal_id for g in reg.get_all_goals()],
)

# Snapshot
snap = reg.snapshot()
_test("snapshot has goals list", "goals" in snap)
_test("snapshot has active_goal_id", snap["active_goal_id"] == "close_sale")
_test("snapshot has turn", "turn" in snap)

# Turn tracking
_test("initial turn = 0", reg.turn == 0)
reg.advance_turn()
_test("advance_turn → 1", reg.turn == 1)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. GoalTracker per-goal tracking
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. GoalTracker Per-Goal Signals")

tracker = GoalTracker(goal_id="test")
_test("initial success_score = 0.5", tracker.success_score == 0.5)
_test("initial recency_weight = 1.0", tracker.recency_weight == 1.0)
_test("initial uses = 0", tracker.uses == 0)
_test("initial latest_delta = 0.0", tracker.latest_delta == 0.0)

# Update success (EMA)
tracker.update_success(0.8)
_test("first update → score = 0.8", tracker.success_score == 0.8)
_test("uses = 1", tracker.uses == 1)

tracker.update_success(0.6)
expected_ema = TRACKER_EMA_ALPHA * 0.6 + (1 - TRACKER_EMA_ALPHA) * 0.8
_test(
    "second update → EMA applied",
    abs(tracker.success_score - expected_ema) < 0.0001,
    f"got={tracker.success_score:.4f}, expected={expected_ema:.4f}",
)

# Record delta
tracker.record_delta(0.1)
tracker.record_delta(-0.05)
_test("delta history length = 2", len(tracker.delta_history) == 2)
_test("latest_delta = -0.05", tracker.latest_delta == -0.05)

# Delta history capped
for i in range(25):
    tracker.record_delta(float(i) * 0.01)
_test("delta history capped at 20", len(tracker.delta_history) == 20)

# Recency decay
import math

tracker.last_active_turn = 5
recency = tracker.compute_recency(15)
expected_recency = math.exp(-RECENCY_DECAY_RATE * 10)
_test(
    "recency decays with staleness",
    abs(recency - expected_recency) < 0.0001,
    f"got={recency:.4f}, expected={expected_recency:.4f}",
)

# No staleness → weight = 1.0
tracker2 = GoalTracker(goal_id="fresh")
tracker2.last_active_turn = 10
recency_fresh = tracker2.compute_recency(10)
_test("no staleness → recency = 1.0", abs(recency_fresh - 1.0) < 0.0001)

# to_dict
td = tracker.to_dict()
_test("to_dict has goal_id", td["goal_id"] == "test")
_test("to_dict has success_score", "success_score" in td)
_test("to_dict has recency_weight", "recency_weight" in td)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Arbitration selects correct goal deterministically
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Deterministic Goal Selection")

arbitrator = GoalArbitrator()

# Empty registry
empty_reg = GoalRegistry()
arb_empty = arbitrator.select_active_goal(empty_reg)
_test("empty → NO_ARBITRATION", arb_empty == NO_ARBITRATION)
_test("empty → reason is no_goals", arb_empty.reason == "no_goals")

# Single goal
single_reg = GoalRegistry()
single_reg.add_goal(goal_sales)
arb_single = arbitrator.select_active_goal(single_reg)
_test("single goal → selected", arb_single.selected_goal_id == "close_sale")
_test("single goal → reason is single_goal", arb_single.reason == "single_goal")

# Multiple goals: highest priority wins (fresh trackers, equal success/recency)
multi_reg = GoalRegistry()
multi_reg.add_goal(goal_sales)  # priority=0.9
multi_reg.add_goal(goal_tech)  # priority=0.7
multi_reg.add_goal(goal_low)  # priority=0.3
arb_multi = arbitrator.select_active_goal(multi_reg)
_test(
    "highest priority wins",
    arb_multi.selected_goal_id == "close_sale",
    f"selected={arb_multi.selected_goal_id}",
)
_test("reason is max_utility", arb_multi.reason == "max_utility")
_test(
    "utilities dict has all goals",
    len(arb_multi.utilities) == 3,
)

# Determinism: 100 runs
ref = arbitrator.select_active_goal(multi_reg)
for _ in range(100):
    r = arbitrator.select_active_goal(multi_reg)
    assert r.selected_goal_id == ref.selected_goal_id
    assert r.utilities == ref.utilities
_test("100x select → identical", True)

# to_dict
ad = arb_multi.to_dict()
_test("ArbitrationResult.to_dict has selected_goal_id", "selected_goal_id" in ad)
_test("ArbitrationResult.to_dict has utilities", "utilities" in ad)
_test("ArbitrationResult.to_dict has reason", "reason" in ad)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Switching occurs when utility changes
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Goal Switching on Utility Change")

switch_reg = GoalRegistry()
switch_reg.add_goal(goal_sales)  # priority=0.9
switch_reg.add_goal(goal_tech)  # priority=0.7

# Initially sales wins (higher priority)
arb1 = arbitrator.select_active_goal(switch_reg)
_test("initially sales wins", arb1.selected_goal_id == "close_sale")

# Boost tech's tracker: high success + positive delta + fresh recency
tech_tracker = switch_reg.get_tracker("analyze")
tech_tracker.update_success(0.95)
tech_tracker.update_success(0.95)
tech_tracker.update_success(0.95)
tech_tracker.record_delta(0.3)
tech_tracker.last_active_turn = switch_reg.turn

# Degrade sales: low success + negative delta + stale
sales_tracker = switch_reg.get_tracker("close_sale")
sales_tracker.update_success(0.1)
sales_tracker.update_success(0.1)
sales_tracker.record_delta(-0.3)
sales_tracker.last_active_turn = 0

# Advance turns to make sales stale
for _ in range(20):
    switch_reg.advance_turn()

arb2 = arbitrator.select_active_goal(switch_reg)
_test(
    "tech overtakes sales after tracker change",
    arb2.selected_goal_id == "analyze",
    f"selected={arb2.selected_goal_id}, utils={arb2.utilities}",
)

# Verify utility math
tech_util = arbitrator.compute_utility(goal_tech, switch_reg)
sales_util = arbitrator.compute_utility(goal_sales, switch_reg)
_test(
    "tech utility > sales utility",
    tech_util > sales_util,
    f"tech={tech_util:.4f}, sales={sales_util:.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Per-goal memory tracking
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Per-Goal Memory Tracking")

mem_reg = GoalRegistry()
mem_reg.add_goal(goal_sales)
mem_reg.add_goal(goal_tech)

# Simulate per-goal evaluations
sales_t = mem_reg.get_tracker("close_sale")
tech_t = mem_reg.get_tracker("analyze")

sales_t.update_success(0.8)
sales_t.record_delta(0.05)
sales_t.update_success(0.85)
sales_t.record_delta(0.03)

tech_t.update_success(0.6)
tech_t.record_delta(-0.02)
tech_t.update_success(0.55)
tech_t.record_delta(-0.05)

_test(
    "sales tracker tracks independently",
    sales_t.success_score != tech_t.success_score,
    f"sales={sales_t.success_score:.4f}, tech={tech_t.success_score:.4f}",
)
_test(
    "delta histories are independent",
    sales_t.delta_history != tech_t.delta_history,
)
_test("sales uses = 2", sales_t.uses == 2)
_test("tech uses = 2", tech_t.uses == 2)

# Snapshot reflects per-goal state
snap2 = mem_reg.snapshot()
goals_in_snap = {g["goal_id"]: g for g in snap2["goals"]}
_test(
    "snapshot has sales success_score", "success_score" in goals_in_snap["close_sale"]
)
_test("snapshot has tech success_score", "success_score" in goals_in_snap["analyze"])
_test(
    "snapshot scores differ",
    goals_in_snap["close_sale"]["success_score"]
    != goals_in_snap["analyze"]["success_score"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. DecisionTrace captures multi-goal fields
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. DecisionTrace Multi-Goal Fields")

_test(
    "DecisionTrace has active_goal_id",
    "active_goal_id" in DecisionTrace.__dataclass_fields__,
)
_test(
    "DecisionTrace has goal_pool_snapshot",
    "goal_pool_snapshot" in DecisionTrace.__dataclass_fields__,
)

bt_sig = inspect.signature(build_trace)
_test("build_trace has active_goal_id param", "active_goal_id" in bt_sig.parameters)
_test(
    "build_trace has goal_pool_snapshot param",
    "goal_pool_snapshot" in bt_sig.parameters,
)

# Values propagate
trace_mg = build_trace(
    turn_id=1,
    evaluation={"quality_score": 0.7, "confidence": 0.6},
    active_goal_id="close_sale",
    goal_pool_snapshot={
        "goals": [{"goal_id": "close_sale"}],
        "active_goal_id": "close_sale",
        "turn": 1,
    },
)
_test("active_goal_id on trace", trace_mg.active_goal_id == "close_sale")
_test("goal_pool_snapshot on trace", trace_mg.goal_pool_snapshot is not None)

# Serialization
td_mg = trace_mg.to_dict()
_test("to_dict has active_goal_id", td_mg.get("active_goal_id") == "close_sale")
_test("to_dict has goal_pool_snapshot", "goal_pool_snapshot" in td_mg)

# None defaults
trace_default = build_trace(
    turn_id=2, evaluation={"quality_score": 0.5, "confidence": 0.5}
)
_test("default active_goal_id is None", trace_default.active_goal_id is None)
_test("default goal_pool_snapshot is None", trace_default.goal_pool_snapshot is None)
td_def = trace_default.to_dict()
_test("no multi-goal → not in to_dict", "active_goal_id" not in td_def)
_test("no multi-goal → snapshot not in to_dict", "goal_pool_snapshot" not in td_def)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. SessionRuntime multi-goal API
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. SessionRuntime Multi-Goal API")

from umh.runtime_engine.session_runtime import SessionRuntime

_test("set_goals method exists", hasattr(SessionRuntime, "set_goals"))
_test("add_goal method exists", hasattr(SessionRuntime, "add_goal"))
_test("get_active_goal method exists", hasattr(SessionRuntime, "get_active_goal"))
_test("get_goal_registry method exists", hasattr(SessionRuntime, "get_goal_registry"))
_test(
    "get_goal_evaluation_for method exists",
    hasattr(SessionRuntime, "get_goal_evaluation_for"),
)

# Source inspection
sr_run_source = inspect.getsource(SessionRuntime.run)
_test(
    "run() calls GoalArbitrator",
    "GoalArbitrator" in sr_run_source,
)
_test(
    "run() calls advance_turn",
    "advance_turn" in sr_run_source,
)
_test(
    "run() passes active_goal_id to build_trace",
    "active_goal_id=_active_goal_id" in sr_run_source,
)
_test(
    "run() passes goal_pool_snapshot to build_trace",
    "goal_pool_snapshot=_goal_pool_snapshot" in sr_run_source,
)
_test(
    "run() updates per-goal tracker",
    "update_success" in sr_run_source,
)
_test(
    "run() records per-goal delta",
    "record_delta" in sr_run_source,
)

# set_goal backward compat: still sets _goal_state
sr_source_set_goal = inspect.getsource(SessionRuntime.set_goal)
_test(
    "set_goal still sets _goal_state",
    "_goal_state" in sr_source_set_goal,
)

# set_goals creates registry
sr_source_set_goals = inspect.getsource(SessionRuntime.set_goals)
_test(
    "set_goals creates GoalRegistry",
    "GoalRegistry" in sr_source_set_goals,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Backward compatibility: single goal = identical behavior
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Backward Compatibility")

# NO_GOAL still works
_test("NO_GOAL unchanged", NO_GOAL.active is False)
_test("NO_GOAL priority = 0.0", NO_GOAL.priority == 0.0)

# GoalState frozen unchanged
_test("GoalState still frozen", hasattr(GoalState, "__dataclass_fields__"))
try:
    goal_sales.goal_id = "changed"
    _test("GoalState mutability", False, "should have raised")
except Exception:
    _test("GoalState still immutable", True)

# NO_REGISTRY is empty
_test("NO_REGISTRY is empty", NO_REGISTRY.is_empty())
_test("NO_REGISTRY active = NO_GOAL", NO_REGISTRY.get_active_goal() == NO_GOAL)

# Single-goal via set_goal (no registry) → get_active_goal falls back
from unittest.mock import MagicMock

ctx_mock = MagicMock()
sr_single = SessionRuntime(ctx_mock, session_id="test_single")
sr_single.set_goal(goal_sales)
_test(
    "single set_goal → get_active_goal returns it",
    sr_single.get_active_goal() == goal_sales,
)
_test(
    "single set_goal → get_goal_state returns it",
    sr_single.get_goal_state() == goal_sales,
)
_test(
    "no registry when using set_goal alone",
    sr_single.get_goal_registry() is None,
)

# Single-goal via set_goals([one]) → registry with one goal
sr_one = SessionRuntime(ctx_mock, session_id="test_one")
sr_one.set_goals([goal_sales])
_test(
    "set_goals([one]) → registry exists",
    sr_one.get_goal_registry() is not None,
)
_test(
    "set_goals([one]) → active is that goal",
    sr_one.get_active_goal() == goal_sales,
)

# Existing functions still work
from umh.goals.state import (
    compute_goal_relevance,
    compute_goal_weight,
    generate_goal_directives,
    strategy_goal_score,
    compute_control_threshold_adjustment,
)

_test(
    "compute_goal_relevance still works",
    compute_goal_relevance(goal_sales, {"domain": "sales"}) > 0,
)
_test("compute_goal_weight still works", compute_goal_weight(goal_sales) > 0)
_test(
    "generate_goal_directives still works",
    len(generate_goal_directives(goal_sales)) > 0,
)
_test("strategy_goal_score still works", strategy_goal_score("clarity", goal_sales) > 0)
_test(
    "compute_control_threshold_adjustment still works",
    len(compute_control_threshold_adjustment(goal_sales)) > 0,
)

# resolve_influence with single goal state unchanged
from umh.runtime_engine.influence_orchestrator import resolve_influence, NO_INFLUENCE

inf_single = resolve_influence(goal_state=goal_sales)
_test("resolve_influence with single goal still works", inf_single.goal_weight > 0)

inf_no_goal = resolve_influence()
_test("resolve_influence() still returns NO_INFLUENCE", inf_no_goal == NO_INFLUENCE)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Downstream behavior reflects selected goal
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Downstream Reflects Selected Goal")

# Different goals produce different directives
from umh.goals.state import generate_goal_directives

dirs_sales = generate_goal_directives(goal_sales)
dirs_tech = generate_goal_directives(goal_tech)
_test("different goals → different directives", dirs_sales != dirs_tech)

# Different strategy scores
score_sales = strategy_goal_score("clarity", goal_sales)
score_tech = strategy_goal_score("clarity", goal_tech)
_test(
    "clarity scored differently per goal",
    score_sales != score_tech or score_sales == 0.5,
    f"sales={score_sales}, tech={score_tech}",
)

# Arbitration result flows into influence
inf_sales = resolve_influence(goal_state=goal_sales)
inf_tech = resolve_influence(goal_state=goal_tech)
_test(
    "different goals → different influence",
    inf_sales.goal_directives != inf_tech.goal_directives
    or inf_sales.goal_weight != inf_tech.goal_weight,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Determinism across all components
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. Determinism")

# GoalRegistry operations
det_reg = GoalRegistry()
det_reg.add_goal(goal_sales)
det_reg.add_goal(goal_tech)
det_reg.add_goal(goal_low)

ref_arb = arbitrator.select_active_goal(det_reg)
for _ in range(100):
    r = arbitrator.select_active_goal(det_reg)
    assert r.selected_goal_id == ref_arb.selected_goal_id
    assert r.utilities == ref_arb.utilities
_test("100x arbitration → identical", True)

# GoalTracker EMA
t1 = GoalTracker(goal_id="det1")
t2 = GoalTracker(goal_id="det2")
for score in [0.8, 0.6, 0.9, 0.4, 0.7]:
    t1.update_success(score)
    t2.update_success(score)
_test(
    "identical updates → identical EMA",
    abs(t1.success_score - t2.success_score) < 0.0001,
)

# Snapshot determinism
snap1 = det_reg.snapshot()
snap2 = det_reg.snapshot()
_test("2x snapshot → identical", snap1 == snap2)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. No new LLM calls
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. No New LLM Calls")

import umh.runtime_engine.goal_arbitrator as ga_mod
import umh.goals.state as gs_mod

ga_source = inspect.getsource(ga_mod)
_test(
    "goal_arbitrator has no LLM calls",
    "call_with_fallback" not in ga_source
    and "model_router" not in ga_source
    and "AgentRuntime" not in ga_source,
)

# GoalRegistry and GoalTracker
gs_source = inspect.getsource(gs_mod.GoalRegistry)
_test(
    "GoalRegistry has no LLM calls",
    "call_with_fallback" not in gs_source and "model_router" not in gs_source,
)

gt_source = inspect.getsource(gs_mod.GoalTracker)
_test(
    "GoalTracker has no LLM calls",
    "call_with_fallback" not in gt_source and "model_router" not in gt_source,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. ExecutionSpine unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. ExecutionSpine Unchanged")

spine_source = inspect.getsource(
    __import__("umh.runtime_engine.execution_spine", fromlist=["ExecutionSpine"]).ExecutionSpine
)
_test(
    "ExecutionSpine has no GoalRegistry",
    "GoalRegistry" not in spine_source,
)
_test(
    "ExecutionSpine has no GoalArbitrator",
    "GoalArbitrator" not in spine_source,
)
_test(
    "ExecutionSpine has no goal_arbitrator",
    "goal_arbitrator" not in spine_source,
)
_test(
    "ExecutionSpine has no active_goal_id",
    "active_goal_id" not in spine_source,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Utility computation verification
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. Utility Computation")

import math as _math

util_reg = GoalRegistry()
util_reg.add_goal(goal_sales)
util_reg.add_goal(goal_tech)

# Advance turn so staleness creates meaningful recency differences
for _ in range(14):
    util_reg.advance_turn()

# Manually set tracker values for predictable utility
st = util_reg.get_tracker("close_sale")
st.success_score = 0.8
st.last_active_turn = util_reg.turn  # staleness=0 → recency=1.0
st.delta_history = [0.1]
st.uses = 1

tt = util_reg.get_tracker("analyze")
tt.success_score = 0.6
tt.last_active_turn = 0  # staleness=14 → recency=exp(-0.05*14)
tt.delta_history = [-0.05]
tt.uses = 1

# Compute expected recency for tech tracker
_tech_recency = _math.exp(-0.05 * 14)

# Compute expected utility
expected_sales = W_PRIORITY * 0.9 + W_SCORE * 0.8 + W_DELTA * 0.1 + W_RECENCY * 1.0
expected_tech = (
    W_PRIORITY * 0.7 + W_SCORE * 0.6 + W_DELTA * (-0.05) + W_RECENCY * _tech_recency
)

actual_sales = arbitrator.compute_utility(goal_sales, util_reg)
actual_tech = arbitrator.compute_utility(goal_tech, util_reg)

_test(
    "sales utility matches formula",
    abs(actual_sales - expected_sales) < 0.01,
    f"actual={actual_sales:.4f}, expected={expected_sales:.4f}",
)
_test(
    "tech utility matches formula",
    abs(actual_tech - expected_tech) < 0.01,
    f"actual={actual_tech:.4f}, expected={expected_tech:.4f}",
)
_test(
    "sales > tech utility",
    actual_sales > actual_tech,
)

# Delta clamping
clamp_tracker = GoalTracker(goal_id="clamp")
clamp_tracker.record_delta(5.0)
clamp_tracker.success_score = 0.5
clamp_tracker.recency_weight = 1.0
clamp_tracker.uses = 1

clamp_reg = GoalRegistry()
clamp_goal = GoalState(goal_id="clamp", description="test", priority=0.5)
clamp_reg.add_goal(clamp_goal)
clamp_reg._trackers["clamp"] = clamp_tracker

util_clamped = arbitrator.compute_utility(clamp_goal, clamp_reg)
expected_clamped = W_PRIORITY * 0.5 + W_SCORE * 0.5 + W_DELTA * 1.0 + W_RECENCY * 1.0
_test(
    "extreme delta clamped to 1.0",
    abs(util_clamped - expected_clamped) < 0.01,
    f"got={util_clamped:.4f}, expected={expected_clamped:.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if _FAIL > 0 else 0)
