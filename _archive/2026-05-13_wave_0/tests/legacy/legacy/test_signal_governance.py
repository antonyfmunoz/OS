"""
Tests for Signal Governance Layer.

Validates:
    - Stale strategies get selected periodically (anti-collapse)
    - Low-confidence evaluations do NOT update strategy stats
    - Directive count never exceeds MAX_DIRECTIVES
    - EMA updates correctly
    - Deterministic ordering preserved
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


from umh.strategy.memory import (
    EMA_ALPHA,
    MIN_CONFIDENCE,
    StrategyStats,
    StrategyMemory,
    get_strategy_memory,
    reset_strategy_memory,
)
from umh.runtime_engine.adaptive_prompt import (
    MAX_DIRECTIVES,
    PRIORITY_CRITICAL,
    PRIORITY_LOW_QUALITY,
    PRIORITY_WORLD_MODEL,
    adapt_prompt,
)
from umh.runtime_engine.multi_strategy import (
    STALE_THRESHOLD,
    STRATEGY_REGISTRY,
    pick_strategies,
    select_best,
    CandidateResult,
)


def _make_candidate(
    output: str,
    strategy: str = "baseline",
    quality: float = 0.7,
    confidence: float = 0.8,
) -> CandidateResult:
    return CandidateResult(
        output=output,
        strategy_name=strategy,
        quality_score=quality,
        confidence=confidence,
        evaluation={"quality_score": quality, "confidence": confidence, "flags": {}},
        model_used="test/test-model",
        tokens_used=100,
        cost_usd=0.001,
        latency_ms=200,
    )


# ═════════════════════════════════════════════════════════════════════════════
# 1. EMA scoring
# ═════════════════════════════════════════════════════════════════════════════

_section("1. EMA Scoring")
reset_strategy_memory()

stats = StrategyStats(name="test")

stats.uses = 1
stats.update_ema(0.8)
_test(
    "first update sets EMA directly",
    abs(stats.ema_score - 0.8) < 0.001,
    f"ema={stats.ema_score}",
)

stats.uses = 2
stats.update_ema(0.4)
expected = (EMA_ALPHA * 0.4) + ((1 - EMA_ALPHA) * 0.8)
_test(
    "second update uses weighted average",
    abs(stats.ema_score - expected) < 0.001,
    f"ema={stats.ema_score}, expected={expected}",
)

stats.uses = 3
stats.update_ema(0.4)
expected2 = (EMA_ALPHA * 0.4) + ((1 - EMA_ALPHA) * expected)
_test(
    "third update continues EMA chain",
    abs(stats.ema_score - expected2) < 0.001,
    f"ema={stats.ema_score}, expected={expected2}",
)

_test(
    "avg_score returns ema_score",
    abs(stats.avg_score - stats.ema_score) < 0.001,
    f"avg={stats.avg_score}, ema={stats.ema_score}",
)

stats_zero = StrategyStats(name="empty")
_test(
    "avg_score is 0.0 when no uses",
    stats_zero.avg_score == 0.0,
)

_test(
    "to_dict includes ema_score and last_used_turn",
    "ema_score" in stats.to_dict() and "last_used_turn" in stats.to_dict(),
)


# ═════════════════════════════════════════════════════════════════════════════
# 2. Confidence gating
# ═════════════════════════════════════════════════════════════════════════════

_section("2. Confidence Gating")
reset_strategy_memory()

mem = get_strategy_memory()

mem.record_win("clarity", 0.9, confidence=0.3)
s = mem.get_stats("clarity")
_test(
    "low-confidence win does NOT update uses",
    s is not None and s.uses == 0,
    f"uses={s.uses if s else 'None'}",
)

mem.record_win("clarity", 0.9, confidence=0.7)
s = mem.get_stats("clarity")
_test(
    "high-confidence win DOES update uses",
    s is not None and s.uses == 1,
    f"uses={s.uses if s else 'None'}",
)

mem.record_loss("baseline", 0.5, confidence=0.4)
s = mem.get_stats("baseline")
_test(
    "low-confidence loss does NOT update uses",
    s is None or s.uses == 0,
    f"uses={s.uses if s else '0 (None)'}",
)

mem.record_loss("baseline", 0.5, confidence=0.8)
s = mem.get_stats("baseline")
_test(
    "high-confidence loss DOES update uses",
    s is not None and s.uses == 1,
    f"uses={s.uses if s else 'None'}",
)

_test(
    "MIN_CONFIDENCE constant is 0.6",
    MIN_CONFIDENCE == 0.6,
    f"MIN_CONFIDENCE={MIN_CONFIDENCE}",
)


# ═════════════════════════════════════════════════════════════════════════════
# 3. Strategy floor (anti-collapse via staleness)
# ═════════════════════════════════════════════════════════════════════════════

_section("3. Strategy Floor (Anti-Collapse)")
reset_strategy_memory()

mem = get_strategy_memory()

for _ in range(STALE_THRESHOLD + 1):
    mem.record_win("baseline", 0.9, confidence=0.8)

stale = mem.get_stale_strategy(
    known_strategies=list(STRATEGY_REGISTRY.keys()),
    stale_threshold=STALE_THRESHOLD,
)
_test(
    "stale strategy detected after threshold exceeded",
    stale is not None and stale != "baseline",
    f"stale={stale}",
)

no_stale = mem.get_stale_strategy(
    known_strategies=["baseline"],
    stale_threshold=STALE_THRESHOLD,
)
_test(
    "no stale when only strategy is active",
    no_stale is None,
    f"result={no_stale}",
)

reset_strategy_memory()
mem = get_strategy_memory()

for _ in range(STALE_THRESHOLD + 1):
    mem.record_win("baseline", 0.9, confidence=0.8)
    mem.record_loss("clarity", 0.5, confidence=0.8)

stale_after_both = mem.get_stale_strategy(
    known_strategies=list(STRATEGY_REGISTRY.keys()),
    stale_threshold=STALE_THRESHOLD,
)
_test(
    "never-used strategies are stale",
    stale_after_both is not None,
    f"stale={stale_after_both}",
)


# ═════════════════════════════════════════════════════════════════════════════
# 4. pick_strategies includes stale strategy
# ═════════════════════════════════════════════════════════════════════════════

_section("4. pick_strategies with Staleness")
reset_strategy_memory()

mem = get_strategy_memory()
for _ in range(STALE_THRESHOLD + 1):
    mem.record_win("baseline", 0.9, confidence=0.8)

picked = pick_strategies(num_candidates=2)
_test(
    "picks include 2 strategies",
    len(picked) == 2,
    f"picked={picked}",
)
_test(
    "top strategy is baseline",
    picked[0] == "baseline",
    f"first={picked[0]}",
)
_test(
    "second strategy is not baseline (stale rotation)",
    picked[1] != "baseline",
    f"second={picked[1]}",
)


# ═════════════════════════════════════════════════════════════════════════════
# 5. Directive cap (MAX_DIRECTIVES)
# ═════════════════════════════════════════════════════════════════════════════

_section("5. Directive Cap")

_test(
    "MAX_DIRECTIVES is 3",
    MAX_DIRECTIVES == 3,
    f"MAX_DIRECTIVES={MAX_DIRECTIVES}",
)


class FakeSessionStats:
    def __init__(self, evaluations):
        self.evaluations = evaluations


class FakeSessionRuntime:
    def __init__(self, evaluations):
        self.stats = FakeSessionStats(evaluations)


bad_evals = [
    {
        "quality_score": 0.2,
        "flags": {
            "hallucination_risk": True,
            "incomplete": True,
            "low_information": True,
        },
    }
] * 3

session = FakeSessionRuntime(bad_evals)

adapted = adapt_prompt(
    base_prompt="Base prompt.",
    context={"agent_type": "test"},
    session_runtime=session,
    world_model=None,
)

directive_lines = [
    l for l in adapted.split("\n") if l.startswith("- ") and "Adaptive" not in l
]
_test(
    "directive count capped at MAX_DIRECTIVES",
    len(directive_lines) <= MAX_DIRECTIVES,
    f"got {len(directive_lines)} directives",
)


# ═════════════════════════════════════════════════════════════════════════════
# 6. Directive priority ordering
# ═════════════════════════════════════════════════════════════════════════════

_section("6. Directive Priority Ordering")

_test(
    "CRITICAL < LOW_QUALITY < WORLD_MODEL",
    PRIORITY_CRITICAL < PRIORITY_LOW_QUALITY < PRIORITY_WORLD_MODEL,
    f"{PRIORITY_CRITICAL} < {PRIORITY_LOW_QUALITY} < {PRIORITY_WORLD_MODEL}",
)

halluc_evals = [
    {
        "quality_score": 0.2,
        "flags": {"hallucination_risk": True, "low_information": True},
    }
] * 3
session_halluc = FakeSessionRuntime(halluc_evals)
adapted_halluc = adapt_prompt(
    base_prompt="Base.",
    context={},
    session_runtime=session_halluc,
)

_test(
    "hallucination directive appears first",
    "hallucination" in adapted_halluc.split("\n")[1].lower(),
    adapted_halluc.split("\n")[1][:80],
)


# ═════════════════════════════════════════════════════════════════════════════
# 7. Deduplication
# ═════════════════════════════════════════════════════════════════════════════

_section("7. Directive Deduplication")

identical_evals = [{"quality_score": 0.2, "flags": {"hallucination_risk": True}}] * 6
session_dup = FakeSessionRuntime(identical_evals)
adapted_dup = adapt_prompt(
    base_prompt="Base.",
    context={},
    session_runtime=session_dup,
)

dup_lines = [l for l in adapted_dup.split("\n") if l.startswith("- ")]
unique_lines = set(dup_lines)
_test(
    "no duplicate directives",
    len(dup_lines) == len(unique_lines),
    f"total={len(dup_lines)}, unique={len(unique_lines)}",
)


# ═════════════════════════════════════════════════════════════════════════════
# 8. No adaptation returns base prompt unchanged
# ═════════════════════════════════════════════════════════════════════════════

_section("8. No-Op Returns Base Unchanged")

no_change = adapt_prompt(
    base_prompt="Original prompt.",
    context={},
    session_runtime=None,
    world_model=None,
)
_test(
    "no signals → base prompt unchanged",
    no_change == "Original prompt.",
)

good_evals = [{"quality_score": 0.9, "flags": {}}] * 3
session_good = FakeSessionRuntime(good_evals)
no_change2 = adapt_prompt(
    base_prompt="Original prompt.",
    context={},
    session_runtime=session_good,
)
_test(
    "high-quality session → no directives injected",
    no_change2 == "Original prompt.",
)


# ═════════════════════════════════════════════════════════════════════════════
# 9. select_best passes confidence through
# ═════════════════════════════════════════════════════════════════════════════

_section("9. Confidence Passthrough in select_best")
reset_strategy_memory()

low_conf_a = _make_candidate("A", "baseline", quality=0.9, confidence=0.3)
low_conf_b = _make_candidate("B", "clarity", quality=0.4, confidence=0.3)

winner = select_best([low_conf_a, low_conf_b])
_test("winner selected", winner is not None and winner.strategy_name == "baseline")

mem = get_strategy_memory()
stats_a = mem.get_stats("baseline")
stats_b = mem.get_stats("clarity")

_test(
    "low-confidence winner NOT counted in uses",
    stats_a is not None and stats_a.uses == 0,
    f"uses={stats_a.uses if stats_a else 'None'}",
)
_test(
    "low-confidence loser NOT counted in uses",
    stats_b is None or stats_b.uses == 0,
    f"uses={stats_b.uses if stats_b else '0'}",
)


# ═════════════════════════════════════════════════════════════════════════════
# 10. EMA stability under noisy inputs
# ═════════════════════════════════════════════════════════════════════════════

_section("10. EMA Stability Under Noise")
reset_strategy_memory()

mem = get_strategy_memory()

scores = [0.9, 0.1, 0.9, 0.1, 0.9, 0.1, 0.9, 0.1]
for s in scores:
    mem.record_win("baseline", s, confidence=0.8)

stats = mem.get_stats("baseline")
_test(
    "EMA doesn't swing to extremes with alternating scores",
    stats is not None and 0.3 < stats.ema_score < 0.7,
    f"ema={stats.ema_score:.4f}",
)

pure_avg = sum(scores) / len(scores)
_test(
    "EMA differs from raw average (recency-weighted)",
    stats is not None and abs(stats.ema_score - pure_avg) > 0.01,
    f"ema={stats.ema_score:.4f}, raw_avg={pure_avg:.4f}",
)


# ═════════════════════════════════════════════════════════════════════════════
# 11. Turn counter and last_used_turn tracking
# ═════════════════════════════════════════════════════════════════════════════

_section("11. Turn Counter Tracking")
reset_strategy_memory()

mem = get_strategy_memory()
_test("initial global_turn is 0", mem.global_turn == 0)

mem.record_win("baseline", 0.8, confidence=0.8)
_test("global_turn increments on win", mem.global_turn == 1)

mem.record_win("clarity", 0.7, confidence=0.8)
_test("global_turn increments again", mem.global_turn == 2)

stats_b = mem.get_stats("baseline")
stats_c = mem.get_stats("clarity")
_test(
    "last_used_turn tracks per strategy",
    stats_b is not None
    and stats_c is not None
    and stats_b.last_used_turn == 1
    and stats_c.last_used_turn == 2,
    f"baseline={stats_b.last_used_turn if stats_b else '?'}, clarity={stats_c.last_used_turn if stats_c else '?'}",
)

mem.record_win("baseline", 0.5, confidence=0.3)
stats_b2 = mem.get_stats("baseline")
_test(
    "low-confidence win still updates last_used_turn",
    stats_b2 is not None and stats_b2.last_used_turn == 3,
    f"last_used_turn={stats_b2.last_used_turn if stats_b2 else '?'}",
)
_test(
    "low-confidence win does NOT update uses",
    stats_b2 is not None and stats_b2.uses == 1,
    f"uses={stats_b2.uses if stats_b2 else '?'}",
)


# ═════════════════════════════════════════════════════════════════════════════
# 12. Deterministic ordering preserved
# ═════════════════════════════════════════════════════════════════════════════

_section("12. Deterministic Ordering Preserved")
reset_strategy_memory()

mem = get_strategy_memory()
mem.record_win("baseline", 0.9, confidence=0.8)
mem.record_win("clarity", 0.7, confidence=0.8)
mem.record_win("concise", 0.5, confidence=0.8)

ranked1 = mem.rank_strategies()
ranked2 = mem.rank_strategies()
_test(
    "ranking is deterministic across calls",
    [n for n, _ in ranked1] == [n for n, _ in ranked2],
    f"{[n for n, _ in ranked1]} vs {[n for n, _ in ranked2]}",
)

_test(
    "highest EMA sorts first",
    ranked1[0][0] == "baseline",
    f"first={ranked1[0][0]}",
)


# ═════════════════════════════════════════════════════════════════════════════
# Summary
# ═════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if _FAIL > 0 else 0)
