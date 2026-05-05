"""
Tests for Meta-Goal Generation Layer.

Validates:
    1. goals are generated under correct conditions
    2. goals decay when unused
    3. no uncontrolled growth (MAX_GOALS cap)
    4. determinism preserved
    5. no regression
    6. no new LLM calls
    7. ExecutionSpine unchanged
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
    print(f"\n{'=' * 60}")
    print(f"  {name}")
    print(f"{'=' * 60}")


# ═══════════════════════════════════════════════════════════════════════════════
# 0. Imports
# ═══════════════════════════════════════════════════════════════════════════════

_section("0. Imports + Setup")

from umh.runtime_engine.meta_goal import (
    MetaGoalEngine,
    MetaGoal,
    GoalMutation,
    MetaGoalResult,
    NO_META_RESULT,
    MAX_GOALS,
    MIN_CONFIDENCE_TO_ACTIVATE,
    DECAY_RATE,
    DECAY_FLOOR,
    LOW_PERFORMANCE_THRESHOLD,
    LOW_PERFORMANCE_WINDOW,
    HIGH_ENTROPY_THRESHOLD,
    SUCCESS_CLUSTER_THRESHOLD,
    SUCCESS_CLUSTER_WINDOW,
    COOLDOWN_TURNS,
    GENERATED_PRIORITY_BASE,
)
from umh.goals.state import GoalState, GoalRegistry, GoalTracker
from umh.runtime_engine.decision_trace import DecisionTrace, build_trace

_test("imports", True)


# ── Mock trace helper ──────────────────────────────────────────────────────


class MockTrace:
    """Minimal trace mock for meta-goal tests."""

    def __init__(self, **kwargs):
        defaults = {
            "turn_id": 0,
            "active_goal_id": None,
            "goal_score": None,
            "goal_delta": None,
            "blended_entropy": None,
            "blended_primary_goal_id": None,
            "convergence_status": None,
            "selected_strategy": "",
            "strategy_scores": {},
            "quality_score": 0.5,
            "confidence": 0.5,
        }
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)


def _make_low_perf_traces(goal_id: str, n: int = 5, score: float = 0.2) -> list:
    """Create n traces with low goal_score for a given goal."""
    return [
        MockTrace(
            turn_id=i,
            active_goal_id=goal_id,
            goal_score=score,
            goal_delta=-0.1,
        )
        for i in range(n)
    ]


def _make_high_entropy_traces(n: int = 3, entropy: float = 0.8) -> list:
    """Create n traces with high blended_entropy."""
    return [
        MockTrace(
            turn_id=i,
            blended_entropy=entropy,
            active_goal_id="goal_a",
            goal_score=0.5,
        )
        for i in range(n)
    ]


def _make_registry_with_goals(*goals_data) -> GoalRegistry:
    """Create a registry with goals. goals_data: (goal_id, priority, ...)."""
    reg = GoalRegistry()
    for gd in goals_data:
        if isinstance(gd, GoalState):
            reg.add_goal(gd)
        elif isinstance(gd, tuple):
            reg.add_goal(
                GoalState(
                    goal_id=gd[0],
                    description=f"Test goal {gd[0]}",
                    priority=gd[1] if len(gd) > 1 else 0.5,
                )
            )
    return reg


# ═══════════════════════════════════════════════════════════════════════════════
# 1. MetaGoal model
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. MetaGoal model")

mg = MetaGoal(
    goal_id="test_goal",
    origin="generated",
    parent_goals=("parent_a",),
    confidence=0.7,
    utility_estimate=0.5,
    lifecycle_state="candidate",
    description="Test description",
    priority=0.5,
    generation_turn=10,
    generation_reason="test",
)

_test("goal_id set", mg.goal_id == "test_goal")
_test("origin set", mg.origin == "generated")
_test("parent_goals tuple", mg.parent_goals == ("parent_a",))
_test("lifecycle_state set", mg.lifecycle_state == "candidate")
_test("frozen", hasattr(mg, "__dataclass_fields__"))

d = mg.to_dict()
_test("to_dict has goal_id", d["goal_id"] == "test_goal")
_test("to_dict has origin", d["origin"] == "generated")
_test("to_dict has parent_goals as list", isinstance(d["parent_goals"], list))
_test("to_dict confidence rounded", isinstance(d["confidence"], float))


# ═══════════════════════════════════════════════════════════════════════════════
# 2. GoalMutation model
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. GoalMutation model")

mut = GoalMutation(
    mutation_type="split",
    source_goals=("parent_a",),
    result_goals=("child_a", "child_b"),
    reason="test_split",
    turn=5,
)
_test("mutation_type", mut.mutation_type == "split")
_test("source_goals", mut.source_goals == ("parent_a",))
_test("result_goals tuple", len(mut.result_goals) == 2)
md = mut.to_dict()
_test("to_dict has mutation_type", md["mutation_type"] == "split")
_test("to_dict source as list", isinstance(md["source_goals"], list))


# ═══════════════════════════════════════════════════════════════════════════════
# 3. MetaGoalResult model
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. MetaGoalResult model")

result = MetaGoalResult(
    generated=(mg,),
    retired=("old_goal",),
    mutations=(mut,),
    reason="test_reason",
)
_test("has_changes true", result.has_changes)
_test("NO_META_RESULT no changes", not NO_META_RESULT.has_changes)
rd = result.to_dict()
_test("to_dict has generated list", len(rd["generated"]) == 1)
_test("to_dict has retired list", len(rd["retired"]) == 1)
_test("to_dict has mutations list", len(rd["mutations"]) == 1)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Engine construction and initial state
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Engine construction")

engine = MetaGoalEngine()
_test("engine created", engine is not None)
_test("generation_counter 0", engine.generation_counter == 0)
_test("generated_count 0", engine.generated_count == 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. No generation with empty registry
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. No generation — empty registry")

engine = MetaGoalEngine()
reg = GoalRegistry()
result = engine.evaluate(reg, traces=[], current_turn=10)
_test("no changes empty registry", not result.has_changes)
_test("reason no_action", result.reason == "no_action")


# ═══════════════════════════════════════════════════════════════════════════════
# 6. No generation — insufficient trace history
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. No generation — insufficient traces")

engine = MetaGoalEngine()
reg = _make_registry_with_goals(("goal_a", 0.7))
traces = [MockTrace(turn_id=0, active_goal_id="goal_a", goal_score=0.2)]
result = engine.evaluate(reg, traces=traces, current_turn=10)
_test("no changes few traces", not result.has_changes)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Low performance trigger — generates alternative goal
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Low performance trigger")

engine = MetaGoalEngine()
reg = _make_registry_with_goals(("goal_a", 0.7))
traces = _make_low_perf_traces("goal_a", n=LOW_PERFORMANCE_WINDOW, score=0.2)
result = engine.evaluate(reg, traces=traces, current_turn=COOLDOWN_TURNS + 1)

_test("generated 1 goal", len(result.generated) == 1)
_test("generated goal origin", result.generated[0].origin == "generated")
_test(
    "generated goal parent",
    result.generated[0].parent_goals == ("goal_a",),
)
_test(
    "generated goal lifecycle candidate",
    result.generated[0].lifecycle_state == "candidate",
)
_test("has split mutation", len(result.mutations) == 1)
_test("mutation type split", result.mutations[0].mutation_type == "split")
_test(
    "reason includes low_performance",
    "low_performance" in result.reason,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. High entropy trigger — generates specialization
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. High entropy trigger")

engine = MetaGoalEngine()
reg = _make_registry_with_goals(("goal_a", 0.7))
traces = _make_high_entropy_traces(n=3, entropy=0.8)
result = engine.evaluate(reg, traces=traces, current_turn=COOLDOWN_TURNS + 1)

_test("generated specialization", len(result.generated) >= 1)
_test(
    "generated is specialization",
    result.generated[0].generation_reason == "high_entropy_specialization",
)
_test(
    "reason includes entropy",
    "entropy" in result.reason,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Success cluster trigger — generates abstraction
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Success cluster trigger")

engine = MetaGoalEngine()
reg = _make_registry_with_goals(("goal_a", 0.7), ("goal_b", 0.8))

# Manually set tracker state to simulate high success
tracker_a = reg.get_tracker("goal_a")
tracker_b = reg.get_tracker("goal_b")
for _ in range(SUCCESS_CLUSTER_WINDOW):
    tracker_a.update_success(0.85)
    tracker_b.update_success(0.90)

traces = [MockTrace(turn_id=i) for i in range(3)]
result = engine.evaluate(reg, traces=traces, current_turn=COOLDOWN_TURNS + 1)

_test("generated merge goal", len(result.generated) == 1)
_test(
    "generated is abstraction",
    result.generated[0].generation_reason == "success_cluster_abstraction",
)
_test(
    "parent includes both",
    set(result.generated[0].parent_goals) == {"goal_a", "goal_b"},
)
_test("has merge mutation", any(m.mutation_type == "merge" for m in result.mutations))


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Cooldown enforcement
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. Cooldown enforcement")

engine = MetaGoalEngine()
reg = _make_registry_with_goals(("goal_a", 0.7))
traces = _make_low_perf_traces("goal_a", n=LOW_PERFORMANCE_WINDOW, score=0.2)

# First evaluation triggers generation
r1 = engine.evaluate(reg, traces=traces, current_turn=COOLDOWN_TURNS + 1)
_test("first eval generates", len(r1.generated) == 1)

# Register the generated goal (as SessionRuntime would)
for _mg in r1.generated:
    engine.register_generated(_mg)

# Second evaluation within cooldown does NOT generate
r2 = engine.evaluate(reg, traces=traces, current_turn=COOLDOWN_TURNS + 2)
_test("cooldown blocks generation", len(r2.generated) == 0)

# After cooldown expires, won't generate again because same alternative exists
r3 = engine.evaluate(
    reg, traces=traces, current_turn=COOLDOWN_TURNS + 1 + COOLDOWN_TURNS + 1
)
_test("duplicate prevention works", len(r3.generated) == 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Decay of unused generated goals
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. Decay of unused goals")

engine = MetaGoalEngine()
reg = _make_registry_with_goals(("goal_a", 0.7))

# Manually register a generated goal
mg_test = MetaGoal(
    goal_id="meta_test",
    origin="generated",
    parent_goals=("goal_a",),
    confidence=0.6,
    utility_estimate=0.5,
    lifecycle_state="candidate",
    generation_turn=0,
    generation_reason="test",
)
engine.register_generated(mg_test)

# Evaluate at a later turn — confidence should decay
engine.evaluate(reg, traces=[], current_turn=10)

decayed = engine.get_generated("meta_test")
_test("confidence decayed", decayed.confidence < 0.6, f"conf={decayed.confidence}")
_test(
    "decay formula correct",
    abs(decayed.confidence - max(0.6 - DECAY_RATE * 10, DECAY_FLOOR)) < 0.01,
    f"expected={max(0.6 - DECAY_RATE * 10, DECAY_FLOOR)}, got={decayed.confidence}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Retirement of decayed goals
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. Retirement of decayed goals")

engine = MetaGoalEngine()
reg = _make_registry_with_goals(("goal_a", 0.7))

# Register a goal with confidence at floor
mg_low = MetaGoal(
    goal_id="meta_low",
    origin="generated",
    parent_goals=("goal_a",),
    confidence=DECAY_FLOOR,
    utility_estimate=0.5,
    lifecycle_state="candidate",
    generation_turn=0,
    generation_reason="test",
)
engine.register_generated(mg_low)

result = engine.evaluate(reg, traces=[], current_turn=5)
_test("retired low confidence", "meta_low" in result.retired)

retired_mg = engine.get_generated("meta_low")
_test("lifecycle retired", retired_mg.lifecycle_state == "retired")


# ═══════════════════════════════════════════════════════════════════════════════
# 13. MAX_GOALS cap enforcement
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. MAX_GOALS cap enforcement")

engine = MetaGoalEngine()
reg = GoalRegistry()

# Add MAX_GOALS + 2 goals to registry
for i in range(MAX_GOALS + 2):
    g = GoalState(
        goal_id=f"goal_{i:02d}",
        description=f"Test goal {i}",
        priority=0.5,
    )
    reg.add_goal(g)

# Register 2 of them as generated (so they can be removed)
for i in range(MAX_GOALS, MAX_GOALS + 2):
    mg_cap = MetaGoal(
        goal_id=f"goal_{i:02d}",
        origin="generated",
        parent_goals=(),
        confidence=0.3,
        utility_estimate=0.5,
        lifecycle_state="active",
        generation_turn=0,
        generation_reason="test",
    )
    engine.register_generated(mg_cap)

result = engine.evaluate(reg, traces=[], current_turn=10)
_test("cap retired overflow goals", len(result.retired) >= 2)
_test(
    "cap in reason",
    "cap_enforced" in result.reason or "retired_low_confidence" in result.reason,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Candidate activation — confidence gate
# ═══════════════════════════════════════════════════════════════════════════════

_section("14. Candidate activation")

engine = MetaGoalEngine()

# Below threshold
mg_low_conf = MetaGoal(
    goal_id="low_conf",
    origin="generated",
    parent_goals=(),
    confidence=0.2,
    utility_estimate=0.5,
    lifecycle_state="candidate",
    generation_turn=0,
    generation_reason="test",
)
engine.register_generated(mg_low_conf)
_test("low confidence not activated", not engine.activate_candidate("low_conf"))

# Above threshold
mg_high_conf = MetaGoal(
    goal_id="high_conf",
    origin="generated",
    parent_goals=(),
    confidence=0.6,
    utility_estimate=0.5,
    lifecycle_state="candidate",
    generation_turn=0,
    generation_reason="test",
)
engine.register_generated(mg_high_conf)
_test("high confidence activated", engine.activate_candidate("high_conf"))

activated = engine.get_generated("high_conf")
_test("lifecycle now active", activated.lifecycle_state == "active")


# ═══════════════════════════════════════════════════════════════════════════════
# 15. Confidence update from performance feedback
# ═══════════════════════════════════════════════════════════════════════════════

_section("15. Confidence update from feedback")

engine = MetaGoalEngine()
mg_update = MetaGoal(
    goal_id="update_test",
    origin="generated",
    parent_goals=(),
    confidence=0.5,
    utility_estimate=0.5,
    lifecycle_state="active",
    generation_turn=0,
    generation_reason="test",
)
engine.register_generated(mg_update)

# Positive feedback
engine.update_confidence("update_test", goal_score=0.9)
after = engine.get_generated("update_test")
_test("confidence increased", after.confidence > 0.5, f"conf={after.confidence}")

# Negative feedback
engine.update_confidence("update_test", goal_score=0.1)
after2 = engine.get_generated("update_test")
_test("confidence decreased", after2.confidence < after.confidence)

# Convergence stable boosts update rate
engine.update_confidence("update_test", goal_score=0.9, convergence_stable=True)
after3 = engine.get_generated("update_test")
_test("convergence boost applied", after3.confidence > after2.confidence)


# ═══════════════════════════════════════════════════════════════════════════════
# 16. Priority adjustment
# ═══════════════════════════════════════════════════════════════════════════════

_section("16. Priority adjustment")

engine = MetaGoalEngine()
reg = _make_registry_with_goals(("perf_goal", 0.7))

mg_adj = MetaGoal(
    goal_id="perf_goal",
    origin="generated",
    parent_goals=(),
    confidence=0.6,
    utility_estimate=0.5,
    lifecycle_state="active",
    priority=0.5,
    generation_turn=0,
    generation_reason="test",
)
engine.register_generated(mg_adj)

# Simulate high performance in tracker
tracker = reg.get_tracker("perf_goal")
for _ in range(5):
    tracker.update_success(0.85)

result = engine.evaluate(reg, traces=[], current_turn=10)
_test(
    "priority adjustment mutation",
    any(m.mutation_type == "priority_adjust" for m in result.mutations),
)

after_adj = engine.get_generated("perf_goal")
_test("priority increased", after_adj.priority > 0.5, f"pri={after_adj.priority}")


# ═══════════════════════════════════════════════════════════════════════════════
# 17. Determinism — same inputs same outputs
# ═══════════════════════════════════════════════════════════════════════════════

_section("17. Determinism")


def _run_determinism_test():
    engine1 = MetaGoalEngine()
    engine2 = MetaGoalEngine()
    reg1 = _make_registry_with_goals(("goal_a", 0.7))
    reg2 = _make_registry_with_goals(("goal_a", 0.7))
    traces = _make_low_perf_traces("goal_a", n=LOW_PERFORMANCE_WINDOW, score=0.2)

    r1 = engine1.evaluate(reg1, traces=traces, current_turn=COOLDOWN_TURNS + 1)
    r2 = engine2.evaluate(reg2, traces=traces, current_turn=COOLDOWN_TURNS + 1)
    return r1, r2


r1, r2 = _run_determinism_test()
_test("same number of generated", len(r1.generated) == len(r2.generated))
_test("same reason", r1.reason == r2.reason)
if r1.generated and r2.generated:
    _test("same goal_id", r1.generated[0].goal_id == r2.generated[0].goal_id)
    _test("same confidence", r1.generated[0].confidence == r2.generated[0].confidence)
    _test("same priority", r1.generated[0].priority == r2.generated[0].priority)


# ═══════════════════════════════════════════════════════════════════════════════
# 18. to_meta_goal_state conversion
# ═══════════════════════════════════════════════════════════════════════════════

_section("18. GoalState conversion")

engine = MetaGoalEngine()
mg_conv = MetaGoal(
    goal_id="conv_test",
    origin="generated",
    parent_goals=("p1",),
    confidence=0.7,
    utility_estimate=0.5,
    lifecycle_state="active",
    description="Converted goal",
    success_criteria={"domain": "test"},
    priority=0.6,
    generation_turn=5,
    generation_reason="test",
)
gs = engine.to_meta_goal_state(mg_conv)
_test("GoalState type", type(gs).__name__ == "GoalState")
_test("GoalState goal_id", gs.goal_id == "conv_test")
_test("GoalState description", gs.description == "Converted goal")
_test("GoalState priority", gs.priority == 0.6)
_test("GoalState active", gs.active is True)
_test("GoalState criteria preserved", gs.success_criteria.get("domain") == "test")


# ═══════════════════════════════════════════════════════════════════════════════
# 19. DecisionTrace fields
# ═══════════════════════════════════════════════════════════════════════════════

_section("19. DecisionTrace fields")

trace = build_trace(
    turn_id=1,
    generated_goals=({"goal_id": "meta_1", "origin": "generated"},),
    goal_mutations=({"mutation_type": "split", "source_goals": ["g1"]},),
    meta_goal_reason="low_performance_split",
)
_test("trace has generated_goals", trace.generated_goals is not None)
_test("trace has goal_mutations", trace.goal_mutations is not None)
_test("trace has meta_goal_reason", trace.meta_goal_reason == "low_performance_split")

td = trace.to_dict()
_test("to_dict has generated_goals", "generated_goals" in td)
_test("to_dict has goal_mutations", "goal_mutations" in td)
_test("to_dict has meta_goal_reason", "meta_goal_reason" in td)

# None fields don't appear
trace_empty = build_trace(turn_id=2)
td2 = trace_empty.to_dict()
_test("empty trace no generated_goals", "generated_goals" not in td2)
_test("empty trace no goal_mutations", "goal_mutations" not in td2)
_test("empty trace no meta_goal_reason", "meta_goal_reason" not in td2)


# ═══════════════════════════════════════════════════════════════════════════════
# 20. Engine snapshot
# ═══════════════════════════════════════════════════════════════════════════════

_section("20. Engine snapshot")

engine = MetaGoalEngine()
mg_snap = MetaGoal(
    goal_id="snap_test",
    origin="generated",
    parent_goals=(),
    confidence=0.7,
    utility_estimate=0.5,
    lifecycle_state="active",
    generation_turn=0,
    generation_reason="test",
)
engine.register_generated(mg_snap)

snap = engine.snapshot()
_test("snapshot has generated_goals", "snap_test" in snap["generated_goals"])
_test("snapshot generation_counter", snap["generation_counter"] == 0)
_test("snapshot active_generated", snap["active_generated"] == 1)
_test("snapshot candidates", snap["candidates"] == 0)
_test("snapshot retired", snap["retired"] == 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 21. No LLM calls verification
# ═══════════════════════════════════════════════════════════════════════════════

_section("21. No LLM calls")

import inspect

src = inspect.getsource(MetaGoalEngine)
_test("no call_with_fallback", "call_with_fallback" not in src)
_test("no anthropic", "anthropic" not in src.lower())
_test("no openai", "openai" not in src.lower())
_test("no genai", "genai" not in src)
_test("no agent_runtime", "agent_runtime" not in src)


# ═══════════════════════════════════════════════════════════════════════════════
# 22. ExecutionSpine unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("22. ExecutionSpine unchanged")

spine_src = inspect.getsource(
    __import__("umh.runtime_engine.execution_spine", fromlist=["ExecutionSpine"]).ExecutionSpine
)
_test("spine has no meta_goal ref", "meta_goal" not in spine_src)
_test("spine has no MetaGoalEngine ref", "MetaGoalEngine" not in spine_src)


# ═══════════════════════════════════════════════════════════════════════════════
# 23. Backward compatibility — no goals = no meta changes
# ═══════════════════════════════════════════════════════════════════════════════

_section("23. Backward compatibility")

engine = MetaGoalEngine()
reg = GoalRegistry()
result = engine.evaluate(reg, traces=[], current_turn=100)
_test("empty registry no changes", not result.has_changes)
_test("empty registry no_action", result.reason == "no_action")

# Single goal, no trigger conditions
engine2 = MetaGoalEngine()
reg2 = _make_registry_with_goals(("goal_a", 0.7))
traces_ok = [
    MockTrace(turn_id=i, active_goal_id="goal_a", goal_score=0.7) for i in range(10)
]
result2 = engine2.evaluate(reg2, traces=traces_ok, current_turn=COOLDOWN_TURNS + 1)
_test("healthy goal no generation", len(result2.generated) == 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 24. Goal split does not remove parent
# ═══════════════════════════════════════════════════════════════════════════════

_section("24. Split preserves parent")

engine = MetaGoalEngine()
reg = _make_registry_with_goals(("goal_a", 0.7))
traces = _make_low_perf_traces("goal_a", n=LOW_PERFORMANCE_WINDOW, score=0.2)
result = engine.evaluate(reg, traces=traces, current_turn=COOLDOWN_TURNS + 1)

_test("parent still in registry", reg.get_goal("goal_a") is not None)
_test("parent not in retired", "goal_a" not in result.retired)


# ═══════════════════════════════════════════════════════════════════════════════
# 25. Multiple evaluations track state correctly
# ═══════════════════════════════════════════════════════════════════════════════

_section("25. Stateful multi-turn tracking")

engine = MetaGoalEngine()
reg = _make_registry_with_goals(("goal_a", 0.7))

# Turn 1: insufficient data
r1 = engine.evaluate(reg, traces=[], current_turn=0)
_test("turn 0 no changes", not r1.has_changes)

# Build up low performance
traces = _make_low_perf_traces("goal_a", n=LOW_PERFORMANCE_WINDOW, score=0.2)

# Turn 6: triggers generation
r2 = engine.evaluate(reg, traces=traces, current_turn=COOLDOWN_TURNS + 1)
_test("turn 6 generates", len(r2.generated) == 1)

# Register generated goal (as SessionRuntime does)
for _mg in r2.generated:
    engine.register_generated(_mg)

_test("engine tracks generation", engine.generated_count == 1)
_test("generation counter incremented", engine.generation_counter == 1)


# ═══════════════════════════════════════════════════════════════════════════════
# 26. Registry integration — generated goals work with arbitrator
# ═══════════════════════════════════════════════════════════════════════════════

_section("26. Registry integration")

from umh.runtime_engine.goal_arbitrator import GoalArbitrator

engine = MetaGoalEngine()
reg = _make_registry_with_goals(("goal_a", 0.7))

# Generate and register a goal
mg_reg = MetaGoal(
    goal_id="meta_alt_goal_a",
    origin="generated",
    parent_goals=("goal_a",),
    confidence=0.8,
    utility_estimate=0.5,
    lifecycle_state="active",
    description="Alternative to goal_a",
    priority=0.8,
    generation_turn=5,
    generation_reason="test",
)
engine.register_generated(mg_reg)
gs = engine.to_meta_goal_state(mg_reg)
reg.add_goal(gs)

arb = GoalArbitrator()
reg.advance_turn()
arb_result = arb.select_active_goal(reg)

_test("arbitrator sees generated goal", "meta_alt_goal_a" in arb_result.utilities)
_test("arbitrator selects one", arb_result.selected_goal_id is not None)
_test("generated goal competes", arb_result.utilities.get("meta_alt_goal_a", 0) > 0)


# ═══════════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'=' * 60}")
print(f"  TOTAL: {_PASS} passed, {_FAIL} failed (out of {_PASS + _FAIL})")
print(f"{'=' * 60}")

if _FAIL > 0:
    sys.exit(1)
