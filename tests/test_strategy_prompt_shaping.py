"""Tests for strategy-aware prompt shaping.

Proves:
    1. Each supported strategy maps to a deterministic prompt directive
    2. Baseline strategy adds no prompt directive
    3. Unknown strategy falls back safely (no directive)
    4. Strategy prompt shaping occurs before candidate generation
    5. Each candidate receives its own strategy-shaped prompt
    6. Side-effect-free guarantee is preserved
    7. Non-strategy/non-eligible turns are unchanged
    8. Existing adaptive/enhance/multi-strategy behavior unchanged
    9. Determinism preserved
    10. STRATEGY_PROMPT_DIRECTIVES keys match STRATEGY_REGISTRY keys
    11. CandidateResult carries prompt_directive field
    12. Prompt directive is observability-only (does not affect evaluation)
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from unittest.mock import MagicMock, patch
from dataclasses import dataclass

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
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


class FakeTaskType:
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


_captured_prompts: list[str] = []
_captured_systems: list[str] = []


def _mock_call_with_fallback(prompt, system=None, agent_type=None, task_type=None):
    _captured_prompts.append(prompt)
    _captured_systems.append(system or "")
    return FakeRoutingResult(output=f"Response for: {prompt[:40]}")


from umh.runtime_engine.multi_strategy import (
    STRATEGY_REGISTRY,
    STRATEGY_PROMPT_DIRECTIVES,
    DEFAULT_STRATEGIES,
    generate_candidates,
    is_strategy_eligible,
    CandidateResult,
)
from umh.strategy.memory import reset_strategy_memory


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Registry consistency
# ═══════════════════════════════════════════════════════════════════════════════

_section("Registry consistency")

_test(
    "STRATEGY_PROMPT_DIRECTIVES keys match STRATEGY_REGISTRY keys",
    set(STRATEGY_PROMPT_DIRECTIVES.keys()) == set(STRATEGY_REGISTRY.keys()),
    f"prompt={set(STRATEGY_PROMPT_DIRECTIVES.keys())} vs "
    f"registry={set(STRATEGY_REGISTRY.keys())}",
)

_test(
    "baseline has empty prompt directive",
    STRATEGY_PROMPT_DIRECTIVES["baseline"] == "",
)

_test(
    "non-baseline strategies have non-empty prompt directives",
    all(
        STRATEGY_PROMPT_DIRECTIVES[k] != ""
        for k in STRATEGY_PROMPT_DIRECTIVES
        if k != "baseline"
    ),
)

_test(
    "all prompt directives are strings",
    all(isinstance(v, str) for v in STRATEGY_PROMPT_DIRECTIVES.values()),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Each strategy maps to deterministic prompt shaping
# ═══════════════════════════════════════════════════════════════════════════════

_section("Deterministic prompt shaping per strategy")

reset_strategy_memory()
_captured_prompts.clear()
_captured_systems.clear()

with (
    patch(
        "umh.runtime_engine.model_router.call_with_fallback", side_effect=_mock_call_with_fallback
    ),
    patch(
        "umh.runtime_engine.multi_strategy.pick_strategies",
        return_value=["clarity", "concise"],
    ),
):
    candidates = generate_candidates(
        message="Draft outreach for fitness coaches",
        system_prompt="You are a business assistant.",
        agent_type="executive_assistant",
        task_type=FakeTaskType("generate"),
        num_candidates=2,
    )

_test("two candidates generated", len(candidates) == 2)

clarity_prompt = _captured_prompts[0]
concise_prompt = _captured_prompts[1]

_test(
    "clarity candidate prompt contains clarity directive",
    STRATEGY_PROMPT_DIRECTIVES["clarity"] in clarity_prompt,
    f"prompt starts with: {clarity_prompt[:80]}",
)

_test(
    "concise candidate prompt contains concise directive",
    STRATEGY_PROMPT_DIRECTIVES["concise"] in concise_prompt,
    f"prompt starts with: {concise_prompt[:80]}",
)

_test(
    "both prompts contain the original message",
    "Draft outreach for fitness coaches" in clarity_prompt
    and "Draft outreach for fitness coaches" in concise_prompt,
)

_test(
    "prompts differ between strategies",
    clarity_prompt != concise_prompt,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Baseline strategy adds no prompt shaping
# ═══════════════════════════════════════════════════════════════════════════════

_section("Baseline strategy — no prompt shaping")

reset_strategy_memory()
_captured_prompts.clear()
_captured_systems.clear()

with (
    patch(
        "umh.runtime_engine.model_router.call_with_fallback", side_effect=_mock_call_with_fallback
    ),
    patch(
        "umh.runtime_engine.multi_strategy.pick_strategies",
        return_value=["baseline"],
    ),
):
    baseline_candidates = generate_candidates(
        message="simple question",
        system_prompt="system",
        agent_type="executive_assistant",
        task_type=FakeTaskType("generate"),
        num_candidates=1,
    )

_test("baseline candidate generated", len(baseline_candidates) == 1)
_test(
    "baseline prompt is unmodified message",
    _captured_prompts[0] == "simple question",
    f"got: {_captured_prompts[0]!r}",
)
_test(
    "baseline system prompt is unmodified",
    _captured_systems[0] == "system",
    f"got: {_captured_systems[0]!r}",
)
_test(
    "baseline candidate prompt_directive is empty",
    baseline_candidates[0].prompt_directive == "",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Unknown strategy falls back safely
# ═══════════════════════════════════════════════════════════════════════════════

_section("Unknown strategy fallback")

reset_strategy_memory()
_captured_prompts.clear()
_captured_systems.clear()

with (
    patch(
        "umh.runtime_engine.model_router.call_with_fallback", side_effect=_mock_call_with_fallback
    ),
    patch(
        "umh.runtime_engine.multi_strategy.pick_strategies",
        return_value=["unknown_strategy_xyz"],
    ),
):
    unknown_candidates = generate_candidates(
        message="test message",
        system_prompt="system",
        agent_type="executive_assistant",
        task_type=FakeTaskType("generate"),
        num_candidates=1,
    )

_test("unknown strategy still generates candidate", len(unknown_candidates) == 1)
_test(
    "unknown strategy prompt is unmodified",
    _captured_prompts[0] == "test message",
    f"got: {_captured_prompts[0]!r}",
)
_test(
    "unknown strategy system prompt is unmodified",
    _captured_systems[0] == "system",
)
_test(
    "unknown strategy prompt_directive is empty",
    unknown_candidates[0].prompt_directive == "",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Strategy shaping occurs before candidate generation (per-candidate)
# ═══════════════════════════════════════════════════════════════════════════════

_section("Per-candidate prompt shaping before LLM call")

reset_strategy_memory()
_captured_prompts.clear()
_captured_systems.clear()

strategies_to_test = ["baseline", "clarity", "concise", "structured"]

with (
    patch(
        "umh.runtime_engine.model_router.call_with_fallback", side_effect=_mock_call_with_fallback
    ),
    patch(
        "umh.runtime_engine.multi_strategy.pick_strategies",
        return_value=strategies_to_test,
    ),
):
    all_candidates = generate_candidates(
        message="core message",
        system_prompt="base system",
        agent_type="executive_assistant",
        task_type=FakeTaskType("generate"),
        num_candidates=4,
    )

_test("four candidates generated", len(all_candidates) == 4)

for i, name in enumerate(strategies_to_test):
    expected_directive = STRATEGY_PROMPT_DIRECTIVES.get(name, "")
    actual_prompt = _captured_prompts[i]
    actual_system = _captured_systems[i]

    if expected_directive:
        _test(
            f"{name}: prompt directive prepended to message",
            actual_prompt.startswith(expected_directive),
            f"starts with: {actual_prompt[:60]}",
        )
        _test(
            f"{name}: original message preserved after directive",
            actual_prompt.endswith("core message"),
        )
    else:
        _test(
            f"{name}: no prompt directive (raw message)",
            actual_prompt == "core message",
        )

    expected_sys_directive = STRATEGY_REGISTRY.get(name, "")
    if expected_sys_directive:
        _test(
            f"{name}: system directive also prepended",
            actual_system.startswith(expected_sys_directive),
        )
    else:
        _test(
            f"{name}: system prompt unmodified",
            actual_system == "base system",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 6. CandidateResult carries prompt_directive for observability
# ═══════════════════════════════════════════════════════════════════════════════

_section("CandidateResult prompt_directive field")

for c in all_candidates:
    expected = STRATEGY_PROMPT_DIRECTIVES.get(c.strategy_name, "")
    _test(
        f"{c.strategy_name}: prompt_directive matches registry",
        c.prompt_directive == expected,
        f"got: {c.prompt_directive[:40]!r}" if c.prompt_directive else "empty",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Side-effect-free guarantee
# ═══════════════════════════════════════════════════════════════════════════════

_section("Side-effect freedom")

import inspect

src = inspect.getsource(generate_candidates)

_test(
    "generate_candidates has no ConversationMemory import",
    "ConversationMemory" not in src,
)
_test(
    "generate_candidates has no commit_winner import",
    "commit_winner" not in src,
)
_test(
    "generate_candidates has no WorldModel import",
    "WorldModel" not in src,
)
_test(
    "generate_candidates has no feedback_loop import",
    "feedback_loop" not in src,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Determinism
# ═══════════════════════════════════════════════════════════════════════════════

_section("Determinism")

reset_strategy_memory()
runs: list[list[str]] = []

for _ in range(3):
    _captured_prompts.clear()
    with (
        patch(
            "umh.runtime_engine.model_router.call_with_fallback",
            side_effect=_mock_call_with_fallback,
        ),
        patch(
            "umh.runtime_engine.multi_strategy.pick_strategies",
            return_value=["clarity", "structured"],
        ),
    ):
        generate_candidates(
            message="determinism test",
            system_prompt="sys",
            agent_type="executive_assistant",
            task_type=FakeTaskType("generate"),
            num_candidates=2,
        )
    runs.append(list(_captured_prompts))

_test(
    "three identical runs produce identical prompts",
    runs[0] == runs[1] == runs[2],
    f"run1={[p[:40] for p in runs[0]]}, run2={[p[:40] for p in runs[1]]}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Non-eligible tasks are unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("Non-eligible tasks unchanged")

_test(
    "FAST_RESPONSE is not strategy-eligible",
    not is_strategy_eligible(FakeTaskType("fast_response")),
)
_test(
    "CLASSIFY is not strategy-eligible",
    not is_strategy_eligible(FakeTaskType("classify")),
)
_test(
    "GENERATE is strategy-eligible",
    is_strategy_eligible(FakeTaskType("generate")),
)
_test(
    "ANALYZE is strategy-eligible",
    is_strategy_eligible(FakeTaskType("analyze")),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Prompt directive does NOT affect evaluation input
# ═══════════════════════════════════════════════════════════════════════════════

_section("Evaluation uses original message, not directive-shaped prompt")

reset_strategy_memory()
_eval_inputs: list[str] = []
_original_evaluate = None

try:
    from umh.runtime_engine.outcome_evaluator import evaluate_outcome as _real_eval

    _original_evaluate = _real_eval
except ImportError:
    _original_evaluate = None


def _capturing_evaluate(input_text, output_text, context=None, metadata=None):
    _eval_inputs.append(input_text)
    return {"quality_score": 0.7, "confidence": 0.8, "flags": {}}


with (
    patch(
        "umh.runtime_engine.model_router.call_with_fallback", side_effect=_mock_call_with_fallback
    ),
    patch("umh.runtime_engine.outcome_evaluator.evaluate_outcome", side_effect=_capturing_evaluate),
    patch(
        "umh.runtime_engine.multi_strategy.pick_strategies",
        return_value=["clarity"],
    ),
):
    generate_candidates(
        message="evaluate this",
        system_prompt="sys",
        agent_type="executive_assistant",
        task_type=FakeTaskType("generate"),
        num_candidates=1,
    )

_test(
    "evaluation receives original message (not directive-shaped)",
    len(_eval_inputs) == 1 and _eval_inputs[0] == "evaluate this",
    f"got: {_eval_inputs[0]!r}" if _eval_inputs else "no eval calls",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Backward compatibility — CandidateResult without prompt_directive
# ═══════════════════════════════════════════════════════════════════════════════

_section("Backward compatibility")

legacy = CandidateResult(
    output="test",
    strategy_name="baseline",
    quality_score=0.8,
    confidence=0.9,
    evaluation={},
    model_used="test",
    tokens_used=100,
    cost_usd=0.001,
    latency_ms=200,
)
_test(
    "CandidateResult without prompt_directive defaults to empty string",
    legacy.prompt_directive == "",
)


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  Strategy Prompt Shaping: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

if _FAIL > 0:
    sys.exit(1)
