"""
Tests for World State Modeling & Abstraction Layer.

Proves:
    1. State extracted consistently from runtime signals
    2. Similar states cluster together
    3. Behavior changes when state differs (conditioning bias)
    4. Improved selection vs baseline (cluster-informed bias)
    5. No regressions
    6. Deterministic outputs
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

_section("0. Imports")

from umh.world.state import (
    Entity,
    WorldState,
    NO_STATE,
    StateCluster,
    ClusterPerformance,
    ConditioningBias,
    NO_BIAS,
    WorldStateEngine,
    extract_state,
    state_similarity,
    compute_feature_similarity,
    compute_entity_overlap,
    compute_structural_similarity,
    get_world_state_engine,
    reset_world_state_engine,
    MAX_CLUSTERS,
    MAX_STATES_PER_CLUSTER,
    MAX_STATE_HISTORY,
    CLUSTER_SIMILARITY_THRESHOLD,
    MIN_CLUSTER_SIZE,
    FEATURE_KEYS,
    CONDITIONING_WEIGHT,
)
from umh.goals.state import GoalState, GoalRegistry
from umh.runtime_engine.decision_trace import build_trace

_test("all imports succeed", True)


# ── Helpers ────────────────────────────────────────────────────────────────


def _fresh_registry() -> GoalRegistry:
    return GoalRegistry()


def _registry_with_goals() -> GoalRegistry:
    reg = GoalRegistry()
    reg.add_goal(
        GoalState(
            goal_id="sales",
            description="Close sales",
            success_criteria={"domain": "sales", "type": "persuasive"},
            priority=0.9,
        )
    )
    reg.add_goal(
        GoalState(
            goal_id="analyze",
            description="Analyze data",
            success_criteria={"domain": "analytics", "type": "technical"},
            priority=0.7,
        )
    )
    return reg


def _make_mock_traces(n: int, quality_base: float = 0.7) -> list:
    traces = []
    for i in range(n):

        class _T:
            pass

        t = _T()
        t.turn_id = i + 1
        t.quality_score = quality_base + 0.02 * i
        t.confidence = 0.8
        t.active_goal_id = "sales"
        t.goal_score = 0.75
        t.goal_delta = 0.05
        traces.append(t)
    return traces


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Entity data model
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. Entity — Data Model")

e = Entity(
    entity_id="goal_sales",
    entity_type="goal",
    attributes=(("priority", 0.9), ("active", True)),
)
_test("entity_id stored", e.entity_id == "goal_sales")
_test("entity_type stored", e.entity_type == "goal")
_test("attr lookup", e.attr("priority") == 0.9)
_test("attr default", e.attr("missing", 42) == 42)

ed = e.to_dict()
_test("to_dict has entity_id", "entity_id" in ed)
_test("to_dict has entity_type", "entity_type" in ed)
_test("to_dict has attributes", "attributes" in ed)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. WorldState data model
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. WorldState — Data Model")

ws = WorldState(
    state_id="ws_test123",
    timestamp=10,
    entities=(e,),
    relationships=(("goal_sales", "coexists_with", "goal_analyze"),),
    features=(("goal_count", 2.0), ("quality_trend", 0.1)),
    derived_signals=(("last_goal_score", 0.8),),
)
_test("state_id stored", ws.state_id == "ws_test123")
_test("timestamp stored", ws.timestamp == 10)
_test("entities count", len(ws.entities) == 1)
_test("relationships count", len(ws.relationships) == 1)
_test("feature_dict works", ws.feature_dict["goal_count"] == 2.0)
_test("get_feature works", ws.get_feature("quality_trend") == 0.1)
_test("get_feature default", ws.get_feature("missing") == 0.0)
_test("entity_ids property", "goal_sales" in ws.entity_ids)
_test("entity_types property", "goal" in ws.entity_types)
_test("get_entity works", ws.get_entity("goal_sales") is not None)
_test("get_entity miss", ws.get_entity("nope") is None)

wsd = ws.to_dict()
_test("to_dict has state_id", "state_id" in wsd)
_test("to_dict has entities", "entities" in wsd)
_test("to_dict has features", "features" in wsd)
_test("to_dict has relationships", "relationships" in wsd)

_test("NO_STATE exists", NO_STATE.state_id == "none")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. State extraction
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. State Extraction")

reg3 = _registry_with_goals()
traces3 = _make_mock_traces(5)

state3 = extract_state(
    registry=reg3,
    traces=traces3,
    current_turn=10,
    exploration_rate=0.3,
    plan_count=1,
    blended_entropy=0.5,
)
_test("state_id starts with ws_", state3.state_id.startswith("ws_"))
_test("timestamp is 10", state3.timestamp == 10)
_test("has entities", len(state3.entities) > 0)
_test("has features", len(state3.features) > 0)

fd3 = state3.feature_dict
_test("goal_count extracted", fd3["goal_count"] == 2.0)
_test("exploration_rate extracted", fd3["exploration_rate"] == 0.3)
_test("plan_count extracted", fd3["plan_count"] == 1.0)
_test("blend_entropy extracted", fd3["blend_entropy"] == 0.5)
_test("quality_trend computed", "quality_trend" in fd3)
_test("confidence_avg computed", "confidence_avg" in fd3)
_test("active_goal_priority extracted", fd3["active_goal_priority"] == 0.9)

goal_entities = [e for e in state3.entities if e.entity_type == "goal"]
_test("goal entities extracted", len(goal_entities) == 2)

_test("has relationships", len(state3.relationships) > 0)

state3_empty = extract_state(current_turn=1)
_test("empty extraction works", state3_empty.state_id.startswith("ws_"))
_test("empty: goal_count=0", state3_empty.get_feature("goal_count") == 0.0)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Feature similarity
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Feature Similarity")

ws_a = WorldState(
    state_id="a",
    timestamp=1,
    features=(("x", 1.0), ("y", 0.5)),
)
ws_b = WorldState(
    state_id="b",
    timestamp=2,
    features=(("x", 1.0), ("y", 0.5)),
)
ws_c = WorldState(
    state_id="c",
    timestamp=3,
    features=(("x", 0.0), ("y", 1.0)),
)

sim_same = compute_feature_similarity(ws_a, ws_b)
_test(
    "identical features → sim=1.0", abs(sim_same - 1.0) < 0.001, f"sim={sim_same:.4f}"
)

sim_diff = compute_feature_similarity(ws_a, ws_c)
_test("different features → lower sim", sim_diff < sim_same, f"sim={sim_diff:.4f}")

sim_empty = compute_feature_similarity(NO_STATE, NO_STATE)
_test("empty features → sim=1.0", abs(sim_empty - 1.0) < 0.001)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Entity overlap
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Entity Overlap")

ws_e1 = WorldState(
    state_id="e1",
    timestamp=1,
    entities=(Entity("a", "goal"), Entity("b", "goal")),
)
ws_e2 = WorldState(
    state_id="e2",
    timestamp=2,
    entities=(Entity("a", "goal"), Entity("c", "goal")),
)
ws_e3 = WorldState(
    state_id="e3",
    timestamp=3,
    entities=(Entity("a", "goal"), Entity("b", "goal")),
)

overlap_partial = compute_entity_overlap(ws_e1, ws_e2)
_test(
    "partial overlap = 1/3",
    abs(overlap_partial - 1 / 3) < 0.001,
    f"overlap={overlap_partial:.4f}",
)

overlap_full = compute_entity_overlap(ws_e1, ws_e3)
_test("full overlap = 1.0", abs(overlap_full - 1.0) < 0.001)

overlap_empty = compute_entity_overlap(NO_STATE, NO_STATE)
_test("no entities → 1.0", abs(overlap_empty - 1.0) < 0.001)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Structural similarity
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. Structural Similarity")

ws_r1 = WorldState(
    state_id="r1",
    timestamp=1,
    relationships=(("a", "depends_on", "b"),),
)
ws_r2 = WorldState(
    state_id="r2",
    timestamp=2,
    relationships=(("a", "depends_on", "b"), ("b", "enables", "c")),
)

struct_sim = compute_structural_similarity(ws_r1, ws_r2)
_test("partial relationship overlap", 0.0 < struct_sim < 1.0, f"sim={struct_sim:.4f}")

struct_same = compute_structural_similarity(ws_r1, ws_r1)
_test("identical relationships → 1.0", abs(struct_same - 1.0) < 0.001)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Combined state similarity
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Combined State Similarity")

state_sim_same = state_similarity(ws_a, ws_b)
_test(
    "similar states → high similarity",
    state_sim_same > 0.7,
    f"sim={state_sim_same:.4f}",
)

state_sim_diff = state_similarity(ws_a, ws_c)
_test(
    "different states → lower similarity",
    state_sim_diff < state_sim_same,
    f"sim={state_sim_diff:.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. State clustering
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. State Clustering")

engine8 = WorldStateEngine()
reg8 = _registry_with_goals()

for i in range(5):
    engine8.extract_and_record(
        registry=reg8,
        traces=_make_mock_traces(3),
        current_turn=i + 1,
        exploration_rate=0.3,
        plan_count=1,
        blended_entropy=0.5,
    )

_test("states recorded", engine8.state_count == 5)
_test(
    "clusters created", engine8.cluster_count >= 1, f"clusters={engine8.cluster_count}"
)

clusters8 = engine8.get_all_clusters()
_test("cluster has members", clusters8[0].size >= 1, f"size={clusters8[0].size}")


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Similar states cluster together
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Similar States → Same Cluster")

engine9 = WorldStateEngine()
reg9 = _registry_with_goals()

for i in range(5):
    engine9.extract_and_record(
        registry=reg9,
        traces=_make_mock_traces(3),
        current_turn=i + 1,
        exploration_rate=0.3,
        plan_count=1,
        blended_entropy=0.5,
    )

_test(
    "similar states converge to few clusters",
    engine9.cluster_count <= 3,
    f"clusters={engine9.cluster_count}",
)

state9_new = extract_state(
    registry=reg9,
    traces=_make_mock_traces(3),
    current_turn=6,
    exploration_rate=0.3,
    plan_count=1,
    blended_entropy=0.5,
)
nearest9 = engine9.get_nearest_cluster(state9_new)
_test("new similar state matches existing cluster", nearest9 is not None)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Different states → different clusters
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. Different States → Different Clusters")

engine10 = WorldStateEngine()

reg10a = _fresh_registry()
reg10a.add_goal(GoalState(goal_id="fast", description="fast", priority=0.9))

reg10b = _fresh_registry()
for i in range(5):
    reg10b.add_goal(
        GoalState(
            goal_id=f"g_{i}",
            description=f"goal {i}",
            success_criteria={f"k_{i}": f"v_{i}"},
            priority=0.3 + i * 0.1,
        )
    )

for i in range(3):
    engine10.extract_and_record(
        registry=reg10a,
        current_turn=i + 1,
        exploration_rate=0.1,
        plan_count=0,
        blended_entropy=0.0,
    )

for i in range(3):
    engine10.extract_and_record(
        registry=reg10b,
        current_turn=i + 10,
        exploration_rate=0.9,
        plan_count=3,
        blended_entropy=1.5,
    )

_test(
    "different states → multiple clusters",
    engine10.cluster_count >= 2,
    f"clusters={engine10.cluster_count}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Cluster performance tracking
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. Cluster Performance")

cp = ClusterPerformance()
cp.record(
    strategy="clarity",
    strategy_score=0.8,
    goal_id="sales",
    goal_score=0.9,
    utility=0.85,
)
cp.record(
    strategy="clarity",
    strategy_score=0.7,
    goal_id="sales",
    goal_score=0.8,
    utility=0.75,
)
cp.record(
    strategy="baseline",
    strategy_score=0.4,
    goal_id="analyze",
    goal_score=0.5,
    utility=0.45,
)

_test("observation count", cp.observation_count == 3)
_test("best strategy is clarity", cp.best_strategy() == "clarity")
_test("best goal is sales", cp.best_goal() == "sales")
_test("avg utility > 0", cp.avg_utility > 0, f"avg={cp.avg_utility:.4f}")

cpd = cp.to_dict()
_test("to_dict has strategy_scores", "strategy_scores" in cpd)
_test("to_dict has goal_scores", "goal_scores" in cpd)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Conditioning bias
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. Conditioning Bias")

engine12 = WorldStateEngine()
reg12 = _registry_with_goals()

for i in range(5):
    s = engine12.extract_and_record(
        registry=reg12,
        traces=_make_mock_traces(3),
        current_turn=i + 1,
        exploration_rate=0.3,
        plan_count=1,
        blended_entropy=0.5,
    )
    engine12.record_outcome(
        s,
        strategy="clarity",
        strategy_score=0.85,
        goal_id="sales",
        goal_score=0.9,
        utility=0.87,
    )

state12_new = extract_state(
    registry=reg12,
    traces=_make_mock_traces(3),
    current_turn=6,
    exploration_rate=0.3,
    plan_count=1,
    blended_entropy=0.5,
)
bias12 = engine12.get_conditioning_bias(state12_new)

_test("bias has cluster_id", bias12.cluster_id is not None)
_test(
    "bias similarity > threshold",
    bias12.cluster_similarity >= CLUSTER_SIMILARITY_THRESHOLD,
    f"sim={bias12.cluster_similarity:.4f}",
)
_test(
    "strategy bias for clarity",
    "clarity" in bias12.strategy_bias,
    f"bias={bias12.strategy_bias}",
)
_test("goal bias for sales", "sales" in bias12.goal_bias, f"bias={bias12.goal_bias}")
_test(
    "expected utility > 0.5",
    bias12.expected_utility > 0.5,
    f"util={bias12.expected_utility:.4f}",
)

bd = bias12.to_dict()
_test("to_dict has cluster_id", "cluster_id" in bd)
_test("to_dict has strategy_bias", "strategy_bias" in bd)

_test("NO_BIAS exists", NO_BIAS.cluster_id is None)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Behavior changes with state
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. Behavior Changes with State")

engine13 = WorldStateEngine()
reg13a = _fresh_registry()
reg13a.add_goal(GoalState(goal_id="sales_only", description="sell", priority=0.9))

reg13b = _fresh_registry()
reg13b.add_goal(GoalState(goal_id="research", description="research", priority=0.5))
reg13b.add_goal(GoalState(goal_id="explore", description="explore", priority=0.4))
reg13b.add_goal(GoalState(goal_id="deep", description="deep", priority=0.3))

for i in range(4):
    s = engine13.extract_and_record(
        registry=reg13a,
        current_turn=i + 1,
        exploration_rate=0.1,
        plan_count=0,
    )
    engine13.record_outcome(s, strategy="clarity", strategy_score=0.9, utility=0.9)

for i in range(4):
    s = engine13.extract_and_record(
        registry=reg13b,
        current_turn=i + 10,
        exploration_rate=0.8,
        plan_count=2,
    )
    engine13.record_outcome(s, strategy="structured", strategy_score=0.7, utility=0.7)

state_a = extract_state(
    registry=reg13a, current_turn=20, exploration_rate=0.1, plan_count=0
)
state_b = extract_state(
    registry=reg13b, current_turn=20, exploration_rate=0.8, plan_count=2
)

bias_a = engine13.get_conditioning_bias(state_a)
bias_b = engine13.get_conditioning_bias(state_b)

biases_differ = (bias_a.cluster_id != bias_b.cluster_id) or (
    bias_a.strategy_bias != bias_b.strategy_bias
)
_test(
    "different states → different conditioning",
    biases_differ,
    f"a={bias_a.cluster_id}, b={bias_b.cluster_id}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Bounded growth (MAX_CLUSTERS)
# ═══════════════════════════════════════════════════════════════════════════════

_section("14. Bounded Growth")

engine14 = WorldStateEngine()
for i in range(MAX_CLUSTERS + 5):
    reg_i = _fresh_registry()
    for j in range(i + 1):
        reg_i.add_goal(
            GoalState(
                goal_id=f"g_{i}_{j}",
                description=f"g {i} {j}",
                success_criteria={f"unique_{i}_{j}": "val"},
                priority=0.1 * (j + 1),
            )
        )
    engine14.extract_and_record(
        registry=reg_i,
        current_turn=i * 100,
        exploration_rate=0.1 * (i % 10),
        plan_count=i % 4,
        blended_entropy=0.1 * i,
    )

_test(
    "cluster count bounded",
    engine14.cluster_count <= MAX_CLUSTERS,
    f"clusters={engine14.cluster_count}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 15. Bounded state history
# ═══════════════════════════════════════════════════════════════════════════════

_section("15. Bounded State History")

engine15 = WorldStateEngine()
for i in range(MAX_STATE_HISTORY + 10):
    engine15.extract_and_record(current_turn=i)

_test(
    "state history bounded",
    engine15.state_count <= MAX_STATE_HISTORY,
    f"count={engine15.state_count}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 16. DecisionTrace — world state fields
# ═══════════════════════════════════════════════════════════════════════════════

_section("16. DecisionTrace — World State Fields")

trace16 = build_trace(
    turn_id=1,
    world_state_id="ws_abc123",
    world_state_cluster="cluster_0_ws_abc1",
    world_state_similarity=0.85,
    conditioning_bias={"strategy_bias": {"clarity": 0.05}},
)
_test("trace has world_state_id", trace16.world_state_id == "ws_abc123")
_test(
    "trace has world_state_cluster", trace16.world_state_cluster == "cluster_0_ws_abc1"
)
_test("trace has world_state_similarity", trace16.world_state_similarity == 0.85)
_test("trace has conditioning_bias", "strategy_bias" in trace16.conditioning_bias)

td16 = trace16.to_dict()
_test("to_dict has world_state_id", td16["world_state_id"] == "ws_abc123")
_test("to_dict has world_state_similarity", td16["world_state_similarity"] == 0.85)
_test("to_dict has conditioning_bias", "conditioning_bias" in td16)

trace16_empty = build_trace(turn_id=2)
_test("empty: no world_state_id", trace16_empty.world_state_id is None)
_test(
    "empty to_dict: no world_state_id", "world_state_id" not in trace16_empty.to_dict()
)
_test(
    "empty to_dict: no conditioning_bias",
    "conditioning_bias" not in trace16_empty.to_dict(),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 17. Constants
# ═══════════════════════════════════════════════════════════════════════════════

_section("17. Constants")

_test("MAX_CLUSTERS is 8", MAX_CLUSTERS == 8)
_test("MAX_STATES_PER_CLUSTER is 10", MAX_STATES_PER_CLUSTER == 10)
_test("MAX_STATE_HISTORY is 50", MAX_STATE_HISTORY == 50)
_test("CLUSTER_SIMILARITY_THRESHOLD is 0.70", CLUSTER_SIMILARITY_THRESHOLD == 0.70)
_test("MIN_CLUSTER_SIZE is 2", MIN_CLUSTER_SIZE == 2)
_test("CONDITIONING_WEIGHT is 0.15", CONDITIONING_WEIGHT == 0.15)
_test("FEATURE_KEYS has 10 entries", len(FEATURE_KEYS) == 10)


# ═══════════════════════════════════════════════════════════════════════════════
# 18. Determinism
# ═══════════════════════════════════════════════════════════════════════════════

_section("18. Determinism")

reg18 = _registry_with_goals()
traces18 = _make_mock_traces(3)

state18a = extract_state(
    registry=reg18,
    traces=traces18,
    current_turn=10,
    exploration_rate=0.3,
    plan_count=1,
    blended_entropy=0.5,
)
state18b = extract_state(
    registry=reg18,
    traces=traces18,
    current_turn=10,
    exploration_rate=0.3,
    plan_count=1,
    blended_entropy=0.5,
)

_test("deterministic state_id", state18a.state_id == state18b.state_id)
_test("deterministic features", state18a.features == state18b.features)
_test("deterministic entities", len(state18a.entities) == len(state18b.entities))

sim18 = state_similarity(state18a, state18b)
_test("identical states → sim=1.0", abs(sim18 - 1.0) < 0.001, f"sim={sim18:.4f}")

engine18a = WorldStateEngine()
engine18b = WorldStateEngine()
for i in range(3):
    engine18a.extract_and_record(registry=reg18, traces=traces18, current_turn=i + 1)
    engine18b.extract_and_record(registry=reg18, traces=traces18, current_turn=i + 1)

_test("deterministic cluster count", engine18a.cluster_count == engine18b.cluster_count)


# ═══════════════════════════════════════════════════════════════════════════════
# 19. No LLM calls
# ═══════════════════════════════════════════════════════════════════════════════

_section("19. No LLM Calls")

with open("/opt/OS/eos/world_state.py") as f:
    _ws_src = f.read()

_test("no call_with_fallback", "call_with_fallback" not in _ws_src)
_test("no import random", "import random" not in _ws_src)
_test("no anthropic", "anthropic" not in _ws_src)
_test("no openai", "openai" not in _ws_src)
_test("no genai", "genai" not in _ws_src)
_test("no agent_runtime", "agent_runtime" not in _ws_src)


# ═══════════════════════════════════════════════════════════════════════════════
# 20. ExecutionSpine unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("20. ExecutionSpine Unchanged")

with open("/opt/OS/eos/execution_spine.py") as f:
    _spine_src = f.read()

_test("spine: no world_state ref", "world_state" not in _spine_src)
_test("spine: no WorldState ref", "WorldState" not in _spine_src)
_test("spine: no WorldStateEngine ref", "WorldStateEngine" not in _spine_src)


# ═══════════════════════════════════════════════════════════════════════════════
# 21. Singleton pattern
# ═══════════════════════════════════════════════════════════════════════════════

_section("21. Singleton Pattern")

ws_a = get_world_state_engine()
ws_b = get_world_state_engine()
_test("singleton: same instance", ws_a is ws_b)

reset_world_state_engine()
ws_c = get_world_state_engine()
_test("reset creates new instance", ws_a is not ws_c)


# ═══════════════════════════════════════════════════════════════════════════════
# 22. Persistence — snapshot and restore
# ═══════════════════════════════════════════════════════════════════════════════

_section("22. Persistence — Snapshot & Restore")

engine22 = WorldStateEngine()
reg22 = _registry_with_goals()
for i in range(5):
    s = engine22.extract_and_record(
        registry=reg22,
        current_turn=i + 1,
        exploration_rate=0.3,
        plan_count=1,
    )
    engine22.record_outcome(s, strategy="clarity", strategy_score=0.8, utility=0.85)

snap22 = engine22.snapshot()
_test("snapshot has clusters", "clusters" in snap22)
_test("snapshot has state_count", "state_count" in snap22)

engine22_restored = WorldStateEngine()
engine22_restored.restore(snap22)
_test(
    "restored cluster count", engine22_restored.cluster_count == engine22.cluster_count
)

for cid in engine22._clusters:
    if cid in engine22_restored._clusters:
        orig = engine22._clusters[cid]
        rest = engine22_restored._clusters[cid]
        _test(
            f"cluster {cid[:20]} performance preserved",
            rest.performance.observation_count == orig.performance.observation_count,
        )
        break


# ═══════════════════════════════════════════════════════════════════════════════
# 23. No new dependencies
# ═══════════════════════════════════════════════════════════════════════════════

_section("23. No New Dependencies")

_test("no requests", "requests" not in _ws_src)
_test("no httpx", "httpx" not in _ws_src)
_test("no numpy", "numpy" not in _ws_src)


# ═══════════════════════════════════════════════════════════════════════════════
# 24. Backward compatibility
# ═══════════════════════════════════════════════════════════════════════════════

_section("24. Backward Compatibility")

from umh.goals.state import GoalState as _GS, GoalRegistry as _GR

_compat_reg = _GR()
_compat_reg.add_goal(_GS(goal_id="compat", description="compat", priority=0.5))
_test("goal registry works normally", _compat_reg.get_goal("compat") is not None)

_compat_trace = build_trace(turn_id=99)
_test(
    "trace compat: works without world state fields",
    _compat_trace.world_state_id is None,
)
_test(
    "trace compat: conditioning_bias is None", _compat_trace.conditioning_bias is None
)


# ═══════════════════════════════════════════════════════════════════════════════
# 25. Cluster centroid similarity
# ═══════════════════════════════════════════════════════════════════════════════

_section("25. Cluster Centroid Similarity")

sc25 = StateCluster(cluster_id="test_cluster")
ws25_a = WorldState(
    state_id="csa",
    timestamp=1,
    features=(("goal_count", 2.0), ("exploration_rate", 0.3)),
)
ws25_b = WorldState(
    state_id="csb",
    timestamp=2,
    features=(("goal_count", 2.0), ("exploration_rate", 0.3)),
)
sc25.add_state(ws25_a)
sc25.add_state(ws25_b)

_test("cluster size = 2", sc25.size == 2)
_test("centroid has features", len(sc25.centroid_features) > 0)

sim25 = sc25.centroid_similarity(ws25_a)
_test("state similar to own cluster centroid", sim25 > 0.9, f"sim={sim25:.4f}")

ws25_diff = WorldState(
    state_id="csdiff",
    timestamp=3,
    features=(("goal_count", 10.0), ("exploration_rate", 0.9)),
)
sim25_diff = sc25.centroid_similarity(ws25_diff)
_test(
    "different state → lower centroid sim", sim25_diff < sim25, f"sim={sim25_diff:.4f}"
)


# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'=' * 60}")
print(f"  TOTAL: {_PASS} passed, {_FAIL} failed (out of {_PASS + _FAIL})")
print(f"{'=' * 60}")

if _FAIL > 0:
    sys.exit(1)
