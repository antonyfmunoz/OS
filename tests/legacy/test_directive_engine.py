"""
Tests for DirectiveEngine — deterministic meta-goal generation and evolution.

Covers: constants, directive generation, scoring, selection, evolution,
effects computation, bounded count, stable selection, deduplication,
DecisionTrace integration, determinism, no LLM, no randomness,
no ExecutionSpine, serialization, singleton, snapshot/reset.
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
from umh.runtime_engine.directive_engine import (
    MAX_ACTIVE_DIRECTIVES,
    MAX_HISTORY,
    SCORE_ALPHA,
    DECAY_RATE,
    MIN_CONFIDENCE,
    EVOLUTION_THRESHOLD,
    GOAL_BIAS,
    STRATEGY_BIAS,
    PLAN_BIAS,
    MAX_GOAL_BIAS,
    MAX_STRATEGY_BIAS,
    MAX_PLAN_BIAS,
    DirectiveType,
)

check(MAX_ACTIVE_DIRECTIVES == 3, "max active", f"got {MAX_ACTIVE_DIRECTIVES}")
check(MAX_HISTORY == 20, "max history", f"got {MAX_HISTORY}")
check(SCORE_ALPHA == 0.20, "score alpha", f"got {SCORE_ALPHA}")
check(len(DirectiveType) == 4, "4 types", f"got {len(DirectiveType)}")

# ── 2. All types have bias tables ─────────────────────────────────────────

header("all types have bias tables")
for dt in DirectiveType:
    check(dt in GOAL_BIAS, f"{dt.value} has goal bias")
    check(dt in STRATEGY_BIAS, f"{dt.value} has strategy bias")
    check(dt in PLAN_BIAS, f"{dt.value} has plan bias")

# ── 3. DirectiveType enum values ──────────────────────────────────────────

header("DirectiveType enum values")
check(DirectiveType.EXPLORE.value == "explore", "explore")
check(DirectiveType.EXPLOIT.value == "exploit", "exploit")
check(DirectiveType.RECOVER.value == "recover", "recover")
check(DirectiveType.OPTIMIZE.value == "optimize", "optimize")

# ── 4. Directive dataclass ────────────────────────────────────────────────

header("Directive dataclass")
from umh.runtime_engine.directive_engine import Directive

d = Directive(
    directive_id="test_1",
    directive_type=DirectiveType.EXPLORE,
    priority=0.80,
    confidence=0.70,
    origin="test",
    turn_created=5,
)
check(d.directive_id == "test_1", "id set")
check(d.directive_type == DirectiveType.EXPLORE, "type set")
check(d.priority == 0.80, "priority set")
check(d.confidence == 0.70, "confidence set")
check(d.score == 0.0, "default score 0")

# ── 5. Directive serialization ────────────────────────────────────────────

header("Directive serialization")
dd = d.to_dict()
check("directive_id" in dd, "has id")
check("directive_type" in dd, "has type")
check(dd["directive_type"] == "explore", "type=explore")
check("priority" in dd, "has priority")
check("score" in dd, "has score")

# ── 6. Generate directives — failure trigger ──────────────────────────────

header("generate — failure trigger")
from umh.runtime_engine.directive_engine import generate_directives

cands = generate_directives(
    failure_streak=3,
    exploration_rate=0.0,
    plan_confidence=0.3,
    quality_trend=0.0,
    current_turn=10,
)
recover_cands = [c for c in cands if c.directive_type == DirectiveType.RECOVER]
check(
    len(recover_cands) == 1, "generates RECOVER on failure", f"got {len(recover_cands)}"
)

# ── 7. Generate directives — explore trigger ──────────────────────────────

header("generate — explore trigger")
cands_explore = generate_directives(
    failure_streak=0,
    exploration_rate=0.60,
    plan_confidence=0.3,
    quality_trend=0.0,
    current_turn=10,
)
explore_cands = [c for c in cands_explore if c.directive_type == DirectiveType.EXPLORE]
check(len(explore_cands) == 1, "generates EXPLORE on high rate")

# ── 8. Generate directives — exploit trigger ──────────────────────────────

header("generate — exploit trigger")
cands_exploit = generate_directives(
    failure_streak=0,
    exploration_rate=0.0,
    plan_confidence=0.80,
    quality_trend=0.10,
    current_turn=10,
)
exploit_cands = [c for c in cands_exploit if c.directive_type == DirectiveType.EXPLOIT]
check(len(exploit_cands) == 1, "generates EXPLOIT on high confidence+trend")

# ── 9. Generate directives — optimize trigger ─────────────────────────────

header("generate — optimize trigger")
optimize_cands = [
    c for c in cands_exploit if c.directive_type == DirectiveType.OPTIMIZE
]
check(len(optimize_cands) == 1, "generates OPTIMIZE on positive trend")

# ── 10. Generate — no triggers ────────────────────────────────────────────

header("generate — no triggers")
cands_none = generate_directives(
    failure_streak=0,
    exploration_rate=0.2,
    plan_confidence=0.4,
    quality_trend=-0.1,
    current_turn=10,
)
check(len(cands_none) == 0, "no candidates when no triggers", f"got {len(cands_none)}")

# ── 11. Score directives ──────────────────────────────────────────────────

header("score directives")
from umh.runtime_engine.directive_engine import score_directives

d1 = Directive("d1", DirectiveType.EXPLOIT, 0.80, 0.90, "test", 5)
d2 = Directive("d2", DirectiveType.EXPLORE, 0.70, 0.60, "test", 5)
scores = score_directives(
    [d1, d2], outcome_quality=0.8, influence_score=0.5, current_turn=6
)
check("d1" in scores, "d1 scored")
check("d2" in scores, "d2 scored")
check(scores["d1"] > 0, "d1 score > 0", f"got {scores['d1']}")
check(scores["d1"] > scores["d2"], "higher priority*conf = higher score")

# ── 12. Score with decay ──────────────────────────────────────────────────

header("score with age decay")
d_old = Directive("old", DirectiveType.EXPLOIT, 0.80, 0.90, "test", 0)
d_new = Directive("new", DirectiveType.EXPLOIT, 0.80, 0.90, "test", 9)
s_old = score_directives(
    [d_old], outcome_quality=0.8, influence_score=0.5, current_turn=10
)
s_new = score_directives(
    [d_new], outcome_quality=0.8, influence_score=0.5, current_turn=10
)
check(s_old["old"] < s_new["new"], "older directive decays more")

# ── 13. Select active — bounded by MAX_ACTIVE ────────────────────────────

header("select — bounded by MAX_ACTIVE_DIRECTIVES")
from umh.runtime_engine.directive_engine import DirectiveState, select_active_directives

state = DirectiveState()
many = [
    Directive(f"c{i}", DirectiveType.EXPLORE, 0.5 + i * 0.1, 0.8, "test", 1)
    for i in range(6)
]
scs = {f"c{i}": 0.5 + i * 0.1 for i in range(6)}
select_active_directives(state, many, scs)
check(
    len(state.active) <= MAX_ACTIVE_DIRECTIVES,
    f"active <= {MAX_ACTIVE_DIRECTIVES}",
    f"got {len(state.active)}",
)
check(len(state.history) > 0, "excess go to history")

# ── 14. Select — deterministic tie-break ──────────────────────────────────

header("select — deterministic tie-break")
state2 = DirectiveState()
tied = [
    Directive("b_tie", DirectiveType.EXPLORE, 0.80, 0.90, "test", 1),
    Directive("a_tie", DirectiveType.EXPLOIT, 0.80, 0.90, "test", 1),
]
tied_scores = {"a_tie": 0.72, "b_tie": 0.72}
select_active_directives(state2, tied, tied_scores)
check(
    state2.active[0].directive_id == "a_tie",
    "alphabetical tie-break",
    f"got {state2.active[0].directive_id}",
)

# ── 15. Select — deduplication by type ────────────────────────────────────

header("select — deduplication by type")
state3 = DirectiveState()
state3.active = [
    Directive("old_explore", DirectiveType.EXPLORE, 0.60, 0.70, "old", 1, score=0.30),
]
new_explore = Directive("new_explore", DirectiveType.EXPLORE, 0.80, 0.90, "new", 5)
dedup_scores = {"old_explore": 0.30}
select_active_directives(state3, [new_explore], dedup_scores)
explore_active = [d for d in state3.active if d.directive_type == DirectiveType.EXPLORE]
check(len(explore_active) <= 1, "at most one per type")

# ── 16. Evolve — decay low-scoring directives ────────────────────────────

header("evolve — decay low-scoring")
from umh.runtime_engine.directive_engine import evolve_directives

state4 = DirectiveState()
d_low = Directive("low", DirectiveType.EXPLORE, 0.50, 0.50, "test", 1, score=0.10)
state4.active = [d_low]
events = evolve_directives(state4, outcome_quality=0.3, current_turn=5)
check(len(events) > 0, "decay event generated")
check(d_low.confidence < 0.50, "confidence decreased", f"got {d_low.confidence}")

# ── 17. Evolve — expire below MIN_CONFIDENCE ─────────────────────────────

header("evolve — expire below MIN_CONFIDENCE")
state5 = DirectiveState()
d_dying = Directive("dying", DirectiveType.RECOVER, 0.50, 0.04, "test", 1, score=0.05)
state5.active = [d_dying]
events5 = evolve_directives(state5, outcome_quality=0.2, current_turn=5)
check(len(state5.active) == 0, "expired directive removed")
check(any("expired" in e for e in events5), "expired event recorded")

# ── 18. Evolve — healthy directives survive ───────────────────────────────

header("evolve — healthy directives survive")
state6 = DirectiveState()
d_healthy = Directive(
    "healthy", DirectiveType.EXPLOIT, 0.80, 0.90, "test", 3, score=0.60
)
state6.active = [d_healthy]
events6 = evolve_directives(state6, outcome_quality=0.8, current_turn=5)
check(len(state6.active) == 1, "healthy survives")
check(d_healthy.confidence == 0.90, "confidence unchanged")

# ── 19. Compute effects — single directive ────────────────────────────────

header("compute effects — single directive")
from umh.runtime_engine.directive_engine import compute_directive_effects

d_eff = Directive("e1", DirectiveType.EXPLORE, 0.80, 1.0, "test", 1)
effects = compute_directive_effects([d_eff])
check(
    effects.goal_bias != 0.0 or GOAL_BIAS[DirectiveType.EXPLORE] == 0.0,
    "goal bias applied",
)
check(effects.strategy_bias != 0.0, "strategy bias applied")
check(effects.plan_bias != 0.0, "plan bias applied")

# ── 20. Compute effects — empty → NO_EFFECTS ─────────────────────────────

header("compute effects — empty")
from umh.runtime_engine.directive_engine import NO_EFFECTS

effects_empty = compute_directive_effects([])
check(effects_empty.goal_bias == 0.0, "goal=0")
check(effects_empty.strategy_bias == 0.0, "strategy=0")
check(effects_empty.plan_bias == 0.0, "plan=0")
check(effects_empty is NO_EFFECTS, "returns NO_EFFECTS singleton")

# ── 21. Compute effects — bounded ────────────────────────────────────────

header("compute effects — bounded")
many_exploit = [
    Directive(f"ex{i}", DirectiveType.EXPLOIT, 0.90, 1.0, "test", 1) for i in range(5)
]
effects_many = compute_directive_effects(many_exploit)
check(
    -MAX_GOAL_BIAS <= effects_many.goal_bias <= MAX_GOAL_BIAS,
    "goal bias bounded",
    f"got {effects_many.goal_bias}",
)
check(
    -MAX_STRATEGY_BIAS <= effects_many.strategy_bias <= MAX_STRATEGY_BIAS,
    "strategy bias bounded",
)
check(
    -MAX_PLAN_BIAS <= effects_many.plan_bias <= MAX_PLAN_BIAS,
    "plan bias bounded",
)

# ── 22. DirectiveEffects serialization ────────────────────────────────────

header("DirectiveEffects serialization")
from umh.runtime_engine.directive_engine import DirectiveEffects

eff = DirectiveEffects(goal_bias=0.03, strategy_bias=-0.02, plan_bias=0.01)
ed = eff.to_dict()
check("goal_bias" in ed, "has goal_bias")
check("strategy_bias" in ed, "has strategy_bias")
check("plan_bias" in ed, "has plan_bias")

# ── 23. DirectiveSnapshot serialization ───────────────────────────────────

header("DirectiveSnapshot serialization")
from umh.runtime_engine.directive_engine import DirectiveSnapshot

snap = DirectiveSnapshot(
    active=({"id": "a"},),
    scores={"a": 0.5},
    selection_reason="test",
    evolution_events=("decay:a",),
    effects=eff,
)
sd = snap.to_dict()
check("active" in sd, "has active")
check("scores" in sd, "has scores")
check("selection_reason" in sd, "has reason")
check("evolution_events" in sd, "has events")
check("effects" in sd, "has effects")

# ── 24. DirectiveEngine.process_turn ──────────────────────────────────────

header("DirectiveEngine.process_turn full cycle")
from umh.runtime_engine.directive_engine import DirectiveEngine

engine = DirectiveEngine()
snap1 = engine.process_turn(
    failure_streak=3,
    exploration_rate=0.0,
    plan_confidence=0.3,
    quality_trend=0.0,
    outcome_quality=0.5,
    influence_score=0.4,
    current_turn=1,
)
check(len(snap1.active) > 0, "directives generated")
check(snap1.selection_reason != "no_directives", "has reason")
check(engine.active_count <= MAX_ACTIVE_DIRECTIVES, "bounded count")

# ── 25. Process multiple turns — stability ────────────────────────────────

header("process multiple turns — no oscillation")
engine2 = DirectiveEngine()
snapshots = []
for t in range(10):
    s = engine2.process_turn(
        failure_streak=0,
        exploration_rate=0.55,
        plan_confidence=0.60,
        quality_trend=0.05,
        outcome_quality=0.7,
        influence_score=0.5,
        current_turn=t,
    )
    snapshots.append(s)
    check(
        len(s.active) <= MAX_ACTIVE_DIRECTIVES,
        f"turn {t}: bounded",
        f"got {len(s.active)}",
    )

types_per_turn = [set(d["directive_type"] for d in s.active) for s in snapshots]
# After initial stabilization (turn 2+), types shouldn't flip every turn
stable_count = 0
for i in range(2, len(types_per_turn)):
    if types_per_turn[i] == types_per_turn[i - 1]:
        stable_count += 1
check(stable_count >= 3, "stable across majority of turns", f"stable={stable_count}/7")

# ── 26. Singleton accessor ────────────────────────────────────────────────

header("singleton accessor")
from umh.runtime_engine.directive_engine import get_directive_engine

ea = get_directive_engine()
eb = get_directive_engine()
check(ea is eb, "singleton returns same instance")

# ── 27. Reset ─────────────────────────────────────────────────────────────

header("reset clears state")
engine3 = DirectiveEngine()
engine3.process_turn(failure_streak=3, current_turn=1)
check(engine3.active_count > 0, "has directives before reset")
engine3.reset()
check(engine3.active_count == 0, "0 after reset")

# ── 28. Snapshot ──────────────────────────────────────────────────────────

header("engine snapshot")
engine4 = DirectiveEngine()
engine4.process_turn(failure_streak=2, current_turn=1)
snap_data = engine4.snapshot()
check("active" in snap_data, "has active")
check("history_count" in snap_data, "has history_count")

# ── 29. History bounded ───────────────────────────────────────────────────

header("history bounded by MAX_HISTORY")
engine5 = DirectiveEngine()
for t in range(50):
    engine5.process_turn(
        failure_streak=3,
        exploration_rate=0.60,
        plan_confidence=0.80,
        quality_trend=0.10,
        outcome_quality=0.5,
        influence_score=0.3,
        current_turn=t,
    )
check(
    len(engine5.state.history) <= MAX_HISTORY,
    f"history <= {MAX_HISTORY}",
    f"got {len(engine5.state.history)}",
)

# ── 30. Determinism ───────────────────────────────────────────────────────

header("determinism — same inputs → same output")
ea1 = DirectiveEngine()
ea2 = DirectiveEngine()
for t in range(5):
    s1 = ea1.process_turn(
        failure_streak=2,
        exploration_rate=0.55,
        plan_confidence=0.60,
        quality_trend=0.05,
        outcome_quality=0.6,
        influence_score=0.4,
        current_turn=t,
    )
    s2 = ea2.process_turn(
        failure_streak=2,
        exploration_rate=0.55,
        plan_confidence=0.60,
        quality_trend=0.05,
        outcome_quality=0.6,
        influence_score=0.4,
        current_turn=t,
    )
check(s1.selection_reason == s2.selection_reason, "same reason")
check(len(s1.active) == len(s2.active), "same active count")
types1 = [d["directive_type"] for d in s1.active]
types2 = [d["directive_type"] for d in s2.active]
check(types1 == types2, "same types")

# ── 31. NO_SNAPSHOT sentinel ──────────────────────────────────────────────

header("NO_SNAPSHOT sentinel")
from umh.runtime_engine.directive_engine import NO_SNAPSHOT

check(len(NO_SNAPSHOT.active) == 0, "no active")
check(NO_SNAPSHOT.selection_reason == "no_directives", "no_directives")

# ── 32. DecisionTrace directive fields ────────────────────────────────────

header("DecisionTrace directive fields")
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
    active_directives=({"id": "d1", "type": "recover"},),
    directive_scores={"d1": 0.65},
    directive_selection_reason="top_1:recover",
    directive_evolution_events=("decay:d1",),
)
check(t.active_directives is not None, "active_directives set")
check(t.directive_scores is not None, "directive_scores set")
check(t.directive_selection_reason is not None, "selection_reason set")
check(t.directive_evolution_events is not None, "evolution_events set")

# ── 33. to_dict serializes directive fields ───────────────────────────────

header("to_dict serializes directive fields")
td = t.to_dict()
check("active_directives" in td, "active_directives in dict")
check("directive_scores" in td, "directive_scores in dict")
check("directive_selection_reason" in td, "selection_reason in dict")
check("directive_evolution_events" in td, "evolution_events in dict")

# ── 34. to_dict omits None directive fields ───────────────────────────────

header("to_dict omits None directive fields")
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
check("active_directives" not in td_none, "omitted when None")
check("directive_scores" not in td_none, "omitted when None")
check("directive_selection_reason" not in td_none, "omitted when None")
check("directive_evolution_events" not in td_none, "omitted when None")

# ── 35. build_trace accepts directive params ──────────────────────────────

header("build_trace accepts directive params")
from umh.runtime_engine.decision_trace import build_trace

bt = build_trace(
    turn_id=10,
    active_directives=({"id": "x"},),
    directive_scores={"x": 0.5},
    directive_selection_reason="top_1:explore",
    directive_evolution_events=("expired:old",),
)
check(bt.active_directives == ({"id": "x"},), "build_trace active_directives")
check(bt.directive_scores == {"x": 0.5}, "build_trace directive_scores")
check(bt.directive_selection_reason == "top_1:explore", "build_trace reason")
check(bt.directive_evolution_events == ("expired:old",), "build_trace events")

# ── 36. No LLM calls ─────────────────────────────────────────────────────

header("no LLM calls")
import inspect
import re as _re

src = inspect.getsource(sys.modules["umh.runtime_engine.directive_engine"])
check("call_with_fallback" not in src, "no call_with_fallback")
check("openai" not in src.lower(), "no openai")

# ── 37. No randomness ────────────────────────────────────────────────────

header("no randomness")
_has_random = bool(_re.search(r"\bimport\s+random\b", src))
check(not _has_random, "no random import")
check("shuffle" not in src, "no shuffle")
check("sample(" not in src, "no sample call")

# ── 38. ExecutionSpine not modified ───────────────────────────────────────

header("ExecutionSpine not modified")
check("ExecutionSpine" not in src, "no ExecutionSpine ref")
check("execution_spine" not in src, "no execution_spine import")

# ── 39. DirectiveState ────────────────────────────────────────────────────

header("DirectiveState")
ds = DirectiveState()
check(ds.active_count == 0, "initial count 0")
dsd = ds.to_dict()
check("active" in dsd, "has active in dict")
check("history_count" in dsd, "has history_count in dict")

# ── 40. Multiple types generated simultaneously ──────────────────────────

header("multiple types generated simultaneously")
cands_multi = generate_directives(
    failure_streak=3,
    exploration_rate=0.60,
    plan_confidence=0.80,
    quality_trend=0.15,
    current_turn=20,
)
types_gen = {c.directive_type for c in cands_multi}
check(DirectiveType.RECOVER in types_gen, "RECOVER generated")
check(DirectiveType.EXPLORE in types_gen, "EXPLORE generated")
check(DirectiveType.EXPLOIT in types_gen, "EXPLOIT generated")
check(DirectiveType.OPTIMIZE in types_gen, "OPTIMIZE generated")
check(len(cands_multi) == 4, "all 4 types", f"got {len(cands_multi)}")

# ── 41. Confidence scaling in effects ─────────────────────────────────────

header("confidence scaling in effects")
d_full = Directive("full", DirectiveType.EXPLORE, 0.80, 1.0, "test", 1)
d_half = Directive("half", DirectiveType.EXPLORE, 0.80, 0.5, "test", 1)
eff_full = compute_directive_effects([d_full])
eff_half = compute_directive_effects([d_half])
check(
    abs(eff_full.strategy_bias) > abs(eff_half.strategy_bias),
    "higher confidence = stronger effect",
)

# ── 42. Score EMA accumulation ────────────────────────────────────────────

header("score EMA accumulation")
d_ema = Directive("ema", DirectiveType.EXPLOIT, 0.80, 0.90, "test", 1, score=0.50)
score_directives([d_ema], outcome_quality=0.9, influence_score=0.8, current_turn=2)
check(d_ema.score != 0.50, "score updated via EMA", f"got {d_ema.score}")

# ═════════════════════════════════════════════════════════════════════════

print()
print("=" * 60)
print(f"Directive Engine: {passed}/{passed + failed} passed")
if failed == 0:
    print("  ALL PASSED")
else:
    print(f"  {failed} FAILED")
print("=" * 60)
