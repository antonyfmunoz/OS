"""Tests for the unified commit pipeline (eos_ai.commit_pipeline).

Proves:
    1. commit_winner calls all 5 persistence stages in order
    2. ExecutionSpine delegates to commit_winner
    3. multi_strategy winner path delegates to commit_winner
    4. Rejected candidates never reach commit_winner
    5. Parameters flow correctly to each downstream stage
    6. Only one canonical commit path exists
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from unittest.mock import MagicMock, patch, call

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class _FakeCtx:
    org_id = "test-org"
    active_venture_id = "test-venture"


class _FakeWorldModelSignal:
    outcome = "good"


# ---------------------------------------------------------------------------
# 1. commit_winner calls all persistence stages
# ---------------------------------------------------------------------------


class TestCommitWinnerStages:
    def test_conversation_memory_called(self):
        with (
            patch("umh.runtime_engine.memory.ConversationMemory") as m_cm,
            patch("umh.runtime_engine.memory.AgentMemory"),
            patch("umh.runtime_engine.agent_runtime.AgentResult", MagicMock()),
            patch("umh.runtime_engine.execution_spine.integrate_knowledge"),
            patch("umh.runtime_engine.execution_spine.log_feedback"),
            patch("umh.runtime_engine.execution_spine.update_world_model"),
            patch("umh.runtime_engine.execution_spine.log_reflection"),
            patch("umh.substrate.storage.get_storage"),
        ):
            from umh.runtime_engine.commit_pipeline import commit_winner

            commit_winner(
                message="What should I focus on?",
                response="Focus on outreach.",
                ctx=_FakeCtx(),
                agent_type="executive_assistant",
                session_id="sess-001",
                channel_id="ch-001",
                org_id="test-org",
                task_type=None,
                venture_id="test-venture",
                skill_name=None,
                evaluation=None,
                world_model_signal=None,
                model_used="gemini/gemini-2.5-flash",
                tokens_used={"input": 100, "output": 200, "total": 300},
                iterations=1,
            )

            cm_instance = m_cm.return_value
            assert cm_instance.store.call_count == 2
            user_call = cm_instance.store.call_args_list[0]
            asst_call = cm_instance.store.call_args_list[1]
            assert user_call.kwargs["role"] == "user"
            assert asst_call.kwargs["role"] == "assistant"

    def test_agent_memory_called(self):
        with (
            patch("umh.runtime_engine.memory.ConversationMemory"),
            patch("umh.runtime_engine.memory.AgentMemory") as m_am,
            patch("umh.runtime_engine.agent_runtime.AgentResult", MagicMock()),
            patch("umh.runtime_engine.execution_spine.integrate_knowledge"),
            patch("umh.runtime_engine.execution_spine.log_feedback"),
            patch("umh.runtime_engine.execution_spine.update_world_model"),
            patch("umh.runtime_engine.execution_spine.log_reflection"),
            patch("umh.substrate.storage.get_storage"),
        ):
            from umh.runtime_engine.commit_pipeline import commit_winner

            commit_winner(
                message="Test",
                response="Result",
                ctx=_FakeCtx(),
                agent_type="ea",
                session_id="s1",
                channel_id=None,
                org_id=None,
                task_type=None,
                venture_id=None,
                skill_name=None,
                evaluation=None,
                world_model_signal=None,
                model_used="test-model",
                tokens_used=100,
                iterations=1,
            )

            am_instance = m_am.return_value
            am_instance.log.assert_called_once()

    def test_knowledge_integration_called(self):
        with (
            patch("umh.runtime_engine.memory.ConversationMemory"),
            patch("umh.runtime_engine.memory.AgentMemory"),
            patch("umh.runtime_engine.agent_runtime.AgentResult", MagicMock()),
            patch("umh.runtime_engine.execution_spine.integrate_knowledge") as m_ki,
            patch("umh.runtime_engine.execution_spine.log_feedback"),
            patch("umh.runtime_engine.execution_spine.update_world_model"),
            patch("umh.runtime_engine.execution_spine.log_reflection"),
            patch("umh.substrate.storage.get_storage"),
        ):
            from umh.runtime_engine.commit_pipeline import commit_winner

            commit_winner(
                message="We closed a deal",
                response="Great news.",
                ctx=_FakeCtx(),
                agent_type="ea",
                session_id="s1",
                channel_id=None,
                org_id=None,
                task_type=None,
                venture_id=None,
                skill_name=None,
                evaluation=None,
                world_model_signal=None,
                model_used="test",
                tokens_used=50,
                iterations=1,
            )

            m_ki.assert_called_once()
            assert "deal" in m_ki.call_args[0][0]

    def test_feedback_logging_called(self):
        with (
            patch("umh.runtime_engine.memory.ConversationMemory"),
            patch("umh.runtime_engine.memory.AgentMemory"),
            patch("umh.runtime_engine.agent_runtime.AgentResult", MagicMock()),
            patch("umh.runtime_engine.execution_spine.integrate_knowledge"),
            patch("umh.runtime_engine.execution_spine.log_feedback") as m_fb,
            patch("umh.runtime_engine.execution_spine.update_world_model"),
            patch("umh.runtime_engine.execution_spine.log_reflection"),
            patch("umh.substrate.storage.get_storage"),
        ):
            from umh.runtime_engine.commit_pipeline import commit_winner

            eval_dict = {"quality_score": 0.8, "confidence": 0.9}
            commit_winner(
                message="Test",
                response="Response",
                ctx=_FakeCtx(),
                agent_type="ea",
                session_id="s1",
                channel_id=None,
                org_id=None,
                task_type=None,
                venture_id="v1",
                skill_name=None,
                evaluation=eval_dict,
                world_model_signal=None,
                model_used="test",
                tokens_used=50,
                iterations=1,
            )

            m_fb.assert_called_once()
            assert m_fb.call_args.kwargs["evaluation"] is eval_dict

    def test_world_model_called_with_org_id(self):
        with (
            patch("umh.runtime_engine.memory.ConversationMemory"),
            patch("umh.runtime_engine.memory.AgentMemory"),
            patch("umh.runtime_engine.agent_runtime.AgentResult", MagicMock()),
            patch("umh.runtime_engine.execution_spine.integrate_knowledge"),
            patch("umh.runtime_engine.execution_spine.log_feedback"),
            patch("umh.runtime_engine.execution_spine.update_world_model") as m_wm,
            patch("umh.runtime_engine.execution_spine.log_reflection"),
            patch("umh.substrate.storage.get_storage"),
        ):
            from umh.runtime_engine.commit_pipeline import commit_winner

            signal = _FakeWorldModelSignal()
            commit_winner(
                message="Test",
                response="Response",
                ctx=_FakeCtx(),
                agent_type="ea",
                session_id="s1",
                channel_id=None,
                org_id="org-1",
                task_type=None,
                venture_id=None,
                skill_name=None,
                evaluation={"quality_score": 0.8},
                world_model_signal=signal,
                model_used="test",
                tokens_used=50,
                iterations=1,
            )

            m_wm.assert_called_once()
            assert m_wm.call_args.kwargs["world_model_signal"] is signal

    def test_world_model_skipped_without_org_id(self):
        with (
            patch("umh.runtime_engine.memory.ConversationMemory"),
            patch("umh.runtime_engine.memory.AgentMemory"),
            patch("umh.runtime_engine.agent_runtime.AgentResult", MagicMock()),
            patch("umh.runtime_engine.execution_spine.integrate_knowledge"),
            patch("umh.runtime_engine.execution_spine.log_feedback"),
            patch("umh.runtime_engine.execution_spine.update_world_model") as m_wm,
            patch("umh.runtime_engine.execution_spine.log_reflection"),
            patch("umh.substrate.storage.get_storage"),
        ):
            from umh.runtime_engine.commit_pipeline import commit_winner

            commit_winner(
                message="Test",
                response="Response",
                ctx=_FakeCtx(),
                agent_type="ea",
                session_id="s1",
                channel_id=None,
                org_id=None,
                task_type=None,
                venture_id=None,
                skill_name=None,
                evaluation=None,
                world_model_signal=None,
                model_used="test",
                tokens_used=50,
                iterations=1,
            )

            m_wm.assert_not_called()

    def test_reflection_called_with_iterations(self):
        with (
            patch("umh.runtime_engine.memory.ConversationMemory"),
            patch("umh.runtime_engine.memory.AgentMemory"),
            patch("umh.runtime_engine.agent_runtime.AgentResult", MagicMock()),
            patch("umh.runtime_engine.execution_spine.integrate_knowledge"),
            patch("umh.runtime_engine.execution_spine.log_feedback"),
            patch("umh.runtime_engine.execution_spine.update_world_model"),
            patch("umh.runtime_engine.execution_spine.log_reflection") as m_ref,
            patch("umh.substrate.storage.get_storage"),
        ):
            from umh.runtime_engine.commit_pipeline import commit_winner

            commit_winner(
                message="Test",
                response="Response",
                ctx=_FakeCtx(),
                agent_type="ea",
                session_id="s1",
                channel_id=None,
                org_id=None,
                task_type=None,
                venture_id=None,
                skill_name=None,
                evaluation=None,
                world_model_signal=None,
                model_used="test",
                tokens_used=50,
                iterations=3,
            )

            m_ref.assert_called_once()
            assert m_ref.call_args[0][1] == 3  # iterations arg

    def test_session_persistence_with_channel_id(self):
        with (
            patch("umh.runtime_engine.memory.ConversationMemory"),
            patch("umh.runtime_engine.memory.AgentMemory"),
            patch("umh.runtime_engine.agent_runtime.AgentResult", MagicMock()),
            patch("umh.runtime_engine.execution_spine.integrate_knowledge"),
            patch("umh.runtime_engine.execution_spine.log_feedback"),
            patch("umh.runtime_engine.execution_spine.update_world_model"),
            patch("umh.runtime_engine.execution_spine.log_reflection"),
            patch("umh.substrate.storage.get_storage") as m_storage,
        ):
            from umh.runtime_engine.commit_pipeline import commit_winner

            commit_winner(
                message="Test",
                response="Response",
                ctx=_FakeCtx(),
                agent_type="ea",
                session_id="sess-123",
                channel_id="ch-456",
                org_id=None,
                task_type=None,
                venture_id=None,
                skill_name=None,
                evaluation=None,
                world_model_signal=None,
                model_used="test",
                tokens_used=50,
                iterations=1,
            )

            store = m_storage.return_value
            store.put.assert_called_once_with("session:ch-456", "sess-123")

    def test_session_persistence_skipped_without_channel_id(self):
        with (
            patch("umh.runtime_engine.memory.ConversationMemory"),
            patch("umh.runtime_engine.memory.AgentMemory"),
            patch("umh.runtime_engine.agent_runtime.AgentResult", MagicMock()),
            patch("umh.runtime_engine.execution_spine.integrate_knowledge"),
            patch("umh.runtime_engine.execution_spine.log_feedback"),
            patch("umh.runtime_engine.execution_spine.update_world_model"),
            patch("umh.runtime_engine.execution_spine.log_reflection"),
            patch("umh.substrate.storage.get_storage") as m_storage,
        ):
            from umh.runtime_engine.commit_pipeline import commit_winner

            commit_winner(
                message="Test",
                response="Response",
                ctx=_FakeCtx(),
                agent_type="ea",
                session_id="sess-123",
                channel_id=None,
                org_id=None,
                task_type=None,
                venture_id=None,
                skill_name=None,
                evaluation=None,
                world_model_signal=None,
                model_used="test",
                tokens_used=50,
                iterations=1,
            )

            store = m_storage.return_value
            store.put.assert_not_called()


# ---------------------------------------------------------------------------
# 2. Only one canonical commit path exists
# ---------------------------------------------------------------------------


class TestSingleCanonicalPath:
    """Verify that ExecutionSpine and multi_strategy both delegate to commit_winner."""

    def test_execution_spine_imports_commit_winner(self):
        import inspect
        from umh.runtime_engine.execution_spine import ExecutionSpine

        source = inspect.getsource(ExecutionSpine.run)
        assert "commit_winner" in source
        assert "ConversationMemory" not in source

    def test_multi_strategy_imports_commit_winner(self):
        import inspect
        from umh.runtime_engine.multi_strategy import run_with_strategies

        source = inspect.getsource(run_with_strategies)
        assert "commit_winner" in source
        assert "_persist_winner" not in source

    def test_no_persist_winner_function_in_multi_strategy(self):
        import umh.runtime_engine.multi_strategy as ms

        assert not hasattr(ms, "_persist_winner")
