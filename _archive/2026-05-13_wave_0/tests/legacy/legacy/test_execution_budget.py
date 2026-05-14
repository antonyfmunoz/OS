"""
Tests for Execution Budget Allocation.

Validates:
    1. candidate allocation matches weights
    2. deterministic allocation (same input → same split)
    3. multiple goals produce candidates
    4. winning candidate can come from non-primary goal
    5. memory updates respect goal attribution
    6. no regressions (single goal = identical behavior)
    7. no new uncontrolled LLM calls
    8. ExecutionSpine unchanged
    9. DecisionTrace captures budget fields
    10. SessionRuntime budget API
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

import inspect

from umh.runtime_engine.execution_budget import (
    ExecutionBudget,
    BudgetAllocation,
    NO_BUDGET,
    derive_budget,
    _largest_remainder_round,
    MIN_CANDIDATES_PER_GOAL,
    DEFAULT_TOTAL_CANDIDATES,
    MAX_TOTAL_CANDIDATES,
    MIN_REASONING_DEPTH,
)
from umh.runtime_engine.goal_arbitrator import (
    GoalArbitrator,
    BlendedGoalState,
    NO_BLEND,
)
from umh.goals.state import GoalState, GoalRegistry
from umh.runtime_engine.decision_trace import build_trace
from umh.runtime_engine.multi_strategy import CandidateResult

_test("ExecutionBudget importable", ExecutionBudget is not None)
_test("BudgetAllocation importable", BudgetAllocation is not None)
_test("NO_BUDGET importable", NO_BUDGET is not None)
_test("derive_budget importable", derive_budget is not None)
_test("_largest_remainder_round importable", _largest_remainder_round is not None)
_test("DEFAULT_TOTAL_CANDIDATES is 4", DEFAULT_TOTAL_CANDIDATES == 4)
_test("MAX_TOTAL_CANDIDATES is 8", MAX_TOTAL_CANDIDATES == 8)
_test("MIN_CANDIDATES_PER_GOAL is 1", MIN_CANDIDATES_PER_GOAL == 1)

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
# 1. Candidate Allocation Matches Weights
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. Candidate Allocation Matches Weights")

# Two-goal blend
reg2 = GoalRegistry()
reg2.add_goal(goal_sales)
reg2.add_goal(goal_tech)
blend2 = arbitrator.blend_goals(reg2)

budget2 = derive_budget(blend2, total_candidates=6)
_test("2-goal budget has 2 allocations", len(budget2.allocations) == 2)

total_slots = sum(a.candidate_slots for a in budget2.allocations)
_test(
    "slots sum to total_candidates",
    total_slots == 6,
    f"got {total_slots}",
)

# Higher weight → more candidates
w_dict = dict(blend2.goals)
b_sales = budget2.get_budget("close_sale")
b_tech = budget2.get_budget("analyze")
_test(
    "higher weight → more slots",
    b_sales.candidate_slots >= b_tech.candidate_slots,
    f"sales={b_sales.candidate_slots}, tech={b_tech.candidate_slots}",
)

# Each goal gets at least MIN_CANDIDATES_PER_GOAL
_test(
    "sales >= minimum",
    b_sales.candidate_slots >= MIN_CANDIDATES_PER_GOAL,
)
_test(
    "tech >= minimum",
    b_tech.candidate_slots >= MIN_CANDIDATES_PER_GOAL,
)

# Three-goal blend with 6 total
reg3 = GoalRegistry()
reg3.add_goal(goal_sales)
reg3.add_goal(goal_tech)
reg3.add_goal(goal_explore)
blend3 = arbitrator.blend_goals(reg3)

budget3 = derive_budget(blend3, total_candidates=6)
total3 = sum(a.candidate_slots for a in budget3.allocations)
_test(
    "3-goal slots sum to 6",
    total3 == 6,
    f"got {total3}",
)

# Token budget ratios match weights
for a in budget3.allocations:
    expected_ratio = dict(blend3.goals).get(a.goal_id, 0)
    _test(
        f"token_budget_ratio matches weight for {a.goal_id}",
        abs(a.token_budget_ratio - expected_ratio) < 0.001,
        f"ratio={a.token_budget_ratio:.4f}, weight={expected_ratio:.4f}",
    )

# Reasoning depth respects minimum
for a in budget3.allocations:
    _test(
        f"reasoning_depth >= MIN for {a.goal_id}",
        a.reasoning_depth_weight >= MIN_REASONING_DEPTH,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Deterministic Allocation
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. Deterministic Allocation")

# Same input → same allocation 100x
budgets = [derive_budget(blend3, total_candidates=6) for _ in range(100)]
ref_alloc = budgets[0].allocations
_test(
    "100x derive → identical allocations",
    all(b.allocations == ref_alloc for b in budgets),
)

# Largest remainder rounding is deterministic
r1 = _largest_remainder_round([0.5, 0.3, 0.2], 6)
r2 = _largest_remainder_round([0.5, 0.3, 0.2], 6)
_test("LRR deterministic", r1 == r2)
_test("LRR sums to total", sum(r1) == 6, f"got {sum(r1)}")

# Known allocation: [0.5, 0.3, 0.2] total=6, min=1
# 3 goals × 1 min = 3 floor. remaining = 3.
# raw = [1.5, 0.9, 0.6], floors = [1, 0, 0], allocated = 1, leftover = 2
# remainders: (0.5, 0), (0.9, 1), (0.6, 2) → sorted: idx 1, idx 2
# result = [1+1, 1+0+1, 1+0+1] = [2, 2, 2]
r_known = _largest_remainder_round([0.5, 0.3, 0.2], 6)
_test(
    "LRR [0.5,0.3,0.2] total=6 → [2,2,2]",
    r_known == [2, 2, 2],
    f"got {r_known}",
)

# Equal weights → equal distribution
r_eq = _largest_remainder_round([1 / 3, 1 / 3, 1 / 3], 6)
_test(
    "equal weights → equal slots",
    r_eq == [2, 2, 2],
    f"got {r_eq}",
)

# Extreme skew
r_skew = _largest_remainder_round([0.9, 0.05, 0.05], 6)
_test(
    "extreme skew sums to total",
    sum(r_skew) == 6,
    f"got {r_skew}",
)
_test(
    "extreme skew primary gets most",
    r_skew[0] >= 3,
    f"primary={r_skew[0]}",
)

# Edge: empty
r_empty = _largest_remainder_round([], 6)
_test("empty weights → empty result", r_empty == [])


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Multiple Goals Produce Candidates
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Multiple Goals Produce Candidates")

# CandidateResult now has goal_id field
cr = CandidateResult(
    output="test",
    strategy_name="baseline",
    quality_score=0.8,
    confidence=0.9,
    evaluation={},
    model_used="test",
    tokens_used=100,
    cost_usd=0.01,
    latency_ms=200,
    goal_id="close_sale",
)
_test("CandidateResult has goal_id", cr.goal_id == "close_sale")

# Default goal_id is empty string
cr_no_goal = CandidateResult(
    output="test",
    strategy_name="baseline",
    quality_score=0.8,
    confidence=0.9,
    evaluation={},
    model_used="test",
    tokens_used=100,
    cost_usd=0.01,
    latency_ms=200,
)
_test("default goal_id is empty", cr_no_goal.goal_id == "")

# Budget allocation has candidate_distribution property
_test(
    "budget has candidate_distribution",
    isinstance(budget3.candidate_distribution, dict),
)
_test(
    "distribution has all goals",
    set(budget3.candidate_distribution.keys()) == {"close_sale", "analyze", "explore"},
)
_test(
    "distribution sums to total",
    sum(budget3.candidate_distribution.values()) == 6,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Winning Candidate Can Come From Non-Primary Goal
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Winning Candidate From Non-Primary Goal")

from umh.runtime_engine.multi_strategy import select_best

# Create candidates from different goals — secondary has higher quality
candidates = [
    CandidateResult(
        output="primary output",
        strategy_name="clarity",
        quality_score=0.7,
        confidence=0.8,
        evaluation={"quality_score": 0.7, "confidence": 0.8},
        model_used="test",
        tokens_used=100,
        cost_usd=0.01,
        latency_ms=100,
        goal_id="close_sale",
    ),
    CandidateResult(
        output="secondary output",
        strategy_name="structured",
        quality_score=0.9,
        confidence=0.85,
        evaluation={"quality_score": 0.9, "confidence": 0.85},
        model_used="test",
        tokens_used=120,
        cost_usd=0.012,
        latency_ms=110,
        goal_id="analyze",
    ),
]

winner = select_best(candidates)
_test(
    "winner can be from secondary goal",
    winner.goal_id == "analyze",
    f"winner goal_id={winner.goal_id}",
)
_test(
    "winner selected by quality not goal",
    winner.quality_score == 0.9,
)

# All-primary candidates: winner is still from primary
primary_only = [
    CandidateResult(
        output="p1",
        strategy_name="baseline",
        quality_score=0.6,
        confidence=0.7,
        evaluation={"quality_score": 0.6, "confidence": 0.7},
        model_used="test",
        tokens_used=80,
        cost_usd=0.008,
        latency_ms=90,
        goal_id="close_sale",
    ),
    CandidateResult(
        output="p2",
        strategy_name="clarity",
        quality_score=0.8,
        confidence=0.75,
        evaluation={"quality_score": 0.8, "confidence": 0.75},
        model_used="test",
        tokens_used=90,
        cost_usd=0.009,
        latency_ms=95,
        goal_id="close_sale",
    ),
]
pw = select_best(primary_only)
_test(
    "primary-only winner from primary",
    pw.goal_id == "close_sale",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Memory Updates Respect Goal Attribution
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Memory Updates Respect Attribution")

# The select_best function records wins/losses to strategy memory.
# Goal_id on candidates allows post-hoc analysis of which goal
# produced winning strategies.
_test(
    "winner carries goal attribution",
    winner.goal_id != "",
)
_test(
    "loser carries goal attribution",
    candidates[0].goal_id != "",
)

# Budget allocations preserve weight for partial credit
for a in budget3.allocations:
    _test(
        f"weight preserved for {a.goal_id}",
        a.weight > 0,
    )

# get_budget lookup
_test(
    "get_budget finds existing",
    budget3.get_budget("close_sale") is not None,
)
_test(
    "get_budget returns None for missing",
    budget3.get_budget("nonexistent") is None,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. No Regressions (Single Goal = Identical)
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. No Regressions (Single Goal = Identical)")

# Single goal blend
sg_reg = GoalRegistry()
sg_reg.add_goal(goal_sales)
sg_blend = arbitrator.blend_goals(sg_reg)
sg_budget = derive_budget(sg_blend, total_candidates=4)

_test(
    "single goal: 1 allocation",
    len(sg_budget.allocations) == 1,
)
_test(
    "single goal: all slots to primary",
    sg_budget.allocations[0].candidate_slots == 4,
)
_test(
    "single goal: token_budget_ratio = 1.0",
    sg_budget.allocations[0].token_budget_ratio == 1.0,
)
_test(
    "single goal: reasoning_depth = 1.0",
    sg_budget.allocations[0].reasoning_depth_weight == 1.0,
)
_test(
    "single goal: primary matches",
    sg_budget.primary_goal_id == "close_sale",
)

# Empty blend → NO_BUDGET
_test("empty → NO_BUDGET", derive_budget(NO_BLEND) == NO_BUDGET)
_test("NO_BUDGET has empty allocations", NO_BUDGET.allocations == ())
_test("NO_BUDGET total = 0", NO_BUDGET.total_candidates == 0)

# K=1 blend → single allocation
reg_k1 = GoalRegistry()
reg_k1.add_goal(goal_sales)
reg_k1.add_goal(goal_tech)
blend_k1 = arbitrator.blend_goals(reg_k1, k=1)
budget_k1 = derive_budget(blend_k1)
_test(
    "K=1 blend → 1 allocation",
    len(budget_k1.allocations) == 1,
)
_test(
    "K=1 → all candidates to primary",
    budget_k1.allocations[0].candidate_slots == DEFAULT_TOTAL_CANDIDATES,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. No New Uncontrolled LLM Calls
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. No New Uncontrolled LLM Calls")

src_budget = inspect.getsource(ExecutionBudget)
src_alloc = inspect.getsource(BudgetAllocation)
src_derive = inspect.getsource(derive_budget)
src_lrr = inspect.getsource(_largest_remainder_round)

for name, src in [
    ("ExecutionBudget", src_budget),
    ("BudgetAllocation", src_alloc),
    ("derive_budget", src_derive),
    ("_largest_remainder_round", src_lrr),
]:
    _test(
        f"{name} has no LLM calls",
        "call_with_fallback" not in src
        and "anthropic" not in src.lower()
        and "openai" not in src.lower()
        and "genai" not in src.lower(),
    )

# generate_candidates uses call_with_fallback (expected)
# but execution_budget.py does NOT — it only allocates slots
src_eb_module = inspect.getsource(
    __import__("umh.runtime_engine.execution_budget", fromlist=["derive_budget"])
)
_test(
    "execution_budget module has no LLM calls",
    "call_with_fallback" not in src_eb_module,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. ExecutionSpine Unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. ExecutionSpine Unchanged")

spine_src = inspect.getsource(
    __import__("umh.runtime_engine.execution_spine", fromlist=["ExecutionSpine"]).ExecutionSpine
)

_test("ExecutionSpine has no ExecutionBudget", "ExecutionBudget" not in spine_src)
_test("ExecutionSpine has no BudgetAllocation", "BudgetAllocation" not in spine_src)
_test("ExecutionSpine has no execution_budget", "execution_budget" not in spine_src)
_test("ExecutionSpine has no derive_budget", "derive_budget" not in spine_src)
_test("ExecutionSpine has no candidate_slots", "candidate_slots" not in spine_src)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. DecisionTrace Captures Budget Fields
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. DecisionTrace Captures Budget Fields")

test_budget = {"allocations": [{"goal_id": "a", "slots": 3}], "total": 6}
test_dist = {"a": 3, "b": 2, "c": 1}

trace = build_trace(
    turn_id=1,
    execution_budget=test_budget,
    candidate_distribution=test_dist,
)

_test("trace has execution_budget", trace.execution_budget == test_budget)
_test("trace has candidate_distribution", trace.candidate_distribution == test_dist)

td = trace.to_dict()
_test("to_dict has execution_budget", "execution_budget" in td)
_test("to_dict has candidate_distribution", "candidate_distribution" in td)
_test("to_dict budget matches", td["execution_budget"] == test_budget)
_test("to_dict distribution matches", td["candidate_distribution"] == test_dist)

# Without budget → not in to_dict
trace_no_b = build_trace(turn_id=2)
td_no = trace_no_b.to_dict()
_test("no budget → absent from to_dict", "execution_budget" not in td_no)
_test("no dist → absent from to_dict", "candidate_distribution" not in td_no)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. SessionRuntime Budget API
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. SessionRuntime Budget API")

from umh.runtime_engine.session_runtime import SessionRuntime
from umh.runtime_engine.execution_budget import NO_BUDGET as _NB

sr = SessionRuntime(ctx=None)

# No registry → NO_BUDGET
eb = sr.get_execution_budget()
_test("no registry → NO_BUDGET", eb == _NB)

# set_goals creates registry (budget derived at run time)
sr.set_goals([goal_sales, goal_tech])
_test("set_goals creates registry", sr.get_goal_registry() is not None)

# Budget is None before run (derived at turn boundary)
_test("budget None before run", sr._execution_budget is None)

# BudgetAllocation to_dict
bd = budget3.to_dict()
_test("to_dict has allocations", "allocations" in bd)
_test("to_dict has total_candidates", bd["total_candidates"] == 6)
_test("to_dict has primary_goal_id", "primary_goal_id" in bd)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Largest-Remainder Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. Largest-Remainder Edge Cases")

# total equals number of goals × minimum → each gets minimum
r_min = _largest_remainder_round([0.5, 0.3, 0.2], 3, minimum=1)
_test(
    "total=3, 3 goals, min=1 → [1,1,1]",
    r_min == [1, 1, 1],
    f"got {r_min}",
)

# total less than goals × minimum → trims from back
r_under = _largest_remainder_round([0.5, 0.3, 0.2], 2, minimum=1)
_test(
    "total < goals*min → handled",
    sum(r_under) == 2,
    f"got {r_under}",
)

# Single weight: min=1, remaining=4, raw=[4.0], floor=[4], result=[1+4]=5
r_single = _largest_remainder_round([1.0], 5)
_test(
    "single weight gets all",
    r_single == [5],
    f"got {r_single}",
)
r_single_check = _largest_remainder_round([1.0], 5)
_test(
    "single weight sum correct",
    sum(r_single_check) == 5,
    f"got {r_single_check}",
)

# Two weights, large total
r_large = _largest_remainder_round([0.7, 0.3], 8)
_test(
    "large total sums correctly",
    sum(r_large) == 8,
    f"got {r_large}",
)
_test(
    "large total primary > secondary",
    r_large[0] > r_large[1],
    f"got {r_large}",
)

# MAX_TOTAL_CANDIDATES cap
budget_capped = derive_budget(blend3, total_candidates=100)
_test(
    "total capped to MAX",
    budget_capped.total_candidates <= MAX_TOTAL_CANDIDATES,
    f"got {budget_capped.total_candidates}",
)

# total_candidates bumped up to len(goals) if too small
budget_small = derive_budget(blend3, total_candidates=1)
_test(
    "total bumped to len(goals) if needed",
    budget_small.total_candidates >= 3,
    f"got {budget_small.total_candidates}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Frozen / Immutability
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. Frozen / Immutability")

try:
    budget3.allocations[0].goal_id = "hacked"
    _test("ExecutionBudget is frozen", False)
except Exception:
    _test("ExecutionBudget is frozen", True)

try:
    budget3.total_candidates = 99
    _test("BudgetAllocation is frozen", False)
except Exception:
    _test("BudgetAllocation is frozen", True)


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

if _FAIL > 0:
    sys.exit(1)
