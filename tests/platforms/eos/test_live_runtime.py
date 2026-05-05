"""Tests for eos_ai.platforms.eos.live_runtime."""

import sys

sys.path.insert(0, "/opt/OS")

import pytest
from eos_ai.platforms.eos.live_runtime import (
    EALiveRuntime,
    LiveRuntimeResult,
    RuntimeState,
    format_live_progress_update,
    get_live_runtime,
    handle_live_user_utterance,
)
from eos_ai.substrate.live_sessions import LiveSessionStore
from eos_ai.substrate.task_system import TaskStore
from eos_ai.substrate.task_pipeline import PipelineStore


def _reset_all_singletons() -> None:
    """Reset every singleton touched by the live runtime."""
    EALiveRuntime.reset_default_for_tests()
    LiveSessionStore.reset_default_for_tests()
    TaskStore.reset_default_for_tests()
    PipelineStore.reset_default_for_tests()


class TestRuntimeState:
    """RuntimeState enum exposes all six lifecycle states."""

    def test_states_exist(self):
        assert RuntimeState.IDLE == "idle"
        assert RuntimeState.LISTENING == "listening"
        assert RuntimeState.EXECUTING == "executing"
        assert RuntimeState.SPEAKING == "speaking"
        assert RuntimeState.PAUSED == "paused"
        assert RuntimeState.STOPPED == "stopped"
        # Exactly six members
        assert len(RuntimeState) == 6


class TestControlPhraseInterception:
    """Control phrases are intercepted BEFORE intent routing."""

    def setup_method(self):
        _reset_all_singletons()

    def teardown_method(self):
        _reset_all_singletons()

    def test_pause_intercepted(self):
        result = handle_live_user_utterance("pause")
        assert result.is_control_action is True
        rt = get_live_runtime()
        assert rt.state == RuntimeState.PAUSED

    def test_hold_on_intercepted(self):
        result = handle_live_user_utterance("hold on")
        assert result.is_control_action is True
        rt = get_live_runtime()
        assert rt.state == RuntimeState.PAUSED

    def test_wait_intercepted(self):
        result = handle_live_user_utterance("wait")
        assert result.is_control_action is True

    def test_stop_intercepted(self):
        result = handle_live_user_utterance("stop")
        assert result.is_control_action is True
        rt = get_live_runtime()
        assert rt.state == RuntimeState.STOPPED

    def test_cancel_intercepted(self):
        result = handle_live_user_utterance("cancel")
        assert result.is_control_action is True

    def test_continue_intercepted(self):
        # Pause first, then continue
        handle_live_user_utterance("pause")
        result = handle_live_user_utterance("continue")
        assert result.is_control_action is True
        rt = get_live_runtime()
        assert rt.state == RuntimeState.LISTENING

    def test_resume_intercepted(self):
        handle_live_user_utterance("pause")
        result = handle_live_user_utterance("resume")
        assert result.is_control_action is True

    def test_keep_going_intercepted(self):
        handle_live_user_utterance("pause")
        result = handle_live_user_utterance("keep going")
        assert result.is_control_action is True

    def test_normal_utterance_not_intercepted(self):
        result = handle_live_user_utterance("what's the status?")
        assert result.is_control_action is False
        assert len(result.spoken_text) > 0


class TestLiveSessionBinding:
    """Live session is created and reused across utterances."""

    def setup_method(self):
        _reset_all_singletons()

    def teardown_method(self):
        _reset_all_singletons()

    def test_session_created_on_first_utterance(self):
        result = handle_live_user_utterance("what's the status?")
        assert result.live_session_id is not None

    def test_session_reused_on_subsequent_utterance(self):
        r1 = handle_live_user_utterance("what's the status?")
        r2 = handle_live_user_utterance("catch me up")
        assert r1.live_session_id is not None
        assert r1.live_session_id == r2.live_session_id

    def test_explicit_session_id_used(self):
        result = handle_live_user_utterance(
            "what's happening?", session_id="sess-explicit"
        )
        # Even with an explicit session_id for orchestrator routing,
        # the live runtime still creates its own live_session_id
        assert result.live_session_id is not None


class TestExecutionIntegration:
    """Execution requests create tasks; status requests don't."""

    def setup_method(self):
        _reset_all_singletons()

    def teardown_method(self):
        _reset_all_singletons()

    def test_execution_request_creates_tasks(self):
        result = handle_live_user_utterance("build the API endpoint", dry_run=True)
        assert len(result.created_task_ids) > 0

    def test_status_request_no_tasks(self):
        result = handle_live_user_utterance("what's the status?")
        assert result.created_task_ids == []


class TestPauseResume:
    """Pause/resume/stop state transitions."""

    def setup_method(self):
        _reset_all_singletons()

    def teardown_method(self):
        _reset_all_singletons()

    def test_pause_then_resume(self):
        handle_live_user_utterance("pause")
        rt = get_live_runtime()
        assert rt.state == RuntimeState.PAUSED

        handle_live_user_utterance("resume")
        assert rt.state == RuntimeState.LISTENING

    def test_stop_runtime(self):
        handle_live_user_utterance("stop")
        rt = get_live_runtime()
        assert rt.state == RuntimeState.STOPPED


class TestLiveRuntimeResult:
    """LiveRuntimeResult serialization."""

    def test_result_to_dict(self):
        r = LiveRuntimeResult(
            spoken_text="Done.",
            created_task_ids=["t1"],
            created_pipeline_ids=["p1"],
            executed_actions_summary={"t1": "ok"},
            blocked_items=["b1"],
            live_session_id="ls_abc",
            is_control_action=False,
        )
        d = r.to_dict()
        assert d["spoken_text"] == "Done."
        assert d["created_task_ids"] == ["t1"]
        assert d["created_pipeline_ids"] == ["p1"]
        assert d["executed_actions_summary"] == {"t1": "ok"}
        assert d["blocked_items"] == ["b1"]
        assert d["live_session_id"] == "ls_abc"
        assert d["is_control_action"] is False


class TestProgressFormatting:
    """format_live_progress_update output."""

    def test_format_progress(self):
        out = format_live_progress_update(
            action="building endpoint", status="in_progress", detail="step 2 of 4"
        )
        assert "building endpoint" in out
        assert "in_progress" in out
        assert "step 2 of 4" in out

    def test_format_progress_no_detail(self):
        out = format_live_progress_update(action="deploying")
        assert "deploying" in out
        assert "in_progress" in out
