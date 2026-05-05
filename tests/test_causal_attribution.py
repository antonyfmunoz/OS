"""
Tests for causal attribution layer.

Proves:
  1. Credit distributes correctly across factors
  2. Weights always sum to 1.0
  3. Edge cases: single factor, missing signals, all-zero signals
  4. Determinism: same trace → same attribution
  5. No regression to existing outcome feedback
  6. No new LLM calls
  7. ExecutionSpine unchanged
  8. Full SessionRuntime pipeline with attribution
"""

import sys
import os
import math

sys.path.insert(0, "/opt/OS")
os.environ.setdefault("EOS_TEST_MODE", "1")

PASS = 0
FAIL = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        suffix = f" -- {detail}" if detail else ""
        print(f"  [FAIL] {label}{suffix}")


def section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


# ─────────────────────────────────────────────────────────────
section("1. Imports")
# ─────────────────────────────────────────────────────────────

try:
    from umh.runtime_engine.causal_attribution import (
        AttributionWeights,
        EQUAL_ATTRIBUTION,
        EQUAL_WEIGHT,
        SIGNAL_FLOOR,
        compute_attribution,
    )

    check("causal_attribution imports", True)
except Exception as e:
    check("causal_attribution imports", False, str(e))

try:
    from umh.runtime_engine.outcome_feedback import (
        Outcome,
        OutcomeSource,
        OutcomeStore,
        apply_outcome_to_strategy_memory,
        apply_outcome_to_directive_memory,
        apply_outcome_to_goal_tracker,
    )

    check("outcome_feedback imports", True)
except Exception as e:
    check("outcome_feedback imports", False, str(e))

try:
    from umh.runtime_engine.decision_trace import DecisionTrace, build_trace

    check("decision_trace imports", True)
except Exception as e:
    check("decision_trace imports", False, str(e))

try:
    from umh.strategy.memory import get_strategy_memory, reset_strategy_memory

    check("strategy_memory imports", True)
except Exception as e:
    check("strategy_memory imports", False, str(e))

try:
    from umh.runtime_engine.directive_memory import get_directive_memory, reset_directive_memory

    check("directive_memory imports", True)
except Exception as e:
    check("directive_memory imports", False, str(e))

try:
    from umh.goals.state import GoalState, GoalRegistry, GoalTracker

    check("goal_state imports", True)
except Exception as e:
    check("goal_state imports", False, str(e))


# ─────────────────────────────────────────────────────────────
section("2. AttributionWeights Model")
# ─────────────────────────────────────────────────────────────

w = AttributionWeights(strategy_weight=0.5, directive_weight=0.3, goal_weight=0.2)
check("created", True)
check("strategy_weight", w.strategy_weight == 0.5)
check("directive_weight", w.directive_weight == 0.3)
check("goal_weight", w.goal_weight == 0.2)
check("context_weight defaults to 0", w.context_weight == 0.0)
check("reason defaults to equal_split", w.reason == "equal_split")
check("sum = 1.0", abs(w.sum() - 1.0) < 1e-9, f"got {w.sum()}")
check("frozen", True)
try:
    w.strategy_weight = 0.9  # type: ignore
    check("frozen enforced", False, "mutation allowed")
except (AttributeError, TypeError):
    check("frozen enforced", True)

d = w.to_dict()
check("to_dict has strategy_weight", "strategy_weight" in d)
check("to_dict has directive_weight", "directive_weight" in d)
check("to_dict has goal_weight", "goal_weight" in d)
check("to_dict has reason", "reason" in d)
check("to_dict no context_weight when 0", "context_weight" not in d)

w2 = AttributionWeights(
    strategy_weight=0.4, directive_weight=0.3, goal_weight=0.2, context_weight=0.1
)
d2 = w2.to_dict()
check("to_dict has context_weight when >0", "context_weight" in d2)
check("sum with context = 1.0", abs(w2.sum() - 1.0) < 1e-9)


# ─────────────────────────────────────────────────────────────
section("3. EQUAL_ATTRIBUTION Sentinel")
# ─────────────────────────────────────────────────────────────

check(
    "equal weights sum to 1.0",
    abs(EQUAL_ATTRIBUTION.sum() - 1.0) < 1e-9,
    f"got {EQUAL_ATTRIBUTION.sum()}",
)
check(
    "each weight is 1/3",
    abs(EQUAL_ATTRIBUTION.strategy_weight - 1.0 / 3.0) < 1e-9,
)
check("reason is equal_split", EQUAL_ATTRIBUTION.reason == "equal_split")


# ─────────────────────────────────────────────────────────────
section("4. compute_attribution — Rich Trace")
# ─────────────────────────────────────────────────────────────

# Build a trace with strategy_scores, strategy_selection with directive_scores,
# blended_goals, and active_goal_id
rich_trace = build_trace(
    turn_id=1,
    evaluation={"quality_score": 0.8, "confidence": 0.9},
    strategy_selection={
        "enabled": True,
        "candidates": 3,
        "selected_strategy": "clarity",
        "candidate_scores": {"clarity": 0.75, "structured": 0.60},
        "directive_scores": {"clarity": 0.65, "structured": 0.50},
    },
    goal_score=0.7,
    active_goal_id="close_sale",
    blended_goals=(("close_sale", 0.8), ("analyze", 0.2)),
    blended_primary_goal_id="close_sale",
)


# Manually set strategy_scores via a fresh trace since build_trace reads from
# the global strategy memory singleton (which may be empty in tests).
# We'll construct a minimal object with the needed attributes.
class MockTrace:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            object.__setattr__(self, k, v)


mt = MockTrace(
    selected_strategy="clarity",
    strategy_scores={"clarity": 0.75, "structured": 0.60},
    strategy_selection={
        "directive_scores": {"clarity": 0.65, "structured": 0.50},
    },
    blended_goals=(("close_sale", 0.8), ("analyze", 0.2)),
    active_goal_id="close_sale",
    goal_score=0.7,
)

attr = compute_attribution(mt)
check("weights sum to 1.0", abs(attr.sum() - 1.0) < 1e-9, f"got {attr.sum()}")
check(
    "all three factors get credit",
    attr.strategy_weight > 0.1 and attr.directive_weight > 0.1 and attr.goal_weight > 0.1,
    f"strat={attr.strategy_weight:.4f}, dir={attr.directive_weight:.4f}, goal={attr.goal_weight:.4f}",
)
check(
    "goal weight reflects blend weight 0.8",
    attr.goal_weight > 0.2,
    f"got {attr.goal_weight:.4f}",
)
check("reason not equal_split", attr.reason != "equal_split")


# ─────────────────────────────────────────────────────────────
section("5. compute_attribution — Missing Signals (Equal Split)")
# ─────────────────────────────────────────────────────────────

empty_trace = MockTrace()
attr_empty = compute_attribution(empty_trace)
check(
    "empty trace → balanced (all at floor)",
    attr_empty.reason == "balanced",
    f"got {attr_empty.reason}",
)
check(
    "equal weights sum to 1.0",
    abs(attr_empty.sum() - 1.0) < 1e-9,
)
check(
    "all three weights equal",
    abs(attr_empty.strategy_weight - attr_empty.directive_weight) < 1e-9
    and abs(attr_empty.directive_weight - attr_empty.goal_weight) < 1e-9,
)


# ─────────────────────────────────────────────────────────────
section("6. compute_attribution — Single Factor Dominant")
# ─────────────────────────────────────────────────────────────

# Strategy-only: high strategy score, no directive/goal info
strat_only = MockTrace(
    selected_strategy="clarity",
    strategy_scores={"clarity": 0.9},
)
attr_strat = compute_attribution(strat_only)
check(
    "strategy_weight > directive_weight",
    attr_strat.strategy_weight > attr_strat.directive_weight,
)
check(
    "strategy_weight > goal_weight",
    attr_strat.strategy_weight > attr_strat.goal_weight,
)
check(
    "weights sum to 1.0",
    abs(attr_strat.sum() - 1.0) < 1e-9,
)
check(
    "reason is strategy_dominant",
    attr_strat.reason == "strategy_dominant",
    f"got {attr_strat.reason}",
)

# Goal-only: high goal score, no strategy
goal_only = MockTrace(
    goal_score=0.95,
    active_goal_id="sell",
    blended_goals=(("sell", 0.95),),
)
attr_goal = compute_attribution(goal_only)
check(
    "goal_weight highest",
    attr_goal.goal_weight >= attr_goal.strategy_weight
    and attr_goal.goal_weight >= attr_goal.directive_weight,
    f"goal={attr_goal.goal_weight:.4f}, strat={attr_goal.strategy_weight:.4f}",
)
check("weights sum to 1.0", abs(attr_goal.sum() - 1.0) < 1e-9)


# ─────────────────────────────────────────────────────────────
section("7. Signal Floor Prevents Zero Weights")
# ─────────────────────────────────────────────────────────────

# Even when signals are missing, SIGNAL_FLOOR ensures no factor gets 0.0
partial = MockTrace(
    selected_strategy="clarity",
    strategy_scores={"clarity": 0.9},
)
attr_partial = compute_attribution(partial)
check(
    "goal_weight > 0 even with no goal signal",
    attr_partial.goal_weight > 0,
    f"got {attr_partial.goal_weight:.4f}",
)
check(
    "directive_weight > 0 even with fallback",
    attr_partial.directive_weight > 0,
    f"got {attr_partial.directive_weight:.4f}",
)


# ─────────────────────────────────────────────────────────────
section("8. Determinism — Same Trace → Same Attribution")
# ─────────────────────────────────────────────────────────────

t1 = MockTrace(
    selected_strategy="structured",
    strategy_scores={"structured": 0.7, "clarity": 0.5},
    strategy_selection={"directive_scores": {"structured": 0.6}},
    blended_goals=(("goal_a", 0.6), ("goal_b", 0.4)),
    active_goal_id="goal_a",
    goal_score=0.65,
)

a1 = compute_attribution(t1)
a2 = compute_attribution(t1)
check(
    "deterministic: same trace → same weights",
    a1.strategy_weight == a2.strategy_weight
    and a1.directive_weight == a2.directive_weight
    and a1.goal_weight == a2.goal_weight,
)
check("deterministic: same reason", a1.reason == a2.reason)


# ─────────────────────────────────────────────────────────────
section("9. Attribution Weight Affects Memory Update Strength")
# ─────────────────────────────────────────────────────────────

# Full weight (1.0) vs partial weight (0.3) should produce different EMA shifts
reset_strategy_memory()
mem = get_strategy_memory()
mem.record_win("test_strat", quality_score=0.5)
mem.record_win("test_strat", quality_score=0.5)
before = mem.get_stats("test_strat").ema_score

outcome = Outcome(
    turn_id=1, success=0.9, source=OutcomeSource.USER_FEEDBACK, confidence=0.8
)

# Apply with full attribution (1.0)
reset_strategy_memory()
mem_full = get_strategy_memory()
mem_full.record_win("test_strat", quality_score=0.5)
mem_full.record_win("test_strat", quality_score=0.5)
before_full = mem_full.get_stats("test_strat").ema_score
apply_outcome_to_strategy_memory("test_strat", 0.5, outcome, attribution_weight=1.0)
after_full = mem_full.get_stats("test_strat").ema_score
shift_full = abs(after_full - before_full)

# Apply with partial attribution (0.3)
reset_strategy_memory()
mem_partial = get_strategy_memory()
mem_partial.record_win("test_strat", quality_score=0.5)
mem_partial.record_win("test_strat", quality_score=0.5)
before_partial = mem_partial.get_stats("test_strat").ema_score
apply_outcome_to_strategy_memory("test_strat", 0.5, outcome, attribution_weight=0.3)
after_partial = mem_partial.get_stats("test_strat").ema_score
shift_partial = abs(after_partial - before_partial)

check(
    "full weight shifts more than partial",
    shift_full > shift_partial,
    f"full={shift_full:.4f}, partial={shift_partial:.4f}",
)
check(
    "partial shift is smaller than full",
    shift_partial < shift_full,
    f"partial={shift_partial:.4f}, full={shift_full:.4f}",
)

# Same check for directive memory
reset_directive_memory()
dm = get_directive_memory()
dm.record_win("test_dir", quality_score=0.5)
dm.record_win("test_dir", quality_score=0.5)
before_d = dm.get_stats("test_dir").ema_score
apply_outcome_to_directive_memory("test_dir", 0.5, outcome, attribution_weight=0.3)
after_d = dm.get_stats("test_dir").ema_score
shift_d = abs(after_d - before_d)

reset_directive_memory()
dm2 = get_directive_memory()
dm2.record_win("test_dir", quality_score=0.5)
dm2.record_win("test_dir", quality_score=0.5)
before_d2 = dm2.get_stats("test_dir").ema_score
apply_outcome_to_directive_memory("test_dir", 0.5, outcome, attribution_weight=1.0)
after_d2 = dm2.get_stats("test_dir").ema_score
shift_d2 = abs(after_d2 - before_d2)

check(
    "directive: full weight shifts more than partial",
    shift_d2 > shift_d,
    f"full={shift_d2:.4f}, partial={shift_d:.4f}",
)

# Goal tracker
registry = GoalRegistry()
goal = GoalState(goal_id="test_goal", description="test", priority=0.8)
registry.add_goal(goal)
tracker = registry.get_tracker("test_goal")
tracker.update_success(0.5)
tracker.update_success(0.5)
before_g = tracker.success_score
apply_outcome_to_goal_tracker(
    "test_goal", 0.5, outcome, registry, attribution_weight=0.3
)
after_g = tracker.success_score
shift_g_partial = abs(after_g - before_g)

registry2 = GoalRegistry()
registry2.add_goal(goal)
tracker2 = registry2.get_tracker("test_goal")
tracker2.update_success(0.5)
tracker2.update_success(0.5)
before_g2 = tracker2.success_score
apply_outcome_to_goal_tracker(
    "test_goal", 0.5, outcome, registry2, attribution_weight=1.0
)
after_g2 = tracker2.success_score
shift_g_full = abs(after_g2 - before_g2)

check(
    "goal: full weight shifts more than partial",
    shift_g_full > shift_g_partial,
    f"full={shift_g_full:.4f}, partial={shift_g_partial:.4f}",
)


# ─────────────────────────────────────────────────────────────
section("10. DecisionTrace Attribution Fields")
# ─────────────────────────────────────────────────────────────

trace_with = build_trace(
    turn_id=5,
    attribution_weights={
        "strategy_weight": 0.5,
        "directive_weight": 0.3,
        "goal_weight": 0.2,
    },
    attribution_reason="strategy_dominant",
)
check("attribution_weights set", trace_with.attribution_weights is not None)
check("attribution_reason set", trace_with.attribution_reason == "strategy_dominant")

d = trace_with.to_dict()
check("attribution_weights in dict", "attribution_weights" in d)
check("attribution_reason in dict", "attribution_reason" in d)

trace_without = build_trace(turn_id=6)
check("attribution_weights None by default", trace_without.attribution_weights is None)
check("attribution_reason None by default", trace_without.attribution_reason is None)

d2 = trace_without.to_dict()
check("attribution_weights absent when None", "attribution_weights" not in d2)
check("attribution_reason absent when None", "attribution_reason" not in d2)


# ─────────────────────────────────────────────────────────────
section("11. SessionRuntime Full Pipeline with Attribution")
# ─────────────────────────────────────────────────────────────

reset_strategy_memory()
reset_directive_memory()

from umh.runtime_engine.session_runtime import SessionRuntime

smem = get_strategy_memory()
smem.record_win("clarity", quality_score=0.7)
smem.record_win("clarity", quality_score=0.7)
smem.record_win("clarity", quality_score=0.7)

dmem = get_directive_memory()
dmem.record_win("clarity", quality_score=0.7)
dmem.record_win("clarity", quality_score=0.7)
dmem.record_win("clarity", quality_score=0.7)

goal_reg = GoalRegistry()
g = GoalState(goal_id="sell", description="close sale", priority=0.9, active=True)
goal_reg.add_goal(g)
gt = goal_reg.get_tracker("sell")
gt.update_success(0.6)
gt.update_success(0.7)

# Build a mock trace manually in a session
session = SessionRuntime(ctx=None)
session._goal_registry = goal_reg

# Create trace with rich signals for attribution
trace = build_trace(
    turn_id=1,
    evaluation={"quality_score": 0.72, "confidence": 0.85},
    strategy_selection={
        "enabled": True,
        "candidates": 2,
        "selected_strategy": "clarity",
        "directive_scores": {"clarity": 0.65},
    },
    goal_score=0.7,
    active_goal_id="sell",
    blended_goals=(("sell", 0.8),),
    blended_primary_goal_id="sell",
)
# Manually inject strategy_scores (build_trace reads from global singleton)
# We need the trace to have strategy_scores for attribution to work
session.stats.decision_traces.append(trace)

before_strat_ema = smem.get_stats("clarity").ema_score
before_dir_ema = dmem.get_stats("clarity").ema_score
before_goal_score = gt.success_score

outcome = Outcome(
    turn_id=1,
    success=0.95,
    source=OutcomeSource.USER_FEEDBACK,
    confidence=0.8,
)

applied = session.record_outcome(outcome)
check("full pipeline: outcome applied", applied)

after_strat_ema = smem.get_stats("clarity").ema_score
after_dir_ema = dmem.get_stats("clarity").ema_score
after_goal_score = gt.success_score

check(
    "strategy EMA shifted",
    after_strat_ema != before_strat_ema,
    f"before={before_strat_ema:.4f}, after={after_strat_ema:.4f}",
)
check(
    "directive EMA shifted",
    after_dir_ema != before_dir_ema,
    f"before={before_dir_ema:.4f}, after={after_dir_ema:.4f}",
)
check(
    "goal tracker shifted",
    after_goal_score != before_goal_score,
    f"before={before_goal_score:.4f}, after={after_goal_score:.4f}",
)

# Check that trace was enriched with attribution
enriched = session.stats.decision_traces[0]
check(
    "trace enriched with attribution_weights",
    getattr(enriched, "attribution_weights", None) is not None,
)
check(
    "trace enriched with attribution_reason",
    getattr(enriched, "attribution_reason", None) is not None,
)
check(
    "trace has outcome_attached=True",
    getattr(enriched, "outcome_attached", None) is True,
)
check(
    "trace has outcome_score",
    getattr(enriched, "outcome_score", None) is not None,
)


# ─────────────────────────────────────────────────────────────
section("12. Attribution Distributes Credit (Not Full)")
# ─────────────────────────────────────────────────────────────

# Compare: with attribution vs old behavior (full credit = weight 1.0)
# Strategy should get LESS shift with attribution than with full credit

reset_strategy_memory()
smem_attr = get_strategy_memory()
smem_attr.record_win("test_s", quality_score=0.5)
smem_attr.record_win("test_s", quality_score=0.5)
before_a = smem_attr.get_stats("test_s").ema_score

# Use a trace where strategy has partial attribution
attr_weights = compute_attribution(
    MockTrace(
        selected_strategy="test_s",
        strategy_scores={"test_s": 0.6},
        goal_score=0.8,
        active_goal_id="g",
        blended_goals=(("g", 0.8),),
    )
)

oc = Outcome(
    turn_id=1, success=0.95, source=OutcomeSource.USER_FEEDBACK, confidence=0.8
)
apply_outcome_to_strategy_memory(
    "test_s", 0.5, oc, attribution_weight=attr_weights.strategy_weight
)
after_a = smem_attr.get_stats("test_s").ema_score
shift_attributed = abs(after_a - before_a)

# Now full credit
reset_strategy_memory()
smem_full = get_strategy_memory()
smem_full.record_win("test_s", quality_score=0.5)
smem_full.record_win("test_s", quality_score=0.5)
before_f = smem_full.get_stats("test_s").ema_score
apply_outcome_to_strategy_memory("test_s", 0.5, oc, attribution_weight=1.0)
after_f = smem_full.get_stats("test_s").ema_score
shift_full = abs(after_f - before_f)

check(
    "attributed shift < full shift",
    shift_attributed < shift_full,
    f"attributed={shift_attributed:.4f}, full={shift_full:.4f}",
)
check(
    "attribution weight < 1.0",
    attr_weights.strategy_weight < 1.0,
    f"got {attr_weights.strategy_weight:.4f}",
)
check(
    "attribution sum = 1.0",
    abs(attr_weights.sum() - 1.0) < 1e-9,
)


# ─────────────────────────────────────────────────────────────
section("13. Backward Compatibility — Default weight=1.0")
# ─────────────────────────────────────────────────────────────

# Calling apply functions without attribution_weight should behave as before
reset_strategy_memory()
mem_compat = get_strategy_memory()
mem_compat.record_win("compat", quality_score=0.5)
mem_compat.record_win("compat", quality_score=0.5)
before_c = mem_compat.get_stats("compat").ema_score

oc = Outcome(turn_id=1, success=0.9, source=OutcomeSource.USER_FEEDBACK, confidence=0.8)
apply_outcome_to_strategy_memory("compat", 0.5, oc)  # no attribution_weight arg
after_c = mem_compat.get_stats("compat").ema_score

check(
    "default weight=1.0 still shifts EMA",
    after_c != before_c,
    f"before={before_c:.4f}, after={after_c:.4f}",
)


# ─────────────────────────────────────────────────────────────
section("14. No LLM Calls")
# ─────────────────────────────────────────────────────────────

import inspect

src = inspect.getsource(sys.modules["umh.runtime_engine.causal_attribution"])
check("no call_with_fallback", "call_with_fallback" not in src)
check("no model_router", "model_router" not in src)
check("no agent_runtime", "agent_runtime" not in src)
check("no GenerativeModel", "GenerativeModel" not in src)


# ─────────────────────────────────────────────────────────────
section("15. ExecutionSpine Unchanged")
# ─────────────────────────────────────────────────────────────

spine_src = open("/opt/OS/eos/execution_spine.py").read()
check("spine has no causal_attribution import", "causal_attribution" not in spine_src)
check("spine has no attribution_weight", "attribution_weight" not in spine_src)
check("spine has no compute_attribution", "compute_attribution" not in spine_src)


# ─────────────────────────────────────────────────────────────
section("16. No Regression — Existing Outcome Feedback Tests")
# ─────────────────────────────────────────────────────────────

reset_strategy_memory()
reset_directive_memory()

# Verify basic outcome feedback still works
smem = get_strategy_memory()
smem.record_win("r", quality_score=0.6)
smem.record_win("r", quality_score=0.6)
before_r = smem.get_stats("r").ema_score

oc = Outcome(turn_id=1, success=0.95, source=OutcomeSource.SYSTEM_EVAL, confidence=0.7)
adj = apply_outcome_to_strategy_memory("r", 0.6, oc, attribution_weight=1.0)
after_r = smem.get_stats("r").ema_score

check("outcome still modifies EMA", after_r != before_r)
check("adjusted score returned", adj > 0)
check("uses unchanged", smem.get_stats("r").uses == 2)

# OutcomeStore still works
store = OutcomeStore()
store.record(oc)
check("store records", store.total_outcomes == 1)
check("store retrieves", len(store.get_for_turn(1)) == 1)


# ─────────────────────────────────────────────────────────────
section("17. Directive Fallback Heuristic")
# ─────────────────────────────────────────────────────────────

# When no directive_scores in strategy_selection, directive signal = strategy * 0.8
t_no_dir = MockTrace(
    selected_strategy="clarity",
    strategy_scores={"clarity": 0.8},
)
attr_no_dir = compute_attribution(t_no_dir)
# directive_signal = 0.8 * 0.8 = 0.64, strategy = 0.8, goal = FLOOR = 0.1
# total = 0.8 + 0.64 + 0.1 = 1.54
expected_dir_weight = 0.64 / (0.8 + 0.64 + 0.1)
check(
    "directive fallback = strategy * 0.8",
    abs(attr_no_dir.directive_weight - expected_dir_weight) < 0.01,
    f"got {attr_no_dir.directive_weight:.4f}, expected ~{expected_dir_weight:.4f}",
)


# ─────────────────────────────────────────────────────────────
section("18. Attribution Reason Classification")
# ─────────────────────────────────────────────────────────────

# Balanced: all signals similar
balanced_t = MockTrace(
    selected_strategy="s",
    strategy_scores={"s": 0.5},
    strategy_selection={"directive_scores": {"s": 0.45}},
    goal_score=0.5,
)
attr_bal = compute_attribution(balanced_t)
check(
    "balanced reason when signals similar",
    attr_bal.reason == "balanced",
    f"got {attr_bal.reason}",
)

# Dominant: one signal much higher
dominant_t = MockTrace(
    selected_strategy="s",
    strategy_scores={"s": 0.95},
)
attr_dom = compute_attribution(dominant_t)
check(
    "dominant reason when one signal high",
    "dominant" in attr_dom.reason,
    f"got {attr_dom.reason}",
)


# ─────────────────────────────────────────────────────────────
section("19. Zero Attribution Weight = No Effect")
# ─────────────────────────────────────────────────────────────

reset_strategy_memory()
mem_zero = get_strategy_memory()
mem_zero.record_win("z", quality_score=0.5)
mem_zero.record_win("z", quality_score=0.5)
before_z = mem_zero.get_stats("z").ema_score

oc = Outcome(
    turn_id=1, success=0.95, source=OutcomeSource.USER_FEEDBACK, confidence=0.8
)
apply_outcome_to_strategy_memory("z", 0.5, oc, attribution_weight=0.0)
after_z = mem_zero.get_stats("z").ema_score

check(
    "zero weight = no EMA change",
    before_z == after_z,
    f"before={before_z:.4f}, after={after_z:.4f}",
)


# ─────────────────────────────────────────────────────────────
section("20. Multiple Outcomes — Attribution Compounds")
# ─────────────────────────────────────────────────────────────

reset_strategy_memory()
mem_multi = get_strategy_memory()
mem_multi.record_win("m", quality_score=0.5)
mem_multi.record_win("m", quality_score=0.5)
start = mem_multi.get_stats("m").ema_score

oc1 = Outcome(
    turn_id=1, success=0.9, source=OutcomeSource.USER_FEEDBACK, confidence=0.8
)
apply_outcome_to_strategy_memory("m", 0.5, oc1, attribution_weight=0.4)
mid = mem_multi.get_stats("m").ema_score

oc2 = Outcome(
    turn_id=2, success=0.95, source=OutcomeSource.EXTERNAL_API, confidence=0.7
)
apply_outcome_to_strategy_memory("m", 0.5, oc2, attribution_weight=0.6)
end = mem_multi.get_stats("m").ema_score

check("first outcome shifts up", mid > start, f"{start:.4f} → {mid:.4f}")
check("second outcome shifts further", end > mid, f"{mid:.4f} → {end:.4f}")


# ═════════════════════════════════════════════════════════════
print(f"\n{'═' * 60}")
print(f"  RESULTS: {PASS} passed, {FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if FAIL > 0 else 0)
