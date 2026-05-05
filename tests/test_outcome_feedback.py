"""
Tests for the Outcome Feedback Layer (Task 10).

Validates:
    - Outcome model creation and serialization
    - Outcome modifies StrategyMemory correctly
    - Outcome modifies DirectiveMemory correctly
    - Outcome modifies GoalTracker correctly
    - Delayed outcomes update correct turn (not current)
    - Determinism: same outcomes → same memory state
    - Confidence gating: below-floor outcomes are ignored
    - Blend formula correctness
    - OutcomeStore ordering and bounded size
    - DecisionTrace outcome_attached and outcome_score
    - SessionRuntime.record_outcome() integration
    - Source types all valid
    - No LLM calls in any outcome module
    - ExecutionSpine unchanged
    - No regression in existing memory tests
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


def _reset_memories():
    """Reset all memory singletons for test isolation."""
    from umh.strategy.memory import reset_strategy_memory

    reset_strategy_memory()

    from umh.runtime_engine.directive_memory import reset_directive_memory

    reset_directive_memory()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Imports
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. Imports")

from umh.runtime_engine.outcome_feedback import (
    Outcome,
    OutcomeSource,
    OutcomeStore,
    NO_OUTCOME,
    compute_outcome_adjusted_score,
    apply_outcome_to_strategy_memory,
    apply_outcome_to_directive_memory,
    apply_outcome_to_goal_tracker,
    OUTCOME_CONFIDENCE_FLOOR,
    MAX_PENDING_OUTCOMES,
)
from umh.strategy.memory import StrategyMemory, StrategyStats, get_strategy_memory, reset_strategy_memory
from umh.runtime_engine.directive_memory import DirectiveMemory, get_directive_memory, reset_directive_memory
from umh.goals.state import GoalState, GoalTracker, GoalRegistry
from umh.runtime_engine.decision_trace import DecisionTrace, build_trace
from umh.runtime_engine.session_runtime import SessionRuntime

_test("outcome_feedback imports", True)
_test("strategy_memory imports", True)
_test("directive_memory imports", True)
_test("goal_state imports", True)
_test("decision_trace imports", True)
_test("session_runtime imports", True)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Outcome Model
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. Outcome Model")

oc = Outcome(
    turn_id=5,
    success=0.9,
    source=OutcomeSource.USER_FEEDBACK,
    confidence=0.8,
)
_test("outcome created", oc.turn_id == 5)
_test("success preserved", oc.success == 0.9)
_test("source is USER_FEEDBACK", oc.source == OutcomeSource.USER_FEEDBACK)
_test("confidence preserved", oc.confidence == 0.8)
_test("outcome_id generated", len(oc.outcome_id) == 12)
_test("timestamp generated", oc.timestamp > 0)

d = oc.to_dict()
_test("to_dict has outcome_id", "outcome_id" in d)
_test("to_dict source is string", d["source"] == "user_feedback")
_test("to_dict success rounded", d["success"] == 0.9)

# Frozen
try:
    oc.success = 0.5
    _test("outcome is frozen", False, "should have raised")
except AttributeError:
    _test("outcome is frozen", True)

# NO_OUTCOME sentinel
_test("NO_OUTCOME turn_id is -1", NO_OUTCOME.turn_id == -1)
_test("NO_OUTCOME confidence is 0", NO_OUTCOME.confidence == 0.0)

# All source types
for src in OutcomeSource:
    _test(f"source {src.value} valid", isinstance(src.value, str))


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Blend Formula
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Blend Formula")

# Full confidence → outcome dominates
adj = compute_outcome_adjusted_score(0.5, 1.0, 1.0)
_test("full confidence → outcome", abs(adj - 1.0) < 0.001, f"got {adj}")

# Zero confidence → internal dominates
adj = compute_outcome_adjusted_score(0.5, 1.0, 0.0)
_test("zero confidence → internal", abs(adj - 0.5) < 0.001, f"got {adj}")

# Half confidence → midpoint
adj = compute_outcome_adjusted_score(0.4, 0.8, 0.5)
expected = 0.4 * 0.5 + 0.8 * 0.5
_test("half confidence → blend", abs(adj - expected) < 0.001, f"got {adj}")

# Clamped to [0, 1]
adj = compute_outcome_adjusted_score(0.0, 1.5, 1.0)
_test("clamped to 1.0", adj == 1.0, f"got {adj}")

adj = compute_outcome_adjusted_score(0.0, -0.5, 1.0)
_test("clamped to 0.0", adj == 0.0, f"got {adj}")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. OutcomeStore
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. OutcomeStore")

store = OutcomeStore()
_test("empty store total is 0", store.total_outcomes == 0)

store.record(Outcome(turn_id=1, success=0.8, source=OutcomeSource.USER_FEEDBACK))
store.record(Outcome(turn_id=1, success=0.9, source=OutcomeSource.SYSTEM_EVAL))
store.record(Outcome(turn_id=3, success=0.5, source=OutcomeSource.EXTERNAL_API))

_test("store has 3 outcomes", store.total_outcomes == 3)
_test("turns_with_outcomes", store.turns_with_outcomes == {1, 3})
_test("get_for_turn(1) has 2", len(store.get_for_turn(1)) == 2)
_test("get_for_turn(3) has 1", len(store.get_for_turn(3)) == 1)
_test("get_for_turn(999) empty", store.get_for_turn(999) == [])

latest = store.get_latest_for_turn(1)
_test("latest for turn 1 is second", latest.success == 0.9)

# Confidence floor — below-floor outcomes should be skipped
store2 = OutcomeStore()
store2.record(Outcome(turn_id=1, success=0.9, source=OutcomeSource.USER_FEEDBACK, confidence=0.05))
_test(
    "below confidence floor skipped",
    store2.total_outcomes == 0,
    f"got {store2.total_outcomes}",
)

# Bounded size
store3 = OutcomeStore()
for i in range(MAX_PENDING_OUTCOMES + 10):
    store3.record(Outcome(turn_id=i, success=0.5, source=OutcomeSource.SYSTEM_EVAL))
_test(
    f"bounded at MAX_PENDING_OUTCOMES={MAX_PENDING_OUTCOMES}",
    store3.total_outcomes == MAX_PENDING_OUTCOMES,
    f"got {store3.total_outcomes}",
)

# Serialization
sd = store.to_dict()
_test("to_dict has total", sd["total"] == 3)
_test("to_dict has turns_covered", sd["turns_covered"] == [1, 3])
_test("to_dict has outcomes list", len(sd["outcomes"]) == 3)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Outcome → StrategyMemory
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Outcome → StrategyMemory")
_reset_memories()

sm = StrategyMemory()
sm.record_win("clarity", 0.7)
sm.record_win("clarity", 0.6)
sm.record_win("clarity", 0.65)

ema_before = sm.get_stats("clarity").ema_score

oc_good = Outcome(turn_id=1, success=0.95, source=OutcomeSource.USER_FEEDBACK, confidence=0.8)
adj = compute_outcome_adjusted_score(0.65, 0.95, 0.8)

sm.apply_outcome("clarity", adj, 0.8)

ema_after = sm.get_stats("clarity").ema_score
_test(
    "outcome shifted EMA upward",
    ema_after > ema_before,
    f"before={ema_before:.4f}, after={ema_after:.4f}",
)
_test(
    "uses unchanged by outcome",
    sm.get_stats("clarity").uses == 3,
    f"got {sm.get_stats('clarity').uses}",
)
_test(
    "wins unchanged by outcome",
    sm.get_stats("clarity").wins == 3,
    f"got {sm.get_stats('clarity').wins}",
)

# Negative outcome shifts down
_reset_memories()
sm2 = StrategyMemory()
sm2.record_win("baseline", 0.8)
sm2.record_win("baseline", 0.85)
ema_before2 = sm2.get_stats("baseline").ema_score

adj_bad = compute_outcome_adjusted_score(0.85, 0.2, 0.9)
sm2.apply_outcome("baseline", adj_bad, 0.9)
ema_after2 = sm2.get_stats("baseline").ema_score
_test(
    "negative outcome shifts EMA down",
    ema_after2 < ema_before2,
    f"before={ema_before2:.4f}, after={ema_after2:.4f}",
)

# No-op on unknown strategy
sm2.apply_outcome("nonexistent", 0.9, 0.8)
_test("unknown strategy is no-op", sm2.get_stats("nonexistent") is None)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Outcome → DirectiveMemory
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. Outcome → DirectiveMemory")
_reset_memories()

dm = DirectiveMemory()
dm.record_win("concise", 0.7)
dm.record_win("concise", 0.6)

ema_before_d = dm.get_stats("concise").ema_score

dm.apply_outcome("concise", 0.95, 0.8)
ema_after_d = dm.get_stats("concise").ema_score

_test(
    "directive outcome shifted EMA",
    ema_after_d > ema_before_d,
    f"before={ema_before_d:.4f}, after={ema_after_d:.4f}",
)
_test(
    "directive uses unchanged",
    dm.get_stats("concise").uses == 2,
)

# No-op on unknown directive
dm.apply_outcome("unknown_dir", 0.9, 0.8)
_test("unknown directive is no-op", dm.get_stats("unknown_dir") is None)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Outcome → GoalTracker
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Outcome → GoalTracker")

tracker = GoalTracker(goal_id="sales")
tracker.update_success(0.6)
tracker.update_success(0.65)

score_before = tracker.success_score

tracker.apply_outcome(0.95, 0.8)
score_after = tracker.success_score

_test(
    "goal tracker outcome shifted score",
    score_after > score_before,
    f"before={score_before:.4f}, after={score_after:.4f}",
)
_test(
    "goal tracker uses unchanged",
    tracker.uses == 2,
    f"got {tracker.uses}",
)

# No-op on zero uses
tracker_empty = GoalTracker(goal_id="empty")
tracker_empty.apply_outcome(0.9, 0.8)
_test("zero-uses tracker is no-op", tracker_empty.success_score == 0.5)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Delayed Outcome — Updates Correct Turn
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Delayed Outcome — Correct Turn")
_reset_memories()

from unittest.mock import MagicMock

mock_ctx = MagicMock()
session = SessionRuntime(mock_ctx, session_id="delay-test")

# Manually create traces for turns 1, 2, 3
for turn in [1, 2, 3]:
    trace = build_trace(
        turn_id=turn,
        evaluation={"quality_score": 0.7, "confidence": 0.8},
    )
    session.stats.decision_traces.append(trace)

# Populate strategy memory so apply_outcome has something to adjust
sm_delay = get_strategy_memory()

# Build a trace with a known strategy for turn 2
from umh.strategy.memory import reset_strategy_memory
reset_strategy_memory()
sm_delay = StrategyMemory()
sm_delay.record_win("clarity", 0.7)
sm_delay.record_win("clarity", 0.75)
ema_before_delay = sm_delay.get_stats("clarity").ema_score

# Rebuild traces with specific strategy info
session.stats.decision_traces = []
for turn in [1, 2, 3]:
    strat = "clarity" if turn == 2 else "baseline"
    trace = DecisionTrace(
        turn_id=turn,
        strategies_considered=("clarity", "baseline"),
        strategy_scores={"clarity": 0.7, "baseline": 0.5},
        selected_strategy=strat,
        quality_score=0.7,
        confidence=0.8,
        signals={},
        attributed_signals={},
        horizon={},
        directives_applied=(),
        model_used="test",
        latency_ms=100,
        tokens_used=None,
        was_enhanced=False,
        active_goal_id="sales" if turn == 2 else None,
        goal_score=0.6 if turn == 2 else None,
    )
    session.stats.decision_traces.append(trace)

# Set up goal registry for the session
reg = GoalRegistry()
reg.add_goal(GoalState(goal_id="sales", description="close", priority=0.9))
reg.get_tracker("sales").update_success(0.6)
session._goal_registry = reg

# Delayed outcome for turn 2 arriving at turn 3
delayed_oc = Outcome(
    turn_id=2,
    success=0.95,
    source=OutcomeSource.USER_FEEDBACK,
    confidence=0.85,
)
result = session.record_outcome(delayed_oc)

_test("delayed outcome applied", result is True)

store = session.get_outcome_store()
_test("outcome store has 1 entry", store.total_outcomes == 1)
_test("outcome linked to turn 2", 2 in store.turns_with_outcomes)

# Outcome for non-existent turn
result_bad = session.record_outcome(
    Outcome(turn_id=999, success=0.5, source=OutcomeSource.SYSTEM_EVAL)
)
_test("non-existent turn returns False", result_bad is False)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Determinism
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Determinism")
_reset_memories()

# Apply identical sequences twice, compare results
def _run_sequence():
    sm = StrategyMemory()
    sm.record_win("a", 0.7)
    sm.record_win("a", 0.8)
    sm.record_win("b", 0.5)

    adj_a = compute_outcome_adjusted_score(0.8, 0.95, 0.7)
    sm.apply_outcome("a", adj_a, 0.7)

    adj_b = compute_outcome_adjusted_score(0.5, 0.3, 0.6)
    sm.apply_outcome("b", adj_b, 0.6)

    return sm.to_dict()

reset_strategy_memory()
result_1 = _run_sequence()

reset_strategy_memory()
result_2 = _run_sequence()

_test("deterministic: same outcomes → same state", result_1 == result_2)

# Verify ordering matters
reset_strategy_memory()
sm_ord = StrategyMemory()
sm_ord.record_win("x", 0.7)
sm_ord.record_win("x", 0.8)

sm_ord.apply_outcome("x", 0.9, 0.8)
sm_ord.apply_outcome("x", 0.3, 0.8)
state_ab = sm_ord.get_stats("x").ema_score

reset_strategy_memory()
sm_ord2 = StrategyMemory()
sm_ord2.record_win("x", 0.7)
sm_ord2.record_win("x", 0.8)

sm_ord2.apply_outcome("x", 0.3, 0.8)
sm_ord2.apply_outcome("x", 0.9, 0.8)
state_ba = sm_ord2.get_stats("x").ema_score

_test(
    "order matters (not commutative)",
    abs(state_ab - state_ba) > 0.001,
    f"ab={state_ab:.4f}, ba={state_ba:.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. DecisionTrace — outcome_attached and outcome_score
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. DecisionTrace Outcome Fields")

trace_oc = build_trace(
    turn_id=1,
    outcome_attached=True,
    outcome_score=0.92,
)
_test("outcome_attached set", trace_oc.outcome_attached is True)
_test("outcome_score set", trace_oc.outcome_score == 0.92)

d = trace_oc.to_dict()
_test("outcome_attached in dict", d.get("outcome_attached") is True)
_test("outcome_score in dict", d.get("outcome_score") == 0.92)

trace_no = build_trace(turn_id=2)
_test("outcome_attached None by default", trace_no.outcome_attached is None)
_test("outcome_score None by default", trace_no.outcome_score is None)

d_no = trace_no.to_dict()
_test("outcome_attached absent when None", "outcome_attached" not in d_no)
_test("outcome_score absent when None", "outcome_score" not in d_no)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. apply_outcome helpers (module-level functions)
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. Module-Level Apply Functions")
_reset_memories()

# Strategy
sm_g = get_strategy_memory()
sm_g.record_win("clarity", 0.7)
oc_s = Outcome(turn_id=1, success=0.95, source=OutcomeSource.USER_FEEDBACK, confidence=0.8)
adj_s = apply_outcome_to_strategy_memory("clarity", 0.7, oc_s)
_test("apply_to_strategy returns adjusted", adj_s > 0.7, f"got {adj_s:.4f}")

# Directive
dm_g = get_directive_memory()
dm_g.record_win("clarity", 0.7)
adj_d = apply_outcome_to_directive_memory("clarity", 0.7, oc_s)
_test("apply_to_directive returns adjusted", adj_d > 0.7, f"got {adj_d:.4f}")

# Goal tracker
reg_g = GoalRegistry()
reg_g.add_goal(GoalState(goal_id="g1", description="test", priority=0.8))
reg_g.get_tracker("g1").update_success(0.6)
adj_gt = apply_outcome_to_goal_tracker("g1", 0.6, oc_s, reg_g)
_test("apply_to_goal returns adjusted", adj_gt > 0.6, f"got {adj_gt:.4f}")

score_after_g = reg_g.get_tracker("g1").success_score
_test(
    "goal tracker modified",
    abs(score_after_g - 0.6) > 0.001,
    f"got {score_after_g:.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. SessionRuntime Integration — Full Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. SessionRuntime — Full Pipeline")
_reset_memories()

session2 = SessionRuntime(MagicMock(), session_id="full-pipeline")

# Set up a goal registry
session2.set_goals([
    GoalState(goal_id="close", description="close sale", priority=0.9),
])

# Simulate turns with traces
for turn in range(1, 4):
    trace = DecisionTrace(
        turn_id=turn,
        strategies_considered=("clarity", "baseline"),
        strategy_scores={"clarity": 0.7},
        selected_strategy="clarity",
        quality_score=0.72,
        confidence=0.85,
        signals={},
        attributed_signals={},
        horizon={},
        directives_applied=("clarity",),
        model_used="test",
        latency_ms=50,
        tokens_used=None,
        was_enhanced=False,
        active_goal_id="close",
        goal_score=0.65,
    )
    session2.stats.decision_traces.append(trace)

# Seed strategy and directive memory
sm_full = get_strategy_memory()
sm_full.record_win("clarity", 0.72)
dm_full = get_directive_memory()
dm_full.record_win("clarity", 0.72)

# Record goal tracker data
reg_full = session2.get_goal_registry()
reg_full.get_tracker("close").update_success(0.65)

ema_strat_before = sm_full.get_stats("clarity").ema_score
ema_dir_before = dm_full.get_stats("clarity").ema_score
goal_before = reg_full.get_tracker("close").success_score

# Apply positive outcome
good_outcome = Outcome(
    turn_id=2,
    success=0.95,
    source=OutcomeSource.USER_FEEDBACK,
    confidence=0.85,
)
applied = session2.record_outcome(good_outcome)

_test("full pipeline outcome applied", applied is True)

ema_strat_after = sm_full.get_stats("clarity").ema_score
ema_dir_after = dm_full.get_stats("clarity").ema_score
goal_after = reg_full.get_tracker("close").success_score

_test(
    "strategy EMA shifted by outcome",
    abs(ema_strat_after - ema_strat_before) > 0.001,
    f"before={ema_strat_before:.4f}, after={ema_strat_after:.4f}",
)
_test(
    "directive EMA shifted by outcome",
    abs(ema_dir_after - ema_dir_before) > 0.001,
    f"before={ema_dir_before:.4f}, after={ema_dir_after:.4f}",
)
_test(
    "goal tracker shifted by outcome",
    abs(goal_after - goal_before) > 0.001,
    f"before={goal_before:.4f}, after={goal_after:.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. SessionRuntime — get_outcome_store API
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. SessionRuntime — get_outcome_store")

store_api = session2.get_outcome_store()
_test("store accessible", store_api is not None)
_test("store has outcomes", store_api.total_outcomes > 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. No LLM Calls
# ═══════════════════════════════════════════════════════════════════════════════

_section("14. No LLM Calls")

import umh.runtime_engine.outcome_feedback as of_mod

src = open(of_mod.__file__).read()
_test("no call_with_fallback", "call_with_fallback" not in src)
_test("no model_router", "model_router" not in src)
_test("no agent_runtime", "agent_runtime" not in src)
_test("no GenerativeModel", "GenerativeModel" not in src)


# ═══════════════════════════════════════════════════════════════════════════════
# 15. ExecutionSpine Unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("15. ExecutionSpine Unchanged")

src_spine = open("/opt/OS/eos/execution_spine.py").read()
_test("spine has no outcome import", "outcome_feedback" not in src_spine)
_test("spine has no apply_outcome", "apply_outcome" not in src_spine)


# ═══════════════════════════════════════════════════════════════════════════════
# 16. Confidence Gating
# ═══════════════════════════════════════════════════════════════════════════════

_section("16. Confidence Gating")
_reset_memories()

sm_cg = StrategyMemory()
sm_cg.record_win("test", 0.7)
ema_cg_before = sm_cg.get_stats("test").ema_score

# Low confidence outcome has minimal effect because blend = min(conf, EMA_ALPHA)
sm_cg.apply_outcome("test", 0.95, 0.05)
ema_cg_after = sm_cg.get_stats("test").ema_score

_test(
    "low confidence has small effect",
    abs(ema_cg_after - ema_cg_before) < 0.05,
    f"delta={abs(ema_cg_after - ema_cg_before):.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 17. Multiple Outcomes Same Turn
# ═══════════════════════════════════════════════════════════════════════════════

_section("17. Multiple Outcomes Same Turn")
_reset_memories()

sm_multi = StrategyMemory()
sm_multi.record_win("x", 0.5)
sm_multi.record_win("x", 0.6)

ema_m0 = sm_multi.get_stats("x").ema_score

sm_multi.apply_outcome("x", 0.9, 0.3)
ema_m1 = sm_multi.get_stats("x").ema_score

sm_multi.apply_outcome("x", 0.95, 0.3)
ema_m2 = sm_multi.get_stats("x").ema_score

_test("first outcome shifts up", ema_m1 > ema_m0, f"{ema_m0:.4f} → {ema_m1:.4f}")
_test("second outcome shifts further", ema_m2 > ema_m1, f"{ema_m1:.4f} → {ema_m2:.4f}")


# ═══════════════════════════════════════════════════════════════════════════════
# 18. OutcomeStore Insertion Order
# ═══════════════════════════════════════════════════════════════════════════════

_section("18. OutcomeStore Insertion Order")

store_order = OutcomeStore()
store_order.record(Outcome(turn_id=3, success=0.3, source=OutcomeSource.SYSTEM_EVAL, outcome_id="aaa"))
store_order.record(Outcome(turn_id=1, success=0.1, source=OutcomeSource.USER_FEEDBACK, outcome_id="bbb"))
store_order.record(Outcome(turn_id=2, success=0.2, source=OutcomeSource.EXTERNAL_API, outcome_id="ccc"))

all_oc = store_order.all_outcomes()
_test("insertion order: first", all_oc[0].outcome_id == "aaa")
_test("insertion order: second", all_oc[1].outcome_id == "bbb")
_test("insertion order: third", all_oc[2].outcome_id == "ccc")


# ═══════════════════════════════════════════════════════════════════════════════
# 19. No Regression — Strategy/Directive Memory Still Works
# ═══════════════════════════════════════════════════════════════════════════════

_section("19. No Regression — Existing Memory")
_reset_memories()

sm_nr = StrategyMemory()
sm_nr.record_win("clarity", 0.85)
sm_nr.record_loss("baseline", 0.5)
ranked = sm_nr.rank_strategies()
_test("record_win still works", sm_nr.get_stats("clarity").uses == 1)
_test("record_loss still works", sm_nr.get_stats("baseline").uses == 1)
_test("rank_strategies still works", len(ranked) >= 2)
_test("clarity ranks above baseline", ranked[0][0] == "clarity")

dm_nr = DirectiveMemory()
dm_nr.record_win("structured", 0.9)
dm_nr.record_loss("concise", 0.4)
_test("directive record_win works", dm_nr.get_stats("structured").uses == 1)
_test("directive record_loss works", dm_nr.get_stats("concise").uses == 1)


# ═══════════════════════════════════════════════════════════════════════════════
# Cleanup
# ═══════════════════════════════════════════════════════════════════════════════

_reset_memories()

# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if _FAIL > 0 else 0)
