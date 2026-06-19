"""Tests for WorkstationSessionRuntime — Campaign 4.4.

Covers: session lifecycle (start→checkpoint→pause→resume→close),
full OrchestratorContext restore on resume, changes detection,
multiple checkpoints, session history, graceful degradation,
next_actions derivation, serialization.
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

from typing import Any
from unittest.mock import MagicMock

import pytest

from substrate.operator.workstation_session_runtime import (
    WorkstationSession,
    WorkstationSessionCheckpoint,
    WorkstationSessionResume,
    WorkstationSessionRuntime,
    WorkstationSessionStatus,
)


# ── Fixtures ──────────────────────────────────────────────────────────────


def _mock_awareness() -> MagicMock:
    m = MagicMock()
    m.context.return_value = {
        "active_projection": "entrepreneuros",
        "active_repo": "OS",
        "active_files": ["types.py"],
        "active_agents": [{"id": "a-1"}],
        "active_compute_nodes": [{"id": "n-1"}],
        "recommendations": [{"action": "deploy"}],
    }
    return m


def _mock_continuity_runtime() -> MagicMock:
    m = MagicMock()
    m.capture_snapshot.return_value = {"snapshot": "captured"}
    m.record_departure.return_value = {"departed": True}
    m.generate_resume.return_value = {"changes": ["file1.py updated", "new agent deployed"]}
    return m


def _mock_continuity_engine() -> MagicMock:
    m = MagicMock()
    m.resume_from_absence.return_value = {"state": "resumed"}
    return m


def _mock_snapshot() -> MagicMock:
    m = MagicMock()
    m.snapshot.return_value = {"device": "vps-01", "session_id": "s-1"}
    m.situation.return_value = {"status": "active", "focus": "development"}
    return m


def _mock_attention() -> MagicMock:
    m = MagicMock()
    m.top.return_value = [
        {"category": "approval", "urgency": 0.9},
        {"category": "drift", "urgency": 0.5},
    ]
    return m


def _mock_loop_rt() -> MagicMock:
    m = MagicMock()
    m.active_loops.return_value = [
        MagicMock(to_dict=lambda: {"loop_id": "l-1", "intent_text": "Build feature", "current_stage": "execute"}),
        MagicMock(to_dict=lambda: {"loop_id": "l-2", "intent_text": "Review PR", "current_stage": "approve"}),
    ]
    return m


def _mock_approval_rt() -> MagicMock:
    m = MagicMock()
    m.pending.return_value = [
        MagicMock(to_dict=lambda: {"approval_id": "ap-1"}),
        MagicMock(to_dict=lambda: {"approval_id": "ap-2"}),
    ]
    return m


def _mock_coherence_rt() -> MagicMock:
    m = MagicMock()
    m.coherence_score.return_value = 0.85
    return m


def _build_full_runtime() -> WorkstationSessionRuntime:
    return WorkstationSessionRuntime(
        continuity_runtime=_mock_continuity_runtime(),
        continuity_engine=_mock_continuity_engine(),
        snapshot_runtime=_mock_snapshot(),
        attention_engine=_mock_attention(),
        awareness=_mock_awareness(),
        operating_loop=_mock_loop_rt(),
        approval_runtime=_mock_approval_rt(),
        coherence_runtime=_mock_coherence_rt(),
    )


# ── Lifecycle ─────────────────────────────────────────────────────────────


class TestLifecycle:
    def test_start_session(self) -> None:
        rt = _build_full_runtime()
        session = rt.start_session()
        assert session.session_id.startswith("wsess-")
        assert session.status == WorkstationSessionStatus.ACTIVE

    def test_checkpoint_creates_entry(self) -> None:
        rt = _build_full_runtime()
        session = rt.start_session()
        chk = rt.checkpoint()
        assert chk.session_id == session.session_id
        assert len(session.checkpoints) == 1

    def test_pause_sets_status(self) -> None:
        rt = _build_full_runtime()
        session = rt.start_session()
        paused = rt.pause()
        assert paused.status == WorkstationSessionStatus.PAUSED

    def test_resume_sets_status(self) -> None:
        rt = _build_full_runtime()
        session = rt.start_session()
        rt.checkpoint()
        rt.pause()
        resume = rt.resume()
        assert isinstance(resume, WorkstationSessionResume)
        assert resume.session_id == session.session_id

    def test_close_sets_status(self) -> None:
        rt = _build_full_runtime()
        session = rt.start_session()
        closed = rt.close()
        assert closed.status == WorkstationSessionStatus.CLOSED

    def test_full_lifecycle(self) -> None:
        rt = _build_full_runtime()
        s = rt.start_session()
        rt.checkpoint()
        rt.pause()
        resume = rt.resume()
        rt.close()
        s_final = rt._sessions[s.session_id]
        assert s_final.status == WorkstationSessionStatus.CLOSED
        assert s_final.resume_count == 1


# ── Resume Context ────────────────────────────────────────────────────────


class TestResumeContext:
    def test_resume_has_orchestrator_context(self) -> None:
        rt = _build_full_runtime()
        rt.start_session()
        rt.checkpoint()
        rt.pause()
        resume = rt.resume()
        assert resume.orchestrator_context.get("active_projection") == "entrepreneuros"

    def test_resume_has_active_repo(self) -> None:
        rt = _build_full_runtime()
        rt.start_session()
        rt.checkpoint()
        rt.pause()
        resume = rt.resume()
        assert resume.orchestrator_context.get("active_repo") == "OS"

    def test_resume_has_active_files(self) -> None:
        rt = _build_full_runtime()
        rt.start_session()
        rt.checkpoint()
        rt.pause()
        resume = rt.resume()
        assert "types.py" in resume.orchestrator_context.get("active_files", [])

    def test_resume_has_active_loops(self) -> None:
        rt = _build_full_runtime()
        rt.start_session()
        rt.checkpoint()
        rt.pause()
        resume = rt.resume()
        assert len(resume.active_loops) == 2

    def test_resume_has_pending_decisions(self) -> None:
        rt = _build_full_runtime()
        rt.start_session()
        rt.checkpoint()
        rt.pause()
        resume = rt.resume()
        assert resume.pending_decisions == 2

    def test_resume_has_coherence_score(self) -> None:
        rt = _build_full_runtime()
        rt.start_session()
        rt.checkpoint()
        rt.pause()
        resume = rt.resume()
        assert resume.coherence_score == 0.85


# ── Changes Detection ─────────────────────────────────────────────────────


class TestChanges:
    def test_resume_has_changes(self) -> None:
        rt = _build_full_runtime()
        rt.start_session()
        rt.checkpoint()
        rt.pause()
        resume = rt.resume()
        assert len(resume.changes_since) == 2
        assert "file1.py updated" in resume.changes_since

    def test_resume_elapsed_time(self) -> None:
        rt = _build_full_runtime()
        rt.start_session()
        rt.checkpoint()
        rt.pause()
        resume = rt.resume()
        assert resume.elapsed_since_last >= 0.0

    def test_previous_checkpoint_included(self) -> None:
        rt = _build_full_runtime()
        rt.start_session()
        chk = rt.checkpoint()
        rt.pause()
        resume = rt.resume()
        assert resume.previous_checkpoint.get("checkpoint_id") == chk.checkpoint_id

    def test_no_checkpoint_resume_still_works(self) -> None:
        rt = _build_full_runtime()
        rt.start_session()
        resume = rt.resume()
        assert resume.previous_checkpoint == {}


# ── Checkpoint ────────────────────────────────────────────────────────────


class TestCheckpoint:
    def test_checkpoint_captures_orchestrator_context(self) -> None:
        rt = _build_full_runtime()
        rt.start_session()
        chk = rt.checkpoint()
        assert chk.orchestrator_context.get("active_projection") == "entrepreneuros"

    def test_checkpoint_captures_loops(self) -> None:
        rt = _build_full_runtime()
        rt.start_session()
        chk = rt.checkpoint()
        assert len(chk.active_loops) == 2

    def test_checkpoint_captures_coherence(self) -> None:
        rt = _build_full_runtime()
        rt.start_session()
        chk = rt.checkpoint()
        assert chk.coherence_score == 0.85

    def test_checkpoint_updates_session_timestamp(self) -> None:
        rt = _build_full_runtime()
        session = rt.start_session()
        before = time.time()
        rt.checkpoint()
        assert session.last_checkpoint_at >= before


# ── Multiple Checkpoints ─────────────────────────────────────────────────


class TestMultipleCheckpoints:
    def test_multiple_checkpoints_ordered(self) -> None:
        rt = _build_full_runtime()
        session = rt.start_session()
        rt.checkpoint()
        rt.checkpoint()
        rt.checkpoint()
        assert len(session.checkpoints) == 3
        timestamps = [c.timestamp for c in session.checkpoints]
        assert timestamps == sorted(timestamps)

    def test_last_checkpoint_returns_most_recent(self) -> None:
        rt = _build_full_runtime()
        rt.start_session()
        rt.checkpoint()
        last = rt.checkpoint()
        result = rt.last_checkpoint()
        assert result is not None
        assert result.checkpoint_id == last.checkpoint_id

    def test_last_checkpoint_no_session(self) -> None:
        rt = _build_full_runtime()
        assert rt.last_checkpoint() is None


# ── Session History ───────────────────────────────────────────────────────


class TestSessionHistory:
    def test_history_returns_sessions(self) -> None:
        rt = _build_full_runtime()
        rt.start_session()
        rt.close()
        rt.start_session()
        history = rt.session_history()
        assert len(history) == 2

    def test_history_reverse_chronological(self) -> None:
        rt = _build_full_runtime()
        s1 = rt.start_session()
        rt.close()
        s2 = rt.start_session()
        history = rt.session_history()
        assert history[0].session_id == s2.session_id

    def test_history_limit(self) -> None:
        rt = _build_full_runtime()
        for _ in range(5):
            rt.start_session()
            rt.close()
        assert len(rt.session_history(limit=3)) == 3


# ── Missing Deps ──────────────────────────────────────────────────────────


class TestMissingDeps:
    def test_no_awareness(self) -> None:
        rt = WorkstationSessionRuntime()
        rt.start_session()
        chk = rt.checkpoint()
        assert chk.orchestrator_context == {}

    def test_no_loops(self) -> None:
        rt = WorkstationSessionRuntime()
        rt.start_session()
        chk = rt.checkpoint()
        assert chk.active_loops == []

    def test_no_approvals(self) -> None:
        rt = WorkstationSessionRuntime()
        rt.start_session()
        chk = rt.checkpoint()
        assert chk.pending_approvals == 0

    def test_no_coherence(self) -> None:
        rt = WorkstationSessionRuntime()
        rt.start_session()
        chk = rt.checkpoint()
        assert chk.coherence_score == 0.0

    def test_no_continuity_runtime(self) -> None:
        rt = WorkstationSessionRuntime()
        rt.start_session()
        rt.checkpoint()
        rt.pause()
        resume = rt.resume()
        assert resume.changes_since == []

    def test_no_attention(self) -> None:
        rt = WorkstationSessionRuntime()
        rt.start_session()
        chk = rt.checkpoint()
        assert chk.attention_items == []

    def test_resume_no_deps(self) -> None:
        rt = WorkstationSessionRuntime()
        rt.start_session()
        resume = rt.resume()
        assert resume.next_actions == ["No immediate actions — system stable"]

    def test_no_session_resume(self) -> None:
        rt = WorkstationSessionRuntime()
        resume = rt.resume()
        assert resume.next_actions == ["No session found"]


# ── Next Actions ──────────────────────────────────────────────────────────


class TestNextActions:
    def test_next_actions_from_blocked_loops(self) -> None:
        rt = _build_full_runtime()
        rt.start_session()
        rt.checkpoint()
        resume = rt.resume()
        assert any("Review/approve" in a for a in resume.next_actions)

    def test_next_actions_from_approvals(self) -> None:
        rt = _build_full_runtime()
        rt.start_session()
        rt.checkpoint()
        resume = rt.resume()
        assert any("approval" in a.lower() for a in resume.next_actions)

    def test_next_actions_from_attention(self) -> None:
        rt = _build_full_runtime()
        rt.start_session()
        rt.checkpoint()
        resume = rt.resume()
        assert any("Attention" in a for a in resume.next_actions)

    def test_next_actions_stable_when_empty(self) -> None:
        rt = WorkstationSessionRuntime()
        rt.start_session()
        resume = rt.resume()
        assert "system stable" in resume.next_actions[0]


# ── Active Session ────────────────────────────────────────────────────────


class TestActiveSession:
    def test_active_session_returns_current(self) -> None:
        rt = _build_full_runtime()
        session = rt.start_session()
        active = rt.active_session()
        assert active is not None
        assert active.session_id == session.session_id

    def test_active_session_none_when_closed(self) -> None:
        rt = _build_full_runtime()
        rt.start_session()
        rt.close()
        assert rt.active_session() is None


# ── Serialization ─────────────────────────────────────────────────────────


class TestSerialization:
    def test_session_to_dict(self) -> None:
        rt = _build_full_runtime()
        session = rt.start_session()
        d = session.to_dict()
        assert "session_id" in d
        assert "status" in d

    def test_resume_to_dict(self) -> None:
        rt = _build_full_runtime()
        rt.start_session()
        rt.checkpoint()
        rt.pause()
        resume = rt.resume()
        d = resume.to_dict()
        assert "orchestrator_context" in d
        assert "next_actions" in d
