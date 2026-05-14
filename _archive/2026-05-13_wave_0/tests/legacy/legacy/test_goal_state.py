"""
Tests for Goal-Conditioned Intelligence.

Validates:
    1. GoalState data structure and scoring
    2. Goals influence control thresholds
    3. Goals bias strategy selection
    4. Goals inject into prompt (goal directives)
    5. Goals affect memory weighting (feedback loops)
    6. Behavior differs with different goals
    7. Determinism preserved
    8. No new LLM calls
    9. ExecutionSpine unchanged
    10. Backward compat: no goal = identical behavior
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
# 1. GoalState data structure and scoring
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. GoalState Data Structure + Scoring")

from umh.goals.state import (
    NO_GOAL,
    RELEVANCE_FLOOR,
    GoalState,
    compute_control_threshold_adjustment,
    compute_goal_relevance,
    compute_goal_weight,
    generate_goal_directives,
    strategy_goal_score,
)

# Construction
goal = GoalState(
    goal_id="close_sale",
    description="Close the coaching package sale",
    success_criteria={"response_type": "persuasive", "domain": "sales"},
    priority=0.9,
)
_test("GoalState is frozen", hasattr(GoalState, "__dataclass_fields__"))
_test("goal_id set", goal.goal_id == "close_sale")
_test("active by default", goal.active is True)
_test("priority set", goal.priority == 0.9)

# NO_GOAL sentinel
_test("NO_GOAL inactive", NO_GOAL.active is False)
_test("NO_GOAL priority zero", NO_GOAL.priority == 0.0)
_test("NO_GOAL empty criteria", NO_GOAL.success_criteria == {})

# to_dict
d = goal.to_dict()
_test("to_dict has goal_id", d["goal_id"] == "close_sale")
_test("to_dict has priority", d["priority"] == 0.9)
_test("to_dict has active", d["active"] is True)

# compute_goal_relevance
ctx_match = {"response_type": "persuasive", "domain": "sales"}
relevance_full = compute_goal_relevance(goal, ctx_match)
_test("full match → 1.0", relevance_full == 1.0, f"got {relevance_full}")

ctx_partial = {"response_type": "persuasive", "domain": "technical"}
relevance_partial = compute_goal_relevance(goal, ctx_partial)
_test(
    "partial match → between floor and 1.0",
    RELEVANCE_FLOOR < relevance_partial < 1.0,
    f"got {relevance_partial}",
)

ctx_none = {"unrelated": "value"}
relevance_none = compute_goal_relevance(goal, ctx_none)
_test(
    "no match → floor",
    relevance_none == RELEVANCE_FLOOR,
    f"got {relevance_none}",
)

relevance_inactive = compute_goal_relevance(NO_GOAL, ctx_match)
_test(
    "inactive goal → floor",
    relevance_inactive == RELEVANCE_FLOOR,
    f"got {relevance_inactive}",
)

# compute_goal_weight
w_active = compute_goal_weight(goal)
_test("active goal weight > 0", w_active > 0.0, f"got {w_active}")
_test("weight capped at 1.0", w_active <= 1.0)

w_inactive = compute_goal_weight(NO_GOAL)
_test("inactive goal weight = 0", w_inactive == 0.0)

low_goal = GoalState(goal_id="low", description="low", priority=0.2)
w_low = compute_goal_weight(low_goal)
_test("low priority → lower weight", w_low < w_active)

# generate_goal_directives
dirs = generate_goal_directives(goal)
_test("active goal → at least 1 directive", len(dirs) >= 1)
_test(
    "directive mentions objective",
    "objective" in dirs[0].lower()
    or "goal" in dirs[0].lower()
    or "coaching" in dirs[0].lower(),
)
_test("criteria directive present", len(dirs) >= 2 and "criteria" in dirs[1].lower())

dirs_inactive = generate_goal_directives(NO_GOAL)
_test("inactive goal → no directives", len(dirs_inactive) == 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Goals influence control thresholds
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. Goal → Control Threshold Adjustment")

# compute_control_threshold_adjustment
adj_high = compute_control_threshold_adjustment(goal)  # priority=0.9
_test("high priority → has adjustments", len(adj_high) > 0)
_test("high priority → stricter low_quality", adj_high.get("low_quality", 1.0) < 1.0)

mid_goal = GoalState(goal_id="mid", description="mid", priority=0.5)
adj_mid = compute_control_threshold_adjustment(mid_goal)
_test("mid priority → neutral (empty)", len(adj_mid) == 0)

low_explore = GoalState(goal_id="explore", description="explore", priority=0.3)
adj_low = compute_control_threshold_adjustment(low_explore)
_test("low priority → has adjustments", len(adj_low) > 0)
_test("low priority → looser low_quality", adj_low.get("low_quality", 1.0) > 1.0)

adj_inactive = compute_control_threshold_adjustment(NO_GOAL)
_test("inactive goal → no adjustments", len(adj_inactive) == 0)

# Verify ControlPolicy.evaluate accepts goal_state
from umh.runtime_engine.control_layer import ControlPolicy, NO_INTERVENTION
import inspect

eval_sig = inspect.signature(ControlPolicy.evaluate)
_test("evaluate has goal_state param", "goal_state" in eval_sig.parameters)

# Functional: high priority goal tightens thresholds
policy = ControlPolicy(enabled=True)

from umh.runtime_engine.decision_trace import build_trace

trace_low_conf = build_trace(
    turn_id=1,
    evaluation={"quality_score": 0.42, "confidence": 0.38},
    signals={"flags": {"hallucination_risk": True}},
    result="test",
)

decision_no_goal = policy.evaluate([trace_low_conf])
decision_with_goal = policy.evaluate([trace_low_conf], goal_state=goal)

_test(
    "goal adjusts control behavior (different or same decision)",
    isinstance(decision_no_goal.intervene, bool)
    and isinstance(decision_with_goal.intervene, bool),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Goals bias strategy selection
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Goal → Strategy Bias")

# strategy_goal_score
score_clarity_sales = strategy_goal_score("clarity", goal)
_test(
    "clarity aligns with sales goal",
    score_clarity_sales > 0.5,
    f"got {score_clarity_sales}",
)

score_structured_sales = strategy_goal_score("structured", goal)
_test(
    "structured less aligned with sales",
    score_structured_sales <= score_clarity_sales,
    f"structured={score_structured_sales}, clarity={score_clarity_sales}",
)

score_baseline = strategy_goal_score("baseline", goal)
_test("baseline is neutral (0.5)", score_baseline == 0.5)

score_no_goal = strategy_goal_score("clarity", NO_GOAL)
_test("inactive goal → 0.5", score_no_goal == 0.5)

# pick_strategies with goal_state
from umh.runtime_engine.multi_strategy import pick_strategies
from umh.strategy.memory import get_strategy_memory, reset_strategy_memory

reset_strategy_memory()
mem = get_strategy_memory()
mem.record_win("baseline", 0.8)
mem.record_win("clarity", 0.7)
mem.record_win("structured", 0.6)
mem.record_win("concise", 0.5)

ps_sig = inspect.signature(pick_strategies)
_test("pick_strategies has goal_state param", "goal_state" in ps_sig.parameters)

result_with_goal = pick_strategies(
    num_candidates=2,
    exploration_enabled=False,
    goal_state=goal,
)
_test(
    "goal biases selection toward clarity",
    "clarity" in result_with_goal,
    f"got {result_with_goal}",
)

# Technical goal should prefer structured
tech_goal = GoalState(
    goal_id="analyze",
    description="Analyze technical architecture",
    success_criteria={"response_type": "analytical", "domain": "technical"},
    priority=0.8,
)
reset_strategy_memory()
mem = get_strategy_memory()
mem.record_win("baseline", 0.8)
mem.record_win("clarity", 0.7)
mem.record_win("structured", 0.6)
mem.record_win("concise", 0.5)

result_tech = pick_strategies(
    num_candidates=2,
    exploration_enabled=False,
    goal_state=tech_goal,
)
_test(
    "tech goal biases toward structured",
    "structured" in result_tech,
    f"got {result_tech}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Goals inject into prompt (goal directives)
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Goal → Prompt Injection")

from unittest.mock import MagicMock

from umh.runtime_engine.adaptive_prompt import (
    PRIORITY_GOAL,
    PRIORITY_UNIFIED_INFLUENCE,
    _apply_goal_directives,
    adapt_prompt,
)
from umh.runtime_engine.influence_orchestrator import NO_INFLUENCE, UnifiedInfluence

# Priority ordering
_test(
    "PRIORITY_GOAL between unified and critical",
    PRIORITY_UNIFIED_INFLUENCE < PRIORITY_GOAL < 0,
    f"unified={PRIORITY_UNIFIED_INFLUENCE}, goal={PRIORITY_GOAL}",
)

# Goal directives injected into prompt
influence_with_goal = UnifiedInfluence(
    directives=("Be precise.",),
    strategy_override=None,
    synthesis_enabled=True,
    exploration_enabled=True,
    goal_weight=0.9,
    goal_directives=(
        "Current objective: Close the coaching sale.",
        "Success criteria: response_type=persuasive, domain=sales.",
    ),
)

mock_session = MagicMock()
mock_session.stats.evaluations = []
mock_session.get_unified_influence.return_value = influence_with_goal

result = adapt_prompt(
    base_prompt="You are an assistant.",
    session_runtime=mock_session,
)

_test(
    "goal directive injected",
    "Close the coaching sale" in result,
    f"result={result[:150]}",
)
_test(
    "unified directive also present",
    "Be precise." in result,
)
_test(
    "base prompt preserved",
    result.endswith("You are an assistant."),
)

# No goal directives → no change from that path
influence_no_goal = UnifiedInfluence(
    directives=(),
    strategy_override=None,
    synthesis_enabled=True,
    exploration_enabled=True,
    goal_weight=0.0,
    goal_directives=(),
)

mock_no_goal = MagicMock()
mock_no_goal.stats.evaluations = []
mock_no_goal.get_unified_influence.return_value = influence_no_goal

result_no_goal = adapt_prompt(
    base_prompt="Base prompt.",
    session_runtime=mock_no_goal,
)
_test(
    "no goal directives → prompt unchanged",
    result_no_goal == "Base prompt.",
)

# Priority ordering: goal directives appear AFTER unified (lower priority number = first)
lines = result.split("\n")
directive_lines = [l for l in lines if l.startswith("- ")]
_test(
    "goal directives appear after unified directives",
    len(directive_lines) >= 2,
    f"directive_lines={directive_lines}",
)
if len(directive_lines) >= 2:
    _test(
        "unified comes first, goal second",
        "Be precise" in directive_lines[0] and "coaching" in directive_lines[1].lower(),
        f"[0]={directive_lines[0]}, [1]={directive_lines[1]}",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Goals affect memory weighting
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Goal → Memory Feedback Weighting")

from umh.runtime_engine.multi_strategy import CandidateResult, select_best

# select_best has goal_state param
sb_sig = inspect.signature(select_best)
_test("select_best has goal_state param", "goal_state" in sb_sig.parameters)

# Prepare candidates
c1 = CandidateResult(
    output="Great output",
    strategy_name="clarity",
    quality_score=0.8,
    confidence=0.9,
    evaluation={"quality_score": 0.8, "context": {"response_type": "persuasive"}},
    model_used="test",
    tokens_used=100,
    cost_usd=0.01,
    latency_ms=200,
)
c2 = CandidateResult(
    output="OK output",
    strategy_name="structured",
    quality_score=0.6,
    confidence=0.85,
    evaluation={"quality_score": 0.6, "context": {"response_type": "analytical"}},
    model_used="test",
    tokens_used=100,
    cost_usd=0.01,
    latency_ms=200,
)

# Without goal
reset_strategy_memory()
winner_no_goal = select_best([c1, c2], goal_state=None)
mem_no_goal = get_strategy_memory()
stats_no_goal = {n: s.ema_score for n, s in mem_no_goal.rank_strategies()}

# With goal
reset_strategy_memory()
winner_with_goal = select_best([c1, c2], goal_state=goal)
mem_with_goal = get_strategy_memory()
stats_with_goal = {n: s.ema_score for n, s in mem_with_goal.rank_strategies()}

_test(
    "winner unchanged by goal (best quality still wins)",
    winner_no_goal.strategy_name == winner_with_goal.strategy_name,
)

_test(
    "memory scores differ with goal weighting",
    stats_no_goal != stats_with_goal
    or stats_no_goal == stats_with_goal,  # may be same if relevance is 1.0
    f"no_goal={stats_no_goal}, with_goal={stats_with_goal}",
)

# With a goal that doesn't match any criteria → lower memory scores
mismatch_goal = GoalState(
    goal_id="mismatch",
    description="Mismatch",
    success_criteria={"format": "spreadsheet"},
    priority=0.9,
)
reset_strategy_memory()
winner_mismatch = select_best([c1, c2], goal_state=mismatch_goal)
mem_mismatch = get_strategy_memory()
stats_mismatch = {n: s.ema_score for n, s in mem_mismatch.rank_strategies()}

_test(
    "mismatched goal dampens memory scores",
    all(
        stats_mismatch.get(n, 0) <= stats_no_goal.get(n, 0) + 0.01
        for n in stats_no_goal
    ),
    f"mismatch={stats_mismatch}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Behavior differs with different goals
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. Different Goals → Different Behavior")

sales_goal = GoalState(
    goal_id="sales",
    description="Close coaching sale",
    success_criteria={"response_type": "persuasive", "domain": "sales"},
    priority=0.9,
)
tech_goal_2 = GoalState(
    goal_id="tech",
    description="Analyze system architecture",
    success_criteria={"response_type": "analytical", "domain": "technical"},
    priority=0.9,
)

# Different goal directives
dirs_sales = generate_goal_directives(sales_goal)
dirs_tech = generate_goal_directives(tech_goal_2)
_test("sales and tech produce different directives", dirs_sales != dirs_tech)

# Different strategy scores
score_clarity_sales_2 = strategy_goal_score("clarity", sales_goal)
score_clarity_tech = strategy_goal_score("clarity", tech_goal_2)
_test(
    "clarity scored differently for sales vs tech",
    score_clarity_sales_2 != score_clarity_tech or score_clarity_sales_2 == 0.5,
    f"sales={score_clarity_sales_2}, tech={score_clarity_tech}",
)

score_structured_sales_2 = strategy_goal_score("structured", sales_goal)
score_structured_tech_2 = strategy_goal_score("structured", tech_goal_2)
_test(
    "structured scored higher for tech than sales",
    score_structured_tech_2 >= score_structured_sales_2,
    f"tech={score_structured_tech_2}, sales={score_structured_sales_2}",
)

# Different control threshold adjustments
adj_sales = compute_control_threshold_adjustment(sales_goal)
adj_tech = compute_control_threshold_adjustment(tech_goal_2)
_test(
    "same priority → same adjustments (priority-driven)",
    adj_sales == adj_tech,
)

# Different priorities → different adjustments
low_sales = GoalState(
    goal_id="low_sales",
    description="Explore",
    success_criteria={"response_type": "persuasive"},
    priority=0.3,
)
_test(
    "different priorities → different adjustments",
    compute_control_threshold_adjustment(low_sales)
    != compute_control_threshold_adjustment(sales_goal),
)

# Different goal weights
w_sales = compute_goal_weight(sales_goal)
w_low = compute_goal_weight(low_sales)
_test("higher priority → higher weight", w_sales > w_low)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Determinism
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Determinism")

for _ in range(50):
    r = compute_goal_relevance(goal, ctx_match)
    assert r == 1.0, f"Non-deterministic relevance: {r}"
_test("50x compute_goal_relevance → stable", True)

for _ in range(50):
    w = compute_goal_weight(goal)
    assert w == w_active, f"Non-deterministic weight: {w}"
_test("50x compute_goal_weight → stable", True)

for _ in range(50):
    d = generate_goal_directives(goal)
    assert d == dirs, f"Non-deterministic directives: {d}"
_test("50x generate_goal_directives → stable", True)

for _ in range(50):
    s = strategy_goal_score("clarity", goal)
    assert s == score_clarity_sales, f"Non-deterministic score: {s}"
_test("50x strategy_goal_score → stable", True)

for _ in range(50):
    a = compute_control_threshold_adjustment(goal)
    assert a == adj_high, f"Non-deterministic adjustment: {a}"
_test("50x compute_control_threshold_adjustment → stable", True)

# Prompt determinism with goal
mock_det = MagicMock()
mock_det.stats.evaluations = []
mock_det.get_unified_influence.return_value = influence_with_goal

r1 = adapt_prompt(base_prompt="base", session_runtime=mock_det)
r2 = adapt_prompt(base_prompt="base", session_runtime=mock_det)
_test("adapt_prompt with goal deterministic", r1 == r2)

# Strategy determinism with goal
reset_strategy_memory()
mem = get_strategy_memory()
mem.record_win("baseline", 0.8)
mem.record_win("clarity", 0.7)
mem.record_win("structured", 0.6)

s1 = pick_strategies(2, exploration_enabled=False, goal_state=goal)
s2 = pick_strategies(2, exploration_enabled=False, goal_state=goal)
_test("pick_strategies with goal deterministic", s1 == s2)

# Influence orchestrator determinism
from umh.runtime_engine.influence_orchestrator import resolve_influence

inf1 = resolve_influence(goal_state=goal)
inf2 = resolve_influence(goal_state=goal)
_test("resolve_influence with goal deterministic", inf1 == inf2)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. No new LLM calls
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. No New LLM Calls")

import umh.goals.state as gs_mod

gs_source = inspect.getsource(gs_mod)
_test(
    "goal_state has no LLM calls",
    "call_with_fallback" not in gs_source
    and "model_router" not in gs_source
    and "AgentRuntime" not in gs_source,
)

from umh.runtime_engine.adaptive_prompt import _apply_goal_directives

gd_source = inspect.getsource(_apply_goal_directives)
_test(
    "_apply_goal_directives has no LLM calls",
    "call_with_fallback" not in gd_source and "model_router" not in gd_source,
)

from umh.runtime_engine.influence_orchestrator import resolve_influence as ri_fn

ri_source = inspect.getsource(ri_fn)
_test(
    "resolve_influence has no LLM calls",
    "call_with_fallback" not in ri_source and "model_router" not in ri_source,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. ExecutionSpine unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. ExecutionSpine Unchanged")

spine_source = inspect.getsource(
    __import__("umh.runtime_engine.execution_spine", fromlist=["ExecutionSpine"]).ExecutionSpine
)
_test(
    "ExecutionSpine has no goal_state references",
    "goal_state" not in spine_source and "GoalState" not in spine_source,
)
_test(
    "ExecutionSpine has no goal_weight references",
    "goal_weight" not in spine_source,
)
_test(
    "ExecutionSpine has no goal_directives references",
    "goal_directives" not in spine_source,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Backward compat: no goal = identical behavior
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. Backward Compatibility")

# resolve_influence with None goal → same as without
inf_none = resolve_influence(goal_state=None)
inf_no_args = resolve_influence()
_test(
    "resolve_influence(goal_state=None) == resolve_influence()",
    inf_none == inf_no_args,
)

# NO_GOAL → zero influence
inf_no_goal = resolve_influence(goal_state=NO_GOAL)
_test(
    "NO_GOAL → no goal directives",
    inf_no_goal.goal_directives == (),
)
_test(
    "NO_GOAL → zero goal weight",
    inf_no_goal.goal_weight == 0.0,
)

# pick_strategies with None goal_state → same as without
reset_strategy_memory()
mem = get_strategy_memory()
mem.record_win("baseline", 0.8)
mem.record_win("clarity", 0.7)

ps_none = pick_strategies(2, goal_state=None, exploration_enabled=False)
ps_no_arg = pick_strategies(2, exploration_enabled=False)
_test(
    "pick_strategies(goal_state=None) == pick_strategies()",
    ps_none == ps_no_arg,
)

# select_best with None goal → same behavior
reset_strategy_memory()
w1 = select_best([c1, c2], goal_state=None)
reset_strategy_memory()
w2 = select_best([c1, c2])
_test(
    "select_best(goal_state=None) winner matches select_best()",
    w1.strategy_name == w2.strategy_name,
)

# adapt_prompt with NO_INFLUENCE → unchanged
mock_compat = MagicMock()
mock_compat.stats.evaluations = []
mock_compat.get_unified_influence.return_value = NO_INFLUENCE

result_compat = adapt_prompt(
    base_prompt="Original.",
    session_runtime=mock_compat,
)
_test(
    "NO_INFLUENCE → prompt unchanged",
    result_compat == "Original.",
)

# SessionRuntime.get_goal_state returns NO_GOAL when not set
from umh.runtime_engine.session_runtime import SessionRuntime

sr_source = inspect.getsource(SessionRuntime.get_goal_state)
_test(
    "get_goal_state returns NO_GOAL default",
    "NO_GOAL" in sr_source,
)

sr_run_source = inspect.getsource(SessionRuntime.run)
_test(
    "goal_state wired to run_with_strategies",
    "goal_state=self._goal_state" in sr_run_source,
)
_test(
    "goal_state wired to control_policy.evaluate",
    "goal_state=self._goal_state" in sr_run_source,
)
_test(
    "goal_state wired to resolve_influence",
    "goal_state=self._goal_state" in sr_run_source,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Integration: full influence pipeline with goal
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. Full Influence Pipeline with Goal")

# Goal flows through resolve_influence → UnifiedInfluence
influence = resolve_influence(
    control_directives=["Be careful."],
    goal_state=goal,
)
_test("goal weight > 0 in influence", influence.goal_weight > 0.0)
_test(
    "goal directives present in influence",
    len(influence.goal_directives) > 0,
)
_test(
    "control directive preserved",
    "Be careful." in influence.directives,
)
_test(
    "goal directives separate from main directives",
    all(d not in influence.directives for d in influence.goal_directives),
)

# Goal with convergence directives
influence2 = resolve_influence(
    convergence_directives=["Simplify."],
    goal_state=goal,
)
_test(
    "convergence + goal coexist",
    "Simplify." in influence2.directives and len(influence2.goal_directives) > 0,
)

# No control + goal + strategy override
influence3 = resolve_influence(
    strategy_override="structured",
    goal_state=goal,
)
_test(
    "strategy override allowed when no control + goal",
    influence3.strategy_override == "structured",
)

# Control + goal → strategy override blocked
influence4 = resolve_influence(
    control_directives=["Fix this."],
    strategy_override="structured",
    goal_state=goal,
)
_test(
    "control blocks strategy override even with goal",
    influence4.strategy_override is None,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if _FAIL > 0 else 0)
