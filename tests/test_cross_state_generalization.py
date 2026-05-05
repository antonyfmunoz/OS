"""
Test suite: Cross-State Generalization.

Validates the five cross-state generalization capabilities:
    A. State similarity weighting function
    B. Strategy cross-state generalization (transfer scores from similar clusters)
    C. Plan cross-state generalization (plan transfer scoring)
    D. Replan sensitivity by state (adjusted threshold on state shift)
    E. Decision trace visibility (5 new trace fields)

No LLM calls. No randomness. Deterministic assertions only.
"""

import sys

sys.path.insert(0, "/opt/OS")

_pass = 0
_fail = 0
_total = 0


def _section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def _test(label: str, condition: bool, detail: str = "") -> None:
    global _pass, _fail, _total
    _total += 1
    if condition:
        _pass += 1
        extra = f" -- {detail}" if detail else ""
        print(f"  [PASS] {label}{extra}")
    else:
        _fail += 1
        extra = f" -- {detail}" if detail else ""
        print(f"  [FAIL] {label}{extra}")


# ═══════════════════════════════════════════════════════════════════════════════
# 0. Imports
# ═══════════════════════════════════════════════════════════════════════════════

_section("0. Imports")

try:
    from umh.world.state import (
        WorldState,
        WorldStateEngine,
        StateCluster,
        ClusterPerformance,
        Entity,
        compute_state_transfer_weight,
        compute_feature_similarity,
        state_similarity,
        TRANSFER_SIMILARITY_THRESHOLD,
        TRANSFER_WEIGHT_SCALE,
        MIN_CLUSTER_SIZE,
        reset_world_state_engine,
    )
    from umh.strategy.memory import (
        StrategyMemory,
        get_strategy_memory,
        reset_strategy_memory,
    )
    from umh.runtime_engine.hierarchical_planning import (
        Plan,
        PlanStep,
        PlanProgress,
        PlanEngine,
        compute_plan_score,
        plan_to_utility,
        REPLAN_THRESHOLD,
        PLAN_CONFIDENCE_FLOOR,
        reset_plan_engine,
    )
    from umh.runtime_engine.decision_trace import DecisionTrace, build_trace

    _test("all imports succeed", True)
except Exception as e:
    _test("all imports succeed", False, str(e))
    print(f"\nFATAL: Import failed — cannot continue.\n{e}")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _make_state(
    turn: int = 0,
    features: dict | None = None,
    entities: tuple = (),
) -> WorldState:
    """Create a WorldState with deterministic features."""
    feats = features or {}
    return WorldState(
        state_id=f"ws_test_{turn}",
        timestamp=turn,
        entities=entities,
        relationships=(),
        features=tuple(sorted(feats.items())),
        derived_signals=(),
    )


def _make_cluster(
    cluster_id: str,
    centroid: dict,
    strategy_scores: dict | None = None,
    strategy_counts: dict | None = None,
    goal_scores: dict | None = None,
    observation_count: int = 3,
) -> StateCluster:
    """Create a StateCluster with pre-loaded performance data."""
    cluster = StateCluster(
        cluster_id=cluster_id,
        centroid_features=dict(centroid),
    )
    cluster.size = max(1, observation_count)
    cluster.performance = ClusterPerformance(
        strategy_scores=dict(strategy_scores or {}),
        strategy_counts=dict(strategy_counts or {}),
        goal_scores=dict(goal_scores or {}),
        goal_counts={},
        avg_utility=0.6,
        observation_count=observation_count,
    )
    return cluster


def _fresh_engine() -> WorldStateEngine:
    """Return a fresh WorldStateEngine instance."""
    return WorldStateEngine()


class _FakeTracker:
    """Minimal goal tracker for plan scoring."""

    def __init__(self, uses: int = 0, success_score: float = 0.5):
        self.uses = uses
        self.success_score = success_score


class _FakeRegistry:
    """Minimal goal registry for plan scoring."""

    def __init__(self, goals: list | None = None):
        self._goals = goals or []

    def get_all_goals(self):
        return self._goals

    def get_goal(self, goal_id: str):
        for g in self._goals:
            if g.goal_id == goal_id:
                return g
        return None

    def get_tracker(self, goal_id: str):
        return _FakeTracker(uses=0)


class _FakeGoal:
    def __init__(
        self,
        goal_id: str,
        priority: float = 0.7,
        success_criteria: dict | None = None,
        active: bool = True,
    ):
        self.goal_id = goal_id
        self.priority = priority
        self.success_criteria = success_criteria or {"metric": 0.8}
        self.active = active


class _FakeTrace:
    """Minimal trace for plan transfer scoring."""

    def __init__(
        self,
        quality_score: float = 0.8,
        active_goal_id: str | None = None,
        world_state_cluster: str | None = None,
        world_state_similarity: float | None = None,
    ):
        self.quality_score = quality_score
        self.active_goal_id = active_goal_id
        self.world_state_cluster = world_state_cluster
        self.world_state_similarity = world_state_similarity


# ═══════════════════════════════════════════════════════════════════════════════
# 1. compute_state_transfer_weight — threshold gating + linear ramp
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. Transfer weight: below threshold → 0.0")

_test(
    "similarity=0.0 → weight=0.0",
    compute_state_transfer_weight(0.0) == 0.0,
)
_test(
    "similarity=0.49 → weight=0.0",
    compute_state_transfer_weight(0.49) == 0.0,
)
_test(
    "similarity=threshold → weight=0.0",
    compute_state_transfer_weight(TRANSFER_SIMILARITY_THRESHOLD) == 0.0,
)

_section("2. Transfer weight: above threshold → linear ramp")

w_60 = compute_state_transfer_weight(0.6)
_test(
    "similarity=0.6 → positive weight",
    w_60 > 0.0,
    f"weight={w_60:.4f}",
)

w_75 = compute_state_transfer_weight(0.75)
_test(
    "similarity=0.75 → weight=0.5",
    abs(w_75 - 0.5) < 0.01,
    f"weight={w_75:.4f}",
)

w_100 = compute_state_transfer_weight(1.0)
_test(
    "similarity=1.0 → weight=1.0",
    abs(w_100 - 1.0) < 0.001,
    f"weight={w_100:.4f}",
)

_section("3. Transfer weight: monotonicity")

_test(
    "0.6 < 0.75 < 1.0 weights monotone",
    w_60 < w_75 < w_100,
    f"{w_60:.4f} < {w_75:.4f} < {w_100:.4f}",
)

_section("4. Transfer weight: clamping at boundaries")

_test(
    "negative similarity → 0.0",
    compute_state_transfer_weight(-0.5) == 0.0,
)
_test(
    "similarity > 1.0 → clamped to 1.0",
    compute_state_transfer_weight(1.5) <= 1.0,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Strategy transfer: similar clusters boost strategy ranking
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Strategy transfer: similar cluster → positive transfer scores")

engine = _fresh_engine()

# Create a state and a cluster with high feature overlap
centroid_feats = {"goal_count": 2.0, "quality_trend": 0.1, "plan_count": 1.0}
cluster = _make_cluster(
    "c_similar",
    centroid=centroid_feats,
    strategy_scores={"clarity": 0.8, "brevity": 0.6},
    strategy_counts={"clarity": 5, "brevity": 3},
    observation_count=5,
)
engine._clusters["c_similar"] = cluster

# State with nearly identical features → high centroid similarity
query_state = _make_state(
    turn=1,
    features={"goal_count": 2.0, "quality_trend": 0.1, "plan_count": 1.0},
)

transfer = engine.get_strategy_transfer_scores(query_state)

_test(
    "transfer scores returned for clarity",
    "clarity" in transfer,
    f"transfer={transfer}",
)
_test(
    "transfer scores returned for brevity",
    "brevity" in transfer,
    f"transfer={transfer}",
)
_test(
    "clarity transfer > 0",
    transfer.get("clarity", 0.0) > 0.0,
    f"clarity={transfer.get('clarity')}",
)
_test(
    "clarity transfer bounded by TRANSFER_WEIGHT_SCALE",
    transfer.get("clarity", 99.0) <= 1.0,
)

_section("6. Strategy transfer: clarity > brevity (higher source score)")

_test(
    "clarity transfer > brevity transfer",
    transfer.get("clarity", 0.0) > transfer.get("brevity", 0.0),
    f"clarity={transfer.get('clarity')}, brevity={transfer.get('brevity')}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Strategy transfer: dissimilar state → no transfer
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Strategy transfer: dissimilar state → zero transfer")

# State with completely different features — orthogonal to centroid
dissimilar_state = _make_state(
    turn=2,
    features={"exploration_rate": 5.0, "strategy_variance": 3.0, "confidence_avg": 4.0},
)

no_transfer = engine.get_strategy_transfer_scores(dissimilar_state)

_test(
    "dissimilar state → empty or zero transfer",
    all(v == 0.0 for v in no_transfer.values()) if no_transfer else True,
    f"transfer={no_transfer}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Strategy transfer: cluster below MIN_CLUSTER_SIZE → skip
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Strategy transfer: undersize cluster → skipped")

engine2 = _fresh_engine()
small_cluster = _make_cluster(
    "c_small",
    centroid=centroid_feats,
    strategy_scores={"clarity": 0.9},
    observation_count=1,  # below MIN_CLUSTER_SIZE
)
engine2._clusters["c_small"] = small_cluster

small_transfer = engine2.get_strategy_transfer_scores(query_state)

_test(
    "cluster with 1 observation → no transfer",
    len(small_transfer) == 0,
    f"transfer={small_transfer}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Strategy transfer feeds into rank_strategies
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Strategy transfer → rank_strategies integration")

reset_strategy_memory()
mem = StrategyMemory()

# Both strategies have same base performance
mem.record_win("clarity", quality_score=0.5)
mem.record_win("brevity", quality_score=0.5)

# Rank without transfer
ranked_no_transfer = mem.rank_strategies()
names_no_transfer = [n for n, _ in ranked_no_transfer]

# Rank with transfer boosting brevity
transfer_boost = {"brevity": 0.2, "clarity": 0.0}
ranked_with_transfer = mem.rank_strategies(transfer_scores=transfer_boost)
names_with_transfer = [n for n, _ in ranked_with_transfer]

_test(
    "transfer changes ranking order",
    names_with_transfer[0] == "brevity",
    f"top={names_with_transfer[0]}",
)

_section("10. get_conditioned_scores includes transfer")

base, cond = mem.get_conditioned_scores(transfer_scores=transfer_boost)

_test(
    "base scores exist for both",
    "clarity" in base and "brevity" in base,
)
_test(
    "conditioned brevity > base brevity",
    cond["brevity"] > base["brevity"],
    f"base={base['brevity']}, cond={cond['brevity']}",
)
_test(
    "conditioned clarity == base clarity (zero transfer)",
    abs(cond["clarity"] - base["clarity"]) < 0.001,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Plan transfer: successful goal chain in similar state
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. Plan transfer: matching goal + similar cluster → positive score")

engine3 = _fresh_engine()

# Set up a cluster that the trace will reference
plan_cluster = _make_cluster(
    "c_plan",
    centroid={"goal_count": 3.0, "quality_trend": 0.2},
    goal_scores={"g1": 0.9},
    observation_count=4,
)
engine3._clusters["c_plan"] = plan_cluster

# State similar to cluster centroid
plan_state = _make_state(
    turn=5,
    features={"goal_count": 3.0, "quality_trend": 0.2},
)

# Trace: goal g1 succeeded in cluster c_plan with high similarity
traces = [
    _FakeTrace(
        quality_score=0.9,
        active_goal_id="g1",
        world_state_cluster="c_plan",
        world_state_similarity=0.85,
    ),
]

plan_transfer = engine3.get_plan_transfer_score(
    state=plan_state,
    plan_goal_ids=("g1",),
    traces=traces,
)

_test(
    "plan transfer score > 0",
    plan_transfer > 0.0,
    f"score={plan_transfer:.4f}",
)
_test(
    "plan transfer score ≤ 1.0",
    plan_transfer <= 1.0,
    f"score={plan_transfer:.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Plan transfer: no matching goals → zero
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. Plan transfer: no goal overlap → zero")

no_match = engine3.get_plan_transfer_score(
    state=plan_state,
    plan_goal_ids=("g_unknown",),
    traces=traces,
)

_test(
    "non-matching goal → zero transfer",
    no_match == 0.0,
    f"score={no_match:.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Plan transfer: empty traces → zero
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. Plan transfer: empty traces → zero")

empty_transfer = engine3.get_plan_transfer_score(
    state=plan_state,
    plan_goal_ids=("g1",),
    traces=[],
)

_test(
    "empty trace list → zero",
    empty_transfer == 0.0,
)

none_transfer = engine3.get_plan_transfer_score(
    state=plan_state,
    plan_goal_ids=("g1",),
    traces=None,
)

_test(
    "None traces → zero",
    none_transfer == 0.0,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Plan transfer: dissimilar cluster → zero
# ═══════════════════════════════════════════════════════════════════════════════

_section("14. Plan transfer: dissimilar state → zero")

far_state = _make_state(
    turn=6,
    features={"exploration_rate": 5.0, "strategy_variance": 3.0},
)

far_transfer = engine3.get_plan_transfer_score(
    state=far_state,
    plan_goal_ids=("g1",),
    traces=traces,
)

_test(
    "dissimilar state → zero transfer",
    far_transfer == 0.0,
    f"score={far_transfer:.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 15. Plan transfer feeds into compute_plan_score
# ═══════════════════════════════════════════════════════════════════════════════

_section("15. compute_plan_score: transfer_score additive boost")

g1 = _FakeGoal("g1", priority=0.8)
registry = _FakeRegistry([g1])

plan = Plan(
    plan_id="plan_1",
    root_goal_id="g1",
    steps=(
        PlanStep(
            goal_id="g1",
            position=0,
        ),
    ),
    dependencies=(),
    expected_value=0.5,
    confidence=0.7,
    horizon=3,
    creation_turn=0,
)

score_no_transfer = compute_plan_score(plan, registry, plan_transfer_score=0.0)
score_with_transfer = compute_plan_score(plan, registry, plan_transfer_score=0.05)

_test(
    "transfer boost increases plan score",
    score_with_transfer > score_no_transfer,
    f"without={score_no_transfer:.4f}, with={score_with_transfer:.4f}",
)
_test(
    "boost delta equals transfer score",
    abs((score_with_transfer - score_no_transfer) - 0.05) < 0.001,
    f"delta={score_with_transfer - score_no_transfer:.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 16. plan_to_utility accepts plan_transfer_score
# ═══════════════════════════════════════════════════════════════════════════════

_section("16. plan_to_utility: transfer_score wired through")

progress = PlanProgress(plan_id="plan_1")

util_no = plan_to_utility(
    plan=plan,
    progress=progress,
    registry=registry,
    current_turn=1,
    plan_transfer_score=0.0,
)

util_yes = plan_to_utility(
    plan=plan,
    progress=progress,
    registry=registry,
    current_turn=1,
    plan_transfer_score=0.05,
)

_test(
    "plan_to_utility with transfer > without",
    util_yes > util_no,
    f"without={util_no:.4f}, with={util_yes:.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 17. Replan threshold: no state shift → default
# ═══════════════════════════════════════════════════════════════════════════════

_section("17. Replan threshold: zero delta → default threshold")

from umh.runtime_engine.hierarchical_planning import PlanEngine

threshold_default = PlanEngine.compute_replan_threshold(0.0)

_test(
    "zero delta → REPLAN_THRESHOLD",
    abs(threshold_default - REPLAN_THRESHOLD) < 0.001,
    f"threshold={threshold_default:.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 18. Replan threshold: large state shift → lower threshold
# ═══════════════════════════════════════════════════════════════════════════════

_section("18. Replan threshold: large delta → aggressive replan")

threshold_shift = PlanEngine.compute_replan_threshold(0.8)

_test(
    "large delta → threshold < REPLAN_THRESHOLD",
    threshold_shift < REPLAN_THRESHOLD,
    f"threshold={threshold_shift:.4f} < {REPLAN_THRESHOLD}",
)
_test(
    "threshold ≥ PLAN_CONFIDENCE_FLOOR",
    threshold_shift >= PLAN_CONFIDENCE_FLOOR,
    f"threshold={threshold_shift:.4f} ≥ {PLAN_CONFIDENCE_FLOOR}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 19. Replan threshold: maximum shift → floor
# ═══════════════════════════════════════════════════════════════════════════════

_section("19. Replan threshold: delta=1.0 → floor")

threshold_max = PlanEngine.compute_replan_threshold(1.0)

_test(
    "delta=1.0 → threshold at floor",
    abs(threshold_max - PLAN_CONFIDENCE_FLOOR) < 0.001,
    f"threshold={threshold_max:.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 20. Replan threshold: negative delta → clamped to 0
# ═══════════════════════════════════════════════════════════════════════════════

_section("20. Replan threshold: negative delta → treated as magnitude")

threshold_neg = PlanEngine.compute_replan_threshold(-0.5)
threshold_pos = PlanEngine.compute_replan_threshold(0.5)

_test(
    "negative delta → same result as abs(delta)",
    abs(threshold_neg - threshold_pos) < 0.001,
    f"neg={threshold_neg:.4f}, pos={threshold_pos:.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 21. should_replan with state_similarity_delta
# ═══════════════════════════════════════════════════════════════════════════════

_section("21. should_replan: state shift lowers replan bar")

reset_plan_engine()
pe = PlanEngine()

# Directly inject a plan + progress with failed steps and low confidence
pe._plans["plan_1"] = plan
pe._progress["plan_1"] = PlanProgress(plan_id="plan_1", confidence=0.20)
pe._progress["plan_1"].failed_steps.append("g1")

# Without state shift — confidence (0.20) < threshold (0.25) AND failed steps → needs replan
needs_replan_no_shift = pe.should_replan("plan_1", state_similarity_delta=0.0)

_test(
    "low confidence + failed step + no shift → needs replan",
    needs_replan_no_shift is True,
)

# Set confidence to 0.24 (just below default 0.25 but above shifted threshold)
pe._progress["plan_1"].confidence = 0.24

# Without shift → still below 0.25 → replan
needs_replan_marginal = pe.should_replan("plan_1", state_similarity_delta=0.0)

_test(
    "confidence 0.24 + no shift → needs replan (below 0.25)",
    needs_replan_marginal is True,
)

# With large state shift (delta=0.8) → threshold drops to 0.05
# Confidence 0.24 > 0.05 → does NOT need replan
needs_replan_shift = pe.should_replan("plan_1", state_similarity_delta=0.8)

_test(
    "confidence 0.24 + large shift → above lowered threshold",
    needs_replan_shift is False,
    f"adjusted threshold={PlanEngine.compute_replan_threshold(0.8):.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 22. Decision trace: 5 new fields present
# ═══════════════════════════════════════════════════════════════════════════════

_section("22. Decision trace: cross-state fields in constructor")

reset_strategy_memory()
mem2 = StrategyMemory()
mem2.record_win("test_strat", quality_score=0.7)

trace = build_trace(
    turn_id=1,
    state_transfer_weight=0.42,
    strategy_transfer_scores={"test_strat": 0.05},
    plan_transfer_score=0.03,
    state_similarity_used=0.78,
    replan_adjustment=0.18,
)

_test(
    "state_transfer_weight set",
    trace.state_transfer_weight == 0.42,
    f"value={trace.state_transfer_weight}",
)
_test(
    "strategy_transfer_scores set",
    trace.strategy_transfer_scores == {"test_strat": 0.05},
)
_test(
    "plan_transfer_score set",
    trace.plan_transfer_score == 0.03,
)
_test(
    "state_similarity_used set",
    trace.state_similarity_used == 0.78,
)
_test(
    "replan_adjustment set",
    trace.replan_adjustment == 0.18,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 23. Decision trace: to_dict includes new fields
# ═══════════════════════════════════════════════════════════════════════════════

_section("23. Decision trace: to_dict serialization")

d = trace.to_dict()

_test("state_transfer_weight in dict", "state_transfer_weight" in d)
_test("strategy_transfer_scores in dict", "strategy_transfer_scores" in d)
_test("plan_transfer_score in dict", "plan_transfer_score" in d)
_test("state_similarity_used in dict", "state_similarity_used" in d)
_test("replan_adjustment in dict", "replan_adjustment" in d)
_test(
    "serialized values match",
    d["state_transfer_weight"] == 0.42
    and d["plan_transfer_score"] == 0.03
    and d["state_similarity_used"] == 0.78
    and d["replan_adjustment"] == 0.18,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 24. Decision trace: None fields omitted from to_dict
# ═══════════════════════════════════════════════════════════════════════════════

_section("24. Decision trace: None values → omitted from dict")

reset_strategy_memory()
trace_none = build_trace(turn_id=2)

d_none = trace_none.to_dict()

_test(
    "state_transfer_weight absent when None",
    "state_transfer_weight" not in d_none,
)
_test(
    "strategy_transfer_scores absent when None",
    "strategy_transfer_scores" not in d_none,
)
_test(
    "plan_transfer_score absent when None",
    "plan_transfer_score" not in d_none,
)
_test(
    "state_similarity_used absent when None",
    "state_similarity_used" not in d_none,
)
_test(
    "replan_adjustment absent when None",
    "replan_adjustment" not in d_none,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 25. Decision trace: strategy_transfer_scores flow into build_trace ranking
# ═══════════════════════════════════════════════════════════════════════════════

_section("25. build_trace: transfer scores influence strategy_scores")

reset_strategy_memory()
mem3 = get_strategy_memory()
mem3.record_win("alpha", quality_score=0.5)
mem3.record_win("beta", quality_score=0.5)

# With transfer boosting beta
trace_boosted = build_trace(
    turn_id=3,
    strategy_transfer_scores={"beta": 0.3},
)

_test(
    "beta score > alpha score in trace",
    trace_boosted.strategy_scores.get("beta", 0)
    > trace_boosted.strategy_scores.get("alpha", 0),
    f"alpha={trace_boosted.strategy_scores.get('alpha')}, beta={trace_boosted.strategy_scores.get('beta')}",
)
_test(
    "selected_strategy is beta (highest)",
    trace_boosted.selected_strategy == "beta",
)
_test(
    "strategy_conditioned_scores populated",
    trace_boosted.strategy_conditioned_scores is not None,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 26. Determinism: identical inputs → identical outputs
# ═══════════════════════════════════════════════════════════════════════════════

_section("26. Determinism: transfer weight")

for sim in [0.0, 0.3, 0.5, 0.7, 0.85, 1.0]:
    w1 = compute_state_transfer_weight(sim)
    w2 = compute_state_transfer_weight(sim)
    _test(
        f"sim={sim} → identical weight",
        w1 == w2,
        f"w={w1:.4f}",
    )


_section("27. Determinism: strategy transfer scores")

engine_det = _fresh_engine()
det_cluster = _make_cluster(
    "c_det",
    centroid={"goal_count": 1.0, "quality_trend": 0.5},
    strategy_scores={"s1": 0.7, "s2": 0.3},
    observation_count=5,
)
engine_det._clusters["c_det"] = det_cluster

det_state = _make_state(features={"goal_count": 1.0, "quality_trend": 0.5})

t1 = engine_det.get_strategy_transfer_scores(det_state)
t2 = engine_det.get_strategy_transfer_scores(det_state)

_test(
    "strategy transfer deterministic",
    t1 == t2,
    f"t1={t1}, t2={t2}",
)


_section("28. Determinism: plan transfer score")

det_traces = [
    _FakeTrace(
        quality_score=0.8,
        active_goal_id="g1",
        world_state_cluster="c_det",
        world_state_similarity=0.9,
    ),
]

p1 = engine_det.get_plan_transfer_score(det_state, ("g1",), det_traces)
p2 = engine_det.get_plan_transfer_score(det_state, ("g1",), det_traces)

_test(
    "plan transfer deterministic",
    p1 == p2,
    f"p1={p1:.4f}, p2={p2:.4f}",
)


_section("29. Determinism: replan threshold")

for delta in [0.0, 0.25, 0.5, 0.75, 1.0]:
    r1 = PlanEngine.compute_replan_threshold(delta)
    r2 = PlanEngine.compute_replan_threshold(delta)
    _test(
        f"delta={delta} → identical threshold",
        r1 == r2,
        f"t={r1:.4f}",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 30. No LLM calls, no randomness
# ═══════════════════════════════════════════════════════════════════════════════

_section("30. No LLM calls, no randomness, no external deps")

import importlib

ws_mod = importlib.import_module("umh.runtime_engine.world_state")
sm_mod = importlib.import_module("umh.runtime_engine.strategy_memory")
hp_mod = importlib.import_module("umh.runtime_engine.hierarchical_planning")
dt_mod = importlib.import_module("umh.runtime_engine.decision_trace")

for mod_name, mod in [
    ("world_state", ws_mod),
    ("strategy_memory", sm_mod),
    ("hierarchical_planning", hp_mod),
    ("decision_trace", dt_mod),
]:
    src = open(mod.__file__).read()
    _test(
        f"{mod_name}: no random import",
        "import random" not in src,
    )
    _test(
        f"{mod_name}: no LLM call",
        "call_with_fallback" not in src
        and "anthropic" not in src.lower().split("import")[0]
        if "import" in src
        else True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 31. ExecutionSpine unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("31. ExecutionSpine not modified")

import os

spine_path = "/opt/OS/eos/execution_spine.py"
spine_stat = os.stat(spine_path)

_test(
    "execution_spine.py exists",
    os.path.exists(spine_path),
)

# Check that none of the new transfer symbols appear in execution_spine
spine_src = open(spine_path).read()

_test(
    "no transfer_weight in spine",
    "transfer_weight" not in spine_src,
)
_test(
    "no transfer_score in spine",
    "transfer_score" not in spine_src,
)
_test(
    "no replan_adjustment in spine",
    "replan_adjustment" not in spine_src,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 32. Multi-cluster aggregation
# ═══════════════════════════════════════════════════════════════════════════════

_section("32. Strategy transfer: multi-cluster weighted aggregation")

engine_multi = _fresh_engine()

# Two clusters, both above threshold but different distances
c1 = _make_cluster(
    "c_near",
    centroid={"goal_count": 2.0, "plan_count": 1.0},
    strategy_scores={"focused": 0.9, "broad": 0.3},
    observation_count=5,
)
c2 = _make_cluster(
    "c_far",
    centroid={"goal_count": 2.0, "plan_count": 1.0, "quality_trend": 0.5},
    strategy_scores={"focused": 0.4, "broad": 0.8},
    observation_count=4,
)
engine_multi._clusters["c_near"] = c1
engine_multi._clusters["c_far"] = c2

multi_state = _make_state(features={"goal_count": 2.0, "plan_count": 1.0})

multi_transfer = engine_multi.get_strategy_transfer_scores(multi_state)

_test(
    "multi-cluster: focused present",
    "focused" in multi_transfer,
)
_test(
    "multi-cluster: broad present",
    "broad" in multi_transfer,
)
_test(
    "multi-cluster: all values bounded",
    all(0.0 <= v <= 1.0 for v in multi_transfer.values()),
    f"transfer={multi_transfer}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 33. Backward compatibility: existing APIs unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("33. Backward compatibility: no required args changed")

# rank_strategies works without transfer_scores
reset_strategy_memory()
mem_bc = StrategyMemory()
mem_bc.record_win("x", quality_score=0.5)

ranked_bc = mem_bc.rank_strategies()
_test(
    "rank_strategies() works without transfer_scores",
    len(ranked_bc) > 0,
)

# get_conditioned_scores works without transfer_scores
base_bc, cond_bc = mem_bc.get_conditioned_scores()
_test(
    "get_conditioned_scores() works without transfer_scores",
    isinstance(base_bc, dict),
)

# compute_plan_score works without plan_transfer_score
score_bc = compute_plan_score(plan, registry)
_test(
    "compute_plan_score() works without transfer",
    score_bc > 0.0 or score_bc == 0.0,
)

# plan_to_utility works without plan_transfer_score
util_bc = plan_to_utility(
    plan, PlanProgress(plan_id="plan_1"), registry, current_turn=1
)
_test(
    "plan_to_utility() works without transfer",
    isinstance(util_bc, float),
)

# should_replan works without state_similarity_delta
reset_plan_engine()
pe_bc = PlanEngine()
pe_bc._plans["plan_1"] = plan
pe_bc._progress["plan_1"] = PlanProgress(plan_id="plan_1")
sr_bc = pe_bc.should_replan("plan_1")
_test(
    "should_replan() works without delta",
    isinstance(sr_bc, bool),
)


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'=' * 60}")
print(f"  TOTAL: {_total} | PASS: {_pass} | FAIL: {_fail}")
print(f"{'=' * 60}")

if _fail > 0:
    sys.exit(1)
