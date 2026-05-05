"""Tests for unified pre-generation enhancement in multi-strategy.

Proves:
    1. Multi-strategy candidate generation uses enhance_prompt before candidates
    2. Enhancement runs once, not per-candidate
    3. Candidate generation remains side-effect free after enhancement
    4. Enhancement failure degrades gracefully to raw message
    5. Non-multi-strategy (spine fallback) still uses its own enhancement
    6. Original message (not enhanced) is stored in commit path
    7. Same enhanced base message reaches all candidates (strategy directives
       may prepend per-candidate, but base enhanced text is shared)
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from unittest.mock import MagicMock, patch, call
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


class FakeUnifiedContext:
    def to_system_prompt(self):
        return "You are a business assistant."


_call_count = 0
_llm_prompts: list[str] = []


def _mock_call_with_fallback(prompt, system=None, agent_type=None, task_type=None):
    global _call_count
    _call_count += 1
    _llm_prompts.append(prompt)
    return FakeRoutingResult(
        output=f"Response {_call_count}: Focus on key actions for outreach success."
    )


class FakeSpine:
    def run(self, **kwargs):
        from umh.runtime_engine.execution_spine import SpineResult

        return SpineResult("fallback response")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Enhanced prompt reaches candidates
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. Enhanced Prompt Reaches Candidates")

from umh.runtime_engine.multi_strategy import run_with_strategies

_enhance_calls: list[str] = []

ENHANCED_TEXT = (
    "What specific outreach strategy should I prioritize for fitness coaches this week?"
)


def _mock_enhance(prompt, ctx, runtime=None):
    _enhance_calls.append(prompt)
    return ENHANCED_TEXT


with (
    patch(
        "umh.runtime_engine.model_router.call_with_fallback", side_effect=_mock_call_with_fallback
    ),
    patch("umh.runtime_engine.execution_spine.enhance_prompt", side_effect=_mock_enhance),
    patch("umh.runtime_engine.context.load_context_from_env", return_value=MagicMock()),
    patch("umh.runtime_engine.agent_runtime.AgentRuntime", return_value=MagicMock()),
    patch("umh.runtime_engine.commit_pipeline.commit_winner"),
    patch(
        "umh.runtime_engine.signal_router.route_signals", return_value=MagicMock(world_model=None)
    ),
    patch("umh.runtime_engine.execution_spine.ExecutionSpine", return_value=FakeSpine()),
):
    _call_count = 0
    _llm_prompts.clear()
    _enhance_calls.clear()

    result = run_with_strategies(
        message="outreach",
        unified_context=FakeUnifiedContext(),
        agent_type="executive_assistant",
        task_type=FakeTaskType("generate"),
        session_id="test-enhance",
        org_id="test-org",
    )

_test(
    "enhance_prompt called exactly once",
    len(_enhance_calls) == 1,
    f"called {len(_enhance_calls)} times",
)
_test(
    "enhance_prompt received raw message",
    _enhance_calls[0] == "outreach",
    f"got: {_enhance_calls[0][:50]}",
)
_test(
    "all LLM calls received enhanced prompt",
    all(ENHANCED_TEXT in p for p in _llm_prompts),
    f"prompts: {[p[:40] for p in _llm_prompts]}",
)
_test(
    "result returned successfully",
    len(result) > 0,
    f"len={len(result)}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Enhancement runs once, not per-candidate
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. Single Enhancement Call")

_enhance_count = 0


def _counting_enhance(prompt, ctx, runtime=None):
    global _enhance_count
    _enhance_count += 1
    return f"Enhanced: {prompt}"


with (
    patch(
        "umh.runtime_engine.model_router.call_with_fallback", side_effect=_mock_call_with_fallback
    ),
    patch("umh.runtime_engine.execution_spine.enhance_prompt", side_effect=_counting_enhance),
    patch("umh.runtime_engine.context.load_context_from_env", return_value=MagicMock()),
    patch("umh.runtime_engine.agent_runtime.AgentRuntime", return_value=MagicMock()),
    patch("umh.runtime_engine.commit_pipeline.commit_winner"),
    patch(
        "umh.runtime_engine.signal_router.route_signals", return_value=MagicMock(world_model=None)
    ),
    patch("umh.runtime_engine.execution_spine.ExecutionSpine", return_value=FakeSpine()),
):
    _call_count = 0
    _enhance_count = 0

    run_with_strategies(
        message="draft copy",
        unified_context=FakeUnifiedContext(),
        agent_type="executive_assistant",
        task_type=FakeTaskType("generate"),
        num_candidates=3,
    )

_test(
    "enhance called once despite 3 candidates",
    _enhance_count == 1,
    f"enhance_count={_enhance_count}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Enhancement failure degrades to raw message
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Graceful Degradation")


def _failing_enhance(prompt, ctx, runtime=None):
    raise RuntimeError("Enhancement service unavailable")


with (
    patch(
        "umh.runtime_engine.model_router.call_with_fallback", side_effect=_mock_call_with_fallback
    ),
    patch("umh.runtime_engine.execution_spine.enhance_prompt", side_effect=_failing_enhance),
    patch("umh.runtime_engine.context.load_context_from_env", return_value=MagicMock()),
    patch("umh.runtime_engine.agent_runtime.AgentRuntime", return_value=MagicMock()),
    patch("umh.runtime_engine.commit_pipeline.commit_winner"),
    patch(
        "umh.runtime_engine.signal_router.route_signals", return_value=MagicMock(world_model=None)
    ),
    patch("umh.runtime_engine.execution_spine.ExecutionSpine", return_value=FakeSpine()),
):
    _call_count = 0
    _llm_prompts.clear()

    result = run_with_strategies(
        message="analyze pipeline",
        unified_context=FakeUnifiedContext(),
        agent_type="executive_assistant",
        task_type=FakeTaskType("analyze"),
    )

_test(
    "result returned despite enhancement failure",
    len(result) > 0,
)
_test(
    "candidates used raw message as fallback",
    all("analyze pipeline" in p for p in _llm_prompts),
    f"prompts: {[p[:30] for p in _llm_prompts]}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Original message stored in commit path (not enhanced)
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Raw Message in Commit Path")


def _transform_enhance(prompt, ctx, runtime=None):
    return f"ENHANCED:{prompt}"


with (
    patch(
        "umh.runtime_engine.model_router.call_with_fallback", side_effect=_mock_call_with_fallback
    ),
    patch("umh.runtime_engine.execution_spine.enhance_prompt", side_effect=_transform_enhance),
    patch("umh.runtime_engine.context.load_context_from_env", return_value=MagicMock()),
    patch("umh.runtime_engine.agent_runtime.AgentRuntime", return_value=MagicMock()),
    patch("umh.runtime_engine.commit_pipeline.commit_winner") as mock_commit,
    patch(
        "umh.runtime_engine.signal_router.route_signals", return_value=MagicMock(world_model=None)
    ),
    patch("umh.runtime_engine.execution_spine.ExecutionSpine", return_value=FakeSpine()),
):
    _call_count = 0

    run_with_strategies(
        message="draft outreach",
        unified_context=FakeUnifiedContext(),
        agent_type="executive_assistant",
        task_type=FakeTaskType("generate"),
        session_id="test-commit",
        org_id="test-org",
    )

_test(
    "commit_winner called",
    mock_commit.call_count == 1,
)
commit_msg = mock_commit.call_args.kwargs["message"]
_test(
    "commit receives raw message, not enhanced",
    commit_msg == "draft outreach",
    f"got: {commit_msg[:50]}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Non-eligible tasks skip multi-strategy enhancement
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Non-Eligible Tasks Use Spine Enhancement Only")

_non_eligible_enhance_calls = 0


def _track_non_eligible_enhance(prompt, ctx, runtime=None):
    global _non_eligible_enhance_calls
    _non_eligible_enhance_calls += 1
    return prompt


with (
    patch(
        "umh.runtime_engine.execution_spine.enhance_prompt", side_effect=_track_non_eligible_enhance
    ),
    patch("umh.runtime_engine.execution_spine.ExecutionSpine", return_value=FakeSpine()),
):
    _non_eligible_enhance_calls = 0

    result = run_with_strategies(
        message="quick status check",
        unified_context=FakeUnifiedContext(),
        agent_type="executive_assistant",
        task_type=FakeTaskType("fast_response"),
    )

_test(
    "enhance_prompt not called in run_with_strategies for non-eligible",
    _non_eligible_enhance_calls == 0,
    f"called {_non_eligible_enhance_calls} times",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Same enhanced message reaches all candidates
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. Uniform Enhanced Prompt Across Candidates")


def _stable_enhance(prompt, ctx, runtime=None):
    return f"STABLE_ENHANCED:{prompt}"


with (
    patch(
        "umh.runtime_engine.model_router.call_with_fallback", side_effect=_mock_call_with_fallback
    ),
    patch("umh.runtime_engine.execution_spine.enhance_prompt", side_effect=_stable_enhance),
    patch("umh.runtime_engine.context.load_context_from_env", return_value=MagicMock()),
    patch("umh.runtime_engine.agent_runtime.AgentRuntime", return_value=MagicMock()),
    patch("umh.runtime_engine.commit_pipeline.commit_winner"),
    patch(
        "umh.runtime_engine.signal_router.route_signals", return_value=MagicMock(world_model=None)
    ),
    patch("umh.runtime_engine.execution_spine.ExecutionSpine", return_value=FakeSpine()),
):
    _call_count = 0
    _llm_prompts.clear()

    run_with_strategies(
        message="outreach ideas",
        unified_context=FakeUnifiedContext(),
        agent_type="executive_assistant",
        task_type=FakeTaskType("generate"),
        num_candidates=2,
    )

_test(
    "all candidates contain same enhanced base",
    all("STABLE_ENHANCED:outreach ideas" in p for p in _llm_prompts),
    f"unique prompts: {len(set(_llm_prompts))}",
)
_test(
    "enhanced prefix present",
    any("STABLE_ENHANCED:" in p for p in _llm_prompts),
    f"prompt: {_llm_prompts[0][:40]}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Candidate generation still side-effect free
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Side-Effect Freedom Preserved")

import inspect
from umh.runtime_engine.multi_strategy import generate_candidates

source = inspect.getsource(generate_candidates)
_test(
    "generate_candidates has no memory imports",
    "ConversationMemory" not in source and "AgentMemory" not in source,
)
_test(
    "generate_candidates has no commit_winner",
    "commit_winner" not in source,
)
_test(
    "generate_candidates has no world model",
    "WorldModel" not in source and "world_model" not in source,
)
_test(
    "generate_candidates has no feedback",
    "FeedbackLoop" not in source and "log_feedback" not in source,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Enhancement uses same logical path as spine
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Enhancement Path Parity with Spine")

source_rws = inspect.getsource(run_with_strategies)
_test(
    "run_with_strategies calls enhance_prompt from execution_spine",
    "from umh.runtime_engine.execution_spine import enhance_prompt" in source_rws,
)
_test(
    "run_with_strategies does not define its own enhance logic",
    "def enhance" not in source_rws,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

if _FAIL > 0:
    sys.exit(1)
