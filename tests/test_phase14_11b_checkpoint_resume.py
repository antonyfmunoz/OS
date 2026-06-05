"""Phase 14.11B — Checkpoint + resume brief tests.

Tests checkpoint creation, persistence, retrieval, return brief generation,
and the resume endpoint integration.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.workstation.checkpoint import CheckpointManager, ContinuityCheckpoint
from substrate.workstation.resume_brief import ReturnBrief, ReturnBriefGenerator


class TestContinuityCheckpoint:
    def test_auto_id(self) -> None:
        cp = ContinuityCheckpoint(
            previous_continuity_state="active",
            new_continuity_state="idle",
        )
        assert cp.checkpoint_id.startswith("ckpt_")

    def test_auto_timestamp(self) -> None:
        cp = ContinuityCheckpoint()
        assert cp.timestamp != ""

    def test_to_dict(self) -> None:
        cp = ContinuityCheckpoint(
            previous_continuity_state="active",
            new_continuity_state="night_sleeping",
            lifecycle_mode="night_cycle",
            risk_ceiling="LOW",
        )
        d = cp.to_dict()
        assert d["previous_continuity_state"] == "active"
        assert d["new_continuity_state"] == "night_sleeping"
        assert d["lifecycle_mode"] == "night_cycle"
        assert d["risk_ceiling"] == "LOW"

    def test_from_dict(self) -> None:
        data = {
            "checkpoint_id": "ckpt_test",
            "previous_continuity_state": "idle",
            "new_continuity_state": "away",
            "lifecycle_mode": "away",
            "active_profile_modes": ["developer", "research"],
        }
        cp = ContinuityCheckpoint.from_dict(data)
        assert cp.checkpoint_id == "ckpt_test"
        assert cp.active_profile_modes == ["developer", "research"]

    def test_all_fields(self) -> None:
        cp = ContinuityCheckpoint(
            previous_continuity_state="active",
            new_continuity_state="night_sleeping",
            lifecycle_mode="night_cycle",
            active_profile_modes=["developer"],
            risk_ceiling="LOW",
            active_node="vps",
            active_environment="linux",
            active_work_packets=[{"id": "wp1"}],
            active_sessions=[{"id": "s1"}],
            active_agents=[{"name": "executor"}],
            pending_approvals=[{"id": "a1"}],
            recent_traces=[{"id": "t1"}],
            open_loops=["loop1"],
            recommended_next_action="review approvals",
            safe_work_constraints={"risk_ceiling": "LOW"},
            transition_reason="end of day",
        )
        d = cp.to_dict()
        assert len(d) == 18


class TestCheckpointManager:
    def test_create_and_retrieve(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(state_dir=tmpdir)
            cp = mgr.create_checkpoint(
                previous_state="active",
                new_state="idle",
                lifecycle_mode="idle",
                transition_reason="timeout",
            )
            assert cp.checkpoint_id.startswith("ckpt_")

            loaded = mgr.latest()
            assert loaded is not None
            assert loaded.previous_continuity_state == "active"
            assert loaded.new_continuity_state == "idle"

    def test_latest_returns_none_when_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(state_dir=tmpdir)
            assert mgr.latest() is None

    def test_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(state_dir=tmpdir)
            mgr.create_checkpoint("active", "idle", transition_reason="1")
            mgr.create_checkpoint("idle", "away", transition_reason="2")
            mgr.create_checkpoint("away", "returning", transition_reason="3")

            history = mgr.history()
            assert len(history) == 3
            assert history[0].transition_reason == "1"
            assert history[2].transition_reason == "3"

    def test_history_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(state_dir=tmpdir)
            for i in range(5):
                mgr.create_checkpoint("a", "b", transition_reason=str(i))
            assert len(mgr.history(limit=3)) == 3

    def test_checkpoint_feeds_resume(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(state_dir=tmpdir)
            cp = mgr.create_checkpoint(
                previous_state="active",
                new_state="night_sleeping",
                lifecycle_mode="night_cycle",
                recommended_next_action="review morning queue",
            )
            loaded = mgr.latest()
            assert loaded.recommended_next_action == "review morning queue"


class TestReturnBrief:
    def test_auto_timestamp(self) -> None:
        brief = ReturnBrief()
        assert brief.generated_at != ""

    def test_to_dict(self) -> None:
        brief = ReturnBrief(
            continuity_state_at_departure="night_sleeping",
            continuity_state_now="active",
            resume_next="review approvals",
        )
        d = brief.to_dict()
        assert d["continuity_state_at_departure"] == "night_sleeping"
        assert d["resume_next"] == "review approvals"

    def test_from_dict(self) -> None:
        data = {
            "continuity_state_at_departure": "away",
            "continuity_state_now": "active",
            "what_happened": ["event1"],
        }
        brief = ReturnBrief.from_dict(data)
        assert brief.what_happened == ["event1"]


class TestReturnBriefGenerator:
    def test_generate_basic(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReturnBriefGenerator(state_dir=tmpdir)
            brief = gen.generate(
                departure_state="night_sleeping",
                current_state="active",
            )
            assert brief.continuity_state_at_departure == "night_sleeping"
            assert brief.continuity_state_now == "active"
            assert brief.resume_next != ""

    def test_generate_persists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReturnBriefGenerator(state_dir=tmpdir)
            gen.generate(departure_state="away", current_state="active")

            loaded = gen.latest()
            assert loaded is not None
            assert loaded.continuity_state_at_departure == "away"

    def test_latest_returns_none_when_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReturnBriefGenerator(state_dir=tmpdir)
            assert gen.latest() is None

    def test_next_action_failures_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReturnBriefGenerator(state_dir=tmpdir)
            brief = ReturnBrief(
                what_failed=["task1"],
                needs_approval=[{"id": "a1"}],
            )
            action = gen._derive_next_action(brief)
            assert "failed" in action.lower()

    def test_next_action_approvals_second(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReturnBriefGenerator(state_dir=tmpdir)
            brief = ReturnBrief(
                needs_approval=[{"id": "a1"}],
                what_is_blocked=["b1"],
            )
            action = gen._derive_next_action(brief)
            assert "approval" in action.lower()

    def test_next_action_blocked_third(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReturnBriefGenerator(state_dir=tmpdir)
            brief = ReturnBrief(what_is_blocked=["b1"])
            action = gen._derive_next_action(brief)
            assert "unblock" in action.lower()

    def test_next_action_default_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReturnBriefGenerator(state_dir=tmpdir)
            brief = ReturnBrief()
            action = gen._derive_next_action(brief)
            assert "ready" in action.lower()

    def test_brief_includes_mode_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReturnBriefGenerator(state_dir=tmpdir)
            brief = gen.generate(
                lifecycle_mode="night_cycle",
                active_profile_modes=["developer", "research"],
            )
            assert brief.lifecycle_mode == "night_cycle"
            assert brief.active_profile_modes == ["developer", "research"]


class TestRouteEndpoints:
    def test_checkpoint_module_imports(self) -> None:
        from substrate.workstation.checkpoint import CheckpointManager, ContinuityCheckpoint
        assert CheckpointManager is not None
        assert ContinuityCheckpoint is not None

    def test_resume_brief_module_imports(self) -> None:
        from substrate.workstation.resume_brief import ReturnBriefGenerator, ReturnBrief
        assert ReturnBriefGenerator is not None
        assert ReturnBrief is not None

    def test_routes_file_imports(self) -> None:
        from transports.api.cockpit_workstation_control_routes import workstation_control_router
        assert workstation_control_router is not None
