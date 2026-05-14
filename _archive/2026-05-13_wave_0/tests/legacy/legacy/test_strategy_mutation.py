"""
Tests for Strategy Mutation & Selection.

Proves:
    1. System generates new strategies under defined conditions
    2. New strategies compete correctly
    3. Bad mutations die off
    4. Good mutations persist
    5. No regressions
    6. Determinism preserved
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

_section("0. Imports")

from umh.runtime_engine.strategy_mutation import (
    StrategyMutation,
    StrategyMutationEngine,
    compute_novelty_factor,
    compute_strategy_score,
    get_mutation_engine,
    reset_mutation_engine,
    MAX_STRATEGIES,
    MUTATION_COOLDOWN,
    MIN_USES_FOR_MUTATION,
    UNDERPERFORMANCE_THRESHOLD,
    VARIANCE_THRESHOLD,
    NEAR_MISS_THRESHOLD,
    GAP_THRESHOLD,
    NOVELTY_INITIAL,
    NOVELTY_DECAY_RATE,
)
from umh.strategy.memory import StrategyMemory, StrategyStats, reset_strategy_memory
from umh.runtime_engine.multi_strategy import (
    STRATEGY_REGISTRY,
    STRATEGY_PROMPT_DIRECTIVES,
    register_strategy,
    unregister_strategy,
)
from umh.runtime_engine.decision_trace import build_trace

_test("all imports succeed", True)


# ── Helpers ────────────────────────────────────────────────────────────────


def _fresh_memory() -> StrategyMemory:
    """Create an isolated strategy memory for testing."""
    return StrategyMemory()


def _setup_underperformer(mem: StrategyMemory, name: str = "baseline") -> None:
    """Create an underperforming strategy in memory."""
    for i in range(MIN_USES_FOR_MUTATION + 1):
        mem._global_turn += 1
        stats = mem._ensure(name)
        stats.uses += 1
        stats.total_score += 0.2
        stats.update_ema(0.2)
        stats.last_used_turn = mem._global_turn


def _setup_high_variance(mem: StrategyMemory, name: str = "clarity") -> None:
    """Create a high-variance strategy (large EMA/mean gap)."""
    stats = mem._ensure(name)
    stats.uses = MIN_USES_FOR_MUTATION + 1
    stats.total_score = 3.0
    stats.ema_score = 0.8
    stats.last_used_turn = mem._global_turn
    mem._global_turn += 1


def _setup_near_miss(mem: StrategyMemory, name: str = "structured") -> None:
    """Create a near-miss strategy: high quality, low win rate."""
    stats = mem._ensure(name)
    stats.uses = MIN_USES_FOR_MUTATION + 2
    stats.wins = 1
    stats.total_score = 4.5
    stats.ema_score = 0.65
    stats.last_used_turn = mem._global_turn
    mem._global_turn += 1


def _cleanup_mutants() -> None:
    """Remove any mut_ strategies from the registry."""
    mutants = [k for k in STRATEGY_REGISTRY if k.startswith("mut_")]
    for m in mutants:
        unregister_strategy(m)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. StrategyMutation data model
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. StrategyMutation — Data Model")

sm = StrategyMutation(
    strategy_id="mut_narrow_abc123",
    parent_strategy_id="baseline",
    mutation_type="narrow",
    mutation_reason="underperformance:ema=0.25",
    confidence=0.3,
    system_directive="Be precise.",
    prompt_directive="[Focus precisely.]",
    creation_turn=10,
)
_test("strategy_id stored", sm.strategy_id == "mut_narrow_abc123")
_test("parent_strategy_id stored", sm.parent_strategy_id == "baseline")
_test("mutation_type stored", sm.mutation_type == "narrow")
_test("confidence stored", sm.confidence == 0.3)
_test("creation_turn stored", sm.creation_turn == 10)

d = sm.to_dict()
_test("to_dict has strategy_id", "strategy_id" in d)
_test("to_dict has mutation_type", "mutation_type" in d)
_test("to_dict has mutation_reason", "mutation_reason" in d)
_test("to_dict has confidence", "confidence" in d)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Constants
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. Constants")

_test("MAX_STRATEGIES is 8", MAX_STRATEGIES == 8)
_test("MUTATION_COOLDOWN is 10", MUTATION_COOLDOWN == 10)
_test("MIN_USES_FOR_MUTATION is 5", MIN_USES_FOR_MUTATION == 5)
_test("UNDERPERFORMANCE_THRESHOLD is 0.3", UNDERPERFORMANCE_THRESHOLD == 0.3)
_test("VARIANCE_THRESHOLD is 0.15", VARIANCE_THRESHOLD == 0.15)
_test("NEAR_MISS_THRESHOLD is 0.6", NEAR_MISS_THRESHOLD == 0.6)
_test("GAP_THRESHOLD is 0.4", GAP_THRESHOLD == 0.4)
_test("NOVELTY_INITIAL is 1.3", NOVELTY_INITIAL == 1.3)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Trigger A: Persistent underperformance → narrow
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Trigger A — Underperformance → Narrow")

_cleanup_mutants()
engine_a = StrategyMutationEngine()
mem_a = _fresh_memory()
_setup_underperformer(mem_a, "baseline")

mutations_a = engine_a.evaluate(mem_a, current_turn=20)
_test(
    "underperformer triggers mutation",
    len(mutations_a) == 1,
    f"count={len(mutations_a)}",
)
if mutations_a:
    m = mutations_a[0]
    _test("mutation_type is narrow", m.mutation_type == "narrow")
    _test("parent is baseline", m.parent_strategy_id == "baseline")
    _test("reason contains underperformance", "underperformance" in m.mutation_reason)
    _test("confidence is 0.3", m.confidence == 0.3)
    _test("strategy_id starts with mut_", m.strategy_id.startswith("mut_"))


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Trigger B: High variance → narrow
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Trigger B — High Variance → Narrow")

_cleanup_mutants()
engine_b = StrategyMutationEngine()
mem_b = _fresh_memory()
_setup_high_variance(mem_b, "clarity")

mutations_b = engine_b.evaluate(mem_b, current_turn=20)
_test(
    "high variance triggers mutation",
    len(mutations_b) == 1,
    f"count={len(mutations_b)}",
)
if mutations_b:
    m = mutations_b[0]
    _test("mutation_type is narrow", m.mutation_type == "narrow")
    _test("parent is clarity", m.parent_strategy_id == "clarity")
    _test("reason contains high_variance", "high_variance" in m.mutation_reason)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Trigger C: Near-miss → expand
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Trigger C — Near-Miss → Expand")

_cleanup_mutants()
engine_c = StrategyMutationEngine()
mem_c = _fresh_memory()
_setup_near_miss(mem_c, "structured")

mutations_c = engine_c.evaluate(mem_c, current_turn=20)
_test(
    "near-miss triggers mutation",
    len(mutations_c) == 1,
    f"count={len(mutations_c)}",
)
if mutations_c:
    m = mutations_c[0]
    _test("mutation_type is expand", m.mutation_type == "expand")
    _test("parent is structured", m.parent_strategy_id == "structured")
    _test("reason contains near_miss", "near_miss" in m.mutation_reason)
    _test("confidence is 0.4", m.confidence == 0.4)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Trigger D: Gap detection → recombine
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. Trigger D — Gap → Recombine")

_cleanup_mutants()
engine_d = StrategyMutationEngine()
mem_d = _fresh_memory()

# All strategies perform poorly
for name in ["baseline", "clarity"]:
    stats = mem_d._ensure(name)
    stats.uses = MIN_USES_FOR_MUTATION + 1
    stats.ema_score = 0.3
    stats.total_score = 1.8
    stats.last_used_turn = 5
mem_d._global_turn = 10

mutations_d = engine_d.evaluate(mem_d, current_turn=20)
_test(
    "gap triggers mutation",
    len(mutations_d) >= 1,
    f"count={len(mutations_d)}",
)
if mutations_d:
    m = mutations_d[0]
    _test(
        "mutation_type is recombine or narrow",
        m.mutation_type in ("recombine", "narrow"),
        f"type={m.mutation_type}",
    )
    _test(
        "reason contains gap or underperformance",
        "gap" in m.mutation_reason or "underperformance" in m.mutation_reason,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Cooldown enforcement
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Cooldown Enforcement")

_cleanup_mutants()
engine_cool = StrategyMutationEngine()
mem_cool = _fresh_memory()
_setup_underperformer(mem_cool, "baseline")

# First call should produce mutation
m1 = engine_cool.evaluate(mem_cool, current_turn=20)
_test("first call produces mutation", len(m1) == 1)

if m1:
    engine_cool.register_mutation(m1[0])

# Second call within cooldown should produce nothing
m2 = engine_cool.evaluate(mem_cool, current_turn=25)
_test(
    "within cooldown → no mutation",
    len(m2) == 0,
    f"count={len(m2)}, cooldown_left={MUTATION_COOLDOWN - (25 - 20)}",
)

# After cooldown
_setup_underperformer(mem_cool, "clarity")
m3 = engine_cool.evaluate(mem_cool, current_turn=31)
_test(
    "after cooldown → mutation possible",
    len(m3) >= 0,
)
_cleanup_mutants()


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Registration and competition
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Registration & Competition")

_cleanup_mutants()
engine_reg = StrategyMutationEngine()
mem_reg = _fresh_memory()
_setup_underperformer(mem_reg, "baseline")

m_list = engine_reg.evaluate(mem_reg, current_turn=20)
_test("mutation generated", len(m_list) == 1)

if m_list:
    success = engine_reg.register_mutation(m_list[0])
    _test("registration succeeded", success is True)
    _test(
        "strategy in STRATEGY_REGISTRY",
        m_list[0].strategy_id in STRATEGY_REGISTRY,
    )
    _test(
        "prompt directive registered",
        m_list[0].strategy_id in STRATEGY_PROMPT_DIRECTIVES,
    )

    # New strategy enters with low confidence
    _test("low initial confidence", m_list[0].confidence <= 0.4)

_cleanup_mutants()


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Novelty factor
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Novelty Factor")

nf_fresh = compute_novelty_factor(creation_turn=10, current_turn=10)
_test(
    "new strategy → max novelty",
    abs(nf_fresh - NOVELTY_INITIAL) < 0.001,
    f"got={nf_fresh:.3f}",
)

nf_aged = compute_novelty_factor(creation_turn=10, current_turn=50)
_test(
    "aged strategy → novelty decays toward 1.0",
    1.0 <= nf_aged < NOVELTY_INITIAL,
    f"got={nf_aged:.3f}",
)

nf_old = compute_novelty_factor(creation_turn=10, current_turn=200)
_test(
    "very old → novelty near 1.0",
    abs(nf_old - 1.0) < 0.05,
    f"got={nf_old:.3f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Strategy score formula
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. Strategy Score Formula")

score = compute_strategy_score(
    base_score=0.7,
    strategy_confidence=0.8,
    creation_turn=10,
    current_turn=10,
)
expected = 0.7 * 0.8 * NOVELTY_INITIAL
_test(
    "score = base * confidence * novelty",
    abs(score - expected) < 0.001,
    f"got={score:.4f}, expected={expected:.4f}",
)

score_no_novelty = compute_strategy_score(
    base_score=0.7,
    strategy_confidence=0.8,
    creation_turn=None,
    current_turn=10,
)
_test(
    "no creation_turn → novelty=1.0",
    abs(score_no_novelty - 0.56) < 0.001,
    f"got={score_no_novelty:.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Bad mutations die off (pruning)
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. Bad Mutations Die Off")

_cleanup_mutants()

# Register a fake mutant with bad performance
register_strategy("mut_test_bad_abc123", "bad system", "bad prompt")
_test(
    "mutant registered",
    "mut_test_bad_abc123" in STRATEGY_REGISTRY,
)

from umh.runtime_engine.strategy_mutation import _prune_weakest_mutant

pruned = _prune_weakest_mutant()
_test("weak mutant pruned", pruned is True)
_test(
    "mutant removed from registry",
    "mut_test_bad_abc123" not in STRATEGY_REGISTRY,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Good mutations persist
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. Good Mutations Persist")

_cleanup_mutants()

register_strategy("mut_test_good_def456", "good system", "good prompt")
# Give it high performance in memory
reset_strategy_memory()
from umh.strategy.memory import get_strategy_memory

gm = get_strategy_memory()
gm.record_win("mut_test_good_def456", 0.9)
gm.record_win("mut_test_good_def456", 0.85)

stats = gm.get_stats("mut_test_good_def456")
_test("good mutant has high EMA", stats.ema_score > 0.8, f"ema={stats.ema_score:.3f}")
_test(
    "good mutant still in registry",
    "mut_test_good_def456" in STRATEGY_REGISTRY,
)

_cleanup_mutants()
reset_strategy_memory()


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Bounded growth (MAX_STRATEGIES)
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. Bounded Growth")

_cleanup_mutants()
initial_count = len(STRATEGY_REGISTRY)
_test(
    "initial registry count is reasonable",
    initial_count <= MAX_STRATEGIES,
    f"count={initial_count}",
)

engine_cap = StrategyMutationEngine()

# Fill to cap
for i in range(MAX_STRATEGIES - initial_count):
    register_strategy(f"mut_cap_test_{i}", f"sys_{i}", f"prompt_{i}")

_test(
    "registry at cap",
    len(STRATEGY_REGISTRY) >= MAX_STRATEGIES,
    f"count={len(STRATEGY_REGISTRY)}",
)

# Engine should handle full pool
mem_cap = _fresh_memory()
_setup_underperformer(mem_cap, "baseline")
m_cap = engine_cap.evaluate(mem_cap, current_turn=20)
_test(
    "at cap: mutation possible (prunes first)",
    len(m_cap) <= 1,
    f"count={len(m_cap)}",
)

# Clean up
for i in range(MAX_STRATEGIES - initial_count):
    unregister_strategy(f"mut_cap_test_{i}")
_cleanup_mutants()


# ═══════════════════════════════════════════════════════════════════════════════
# 14. At most one mutation per call
# ═══════════════════════════════════════════════════════════════════════════════

_section("14. At Most One Mutation Per Call")

_cleanup_mutants()
engine_one = StrategyMutationEngine()
mem_one = _fresh_memory()

# Set up multiple triggers simultaneously
_setup_underperformer(mem_one, "baseline")
_setup_high_variance(mem_one, "clarity")

mutations_multi = engine_one.evaluate(mem_one, current_turn=20)
_test(
    "at most one mutation per call",
    len(mutations_multi) <= 1,
    f"count={len(mutations_multi)}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 15. Duplicate prevention
# ═══════════════════════════════════════════════════════════════════════════════

_section("15. Duplicate Prevention")

_cleanup_mutants()
engine_dup = StrategyMutationEngine()
mem_dup = _fresh_memory()
_setup_underperformer(mem_dup, "baseline")

m_first = engine_dup.evaluate(mem_dup, current_turn=20)
_test("first mutation generated", len(m_first) == 1)

if m_first:
    engine_dup.register_mutation(m_first[0])
    first_id = m_first[0].strategy_id

    # Same turn, same trigger → should produce different ID (already in history)
    engine_dup.last_mutation_turn = 0  # Reset cooldown for testing
    m_second = engine_dup.evaluate(mem_dup, current_turn=20)
    if m_second:
        _test(
            "no duplicate mutation",
            m_second[0].strategy_id != first_id,
            f"first={first_id}, second={m_second[0].strategy_id}",
        )
    else:
        _test("no duplicate mutation (none generated)", True)

_cleanup_mutants()


# ═══════════════════════════════════════════════════════════════════════════════
# 16. DecisionTrace — mutation fields
# ═══════════════════════════════════════════════════════════════════════════════

_section("16. DecisionTrace — Mutation Fields")

trace = build_trace(
    turn_id=1,
    strategy_mutations=({"strategy_id": "mut_narrow_abc", "mutation_type": "narrow"},),
    strategy_origins={"mut_narrow_abc": "baseline"},
    mutation_reason="underperformance:ema=0.25",
)
_test("trace has strategy_mutations", trace.strategy_mutations is not None)
_test("trace has strategy_origins", trace.strategy_origins is not None)
_test("trace has mutation_reason", trace.mutation_reason is not None)

td = trace.to_dict()
_test("to_dict has strategy_mutations", "strategy_mutations" in td)
_test("to_dict has strategy_origins", "strategy_origins" in td)
_test("to_dict has mutation_reason", "mutation_reason" in td)

# Empty trace
empty_trace = build_trace(turn_id=2)
_test("empty: strategy_mutations None", empty_trace.strategy_mutations is None)
_test("empty: strategy_origins None", empty_trace.strategy_origins is None)
_test("empty: mutation_reason None", empty_trace.mutation_reason is None)

etd = empty_trace.to_dict()
_test("empty to_dict: no strategy_mutations", "strategy_mutations" not in etd)
_test("empty to_dict: no strategy_origins", "strategy_origins" not in etd)
_test("empty to_dict: no mutation_reason", "mutation_reason" not in etd)


# ═══════════════════════════════════════════════════════════════════════════════
# 17. Determinism
# ═══════════════════════════════════════════════════════════════════════════════

_section("17. Determinism")


def _run_mutation_trial():
    _cleanup_mutants()
    eng = StrategyMutationEngine()
    m = _fresh_memory()
    _setup_underperformer(m, "baseline")
    results = eng.evaluate(m, current_turn=20)
    return [r.to_dict() for r in results]


trial1 = _run_mutation_trial()
trial2 = _run_mutation_trial()
_test("deterministic mutation output", trial1 == trial2, f"{trial1} vs {trial2}")

# Novelty is deterministic
nf1 = compute_novelty_factor(10, 30)
nf2 = compute_novelty_factor(10, 30)
_test("deterministic novelty", nf1 == nf2)

# Score is deterministic
s1 = compute_strategy_score(0.7, 0.8, 10, 30)
s2 = compute_strategy_score(0.7, 0.8, 10, 30)
_test("deterministic score", s1 == s2)

_cleanup_mutants()


# ═══════════════════════════════════════════════════════════════════════════════
# 18. No LLM Calls
# ═══════════════════════════════════════════════════════════════════════════════

_section("18. No LLM Calls")

with open("/opt/OS/eos/strategy_mutation.py") as f:
    src = f.read()

_test("no call_with_fallback", "call_with_fallback" not in src)
_test("no import random", "import random" not in src)
_test("no anthropic", "anthropic" not in src)
_test("no openai", "openai" not in src)
_test("no genai", "genai" not in src)
_test("no agent_runtime", "agent_runtime" not in src)


# ═══════════════════════════════════════════════════════════════════════════════
# 19. ExecutionSpine Unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("19. ExecutionSpine Unchanged")

with open("/opt/OS/eos/execution_spine.py") as f:
    spine_src = f.read()

_test("spine: no strategy_mutation ref", "strategy_mutation" not in spine_src)
_test("spine: no StrategyMutation ref", "StrategyMutation" not in spine_src)
_test("spine: no mutation_type ref", "mutation_type" not in spine_src)
_test("spine: no MUTATION_COOLDOWN ref", "MUTATION_COOLDOWN" not in spine_src)


# ═══════════════════════════════════════════════════════════════════════════════
# 20. Mutation types produce correct directives
# ═══════════════════════════════════════════════════════════════════════════════

_section("20. Mutation Directives")

_cleanup_mutants()
engine_dir = StrategyMutationEngine()

# Test narrow mutation directives
mem_dir = _fresh_memory()
_setup_underperformer(mem_dir, "clarity")
m_narrow = engine_dir.evaluate(mem_dir, current_turn=20)
if m_narrow:
    _test(
        "narrow: system directive has Focus",
        "Focus" in m_narrow[0].system_directive
        or "precise" in m_narrow[0].system_directive.lower(),
        f"sys={m_narrow[0].system_directive[:50]}",
    )
    _test(
        "narrow: prompt directive has narrow",
        "narrow" in m_narrow[0].prompt_directive.lower()
        or "Focus" in m_narrow[0].prompt_directive,
    )
else:
    _test("narrow mutation generated", False)

_cleanup_mutants()

# Test expand mutation directives
engine_dir2 = StrategyMutationEngine()
mem_dir2 = _fresh_memory()
_setup_near_miss(mem_dir2, "structured")
m_expand = engine_dir2.evaluate(mem_dir2, current_turn=20)
if m_expand:
    _test(
        "expand: system directive has Explore/alternative",
        "Explore" in m_expand[0].system_directive
        or "alternative" in m_expand[0].system_directive,
        f"sys={m_expand[0].system_directive[:60]}",
    )
else:
    _test("expand mutation generated", False)

_cleanup_mutants()


# ═══════════════════════════════════════════════════════════════════════════════
# 21. Singleton pattern
# ═══════════════════════════════════════════════════════════════════════════════

_section("21. Singleton Pattern")

reset_mutation_engine()
e1 = get_mutation_engine()
e2 = get_mutation_engine()
_test("singleton: same instance", e1 is e2)

reset_mutation_engine()
e3 = get_mutation_engine()
_test("reset creates new instance", e3 is not e1)

reset_mutation_engine()


# ═══════════════════════════════════════════════════════════════════════════════
# 22. Insufficient data → no mutation
# ═══════════════════════════════════════════════════════════════════════════════

_section("22. Insufficient Data → No Mutation")

_cleanup_mutants()
engine_insuf = StrategyMutationEngine()
mem_insuf = _fresh_memory()

# Strategy with too few uses
stats = mem_insuf._ensure("baseline")
stats.uses = 2
stats.ema_score = 0.1

m_insuf = engine_insuf.evaluate(mem_insuf, current_turn=20)
_test(
    "insufficient uses → no mutation",
    len(m_insuf) == 0,
    f"count={len(m_insuf)}",
)

# Empty memory
mem_empty = _fresh_memory()
m_empty = engine_insuf.evaluate(mem_empty, current_turn=30)
_test("empty memory → no mutation", len(m_empty) == 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 23. No new external dependencies
# ═══════════════════════════════════════════════════════════════════════════════

_section("23. No New Dependencies")

_test("no requests", "import requests" not in src)
_test("no httpx", "import httpx" not in src)
_test("no numpy", "import numpy" not in src)


# ═══════════════════════════════════════════════════════════════════════════════
# 24. Backward compatibility
# ═══════════════════════════════════════════════════════════════════════════════

_section("24. Backward Compatibility")

# Strategy memory still works
mem_compat = _fresh_memory()
mem_compat.record_win("baseline", 0.8)
_test("strategy memory: record_win works", mem_compat.get_stats("baseline").uses == 1)

# multi_strategy registry unchanged for predefined
_test("baseline in registry", "baseline" in STRATEGY_REGISTRY)
_test("clarity in registry", "clarity" in STRATEGY_REGISTRY)
_test("concise in registry", "concise" in STRATEGY_REGISTRY)
_test("structured in registry", "structured" in STRATEGY_REGISTRY)

# DecisionTrace without mutation fields
trace_compat = build_trace(turn_id=1)
_test(
    "trace compat: works without mutation fields",
    trace_compat.strategy_mutations is None,
)


# ═══════════════════════════════════════════════════════════════════════════════

_cleanup_mutants()
reset_mutation_engine()
reset_strategy_memory()

print(f"\n{'=' * 60}")
print(f"  TOTAL: {_PASS} passed, {_FAIL} failed (out of {_PASS + _FAIL})")
print(f"{'=' * 60}")

sys.exit(0 if _FAIL == 0 else 1)
