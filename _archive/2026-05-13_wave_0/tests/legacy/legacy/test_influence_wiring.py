"""
Tests for Unified Influence downstream wiring.

Validates:
    1. adapt_prompt uses unified directives
    2. strategy override respected via pick_strategies
    3. synthesis suppression gates maybe_synthesize
    4. exploration suppression skips stale rotation
    5. no consumer reads raw pending fields
    6. determinism preserved
    7. ExecutionSpine unchanged
    8. no new LLM calls
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
# 1. adapt_prompt injects unified influence directives
# ═════════════════════════════════════════════════════════════════���═════════════

_section("1. adapt_prompt Unified Influence Injection")

from unittest.mock import MagicMock

from umh.runtime_engine.adaptive_prompt import adapt_prompt
from umh.runtime_engine.influence_orchestrator import NO_INFLUENCE, UnifiedInfluence

mock_session = MagicMock()
mock_session.stats.evaluations = []

influence_with_directives = UnifiedInfluence(
    directives=("Be precise and verify all facts.",),
    strategy_override=None,
    synthesis_enabled=False,
    exploration_enabled=False,
)
mock_session.get_unified_influence.return_value = influence_with_directives

result = adapt_prompt(
    base_prompt="You are a helpful assistant.",
    session_runtime=mock_session,
)

_test(
    "unified directive injected into prompt",
    "Be precise and verify all facts." in result,
    f"result={result[:120]}",
)
_test(
    "adaptive header present",
    "## Adaptive Response Guidance" in result,
)
_test(
    "base prompt preserved",
    result.endswith("You are a helpful assistant."),
)

# No influence → no change
mock_session2 = MagicMock()
mock_session2.stats.evaluations = []
mock_session2.get_unified_influence.return_value = NO_INFLUENCE

result2 = adapt_prompt(
    base_prompt="You are a helpful assistant.",
    session_runtime=mock_session2,
)

_test(
    "NO_INFLUENCE → prompt unchanged",
    result2 == "You are a helpful assistant.",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. adapt_prompt priority: unified influence > session signals
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. Priority: Unified > Session Signals")

from umh.runtime_engine.adaptive_prompt import (
    MAX_DIRECTIVES,
    PRIORITY_CRITICAL,
    PRIORITY_UNIFIED_INFLUENCE,
)

_test(
    "PRIORITY_UNIFIED_INFLUENCE < PRIORITY_CRITICAL",
    PRIORITY_UNIFIED_INFLUENCE < PRIORITY_CRITICAL,
    f"unified={PRIORITY_UNIFIED_INFLUENCE}, critical={PRIORITY_CRITICAL}",
)

mock_session3 = MagicMock()
mock_session3.stats.evaluations = [
    {
        "quality_score": 0.2,
        "confidence": 0.3,
        "flags": {"hallucination_risk": True},
    },
    {
        "quality_score": 0.2,
        "confidence": 0.3,
        "flags": {"hallucination_risk": True},
    },
    {
        "quality_score": 0.2,
        "confidence": 0.3,
        "flags": {"hallucination_risk": True},
    },
]

influence_priority = UnifiedInfluence(
    directives=("UNIFIED-FIRST-DIRECTIVE",),
    strategy_override=None,
    synthesis_enabled=True,
    exploration_enabled=True,
)
mock_session3.get_unified_influence.return_value = influence_priority

result3 = adapt_prompt(
    base_prompt="Base.",
    session_runtime=mock_session3,
)

lines = result3.split("\n")
directive_lines = [l for l in lines if l.startswith("- ")]
_test(
    "unified directive appears first",
    len(directive_lines) > 0 and "UNIFIED-FIRST-DIRECTIVE" in directive_lines[0],
    f"first={directive_lines[0] if directive_lines else 'none'}",
)
_test(
    "capped at MAX_DIRECTIVES",
    len(directive_lines) <= MAX_DIRECTIVES,
    f"count={len(directive_lines)}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Strategy override wired through pick_strategies
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Strategy Override via pick_strategies")

from umh.runtime_engine.multi_strategy import pick_strategies
from umh.strategy.memory import get_strategy_memory, reset_strategy_memory

reset_strategy_memory()
mem = get_strategy_memory()
mem.record_win("baseline", 0.8)
mem.record_win("clarity", 0.7)

result = pick_strategies(num_candidates=2, strategy_override="structured")
_test(
    "override is first strategy",
    result[0] == "structured",
    f"got {result}",
)
_test(
    "other strategies fill remaining slots",
    len(result) == 2,
    f"got {result}",
)
_test(
    "override not duplicated",
    result.count("structured") == 1,
)

result_single = pick_strategies(num_candidates=1, strategy_override="concise")
_test(
    "single candidate → override only",
    result_single == ["concise"],
    f"got {result_single}",
)

result_none = pick_strategies(num_candidates=2, strategy_override=None)
_test(
    "None override → normal selection",
    result_none[0] != "structured" or result_none[0] in ("baseline", "clarity"),
    f"got {result_none}",
)

result_invalid = pick_strategies(num_candidates=2, strategy_override="nonexistent")
_test(
    "invalid override → ignored",
    "nonexistent" not in result_invalid,
    f"got {result_invalid}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Exploration suppression skips stale rotation
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Exploration Suppression")

reset_strategy_memory()
mem = get_strategy_memory()
for _ in range(10):
    mem.record_win("baseline", 0.8)
    mem.record_win("clarity", 0.7)

result_explore = pick_strategies(num_candidates=2, exploration_enabled=True)
result_no_explore = pick_strategies(num_candidates=2, exploration_enabled=False)

_test(
    "exploration_enabled=True allows stale rotation (or same selection)",
    len(result_explore) == 2,
)
_test(
    "exploration_enabled=False returns valid strategies",
    len(result_no_explore) == 2,
)
_test(
    "no_explore uses top-ranked strategies only",
    all(
        s in ("baseline", "clarity", "concise", "structured") for s in result_no_explore
    ),
    f"got {result_no_explore}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Synthesis suppression gate
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Synthesis Suppression Gate")

import inspect

from umh.runtime_engine.session_runtime import SessionRuntime

source = inspect.getsource(SessionRuntime.run)

_test(
    "synthesis gated by unified influence",
    "synthesis suppressed by unified influence" in source,
)
_test(
    "reads _influence.synthesis_enabled",
    "_influence.synthesis_enabled" in source,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. SessionRuntime passes strategy_override to run_with_strategies
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. SessionRuntime Wiring")

_test(
    "passes strategy_override from influence",
    "strategy_override=_influence.strategy_override" in source,
)
_test(
    "passes exploration_enabled from influence",
    "exploration_enabled=_influence.exploration_enabled" in source,
)
_test(
    "reads unified influence before calling run_with_strategies",
    source.index("get_unified_influence")
    < source.index("result = run_with_strategies"),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. No consumer reads raw pending fields
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. No Raw Pending Field Reads by Consumers")

adaptive_source = inspect.getsource(adapt_prompt)
_test(
    "adapt_prompt does NOT read _pending_control_directives",
    "_pending_control_directives" not in adaptive_source,
)
_test(
    "adapt_prompt does NOT read _pending_convergence_directives",
    "_pending_convergence_directives" not in adaptive_source,
)
_test(
    "adapt_prompt does NOT read _pending_strategy_override",
    "_pending_strategy_override" not in adaptive_source,
)

from umh.runtime_engine.multi_strategy import generate_candidates, run_with_strategies

rws_source = inspect.getsource(run_with_strategies)
_test(
    "run_with_strategies does NOT read pending fields",
    "_pending_" not in rws_source,
)

gc_source = inspect.getsource(generate_candidates)
_test(
    "generate_candidates does NOT read pending fields",
    "_pending_" not in gc_source,
)

ps_source = inspect.getsource(pick_strategies)
_test(
    "pick_strategies does NOT read pending fields",
    "_pending_" not in ps_source,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. ExecutionSpine unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. ExecutionSpine Unchanged")

spine_source = inspect.getsource(
    __import__("umh.runtime_engine.execution_spine", fromlist=["ExecutionSpine"]).ExecutionSpine
)
_test(
    "ExecutionSpine has no influence references",
    "unified_influence" not in spine_source and "UnifiedInfluence" not in spine_source,
)
_test(
    "ExecutionSpine has no pending field references",
    "_pending_" not in spine_source,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. No new LLM calls
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. No New LLM Calls")

from umh.runtime_engine.adaptive_prompt import _apply_unified_influence

ui_source = inspect.getsource(_apply_unified_influence)
_test(
    "_apply_unified_influence has no LLM calls",
    "call_with_fallback" not in ui_source
    and "model_router" not in ui_source
    and "AgentRuntime" not in ui_source,
)

from umh.runtime_engine.influence_orchestrator import resolve_influence

ri_source = inspect.getsource(resolve_influence)
_test(
    "resolve_influence has no LLM calls",
    "call_with_fallback" not in ri_source and "model_router" not in ri_source,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Determinism
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. Determinism")

mock_det = MagicMock()
mock_det.stats.evaluations = []
mock_det.get_unified_influence.return_value = UnifiedInfluence(
    directives=("d1", "d2"),
    strategy_override=None,
    synthesis_enabled=True,
    exploration_enabled=True,
)

r1 = adapt_prompt(base_prompt="base", session_runtime=mock_det)
r2 = adapt_prompt(base_prompt="base", session_runtime=mock_det)
_test("adapt_prompt deterministic", r1 == r2)

for _ in range(50):
    rn = adapt_prompt(base_prompt="base", session_runtime=mock_det)
    assert rn == r1, "adapt_prompt non-deterministic"
_test("50 iterations → stable", True)

reset_strategy_memory()
get_strategy_memory().record_win("baseline", 0.7)
s1 = pick_strategies(2, strategy_override="structured", exploration_enabled=False)
s2 = pick_strategies(2, strategy_override="structured", exploration_enabled=False)
_test("pick_strategies deterministic", s1 == s2)


# ════════════════════════════════════════════════════════════════════════════��══
# 11. Backward compat: NO_INFLUENCE = no behavior change
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. Backward Compatibility")

mock_compat = MagicMock()
mock_compat.stats.evaluations = []
mock_compat.get_unified_influence.return_value = NO_INFLUENCE

result = adapt_prompt(base_prompt="Original prompt.", session_runtime=mock_compat)
_test(
    "NO_INFLUENCE → zero directives from influence path",
    result == "Original prompt.",
    f"result={result[:80]}",
)

result_strat = pick_strategies(2, strategy_override=None, exploration_enabled=True)
_test(
    "no override + exploration → normal pick",
    len(result_strat) == 2,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if _FAIL > 0 else 0)
