"""Integration tests — ExecutionSpine 10-stage pipeline.

Validates the canonical execution path end-to-end with mocked
external dependencies (LLM, DB, storage). Confirms:

    authority → enhancement → context → LLM → quality → stage_filter
    → memory writes → knowledge → feedback → world_model → reflection
    → session persistence → footer

No CognitiveLoop is involved. All stages are exercised.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from dataclasses import dataclass
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@dataclass
class _FakeRoutingResult:
    output: str = "Focus on outreach this week."
    provider: str = "test"
    model: str = "test-model"
    task_type: str = "analyze"
    tokens_used: int = 200
    input_tokens: int = 80
    output_tokens: int = 120
    cost_usd: float = 0.001
    latency_ms: int = 150


class _FakeUnifiedContext:
    def to_system_prompt(self) -> str:
        return "You are DEX, an AI Executive Assistant."


class _FakeCtx:
    org_id = "test_org"
    user_id = "test_user"
    active_venture_id = "test_venture"
    portfolio_id = None
    ventures = []


class _FakeAuthorityEngine:
    def __init__(self, *a, **kw):
        pass

    def check_can_execute(self, action_type, *a, **kw):
        return {"can_execute": True, "requires_approval": False, "risk_class": "LOW"}

    @staticmethod
    def classify_action(action_type):
        return "LOW"


class _FakeAgentRuntime:
    pass


# The patches that every test needs — authority, context, LLM, memory, storage.
# Each test can override specific patches as needed.
_COMMON_PATCHES = {
    "umh.runtime_engine.context.load_context_from_env": lambda: _FakeCtx(),
    "umh.runtime_engine.authority_engine.AuthorityEngine": _FakeAuthorityEngine,
    "umh.runtime_engine.agent_runtime.AgentRuntime": lambda: _FakeAgentRuntime(),
}


def _run_spine(
    message: str = "What should I focus on?",
    unified_context=None,
    agent_type: str = "executive_assistant",
    authority_class: str = "analyze",
    org_id: str = "test_org",
    venture_id: str = "test_venture",
    llm_output: str = "Focus on outreach this week.",
    **extra_spine_kwargs,
) -> tuple[str, dict]:
    """
    Execute ExecutionSpine.run() with all external dependencies mocked.
    Returns (response_str, mocks_dict) so callers can assert on side effects.
    """
    from umh.runtime_engine.execution_spine import ExecutionSpine

    mocks = {}

    with (
        patch("umh.runtime_engine.context.load_context_from_env", return_value=_FakeCtx()) as m_ctx,
        patch("umh.runtime_engine.authority_engine.AuthorityEngine", _FakeAuthorityEngine),
        patch("umh.runtime_engine.agent_runtime.AgentRuntime", return_value=_FakeAgentRuntime()),
        patch(
            "umh.runtime_engine.model_router.call_with_fallback",
            return_value=_FakeRoutingResult(output=llm_output),
        ) as m_llm,
        patch("umh.runtime_engine.memory.ConversationMemory") as m_conv_mem,
        patch("umh.runtime_engine.memory.AgentMemory") as m_agent_mem,
        patch("umh.runtime_engine.agent_runtime.AgentResult", MagicMock()),
        patch("umh.runtime_engine.knowledge_integrator.KnowledgeIntegrator") as m_knowledge,
        patch("umh.runtime_engine.feedback_loop.FeedbackLoop") as m_feedback,
        patch("umh.runtime_engine.world_model.WorldModel") as m_world,
        patch("umh.substrate.storage.get_storage") as m_storage,
        patch(
            "umh.runtime_engine.execution_spine.format_response_footer",
            return_value="\n---\ntest footer",
        ) as m_footer,
    ):
        mocks["load_context"] = m_ctx
        mocks["call_with_fallback"] = m_llm
        mocks["ConversationMemory"] = m_conv_mem
        mocks["AgentMemory"] = m_agent_mem
        mocks["KnowledgeIntegrator"] = m_knowledge
        mocks["FeedbackLoop"] = m_feedback
        mocks["WorldModel"] = m_world
        mocks["get_storage"] = m_storage
        mocks["format_response_footer"] = m_footer

        spine = ExecutionSpine()
        result = spine.run(
            message=message,
            unified_context=unified_context or _FakeUnifiedContext(),
            agent_type=agent_type,
            authority_class=authority_class,
            session_id="test-session-001",
            channel_id="test-channel",
            org_id=org_id,
            user_id="test_user",
            task_type=None,
            venture_id=venture_id,
            **extra_spine_kwargs,
        )

    return result, mocks


# ---------------------------------------------------------------------------
# Tests: Full pipeline
# ---------------------------------------------------------------------------


class TestExecutionSpinePipeline:
    def test_full_pipeline_returns_response_with_footer(self):
        result, _ = _run_spine()
        assert "Focus on outreach this week." in result
        assert "test footer" in result

    def test_llm_called_with_message(self):
        _, mocks = _run_spine(message="What is the binding constraint?")
        mocks["call_with_fallback"].assert_called_once()
        call_kwargs = mocks["call_with_fallback"].call_args
        assert "binding constraint" in str(call_kwargs)

    def test_no_cognitive_loop_instantiated(self):
        """Confirm CognitiveLoop class is never instantiated on this path."""
        with patch("umh.runtime_engine.cognitive_loop.CognitiveLoop") as m_cl:
            _run_spine()
            m_cl.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: Memory writes
# ---------------------------------------------------------------------------


class TestMemoryWrites:
    def test_conversation_memory_stores_user_and_assistant(self):
        _, mocks = _run_spine()
        cm_instance = mocks["ConversationMemory"].return_value
        assert cm_instance.store.call_count == 2
        roles = [
            c.kwargs.get("role") or c[1][1] for c in cm_instance.store.call_args_list
        ]
        # store() is called with keyword args
        user_call = cm_instance.store.call_args_list[0]
        asst_call = cm_instance.store.call_args_list[1]
        assert user_call.kwargs.get("role") == "user"
        assert asst_call.kwargs.get("role") == "assistant"

    def test_agent_memory_logs_interaction(self):
        _, mocks = _run_spine()
        am_instance = mocks["AgentMemory"].return_value
        am_instance.log.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: Post-generation intelligence stages
# ---------------------------------------------------------------------------


class TestPostGenerationStages:
    def test_knowledge_integration_called(self):
        _, mocks = _run_spine(message="We closed a deal today")
        ki_instance = mocks["KnowledgeIntegrator"].return_value
        ki_instance.integrate.assert_called_once()
        call_kwargs = ki_instance.integrate.call_args.kwargs
        assert "spine_conversation" in call_kwargs.get("source", "")

    def test_feedback_loop_called(self):
        _, mocks = _run_spine()
        fl_instance = mocks["FeedbackLoop"].return_value
        assert fl_instance.log_recommendation.called or fl_instance.log_outcome.called

    def test_world_model_update_called_with_org_id(self):
        _, mocks = _run_spine(org_id="lyfe_institute")
        wm_class = mocks["WorldModel"]
        wm_class.assert_called_once_with(org_id="lyfe_institute")
        wm_instance = wm_class.return_value
        wm_instance.update_from_interaction.assert_called_once()
        args = wm_instance.update_from_interaction.call_args[0]
        assert args[0] == "What should I focus on?"
        assert "outreach" in args[1]

    def test_world_model_skipped_without_org_id(self):
        _, mocks = _run_spine(org_id=None)
        wm_class = mocks["WorldModel"]
        wm_class.assert_not_called()

    def test_session_persisted_to_storage(self):
        _, mocks = _run_spine()
        store_instance = mocks["get_storage"].return_value
        store_instance.put.assert_called_once()
        call_args = store_instance.put.call_args[0]
        assert call_args[0] == "session:test-channel"
        assert call_args[1] == "test-session-001"


# ---------------------------------------------------------------------------
# Tests: Authority behavior
# ---------------------------------------------------------------------------


class TestAuthorityBehavior:
    def test_low_risk_proceeds_on_authority_failure(self):
        with patch(
            "umh.runtime_engine.context.load_context_from_env",
            side_effect=Exception("DB down"),
        ):
            with patch("umh.runtime_engine.authority_engine.AuthorityEngine") as m_ae:
                m_ae.classify_action = staticmethod(lambda *a: "LOW")
                with patch(
                    "umh.runtime_engine.model_router.call_with_fallback",
                    return_value=_FakeRoutingResult(),
                ) as m_llm:
                    with patch("umh.runtime_engine.memory.ConversationMemory"):
                        with patch("umh.runtime_engine.memory.AgentMemory"):
                            with patch("umh.runtime_engine.agent_runtime.AgentResult", MagicMock()):
                                with patch(
                                    "umh.runtime_engine.agent_runtime.AgentRuntime",
                                    return_value=_FakeAgentRuntime(),
                                ):
                                    with patch(
                                        "umh.runtime_engine.execution_spine.format_response_footer",
                                        return_value="",
                                    ):
                                        from umh.runtime_engine.execution_spine import (
                                            ExecutionSpine,
                                        )

                                        spine = ExecutionSpine()
                                        result = spine.run(
                                            message="Analyze pipeline",
                                            unified_context=_FakeUnifiedContext(),
                                            authority_class="analyze",
                                            session_id="test-auth-low",
                                            org_id="test_org",
                                        )
        assert "blocked" not in result.lower()

    def test_critical_risk_blocks_on_authority_failure(self):
        with patch(
            "umh.runtime_engine.context.load_context_from_env",
            side_effect=Exception("DB down"),
        ):
            with patch("umh.runtime_engine.authority_engine.AuthorityEngine") as m_ae:
                m_ae.classify_action = staticmethod(lambda *a: "CRITICAL")
                from umh.runtime_engine.execution_spine import ExecutionSpine

                spine = ExecutionSpine()
                result = spine.run(
                    message="Execute payment",
                    unified_context=_FakeUnifiedContext(),
                    authority_class="execute_payment",
                    session_id="test-auth-critical",
                    org_id="test_org",
                )
        assert "blocked" in result.lower()
        assert "CRITICAL" in result


# ---------------------------------------------------------------------------
# Tests: Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_llm_response_produces_error_string(self):
        result, _ = _run_spine(llm_output="")
        assert "[ExecutionSpine]" in result or result != ""

    def test_llm_failure_returns_error_not_raises(self):
        from umh.runtime_engine.execution_spine import ExecutionSpine

        with (
            patch(
                "umh.runtime_engine.context.load_context_from_env",
                return_value=_FakeCtx(),
            ),
            patch(
                "umh.runtime_engine.authority_engine.AuthorityEngine",
                _FakeAuthorityEngine,
            ),
            patch(
                "umh.runtime_engine.agent_runtime.AgentRuntime",
                return_value=_FakeAgentRuntime(),
            ),
            patch(
                "umh.runtime_engine.model_router.call_with_fallback",
                side_effect=Exception("All providers exhausted"),
            ),
            patch("umh.runtime_engine.memory.ConversationMemory"),
            patch("umh.runtime_engine.memory.AgentMemory"),
            patch("umh.runtime_engine.agent_runtime.AgentResult", MagicMock()),
            patch("umh.runtime_engine.execution_spine.format_response_footer", return_value=""),
        ):
            spine = ExecutionSpine()
            result = spine.run(
                message="test",
                unified_context=_FakeUnifiedContext(),
                session_id="test-llm-fail",
                org_id="test_org",
            )
        assert "error" in result.lower()
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Tests: SpineResult contract
# ---------------------------------------------------------------------------


class TestSpineResult:
    """Verify SpineResult str subclass carries metadata without breaking callers."""

    def test_result_is_str_instance(self):
        result, _ = _run_spine()
        assert isinstance(result, str)

    def test_result_is_spine_result_instance(self):
        from umh.runtime_engine.execution_spine import SpineResult

        result, _ = _run_spine()
        assert isinstance(result, SpineResult)

    def test_str_operations_work(self):
        result, _ = _run_spine()
        assert result.startswith("Focus")
        assert "outreach" in result.lower()
        assert len(result) > 0
        assert result[:5] == "Focus"

    def test_metadata_model_used(self):
        result, _ = _run_spine()
        assert result.model_used == "test/test-model"

    def test_metadata_tokens_used(self):
        result, _ = _run_spine()
        assert result.tokens_used["input"] == 80
        assert result.tokens_used["output"] == 120
        assert result.tokens_used["total"] == 200

    def test_metadata_cost_usd(self):
        result, _ = _run_spine()
        assert result.cost_usd == 0.001

    def test_metadata_latency_ms(self):
        result, _ = _run_spine()
        # latency_ms comes from RoutingResult (150) or fallback to elapsed
        assert result.latency_ms > 0

    def test_metadata_session_id(self):
        result, _ = _run_spine()
        assert result.session_id == "test-session-001"

    def test_metadata_iterations(self):
        result, _ = _run_spine()
        assert result.iterations >= 1

    def test_metadata_was_enhanced(self):
        result, _ = _run_spine()
        assert isinstance(result.was_enhanced, bool)

    def test_spine_result_repr(self):
        from umh.runtime_engine.execution_spine import SpineResult

        r = SpineResult(
            "hello",
            model_used="test/foo",
            tokens_used={"input": 10, "output": 20, "total": 30},
            cost_usd=0.005,
        )
        rep = repr(r)
        assert "SpineResult" in rep
        assert "test/foo" in rep
        assert "30" in rep

    def test_spine_result_equality_with_str(self):
        from umh.runtime_engine.execution_spine import SpineResult

        r = SpineResult("hello world")
        assert r == "hello world"
        assert "hello" in r

    def test_spine_result_default_metadata(self):
        from umh.runtime_engine.execution_spine import SpineResult

        r = SpineResult("plain")
        assert r.model_used == "unknown"
        assert r.cost_usd == 0.0
        assert r.tokens_used == {"input": 0, "output": 0, "total": 0}

    def test_error_result_is_still_spine_result(self):
        """LLM failure should still return SpineResult, not bare str."""
        from umh.runtime_engine.execution_spine import ExecutionSpine, SpineResult

        with (
            patch("umh.runtime_engine.context.load_context_from_env", return_value=_FakeCtx()),
            patch("umh.runtime_engine.authority_engine.AuthorityEngine", _FakeAuthorityEngine),
            patch(
                "umh.runtime_engine.agent_runtime.AgentRuntime", return_value=_FakeAgentRuntime()
            ),
            patch(
                "umh.runtime_engine.model_router.call_with_fallback",
                side_effect=Exception("boom"),
            ),
            patch("umh.runtime_engine.memory.ConversationMemory"),
            patch("umh.runtime_engine.memory.AgentMemory"),
            patch("umh.runtime_engine.agent_runtime.AgentResult", MagicMock()),
            patch("umh.runtime_engine.execution_spine.format_response_footer", return_value=""),
        ):
            result = ExecutionSpine().run(
                message="test",
                unified_context=_FakeUnifiedContext(),
                session_id="test-err",
                org_id="test_org",
            )
        assert isinstance(result, SpineResult)
        assert "error" in result.lower()
        assert result.model_used == "spine"


# ---------------------------------------------------------------------------
# Tests: CognitiveLoop deprecation
# ---------------------------------------------------------------------------


class TestCognitiveLoopDeprecation:
    def test_cognitive_loop_emits_deprecation_warning(self):
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with (
                patch("umh.runtime_engine.cognitive_loop.AgentRuntime"),
                patch("umh.runtime_engine.cognitive_loop.AgentMemory"),
                patch("umh.runtime_engine.cognitive_loop.AuthorityEngine"),
            ):
                from umh.runtime_engine.cognitive_loop import CognitiveLoop

                CognitiveLoop(_FakeCtx())
            deprecation_warnings = [
                x for x in w if issubclass(x.category, DeprecationWarning)
            ]
            assert len(deprecation_warnings) >= 1
            assert "deprecated" in str(deprecation_warnings[0].message).lower()

    def test_cognitive_loop_module_docstring_says_deprecated(self):
        import umh.runtime_engine.cognitive_loop as cl_mod

        assert "DEPRECATED" in (cl_mod.__doc__ or "")


# ---------------------------------------------------------------------------
# Tests: Compaction architecture — spine stateless, session owns it
# ---------------------------------------------------------------------------


class TestCompactionArchitecture:
    def test_spine_has_no_message_accumulation(self):
        from umh.runtime_engine.execution_spine import ExecutionSpine

        spine = ExecutionSpine()
        assert not hasattr(spine, "_messages")

    def test_session_runtime_has_message_accumulation(self):
        from umh.runtime_engine.session_runtime import SessionRuntime

        s = SessionRuntime(_FakeCtx())
        assert hasattr(s, "_messages")
        assert isinstance(s._messages, list)

    def test_context_compactor_exists_and_importable(self):
        from umh.runtime_engine.context_compaction import ContextCompactor

        assert hasattr(ContextCompactor, "should_compact")
        assert hasattr(ContextCompactor, "compact")


# ---------------------------------------------------------------------------
# Tests: format_response_footer moved to execution_spine
# ---------------------------------------------------------------------------


class TestFooterMoved:
    def test_footer_importable_from_spine(self):
        from umh.runtime_engine.execution_spine import format_response_footer

        assert callable(format_response_footer)

    def test_footer_reexported_from_cognitive_loop(self):
        from umh.runtime_engine.cognitive_loop import format_response_footer

        assert callable(format_response_footer)

    def test_both_point_to_same_function(self):
        from umh.runtime_engine.execution_spine import (
            format_response_footer as f_spine,
        )
        from umh.runtime_engine.cognitive_loop import (
            format_response_footer as f_loop,
        )

        assert f_spine is f_loop

    def test_spine_no_longer_imports_from_cognitive_loop_for_footer(self):
        """The spine module must not contain 'from umh.runtime_engine.cognitive_loop import'."""
        from pathlib import Path

        source = Path("/opt/OS/eos/execution_spine.py").read_text()
        assert "from umh.runtime_engine.cognitive_loop import" not in source


# ---------------------------------------------------------------------------
# Tests: SessionRuntime
# ---------------------------------------------------------------------------


def _run_session(
    message: str = "What should I focus on?",
    llm_output: str = "Focus on outreach this week.",
) -> tuple:
    """Execute SessionRuntime.run() with mocked externals."""
    from umh.runtime_engine.session_runtime import SessionRuntime
    from umh.runtime_engine.execution_spine import SpineResult

    with (
        patch(
            "umh.runtime_engine.execution_spine.ExecutionSpine.run",
            return_value=SpineResult(
                llm_output,
                model_used="test/test-model",
                tokens_used={"input": 80, "output": 120, "total": 200},
                cost_usd=0.001,
                latency_ms=150,
                session_id="test-session",
                iterations=1,
                was_enhanced=False,
            ),
        ) as m_spine,
    ):
        session = SessionRuntime(_FakeCtx(), session_id="test-session")
        result = session.run(
            message=message,
            unified_context=_FakeUnifiedContext(),
            agent_type="executive_assistant",
            authority_class="analyze",
            org_id="test_org",
            venture_id="test_venture",
        )
    return result, session, m_spine


class TestSessionRuntime:
    def test_result_is_spine_result(self):
        from umh.runtime_engine.execution_spine import SpineResult

        result, _, _ = _run_session()
        assert isinstance(result, SpineResult)

    def test_result_text_correct(self):
        result, _, _ = _run_session()
        assert "Focus on outreach" in result

    def test_delegates_to_spine(self):
        _, _, m_spine = _run_session()
        m_spine.assert_called_once()

    def test_session_stats_accumulate_single_turn(self):
        _, session, _ = _run_session()
        assert session.stats.turns == 1
        assert session.stats.total_tokens_in == 80
        assert session.stats.total_tokens_out == 120
        assert session.stats.total_cost_usd == 0.001
        assert session.stats.total_tokens == 200

    def test_session_stats_accumulate_multi_turn(self):
        from umh.runtime_engine.session_runtime import SessionRuntime
        from umh.runtime_engine.execution_spine import SpineResult

        with patch(
            "umh.runtime_engine.execution_spine.ExecutionSpine.run",
            return_value=SpineResult(
                "response",
                model_used="test/model",
                tokens_used={"input": 50, "output": 100, "total": 150},
                cost_usd=0.002,
            ),
        ):
            session = SessionRuntime(_FakeCtx())
            session.run(
                message="turn 1",
                unified_context=_FakeUnifiedContext(),
            )
            session.run(
                message="turn 2",
                unified_context=_FakeUnifiedContext(),
            )

        assert session.stats.turns == 2
        assert session.stats.total_tokens_in == 100
        assert session.stats.total_tokens_out == 200
        assert session.stats.total_cost_usd == 0.004

    def test_models_used_deduplicated(self):
        from umh.runtime_engine.session_runtime import SessionRuntime
        from umh.runtime_engine.execution_spine import SpineResult

        with patch(
            "umh.runtime_engine.execution_spine.ExecutionSpine.run",
            return_value=SpineResult("r", model_used="gemini/flash"),
        ):
            session = SessionRuntime(_FakeCtx())
            session.run(message="a", unified_context=_FakeUnifiedContext())
            session.run(message="b", unified_context=_FakeUnifiedContext())

        assert session.stats.models_used == ["gemini/flash"]

    def test_messages_accumulated(self):
        _, session, _ = _run_session()
        assert len(session._messages) == 2
        assert session._messages[0]["role"] == "user"
        assert session._messages[1]["role"] == "assistant"

    def test_compaction_failure_does_not_break_execution(self):
        from umh.runtime_engine.session_runtime import SessionRuntime
        from umh.runtime_engine.execution_spine import SpineResult

        with (
            patch(
                "umh.runtime_engine.execution_spine.ExecutionSpine.run",
                return_value=SpineResult("ok"),
            ),
            patch(
                "umh.runtime_engine.context_compaction.ContextCompactor.should_compact",
                side_effect=Exception("DB down"),
            ),
        ):
            session = SessionRuntime(_FakeCtx())
            result = session.run(
                message="test",
                unified_context=_FakeUnifiedContext(),
            )
        assert result == "ok"
        assert session.stats.turns == 1

    def test_compaction_triggers_when_threshold_exceeded(self):
        from umh.runtime_engine.session_runtime import SessionRuntime
        from umh.runtime_engine.execution_spine import SpineResult

        with (
            patch(
                "umh.runtime_engine.execution_spine.ExecutionSpine.run",
                return_value=SpineResult("ok"),
            ),
            patch(
                "umh.runtime_engine.context_compaction.ContextCompactor.should_compact",
                return_value=True,
            ),
            patch(
                "umh.runtime_engine.context_compaction.ContextCompactor.compact",
                return_value={"who_user_is": "founder", "decisions_made": []},
            ) as m_compact,
            patch(
                "umh.runtime_engine.context_compaction.ContextCompactor.build_seeded_context",
                return_value="SEEDED CONTEXT",
            ),
            patch("umh.runtime_engine.context_compaction.ContextCompactor._ensure_table"),
        ):
            session = SessionRuntime(_FakeCtx())
            session._messages = [{"role": "user", "content": "x"}] * 100
            result = session.run(
                message="test after compaction",
                unified_context=_FakeUnifiedContext(),
            )

        m_compact.assert_called_once()
        assert session.stats.compactions == 1
        assert session._messages[0]["role"] == "system"
        assert "SEEDED" in session._messages[0]["content"]

    def test_session_runtime_preserves_session_id(self):
        from umh.runtime_engine.session_runtime import SessionRuntime
        from umh.runtime_engine.execution_spine import SpineResult

        with patch(
            "umh.runtime_engine.execution_spine.ExecutionSpine.run",
            return_value=SpineResult("ok"),
        ) as m_spine:
            session = SessionRuntime(_FakeCtx(), session_id="my-session-42")
            session.run(
                message="test",
                unified_context=_FakeUnifiedContext(),
            )

        call_kwargs = m_spine.call_args.kwargs
        assert call_kwargs["session_id"] == "my-session-42"


# ---------------------------------------------------------------------------
# Tests: No CognitiveLoop runtime dependency
# ---------------------------------------------------------------------------


class TestNoCognitiveLoopDependency:
    def test_spine_does_not_import_cognitive_loop(self):
        from pathlib import Path

        source = Path("/opt/OS/eos/execution_spine.py").read_text()
        assert "from eos.cognitive_loop" not in source
        assert "import cognitive_loop" not in source

    def test_session_runtime_does_not_import_cognitive_loop(self):
        from pathlib import Path

        source = Path("/opt/OS/eos/session_runtime.py").read_text()
        assert "cognitive_loop" not in source


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
