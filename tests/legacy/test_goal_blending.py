"""
Tests for Multi-Goal Blending.

Validates:
    1. top-K selection is deterministic
    2. weights sum to 1
    3. blending changes downstream behavior
    4. memory updates distribute correctly
    5. prompt directives merge correctly
    6. no regressions (single goal = identical behavior)
    7. no new LLM calls
    8. ExecutionSpine unchanged
    9. DecisionTrace captures blend fields
    10. SessionRuntime blending API
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
# 0. Imports + Setup
# ═══════════════════════════════════════════════════════════════════════════════

_section("0. Imports + Setup")

import math
import inspect

from umh.goals.state import (
    GoalState,
    GoalRegistry,
    GoalTracker,
    NO_GOAL,
    compute_goal_weight,
    generate_goal_directives,
    strategy_goal_score,
)
from umh.runtime_engine.goal_arbitrator import (
    GoalArbitrator,
    BlendedGoalState,
    NO_BLEND,
    ArbitrationResult,
    _stable_softmax,
    _shannon_entropy,
    W_PRIORITY,
    W_SCORE,
    W_DELTA,
    W_RECENCY,
    DEFAULT_BLEND_K,
    SOFTMAX_TEMPERATURE,
)
from umh.runtime_engine.decision_trace import DecisionTrace, build_trace
from umh.runtime_engine.influence_orchestrator import resolve_influence, NO_INFLUENCE

_test("BlendedGoalState importable", BlendedGoalState is not None)
_test("NO_BLEND importable", NO_BLEND is not None)
_test("_stable_softmax importable", _stable_softmax is not None)
_test("_shannon_entropy importable", _shannon_entropy is not None)
_test("DEFAULT_BLEND_K is 3", DEFAULT_BLEND_K == 3)
_test("SOFTMAX_TEMPERATURE is 1.0", SOFTMAX_TEMPERATURE == 1.0)

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
goal_explore = GoalState(
    goal_id="explore",
    description="Explore possibilities",
    success_criteria={"response_type": "creative"},
    priority=0.3,
)

arbitrator = GoalArbitrator()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Top-K Selection is Deterministic
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. Top-K Selection is Deterministic")

reg = GoalRegistry()
reg.add_goal(goal_sales)
reg.add_goal(goal_tech)
reg.add_goal(goal_explore)

blend1 = arbitrator.blend_goals(reg)
blend2 = arbitrator.blend_goals(reg)

_test("blend1 == blend2 (goals)", blend1.goals == blend2.goals)
_test("blend1 == blend2 (primary)", blend1.primary_goal_id == blend2.primary_goal_id)
_test("blend1 == blend2 (entropy)", blend1.entropy == blend2.entropy)

# 100x determinism check
blends = [arbitrator.blend_goals(reg) for _ in range(100)]
_test(
    "100x blend → identical goals",
    all(b.goals == blends[0].goals for b in blends),
)
_test(
    "100x blend → identical primary",
    all(b.primary_goal_id == blends[0].primary_goal_id for b in blends),
)
_test(
    "100x blend → identical entropy",
    all(b.entropy == blends[0].entropy for b in blends),
)

# Top-K selects highest utility goals
_test(
    "primary is highest priority goal",
    blend1.primary_goal_id == "close_sale",
)
_test(
    "3 goals blended (K=3)",
    len(blend1.goals) == 3,
    f"got {len(blend1.goals)}",
)

# K=2 limits to top 2
blend_k2 = arbitrator.blend_goals(reg, k=2)
_test(
    "K=2 → only 2 goals blended",
    len(blend_k2.goals) == 2,
)
_test(
    "K=2 → lowest priority excluded",
    "explore" not in dict(blend_k2.goals),
)

# Deterministic ordering: sorted by utility desc then alphabetical
ids_in_order = [gid for gid, _ in blend1.goals]
_test(
    "goals ordered by utility desc",
    ids_in_order[0] == "close_sale",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Weights Sum to 1
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. Weights Sum to 1")

weight_sum = sum(w for _, w in blend1.goals)
_test(
    "3-goal weights sum to 1.0",
    abs(weight_sum - 1.0) < 1e-10,
    f"sum={weight_sum:.10f}",
)

weight_sum_k2 = sum(w for _, w in blend_k2.goals)
_test(
    "K=2 weights sum to 1.0",
    abs(weight_sum_k2 - 1.0) < 1e-10,
    f"sum={weight_sum_k2:.10f}",
)

# Single goal → weight = 1.0
single_reg = GoalRegistry()
single_reg.add_goal(goal_sales)
blend_single = arbitrator.blend_goals(single_reg)
_test(
    "single goal → weight = 1.0",
    len(blend_single.goals) == 1 and blend_single.goals[0][1] == 1.0,
)

# Empty registry → NO_BLEND
empty_reg = GoalRegistry()
blend_empty = arbitrator.blend_goals(empty_reg)
_test("empty → NO_BLEND", blend_empty == NO_BLEND)

# Higher utility → higher weight
weights_dict = dict(blend1.goals)
_test(
    "sales weight > tech weight",
    weights_dict["close_sale"] > weights_dict["analyze"],
    f"sales={weights_dict['close_sale']:.4f}, tech={weights_dict['analyze']:.4f}",
)
_test(
    "tech weight > explore weight",
    weights_dict["analyze"] > weights_dict["explore"],
    f"tech={weights_dict['analyze']:.4f}, explore={weights_dict['explore']:.4f}",
)

# Softmax unit tests
_test("softmax([1]) = [1.0]", _stable_softmax([1.0]) == [1.0])
_test("softmax([]) = []", _stable_softmax([]) == [])

sm_equal = _stable_softmax([1.0, 1.0, 1.0])
_test(
    "softmax(equal) = uniform",
    all(abs(w - 1 / 3) < 1e-10 for w in sm_equal),
)

sm_sum = sum(_stable_softmax([0.7, 0.4, 0.1]))
_test(
    "softmax sum = 1.0",
    abs(sm_sum - 1.0) < 1e-10,
)

# Stable softmax: large values don't overflow
sm_large = _stable_softmax([1000.0, 999.0, 998.0])
_test(
    "softmax large values don't overflow",
    all(math.isfinite(w) for w in sm_large),
)
_test(
    "softmax large values sum to 1.0",
    abs(sum(sm_large) - 1.0) < 1e-10,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Blending Changes Downstream Behavior
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Blending Changes Downstream Behavior")

# Single goal influence
inf_single = resolve_influence(goal_state=goal_sales)
single_dirs = inf_single.goal_directives
single_weight = inf_single.goal_weight

# Blended influence: should produce different directives
blend_reg = GoalRegistry()
blend_reg.add_goal(goal_sales)
blend_reg.add_goal(goal_tech)
blend_state = arbitrator.blend_goals(blend_reg)

inf_blended = resolve_influence(
    goal_state=goal_sales,
    blended_goal_state=blend_state,
    goal_registry=blend_reg,
)
blended_dirs = inf_blended.goal_directives
blended_weight = inf_blended.goal_weight

_test(
    "blended has more directives than single",
    len(blended_dirs) > len(single_dirs),
    f"blended={len(blended_dirs)}, single={len(single_dirs)}",
)

_test(
    "blended weight differs from single",
    abs(blended_weight - single_weight) > 0.01,
    f"blended={blended_weight:.4f}, single={single_weight:.4f}",
)

# Primary goal directives appear first
_test(
    "primary directives first in blend",
    blended_dirs[0] == single_dirs[0],
    f"first_blend='{blended_dirs[0][:40]}...', first_single='{single_dirs[0][:40]}...'",
)

# Secondary goal adds new directives
tech_dirs = generate_goal_directives(goal_tech)
_test(
    "tech directives present in blend",
    any("Analyze architecture" in d for d in blended_dirs),
)

# Strategy scoring differs with blending
score_single = strategy_goal_score("clarity", goal_sales)
score_tech = strategy_goal_score("structured", goal_tech)
_test(
    "clarity scores high for sales",
    score_single > 0.5,
    f"score={score_single}",
)
_test(
    "structured scores high for tech",
    score_tech > 0.5,
    f"score={score_tech}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Memory Updates Distribute Correctly
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Memory Updates Distribute Correctly")

dist_reg = GoalRegistry()
dist_reg.add_goal(goal_sales)
dist_reg.add_goal(goal_tech)

# Record initial tracker states
t_sales = dist_reg.get_tracker("close_sale")
t_tech = dist_reg.get_tracker("analyze")
t_sales.success_score = 0.5
t_tech.success_score = 0.5
t_sales.uses = 1
t_tech.uses = 1

# Simulate blended update with weights
blend_for_dist = arbitrator.blend_goals(dist_reg)
w_dict = dict(blend_for_dist.goals)
w_sales = w_dict.get("close_sale", 0)
w_tech = w_dict.get("analyze", 0)

goal_score = 0.8
goal_delta = 0.1

# Simulate partial credit (same logic as SessionRuntime)
primary_gid = blend_for_dist.primary_goal_id
for bgid, bw in blend_for_dist.goals:
    btracker = dist_reg.get_tracker(bgid)
    if btracker is not None:
        btracker.update_success(goal_score * bw)
        btracker.record_delta(goal_delta * (1.0 if bgid == primary_gid else bw))

_test(
    "primary tracker updated",
    t_sales.uses == 2,
)
_test(
    "secondary tracker updated",
    t_tech.uses == 2,
)

# Primary gets weighted score
expected_sales_score = 0.3 * (goal_score * w_sales) + 0.7 * 0.5
_test(
    "primary score is EMA of weighted goal_score",
    abs(t_sales.success_score - expected_sales_score) < 0.01,
    f"got={t_sales.success_score:.4f}, expected={expected_sales_score:.4f}",
)

# Primary gets full delta
_test(
    "primary delta = full delta",
    t_sales.latest_delta == goal_delta,
    f"got={t_sales.latest_delta}",
)

# Secondary gets weighted delta
expected_tech_delta = goal_delta * w_tech
_test(
    "secondary delta = weighted delta",
    abs(t_tech.latest_delta - expected_tech_delta) < 0.001,
    f"got={t_tech.latest_delta:.4f}, expected={expected_tech_delta:.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Prompt Directives Merge Correctly
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Prompt Directives Merge Correctly")

merge_reg = GoalRegistry()
merge_reg.add_goal(goal_sales)
merge_reg.add_goal(goal_tech)
merge_reg.add_goal(goal_explore)
merge_blend = arbitrator.blend_goals(merge_reg)

inf_merged = resolve_influence(
    goal_state=goal_sales,
    blended_goal_state=merge_blend,
    goal_registry=merge_reg,
)

merged_dirs = inf_merged.goal_directives

_test(
    "merged directives not empty",
    len(merged_dirs) > 0,
)

# Check ordering: primary goal directives first
sales_dirs = generate_goal_directives(goal_sales)
_test(
    "sales directives appear first",
    merged_dirs[0] == sales_dirs[0],
)

# No duplicates
_test(
    "no duplicate directives",
    len(merged_dirs) == len(set(merged_dirs)),
)

# All goals contribute directives
tech_dirs_set = set(generate_goal_directives(goal_tech))
explore_dirs_set = set(generate_goal_directives(goal_explore))
merged_set = set(merged_dirs)

_test(
    "tech directives present",
    len(tech_dirs_set & merged_set) > 0,
)
_test(
    "explore directives present",
    len(explore_dirs_set & merged_set) > 0,
)

# Weight is a blend, not just primary
single_sales_weight = compute_goal_weight(goal_sales)
_test(
    "blended weight < single primary weight",
    inf_merged.goal_weight < single_sales_weight,
    f"blended={inf_merged.goal_weight:.4f}, single={single_sales_weight:.4f}",
)

# Without blend → only primary directives
inf_no_blend = resolve_influence(goal_state=goal_sales)
_test(
    "no blend → only sales directives",
    set(inf_no_blend.goal_directives) == set(sales_dirs),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. No Regressions (Single Goal = Identical)
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. No Regressions (Single Goal = Identical)")

# Single goal blend = same as single goal arbitration
sg_reg = GoalRegistry()
sg_reg.add_goal(goal_sales)

sg_blend = arbitrator.blend_goals(sg_reg)
sg_arb = arbitrator.select_active_goal(sg_reg)

_test(
    "single goal: primary matches arbitration",
    sg_blend.primary_goal_id == sg_arb.selected_goal_id,
)
_test(
    "single goal: weight = 1.0",
    sg_blend.goals[0][1] == 1.0,
)
_test(
    "single goal: entropy = 0.0",
    sg_blend.entropy == 0.0,
)

# Single goal influence via blend = same as direct
inf_sg_blend = resolve_influence(
    goal_state=goal_sales,
    blended_goal_state=sg_blend,
    goal_registry=sg_reg,
)
inf_sg_direct = resolve_influence(goal_state=goal_sales)

_test(
    "single goal: directives match",
    inf_sg_blend.goal_directives == inf_sg_direct.goal_directives,
)
_test(
    "single goal: weight matches",
    abs(inf_sg_blend.goal_weight - inf_sg_direct.goal_weight) < 0.001,
    f"blend={inf_sg_blend.goal_weight:.4f}, direct={inf_sg_direct.goal_weight:.4f}",
)

# K=1 forced → identical to single
k1_blend = arbitrator.blend_goals(reg, k=1)
_test(
    "K=1: only primary in blend",
    len(k1_blend.goals) == 1,
)
_test(
    "K=1: weight = 1.0",
    k1_blend.goals[0][1] == 1.0,
)
_test(
    "K=1: entropy = 0.0",
    k1_blend.entropy == 0.0,
)

# Empty → NO_BLEND
_test("empty blend is NO_BLEND", arbitrator.blend_goals(GoalRegistry()) == NO_BLEND)

# NO_BLEND has empty primary
_test("NO_BLEND primary is empty", NO_BLEND.primary_goal_id == "")
_test("NO_BLEND goals is empty", NO_BLEND.goals == ())

# No blend param → falls back to single goal path
inf_no_blend_param = resolve_influence(goal_state=goal_sales)
_test(
    "no blend param → uses single goal path",
    inf_no_blend_param.goal_weight == single_sales_weight,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. No New LLM Calls
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. No New LLM Calls")

src_arb = inspect.getsource(GoalArbitrator)
src_blend = inspect.getsource(BlendedGoalState)
src_softmax = inspect.getsource(_stable_softmax)
src_entropy = inspect.getsource(_shannon_entropy)

for name, src in [
    ("GoalArbitrator", src_arb),
    ("BlendedGoalState", src_blend),
    ("_stable_softmax", src_softmax),
    ("_shannon_entropy", src_entropy),
]:
    _test(
        f"{name} has no LLM calls",
        "call_with_fallback" not in src
        and "anthropic" not in src.lower()
        and "openai" not in src.lower()
        and "genai" not in src.lower(),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 8. ExecutionSpine Unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. ExecutionSpine Unchanged")

spine_src = inspect.getsource(
    __import__("umh.runtime_engine.execution_spine", fromlist=["ExecutionSpine"]).ExecutionSpine
)

_test("ExecutionSpine has no BlendedGoalState", "BlendedGoalState" not in spine_src)
_test("ExecutionSpine has no blend_goals", "blend_goals" not in spine_src)
_test("ExecutionSpine has no blended_goal", "blended_goal" not in spine_src)
_test("ExecutionSpine has no GoalRegistry", "GoalRegistry" not in spine_src)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. DecisionTrace Captures Blend Fields
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. DecisionTrace Captures Blend Fields")

# Build trace with blend fields
test_blend_goals = (("close_sale", 0.6), ("analyze", 0.4))
trace = build_trace(
    turn_id=1,
    blended_goals=test_blend_goals,
    blended_primary_goal_id="close_sale",
    blended_entropy=0.673,
)

_test("trace has blended_goals", trace.blended_goals == test_blend_goals)
_test(
    "trace has blended_primary_goal_id", trace.blended_primary_goal_id == "close_sale"
)
_test("trace has blended_entropy", trace.blended_entropy == 0.673)

# to_dict serialization
td = trace.to_dict()
_test("to_dict has blended_goals", "blended_goals" in td)
_test(
    "to_dict blended_goals is list of tuples",
    td["blended_goals"] == [("close_sale", 0.6), ("analyze", 0.4)],
)
_test(
    "to_dict has blended_primary_goal_id", td["blended_primary_goal_id"] == "close_sale"
)
_test("to_dict has blended_entropy", td["blended_entropy"] == 0.673)

# Without blend fields → not in to_dict
trace_no_blend = build_trace(turn_id=2)
td_no = trace_no_blend.to_dict()
_test("no blend → blended_goals absent", "blended_goals" not in td_no)
_test("no blend → blended_primary absent", "blended_primary_goal_id" not in td_no)
_test("no blend → blended_entropy absent", "blended_entropy" not in td_no)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. SessionRuntime Blending API
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. SessionRuntime Blending API")

from umh.runtime_engine.session_runtime import SessionRuntime

sr = SessionRuntime(ctx=None)

# get_blended_goal returns NO_BLEND when no registry
from umh.runtime_engine.goal_arbitrator import NO_BLEND as _NB

bg = sr.get_blended_goal()
_test("no registry → NO_BLEND", bg == _NB)

# set_goals creates registry + blended state after run would execute
sr.set_goals([goal_sales, goal_tech])
_test("set_goals creates registry", sr.get_goal_registry() is not None)

# get_active_goal still works (backward compat)
active = sr.get_active_goal()
_test(
    "get_active_goal returns a GoalState",
    hasattr(active, "goal_id"),
)

# _blended_goal_state is None before run (blend happens at turn boundary)
_test(
    "blend is None before first run",
    sr._blended_goal_state is None,
)

# set_goal backward compat
sr2 = SessionRuntime(ctx=None)
sr2.set_goal(goal_sales)
_test(
    "set_goal still works",
    sr2.get_goal_state().goal_id == "close_sale",
)

# add_goal works
sr3 = SessionRuntime(ctx=None)
sr3.add_goal(goal_sales)
sr3.add_goal(goal_tech)
_test(
    "add_goal creates registry",
    sr3.get_goal_registry() is not None,
)
_test(
    "add_goal registry has 2 goals",
    sr3.get_goal_registry().size == 2,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. BlendedGoalState API
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. BlendedGoalState API")

bg_state = BlendedGoalState(
    goals=(("a", 0.6), ("b", 0.3), ("c", 0.1)),
    primary_goal_id="a",
    entropy=0.8,
)

_test("weights property", bg_state.weights == {"a": 0.6, "b": 0.3, "c": 0.1})
_test("weight_for existing", bg_state.weight_for("a") == 0.6)
_test("weight_for missing", bg_state.weight_for("z") == 0.0)
_test("to_dict has goals", "goals" in bg_state.to_dict())
_test("to_dict rounds weights", bg_state.to_dict()["entropy"] == 0.8)

# Frozen check
try:
    bg_state.primary_goal_id = "x"
    _test("BlendedGoalState is frozen", False)
except Exception:
    _test("BlendedGoalState is frozen", True)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Entropy Calculations
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. Entropy Calculations")

# Uniform distribution → maximum entropy
ent_uniform = _shannon_entropy([1 / 3, 1 / 3, 1 / 3])
max_ent = math.log(3)
_test(
    "uniform → max entropy",
    abs(ent_uniform - max_ent) < 1e-10,
    f"got={ent_uniform:.6f}, expected={max_ent:.6f}",
)

# Single weight → zero entropy
ent_single = _shannon_entropy([1.0])
_test("single weight → entropy = 0", ent_single == 0.0)

# Concentrated → low entropy
ent_conc = _shannon_entropy([0.99, 0.01])
_test(
    "concentrated → low entropy",
    ent_conc < 0.1,
    f"entropy={ent_conc:.6f}",
)

# Blend entropy matches
blend_weights = [w for _, w in blend1.goals]
expected_ent = _shannon_entropy(blend_weights)
_test(
    "blend entropy matches manual calc",
    abs(blend1.entropy - expected_ent) < 1e-10,
)

# Single goal blend → entropy = 0
_test("single goal blend entropy = 0", blend_single.entropy == 0.0)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Control/Convergence Priority Preserved
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. Control/Convergence Priority Preserved")

# Control directives override — blend doesn't bypass
inf_ctrl_blend = resolve_influence(
    control_directives=["safety: reduce risk"],
    goal_state=goal_sales,
    blended_goal_state=blend_state,
    goal_registry=blend_reg,
)
_test(
    "control + blend → synthesis disabled",
    not inf_ctrl_blend.synthesis_enabled,
)
_test(
    "control + blend → exploration disabled",
    not inf_ctrl_blend.exploration_enabled,
)
_test(
    "control directives preserved",
    "safety: reduce risk" in inf_ctrl_blend.directives,
)

# Convergence suppression not bypassed by blend
inf_conv_blend = resolve_influence(
    convergence_directives=["simplify"],
    synthesis_suppressed=True,
    goal_state=goal_sales,
    blended_goal_state=blend_state,
    goal_registry=blend_reg,
)
_test(
    "convergence + blend → synthesis disabled",
    not inf_conv_blend.synthesis_enabled,
)

# Goal gating still works with blend
inf_neg_blend = resolve_influence(
    goal_state=goal_sales,
    goal_progress_signal=-0.1,
    blended_goal_state=blend_state,
    goal_registry=blend_reg,
)
_test(
    "negative delta + blend → exploration disabled",
    not inf_neg_blend.exploration_enabled,
)
_test(
    "negative delta → gating reason set",
    inf_neg_blend.goal_gating_reason is not None,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════

_section("14. Edge Cases")

# K larger than pool → uses all goals
reg_2 = GoalRegistry()
reg_2.add_goal(goal_sales)
reg_2.add_goal(goal_tech)
blend_k5 = arbitrator.blend_goals(reg_2, k=5)
_test(
    "K>pool → uses all available",
    len(blend_k5.goals) == 2,
)

# All equal priority goals
eq_reg = GoalRegistry()
eq1 = GoalState(goal_id="a", description="A", priority=0.5)
eq2 = GoalState(goal_id="b", description="B", priority=0.5)
eq3 = GoalState(goal_id="c", description="C", priority=0.5)
eq_reg.add_goal(eq1)
eq_reg.add_goal(eq2)
eq_reg.add_goal(eq3)
blend_eq = arbitrator.blend_goals(eq_reg)
eq_weights = [w for _, w in blend_eq.goals]
_test(
    "equal priorities → near-equal weights",
    max(eq_weights) - min(eq_weights) < 0.05,
    f"weights={[round(w, 4) for w in eq_weights]}",
)

# Blend with no registry → falls back to single goal
inf_blend_no_reg = resolve_influence(
    goal_state=goal_sales,
    blended_goal_state=blend_state,
)
_test(
    "blend + no registry → uses single goal path",
    inf_blend_no_reg.goal_weight == single_sales_weight,
)

# Softmax with zero temperature would cause issues — but we default to 1.0
_test(
    "default temperature is 1.0",
    SOFTMAX_TEMPERATURE == 1.0,
)

# Goal not in registry → skipped in directive merge
partial_reg = GoalRegistry()
partial_reg.add_goal(goal_sales)
# blend_state references "analyze" but registry only has "close_sale"
inf_partial = resolve_influence(
    goal_state=goal_sales,
    blended_goal_state=blend_state,
    goal_registry=partial_reg,
)
_test(
    "missing goal in registry → skipped gracefully",
    inf_partial.goal_weight > 0,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

if _FAIL > 0:
    sys.exit(1)
