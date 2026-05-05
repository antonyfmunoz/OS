"""
Tests for the Unified Influence Orchestrator.

Validates:
    1. Deterministic merge (same inputs → same output)
    2. Control overrides everything
    3. Convergence suppresses synthesis correctly
    4. Strategy override respected when allowed
    5. Deduplication works
    6. No ordering instability
    7. SessionRuntime uses orchestrator only
    8. No regressions (backward compatibility)
    9. DecisionTrace includes unified_influence
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


from umh.runtime_engine.influence_orchestrator import (
    NO_INFLUENCE,
    UnifiedInfluence,
    resolve_influence,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. UnifiedInfluence immutability and serialization
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. UnifiedInfluence Structure")

ui = UnifiedInfluence(
    directives=("a", "b"),
    strategy_override="structured",
    synthesis_enabled=False,
    exploration_enabled=True,
)

_test("frozen dataclass", hasattr(ui, "__dataclass_fields__"))

try:
    ui.synthesis_enabled = True
    _test("mutation blocked", False, "should have raised")
except AttributeError:
    _test("mutation blocked", True)

_test("directives is tuple", isinstance(ui.directives, tuple))

d = ui.to_dict()
_test("to_dict has directives", d["directives"] == ["a", "b"])
_test("to_dict has strategy_override", d["strategy_override"] == "structured")
_test("to_dict has synthesis_enabled", d["synthesis_enabled"] is False)
_test("to_dict has exploration_enabled", d["exploration_enabled"] is True)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. NO_INFLUENCE sentinel
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. NO_INFLUENCE Sentinel")

_test("NO_INFLUENCE is UnifiedInfluence", isinstance(NO_INFLUENCE, UnifiedInfluence))
_test("no directives", NO_INFLUENCE.directives == ())
_test("no strategy override", NO_INFLUENCE.strategy_override is None)
_test("synthesis enabled", NO_INFLUENCE.synthesis_enabled is True)
_test("exploration enabled", NO_INFLUENCE.exploration_enabled is True)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. No inputs → NO_INFLUENCE
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. No Inputs (Backward Compatibility)")

result = resolve_influence()
_test("no inputs → NO_INFLUENCE", result is NO_INFLUENCE)

result2 = resolve_influence(
    control_directives=[],
    convergence_directives=[],
    strategy_override=None,
    synthesis_suppressed=False,
    exploration_suppressed=False,
)
_test("explicit empty → NO_INFLUENCE", result2 is NO_INFLUENCE)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Deterministic merge
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Deterministic Merge")

kwargs = dict(
    control_directives=["ctrl-1", "ctrl-2"],
    convergence_directives=["conv-1"],
    strategy_override="structured",
    synthesis_suppressed=True,
    exploration_suppressed=False,
)

r1 = resolve_influence(**kwargs)
r2 = resolve_influence(**kwargs)

_test("same directives", r1.directives == r2.directives)
_test("same strategy_override", r1.strategy_override == r2.strategy_override)
_test("same synthesis_enabled", r1.synthesis_enabled == r2.synthesis_enabled)
_test("same exploration_enabled", r1.exploration_enabled == r2.exploration_enabled)
_test("same to_dict", r1.to_dict() == r2.to_dict())

for _ in range(100):
    rn = resolve_influence(**kwargs)
    assert rn.directives == r1.directives, "ordering instability detected"
_test("100 iterations → stable ordering", True)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Control overrides everything
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Control Overrides Everything")

result = resolve_influence(
    control_directives=["be precise", "verify facts"],
    convergence_directives=["simplify"],
    strategy_override="creative",
    synthesis_suppressed=False,
    exploration_suppressed=False,
)

_test(
    "control directives come first",
    result.directives[:2] == ("be precise", "verify facts"),
)
_test("convergence appended after", result.directives[2] == "simplify")
_test(
    "strategy override blocked by control",
    result.strategy_override is None,
    f"got {result.strategy_override}",
)
_test("synthesis disabled by control", result.synthesis_enabled is False)
_test("exploration disabled by control", result.exploration_enabled is False)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Convergence suppresses synthesis correctly
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. Convergence Suppression")

result = resolve_influence(
    control_directives=[],
    convergence_directives=["focus on consistency"],
    synthesis_suppressed=True,
    exploration_suppressed=False,
)

_test("synthesis disabled by convergence", result.synthesis_enabled is False)
_test("exploration NOT disabled", result.exploration_enabled is True)
_test("convergence directive present", "focus on consistency" in result.directives)

result2 = resolve_influence(
    control_directives=[],
    convergence_directives=["stabilize"],
    synthesis_suppressed=True,
    exploration_suppressed=True,
)

_test("both suppressed", result2.synthesis_enabled is False)
_test("both suppressed (exploration)", result2.exploration_enabled is False)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Strategy override respected when allowed
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Strategy Override")

result = resolve_influence(
    control_directives=[],
    convergence_directives=["improve accuracy"],
    strategy_override="structured",
)

_test(
    "strategy override passes when no control",
    result.strategy_override == "structured",
)

result2 = resolve_influence(
    control_directives=["ctrl"],
    strategy_override="structured",
)

_test(
    "strategy override blocked when control active",
    result2.strategy_override is None,
)

result3 = resolve_influence(strategy_override="analytical")

_test(
    "strategy override alone works",
    result3.strategy_override == "analytical",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Deduplication
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Deduplication")

result = resolve_influence(
    control_directives=["be precise", "verify facts"],
    convergence_directives=["be precise", "simplify"],
)

_test(
    "duplicate removed",
    result.directives.count("be precise") == 1,
    f"got {result.directives}",
)
_test(
    "first occurrence kept (control priority)",
    result.directives.index("be precise") < result.directives.index("simplify"),
)
_test("total 3 directives", len(result.directives) == 3)

result2 = resolve_influence(
    control_directives=["same", "same"],
    convergence_directives=["same"],
)

_test(
    "intra-list dedup",
    result2.directives == ("same",),
    f"got {result2.directives}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Ordering stability (no randomness)
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Ordering Stability")

ctrl = ["c1", "c2", "c3"]
conv = ["v1", "v2"]

result = resolve_influence(control_directives=ctrl, convergence_directives=conv)
expected = ("c1", "c2", "c3", "v1", "v2")
_test(
    "control before convergence always",
    result.directives == expected,
    f"got {result.directives}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. DecisionTrace includes unified_influence
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. DecisionTrace Integration")

from umh.runtime_engine.decision_trace import DecisionTrace, build_trace
from umh.strategy.memory import get_strategy_memory, reset_strategy_memory

reset_strategy_memory()
get_strategy_memory().record_win("baseline", 0.7)

ui_dict = {
    "directives": ["be precise"],
    "strategy_override": None,
    "synthesis_enabled": False,
    "exploration_enabled": False,
}

trace = build_trace(turn_id=1, unified_influence=ui_dict)
_test("unified_influence on trace", trace.unified_influence == ui_dict)
_test("unified_influence in to_dict", "unified_influence" in trace.to_dict())
_test(
    "to_dict value matches",
    trace.to_dict()["unified_influence"] == ui_dict,
)

trace_none = build_trace(turn_id=2)
_test("None by default", trace_none.unified_influence is None)
_test("not in to_dict when None", "unified_influence" not in trace_none.to_dict())


# ═══════════════════════════════════════════════════════════════════════════════
# 11. SessionRuntime integration
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. SessionRuntime Integration")

from unittest.mock import MagicMock

from umh.runtime_engine.session_runtime import SessionRuntime

mock_ctx = MagicMock()

session = SessionRuntime(mock_ctx, session_id="test-influence")
_test("_unified_influence starts None", session._unified_influence is None)

influence = session.get_unified_influence()
_test("get_unified_influence returns NO_INFLUENCE initially", influence is NO_INFLUENCE)
_test("synthesis enabled by default", influence.synthesis_enabled is True)
_test("exploration enabled by default", influence.exploration_enabled is True)
_test("no directives by default", influence.directives == ())


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Edge cases
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. Edge Cases")

result = resolve_influence(control_directives=None, convergence_directives=None)
_test("None lists → NO_INFLUENCE", result is NO_INFLUENCE)

result = resolve_influence(synthesis_suppressed=True)
_test("suppression alone creates influence", result is not NO_INFLUENCE)
_test("suppression alone disables synthesis", result.synthesis_enabled is False)
_test("suppression alone keeps exploration", result.exploration_enabled is True)
_test("suppression alone no directives", result.directives == ())

result = resolve_influence(exploration_suppressed=True)
_test("exploration suppression alone", result.exploration_enabled is False)
_test("exploration suppression keeps synthesis", result.synthesis_enabled is True)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Control-only (no convergence)
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. Control Only")

result = resolve_influence(control_directives=["verify"])
_test("control only → directives", result.directives == ("verify",))
_test("control only → no override", result.strategy_override is None)
_test("control only → synthesis off", result.synthesis_enabled is False)
_test("control only → exploration off", result.exploration_enabled is False)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Convergence-only (no control)
# ═══════════════════════════════════════════════════════════════════════════════

_section("14. Convergence Only")

result = resolve_influence(
    convergence_directives=["simplify"],
    synthesis_suppressed=False,
    exploration_suppressed=True,
)
_test("conv only → directives", result.directives == ("simplify",))
_test("conv only → synthesis still on", result.synthesis_enabled is True)
_test("conv only → exploration off", result.exploration_enabled is False)


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if _FAIL > 0 else 0)
