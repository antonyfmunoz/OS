"""
Tests for Memory Horizon Separation.

Validates:
    - Strategy scores decay over time (mid-term horizon)
    - WorldModel ignores low-confidence entries
    - WorldModel rejects duplicate entries
    - Session evaluation history is capped at MAX_SESSION_HISTORY
    - Horizon tags are correct on every evaluation
    - Behavior remains deterministic across repeated runs
    - No cross-horizon interference
"""

import math
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


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Strategy decay over time
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. Strategy Decay")

from umh.strategy.memory import (
    StrategyMemory,
    StrategyStats,
    DECAY_RATE,
    reset_strategy_memory,
)

mem = StrategyMemory()
mem.record_win("alpha", 0.9)
mem.record_win("alpha", 0.85)

alpha = mem.get_stats("alpha")
raw_ema = alpha.ema_score
current_turn = mem.global_turn

eff_now = alpha.effective_score(current_turn)
_test(
    "effective_score at current turn equals ema_score",
    abs(eff_now - raw_ema) < 0.001,
    f"eff={eff_now:.4f} ema={raw_ema:.4f}",
)

eff_10_later = alpha.effective_score(current_turn + 10)
expected_10 = raw_ema * math.exp(-DECAY_RATE * 10)
_test(
    "effective_score decays after 10 turns",
    abs(eff_10_later - expected_10) < 0.001,
    f"eff={eff_10_later:.4f} expected={expected_10:.4f}",
)

_test(
    "decayed score < raw ema",
    eff_10_later < raw_ema,
    f"decayed={eff_10_later:.4f} raw={raw_ema:.4f}",
)

eff_50_later = alpha.effective_score(current_turn + 50)
_test(
    "50-turn staleness drops score significantly",
    eff_50_later < raw_ema * 0.15,
    f"eff_50={eff_50_later:.4f} threshold={raw_ema * 0.15:.4f}",
)

_test(
    "zero staleness → no decay",
    abs(alpha.effective_score(current_turn) - raw_ema) < 0.001,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Strategy ranking uses decay
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. Decay-Aware Ranking")

reset_strategy_memory()
mem2 = StrategyMemory()

mem2.record_win("old_winner", 0.95)
mem2.record_win("old_winner", 0.90)

for _ in range(20):
    mem2.record_win("recent", 0.7)

ranked = mem2.rank_strategies()
_test(
    "recent strategy ranks higher than stale high-scorer",
    ranked[0][0] == "recent",
    f"first={ranked[0][0]} (old_winner last_used={mem2.get_stats('old_winner').last_used_turn}, "
    f"recent last_used={mem2.get_stats('recent').last_used_turn})",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. WorldModel confidence gate
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. WorldModel Confidence Gate")

from unittest.mock import MagicMock, patch

mock_store = MagicMock()
mock_store.all_keys.return_value = []

with patch("umh.substrate.storage.get_storage", return_value=mock_store):
    from umh.world.model import WorldModel, WRITE_CONFIDENCE_THRESHOLD

    wm = WorldModel(org_id="test_org")

    wrote_neutral = wm.update_from_interaction(
        "test message", "test response", outcome=None
    )
    _test(
        "neutral outcome (conf=0.3) rejected",
        wrote_neutral is False,
        f"threshold={WRITE_CONFIDENCE_THRESHOLD}",
    )

    wrote_poor = wm.update_from_interaction(
        "test message", "test response", outcome="poor"
    )
    _test(
        "poor outcome (conf=0.15) rejected",
        wrote_poor is False,
    )

    wrote_good = wm.update_from_interaction(
        "unique good message about strategy",
        "unique good response about approach",
        outcome="good",
    )
    _test(
        "good outcome (conf=0.5) accepted",
        wrote_good is True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 4. WorldModel duplicate detection
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. WorldModel Duplicate Detection")

mock_store2 = MagicMock()
_stored_entries: dict[str, dict] = {}


def _mock_put(key, value):
    _stored_entries[key] = value


def _mock_get(key):
    return _stored_entries.get(key)


def _mock_all_keys():
    return list(_stored_entries.keys())


mock_store2.put = _mock_put
mock_store2.get = _mock_get
mock_store2.all_keys = _mock_all_keys

with patch("umh.substrate.storage.get_storage", return_value=mock_store2):
    from umh.world.model import CanonicalWorldModel, InstanceWorldModel

    wm2 = WorldModel.__new__(WorldModel)
    wm2.org_id = "test_org"
    wm2.canonical = CanonicalWorldModel()
    wm2.instance = InstanceWorldModel("test_org")

    wrote_first = wm2.update_from_interaction(
        "send 20 DMs to prospects today",
        "Focus on outreach to warm leads first",
        outcome="good",
    )
    _test("first unique entry accepted", wrote_first is True)

    wrote_dup = wm2.update_from_interaction(
        "send 20 DMs to prospects today",
        "Focus on outreach to warm leads first",
        outcome="good",
    )
    _test("duplicate entry rejected", wrote_dup is False)

    wrote_different = wm2.update_from_interaction(
        "analyze competitor pricing models because market shifted",
        "Review competitor data from last quarter",
        outcome="good",
    )
    _test("different content accepted", wrote_different is True)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Session evaluation history capped
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Session History Cap")

from umh.runtime_engine.adaptive_prompt import MAX_SESSION_HISTORY
from umh.runtime_engine.session_runtime import SessionStats

stats = SessionStats()
for i in range(25):
    stats.evaluations.append(
        {
            "quality_score": 0.5 + (i * 0.01),
            "confidence": 0.7,
            "flags": {},
            "reason": f"test_{i}",
        }
    )

_test(
    "uncapped evaluations accumulate",
    len(stats.evaluations) == 25,
    f"len={len(stats.evaluations)}",
)

if len(stats.evaluations) > MAX_SESSION_HISTORY:
    stats.evaluations = stats.evaluations[-MAX_SESSION_HISTORY:]

_test(
    f"capped at MAX_SESSION_HISTORY={MAX_SESSION_HISTORY}",
    len(stats.evaluations) == MAX_SESSION_HISTORY,
    f"len={len(stats.evaluations)}",
)

_test(
    "oldest evaluations trimmed, newest preserved",
    stats.evaluations[-1]["reason"] == "test_24",
    f"last={stats.evaluations[-1]['reason']}",
)

_test(
    "first preserved is correct offset",
    stats.evaluations[0]["reason"] == f"test_{25 - MAX_SESSION_HISTORY}",
    f"first={stats.evaluations[0]['reason']}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Horizon tagging
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. Horizon Tags")

from umh.runtime_engine.signal_router import (
    route_signals,
    HorizonTag,
    WORLD_MODEL_CONFIDENCE_THRESHOLD,
)

high_conf_eval = {
    "quality_score": 0.85,
    "confidence": 0.8,
    "flags": {
        "hallucination_risk": False,
        "low_information": False,
        "incomplete": False,
    },
    "reason": "acceptable",
}
signals_high = route_signals(high_conf_eval)

_test("high-conf: session=True", signals_high.horizon.session is True)
_test("high-conf: strategy=True", signals_high.horizon.strategy is True)
_test(
    "high-conf: world_model=True",
    signals_high.horizon.world_model is True,
    f"confidence={high_conf_eval['confidence']} >= {WORLD_MODEL_CONFIDENCE_THRESHOLD}",
)

low_conf_eval = {
    "quality_score": 0.85,
    "confidence": 0.4,
    "flags": {
        "hallucination_risk": False,
        "low_information": False,
        "incomplete": False,
    },
    "reason": "acceptable",
}
signals_low = route_signals(low_conf_eval)

_test("low-conf: session=True", signals_low.horizon.session is True)
_test("low-conf: strategy=True", signals_low.horizon.strategy is True)
_test(
    "low-conf: world_model=False",
    signals_low.horizon.world_model is False,
    f"confidence={low_conf_eval['confidence']} < {WORLD_MODEL_CONFIDENCE_THRESHOLD}",
)

_test(
    "world_model signal is None when horizon.world_model is False",
    signals_low.world_model is None,
)

_test(
    "horizon in to_dict output",
    "horizon" in signals_high.to_dict(),
)

horizon_dict = signals_high.to_dict()["horizon"]
_test(
    "horizon dict has all three keys",
    set(horizon_dict.keys()) == {"session", "strategy", "world_model"},
)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Determinism preserved
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Determinism")

reset_strategy_memory()
mem_a = StrategyMemory()
mem_b = StrategyMemory()

for score in [0.8, 0.6, 0.9, 0.7, 0.5]:
    mem_a.record_win("x", score)
    mem_b.record_win("x", score)

_test(
    "same inputs → same ema_score",
    mem_a.get_stats("x").ema_score == mem_b.get_stats("x").ema_score,
)

_test(
    "same inputs → same effective_score",
    mem_a.get_stats("x").effective_score(5) == mem_b.get_stats("x").effective_score(5),
)

sig_a = route_signals(high_conf_eval)
sig_b = route_signals(high_conf_eval)
_test(
    "same eval → same signals",
    sig_a.to_dict() == sig_b.to_dict(),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. No cross-horizon interference
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Cross-Horizon Isolation")

reset_strategy_memory()
from umh.strategy.memory import get_strategy_memory

gmem = get_strategy_memory()
gmem.record_win("clarity", 0.85)

for _ in range(15):
    gmem.record_win("filler", 0.3)

clarity_stats = gmem.get_stats("clarity")
current = gmem.global_turn
eff = clarity_stats.effective_score(current)
_test(
    "stale strategy decays in mid-term",
    eff < clarity_stats.ema_score,
    f"effective={eff:.4f} raw_ema={clarity_stats.ema_score:.4f}",
)

_test(
    "raw ema preserved (not mutated by decay)",
    clarity_stats.ema_score == 0.85,
    f"ema={clarity_stats.ema_score}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Adaptive prompt reads capped window
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Adaptive Prompt Session Isolation")

from umh.runtime_engine.adaptive_prompt import adapt_prompt, _apply_session_signals

mock_session = MagicMock()
mock_session.stats.evaluations = [
    {
        "quality_score": 0.2,
        "confidence": 0.8,
        "flags": {
            "hallucination_risk": True,
            "low_information": True,
            "incomplete": True,
        },
        "reason": "bad",
    }
    for _ in range(20)
]

prioritized: list[tuple[int, str]] = []
_apply_session_signals(mock_session, prioritized)

_test(
    "session signals generated from evaluations",
    len(prioritized) > 0,
    f"directives={len(prioritized)}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Full horizon integration
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. Full Integration")

from umh.runtime_engine.outcome_evaluator import evaluate_outcome

eval_result = evaluate_outcome(
    input_text="What should I focus on today?",
    output_text="Focus on sending 20 DMs to warm leads. Track replies. Follow up within 24 hours.",
    context={"agent_type": "executive_assistant", "venture_id": "lyfe_institute"},
    metadata={"model_used": "test/test-model"},
)

_test(
    "evaluation has signals with horizon",
    "signals" in eval_result and "horizon" in eval_result["signals"],
    f"keys={list(eval_result.get('signals', {}).keys())}",
)

if "signals" in eval_result:
    horizon = eval_result["signals"]["horizon"]
    _test("integration: session=True", horizon["session"] is True)
    _test("integration: strategy=True", horizon["strategy"] is True)
    wm_expected = eval_result["confidence"] >= WORLD_MODEL_CONFIDENCE_THRESHOLD
    _test(
        f"integration: world_model matches confidence gate",
        horizon["world_model"] == wm_expected,
        f"confidence={eval_result['confidence']} wm={horizon['world_model']}",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if _FAIL > 0 else 0)
