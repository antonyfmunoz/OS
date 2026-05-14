"""
Tests for adaptive exploration controller.

Proves:
  1. Exploration increases under instability
  2. Exploration decreases under convergence
  3. Bounded behavior [MIN, MAX]
  4. Determinism: same signals → same rate
  5. No regression to existing systems
  6. No new LLM calls
  7. ExecutionSpine unchanged
  8. Integration: num_candidates and budget respond to rate
"""

import sys
import os

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
    from umh.runtime_engine.adaptive_exploration import (
        ExplorationController,
        ExplorationState,
        NO_EXPLORATION_STATE,
        MIN_EXPLORATION,
        MAX_EXPLORATION,
        DEFAULT_EXPLORATION,
        exploration_rate_to_num_candidates,
        exploration_rate_to_budget_modifier,
    )

    check("adaptive_exploration imports", True)
except Exception as e:
    check("adaptive_exploration imports", False, str(e))

try:
    from umh.runtime_engine.decision_trace import DecisionTrace, build_trace

    check("decision_trace imports", True)
except Exception as e:
    check("decision_trace imports", False, str(e))

try:
    from umh.runtime_engine.execution_budget import derive_budget

    check("execution_budget imports", True)
except Exception as e:
    check("execution_budget imports", False, str(e))

try:
    from umh.runtime_engine.multi_strategy import run_with_strategies

    check("multi_strategy imports", True)
except Exception as e:
    check("multi_strategy imports", False, str(e))


# ─────────────────────────────────────────────────────────────
section("2. ExplorationState Model")
# ─────────────────────────────────────────────────────────────

state = ExplorationState(
    exploration_rate=0.35,
    uncertainty_score=0.2,
    recent_performance=0.05,
    convergence_state="stable",
    reason="stable_positive_progress",
)
check("created", True)
check("exploration_rate", state.exploration_rate == 0.35)
check("uncertainty_score", state.uncertainty_score == 0.2)
check("convergence_state", state.convergence_state == "stable")
check("reason", state.reason == "stable_positive_progress")

try:
    state.exploration_rate = 0.5  # type: ignore
    check("frozen enforced", False, "mutation allowed")
except (AttributeError, TypeError):
    check("frozen enforced", True)

d = state.to_dict()
check("to_dict has exploration_rate", "exploration_rate" in d)
check("to_dict has uncertainty_score", "uncertainty_score" in d)
check("to_dict has convergence_state", "convergence_state" in d)
check("to_dict has reason", "reason" in d)


# ─────────────────────────────────────────────────────────────
section("3. NO_EXPLORATION_STATE Sentinel")
# ─────────────────────────────────────────────────────────────

check(
    "default rate",
    NO_EXPLORATION_STATE.exploration_rate == DEFAULT_EXPLORATION,
    f"got {NO_EXPLORATION_STATE.exploration_rate}",
)
check("no_signals reason", NO_EXPLORATION_STATE.reason == "no_signals")


# ─────────────────────────────────────────────────────────────
section("4. Exploration Increases Under Instability")
# ─────────────────────────────────────────────────────────────

ctrl = ExplorationController()

# Unstable convergence → higher exploration
unstable = ctrl.compute(
    convergence_status="unstable",
    goal_deltas=[-0.1, -0.05, -0.08],
)
check(
    "unstable → above default",
    unstable.exploration_rate > DEFAULT_EXPLORATION,
    f"got {unstable.exploration_rate:.4f}, default={DEFAULT_EXPLORATION}",
)
check("reason contains unstable", "unstable" in unstable.reason)

# High variance in candidate scores → higher uncertainty → higher exploration
ctrl2 = ExplorationController()
high_var = ctrl2.compute(
    candidate_scores=[0.3, 0.9, 0.2, 0.85],
)
check(
    "high variance → high uncertainty",
    high_var.uncertainty_score > 0.3,
    f"got {high_var.uncertainty_score:.4f}",
)

# Negative deltas → boost
ctrl3 = ExplorationController()
negative = ctrl3.compute(
    goal_deltas=[-0.1, -0.05, -0.08, -0.06, -0.04],
)
check(
    "negative deltas → above default",
    negative.exploration_rate > DEFAULT_EXPLORATION,
    f"got {negative.exploration_rate:.4f}",
)
check("reason contains negative", "negative" in negative.reason)


# ─────────────────────────────────────────────────────────────
section("5. Exploration Decreases Under Convergence")
# ─────────────────────────────────────────────────────────────

ctrl4 = ExplorationController()
stable = ctrl4.compute(
    convergence_status="stable",
    goal_deltas=[0.05, 0.08, 0.06, 0.07, 0.04],
)
check(
    "stable + positive → below default",
    stable.exploration_rate < DEFAULT_EXPLORATION,
    f"got {stable.exploration_rate:.4f}",
)
check(
    "reason contains stable",
    "stable" in stable.reason,
    f"got {stable.reason}",
)
check(
    "reason contains positive",
    "positive" in stable.reason,
    f"got {stable.reason}",
)


# ─────────────────────────────────────────────────────────────
section("6. Bounded Behavior")
# ─────────────────────────────────────────────────────────────

# Push everything to max
ctrl_max = ExplorationController()
extreme_high = ctrl_max.compute(
    convergence_status="unstable",
    goal_deltas=[-0.5, -0.4, -0.3, -0.2, -0.1],
    blended_entropy=0.9,
    candidate_scores=[0.1, 0.9, 0.2, 0.8],
)
check(
    "clamped to MAX_EXPLORATION",
    extreme_high.exploration_rate <= MAX_EXPLORATION,
    f"got {extreme_high.exploration_rate:.4f}, max={MAX_EXPLORATION}",
)
check(
    "above MIN_EXPLORATION",
    extreme_high.exploration_rate >= MIN_EXPLORATION,
)

# Push everything to min
ctrl_min = ExplorationController()
extreme_low = ctrl_min.compute(
    convergence_status="stable",
    goal_deltas=[0.2, 0.3, 0.15, 0.25, 0.1],
)
check(
    "clamped to MIN_EXPLORATION",
    extreme_low.exploration_rate >= MIN_EXPLORATION,
    f"got {extreme_low.exploration_rate:.4f}, min={MIN_EXPLORATION}",
)
check(
    "below MAX_EXPLORATION",
    extreme_low.exploration_rate <= MAX_EXPLORATION,
)


# ─────────────────────────────────────────────────────────────
section("7. Oscillation Detection")
# ─────────────────────────────────────────────────────────────

ctrl_osc = ExplorationController()
oscillating = ctrl_osc.compute(
    goal_deltas=[0.05, -0.05, 0.04, -0.06, 0.03, -0.04],
)
check(
    "oscillation detected",
    "oscillating" in oscillating.reason,
    f"got reason: {oscillating.reason}",
)


# ─────────────────────────────────────────────────────────────
section("8. Entropy Boost")
# ─────────────────────────────────────────────────────────────

ctrl_ent = ExplorationController()
high_ent = ctrl_ent.compute(blended_entropy=0.8)
ctrl_ent2 = ExplorationController()
low_ent = ctrl_ent2.compute(blended_entropy=0.2)
check(
    "high entropy → higher rate",
    high_ent.exploration_rate > low_ent.exploration_rate,
    f"high={high_ent.exploration_rate:.4f}, low={low_ent.exploration_rate:.4f}",
)


# ─────────────────────────────────────────────────────────────
section("9. Determinism — Same Signals → Same Rate")
# ─────────────────────────────────────────────────────────────

ctrl_d1 = ExplorationController()
ctrl_d2 = ExplorationController()

signals = {
    "goal_deltas": [0.03, -0.02, 0.05],
    "convergence_status": "recovering",
    "blended_entropy": 0.4,
    "candidate_scores": [0.6, 0.7, 0.65],
}

s1 = ctrl_d1.compute(**signals)
s2 = ctrl_d2.compute(**signals)
check(
    "deterministic: same rate",
    s1.exploration_rate == s2.exploration_rate,
    f"s1={s1.exploration_rate:.4f}, s2={s2.exploration_rate:.4f}",
)
check("deterministic: same reason", s1.reason == s2.reason)
check("deterministic: same uncertainty", s1.uncertainty_score == s2.uncertainty_score)


# ─────────────────────────────────────────────────────────────
section("10. Performance EMA Tracking")
# ─────────────────────────────────────────────────────────────

ctrl_ema = ExplorationController()
ctrl_ema.compute(goal_deltas=[0.1, 0.2])
ema1 = ctrl_ema.performance_ema
ctrl_ema.compute(goal_deltas=[0.1, 0.2, -0.3])
ema2 = ctrl_ema.performance_ema
check(
    "EMA decreases after negative delta",
    ema2 < ema1,
    f"ema1={ema1:.4f}, ema2={ema2:.4f}",
)
check("turns tracked", ctrl_ema.turns_computed == 2)


# ─────────────────────────────────────────────────────────────
section("11. exploration_rate_to_num_candidates")
# ─────────────────────────────────────────────────────────────

check(
    "rate=0.0 → base candidates",
    exploration_rate_to_num_candidates(0.0) == 2,
    f"got {exploration_rate_to_num_candidates(0.0)}",
)
check(
    "rate=1.0 → max candidates",
    exploration_rate_to_num_candidates(1.0) == 5,
    f"got {exploration_rate_to_num_candidates(1.0)}",
)
check(
    "rate=0.5 → mid candidates",
    2 <= exploration_rate_to_num_candidates(0.5) <= 5,
    f"got {exploration_rate_to_num_candidates(0.5)}",
)
check(
    "monotonic: higher rate → more candidates",
    exploration_rate_to_num_candidates(0.8) >= exploration_rate_to_num_candidates(0.2),
)


# ─────────────────────────────────────────────────────────────
section("12. exploration_rate_to_budget_modifier")
# ─────────────────────────────────────────────────────────────

check(
    "rate=0.0 → 0.5 (concentrated)",
    exploration_rate_to_budget_modifier(0.0) == 0.5,
)
check(
    "rate=0.5 → 1.0 (neutral)",
    exploration_rate_to_budget_modifier(0.5) == 1.0,
)
check(
    "rate=1.0 → 1.5 (spread)",
    exploration_rate_to_budget_modifier(1.0) == 1.5,
)


# ─────────────────────────────────────────────────────────────
section("13. DecisionTrace Exploration Fields")
# ─────────────────────────────────────────────────────────────

trace_with = build_trace(
    turn_id=7,
    exploration_rate=0.35,
    exploration_reason="stable_positive_progress",
)
check("exploration_rate set", trace_with.exploration_rate == 0.35)
check(
    "exploration_reason set",
    trace_with.exploration_reason == "stable_positive_progress",
)

d = trace_with.to_dict()
check("exploration_rate in dict", "exploration_rate" in d)
check("exploration_reason in dict", "exploration_reason" in d)
check("exploration_rate rounded", d["exploration_rate"] == 0.35)

trace_without = build_trace(turn_id=8)
check("exploration_rate None by default", trace_without.exploration_rate is None)
check("exploration_reason None by default", trace_without.exploration_reason is None)

d2 = trace_without.to_dict()
check("exploration_rate absent when None", "exploration_rate" not in d2)
check("exploration_reason absent when None", "exploration_reason" not in d2)


# ─────────────────────────────────────────────────────────────
section("14. Execution Budget with Exploration Modifier")
# ─────────────────────────────────────────────────────────────


# Create a mock BlendedGoalState
class MockBlend:
    def __init__(self, goals, primary_goal_id):
        self.goals = goals
        self.primary_goal_id = primary_goal_id


blend = MockBlend(
    goals=(("sell", 0.7), ("analyze", 0.3)),
    primary_goal_id="sell",
)

# No modifier (default = 1.0)
budget_neutral = derive_budget(blend, total_candidates=6, exploration_modifier=1.0)
sell_neutral = budget_neutral.get_budget("sell").candidate_slots
analyze_neutral = budget_neutral.get_budget("analyze").candidate_slots

# High exploration (modifier = 1.5) → secondary gets more relative slots
budget_explore = derive_budget(blend, total_candidates=6, exploration_modifier=1.5)
sell_explore = budget_explore.get_budget("sell").candidate_slots
analyze_explore = budget_explore.get_budget("analyze").candidate_slots

# Low exploration (modifier = 0.5) → secondary gets fewer relative slots
budget_exploit = derive_budget(blend, total_candidates=6, exploration_modifier=0.5)
sell_exploit = budget_exploit.get_budget("sell").candidate_slots
analyze_exploit = budget_exploit.get_budget("analyze").candidate_slots

check(
    "total candidates preserved (neutral)",
    sell_neutral + analyze_neutral == 6,
)
check(
    "total candidates preserved (explore)",
    sell_explore + analyze_explore == 6,
)
check(
    "total candidates preserved (exploit)",
    sell_exploit + analyze_exploit == 6,
)
check(
    "high exploration → secondary gets more or equal",
    analyze_explore >= analyze_exploit,
    f"explore={analyze_explore}, exploit={analyze_exploit}",
)


# ─────────────────────────────────────────────────────────────
section("15. SessionRuntime Integration")
# ─────────────────────────────────────────────────────────────

from umh.runtime_engine.session_runtime import SessionRuntime

session = SessionRuntime(ctx=None)
exp_state = session.get_exploration_state()
check(
    "initial state is NO_EXPLORATION_STATE",
    exp_state.reason == "no_signals",
)


# ─────────────────────────────────────────────────────────────
section("16. No LLM Calls")
# ─────────────────────────────────────────────────────────────

import inspect

src = inspect.getsource(sys.modules["umh.runtime_engine.adaptive_exploration"])
check("no call_with_fallback", "call_with_fallback" not in src)
check("no model_router", "model_router" not in src)
check("no agent_runtime", "agent_runtime" not in src)
check("no GenerativeModel", "GenerativeModel" not in src)


# ─────────────────────────────────────────────────────────────
section("17. ExecutionSpine Unchanged")
# ─────────────────────────────────────────────────────────────

spine_src = open("/opt/OS/eos/execution_spine.py").read()
check(
    "spine has no adaptive_exploration import", "adaptive_exploration" not in spine_src
)
check("spine has no exploration_rate", "exploration_rate" not in spine_src)
check("spine has no ExplorationController", "ExplorationController" not in spine_src)


# ─────────────────────────────────────────────────────────────
section("18. No Regression — Existing Systems")
# ─────────────────────────────────────────────────────────────

# Verify multi_strategy signature still works without exploration_rate
from umh.runtime_engine.multi_strategy import pick_strategies

strats = pick_strategies(num_candidates=2)
check("pick_strategies works", len(strats) >= 1)

# Verify execution_budget backward compat (no modifier = 1.0)
budget_compat = derive_budget(blend, total_candidates=4)
check("derive_budget works without modifier", budget_compat.total_candidates >= 2)

# Verify convergence imports still work
from umh.runtime_engine.convergence import ConvergenceStatus

check("ConvergenceStatus accessible", ConvergenceStatus.STABLE.value == "stable")


# ─────────────────────────────────────────────────────────────
section("19. Multi-Turn Evolution")
# ─────────────────────────────────────────────────────────────

# Simulate a session: starts unstable, converges, verify rate decreases
ctrl_mt = ExplorationController()

# Turn 1: unstable
s_t1 = ctrl_mt.compute(
    convergence_status="unstable",
    goal_deltas=[-0.1],
)

# Turn 2: recovering
s_t2 = ctrl_mt.compute(
    convergence_status="recovering",
    goal_deltas=[-0.1, 0.02],
)

# Turn 3-5: stable with positive progress
s_t3 = ctrl_mt.compute(
    convergence_status="stable",
    goal_deltas=[-0.1, 0.02, 0.05, 0.06, 0.04],
)

check(
    "rate decreases as system stabilizes",
    s_t3.exploration_rate < s_t1.exploration_rate,
    f"t1={s_t1.exploration_rate:.4f}, t3={s_t3.exploration_rate:.4f}",
)
check("turns tracked", ctrl_mt.turns_computed == 3)


# ─────────────────────────────────────────────────────────────
section("20. Recovery State")
# ─────────────────────────────────────────────────────────────

ctrl_rec = ExplorationController()
recovering = ctrl_rec.compute(
    convergence_status="recovering",
    goal_deltas=[0.01, 0.02, 0.03],
)
check(
    "recovering → moderate exploration",
    recovering.exploration_rate > MIN_EXPLORATION,
    f"got {recovering.exploration_rate:.4f}",
)
check(
    "recovering → reason contains recovering",
    "recovering" in recovering.reason,
)


# ═════════════════════════════════════════════════════════════
print(f"\n{'═' * 60}")
print(f"  RESULTS: {PASS} passed, {FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if FAIL > 0 else 0)
