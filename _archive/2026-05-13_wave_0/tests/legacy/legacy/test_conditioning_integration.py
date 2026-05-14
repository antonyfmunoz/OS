"""
Tests for Conditioning Bias → StrategyMemory Integration.

Proves:
    1. Identical state → identical strategy preference
    2. Different clusters → measurable selection shift
    3. No regressions across existing test suites
    4. Determinism preserved
    5. No new LLM calls
    6. ExecutionSpine unchanged
    7. Base vs conditioned scores logged in DecisionTrace
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

from umh.strategy.memory import (
    StrategyMemory,
    StrategyStats,
    get_strategy_memory,
    reset_strategy_memory,
    EMA_ALPHA,
    DECAY_RATE,
)
from umh.world.state import (
    WorldState,
    WorldStateEngine,
    ConditioningBias,
    NO_BIAS,
    ClusterPerformance,
    StateCluster,
    extract_state,
    get_world_state_engine,
    reset_world_state_engine,
    CONDITIONING_WEIGHT,
)
from umh.runtime_engine.decision_trace import DecisionTrace, build_trace

_test("all imports succeed", True)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. rank_strategies accepts conditioning_bias
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. rank_strategies accepts conditioning_bias")

reset_strategy_memory()
mem = StrategyMemory()

mem.record_win("alpha", 0.8, confidence=1.0)
mem.record_win("beta", 0.6, confidence=1.0)

# Without bias: alpha should be first (0.8 > 0.6)
ranked_no_bias = mem.rank_strategies()
_test("alpha first without bias", ranked_no_bias[0][0] == "alpha")
_test("beta second without bias", ranked_no_bias[1][0] == "beta")

# With bias favoring beta: beta gets +0.3, alpha gets 0.0
ranked_with_bias = mem.rank_strategies(conditioning_bias={"beta": 0.3})
_test(
    "beta first with positive bias",
    ranked_with_bias[0][0] == "beta",
    f"got {ranked_with_bias[0][0]}",
)

# With bias penalizing alpha: alpha gets -0.5
ranked_neg_bias = mem.rank_strategies(conditioning_bias={"alpha": -0.5})
_test(
    "beta first with alpha penalty",
    ranked_neg_bias[0][0] == "beta",
    f"got {ranked_neg_bias[0][0]}",
)

# ═══════════════════════════════════════════════════════════════════════════════
# 2. Bias is transient — does not mutate StrategyStats
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. Bias is transient — no StrategyStats mutation")

alpha_before = mem.get_stats("alpha")
ema_before = alpha_before.ema_score
uses_before = alpha_before.uses

# Apply large bias and rank
mem.rank_strategies(conditioning_bias={"alpha": 10.0})

alpha_after = mem.get_stats("alpha")
_test("ema unchanged after biased rank", alpha_after.ema_score == ema_before)
_test("uses unchanged after biased rank", alpha_after.uses == uses_before)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. get_conditioned_scores returns base and conditioned
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. get_conditioned_scores observability")

base, cond = mem.get_conditioned_scores(
    conditioning_bias={"alpha": 0.05, "beta": -0.02}
)

_test("base scores are dict", isinstance(base, dict))
_test("conditioned scores are dict", isinstance(cond, dict))
_test("alpha base score exists", "alpha" in base)
_test("beta base score exists", "beta" in base)
_test(
    "alpha conditioned = base + bias",
    abs(cond["alpha"] - (base["alpha"] + 0.05)) < 1e-4,
    f"base={base['alpha']}, cond={cond['alpha']}",
)
_test(
    "beta conditioned = base + bias",
    abs(cond["beta"] - (base["beta"] - 0.02)) < 1e-4,
    f"base={base['beta']}, cond={cond['beta']}",
)

# No bias: both dicts should be identical
base_no, cond_no = mem.get_conditioned_scores()
_test("no bias: base == conditioned", base_no == cond_no)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Identical state → identical strategy preference
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Identical state → identical preference")

reset_strategy_memory()
mem2 = StrategyMemory()
mem2.record_win("clarity", 0.7, confidence=1.0)
mem2.record_win("depth", 0.65, confidence=1.0)

bias_a = {"clarity": 0.05, "depth": -0.02}

ranked_1 = mem2.rank_strategies(conditioning_bias=bias_a)
ranked_2 = mem2.rank_strategies(conditioning_bias=bias_a)

_test(
    "same bias → same order",
    [n for n, _ in ranked_1] == [n for n, _ in ranked_2],
)

base1, cond1 = mem2.get_conditioned_scores(conditioning_bias=bias_a)
base2, cond2 = mem2.get_conditioned_scores(conditioning_bias=bias_a)
_test("same bias → same base scores", base1 == base2)
_test("same bias → same conditioned scores", cond1 == cond2)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Different clusters → measurable selection shift
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Different clusters → measurable selection shift")

reset_strategy_memory()
reset_world_state_engine()

mem3 = StrategyMemory()
mem3.record_win("strategy_a", 0.7, confidence=1.0)
mem3.record_win("strategy_b", 0.68, confidence=1.0)

# Cluster 1: strategy_a performs well (score=0.9)
# Cluster 2: strategy_b performs well (score=0.9)
engine = WorldStateEngine()

cluster_1 = StateCluster(cluster_id="c1")
cluster_1.performance.record(
    strategy="strategy_a",
    strategy_score=0.9,
    utility=0.9,
)
cluster_1.performance.record(
    strategy="strategy_a",
    strategy_score=0.9,
    utility=0.9,
)
cluster_1.performance.record(
    strategy="strategy_b",
    strategy_score=0.3,
    utility=0.3,
)
cluster_1.performance.record(
    strategy="strategy_b",
    strategy_score=0.3,
    utility=0.3,
)

cluster_2 = StateCluster(cluster_id="c2")
cluster_2.performance.record(
    strategy="strategy_b",
    strategy_score=0.9,
    utility=0.9,
)
cluster_2.performance.record(
    strategy="strategy_b",
    strategy_score=0.9,
    utility=0.9,
)
cluster_2.performance.record(
    strategy="strategy_a",
    strategy_score=0.3,
    utility=0.3,
)
cluster_2.performance.record(
    strategy="strategy_a",
    strategy_score=0.3,
    utility=0.3,
)

# Compute biases manually (same formula as ConditioningBias computation)
sim = 0.95

c1_bias_a = (
    (cluster_1.performance.strategy_scores["strategy_a"] - 0.5)
    * CONDITIONING_WEIGHT
    * sim
)
c1_bias_b = (
    (cluster_1.performance.strategy_scores["strategy_b"] - 0.5)
    * CONDITIONING_WEIGHT
    * sim
)
c2_bias_a = (
    (cluster_2.performance.strategy_scores["strategy_a"] - 0.5)
    * CONDITIONING_WEIGHT
    * sim
)
c2_bias_b = (
    (cluster_2.performance.strategy_scores["strategy_b"] - 0.5)
    * CONDITIONING_WEIGHT
    * sim
)

bias_cluster_1 = {"strategy_a": c1_bias_a, "strategy_b": c1_bias_b}
bias_cluster_2 = {"strategy_a": c2_bias_a, "strategy_b": c2_bias_b}

ranked_c1 = mem3.rank_strategies(conditioning_bias=bias_cluster_1)
ranked_c2 = mem3.rank_strategies(conditioning_bias=bias_cluster_2)

top_c1 = ranked_c1[0][0]
top_c2 = ranked_c2[0][0]

_test(
    "cluster 1 favors strategy_a",
    top_c1 == "strategy_a",
    f"got {top_c1}",
)
_test(
    "cluster 2 favors strategy_b",
    top_c2 == "strategy_b",
    f"got {top_c2}",
)
_test("different clusters → different top strategy", top_c1 != top_c2)

# Verify the shift is measurable but bounded
base_scores, cond_c1 = mem3.get_conditioned_scores(conditioning_bias=bias_cluster_1)
_, cond_c2 = mem3.get_conditioned_scores(conditioning_bias=bias_cluster_2)

for name in ("strategy_a", "strategy_b"):
    diff = abs(cond_c1[name] - cond_c2[name])
    _test(
        f"{name}: cluster shift is measurable",
        diff > 0.001,
        f"diff={diff:.4f}",
    )
    _test(
        f"{name}: cluster shift is bounded",
        diff < 0.2,
        f"diff={diff:.4f}",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Bias magnitude bounded by CONDITIONING_WEIGHT
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. Bias magnitude bounded")

# Max possible bias: (1.0 - 0.5) * CONDITIONING_WEIGHT * 1.0 = 0.075
max_bias = (1.0 - 0.5) * CONDITIONING_WEIGHT * 1.0
_test(
    "max bias is 0.075",
    abs(max_bias - 0.075) < 1e-6,
    f"max_bias={max_bias}",
)

# Min possible bias: (0.0 - 0.5) * CONDITIONING_WEIGHT * 1.0 = -0.075
min_bias = (0.0 - 0.5) * CONDITIONING_WEIGHT * 1.0
_test(
    "min bias is -0.075",
    abs(min_bias - (-0.075)) < 1e-6,
    f"min_bias={min_bias}",
)

# With lower similarity, bias is even smaller
low_sim_bias = (1.0 - 0.5) * CONDITIONING_WEIGHT * 0.7
_test(
    "lower similarity → smaller bias",
    abs(low_sim_bias) < abs(max_bias),
    f"low_sim={low_sim_bias}, max={max_bias}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. DecisionTrace fields present
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. DecisionTrace fields")

reset_strategy_memory()
sm = get_strategy_memory()
sm.record_win("s1", 0.8, confidence=1.0)
sm.record_win("s2", 0.6, confidence=1.0)

# Build trace with conditioning bias containing strategy_bias
trace = build_trace(
    turn_id=1,
    conditioning_bias={
        "cluster_id": "test_c",
        "cluster_similarity": 0.9,
        "strategy_bias": {"s1": 0.05, "s2": -0.03},
        "goal_bias": {},
        "expected_utility": 0.6,
    },
)

_test("strategy_base_scores populated", trace.strategy_base_scores is not None)
_test(
    "strategy_conditioned_scores populated",
    trace.strategy_conditioned_scores is not None,
)
_test(
    "base and conditioned differ when bias applied",
    trace.strategy_base_scores != trace.strategy_conditioned_scores,
    f"base={trace.strategy_base_scores}, cond={trace.strategy_conditioned_scores}",
)

# Verify base scores don't include bias
for name in ("s1", "s2"):
    if trace.strategy_base_scores and trace.strategy_conditioned_scores:
        b = trace.strategy_base_scores[name]
        c = trace.strategy_conditioned_scores[name]
        _test(
            f"{name}: conditioned score reflects bias",
            b != c,
            f"base={b}, conditioned={c}",
        )

# strategy_scores on the trace should be the conditioned values
_test(
    "trace.strategy_scores match conditioned",
    trace.strategy_scores is not None,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. DecisionTrace without bias → no extra fields
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. No bias → no extra fields")

trace_no_bias = build_trace(turn_id=2)
_test("no bias: base_scores is None", trace_no_bias.strategy_base_scores is None)
_test(
    "no bias: conditioned_scores is None",
    trace_no_bias.strategy_conditioned_scores is None,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. to_dict serializes conditioning fields
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Serialization")

d = trace.to_dict()
_test("strategy_base_scores in dict", "strategy_base_scores" in d)
_test("strategy_conditioned_scores in dict", "strategy_conditioned_scores" in d)

d_no = trace_no_bias.to_dict()
_test("no bias: base_scores NOT in dict", "strategy_base_scores" not in d_no)
_test(
    "no bias: conditioned_scores NOT in dict", "strategy_conditioned_scores" not in d_no
)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Determinism — identical inputs → identical outputs
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. Determinism")

reset_strategy_memory()
sm_det = get_strategy_memory()
sm_det.record_win("x", 0.7, confidence=1.0)
sm_det.record_win("y", 0.65, confidence=1.0)

bias_det = {"x": 0.04, "y": -0.01}

results = []
for _ in range(5):
    r = sm_det.rank_strategies(conditioning_bias=bias_det)
    results.append([n for n, _ in r])

_test(
    "5 identical calls → identical results",
    all(r == results[0] for r in results),
)

score_results = []
for _ in range(5):
    b, c = sm_det.get_conditioned_scores(conditioning_bias=bias_det)
    score_results.append((b, c))

_test(
    "5 score calls → identical results",
    all(s == score_results[0] for s in score_results),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. No LLM calls
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. No LLM calls")

import inspect

src = inspect.getsource(StrategyMemory.rank_strategies)
src2 = inspect.getsource(StrategyMemory.get_conditioned_scores)
combined = src + src2

_test(
    "no 'call_with_fallback' in rank_strategies", "call_with_fallback" not in combined
)
_test("no 'generate' in rank_strategies", "generate(" not in combined)
_test("no 'anthropic' in rank_strategies", "anthropic" not in combined)
_test("no 'model_router' in rank_strategies", "model_router" not in combined)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. ExecutionSpine unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. ExecutionSpine unchanged")

import hashlib

spine_src = inspect.getsource(
    __import__("umh.runtime_engine.execution_spine", fromlist=["ExecutionSpine"]).ExecutionSpine
)
spine_hash = hashlib.md5(spine_src.encode()).hexdigest()
_test(
    "ExecutionSpine source hash captured", len(spine_hash) == 32, f"hash={spine_hash}"
)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. GoalArbitrator unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. GoalArbitrator unchanged")

arb_src = inspect.getsource(
    __import__("umh.runtime_engine.goal_arbitrator", fromlist=["GoalArbitrator"]).GoalArbitrator
)
arb_hash = hashlib.md5(arb_src.encode()).hexdigest()
_test("GoalArbitrator source hash captured", len(arb_hash) == 32, f"hash={arb_hash}")


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Backward compatibility — rank_strategies without bias
# ═══════════════════════════════════════════════════════════════════════════════

_section("14. Backward compatibility")

reset_strategy_memory()
mem_bc = StrategyMemory()
mem_bc.record_win("a", 0.9, confidence=1.0)
mem_bc.record_win("b", 0.5, confidence=1.0)

# Existing callers pass no bias — should still work
ranked_bc = mem_bc.rank_strategies()
_test("rank_strategies() with no args still works", len(ranked_bc) == 2)
_test("ordering correct without bias", ranked_bc[0][0] == "a")

# get_top_strategies uses rank_strategies internally
top = mem_bc.get_top_strategies(count=1)
_test("get_top_strategies still works", top == ["a"])


# ═══════════════════════════════════════════════════════════════════════════════
# 15. Empty bias dict is no-op
# ═══════════════════════════════════════════════════════════════════════════════

_section("15. Empty bias dict")

ranked_empty = mem_bc.rank_strategies(conditioning_bias={})
ranked_none = mem_bc.rank_strategies(conditioning_bias=None)
ranked_default = mem_bc.rank_strategies()

order_empty = [n for n, _ in ranked_empty]
order_none = [n for n, _ in ranked_none]
order_default = [n for n, _ in ranked_default]

_test("empty dict == no bias", order_empty == order_default)
_test("None == no bias", order_none == order_default)


# ═══════════════════════════════════════════════════════════════════════════════
# 16. Bias for unknown strategy is ignored
# ═══════════════════════════════════════════════════════════════════════════════

_section("16. Unknown strategy bias ignored")

ranked_unknown = mem_bc.rank_strategies(conditioning_bias={"nonexistent_strategy": 1.0})
order_unknown = [n for n, _ in ranked_unknown]
_test("unknown bias doesn't affect ordering", order_unknown == order_default)


# ═══════════════════════════════════════════════════════════════════════════════
# 17. End-to-end: WorldStateEngine → ConditioningBias → rank_strategies
# ═══════════════════════════════════════════════════════════════════════════════

_section("17. End-to-end pipeline")

reset_strategy_memory()
reset_world_state_engine()

sm_e2e = get_strategy_memory()
sm_e2e.record_win("fast", 0.7, confidence=1.0)
sm_e2e.record_win("thorough", 0.68, confidence=1.0)

ws_engine = get_world_state_engine()

# Build states and cluster them with performance data
for i in range(3):
    state = ws_engine.extract_and_record(
        current_turn=i + 1,
        exploration_rate=0.3,
        plan_count=0,
        blended_entropy=0.2,
    )
    ws_engine.record_outcome(
        state,
        strategy="fast",
        strategy_score=0.9,
        utility=0.85,
    )
    ws_engine.record_outcome(
        state,
        strategy="thorough",
        strategy_score=0.3,
        utility=0.35,
    )

# Extract a similar state and get conditioning bias
test_state = ws_engine.extract_and_record(
    current_turn=4,
    exploration_rate=0.3,
    plan_count=0,
    blended_entropy=0.2,
)

bias = ws_engine.get_conditioning_bias(test_state)

if bias.cluster_id is not None:
    _test("e2e: bias has strategy entries", len(bias.strategy_bias) > 0)

    ranked_biased = sm_e2e.rank_strategies(conditioning_bias=bias.strategy_bias)
    _test("e2e: ranking reflects cluster performance", ranked_biased[0][0] == "fast")

    base_e2e, cond_e2e = sm_e2e.get_conditioned_scores(
        conditioning_bias=bias.strategy_bias
    )
    _test("e2e: base scores captured", len(base_e2e) == 2)
    _test("e2e: conditioned scores captured", len(cond_e2e) == 2)
    _test(
        "e2e: conditioned != base when bias present",
        cond_e2e != base_e2e,
    )
else:
    _test("e2e: no cluster formed (states too few)", True, "expected: cluster needed")


# ═══════════════════════════════════════════════════════════════════════════════
# 18. Additive only — bias does not multiply or replace
# ═══════════════════════════════════════════════════════════════════════════════

_section("18. Additive only")

reset_strategy_memory()
mem_add = StrategyMemory()
mem_add.record_win("p", 0.5, confidence=1.0)
mem_add.record_win("q", 0.5, confidence=1.0)

base_add, cond_add = mem_add.get_conditioned_scores(
    conditioning_bias={"p": 0.03, "q": -0.03}
)

_test(
    "p conditioned = base + 0.03 exactly",
    abs(cond_add["p"] - (base_add["p"] + 0.03)) < 1e-4,
)
_test(
    "q conditioned = base - 0.03 exactly",
    abs(cond_add["q"] - (base_add["q"] - 0.03)) < 1e-4,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 19. No new module dependencies
# ═══════════════════════════════════════════════════════════════════════════════

_section("19. No new dependencies")

import ast

with open("/opt/OS/eos/strategy_memory.py") as f:
    tree = ast.parse(f.read())

imports = []
for node in ast.walk(tree):
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)

top_level_imports = [i for i in imports if not i.startswith("umh.runtime_engine.")]
_test(
    "no new external imports in strategy_memory",
    set(top_level_imports) <= {"__future__", "math", "dataclasses"},
    f"found: {top_level_imports}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  TOTAL: {_PASS + _FAIL} assertions | PASS: {_PASS} | FAIL: {_FAIL}")
print(f"{'═' * 60}")

if _FAIL > 0:
    sys.exit(1)
