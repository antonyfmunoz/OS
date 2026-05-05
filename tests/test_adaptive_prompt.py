"""
Tests for the Adaptive Prompt Layer.

Validates:
    - No signals → prompt unchanged
    - Low-quality streak → precision directive injected
    - Hallucination flags → grounding directive injected
    - Incomplete flags → conclusion directive injected
    - Low-information flags → substance directive injected
    - High-confidence world model patterns → pattern directive injected
    - SessionRuntime records evaluations
    - ContextBuilder accepts session_runtime param
    - Integration: evaluation history influences adaptation
"""

import sys
import uuid

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


from umh.runtime_engine.adaptive_prompt import adapt_prompt


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers — minimal stubs
# ═══════════════════════════════════════════════════════════════════════════════


class FakeCtx:
    org_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000002")


def _make_session(evaluations: list[dict] | None = None):
    from umh.runtime_engine.session_runtime import SessionRuntime

    session = SessionRuntime(FakeCtx(), session_id="test-adaptive")
    if evaluations:
        session.stats.evaluations = evaluations
    return session


def _make_evaluation(
    quality_score: float = 0.7,
    hallucination_risk: bool = False,
    low_information: bool = False,
    incomplete: bool = False,
) -> dict:
    return {
        "quality_score": quality_score,
        "confidence": 0.8,
        "flags": {
            "hallucination_risk": hallucination_risk,
            "low_information": low_information,
            "incomplete": incomplete,
        },
        "reason": "test",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 1. No signals → prompt unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. No Signals")

base = "You are a helpful assistant."
result = adapt_prompt(base)
_test("no args → unchanged", result == base)

result2 = adapt_prompt(base, session_runtime=_make_session())
_test("empty session → unchanged", result2 == base)

result3 = adapt_prompt(
    base,
    session_runtime=_make_session(
        [
            _make_evaluation(0.8),
            _make_evaluation(0.75),
            _make_evaluation(0.9),
        ]
    ),
)
_test("high-quality evaluations → unchanged", result3 == base)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Low-quality streak
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. Low-Quality Streak")

low_evals = [_make_evaluation(0.3), _make_evaluation(0.2), _make_evaluation(0.35)]
session = _make_session(low_evals)
result = adapt_prompt(base, session_runtime=session)

_test("low quality streak → prompt modified", result != base)
_test(
    "precision directive present",
    "precise" in result.lower() or "reduce verbosity" in result.lower(),
    result[:200],
)
_test("original prompt preserved", base in result)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Hallucination flags
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Hallucination Flags")

halluc_evals = [
    _make_evaluation(0.6, hallucination_risk=True),
    _make_evaluation(0.5, hallucination_risk=True),
    _make_evaluation(0.7, hallucination_risk=False),
]
session = _make_session(halluc_evals)
result = adapt_prompt(base, session_runtime=session)

_test("hallucination flags → prompt modified", result != base)
_test(
    "grounding directive present",
    "uncertain" in result.lower() or "confident" in result.lower(),
    result[:200],
)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Incomplete flags
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Incomplete Flags")

incomplete_evals = [
    _make_evaluation(0.6, incomplete=True),
    _make_evaluation(0.5, incomplete=True),
    _make_evaluation(0.7, incomplete=False),
]
session = _make_session(incomplete_evals)
result = adapt_prompt(base, session_runtime=session)

_test("incomplete flags → prompt modified", result != base)
_test(
    "conclusion directive present",
    "conclusion" in result.lower() or "complete" in result.lower(),
    result[:200],
)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Low-information flags
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Low-Information Flags")

low_info_evals = [
    _make_evaluation(0.3, low_information=True),
    _make_evaluation(0.2, low_information=True),
    _make_evaluation(0.7, low_information=False),
]
session = _make_session(low_info_evals)
result = adapt_prompt(base, session_runtime=session)

_test("low-info flags → prompt modified", result != base)
_test(
    "substance directive present",
    "substance" in result.lower() or "actionable" in result.lower(),
    result[:200],
)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. World model high-confidence patterns
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. World Model Patterns")

from umh.world.model import WorldModel

wm = WorldModel(org_id="test_adaptive")

# Add a high-confidence good outcome entry
wm.update_from_interaction(
    "What should I focus on?",
    "Send 20 DMs to prospects in your ICP and track reply rates",
    outcome="good",
)

# Manually boost confidence above threshold for the test
entries = wm.instance.get_entries()
for e in entries:
    if "[outcome=good]" in e.content:
        e.confidence = 0.7
        from dataclasses import asdict

        key = wm.instance._key(e.entry_type, e.id)
        wm.instance._store.put(key, asdict(e))

result = adapt_prompt(base, world_model=wm)
_test(
    "high-confidence good pattern → prompt modified",
    result != base,
    f"len={len(result)} vs base={len(base)}",
)
if result != base:
    _test(
        "pattern reference present",
        "high-performing response patterns" in result.lower()
        or "resembled" in result.lower(),
        result[:300],
    )
else:
    _test("pattern reference present", False, "prompt was not modified")


# ═══════════════════════════════════════════════════════════════════════════════
# 7. World model with no good patterns → unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. World Model No Patterns")

wm_empty = WorldModel(org_id="test_adaptive_empty")
result = adapt_prompt(base, world_model=wm_empty)
_test("no good patterns → unchanged", result == base)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Multiple directives combine
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Combined Directives")

combined_evals = [
    _make_evaluation(0.2, hallucination_risk=True, low_information=True),
    _make_evaluation(0.3, hallucination_risk=True, low_information=True),
    _make_evaluation(0.1, incomplete=True, low_information=True),
]
session = _make_session(combined_evals)
result = adapt_prompt(base, session_runtime=session)

directive_count = result.count("- ")
_test(
    "multiple directives present",
    directive_count >= 3,
    f"found {directive_count} directives",
)
_test("adaptive header present", "Adaptive Response Guidance" in result)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. SessionRuntime records evaluations
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. SessionRuntime Evaluation Recording")

from umh.runtime_engine.session_runtime import SessionRuntime, SessionStats

stats = SessionStats()
_test("evaluations list exists", hasattr(stats, "evaluations"))
_test("evaluations starts empty", len(stats.evaluations) == 0)

stats.evaluations.append(_make_evaluation(0.7))
_test("can append evaluation", len(stats.evaluations) == 1)
_test(
    "evaluation has quality_score",
    stats.evaluations[0]["quality_score"] == 0.7,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. ContextBuilder accepts session_runtime
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. ContextBuilder Integration")

import inspect
from umh.runtime_engine.context_builder import ContextBuilder, UnifiedContext

sig = inspect.signature(ContextBuilder.build)
_test(
    "ContextBuilder.build has session_runtime param",
    "session_runtime" in sig.parameters,
)

_test(
    "UnifiedContext has adaptive_directives field",
    hasattr(UnifiedContext(), "adaptive_directives"),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Gateway passes session_runtime to ContextBuilder
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. Gateway Integration")

from umh.runtime_engine.gateway import EOSGateway

source = inspect.getsource(EOSGateway)
_test(
    "gateway passes session_runtime to build()",
    "session_runtime=_session" in source,
)
_test(
    "gateway gets session before building context",
    source.index("get_session(session_id") < source.index("builder.build("),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Adaptation is deterministic
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. Determinism")

det_evals = [_make_evaluation(0.2), _make_evaluation(0.3), _make_evaluation(0.1)]
det_session = _make_session(det_evals)
r1 = adapt_prompt(base, session_runtime=det_session)
r2 = adapt_prompt(base, session_runtime=det_session)
_test("same inputs → same output", r1 == r2)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. adapt_prompt preserves full base prompt
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. Base Prompt Preservation")

long_base = "System prompt with many details. " * 50
det_session2 = _make_session(det_evals)
result = adapt_prompt(long_base, session_runtime=det_session2)
_test("long base prompt fully preserved", long_base in result)


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if _FAIL > 0 else 0)
