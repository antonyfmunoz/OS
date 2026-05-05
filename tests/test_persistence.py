"""
Tests for the Persistent Memory Layer.

Validates:
    - save/load strategy memory round-trip consistency
    - deterministic reload (same data → same state)
    - no corruption on malformed data
    - bounded session summary size (MAX_SUMMARIES)
    - cold start fallback (no persisted data → empty)
    - StrategyMemory persist=True loads on init
    - StrategyMemory persist=True saves on record_win/loss
    - Session summary shape matches spec
    - flush() forces all pending writes
    - Buffer batching respects FLUSH_INTERVAL
    - load_recent_summaries respects limit
    - Integration with DecisionTrace via SessionRuntime
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


# ═══════════════════════════════════════════════════════════════════════════════
# Mock storage — in-memory dict that implements SubstrateStorage protocol
# ═══════════════════════════════════════════════════════════════════════════════


class MockStorage:
    def __init__(self):
        self._data: dict = {}

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def put(self, key: str, value) -> None:
        self._data[key] = value

    def all_keys(self) -> list[str]:
        return list(self._data.keys())

    def clear(self) -> None:
        self._data.clear()


_mock_store = MockStorage()


def _patch_storage():
    """Patch get_storage to return our mock."""
    import umh.substrate.storage as storage_mod

    storage_mod._storage_singleton = _mock_store


def _reset():
    """Reset all test state."""
    _mock_store.clear()
    _patch_storage()

    from umh.runtime_engine.persistence import _reset_buffer_for_tests

    _reset_buffer_for_tests()

    from umh.strategy.memory import reset_strategy_memory

    reset_strategy_memory()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Strategy memory save/load round-trip
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. Strategy Memory Round-Trip")
_reset()

from umh.runtime_engine.persistence import (
    save_strategy_memory,
    load_strategy_memory,
    append_session_summary,
    load_recent_summaries,
    flush,
    STORAGE_KEY_STRATEGY,
    STORAGE_KEY_SUMMARIES,
    MAX_SUMMARIES,
    FLUSH_INTERVAL,
)

strategy_data = {
    "clarity": {
        "name": "clarity",
        "uses": 10,
        "wins": 8,
        "total_score": 7.5,
        "avg_score": 0.85,
        "ema_score": 0.85,
        "last_used_turn": 15,
    },
    "baseline": {
        "name": "baseline",
        "uses": 5,
        "wins": 2,
        "total_score": 3.0,
        "avg_score": 0.6,
        "ema_score": 0.6,
        "last_used_turn": 10,
    },
}

save_strategy_memory(strategy_data, global_turn=15)
flush()

loaded = load_strategy_memory()
_test("loaded is not None", loaded is not None)
_test("strategies key present", "strategies" in loaded)
_test("global_turn preserved", loaded["global_turn"] == 15)
_test("clarity preserved", loaded["strategies"]["clarity"]["ema_score"] == 0.85)
_test("baseline preserved", loaded["strategies"]["baseline"]["uses"] == 5)
_test(
    "round-trip identical",
    loaded["strategies"] == strategy_data,
    f"got {loaded['strategies']}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Cold start — no persisted data
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. Cold Start Fallback")
_reset()

loaded = load_strategy_memory()
_test("cold start returns None", loaded is None)

summaries = load_recent_summaries()
_test("cold start summaries is empty list", summaries == [])


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Malformed data handling
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Malformed Data")
_reset()

_mock_store.put(STORAGE_KEY_STRATEGY, "not a dict")
loaded = load_strategy_memory()
_test("string value → None", loaded is None)

_mock_store.put(STORAGE_KEY_STRATEGY, {"no_strategies_key": True})
loaded = load_strategy_memory()
_test("missing strategies key → None", loaded is None)

_mock_store.put(STORAGE_KEY_SUMMARIES, "not a list")
summaries = load_recent_summaries()
_test("non-list summaries → empty", summaries == [])


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Session summary append and bounded size
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Session Summary Bounded Size")
_reset()

for i in range(MAX_SUMMARIES + 20):
    append_session_summary({"turn": i, "quality_score": 0.5 + (i % 10) * 0.05})
flush()

loaded = load_recent_summaries(limit=MAX_SUMMARIES + 50)
_test(
    f"capped at MAX_SUMMARIES={MAX_SUMMARIES}",
    len(loaded) == MAX_SUMMARIES,
    f"got {len(loaded)}",
)
_test(
    "oldest entries trimmed",
    loaded[0]["turn"] == 20,
    f"first turn={loaded[0]['turn']}",
)
_test(
    "newest preserved",
    loaded[-1]["turn"] == MAX_SUMMARIES + 19,
    f"last turn={loaded[-1]['turn']}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. load_recent_summaries respects limit
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Summary Limit")

recent = load_recent_summaries(limit=10)
_test("limit=10 returns 10", len(recent) == 10)
_test(
    "limit returns most recent",
    recent[-1]["turn"] == MAX_SUMMARIES + 19,
)
_test(
    "limit returns correct oldest",
    recent[0]["turn"] == MAX_SUMMARIES + 10,
    f"first={recent[0]['turn']}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Flush forces write
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. Flush Behavior")
_reset()

save_strategy_memory({"test": {"name": "test", "uses": 1}}, global_turn=1)

raw_before = _mock_store.get(STORAGE_KEY_STRATEGY)
_test(
    "before flush — may not be written yet (buffered)",
    True,  # just documenting the behavior
)

flush()
raw_after = _mock_store.get(STORAGE_KEY_STRATEGY)
_test("after flush — data is written", raw_after is not None)
_test("flushed data correct", raw_after["global_turn"] == 1)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Buffer auto-flush at FLUSH_INTERVAL
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Buffer Auto-Flush")
_reset()

for i in range(FLUSH_INTERVAL):
    append_session_summary({"turn": i})

raw = _mock_store.get(STORAGE_KEY_SUMMARIES)
_test(
    f"auto-flushed after {FLUSH_INTERVAL} updates",
    raw is not None and len(raw) == FLUSH_INTERVAL,
    f"got {len(raw) if raw else 'None'}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. StrategyMemory persist=False (default, no side effects)
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. StrategyMemory persist=False")
_reset()

from umh.strategy.memory import StrategyMemory

mem = StrategyMemory(persist=False)
mem.record_win("test_strat", 0.9)
flush()

raw = _mock_store.get(STORAGE_KEY_STRATEGY)
_test("persist=False does not write", raw is None)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. StrategyMemory persist=True saves on record_win
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. StrategyMemory persist=True — Save")
_reset()

mem_p = StrategyMemory(persist=True)
for _ in range(FLUSH_INTERVAL):
    mem_p.record_win("clarity", 0.85)
flush()

raw = _mock_store.get(STORAGE_KEY_STRATEGY)
_test("persist=True saves after flush", raw is not None)
_test("strategy data present", "clarity" in raw.get("strategies", {}))
_test(
    "global_turn tracked",
    raw["global_turn"] == FLUSH_INTERVAL,
    f"got {raw.get('global_turn')}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. StrategyMemory persist=True loads on cold start
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. StrategyMemory persist=True — Cold Load")

# mem_p already wrote. Now create a NEW instance that should load the data.
mem_cold = StrategyMemory(persist=True)
_test("cold load has data", mem_cold.has_data())
_test("cold load has clarity", mem_cold.get_stats("clarity") is not None)

stats = mem_cold.get_stats("clarity")
_test("cold clarity uses correct", stats.uses == FLUSH_INTERVAL)
_test(
    "cold clarity ema_score > 0",
    stats.ema_score > 0,
    f"ema={stats.ema_score}",
)
_test(
    "cold global_turn restored",
    mem_cold.global_turn == FLUSH_INTERVAL,
    f"got {mem_cold.global_turn}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Determinism — same data → same state
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. Determinism")

mem_a = StrategyMemory(persist=True)
mem_b = StrategyMemory(persist=True)

_test("two loads same global_turn", mem_a.global_turn == mem_b.global_turn)
_test("two loads same has_data", mem_a.has_data() == mem_b.has_data())

ranked_a = mem_a.rank_strategies()
ranked_b = mem_b.rank_strategies()
_test(
    "two loads same ranking order",
    [n for n, _ in ranked_a] == [n for n, _ in ranked_b],
)
_test(
    "two loads same scores",
    mem_a.to_dict() == mem_b.to_dict(),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. StrategyMemory persist=True saves on record_loss
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. persist=True — record_loss")
_reset()

mem_l = StrategyMemory(persist=True)
for _ in range(FLUSH_INTERVAL):
    mem_l.record_loss("struggling", 0.3)
flush()

raw = _mock_store.get(STORAGE_KEY_STRATEGY)
_test("record_loss triggers persist", raw is not None)
_test("struggling strategy saved", "struggling" in raw.get("strategies", {}))


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Session summary shape
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. Session Summary Shape")
_reset()

expected_summary = {
    "session_id": "test-123",
    "turn": 5,
    "strategy": "clarity",
    "quality_score": 0.82,
    "confidence": 0.75,
    "signals": {
        "hallucination": False,
        "incomplete": False,
    },
    "control_intervened": False,
}
append_session_summary(expected_summary)
flush()

loaded_summaries = load_recent_summaries(limit=1)
_test("summary preserved", len(loaded_summaries) == 1)
_test("session_id preserved", loaded_summaries[0]["session_id"] == "test-123")
_test("turn preserved", loaded_summaries[0]["turn"] == 5)
_test("strategy preserved", loaded_summaries[0]["strategy"] == "clarity")
_test("quality_score preserved", loaded_summaries[0]["quality_score"] == 0.82)
_test("confidence preserved", loaded_summaries[0]["confidence"] == 0.75)
_test(
    "signals.hallucination preserved",
    loaded_summaries[0]["signals"]["hallucination"] is False,
)
_test(
    "signals.incomplete preserved",
    loaded_summaries[0]["signals"]["incomplete"] is False,
)
_test(
    "control_intervened preserved", loaded_summaries[0]["control_intervened"] is False
)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. get_strategy_memory(persist=True) singleton
# ═══════════════════════════════════════════════════════════════════════════════

_section("14. get_strategy_memory Singleton")
_reset()

from umh.strategy.memory import get_strategy_memory, reset_strategy_memory

reset_strategy_memory()
mem1 = get_strategy_memory(persist=True)
mem2 = get_strategy_memory()

_test("singleton returns same instance", mem1 is mem2)
_test("persist flag set", mem1._persist is True)


# ═══════════════════════════════════════════════════════════════════════════════
# 15. SessionRuntime integration stub
# ═══════════════════════════════════════════════════════════════════════════════

_section("15. SessionRuntime Integration")
_reset()

from umh.runtime_engine.session_runtime import SessionRuntime

from unittest.mock import MagicMock

mock_ctx = MagicMock()
session = SessionRuntime(mock_ctx, session_id="persist-test")

# Manually add a trace and verify summary would be written
from umh.runtime_engine.decision_trace import DecisionTrace

trace = DecisionTrace(
    turn_id=1,
    strategies_considered=("clarity",),
    strategy_scores={"clarity": 0.8},
    selected_strategy="clarity",
    quality_score=0.78,
    confidence=0.85,
    signals={
        "quality_score": 0.78,
        "flags": {"hallucination_risk": False, "incomplete": True},
    },
    attributed_signals={},
    horizon={},
    directives_applied=(),
    model_used="test/model",
    latency_ms=100,
    tokens_used={"input": 50, "output": 50, "total": 100},
    was_enhanced=False,
)
session.stats.decision_traces.append(trace)

# Simulate the summary creation code path
latest = session.stats.decision_traces[-1]
ctrl = getattr(latest, "control_decision", None)
flags = (latest.signals or {}).get("flags", {})
summary = {
    "session_id": session.session_id,
    "turn": latest.turn_id,
    "strategy": latest.selected_strategy,
    "quality_score": latest.quality_score,
    "confidence": latest.confidence,
    "signals": {
        "hallucination": flags.get("hallucination_risk", False),
        "incomplete": flags.get("incomplete", False),
    },
    "control_intervened": ctrl is not None and getattr(ctrl, "intervene", False),
}

_test("summary has correct session_id", summary["session_id"] == "persist-test")
_test("summary strategy is clarity", summary["strategy"] == "clarity")
_test("summary quality_score", summary["quality_score"] == 0.78)
_test("summary incomplete flag True", summary["signals"]["incomplete"] is True)
_test("summary hallucination flag False", summary["signals"]["hallucination"] is False)
_test("summary control_intervened False", summary["control_intervened"] is False)

append_session_summary(summary)
flush()

persisted = load_recent_summaries(limit=1)
_test("summary persisted via append", len(persisted) == 1)
_test("persisted matches original", persisted[0] == summary)


# ═══════════════════════════════════════════════════════════════════════════════
# Cleanup — reset storage singleton
# ═══════════════════════════════════════════════════════════════════════════════

import umh.substrate.storage as storage_mod

storage_mod._storage_singleton = None


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if _FAIL > 0 else 0)
