"""
Tests for the Persistent Memory Substrate (Task 9).

Validates:
    - Directive memory save/load round-trip consistency
    - Goal tracker save/load round-trip consistency
    - Cross-session reload (new instance loads persisted state)
    - Deterministic reload (same data → same state, twice)
    - Session boundary (session_id tagging via SessionRuntime)
    - Performance (reads only on startup, batched writes)
    - DecisionTrace memory_persisted + memory_version fields
    - Backward compatibility (persist=False unchanged)
    - No LLM calls
    - No regression to existing StrategyMemory persistence
    - ExecutionSpine unchanged (no imports)
    - GoalTracker hydration with re-added goals
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

    from umh.runtime_engine.directive_memory import reset_directive_memory

    reset_directive_memory()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Imports
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. Imports")

from umh.runtime_engine.persistence import (
    save_directive_memory,
    load_directive_memory,
    save_goal_trackers,
    load_goal_trackers,
    save_strategy_memory,
    load_strategy_memory,
    flush,
    STORAGE_KEY_DIRECTIVE,
    STORAGE_KEY_TRACKERS,
    FLUSH_INTERVAL,
)
from umh.runtime_engine.directive_memory import (
    DirectiveMemory,
    DirectiveStats,
    get_directive_memory,
    reset_directive_memory,
)
from umh.goals.state import GoalRegistry, GoalTracker, GoalState
from umh.runtime_engine.decision_trace import DecisionTrace, build_trace
from umh.runtime_engine.session_runtime import SessionRuntime

_test("persistence imports", True)
_test("directive_memory imports", True)
_test("goal_state imports", True)
_test("decision_trace imports", True)
_test("session_runtime imports", True)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Directive Memory Round-Trip
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. Directive Memory Round-Trip")
_reset()

directive_data = {
    "clarity": {
        "name": "clarity",
        "uses": 12,
        "wins": 9,
        "total_score": 8.5,
        "avg_score": 0.82,
        "ema_score": 0.82,
        "last_used_turn": 20,
    },
    "concise": {
        "name": "concise",
        "uses": 4,
        "wins": 2,
        "total_score": 2.8,
        "avg_score": 0.7,
        "ema_score": 0.7,
        "last_used_turn": 15,
    },
}

save_directive_memory(directive_data, global_turn=20)
flush()

loaded = load_directive_memory()
_test("loaded is not None", loaded is not None)
_test("directives key present", "directives" in loaded)
_test("global_turn preserved", loaded["global_turn"] == 20)
_test("clarity ema preserved", loaded["directives"]["clarity"]["ema_score"] == 0.82)
_test("concise uses preserved", loaded["directives"]["concise"]["uses"] == 4)
_test(
    "round-trip identical",
    loaded["directives"] == directive_data,
    f"got {loaded['directives']}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Goal Tracker Round-Trip
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Goal Tracker Round-Trip")
_reset()

tracker_data = {
    "close_sale": {
        "goal_id": "close_sale",
        "success_score": 0.72,
        "recency_weight": 0.85,
        "last_active_turn": 8,
        "latest_delta": 0.05,
        "uses": 6,
    },
    "analyze": {
        "goal_id": "analyze",
        "success_score": 0.55,
        "recency_weight": 0.6,
        "last_active_turn": 3,
        "latest_delta": -0.02,
        "uses": 3,
    },
}

save_goal_trackers(tracker_data, registry_turn=10)
flush()

loaded = load_goal_trackers()
_test("loaded is not None", loaded is not None)
_test("trackers key present", "trackers" in loaded)
_test("registry_turn preserved", loaded["registry_turn"] == 10)
_test(
    "close_sale success preserved",
    loaded["trackers"]["close_sale"]["success_score"] == 0.72,
)
_test("analyze uses preserved", loaded["trackers"]["analyze"]["uses"] == 3)
_test(
    "round-trip identical",
    loaded["trackers"] == tracker_data,
    f"got {loaded['trackers']}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Cold Start — No Persisted Data
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Cold Start — No Persisted Data")
_reset()

_test("cold directive returns None", load_directive_memory() is None)
_test("cold trackers returns None", load_goal_trackers() is None)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Malformed Data Handling
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Malformed Data Handling")
_reset()

_mock_store.put(STORAGE_KEY_DIRECTIVE, "not a dict")
_test("string directive → None", load_directive_memory() is None)

_mock_store.put(STORAGE_KEY_DIRECTIVE, {"no_directives_key": True})
_test("missing directives key → None", load_directive_memory() is None)

_mock_store.put(STORAGE_KEY_TRACKERS, 42)
_test("int trackers → None", load_goal_trackers() is None)

_mock_store.put(STORAGE_KEY_TRACKERS, {"no_trackers_key": True})
_test("missing trackers key → None", load_goal_trackers() is None)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. DirectiveMemory persist=True — Save
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. DirectiveMemory persist=True — Save")
_reset()

dm = DirectiveMemory(persist=True)
for _ in range(FLUSH_INTERVAL):
    dm.record_win("clarity", 0.85)
flush()

raw = _mock_store.get(STORAGE_KEY_DIRECTIVE)
_test("persist=True saves after flush", raw is not None)
_test("directive data present", "clarity" in raw.get("directives", {}))
_test(
    "global_turn tracked",
    raw["global_turn"] == FLUSH_INTERVAL,
    f"got {raw.get('global_turn')}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. DirectiveMemory persist=True — Cold Load
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. DirectiveMemory persist=True — Cold Load")

dm_cold = DirectiveMemory(persist=True)
_test("cold load has data", dm_cold.has_data())
_test("cold load has clarity", dm_cold.get_stats("clarity") is not None)

stats = dm_cold.get_stats("clarity")
_test("cold clarity uses correct", stats.uses == FLUSH_INTERVAL)
_test("cold clarity ema > 0", stats.ema_score > 0, f"ema={stats.ema_score}")
_test(
    "cold global_turn restored",
    dm_cold.global_turn == FLUSH_INTERVAL,
    f"got {dm_cold.global_turn}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. DirectiveMemory persist=False — No Side Effects
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. DirectiveMemory persist=False — No Side Effects")
_reset()

dm_np = DirectiveMemory(persist=False)
dm_np.record_win("test_d", 0.9)
flush()

raw = _mock_store.get(STORAGE_KEY_DIRECTIVE)
_test("persist=False does not write", raw is None)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. DirectiveMemory record_loss persists
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. DirectiveMemory persist=True — record_loss")
_reset()

dm_l = DirectiveMemory(persist=True)
for _ in range(FLUSH_INTERVAL):
    dm_l.record_loss("struggling", 0.3)
flush()

raw = _mock_store.get(STORAGE_KEY_DIRECTIVE)
_test("record_loss triggers persist", raw is not None)
_test("struggling directive saved", "struggling" in raw.get("directives", {}))


# ═══════════════════════════════════════════════════════════════════════════════
# 10. get_directive_memory(persist=True) Singleton
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. get_directive_memory Singleton")
_reset()

reset_directive_memory()
dm1 = get_directive_memory(persist=True)
dm2 = get_directive_memory()

_test("singleton returns same instance", dm1 is dm2)
_test("persist flag set", dm1._persist is True)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. GoalRegistry persist=True — Save and Load
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. GoalRegistry persist=True — Save and Load")
_reset()

reg = GoalRegistry(persist=True)
reg.add_goal(
    GoalState(
        goal_id="close_sale",
        description="Close the coaching sale",
        success_criteria={"domain": "sales"},
        priority=0.9,
    )
)
reg.add_goal(
    GoalState(
        goal_id="analyze",
        description="Analyze architecture",
        success_criteria={"domain": "tech"},
        priority=0.7,
    )
)

tracker_cs = reg.get_tracker("close_sale")
tracker_cs.update_success(0.8)
tracker_cs.record_delta(0.1)

tracker_an = reg.get_tracker("analyze")
tracker_an.update_success(0.6)

reg.advance_turn()
reg.advance_turn()

reg.persist_trackers()
flush()

raw = _mock_store.get(STORAGE_KEY_TRACKERS)
_test("GoalRegistry persist writes", raw is not None)
_test("close_sale tracker present", "close_sale" in raw.get("trackers", {}))
_test("analyze tracker present", "analyze" in raw.get("trackers", {}))
_test("registry_turn preserved", raw["registry_turn"] == 2)
_test(
    "close_sale success_score",
    raw["trackers"]["close_sale"]["success_score"] == round(0.8, 4),
    f"got {raw['trackers']['close_sale']['success_score']}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. GoalRegistry persist=True — Cold Load Hydrates Trackers
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. GoalRegistry Cold Load Hydrates Trackers")

reg2 = GoalRegistry(persist=True)

_test("cold load has trackers", len(reg2.get_all_trackers()) > 0)
_test("cold turn restored", reg2.turn == 2, f"got {reg2.turn}")

t_cs = reg2.get_tracker("close_sale")
_test("close_sale tracker hydrated", t_cs is not None)
_test(
    "close_sale success_score restored",
    abs(t_cs.success_score - 0.8) < 0.001,
    f"got {t_cs.success_score}",
)
_test("close_sale uses restored", t_cs.uses == 1, f"got {t_cs.uses}")

t_an = reg2.get_tracker("analyze")
_test("analyze tracker hydrated", t_an is not None)
_test(
    "analyze success_score restored",
    abs(t_an.success_score - 0.6) < 0.001,
    f"got {t_an.success_score}",
)

# Goals NOT hydrated (by design — caller re-adds them)
_test("goals not persisted", reg2.size == 0)

# Re-add goals — trackers should survive (not overwritten)
reg2.add_goal(
    GoalState(
        goal_id="close_sale",
        description="Close sale",
        priority=0.9,
    )
)
t_cs2 = reg2.get_tracker("close_sale")
_test(
    "tracker survives goal re-add",
    abs(t_cs2.success_score - 0.8) < 0.001,
    f"got {t_cs2.success_score}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. GoalRegistry persist=False — No Side Effects
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. GoalRegistry persist=False — No Side Effects")
_reset()

reg_np = GoalRegistry(persist=False)
reg_np.add_goal(GoalState(goal_id="test_g", description="test", priority=0.5))
reg_np.get_tracker("test_g").update_success(0.9)
reg_np.persist_trackers()
flush()

raw = _mock_store.get(STORAGE_KEY_TRACKERS)
_test("persist=False does not write", raw is None)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Deterministic Reload
# ═══════════════════════════════════════════════════════════════════════════════

_section("14. Deterministic Reload")
_reset()

dm_det = DirectiveMemory(persist=True)
for i in range(FLUSH_INTERVAL + 1):
    dm_det.record_win("a", 0.8)
    dm_det.record_win("b", 0.6)
flush()

dm_a = DirectiveMemory(persist=True)
dm_b = DirectiveMemory(persist=True)

_test("two loads same global_turn", dm_a.global_turn == dm_b.global_turn)
_test("two loads same has_data", dm_a.has_data() == dm_b.has_data())
_test("two loads same ranking", dm_a.to_dict() == dm_b.to_dict())


# ═══════════════════════════════════════════════════════════════════════════════
# 15. DecisionTrace — memory_persisted and memory_version
# ═══════════════════════════════════════════════════════════════════════════════

_section("15. DecisionTrace Persistence Fields")
_reset()

trace = build_trace(
    turn_id=1,
    memory_persisted=True,
    memory_version=5,
)
_test("memory_persisted set", trace.memory_persisted is True)
_test("memory_version set", trace.memory_version == 5)

d = trace.to_dict()
_test("memory_persisted in dict", d.get("memory_persisted") is True)
_test("memory_version in dict", d.get("memory_version") == 5)

trace_none = build_trace(turn_id=2)
_test("memory_persisted None by default", trace_none.memory_persisted is None)
_test("memory_version None by default", trace_none.memory_version is None)

d_none = trace_none.to_dict()
_test("memory_persisted absent when None", "memory_persisted" not in d_none)
_test("memory_version absent when None", "memory_version" not in d_none)


# ═══════════════════════════════════════════════════════════════════════════════
# 16. SessionRuntime — persist_memory flag
# ═══════════════════════════════════════════════════════════════════════════════

_section("16. SessionRuntime — persist_memory Flag")
_reset()

from unittest.mock import MagicMock

mock_ctx = MagicMock()

session = SessionRuntime(mock_ctx, session_id="persist-test", persist_memory=True)
_test("persist_memory_enabled True", session.persist_memory_enabled is True)
_test("memory_version starts at 0", session.memory_version == 0)

session_np = SessionRuntime(mock_ctx, session_id="no-persist", persist_memory=False)
_test("persist_memory_enabled False", session_np.persist_memory_enabled is False)


# ═══════════════════════════════════════════════════════════════════════════════
# 17. SessionRuntime — set_goals creates persistent registry
# ═══════════════════════════════════════════════════════════════════════════════

_section("17. SessionRuntime — set_goals Persistent Registry")
_reset()

session_g = SessionRuntime(mock_ctx, session_id="goals-persist", persist_memory=True)
session_g.set_goals(
    [
        GoalState(goal_id="g1", description="goal 1", priority=0.9),
        GoalState(goal_id="g2", description="goal 2", priority=0.7),
    ]
)

reg_g = session_g.get_goal_registry()
_test("goal registry created", reg_g is not None)
_test(
    "goal registry has persist", hasattr(reg_g, "_persist") and reg_g._persist is True
)


# ═══════════════════════════════════════════════════════════════════════════════
# 18. No LLM Calls
# ═══════════════════════════════════════════════════════════════════════════════

_section("18. No LLM Calls")
_reset()

import umh.runtime_engine.persistence as persist_mod
import umh.runtime_engine.directive_memory as dm_mod
import umh.goals.state as gs_mod

src_persist = open(persist_mod.__file__).read()
src_dm = open(dm_mod.__file__).read()
src_gs = open(gs_mod.__file__).read()

for src, name in [
    (src_persist, "persistence.py"),
    (src_dm, "directive_memory.py"),
    (src_gs, "goal_state.py"),
]:
    _test(
        f"no call_with_fallback in {name}",
        "call_with_fallback" not in src,
    )
    _test(
        f"no model_router in {name}",
        "model_router" not in src,
    )
    _test(
        f"no agent_runtime in {name}",
        "agent_runtime" not in src,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 19. ExecutionSpine Unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("19. ExecutionSpine Unchanged")

src_spine = open("/opt/OS/eos/execution_spine.py").read()
_test("spine has no persistence import", "from eos.persistence" not in src_spine)
_test("spine has no save_directive", "save_directive" not in src_spine)
_test("spine has no save_goal_trackers", "save_goal_trackers" not in src_spine)


# ═══════════════════════════════════════════════════════════════════════════════
# 20. No Regression — StrategyMemory Persistence Still Works
# ═══════════════════════════════════════════════════════════════════════════════

_section("20. No Regression — StrategyMemory Persistence")
_reset()

from umh.strategy.memory import StrategyMemory

sm = StrategyMemory(persist=True)
for _ in range(FLUSH_INTERVAL):
    sm.record_win("clarity", 0.9)
flush()

from umh.runtime_engine.persistence import STORAGE_KEY_STRATEGY

raw = _mock_store.get(STORAGE_KEY_STRATEGY)
_test("strategy memory still saves", raw is not None)
_test("strategy data present", "clarity" in raw.get("strategies", {}))

sm_cold = StrategyMemory(persist=True)
_test("strategy cold load works", sm_cold.has_data())
_test("strategy uses correct", sm_cold.get_stats("clarity").uses == FLUSH_INTERVAL)


# ═══════════════════════════════════════════════════════════════════════════════
# 21. Buffer Batching — Directive + Tracker Interleaved
# ═══════════════════════════════════════════════════════════════════════════════

_section("21. Buffer Batching — Interleaved Writes")
_reset()

save_directive_memory({"x": {"name": "x", "uses": 1}}, global_turn=1)
save_goal_trackers({"g": {"goal_id": "g", "uses": 1}}, registry_turn=1)
save_directive_memory({"x": {"name": "x", "uses": 2}}, global_turn=2)
save_goal_trackers({"g": {"goal_id": "g", "uses": 2}}, registry_turn=2)
save_directive_memory({"x": {"name": "x", "uses": 3}}, global_turn=3)

# At FLUSH_INTERVAL=5, this should have auto-flushed
raw_d = _mock_store.get(STORAGE_KEY_DIRECTIVE)
raw_t = _mock_store.get(STORAGE_KEY_TRACKERS)
_test("directive auto-flushed", raw_d is not None)
_test("tracker auto-flushed", raw_t is not None)
_test(
    "directive has latest data",
    raw_d["global_turn"] == 3 if raw_d else False,
    f"got {raw_d}",
)
_test(
    "tracker has latest data",
    raw_t["registry_turn"] == 2 if raw_t else False,
    f"got {raw_t}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 22. Frozen Trace Immutability
# ═══════════════════════════════════════════════════════════════════════════════

_section("22. Frozen Trace Immutability")

trace_f = build_trace(turn_id=1, memory_persisted=True, memory_version=3)
try:
    trace_f.memory_persisted = False
    _test("frozen trace rejects mutation", False, "should have raised")
except AttributeError:
    _test("frozen trace rejects mutation", True)


# ═══════════════════════════════════════════════════════════════════════════════
# 23. EMA Values Persist Correctly Across Restart
# ═══════════════════════════════════════════════════════════════════════════════

_section("23. EMA Values Persist Correctly")
_reset()

dm_ema = DirectiveMemory(persist=True)
dm_ema.record_win("alpha", 1.0)
dm_ema.record_win("alpha", 0.5)
dm_ema.record_win("alpha", 0.8)
dm_ema.record_win("alpha", 0.7)
dm_ema.record_win("alpha", 0.9)
flush()

expected_ema = dm_ema.get_stats("alpha").ema_score

dm_reload = DirectiveMemory(persist=True)
reloaded_ema = dm_reload.get_stats("alpha").ema_score

_test(
    "EMA survives restart",
    abs(reloaded_ema - expected_ema) < 0.001,
    f"expected={expected_ema:.4f}, got={reloaded_ema:.4f}",
)
_test("uses survive restart", dm_reload.get_stats("alpha").uses == 5)
_test("wins survive restart", dm_reload.get_stats("alpha").wins == 5)


# ═══════════════════════════════════════════════════════════════════════════════
# 24. GoalTracker Hydration Preserves Prior Learning
# ═══════════════════════════════════════════════════════════════════════════════

_section("24. GoalTracker Hydration Preserves Prior Learning")
_reset()

reg_h = GoalRegistry(persist=True)
reg_h.add_goal(GoalState(goal_id="sales", description="sales", priority=0.9))

t = reg_h.get_tracker("sales")
for score in [0.6, 0.7, 0.8, 0.75, 0.9]:
    t.update_success(score)
    t.record_delta(score - 0.5)

expected_success = t.success_score
expected_uses = t.uses

reg_h.persist_trackers()
flush()

# Simulate restart: new registry, load persisted trackers
reg_h2 = GoalRegistry(persist=True)
reg_h2.add_goal(GoalState(goal_id="sales", description="sales", priority=0.9))

t2 = reg_h2.get_tracker("sales")
_test(
    "success_score preserved across restart",
    abs(t2.success_score - expected_success) < 0.001,
    f"expected={expected_success:.4f}, got={t2.success_score:.4f}",
)
_test(
    "uses preserved across restart",
    t2.uses == expected_uses,
    f"expected={expected_uses}, got={t2.uses}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 25. Multiple Memory Types Coexist
# ═══════════════════════════════════════════════════════════════════════════════

_section("25. Multiple Memory Types Coexist")
_reset()

save_strategy_memory({"s1": {"name": "s1", "uses": 1}}, global_turn=10)
save_directive_memory({"d1": {"name": "d1", "uses": 2}}, global_turn=20)
save_goal_trackers({"g1": {"goal_id": "g1", "uses": 3}}, registry_turn=30)
flush()

ls = load_strategy_memory()
ld = load_directive_memory()
lt = load_goal_trackers()

_test("strategy loaded independently", ls is not None and ls["global_turn"] == 10)
_test("directive loaded independently", ld is not None and ld["global_turn"] == 20)
_test("trackers loaded independently", lt is not None and lt["registry_turn"] == 30)


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
