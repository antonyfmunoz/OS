"""
Tests for Multi-Strategy Execution Layer.

Validates:
    - Multiple candidates generated with different strategies
    - Evaluator scores differ between candidates
    - Best candidate selected by quality_score (tie-break: confidence)
    - Only selected output would be stored (persistence stages called once)
    - Fallback to normal execution for non-eligible task types
    - Fallback when all candidates fail
    - Strategy eligibility check
    - Deterministic selection
"""

import sys
import uuid
from dataclasses import dataclass
from unittest.mock import MagicMock, patch, call

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


from umh.runtime_engine.multi_strategy import (
    CandidateResult,
    generate_candidates,
    is_strategy_eligible,
    pick_strategies,
    run_with_strategies,
    select_best,
    STRATEGY_REGISTRY,
    DEFAULT_STRATEGIES,
)
from umh.strategy.memory import get_strategy_memory, reset_strategy_memory
from umh.runtime_engine.outcome_evaluator import evaluate_outcome

reset_strategy_memory()


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


class FakeTaskType:
    """Mimics TaskType enum for testing."""

    def __init__(self, value: str):
        self.value = value

    def __str__(self):
        return self.value


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
# 1. Strategy eligibility
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. Strategy Eligibility")

_test("GENERATE is eligible", is_strategy_eligible(FakeTaskType("generate")))
_test("ANALYZE is eligible", is_strategy_eligible(FakeTaskType("analyze")))
_test(
    "FAST_RESPONSE not eligible",
    not is_strategy_eligible(FakeTaskType("fast_response")),
)
_test("CLASSIFY not eligible", not is_strategy_eligible(FakeTaskType("classify")))
_test("SCORE not eligible", not is_strategy_eligible(FakeTaskType("score")))
_test("SUMMARIZE not eligible", not is_strategy_eligible(FakeTaskType("summarize")))
_test("None not eligible", not is_strategy_eligible(None))
_test("string generate eligible", is_strategy_eligible(FakeTaskType("generate")))

reset_strategy_memory()

# ═══════════════════════════════════════════════════════════════════════════════
# 2. Multiple candidates generated
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. Candidate Generation")

_call_count = 0
_call_systems: list[str] = []


def _mock_call_with_fallback(prompt, system=None, agent_type=None, task_type=None):
    global _call_count
    _call_count += 1
    _call_systems.append(system or "")
    if _call_count == 1:
        return FakeRoutingResult(
            output="Here is a comprehensive analysis of your business strategy for outreach."
        )
    else:
        return FakeRoutingResult(
            output="Focus on 3 key actions: 1. Send 20 DMs. 2. Track reply rates. 3. Follow up within 24h."
        )


with patch(
    "umh.runtime_engine.model_router.call_with_fallback", side_effect=_mock_call_with_fallback
):
    _call_count = 0
    _call_systems = []
    candidates = generate_candidates(
        message="What should I focus on for outreach?",
        system_prompt="You are a business assistant.",
        agent_type="executive_assistant",
        task_type=FakeTaskType("generate"),
        num_candidates=2,
    )

_test("two candidates generated", len(candidates) == 2, f"got {len(candidates)}")
_test(
    "strategies differ",
    candidates[0].strategy_name != candidates[1].strategy_name,
    f"{candidates[0].strategy_name} vs {candidates[1].strategy_name}",
)
_test(
    "second call has clarity directive in system prompt",
    "clarity" in _call_systems[1].lower() or "precision" in _call_systems[1].lower(),
    _call_systems[1][:100],
)
_test(
    "first call uses base system prompt",
    _call_systems[0] == "You are a business assistant.",
    _call_systems[0][:100],
)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Evaluator scores differ
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Score Differentiation")

_test(
    "candidates have different scores",
    candidates[0].quality_score != candidates[1].quality_score,
    f"{candidates[0].quality_score} vs {candidates[1].quality_score}",
)

_test(
    "scores are floats in [0, 1]",
    all(0.0 <= c.quality_score <= 1.0 for c in candidates),
    f"{[c.quality_score for c in candidates]}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Best candidate selected
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Selection Logic")

best = select_best(candidates)
_test("winner selected", best is not None)
expected_best = max(candidates, key=lambda c: c.quality_score)
_test(
    "highest score wins",
    best.quality_score == expected_best.quality_score,
    f"winner={best.quality_score}, expected={expected_best.quality_score}",
)

# Tie-breaking test
tied_a = _make_candidate("A", "baseline", quality=0.7, confidence=0.9)
tied_b = _make_candidate("B", "clarity", quality=0.7, confidence=0.5)
tie_winner = select_best([tied_a, tied_b])
_test(
    "tie breaks on confidence",
    tie_winner.confidence == 0.9,
    f"winner confidence={tie_winner.confidence}",
)

# Empty candidates
empty_winner = select_best([])
_test("empty candidates → None", empty_winner is None)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Only winner is persisted
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Selective Persistence")


_persist_calls: list[dict] = []


def _mock_persist(**kwargs):
    _persist_calls.append(kwargs)


_spine_calls = 0


class FakeSpine:
    def run(self, **kwargs):
        global _spine_calls
        _spine_calls += 1
        from umh.runtime_engine.execution_spine import SpineResult

        return SpineResult("fallback response")


class FakeUnifiedContext:
    def to_system_prompt(self):
        return "You are a business assistant."


with (
    patch(
        "umh.runtime_engine.model_router.call_with_fallback", side_effect=_mock_call_with_fallback
    ),
    patch("umh.runtime_engine.commit_pipeline.commit_winner") as mock_commit,
    patch("umh.runtime_engine.context.load_context_from_env", return_value=MagicMock()),
    patch(
        "umh.runtime_engine.signal_router.route_signals", return_value=MagicMock(world_model=None)
    ),
    patch("umh.runtime_engine.execution_spine.ExecutionSpine", return_value=FakeSpine()),
):
    _call_count = 0
    result = run_with_strategies(
        message="Draft outreach copy",
        unified_context=FakeUnifiedContext(),
        agent_type="executive_assistant",
        task_type=FakeTaskType("generate"),
        session_id="test-session",
        org_id="test-org",
    )

_test("result returned", len(result) > 0, f"len={len(result)}")
_test(
    "commit_winner called exactly once",
    mock_commit.call_count == 1,
    f"called {mock_commit.call_count} times",
)

commit_kwargs = mock_commit.call_args
_test(
    "commit receives evaluation",
    "evaluation" in commit_kwargs.kwargs,
    str(list(commit_kwargs.kwargs.keys())),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Fallback for non-eligible types
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. Non-Eligible Fallback")

_spine_calls = 0

with patch("umh.runtime_engine.execution_spine.ExecutionSpine", return_value=FakeSpine()):
    _spine_calls = 0
    result = run_with_strategies(
        message="Quick check",
        unified_context=FakeUnifiedContext(),
        agent_type="executive_assistant",
        task_type=FakeTaskType("fast_response"),
    )

_test(
    "non-eligible falls back to spine",
    _spine_calls == 1,
    f"spine called {_spine_calls} times",
)
_test("fallback result returned", "fallback" in str(result).lower())


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Fallback when all candidates fail
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. All-Fail Fallback")


def _mock_fail(*args, **kwargs):
    raise RuntimeError("LLM unavailable")


_spine_calls = 0

with (
    patch("umh.runtime_engine.model_router.call_with_fallback", side_effect=_mock_fail),
    patch("umh.runtime_engine.execution_spine.ExecutionSpine", return_value=FakeSpine()),
):
    _spine_calls = 0
    result = run_with_strategies(
        message="Analyze pipeline",
        unified_context=FakeUnifiedContext(),
        agent_type="executive_assistant",
        task_type=FakeTaskType("generate"),
    )

_test(
    "all-fail falls back to spine",
    _spine_calls == 1,
    f"spine called {_spine_calls} times",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Candidate with higher score wins over lower
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Score-Based Winner Selection")

low = _make_candidate("Bad response", "baseline", quality=0.3, confidence=0.9)
high = _make_candidate(
    "Great targeted response with 5 specific action items",
    "clarity",
    quality=0.85,
    confidence=0.7,
)

winner = select_best([low, high])
_test(
    "higher quality wins even with lower confidence",
    winner.strategy_name == "clarity",
    f"winner={winner.strategy_name} score={winner.quality_score}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Strategy directives are well-formed
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Strategy Registry")

_test(
    "at least 4 strategies in registry",
    len(STRATEGY_REGISTRY) >= 4,
    f"got {len(STRATEGY_REGISTRY)}",
)
_test(
    "baseline has empty directive",
    STRATEGY_REGISTRY.get("baseline") == "",
)
_test(
    "all registry values are strings",
    all(isinstance(v, str) for v in STRATEGY_REGISTRY.values()),
)
_test(
    "default strategies exist in registry",
    all(s in STRATEGY_REGISTRY for s in DEFAULT_STRATEGIES),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Deterministic selection
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. Determinism")

c1 = _make_candidate("A", "baseline", quality=0.6, confidence=0.8)
c2 = _make_candidate("B", "clarity", quality=0.8, confidence=0.7)

r1 = select_best([c1, c2])
r2 = select_best([c1, c2])
_test(
    "same inputs → same winner",
    r1.strategy_name == r2.strategy_name,
    f"{r1.strategy_name} vs {r2.strategy_name}",
)

# Order-independent
r3 = select_best([c2, c1])
_test(
    "order-independent selection",
    r3.strategy_name == r1.strategy_name,
    f"reversed={r3.strategy_name} vs original={r1.strategy_name}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Cost aggregation
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. Cost Aggregation")

with (
    patch(
        "umh.runtime_engine.model_router.call_with_fallback", side_effect=_mock_call_with_fallback
    ),
    patch("umh.runtime_engine.commit_pipeline.commit_winner"),
    patch("umh.runtime_engine.context.load_context_from_env", return_value=MagicMock()),
    patch(
        "umh.runtime_engine.signal_router.route_signals", return_value=MagicMock(world_model=None)
    ),
    patch("umh.runtime_engine.execution_spine.ExecutionSpine", return_value=FakeSpine()),
):
    _call_count = 0
    result = run_with_strategies(
        message="Generate analysis",
        unified_context=FakeUnifiedContext(),
        agent_type="executive_assistant",
        task_type=FakeTaskType("generate"),
        num_candidates=2,
    )

_test(
    "cost aggregated across candidates",
    result.cost_usd >= 0.002,
    f"cost={result.cost_usd}",
)
_test(
    "iterations matches candidate count",
    result.iterations == 2,
    f"iterations={result.iterations}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if _FAIL > 0 else 0)
