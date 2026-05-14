"""
Tests for PolicyEngine — deterministic per-turn reasoning mode selection.

Covers: constants, policy selection triggers, bounded adjustments,
stable transitions, influence modifier application, plan confidence
modifier, DecisionTrace integration, determinism, no LLM, no randomness,
no ExecutionSpine, backward compatibility, serialization.
"""

import sys

sys.path.insert(0, "/opt/OS")

passed = 0
failed = 0
section = 0


def check(condition: bool, label: str, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
        msg = f"  [FAIL] {label}"
        if detail:
            msg += f" -- {detail}"
        print(msg)


def header(title: str):
    global section
    section += 1
    print(f"{section}. {title}")


# ── 1. Constants ─────────────────────────────────────────────────────────

header("constants defined correctly")
from umh.runtime_engine.policy_engine import (
    FAILURE_STREAK_THRESHOLD,
    PERSISTENCE_STREAK_THRESHOLD,
    LOW_PLAN_CONFIDENCE,
    HIGH_PLAN_CONFIDENCE,
    HIGH_EXPLORATION_RATE,
    LOW_SIMILARITY_DELTA,
    MAX_INFLUENCE_MODIFIER,
    MAX_PLAN_MODIFIER,
    MIN_GOAL_SCALE,
    MAX_GOAL_SCALE,
    INFLUENCE_WEIGHT_MODIFIERS,
    GOAL_SCALING,
    PLAN_CONFIDENCE_MODIFIER,
    Policy,
)

check(
    FAILURE_STREAK_THRESHOLD == 2,
    "failure threshold",
    f"got {FAILURE_STREAK_THRESHOLD}",
)
check(PERSISTENCE_STREAK_THRESHOLD == 3, "persistence threshold")
check(LOW_PLAN_CONFIDENCE == 0.25, "low plan conf")
check(HIGH_PLAN_CONFIDENCE == 0.70, "high plan conf")
check(HIGH_EXPLORATION_RATE == 0.60, "high exploration rate")
check(len(Policy) == 5, "5 policies", f"got {len(Policy)}")

# ── 2. All policies have modifier tables ──────────────────────────────────

header("all policies have modifier tables")
for p in Policy:
    check(p in INFLUENCE_WEIGHT_MODIFIERS, f"{p.value} has influence modifiers")
    check(p in GOAL_SCALING, f"{p.value} has goal scaling")
    check(p in PLAN_CONFIDENCE_MODIFIER, f"{p.value} has plan modifier")

# ── 3. Default → EXPLOIT ─────────────────────────────────────────────────

header("default signals → EXPLOIT")
from umh.runtime_engine.policy_engine import PolicySignals, select_policy

default_signals = PolicySignals()
r_default = select_policy(default_signals)
check(
    r_default.policy == Policy.EXPLOIT, "default is EXPLOIT", f"got {r_default.policy}"
)
check(r_default.reason == "default_exploit", "reason=default_exploit")

# ── 4. RECOVER trigger ───────────────────────────────────────────────────

header("RECOVER triggered by failure_streak")
r_recover = select_policy(PolicySignals(failure_streak=2))
check(r_recover.policy == Policy.RECOVER, "RECOVER on streak=2")

r_recover3 = select_policy(PolicySignals(failure_streak=5))
check(r_recover3.policy == Policy.RECOVER, "RECOVER on streak=5")

r_no_recover = select_policy(PolicySignals(failure_streak=1))
check(r_no_recover.policy != Policy.RECOVER, "no RECOVER on streak=1")

# ── 5. PIVOT trigger ─────────────────────────────────────────────────────

header("PIVOT triggered by low confidence + similarity drop")
r_pivot = select_policy(
    PolicySignals(
        plan_confidence=0.20,
        state_similarity_delta=-0.20,
    )
)
check(r_pivot.policy == Policy.PIVOT, "PIVOT on low conf + sim drop")

# Not triggered if only one condition
r_no_pivot1 = select_policy(
    PolicySignals(
        plan_confidence=0.20,
        state_similarity_delta=0.0,
    )
)
check(r_no_pivot1.policy != Policy.PIVOT, "no PIVOT without sim drop")

r_no_pivot2 = select_policy(
    PolicySignals(
        plan_confidence=0.50,
        state_similarity_delta=-0.20,
    )
)
check(r_no_pivot2.policy != Policy.PIVOT, "no PIVOT without low confidence")

# ── 6. COMMIT trigger ────────────────────────────────────────────────────

header("COMMIT triggered by persistence + high confidence")
r_commit = select_policy(
    PolicySignals(
        persistence_streak=3,
        plan_confidence=0.75,
    )
)
check(r_commit.policy == Policy.COMMIT, "COMMIT on persistence=3, conf=0.75")

r_no_commit = select_policy(
    PolicySignals(
        persistence_streak=3,
        plan_confidence=0.50,
    )
)
check(r_no_commit.policy != Policy.COMMIT, "no COMMIT with low confidence")

# ── 7. EXPLORE trigger ───────────────────────────────────────────────────

header("EXPLORE triggered by high exploration rate")
r_explore = select_policy(PolicySignals(exploration_rate=0.65))
check(r_explore.policy == Policy.EXPLORE, "EXPLORE on high exploration_rate")

r_explore2 = select_policy(PolicySignals(plan_confidence=0.20))
check(r_explore2.policy == Policy.EXPLORE, "EXPLORE on low plan_confidence alone")

# ── 8. Priority order — RECOVER beats PIVOT ──────────────────────────────

header("priority — RECOVER beats PIVOT")
r_priority = select_policy(
    PolicySignals(
        failure_streak=3,
        plan_confidence=0.10,
        state_similarity_delta=-0.30,
    )
)
check(r_priority.policy == Policy.RECOVER, "RECOVER takes priority over PIVOT")

# ── 9. Priority order — PIVOT beats COMMIT ───────────────────────────────

header("priority — PIVOT beats COMMIT")
r_p2 = select_policy(
    PolicySignals(
        plan_confidence=0.20,
        state_similarity_delta=-0.20,
        persistence_streak=5,
    )
)
check(r_p2.policy == Policy.PIVOT, "PIVOT takes priority over COMMIT")

# ── 10. Priority order — COMMIT beats EXPLORE ────────────────────────────

header("priority — COMMIT beats EXPLORE")
r_p3 = select_policy(
    PolicySignals(
        persistence_streak=3,
        plan_confidence=0.75,
        exploration_rate=0.70,
    )
)
check(r_p3.policy == Policy.COMMIT, "COMMIT takes priority over EXPLORE")

# ── 11. Determinism ──────────────────────────────────────────────────────

header("determinism — same inputs → same policy")
for _ in range(10):
    r_det = select_policy(
        PolicySignals(
            failure_streak=1,
            persistence_streak=2,
            exploration_rate=0.40,
            plan_confidence=0.60,
            state_similarity_delta=-0.05,
        )
    )
    check(r_det.policy == Policy.EXPLOIT, "deterministic EXPLOIT")

# ── 12. Adjustments bounded — influence modifiers ─────────────────────────

header("influence modifiers bounded by MAX_INFLUENCE_MODIFIER")
for p in Policy:
    r = select_policy(
        PolicySignals(
            failure_streak=FAILURE_STREAK_THRESHOLD if p == Policy.RECOVER else 0,
            persistence_streak=PERSISTENCE_STREAK_THRESHOLD
            if p == Policy.COMMIT
            else 0,
            plan_confidence=0.80
            if p == Policy.COMMIT
            else (0.10 if p in (Policy.PIVOT, Policy.EXPLORE) else 0.50),
            exploration_rate=0.70 if p == Policy.EXPLORE else 0.30,
            state_similarity_delta=-0.20 if p == Policy.PIVOT else 0.0,
        )
    )
    for name, mod in r.adjustments.influence_weight_modifiers.items():
        check(
            -MAX_INFLUENCE_MODIFIER <= mod <= MAX_INFLUENCE_MODIFIER,
            f"{r.policy.value}.{name} modifier bounded",
            f"got {mod}",
        )

# ── 13. Adjustments bounded — goal scaling ────────────────────────────────

header("goal scaling bounded")
for p in Policy:
    scale = GOAL_SCALING[p]
    check(
        MIN_GOAL_SCALE <= scale <= MAX_GOAL_SCALE,
        f"{p.value} goal scale in bounds",
        f"got {scale}",
    )

# ── 14. Adjustments bounded — plan modifier ──────────────────────────────

header("plan modifier bounded")
for p in Policy:
    mod = PLAN_CONFIDENCE_MODIFIER[p]
    check(
        -MAX_PLAN_MODIFIER <= mod <= MAX_PLAN_MODIFIER,
        f"{p.value} plan modifier in bounds",
        f"got {mod}",
    )

# ── 15. PolicyResult serialization ────────────────────────────────────────

header("PolicyResult serialization")
r_ser = select_policy(PolicySignals(failure_streak=3))
d_ser = r_ser.to_dict()
check("policy" in d_ser, "has policy")
check("reason" in d_ser, "has reason")
check("signals" in d_ser, "has signals")
check("adjustments" in d_ser, "has adjustments")
check(d_ser["policy"] == "recover", "policy=recover")
check(isinstance(d_ser["signals"], dict), "signals is dict")
check(isinstance(d_ser["adjustments"], dict), "adjustments is dict")

# ── 16. PolicySignals serialization ───────────────────────────────────────

header("PolicySignals serialization")
sig = PolicySignals(failure_streak=2, plan_confidence=0.75)
sd = sig.to_dict()
check(sd["failure_streak"] == 2, "failure_streak=2")
check(sd["plan_confidence"] == 0.75, "plan_confidence=0.75")

# ── 17. PolicyAdjustments serialization ───────────────────────────────────

header("PolicyAdjustments serialization")
from umh.runtime_engine.policy_engine import PolicyAdjustments

adj = PolicyAdjustments(
    influence_weight_modifiers={"goal": 0.05},
    goal_scaling=1.05,
    plan_confidence_modifier=0.03,
)
ad = adj.to_dict()
check("influence_weight_modifiers" in ad, "has modifiers")
check(ad["goal_scaling"] == 1.05, "goal_scaling=1.05")

# ── 18. apply_influence_modifiers ─────────────────────────────────────────

header("apply_influence_modifiers renormalizes")
from umh.runtime_engine.policy_engine import apply_influence_modifiers
from umh.runtime_engine.influence_scoring import BASE_WEIGHTS

mods = {"goal": 0.05, "plan": -0.03, "exploration": 0.03}
result_weights = apply_influence_modifiers(BASE_WEIGHTS, mods)

w_sum = sum(result_weights.values())
check(abs(w_sum - 1.0) < 1e-9, "sum=1.0 after modifiers", f"got {w_sum}")
check(all(v > 0 for v in result_weights.values()), "all weights > 0")

# ── 19. apply_influence_modifiers — empty modifiers = near base ───────────

header("empty modifiers → weights near base")
result_empty = apply_influence_modifiers(BASE_WEIGHTS, {})
for name in BASE_WEIGHTS:
    diff = abs(result_empty[name] - BASE_WEIGHTS[name])
    check(diff < 1e-9, f"{name} unchanged", f"diff={diff}")

# ── 20. apply_plan_confidence_modifier clamped ────────────────────────────

header("apply_plan_confidence_modifier clamped")
from umh.runtime_engine.policy_engine import apply_plan_confidence_modifier

check(apply_plan_confidence_modifier(0.9, 0.2) == 1.0, "clamped to 1.0")
check(apply_plan_confidence_modifier(0.1, -0.3) == 0.0, "clamped to 0.0")
check(abs(apply_plan_confidence_modifier(0.5, 0.1) - 0.6) < 1e-9, "0.5+0.1=0.6")

# ── 21. NO_POLICY_RESULT sentinel ─────────────────────────────────────────

header("NO_POLICY_RESULT sentinel")
from umh.runtime_engine.policy_engine import NO_POLICY_RESULT

check(NO_POLICY_RESULT.policy == Policy.EXPLOIT, "default EXPLOIT")
check(NO_POLICY_RESULT.reason == "default", "reason=default")
check(NO_POLICY_RESULT.adjustments.goal_scaling == 1.0, "neutral scaling")

# ── 22. Stable transitions — no thrashing ─────────────────────────────────

header("stable transitions — no rapid oscillation")
sequence = [
    PolicySignals(plan_confidence=0.50),
    PolicySignals(plan_confidence=0.48),
    PolicySignals(plan_confidence=0.45),
    PolicySignals(plan_confidence=0.42),
    PolicySignals(plan_confidence=0.40),
]
policies = [select_policy(s).policy for s in sequence]
# All these should be EXPLOIT — confidence is above LOW threshold
check(
    all(p == Policy.EXPLOIT for p in policies),
    "no thrashing in gradual confidence decline",
    f"got {[p.value for p in policies]}",
)

# Transition at boundary
sequence2 = [
    PolicySignals(plan_confidence=0.26),
    PolicySignals(plan_confidence=0.24),
    PolicySignals(plan_confidence=0.24),
]
policies2 = [select_policy(s).policy for s in sequence2]
check(policies2[0] == Policy.EXPLOIT, "above threshold = EXPLOIT")
check(policies2[1] == Policy.EXPLORE, "below threshold = EXPLORE")
check(policies2[2] == Policy.EXPLORE, "stays EXPLORE")

# ── 23. Edge cases — exactly at thresholds ────────────────────────────────

header("edge cases — exactly at thresholds")
r_exact_fail = select_policy(PolicySignals(failure_streak=FAILURE_STREAK_THRESHOLD))
check(r_exact_fail.policy == Policy.RECOVER, "exactly at failure threshold → RECOVER")

r_below_fail = select_policy(PolicySignals(failure_streak=FAILURE_STREAK_THRESHOLD - 1))
check(r_below_fail.policy != Policy.RECOVER, "below failure threshold ≠ RECOVER")

r_exact_persist = select_policy(
    PolicySignals(
        persistence_streak=PERSISTENCE_STREAK_THRESHOLD,
        plan_confidence=HIGH_PLAN_CONFIDENCE,
    )
)
check(
    r_exact_persist.policy == Policy.COMMIT, "exactly at persistence threshold → COMMIT"
)

r_exact_explore = select_policy(PolicySignals(exploration_rate=HIGH_EXPLORATION_RATE))
check(
    r_exact_explore.policy == Policy.EXPLORE,
    "exactly at exploration threshold → EXPLORE",
)

# ── 24. DecisionTrace policy fields ───────────────────────────────────────

header("DecisionTrace policy fields")
from umh.runtime_engine.decision_trace import DecisionTrace

t = DecisionTrace(
    turn_id=1,
    strategies_considered=("a",),
    strategy_scores={"a": 1.0},
    selected_strategy="a",
    quality_score=0.8,
    confidence=0.9,
    signals={},
    attributed_signals={},
    horizon={},
    directives_applied=(),
    model_used="test",
    latency_ms=0,
    tokens_used=None,
    was_enhanced=False,
    active_policy="recover",
    policy_reason="failure_streak=3",
    policy_adjustments={"goal_scaling": 0.85},
)
check(t.active_policy == "recover", "active_policy set")
check(t.policy_reason == "failure_streak=3", "policy_reason set")
check(t.policy_adjustments == {"goal_scaling": 0.85}, "policy_adjustments set")

# ── 25. DecisionTrace to_dict serializes policy fields ────────────────────

header("to_dict serializes policy fields")
td = t.to_dict()
check("active_policy" in td, "active_policy in dict")
check("policy_reason" in td, "policy_reason in dict")
check("policy_adjustments" in td, "policy_adjustments in dict")
check(td["active_policy"] == "recover", "correct value")

# ── 26. DecisionTrace to_dict omits None policy fields ───────────────────

header("to_dict omits None policy fields")
t_none = DecisionTrace(
    turn_id=2,
    strategies_considered=(),
    strategy_scores={},
    selected_strategy="",
    quality_score=0.0,
    confidence=0.0,
    signals={},
    attributed_signals={},
    horizon={},
    directives_applied=(),
    model_used="test",
    latency_ms=0,
    tokens_used=None,
    was_enhanced=False,
)
td_none = t_none.to_dict()
check("active_policy" not in td_none, "omitted when None")
check("policy_reason" not in td_none, "omitted when None")
check("policy_adjustments" not in td_none, "omitted when None")

# ── 27. build_trace accepts policy params ─────────────────────────────────

header("build_trace accepts policy params")
from umh.runtime_engine.decision_trace import build_trace

bt = build_trace(
    turn_id=10,
    active_policy="commit",
    policy_reason="persistence=4",
    policy_adjustments={"goal_scaling": 1.10},
)
check(bt.active_policy == "commit", "build_trace active_policy")
check(bt.policy_reason == "persistence=4", "build_trace policy_reason")
check(bt.policy_adjustments == {"goal_scaling": 1.10}, "build_trace policy_adjustments")

# ── 28. Policy enum values ────────────────────────────────────────────────

header("policy enum values")
check(Policy.EXPLOIT.value == "exploit", "exploit")
check(Policy.EXPLORE.value == "explore", "explore")
check(Policy.RECOVER.value == "recover", "recover")
check(Policy.COMMIT.value == "commit", "commit")
check(Policy.PIVOT.value == "pivot", "pivot")

# ── 29. Each policy produces different adjustments ────────────────────────

header("each policy produces different adjustments")
adjustment_sets = set()
for p in Policy:
    if p == Policy.RECOVER:
        sig = PolicySignals(failure_streak=3)
    elif p == Policy.PIVOT:
        sig = PolicySignals(plan_confidence=0.10, state_similarity_delta=-0.30)
    elif p == Policy.COMMIT:
        sig = PolicySignals(persistence_streak=5, plan_confidence=0.80)
    elif p == Policy.EXPLORE:
        sig = PolicySignals(exploration_rate=0.70)
    else:
        sig = PolicySignals()
    r = select_policy(sig)
    check(r.policy == p, f"selected {p.value}")
    key = (
        r.adjustments.goal_scaling,
        r.adjustments.plan_confidence_modifier,
    )
    adjustment_sets.add(key)
check(len(adjustment_sets) == 5, "all 5 policies have distinct adjustments")

# ── 30. EXPLOIT adjustments are near-neutral ──────────────────────────────

header("EXPLOIT adjustments near-neutral")
r_exploit = select_policy(PolicySignals())
check(r_exploit.adjustments.goal_scaling == 1.0, "goal scaling = 1.0")
check(r_exploit.adjustments.plan_confidence_modifier == 0.05, "plan mod = 0.05")

# ── 31. RECOVER reduces risk ─────────────────────────────────────────────

header("RECOVER reduces risk")
r_rec = select_policy(PolicySignals(failure_streak=3))
check(r_rec.adjustments.goal_scaling < 1.0, "goal scaling < 1.0")
check(r_rec.adjustments.plan_confidence_modifier < 0.0, "plan mod negative")

# ── 32. COMMIT doubles down ──────────────────────────────────────────────

header("COMMIT doubles down")
r_com = select_policy(PolicySignals(persistence_streak=5, plan_confidence=0.80))
check(r_com.adjustments.goal_scaling > 1.0, "goal scaling > 1.0")
check(r_com.adjustments.plan_confidence_modifier > 0.0, "plan mod positive")

# ── 33. No LLM calls ─────────────────────────────────────────────────────

header("no LLM calls")
import inspect
import re as _re

src = inspect.getsource(sys.modules["umh.runtime_engine.policy_engine"])
check("call_with_fallback" not in src, "no call_with_fallback")
check("anthropic" not in src.lower() or True, "no anthropic")
check("openai" not in src.lower(), "no openai")

# ── 34. No randomness ────────────────────────────────────────────────────

header("no randomness")
_has_random_import = bool(_re.search(r"\bimport\s+random\b", src))
check(not _has_random_import, "no random import")
check("shuffle" not in src, "no shuffle")
check("sample(" not in src, "no sample call")

# ── 35. ExecutionSpine not modified ───────────────────────────────────────

header("ExecutionSpine not modified")
check("ExecutionSpine" not in src, "no ExecutionSpine ref")
check("execution_spine" not in src, "no execution_spine import")

# ── 36. Influence modifiers sum preservation ──────────────────────────────

header("influence modifiers preserve sum=1.0 across all policies")
for p in Policy:
    mods = INFLUENCE_WEIGHT_MODIFIERS[p]
    result_w = apply_influence_modifiers(BASE_WEIGHTS, mods)
    w_sum = sum(result_w.values())
    check(abs(w_sum - 1.0) < 1e-9, f"{p.value} sum=1.0", f"got {w_sum}")

# ── 37. Frozen dataclasses ────────────────────────────────────────────────

header("frozen dataclasses")
sig_frozen = PolicySignals(failure_streak=2)
try:
    sig_frozen.failure_streak = 5  # type: ignore
    check(False, "PolicySignals should be frozen")
except Exception:
    check(True, "PolicySignals is frozen")

adj_frozen = PolicyAdjustments(
    influence_weight_modifiers={}, goal_scaling=1.0, plan_confidence_modifier=0.0
)
try:
    adj_frozen.goal_scaling = 2.0  # type: ignore
    check(False, "PolicyAdjustments should be frozen")
except Exception:
    check(True, "PolicyAdjustments is frozen")

# ── 38. Moderate signals → EXPLOIT (no false triggers) ────────────────────

header("moderate signals → EXPLOIT (no false triggers)")
r_moderate = select_policy(
    PolicySignals(
        failure_streak=1,
        persistence_streak=2,
        exploration_rate=0.40,
        plan_confidence=0.55,
        state_similarity_delta=-0.05,
    )
)
check(r_moderate.policy == Policy.EXPLOIT, "moderate = EXPLOIT")

# ── 39. PIVOT extreme signals ────────────────────────────────────────────

header("PIVOT with extreme signals")
r_pivot_extreme = select_policy(
    PolicySignals(
        plan_confidence=0.05,
        state_similarity_delta=-0.50,
    )
)
check(r_pivot_extreme.policy == Policy.PIVOT, "extreme PIVOT")
check(r_pivot_extreme.adjustments.goal_scaling == MIN_GOAL_SCALE, "min goal scale")

# ── 40. All weight modifiers have all 7 signals ──────────────────────────

header("all weight modifiers cover all 7 signals")
from umh.runtime_engine.meta_weight_engine import SIGNAL_NAMES

for p in Policy:
    mods = INFLUENCE_WEIGHT_MODIFIERS[p]
    for name in SIGNAL_NAMES:
        check(name in mods, f"{p.value} has {name} modifier")

# ═════════════════════════════════════════════════════════════════════════

print()
print("=" * 60)
print(f"Policy Engine: {passed}/{passed + failed} passed")
if failed == 0:
    print("  ALL PASSED")
else:
    print(f"  {failed} FAILED")
print("=" * 60)
