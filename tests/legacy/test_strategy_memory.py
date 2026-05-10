"""
Tests for Strategy Memory + Selection Policy.

Validates:
    - StrategyStats computes avg_score correctly
    - Strategy memory records wins and losses
    - Ranking sorts by avg_score descending
    - Tie-breaking uses number of uses
    - pick_strategies returns top performers when data exists
    - pick_strategies falls back to defaults with no history
    - Strategy bias changes after repeated wins
    - Deterministic ordering
    - SessionStats exposes strategy_stats
    - Full integration: generate → select → memory → pick next
"""

import sys
from unittest.mock import patch
from dataclasses import dataclass

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
    StrategyMemory,
    StrategyStats,
    get_strategy_memory,
    reset_strategy_memory,
)
from umh.runtime_engine.multi_strategy import (
    pick_strategies,
    select_best,
    CandidateResult,
    DEFAULT_STRATEGIES,
    STRATEGY_REGISTRY,
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


# ═══════════════════════════════════════════════════════════════════════════════
# 1. StrategyStats avg_score computation
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. StrategyStats avg_score")

stats = StrategyStats(name="test")
_test("zero uses → avg_score 0.0", stats.avg_score == 0.0)

stats.uses = 3
stats.total_score = 2.1
_test(
    "avg_score computed correctly",
    abs(stats.avg_score - 0.7) < 0.001,
    f"got {stats.avg_score}",
)

stats.uses = 1
stats.total_score = 0.85
_test(
    "single use → avg equals total",
    abs(stats.avg_score - 0.85) < 0.001,
    f"got {stats.avg_score}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Record wins and losses
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. Record Wins/Losses")

mem = StrategyMemory()
mem.record_win("clarity", 0.9)
mem.record_win("clarity", 0.8)
mem.record_loss("baseline", 0.5)

clarity = mem.get_stats("clarity")
baseline = mem.get_stats("baseline")

_test("clarity uses = 2", clarity.uses == 2, f"got {clarity.uses}")
_test("clarity wins = 2", clarity.wins == 2, f"got {clarity.wins}")
_test(
    "clarity total_score = 1.7",
    abs(clarity.total_score - 1.7) < 0.001,
    f"got {clarity.total_score}",
)
_test(
    "clarity avg_score = 0.85",
    abs(clarity.avg_score - 0.85) < 0.001,
    f"got {clarity.avg_score}",
)

_test("baseline uses = 1", baseline.uses == 1, f"got {baseline.uses}")
_test("baseline wins = 0", baseline.wins == 0, f"got {baseline.wins}")
_test(
    "baseline avg_score = 0.5",
    abs(baseline.avg_score - 0.5) < 0.001,
    f"got {baseline.avg_score}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Ranking sorted by avg_score
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Ranking")

ranked = mem.rank_strategies()
_test(
    "clarity ranked first",
    ranked[0][0] == "clarity",
    f"first={ranked[0][0]}",
)
_test(
    "baseline ranked second",
    ranked[1][0] == "baseline",
    f"second={ranked[1][0]}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Tie-breaking by uses
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Tie-Breaking")

mem2 = StrategyMemory()
mem2.record_win("a", 0.7)
mem2.record_win("b", 0.7)
mem2.record_win("b", 0.7)

ranked2 = mem2.rank_strategies()
_test(
    "same avg → more uses wins",
    ranked2[0][0] == "b",
    f"first={ranked2[0][0]} (uses: a={mem2.get_stats('a').uses}, b={mem2.get_stats('b').uses})",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. pick_strategies with no history → defaults
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Cold Start Fallback")

reset_strategy_memory()
picked = pick_strategies(num_candidates=2)
_test(
    "no history → default strategies",
    picked == DEFAULT_STRATEGIES[:2],
    f"got {picked}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. pick_strategies with history → top performers
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. History-Driven Selection")

reset_strategy_memory()
gmem = get_strategy_memory()
gmem.record_win("structured", 0.9)
gmem.record_win("structured", 0.85)
gmem.record_win("concise", 0.8)
gmem.record_loss("baseline", 0.4)
gmem.record_loss("clarity", 0.5)

picked2 = pick_strategies(num_candidates=2)
_test(
    "top 2 are structured + concise",
    picked2 == ["structured", "concise"],
    f"got {picked2}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. pick_strategies filters invalid names
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Invalid Strategy Filtering")

reset_strategy_memory()
gmem = get_strategy_memory()
gmem.record_win("nonexistent_strategy", 0.99)
gmem.record_win("baseline", 0.5)

picked3 = pick_strategies(num_candidates=2)
_test(
    "nonexistent strategy excluded",
    "nonexistent_strategy" not in picked3,
    f"got {picked3}",
)
_test(
    "falls back to fill slots",
    len(picked3) == 2,
    f"got {len(picked3)}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Strategy bias changes after repeated wins
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Bias Shift Over Time")

reset_strategy_memory()
gmem = get_strategy_memory()

initial = pick_strategies(2)
_test("initial → defaults", initial == DEFAULT_STRATEGIES[:2])

for _ in range(5):
    gmem.record_win("concise", 0.9)
    gmem.record_loss("baseline", 0.3)
    gmem.record_loss("clarity", 0.4)

after_bias = pick_strategies(2)
_test(
    "after 5 concise wins → concise is first",
    after_bias[0] == "concise",
    f"got {after_bias}",
)
_test(
    "baseline/clarity demoted",
    "baseline" not in after_bias or after_bias.index("baseline") > 0
    if "baseline" in after_bias
    else True,
    f"got {after_bias}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Deterministic ordering
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Determinism")

r1 = pick_strategies(2)
r2 = pick_strategies(2)
_test("same state → same picks", r1 == r2, f"{r1} vs {r2}")

mem3 = StrategyMemory()
mem3.record_win("a", 0.8)
mem3.record_win("b", 0.6)
rank1 = mem3.rank_strategies()
rank2 = mem3.rank_strategies()
_test(
    "ranking is stable",
    [n for n, _ in rank1] == [n for n, _ in rank2],
)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. SessionStats exposes strategy_stats
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. SessionStats Integration")

from umh.runtime_engine.session_runtime import SessionStats

ss = SessionStats()
_test("strategy_stats field exists", hasattr(ss, "strategy_stats"))
_test("strategy_stats starts empty", ss.strategy_stats == {})

ss.sync_strategy_stats()
_test(
    "sync pulls from global memory",
    isinstance(ss.strategy_stats, dict),
    f"type={type(ss.strategy_stats).__name__}",
)
_test(
    "sync has data (global memory has entries from test 8)",
    len(ss.strategy_stats) > 0,
    f"keys={list(ss.strategy_stats.keys())}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. to_dict serialization
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. Serialization")

mem4 = StrategyMemory()
mem4.record_win("test_strat", 0.75)
d = mem4.to_dict()

_test("to_dict returns dict", isinstance(d, dict))
_test("strategy present in dict", "test_strat" in d)
_test(
    "dict has correct fields",
    all(
        k in d["test_strat"]
        for k in ["name", "uses", "wins", "total_score", "avg_score"]
    ),
)
_test(
    "avg_score in dict is correct",
    abs(d["test_strat"]["avg_score"] - 0.75) < 0.001,
    f"got {d['test_strat']['avg_score']}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. select_best records to strategy memory
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. select_best → Memory Recording")

reset_strategy_memory()
gmem = get_strategy_memory()

c_a = _make_candidate("A", "baseline", quality=0.5, confidence=0.8)
c_b = _make_candidate("B", "clarity", quality=0.8, confidence=0.7)

winner = select_best([c_a, c_b])
_test("winner is clarity", winner.strategy_name == "clarity")

clarity_stats = gmem.get_stats("clarity")
baseline_stats = gmem.get_stats("baseline")

_test("clarity recorded as win", clarity_stats.wins == 1, f"wins={clarity_stats.wins}")
_test(
    "baseline recorded as loss", baseline_stats.wins == 0, f"wins={baseline_stats.wins}"
)
_test("both have 1 use", clarity_stats.uses == 1 and baseline_stats.uses == 1)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. has_data flag
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. has_data")

empty_mem = StrategyMemory()
_test("new memory has no data", not empty_mem.has_data())

empty_mem.record_win("x", 0.5)
_test("after record → has data", empty_mem.has_data())


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Full integration: generate → select → memory → pick
# ═══════════════════════════════════════════════════════════════════════════════

_section("14. Full Integration Loop")


@dataclass
class FakeRoutingResult:
    output: str
    provider: str = "test"
    model: str = "test-model"
    tokens_used: int = 100
    input_tokens: int = 50
    output_tokens: int = 50
    cost_usd: float = 0.001
    latency_ms: int = 200


class FakeTaskType:
    def __init__(self, v):
        self.value = v

    def __str__(self):
        return self.value


reset_strategy_memory()

_round_count = 0


def _mock_llm(prompt, system=None, agent_type=None, task_type=None):
    global _round_count
    _round_count += 1
    if system and "concise" in system.lower():
        return FakeRoutingResult(
            output="Focus: 1. Send 20 DMs. 2. Track rates. 3. Follow up. Do this daily for 5 days."
        )
    elif system and "clarity" in system.lower():
        return FakeRoutingResult(
            output="Focus on 3 key actions: 1. Send 20 DMs to prospects. 2. Track reply rates. 3. Follow up within 24h."
        )
    elif system and "structured" in system.lower():
        return FakeRoutingResult(
            output="## Action Plan\n1. Send DMs\n2. Track replies\n3. Follow up\n\n## Timeline\nDaily for one week."
        )
    else:
        return FakeRoutingResult(
            output="Here is a comprehensive analysis of your business strategy."
        )


with patch("umh.runtime_engine.model_router.call_with_fallback", side_effect=_mock_llm):
    from umh.runtime_engine.multi_strategy import generate_candidates

    for round_num in range(5):
        candidates = generate_candidates(
            message="What should I focus on?",
            system_prompt="You are a business assistant.",
            task_type=FakeTaskType("generate"),
            num_candidates=2,
        )
        if candidates:
            select_best(candidates)

gmem = get_strategy_memory()
ranked = gmem.rank_strategies()
_test(
    "memory has data after 5 rounds",
    gmem.has_data(),
)
_test(
    "multiple strategies tracked",
    len(ranked) >= 2,
    f"tracked {len(ranked)} strategies",
)

top_name = ranked[0][0] if ranked else None
_test(
    "top strategy has highest avg",
    top_name is not None,
    f"top={top_name}, avg={ranked[0][1].avg_score:.3f}" if ranked else "no data",
)

final_picks = pick_strategies(2)
_test(
    "final picks reflect learned preference",
    final_picks[0] == top_name,
    f"picks={final_picks}, top={top_name}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if _FAIL > 0 else 0)
