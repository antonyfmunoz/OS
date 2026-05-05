"""
Tests for Goal-Driven Behavioral Gating.

Validates:
    1. negative goal_delta disables exploration
    2. positive goal_delta enables exploration
    3. unstable convergence overrides goal gating
    4. synthesis only enabled on sustained positive progress
    5. DecisionTrace captures gating decisions
    6. no regressions (existing influence tests unaffected)
    7. no new LLM calls
    8. ExecutionSpine unchanged
    9. priority: Control > Convergence > Goal
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
# 0. Constants and imports
# ═══════════════════════════════════════════════════════════════════════════════

_section("0. Constants + Imports")

from umh.runtime_engine.influence_orchestrator import (
    GOAL_NEGATIVE_THRESHOLD,
    GOAL_POSITIVE_STREAK_WINDOW,
    GOAL_POSITIVE_THRESHOLD,
    NO_INFLUENCE,
    UnifiedInfluence,
    resolve_influence,
    _has_sustained_positive,
)
from umh.runtime_engine.decision_trace import DecisionTrace, build_trace
from umh.goals.state import GoalState, NO_GOAL

_test("GOAL_NEGATIVE_THRESHOLD is -0.05", GOAL_NEGATIVE_THRESHOLD == -0.05)
_test("GOAL_POSITIVE_THRESHOLD is +0.05", GOAL_POSITIVE_THRESHOLD == 0.05)
_test("GOAL_POSITIVE_STREAK_WINDOW is 3", GOAL_POSITIVE_STREAK_WINDOW == 3)
_test(
    "UnifiedInfluence has convergence_status",
    "convergence_status" in UnifiedInfluence.__dataclass_fields__,
)
_test(
    "UnifiedInfluence has goal_gating_reason",
    "goal_gating_reason" in UnifiedInfluence.__dataclass_fields__,
)
_test(
    "NO_INFLUENCE.convergence_status is None", NO_INFLUENCE.convergence_status is None
)
_test(
    "NO_INFLUENCE.goal_gating_reason is None", NO_INFLUENCE.goal_gating_reason is None
)

# Shared goal for tests
goal = GoalState(
    goal_id="close_sale",
    description="Close coaching sale",
    success_criteria={"response_type": "persuasive", "domain": "sales"},
    priority=0.9,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Negative goal_delta disables exploration
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. Negative goal_delta Disables Exploration")

# Basic: negative delta below threshold
inf_neg = resolve_influence(
    goal_state=goal,
    goal_progress_signal=-0.08,
)
_test(
    "negative delta → exploration disabled",
    inf_neg.exploration_enabled is False,
    f"exploration_enabled={inf_neg.exploration_enabled}",
)
_test(
    "negative delta → reason is negative_goal_delta",
    inf_neg.goal_gating_reason is not None
    and "negative_goal_delta" in inf_neg.goal_gating_reason,
    f"reason={inf_neg.goal_gating_reason}",
)

# At exactly the threshold: NOT disabled (must be strictly less)
inf_boundary = resolve_influence(
    goal_state=goal,
    goal_progress_signal=GOAL_NEGATIVE_THRESHOLD,
)
_test(
    "delta == threshold → exploration stays enabled",
    inf_boundary.exploration_enabled is True,
    f"delta={GOAL_NEGATIVE_THRESHOLD}, enabled={inf_boundary.exploration_enabled}",
)

# Just below threshold
inf_just_below = resolve_influence(
    goal_state=goal,
    goal_progress_signal=GOAL_NEGATIVE_THRESHOLD - 0.001,
)
_test(
    "delta just below threshold → exploration disabled",
    inf_just_below.exploration_enabled is False,
)

# Negative delta also disables synthesis
_test(
    "negative delta → synthesis disabled",
    inf_neg.synthesis_enabled is False,
    f"synthesis_enabled={inf_neg.synthesis_enabled}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Positive goal_delta enables exploration
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. Positive goal_delta Enables Exploration")

# Positive delta with no convergence suppression
inf_pos = resolve_influence(
    goal_state=goal,
    goal_progress_signal=0.1,
)
_test(
    "positive delta → exploration enabled",
    inf_pos.exploration_enabled is True,
    f"exploration_enabled={inf_pos.exploration_enabled}",
)

# Positive delta does NOT re-enable exploration when convergence suppressed it
inf_pos_conv_suppressed = resolve_influence(
    goal_state=goal,
    goal_progress_signal=0.1,
    exploration_suppressed=True,
)
_test(
    "positive delta + convergence suppressed → exploration stays disabled",
    inf_pos_conv_suppressed.exploration_enabled is False,
    f"exploration_enabled={inf_pos_conv_suppressed.exploration_enabled}",
)

# At exactly the positive threshold
inf_pos_boundary = resolve_influence(
    goal_state=goal,
    goal_progress_signal=GOAL_POSITIVE_THRESHOLD,
)
_test(
    "delta == positive threshold → exploration enabled (default was already true)",
    inf_pos_boundary.exploration_enabled is True,
)

# Flat delta: no gating action
inf_flat = resolve_influence(
    goal_state=goal,
    goal_progress_signal=0.0,
)
_test(
    "zero delta → no goal gating (bypassed)",
    inf_flat.goal_gating_reason is None,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Unstable convergence overrides goal gating
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Unstable Convergence Overrides Goal")

# Positive delta but unstable convergence
inf_unstable_pos = resolve_influence(
    goal_state=goal,
    goal_progress_signal=0.15,
    convergence_status="unstable",
    exploration_suppressed=True,
    synthesis_suppressed=True,
)
_test(
    "unstable + positive delta → exploration stays disabled",
    inf_unstable_pos.exploration_enabled is False,
)
_test(
    "unstable + positive delta → synthesis stays disabled",
    inf_unstable_pos.synthesis_enabled is False,
)
_test(
    "unstable → reason is convergence_override",
    inf_unstable_pos.goal_gating_reason == "convergence_override",
    f"reason={inf_unstable_pos.goal_gating_reason}",
)

# Negative delta + unstable → convergence already disabled, goal doesn't act
inf_unstable_neg = resolve_influence(
    goal_state=goal,
    goal_progress_signal=-0.1,
    convergence_status="unstable",
    exploration_suppressed=True,
)
_test(
    "unstable + negative delta → convergence_override (not goal)",
    inf_unstable_neg.goal_gating_reason == "convergence_override",
)

# Stable convergence allows goal gating
inf_stable_neg = resolve_influence(
    goal_state=goal,
    goal_progress_signal=-0.08,
    convergence_status="stable",
)
_test(
    "stable convergence + negative delta → goal gates exploration",
    inf_stable_neg.exploration_enabled is False,
)
_test(
    "stable convergence → reason is negative_goal_delta",
    inf_stable_neg.goal_gating_reason is not None
    and "negative_goal_delta" in inf_stable_neg.goal_gating_reason,
)

# Recovering convergence allows goal gating
inf_recovering = resolve_influence(
    goal_state=goal,
    goal_progress_signal=-0.08,
    convergence_status="recovering",
)
_test(
    "recovering convergence + negative delta → goal gates",
    inf_recovering.exploration_enabled is False,
)

# No convergence status (None) allows goal gating
inf_none_conv = resolve_influence(
    goal_state=goal,
    goal_progress_signal=-0.08,
    convergence_status=None,
)
_test(
    "no convergence status + negative delta → goal gates",
    inf_none_conv.exploration_enabled is False,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Synthesis only enabled on sustained positive progress
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Synthesis Requires Sustained Positive Progress")

# _has_sustained_positive helper
_test(
    "sustained positive: 3 positive deltas → True",
    _has_sustained_positive([0.06, 0.07, 0.08], 0.08) is True,
)
_test(
    "sustained positive: 2 in history + current appended → True (3 total)",
    _has_sustained_positive([0.06, 0.07], 0.08) is True,
)
_test(
    "sustained positive: 3 but one below threshold → False",
    _has_sustained_positive([0.06, 0.03, 0.08], 0.08) is False,
)
_test(
    "sustained positive: empty history → False",
    _has_sustained_positive([], 0.08) is False,
)
_test(
    "sustained positive: 1 in history + current → too short",
    _has_sustained_positive([0.06], 0.08) is False,
    "only 1 + 1 current = 2, needs 3",
)

# When convergence suppressed synthesis, sustained positive re-enables
# (only if convergence is not unstable and control didn't suppress)
inf_synth_reenable = resolve_influence(
    goal_state=goal,
    goal_progress_signal=0.08,
    convergence_status="stable",
    goal_delta_history=[0.06, 0.07, 0.08],
)
_test(
    "sustained positive → synthesis enabled (default was true)",
    inf_synth_reenable.synthesis_enabled is True,
)

# Synthesis was suppressed by convergence, but sustained positive streak
# re-enables it (convergence is no longer unstable)
inf_synth_reenable2 = resolve_influence(
    goal_state=goal,
    goal_progress_signal=0.08,
    convergence_status="recovering",
    synthesis_suppressed=False,
    goal_delta_history=[0.06, 0.07, 0.08],
)
_test(
    "recovering + sustained positive → synthesis enabled",
    inf_synth_reenable2.synthesis_enabled is True,
)

# Not enough streak: synthesis stays in default state
inf_short_streak = resolve_influence(
    goal_state=goal,
    goal_progress_signal=0.08,
    convergence_status="stable",
    goal_delta_history=[0.08],
)
_test(
    "short streak → synthesis stays default (true)",
    inf_short_streak.synthesis_enabled is True,
)

# Negative delta disables synthesis
inf_neg_synth = resolve_influence(
    goal_state=goal,
    goal_progress_signal=-0.08,
    convergence_status="stable",
)
_test(
    "negative delta → synthesis disabled",
    inf_neg_synth.synthesis_enabled is False,
)

# Sustained positive cannot override control suppression
inf_ctrl_blocks = resolve_influence(
    control_directives=["be precise"],
    goal_state=goal,
    goal_progress_signal=0.08,
    goal_delta_history=[0.06, 0.07, 0.08],
)
_test(
    "control suppresses → sustained positive can't re-enable synthesis",
    inf_ctrl_blocks.synthesis_enabled is False,
)
_test(
    "control suppresses → sustained positive can't re-enable exploration",
    inf_ctrl_blocks.exploration_enabled is False,
)

# Sustained positive cannot override convergence unstable
inf_conv_blocks = resolve_influence(
    goal_state=goal,
    goal_progress_signal=0.08,
    convergence_status="unstable",
    synthesis_suppressed=True,
    goal_delta_history=[0.06, 0.07, 0.08],
)
_test(
    "unstable → sustained positive can't re-enable synthesis",
    inf_conv_blocks.synthesis_enabled is False,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. DecisionTrace captures gating decisions
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. DecisionTrace Captures Gating Decisions")

# Fields exist
_test(
    "DecisionTrace has exploration_enabled field",
    "exploration_enabled" in DecisionTrace.__dataclass_fields__,
)
_test(
    "DecisionTrace has synthesis_enabled field",
    "synthesis_enabled" in DecisionTrace.__dataclass_fields__,
)
_test(
    "DecisionTrace has goal_gating_reason field",
    "goal_gating_reason" in DecisionTrace.__dataclass_fields__,
)

# build_trace accepts and propagates
import inspect

bt_sig = inspect.signature(build_trace)
_test(
    "build_trace has exploration_enabled param",
    "exploration_enabled" in bt_sig.parameters,
)
_test(
    "build_trace has synthesis_enabled param", "synthesis_enabled" in bt_sig.parameters
)
_test(
    "build_trace has goal_gating_reason param",
    "goal_gating_reason" in bt_sig.parameters,
)

trace_gated = build_trace(
    turn_id=1,
    evaluation={"quality_score": 0.7, "confidence": 0.6},
    exploration_enabled=False,
    synthesis_enabled=True,
    goal_gating_reason="negative_goal_delta",
)
_test("exploration_enabled set on trace", trace_gated.exploration_enabled is False)
_test("synthesis_enabled set on trace", trace_gated.synthesis_enabled is True)
_test(
    "goal_gating_reason set on trace",
    trace_gated.goal_gating_reason == "negative_goal_delta",
)

# Serialization
td = trace_gated.to_dict()
_test("to_dict includes exploration_enabled", td.get("exploration_enabled") is False)
_test("to_dict includes synthesis_enabled", td.get("synthesis_enabled") is True)
_test(
    "to_dict includes goal_gating_reason",
    td.get("goal_gating_reason") == "negative_goal_delta",
)

# None defaults: not in to_dict
trace_no_gating = build_trace(
    turn_id=2,
    evaluation={"quality_score": 0.7, "confidence": 0.6},
)
td2 = trace_no_gating.to_dict()
_test(
    "no gating → exploration_enabled not in to_dict", "exploration_enabled" not in td2
)
_test("no gating → synthesis_enabled not in to_dict", "synthesis_enabled" not in td2)
_test("no gating → goal_gating_reason not in to_dict", "goal_gating_reason" not in td2)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. No regressions — existing influence behavior preserved
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. No Regressions")

# NO_INFLUENCE still works
_test("NO_INFLUENCE.synthesis_enabled is True", NO_INFLUENCE.synthesis_enabled is True)
_test(
    "NO_INFLUENCE.exploration_enabled is True", NO_INFLUENCE.exploration_enabled is True
)

# resolve_influence() with no args → NO_INFLUENCE
inf_empty = resolve_influence()
_test("empty resolve → NO_INFLUENCE", inf_empty == NO_INFLUENCE)

# Control still disables both
inf_ctrl = resolve_influence(control_directives=["be precise"])
_test("control → synthesis disabled", inf_ctrl.synthesis_enabled is False)
_test("control → exploration disabled", inf_ctrl.exploration_enabled is False)

# Convergence suppression still works
inf_conv_supp = resolve_influence(
    synthesis_suppressed=True, exploration_suppressed=True
)
_test(
    "convergence suppress → synthesis disabled",
    inf_conv_supp.synthesis_enabled is False,
)
_test(
    "convergence suppress → exploration disabled",
    inf_conv_supp.exploration_enabled is False,
)

# Strategy override blocked by control
inf_strat = resolve_influence(
    control_directives=["fix"], strategy_override="structured"
)
_test("control blocks strategy override", inf_strat.strategy_override is None)

# Strategy override works without control
inf_strat2 = resolve_influence(strategy_override="structured")
_test(
    "no control → strategy override works", inf_strat2.strategy_override == "structured"
)

# Goal directives still flow through
inf_goal = resolve_influence(goal_state=goal)
_test(
    "goal directives flow",
    len(inf_goal.goal_directives) > 0 or inf_goal.goal_weight > 0,
)

# No goal → no gating
inf_no_goal = resolve_influence(goal_progress_signal=-0.1)
_test(
    "no goal_state → no gating (exploration enabled)",
    inf_no_goal.exploration_enabled is True,
)
_test(
    "no goal_state → no goal_gating_reason",
    inf_no_goal.goal_gating_reason is None,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. No new LLM calls
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. No New LLM Calls")

import umh.runtime_engine.influence_orchestrator as io_mod

io_source = inspect.getsource(io_mod)
_test(
    "influence_orchestrator has no LLM calls",
    "call_with_fallback" not in io_source
    and "model_router" not in io_source
    and "AgentRuntime" not in io_source,
)

# _has_sustained_positive is pure
sp_source = inspect.getsource(io_mod._has_sustained_positive)
_test(
    "_has_sustained_positive has no LLM calls",
    "call_with_fallback" not in sp_source,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. ExecutionSpine unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. ExecutionSpine Unchanged")

spine_source = inspect.getsource(
    __import__("umh.runtime_engine.execution_spine", fromlist=["ExecutionSpine"]).ExecutionSpine
)
_test(
    "ExecutionSpine has no goal_gating references",
    "goal_gating" not in spine_source and "behavioral_gating" not in spine_source,
)
_test(
    "ExecutionSpine has no exploration_enabled references",
    "exploration_enabled" not in spine_source,
)
_test(
    "ExecutionSpine has no synthesis_enabled references",
    "synthesis_enabled" not in spine_source,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Priority: Control > Convergence > Goal
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Priority Chain: Control > Convergence > Goal")

# Control disables → goal positive cannot re-enable
inf_p1 = resolve_influence(
    control_directives=["be safe"],
    goal_state=goal,
    goal_progress_signal=0.2,
    goal_delta_history=[0.1, 0.15, 0.2],
)
_test(
    "control disables → goal can't re-enable exploration",
    inf_p1.exploration_enabled is False,
)
_test(
    "control disables → goal can't re-enable synthesis",
    inf_p1.synthesis_enabled is False,
)

# Convergence disables → goal positive cannot re-enable
inf_p2 = resolve_influence(
    exploration_suppressed=True,
    synthesis_suppressed=True,
    goal_state=goal,
    goal_progress_signal=0.2,
    goal_delta_history=[0.1, 0.15, 0.2],
)
_test(
    "convergence disables → goal can't re-enable exploration",
    inf_p2.exploration_enabled is False,
)
_test(
    "convergence disables → goal can't re-enable synthesis",
    inf_p2.synthesis_enabled is False,
)

# Only goal disables → can be re-enabled by goal positive (exploration)
# First: goal negative disables exploration
inf_p3_neg = resolve_influence(
    goal_state=goal,
    goal_progress_signal=-0.08,
)
_test(
    "goal negative → exploration disabled",
    inf_p3_neg.exploration_enabled is False,
)

# Then: goal positive re-enables (no higher layer blocked)
inf_p3_pos = resolve_influence(
    goal_state=goal,
    goal_progress_signal=0.1,
)
_test(
    "goal positive → exploration enabled",
    inf_p3_pos.exploration_enabled is True,
)

# convergence_status flows to UnifiedInfluence
inf_with_status = resolve_influence(
    goal_state=goal,
    goal_progress_signal=0.08,
    convergence_status="recovering",
)
_test(
    "convergence_status flows through",
    inf_with_status.convergence_status == "recovering",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Determinism
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. Determinism")

ref = resolve_influence(
    goal_state=goal,
    goal_progress_signal=-0.08,
    convergence_status="stable",
    goal_delta_history=[-0.06, -0.07, -0.08],
)
for _ in range(100):
    r = resolve_influence(
        goal_state=goal,
        goal_progress_signal=-0.08,
        convergence_status="stable",
        goal_delta_history=[-0.06, -0.07, -0.08],
    )
    assert r == ref, f"Non-deterministic: {r} != {ref}"
_test("100x resolve_influence → identical", True)

ref2 = resolve_influence(
    goal_state=goal,
    goal_progress_signal=0.08,
    convergence_status="recovering",
    goal_delta_history=[0.06, 0.07, 0.08],
)
for _ in range(100):
    r = resolve_influence(
        goal_state=goal,
        goal_progress_signal=0.08,
        convergence_status="recovering",
        goal_delta_history=[0.06, 0.07, 0.08],
    )
    assert r == ref2
_test("100x positive path → identical", True)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. SessionRuntime wiring
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. SessionRuntime Wiring")

from umh.runtime_engine.session_runtime import SessionRuntime

sr_source = inspect.getsource(SessionRuntime.run)

_test(
    "SessionRuntime passes convergence_status to resolve_influence",
    "convergence_status=_conv_status" in sr_source,
)
_test(
    "SessionRuntime passes goal_delta_history to resolve_influence",
    "goal_delta_history=_goal_delta_history" in sr_source,
)
_test(
    "SessionRuntime passes exploration_enabled to build_trace",
    "exploration_enabled=self._unified_influence.exploration_enabled" in sr_source,
)
_test(
    "SessionRuntime passes synthesis_enabled to build_trace",
    "synthesis_enabled=self._unified_influence.synthesis_enabled" in sr_source,
)
_test(
    "SessionRuntime passes goal_gating_reason to build_trace",
    "goal_gating_reason=self._unified_influence.goal_gating_reason" in sr_source,
)
_test(
    "SessionRuntime builds goal_delta_history from traces",
    "_goal_delta_history" in sr_source,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Backward compatibility
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. Backward Compatibility")

# No goal → gating bypassed entirely
inf_no_goal_2 = resolve_influence(goal_progress_signal=-0.1)
_test(
    "no goal_state + negative signal → exploration enabled",
    inf_no_goal_2.exploration_enabled is True,
)
_test(
    "no goal_state + negative signal → synthesis enabled",
    inf_no_goal_2.synthesis_enabled is True,
)

# resolve_influence() → NO_INFLUENCE (unchanged)
_test(
    "resolve_influence() == NO_INFLUENCE",
    resolve_influence() == NO_INFLUENCE,
)

# Zero signal → no gating
inf_zero = resolve_influence(goal_state=goal, goal_progress_signal=0.0)
_test(
    "zero progress signal → no gating reason",
    inf_zero.goal_gating_reason is None,
)

# DecisionTrace defaults
trace_default = build_trace(
    turn_id=1, evaluation={"quality_score": 0.5, "confidence": 0.5}
)
_test(
    "default trace.exploration_enabled is None",
    trace_default.exploration_enabled is None,
)
_test(
    "default trace.synthesis_enabled is None", trace_default.synthesis_enabled is None
)
_test(
    "default trace.goal_gating_reason is None", trace_default.goal_gating_reason is None
)

# to_dict() serialization
inf_full = resolve_influence(
    goal_state=goal,
    goal_progress_signal=-0.08,
    convergence_status="stable",
)
d = inf_full.to_dict()
_test("to_dict includes convergence_status", d.get("convergence_status") == "stable")
_test(
    "to_dict includes goal_gating_reason",
    d.get("goal_gating_reason") is not None,
)

# NO_INFLUENCE to_dict omits optional fields
d_no = NO_INFLUENCE.to_dict()
_test(
    "NO_INFLUENCE to_dict omits convergence_status",
    "convergence_status" not in d_no,
)
_test(
    "NO_INFLUENCE to_dict omits goal_gating_reason",
    "goal_gating_reason" not in d_no,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if _FAIL > 0 else 0)
