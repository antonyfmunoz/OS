"""
Tests for Plan Persistence & Commitment Pressure.

Proves:
    1. System sticks with a good goal across turns
    2. Avoids oscillation between near-equal goals
    3. Switches when a clearly better goal appears
    4. Uncertainty can override commitment
    5. Determinism preserved
    6. No regressions
    7. No LLM calls
    8. ExecutionSpine unchanged
"""

import sys
import inspect

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
    print(f"\n{'=' * 60}")
    print(f"  {name}")
    print(f"{'=' * 60}")


# ═══════════════════════════════════════════════════════════════════════════════
# 0. Imports
# ═══════════════════════════════════════════════════════════════════════════════

_section("0. Imports")

from umh.goals.state import (
    GoalState,
    GoalRegistry,
    GoalTracker,
    PERSISTENCE_DECAY,
)
from umh.runtime_engine.counterfactual_eval import (
    CounterfactualResult,
    CounterfactualEvaluator,
    COMMITMENT_WEIGHT,
    COMMITMENT_CAP,
    UNCERTAINTY_WEIGHT,
    HORIZON_WEIGHT,
)
from umh.runtime_engine.goal_arbitrator import (
    GoalArbitrator,
    SWITCH_COST,
    W_PRIORITY,
    W_SCORE,
    W_DELTA,
    W_RECENCY,
)
from umh.runtime_engine.decision_trace import build_trace

_test("all imports succeed", True)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. GoalTracker — persistence_streak field
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. GoalTracker — persistence_streak")

tracker = GoalTracker(goal_id="t1")
_test("initial streak is 0.0", tracker.persistence_streak == 0.0)

tracker.update_persistence(is_active=True)
_test("active → streak increments to 1.0", tracker.persistence_streak == 1.0)

tracker.update_persistence(is_active=True)
_test("active again → streak is 2.0", tracker.persistence_streak == 2.0)

tracker.update_persistence(is_active=False)
expected_decay = 2.0 * PERSISTENCE_DECAY
_test(
    "inactive → streak decays",
    abs(tracker.persistence_streak - expected_decay) < 0.001,
    f"got={tracker.persistence_streak:.3f}, expected={expected_decay:.3f}",
)

tracker.update_persistence(is_active=False)
expected_decay2 = expected_decay * PERSISTENCE_DECAY
_test(
    "inactive again → further decay",
    abs(tracker.persistence_streak - expected_decay2) < 0.001,
    f"got={tracker.persistence_streak:.3f}",
)

tracker.update_persistence(is_active=True)
expected_resume = expected_decay2 + 1.0
_test(
    "reactivated → decayed base + 1",
    abs(tracker.persistence_streak - expected_resume) < 0.001,
    f"got={tracker.persistence_streak:.3f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. GoalTracker — to_dict includes persistence_streak
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. GoalTracker — to_dict")

t = GoalTracker(goal_id="d1")
t.update_persistence(is_active=True)
t.update_persistence(is_active=True)
d = t.to_dict()
_test("to_dict has persistence_streak", "persistence_streak" in d)
_test("to_dict persistence_streak correct", abs(d["persistence_streak"] - 2.0) < 0.001)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. PERSISTENCE_DECAY constant
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Constants")

_test("PERSISTENCE_DECAY is 0.8", PERSISTENCE_DECAY == 0.8)
_test("COMMITMENT_WEIGHT is 0.05", COMMITMENT_WEIGHT == 0.05)
_test("COMMITMENT_CAP is 0.3", COMMITMENT_CAP == 0.3)
_test("SWITCH_COST is 0.1", SWITCH_COST == 0.1)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. CounterfactualResult — commitment_bonus field
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. CounterfactualResult — commitment_bonus")

cr_committed = CounterfactualResult(
    expected_utility=0.3,
    expected_delta=0.0,
    confidence=0.8,
    reasoning="test",
    commitment_bonus=0.15,
)
_test("commitment_bonus stored", cr_committed.commitment_bonus == 0.15)

cr_no_commit = CounterfactualResult(
    expected_utility=0.3,
    expected_delta=0.0,
    confidence=0.8,
    reasoning="test",
)
_test("default commitment_bonus is 0.0", cr_no_commit.commitment_bonus == 0.0)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. effective_utility — four components
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Effective Utility — Four Components")

cr4 = CounterfactualResult(
    expected_utility=0.3,
    expected_delta=0.0,
    confidence=0.7,
    reasoning="test",
    horizon_value=0.4,
    commitment_bonus=0.1,
)

exploration = (1.0 - 0.7) * UNCERTAINTY_WEIGHT
horizon_contrib = HORIZON_WEIGHT * 0.4
expected_eff = min(1.0, 0.3 + exploration + horizon_contrib + 0.1)
_test(
    "four-component formula",
    abs(cr4.effective_utility - expected_eff) < 0.001,
    f"got={cr4.effective_utility:.4f}, expected={expected_eff:.4f}",
)

cr_no_commit_check = CounterfactualResult(
    expected_utility=0.3,
    expected_delta=0.0,
    confidence=0.7,
    reasoning="test",
    horizon_value=0.4,
    commitment_bonus=0.0,
)
_test(
    "commitment_bonus=0 → same as three-component",
    abs(cr_no_commit_check.effective_utility - (0.3 + exploration + horizon_contrib))
    < 0.001,
)

# Clamping
cr_over = CounterfactualResult(
    expected_utility=0.9,
    expected_delta=0.0,
    confidence=0.1,
    reasoning="test",
    commitment_bonus=0.3,
)
_test("clamped to 1.0", cr_over.effective_utility == 1.0)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. to_dict includes commitment_bonus
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. to_dict — commitment_bonus")

d_commit = cr_committed.to_dict()
_test("to_dict has commitment_bonus", "commitment_bonus" in d_commit)
_test(
    "to_dict commitment_bonus correct",
    abs(d_commit["commitment_bonus"] - 0.15) < 0.001,
)

d_no = cr_no_commit.to_dict()
_test(
    "to_dict commitment_bonus present even when 0",
    "commitment_bonus" in d_no,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. commitment_bonus formula: min(streak * COMMITMENT_WEIGHT, COMMITMENT_CAP)
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Commitment Bonus Formula")

# streak=3 → 3 * 0.05 = 0.15
bonus_3 = min(3 * COMMITMENT_WEIGHT, COMMITMENT_CAP)
_test("streak 3 → bonus 0.15", abs(bonus_3 - 0.15) < 0.001, f"got={bonus_3:.3f}")

# streak=6 → 6 * 0.05 = 0.30 = cap
bonus_6 = min(6 * COMMITMENT_WEIGHT, COMMITMENT_CAP)
_test("streak 6 → bonus hits cap 0.30", abs(bonus_6 - 0.30) < 0.001)

# streak=10 → 10 * 0.05 = 0.50 → capped to 0.30
bonus_10 = min(10 * COMMITMENT_WEIGHT, COMMITMENT_CAP)
_test("streak 10 → still capped at 0.30", abs(bonus_10 - 0.30) < 0.001)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. CounterfactualEvaluator computes commitment from tracker
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Evaluator → Commitment from Tracker")

from umh.runtime_engine.meta_goal import MetaGoal

reg = GoalRegistry()
gs = GoalState(
    goal_id="committed_goal",
    description="Test",
    success_criteria={"domain": "test"},
    priority=0.7,
)
reg.add_goal(gs)
trk = reg.get_tracker("committed_goal")
for _ in range(4):
    trk.update_persistence(is_active=True)

evaluator = CounterfactualEvaluator()
mg = MetaGoal(
    goal_id="committed_goal",
    origin="test",
    parent_goals=(),
    confidence=0.7,
    utility_estimate=0.5,
    lifecycle_state="active",
    description="Test",
    success_criteria={"domain": "test"},
    priority=0.7,
    generation_turn=1,
    generation_reason="test",
)
result = evaluator.evaluate_counterfactual(mg, reg)
expected_bonus = min(4 * COMMITMENT_WEIGHT, COMMITMENT_CAP)
_test(
    "evaluator computes commitment from streak",
    abs(result.commitment_bonus - expected_bonus) < 0.001,
    f"got={result.commitment_bonus:.3f}, expected={expected_bonus:.3f}",
)
_test(
    "commitment in reasoning",
    "commitment:" in result.reasoning,
    f"reasoning={result.reasoning}",
)

# No streak → no commitment
reg2 = GoalRegistry()
reg2.add_goal(GoalState(goal_id="new_goal", description="New", priority=0.5))
mg2 = MetaGoal(
    goal_id="new_goal",
    origin="test",
    parent_goals=(),
    confidence=0.7,
    utility_estimate=0.5,
    lifecycle_state="active",
    description="New",
    success_criteria={"domain": "test"},
    priority=0.5,
    generation_turn=1,
    generation_reason="test",
)
result2 = evaluator.evaluate_counterfactual(mg2, reg2)
_test(
    "no streak → commitment_bonus is 0.0",
    result2.commitment_bonus == 0.0,
    f"got={result2.commitment_bonus}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. GoalArbitrator — switch_penalty
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. GoalArbitrator — Switch Penalty")

arb = GoalArbitrator()
sw_reg = GoalRegistry()
g_a = GoalState(goal_id="goal_a", description="A", priority=0.7)
g_b = GoalState(goal_id="goal_b", description="B", priority=0.7)
sw_reg.add_goal(g_a)
sw_reg.add_goal(g_b)

ta = sw_reg.get_tracker("goal_a")
tb = sw_reg.get_tracker("goal_b")
ta.update_success(0.6)
ta.uses = 3
tb.update_success(0.55)
tb.uses = 3

# Without previous_active → no penalty
arb_result_none = arb.select_active_goal(sw_reg, previous_active_goal_id=None)
_test(
    "no previous → no penalty influence",
    arb_result_none.selected_goal_id is not None,
)

# With goal_a as previous → switching to goal_b incurs penalty
arb_result_a = arb.select_active_goal(sw_reg, previous_active_goal_id="goal_a")
_test(
    "previous=goal_a → goal_a favored by switch cost",
    arb_result_a.selected_goal_id == "goal_a",
    f"selected={arb_result_a.selected_goal_id}",
)
_test(
    "reason indicates commitment",
    "committed" in arb_result_a.reason,
    f"reason={arb_result_a.reason}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. System sticks with good goal across turns
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. Sticks with Good Goal Across Turns")

stick_reg = GoalRegistry()
g1 = GoalState(goal_id="primary", description="Primary", priority=0.7)
g2 = GoalState(goal_id="secondary", description="Secondary", priority=0.65)
stick_reg.add_goal(g1)
stick_reg.add_goal(g2)
stick_arb = GoalArbitrator()

selections = []
prev = None
for turn in range(5):
    stick_reg.advance_turn()
    result = stick_arb.select_active_goal(stick_reg, previous_active_goal_id=prev)
    selected = result.selected_goal_id
    selections.append(selected)
    # Update persistence
    for gid, trk in stick_reg.get_all_trackers().items():
        trk.update_persistence(is_active=(gid == selected))
    stick_reg.set_active_goal(selected)
    prev = selected

_test(
    "same goal selected every turn",
    len(set(selections)) == 1,
    f"selections={selections}",
)
_test(
    "primary selected",
    selections[0] == "primary",
)

# Check streak accumulated
trk_primary = stick_reg.get_tracker("primary")
_test(
    "persistence streak accumulated",
    trk_primary.persistence_streak == 5.0,
    f"streak={trk_primary.persistence_streak}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Avoids oscillation between near-equal goals
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. Oscillation Prevention")

osc_reg = GoalRegistry()
osc_a = GoalState(goal_id="osc_a", description="A", priority=0.7)
osc_b = GoalState(goal_id="osc_b", description="B", priority=0.7)
osc_reg.add_goal(osc_a)
osc_reg.add_goal(osc_b)

# Make them nearly equal
ta = osc_reg.get_tracker("osc_a")
tb = osc_reg.get_tracker("osc_b")
ta.update_success(0.60)
tb.update_success(0.59)
ta.uses = 5
tb.uses = 5

osc_arb = GoalArbitrator()
osc_selections = []
osc_prev = "osc_a"
osc_reg.set_active_goal("osc_a")

for turn in range(8):
    osc_reg.advance_turn()
    result = osc_arb.select_active_goal(osc_reg, previous_active_goal_id=osc_prev)
    selected = result.selected_goal_id
    osc_selections.append(selected)
    for gid, trk in osc_reg.get_all_trackers().items():
        trk.update_persistence(is_active=(gid == selected))
    osc_reg.set_active_goal(selected)
    osc_prev = selected

switches = sum(
    1
    for i in range(1, len(osc_selections))
    if osc_selections[i] != osc_selections[i - 1]
)
_test(
    "near-equal goals: minimal switching",
    switches <= 1,
    f"switches={switches}, selections={osc_selections}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Switches when clearly better goal appears
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. Switches for Clearly Better Goal")

sw2_reg = GoalRegistry()
sw2_a = GoalState(goal_id="incumbent", description="A", priority=0.6)
sw2_b = GoalState(goal_id="challenger", description="B", priority=0.9)
sw2_reg.add_goal(sw2_a)
sw2_reg.add_goal(sw2_b)

ta = sw2_reg.get_tracker("incumbent")
tb = sw2_reg.get_tracker("challenger")
ta.update_success(0.5)
tb.update_success(0.8)
ta.uses = 5
tb.uses = 5

sw2_arb = GoalArbitrator()
result = sw2_arb.select_active_goal(sw2_reg, previous_active_goal_id="incumbent")
_test(
    "clearly better goal wins despite switch cost",
    result.selected_goal_id == "challenger",
    f"selected={result.selected_goal_id}",
)
_test(
    "reason indicates switch",
    "switched" in result.reason,
    f"reason={result.reason}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Uncertainty can override commitment
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. Uncertainty Overrides Commitment")

cr_committed_low_conf = CounterfactualResult(
    expected_utility=0.2,
    expected_delta=0.0,
    confidence=0.2,
    reasoning="test",
    commitment_bonus=0.15,
)

cr_new_low_conf = CounterfactualResult(
    expected_utility=0.2,
    expected_delta=0.0,
    confidence=0.2,
    reasoning="test",
    commitment_bonus=0.0,
)

# Both have low confidence → high exploration_boost
exp_committed = cr_committed_low_conf.exploration_boost
exp_new = cr_new_low_conf.exploration_boost
_test(
    "both get same exploration_boost from uncertainty",
    abs(exp_committed - exp_new) < 0.001,
    f"committed={exp_committed:.3f}, new={exp_new:.3f}",
)

# But the new goal's uncertainty competes with the committed goal's bonus
_test(
    "exploration_boost is significant vs commitment",
    exp_new > 0.5 * cr_committed_low_conf.commitment_bonus,
    f"exp_boost={exp_new:.3f}, half_commit={0.5 * cr_committed_low_conf.commitment_bonus:.3f}",
)

# High uncertainty on a novel goal with decent utility beats commitment
cr_high_unc = CounterfactualResult(
    expected_utility=0.4,
    expected_delta=0.0,
    confidence=0.1,
    reasoning="test",
    commitment_bonus=0.0,
)
cr_committed_moderate = CounterfactualResult(
    expected_utility=0.3,
    expected_delta=0.0,
    confidence=0.8,
    reasoning="test",
    commitment_bonus=0.15,
)
_test(
    "high uncertainty novel goal can beat committed goal",
    cr_high_unc.effective_utility > cr_committed_moderate.effective_utility,
    f"novel={cr_high_unc.effective_utility:.3f}, committed={cr_committed_moderate.effective_utility:.3f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Exploration still competes with commitment
# ═══════════════════════════════════════════════════════════════════════════════

_section("14. Exploration vs Commitment Tradeoff")

from umh.runtime_engine.adaptive_exploration import ExplorationController, DEFAULT_EXPLORATION

ctrl = ExplorationController()
state_default = ctrl.compute()
_test(
    "default exploration rate unchanged",
    abs(state_default.exploration_rate - DEFAULT_EXPLORATION) < 0.001,
)

ctrl2 = ExplorationController()
state_unstable = ctrl2.compute(convergence_status="unstable")
_test(
    "unstable → higher exploration even with commitment in system",
    state_unstable.exploration_rate > DEFAULT_EXPLORATION,
    f"rate={state_unstable.exploration_rate:.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 15. DecisionTrace — persistence fields
# ═══════════════════════════════════════════════════════════════════════════════

_section("15. DecisionTrace — Persistence Fields")

trace = build_trace(
    turn_id=1,
    persistence_streaks={"goal_a": 3.0, "goal_b": 0.5},
    commitment_bonuses={"goal_a": 0.15, "goal_b": 0.0},
    switch_penalty_applied=False,
)
_test("trace has persistence_streaks", trace.persistence_streaks is not None)
_test("trace has commitment_bonuses", trace.commitment_bonuses is not None)
_test("trace has switch_penalty_applied", trace.switch_penalty_applied is not None)
_test("switch_penalty_applied is False", trace.switch_penalty_applied is False)

td = trace.to_dict()
_test("to_dict has persistence_streaks", "persistence_streaks" in td)
_test("to_dict has commitment_bonuses", "commitment_bonuses" in td)
_test("to_dict has switch_penalty_applied", "switch_penalty_applied" in td)

# Empty trace: fields are None
empty_trace = build_trace(turn_id=2)
_test("empty: persistence_streaks None", empty_trace.persistence_streaks is None)
_test("empty: commitment_bonuses None", empty_trace.commitment_bonuses is None)
_test("empty: switch_penalty_applied None", empty_trace.switch_penalty_applied is None)

etd = empty_trace.to_dict()
_test("empty to_dict: no persistence_streaks", "persistence_streaks" not in etd)
_test("empty to_dict: no commitment_bonuses", "commitment_bonuses" not in etd)
_test("empty to_dict: no switch_penalty_applied", "switch_penalty_applied" not in etd)

# Switch applied trace
switch_trace = build_trace(
    turn_id=3,
    switch_penalty_applied=True,
)
_test("switch trace: applied=True", switch_trace.switch_penalty_applied is True)


# ═══════════════════════════════════════════════════════════════════════════════
# 16. Determinism
# ═══════════════════════════════════════════════════════════════════════════════

_section("16. Determinism")


def _run_determinism_trial():
    r = GoalRegistry()
    a = GoalState(goal_id="da", description="A", priority=0.7)
    b = GoalState(goal_id="db", description="B", priority=0.65)
    r.add_goal(a)
    r.add_goal(b)
    arb = GoalArbitrator()

    results = []
    prev = None
    for _ in range(5):
        r.advance_turn()
        res = arb.select_active_goal(r, previous_active_goal_id=prev)
        results.append(res.selected_goal_id)
        for gid, trk in r.get_all_trackers().items():
            trk.update_persistence(is_active=(gid == res.selected_goal_id))
        r.set_active_goal(res.selected_goal_id)
        prev = res.selected_goal_id
    return results


trial1 = _run_determinism_trial()
trial2 = _run_determinism_trial()
_test("deterministic selection sequence", trial1 == trial2, f"{trial1} vs {trial2}")

# CounterfactualResult determinism
cr_a = CounterfactualResult(
    expected_utility=0.3,
    expected_delta=0.0,
    confidence=0.7,
    reasoning="test",
    commitment_bonus=0.15,
)
cr_b = CounterfactualResult(
    expected_utility=0.3,
    expected_delta=0.0,
    confidence=0.7,
    reasoning="test",
    commitment_bonus=0.15,
)
_test(
    "deterministic effective_utility", cr_a.effective_utility == cr_b.effective_utility
)

# 100x
all_same = all(
    CounterfactualResult(
        expected_utility=0.3,
        expected_delta=0.0,
        confidence=0.7,
        reasoning="test",
        commitment_bonus=0.15,
    ).effective_utility
    == cr_a.effective_utility
    for _ in range(100)
)
_test("100x identical", all_same)


# ═══════════════════════════════════════════════════════════════════════════════
# 17. Backward Compatibility
# ═══════════════════════════════════════════════════════════════════════════════

_section("17. Backward Compatibility")

cr_compat = CounterfactualResult(
    expected_utility=0.3,
    expected_delta=0.0,
    confidence=0.8,
    reasoning="test",
)
_test("compat: commitment_bonus defaults 0.0", cr_compat.commitment_bonus == 0.0)
_test(
    "compat: effective = expected + exploration + horizon (no commitment)",
    abs(
        cr_compat.effective_utility
        - (cr_compat.expected_utility + cr_compat.exploration_boost)
    )
    < 0.001,
)

# GoalTracker backward compat
t_compat = GoalTracker(goal_id="c1")
_test("compat: persistence_streak defaults 0.0", t_compat.persistence_streak == 0.0)
_test("compat: to_dict still works", "persistence_streak" in t_compat.to_dict())

# GoalArbitrator without previous_active
arb_compat = GoalArbitrator()
compat_reg = GoalRegistry()
compat_reg.add_goal(GoalState(goal_id="x", description="X", priority=0.5))
compat_result = arb_compat.select_active_goal(compat_reg)
_test(
    "compat: arbitrator works without previous_active",
    compat_result.selected_goal_id == "x",
)

# DecisionTrace without new fields
trace_compat = build_trace(turn_id=1)
_test(
    "compat: trace works without persistence fields",
    trace_compat.persistence_streaks is None,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 18. No LLM Calls
# ═══════════════════════════════════════════════════════════════════════════════

_section("18. No LLM Calls")

_changed_files = [
    "eos/goal_state.py",
    "eos/counterfactual_eval.py",
    "eos/goal_arbitrator.py",
    "eos/decision_trace.py",
]

for fpath in _changed_files:
    with open(f"/opt/OS/{fpath}") as f:
        src = f.read()
    _test(
        f"{fpath.split('/')[-1]}: no call_with_fallback",
        "call_with_fallback" not in src,
    )
    _test(f"{fpath.split('/')[-1]}: no import random", "import random" not in src)


# ═══════════════════════════════════════════════════════════════════════════════
# 19. ExecutionSpine Unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("19. ExecutionSpine Unchanged")

with open("/opt/OS/eos/execution_spine.py") as f:
    spine_src = f.read()

_test("spine: no persistence ref", "persistence_streak" not in spine_src)
_test("spine: no commitment ref", "commitment_bonus" not in spine_src)
_test("spine: no switch_penalty ref", "switch_penalty" not in spine_src)
_test("spine: no SWITCH_COST ref", "SWITCH_COST" not in spine_src)


# ═══════════════════════════════════════════════════════════════════════════════
# 20. Switch Cost math
# ═══════════════════════════════════════════════════════════════════════════════

_section("20. Switch Cost Math")

# Two goals with known utilities
math_reg = GoalRegistry()
math_reg.add_goal(GoalState(goal_id="ma", description="A", priority=0.6))
math_reg.add_goal(GoalState(goal_id="mb", description="B", priority=0.6))
ta = math_reg.get_tracker("ma")
tb = math_reg.get_tracker("mb")
ta.update_success(0.5)
tb.update_success(0.5)
ta.uses = 1
tb.uses = 1

# Utilities should be equal
math_arb = GoalArbitrator()
r_no_prev = math_arb.select_active_goal(math_reg)

# With previous=ma, switching to mb costs SWITCH_COST
r_prev_a = math_arb.select_active_goal(math_reg, previous_active_goal_id="ma")
_test(
    "equal goals: previous incumbent wins",
    r_prev_a.selected_goal_id == "ma",
    f"selected={r_prev_a.selected_goal_id}",
)

# Give mb enough advantage to overcome SWITCH_COST
tb.success_score = 0.95
r_prev_a2 = math_arb.select_active_goal(math_reg, previous_active_goal_id="ma")
_test(
    "large advantage overcomes switch cost",
    r_prev_a2.selected_goal_id == "mb",
    f"selected={r_prev_a2.selected_goal_id}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 21. Persistence streak decay to near-zero
# ═══════════════════════════════════════════════════════════════════════════════

_section("21. Streak Decay to Near-Zero")

decay_trk = GoalTracker(goal_id="decay")
decay_trk.update_persistence(is_active=True)
decay_trk.update_persistence(is_active=True)
_test("start streak=2", decay_trk.persistence_streak == 2.0)

for _ in range(30):
    decay_trk.update_persistence(is_active=False)

_test(
    "30 inactive turns → streak near zero",
    decay_trk.persistence_streak < 0.01,
    f"streak={decay_trk.persistence_streak:.6f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 22. Commitment bonus capping
# ═══════════════════════════════════════════════════════════════════════════════

_section("22. Commitment Bonus Capping")

cap_reg = GoalRegistry()
cap_reg.add_goal(GoalState(goal_id="capped", description="Test", priority=0.5))
cap_trk = cap_reg.get_tracker("capped")
for _ in range(20):
    cap_trk.update_persistence(is_active=True)

mg_cap = MetaGoal(
    goal_id="capped",
    origin="test",
    parent_goals=(),
    confidence=0.7,
    utility_estimate=0.5,
    lifecycle_state="active",
    description="Test",
    success_criteria={"domain": "test"},
    priority=0.5,
    generation_turn=1,
    generation_reason="test",
)
cf_cap = CounterfactualEvaluator()
result_cap = cf_cap.evaluate_counterfactual(mg_cap, cap_reg)
_test(
    "commitment capped at COMMITMENT_CAP",
    abs(result_cap.commitment_bonus - COMMITMENT_CAP) < 0.001,
    f"got={result_cap.commitment_bonus:.3f}, cap={COMMITMENT_CAP}",
)
_test(
    "streak=20 but bonus not > cap",
    result_cap.commitment_bonus <= COMMITMENT_CAP,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 23. Blend passes previous_active_goal_id
# ═══════════════════════════════════════════════════════════════════════════════

_section("23. Blend with Previous Active")

blend_reg = GoalRegistry()
blend_reg.add_goal(GoalState(goal_id="ba", description="A", priority=0.7))
blend_reg.add_goal(GoalState(goal_id="bb", description="B", priority=0.65))
blend_arb = GoalArbitrator()

# Blend without previous
blend1 = blend_arb.blend_goals(blend_reg)
_test("blend works without previous", blend1.primary_goal_id == "ba")

# Blend with previous
blend2 = blend_arb.blend_goals(blend_reg, previous_active_goal_id="ba")
_test("blend with previous selects same", blend2.primary_goal_id == "ba")


# ═══════════════════════════════════════════════════════════════════════════════
# 24. No New Dependencies
# ═══════════════════════════════════════════════════════════════════════════════

_section("24. No New Dependencies")

for fpath in _changed_files:
    with open(f"/opt/OS/{fpath}") as f:
        src = f.read()
    _test(f"{fpath.split('/')[-1]}: no requests", "import requests" not in src)
    _test(f"{fpath.split('/')[-1]}: no httpx", "import httpx" not in src)
    _test(f"{fpath.split('/')[-1]}: no numpy", "import numpy" not in src)


# ═══════════════════════════════════════════════════════════════════════════════
# 25. GoalRegistry snapshot includes persistence
# ═══════════════════════════════════════════════════════════════════════════════

_section("25. Registry Snapshot — Persistence")

snap_reg = GoalRegistry()
snap_reg.add_goal(GoalState(goal_id="snap_a", description="A", priority=0.7))
trk = snap_reg.get_tracker("snap_a")
trk.update_persistence(is_active=True)
trk.update_persistence(is_active=True)

snap = snap_reg.snapshot()
goal_entry = snap["goals"][0]
_test("snapshot has persistence_streak", "persistence_streak" in goal_entry)
_test(
    "snapshot persistence_streak correct",
    abs(goal_entry["persistence_streak"] - 2.0) < 0.001,
)


# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'=' * 60}")
print(f"  TOTAL: {_PASS} passed, {_FAIL} failed (out of {_PASS + _FAIL})")
print(f"{'=' * 60}")

sys.exit(0 if _FAIL == 0 else 1)
