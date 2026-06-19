"""Tests for OperatingLoopRuntime — Campaign 4.1.

Covers: loop tracking, transitions, active/completed filtering,
intent correlation, lineage, snapshots, error handling,
graceful degradation, serialization.
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

from typing import Any
from unittest.mock import MagicMock

import pytest

from substrate.workstation.operating_loop_runtime import (
    OperatingLoop,
    OperatingLoopRuntime,
    OperatingLoopSnapshot,
    OperatingLoopStage,
    OperatingLoopTransition,
)


# ── Fixtures ──────────────────────────────────────────────────────────────


def _mock_graph() -> MagicMock:
    m = MagicMock()
    m.trace_from_intent.return_value = {
        "intent_id": "i-1",
        "nodes": [{"id": "n-1"}, {"id": "n-2"}],
    }
    m.audit_completeness.return_value = {"complete": 10, "incomplete": 2}
    return m


def _build_runtime(**kwargs: Any) -> OperatingLoopRuntime:
    return OperatingLoopRuntime(**kwargs)


# ── Track ─────────────────────────────────────────────────────────────────


class TestTrack:
    def test_track_creates_loop(self) -> None:
        rt = _build_runtime()
        loop = rt.track("Build feature X")
        assert loop.loop_id.startswith("oloop-")
        assert loop.intent_text == "Build feature X"
        assert loop.current_stage == OperatingLoopStage.INTENT

    def test_track_with_intent_id(self) -> None:
        rt = _build_runtime()
        loop = rt.track("Build feature", intent_id="int-abc")
        assert loop.intent_id == "int-abc"

    def test_track_records_initial_transition(self) -> None:
        rt = _build_runtime()
        loop = rt.track("Test")
        assert len(loop.lineage) == 1
        assert loop.lineage[0].subsystem == "operator"

    def test_track_sets_created_at(self) -> None:
        rt = _build_runtime()
        before = time.time()
        loop = rt.track("Test")
        assert loop.created_at >= before


# ── Transitions ───────────────────────────────────────────────────────────


class TestTransitions:
    def test_transition_updates_stage(self) -> None:
        rt = _build_runtime()
        loop = rt.track("Test")
        updated = rt.record_transition(loop.loop_id, OperatingLoopStage.PLAN, "meta_ide")
        assert updated.current_stage == OperatingLoopStage.PLAN

    def test_transition_appends_lineage(self) -> None:
        rt = _build_runtime()
        loop = rt.track("Test")
        rt.record_transition(loop.loop_id, OperatingLoopStage.PLAN, "meta_ide")
        rt.record_transition(loop.loop_id, OperatingLoopStage.ASSIGN, "fleet")
        assert len(loop.lineage) == 3

    def test_transition_from_stage_correct(self) -> None:
        rt = _build_runtime()
        loop = rt.track("Test")
        rt.record_transition(loop.loop_id, OperatingLoopStage.PLAN, "ide")
        last = loop.lineage[-1]
        assert last.from_stage == OperatingLoopStage.INTENT
        assert last.to_stage == OperatingLoopStage.PLAN

    def test_transition_with_metadata(self) -> None:
        rt = _build_runtime()
        loop = rt.track("Test")
        rt.record_transition(loop.loop_id, OperatingLoopStage.PLAN, "ide", {"plan_id": "p-1"})
        assert loop.lineage[-1].metadata["plan_id"] == "p-1"

    def test_transition_to_complete(self) -> None:
        rt = _build_runtime()
        loop = rt.track("Test")
        rt.record_transition(loop.loop_id, OperatingLoopStage.COMPLETE, "learning")
        assert loop.completed_at > 0

    def test_transition_unknown_loop(self) -> None:
        rt = _build_runtime()
        result = rt.record_transition("bad-id", OperatingLoopStage.PLAN, "ide")
        assert result.error == "Loop not found"


# ── Active/Completed ─────────────────────────────────────────────────────


class TestActiveCompleted:
    def test_active_loops_returns_non_terminal(self) -> None:
        rt = _build_runtime()
        rt.track("A")
        rt.track("B")
        assert len(rt.active_loops()) == 2

    def test_completed_not_in_active(self) -> None:
        rt = _build_runtime()
        loop = rt.track("Done")
        rt.record_transition(loop.loop_id, OperatingLoopStage.COMPLETE, "done")
        assert len(rt.active_loops()) == 0

    def test_completed_loops_returns_terminal(self) -> None:
        rt = _build_runtime()
        loop = rt.track("Done")
        rt.record_transition(loop.loop_id, OperatingLoopStage.COMPLETE, "done")
        assert len(rt.completed_loops()) == 1

    def test_completed_loops_limit(self) -> None:
        rt = _build_runtime()
        for i in range(5):
            loop = rt.track(f"T{i}")
            rt.record_transition(loop.loop_id, OperatingLoopStage.COMPLETE, "done")
        assert len(rt.completed_loops(limit=2)) == 2


# ── Correlate ─────────────────────────────────────────────────────────────


class TestCorrelate:
    def test_correlate_by_intent_id(self) -> None:
        rt = _build_runtime()
        loop = rt.track("Feature", intent_id="int-xyz")
        found = rt.correlate_intent("int-xyz")
        assert found is not None
        assert found.loop_id == loop.loop_id

    def test_correlate_not_found(self) -> None:
        rt = _build_runtime()
        assert rt.correlate_intent("nonexistent") is None

    def test_get_by_id(self) -> None:
        rt = _build_runtime()
        loop = rt.track("Test")
        assert rt.get(loop.loop_id) is not None

    def test_get_unknown_returns_none(self) -> None:
        rt = _build_runtime()
        assert rt.get("fake") is None


# ── Lineage ───────────────────────────────────────────────────────────────


class TestLineage:
    def test_lineage_for_with_graph(self) -> None:
        rt = _build_runtime(execution_graph=_mock_graph())
        loop = rt.track("Feature", intent_id="i-1")
        result = rt.lineage_for(loop.loop_id)
        assert "nodes" in result

    def test_lineage_for_no_graph(self) -> None:
        rt = _build_runtime()
        loop = rt.track("Feature", intent_id="i-1")
        result = rt.lineage_for(loop.loop_id)
        assert "lineage" in result

    def test_lineage_for_no_intent_id(self) -> None:
        rt = _build_runtime(execution_graph=_mock_graph())
        loop = rt.track("Feature")
        result = rt.lineage_for(loop.loop_id)
        assert result["note"] == "No intent_id to trace"

    def test_lineage_for_unknown_loop(self) -> None:
        rt = _build_runtime()
        result = rt.lineage_for("bad-id")
        assert "error" in result


# ── Snapshot ──────────────────────────────────────────────────────────────


class TestSnapshot:
    def test_snapshot_empty(self) -> None:
        rt = _build_runtime()
        snap = rt.snapshot()
        assert snap.active_loops == 0
        assert snap.completed_count == 0

    def test_snapshot_counts_active(self) -> None:
        rt = _build_runtime()
        rt.track("A")
        rt.track("B")
        snap = rt.snapshot()
        assert snap.active_loops == 2

    def test_snapshot_counts_by_stage(self) -> None:
        rt = _build_runtime()
        loop = rt.track("A")
        rt.record_transition(loop.loop_id, OperatingLoopStage.PLAN, "ide")
        rt.track("B")
        snap = rt.snapshot()
        assert snap.by_stage.get("plan", 0) == 1
        assert snap.by_stage.get("intent", 0) == 1

    def test_snapshot_lineage_health_from_graph(self) -> None:
        rt = _build_runtime(execution_graph=_mock_graph())
        snap = rt.snapshot()
        assert snap.lineage_health.get("complete") == 10

    def test_snapshot_to_dict(self) -> None:
        rt = _build_runtime()
        rt.track("A")
        d = rt.snapshot().to_dict()
        assert "active_loops" in d
        assert "generated_at" in d


# ── Error/Failed ──────────────────────────────────────────────────────────


class TestErrorHandling:
    def test_failed_stage_records_error(self) -> None:
        rt = _build_runtime()
        loop = rt.track("Bad task")
        rt.record_transition(
            loop.loop_id, OperatingLoopStage.FAILED, "compute",
            metadata={"error": "OOM"},
        )
        assert loop.error == "OOM"
        assert loop.current_stage == OperatingLoopStage.FAILED

    def test_failed_loop_in_completed(self) -> None:
        rt = _build_runtime()
        loop = rt.track("Bad")
        rt.record_transition(loop.loop_id, OperatingLoopStage.FAILED, "x")
        assert len(rt.active_loops()) == 0
        assert len(rt.completed_loops()) == 1

    def test_failed_without_error_metadata(self) -> None:
        rt = _build_runtime()
        loop = rt.track("Bad")
        rt.record_transition(loop.loop_id, OperatingLoopStage.FAILED, "x")
        assert loop.error == "Unknown failure"


# ── No Deps ──────────────────────────────────────────────────────────────


class TestNoDeps:
    def test_no_graph_snapshot_graceful(self) -> None:
        rt = _build_runtime()
        snap = rt.snapshot()
        assert snap.lineage_health == {}

    def test_no_deps_track_works(self) -> None:
        rt = _build_runtime()
        loop = rt.track("Independent")
        assert loop.loop_id.startswith("oloop-")

    def test_no_deps_transition_works(self) -> None:
        rt = _build_runtime()
        loop = rt.track("Test")
        updated = rt.record_transition(loop.loop_id, OperatingLoopStage.PLAN, "manual")
        assert updated.current_stage == OperatingLoopStage.PLAN


# ── Serialization ─────────────────────────────────────────────────────────


class TestSerialization:
    def test_loop_to_dict(self) -> None:
        rt = _build_runtime()
        loop = rt.track("Test")
        d = loop.to_dict()
        assert d["loop_id"] == loop.loop_id
        assert d["current_stage"] == "intent"
        assert "lineage" in d

    def test_transition_to_dict(self) -> None:
        t = OperatingLoopTransition(
            from_stage=OperatingLoopStage.INTENT,
            to_stage=OperatingLoopStage.PLAN,
            subsystem="ide",
        )
        d = t.to_dict()
        assert d["from_stage"] == "intent"
        assert d["to_stage"] == "plan"

    def test_snapshot_to_dict_round_trip(self) -> None:
        snap = OperatingLoopSnapshot(active_loops=3, by_stage={"plan": 2, "intent": 1})
        d = snap.to_dict()
        assert d["active_loops"] == 3
        assert d["by_stage"]["plan"] == 2


# ── Multiple Loops ────────────────────────────────────────────────────────


class TestMultipleLoops:
    def test_concurrent_tracking(self) -> None:
        rt = _build_runtime()
        l1 = rt.track("Feature A", intent_id="i-a")
        l2 = rt.track("Feature B", intent_id="i-b")
        rt.record_transition(l1.loop_id, OperatingLoopStage.PLAN, "ide")
        rt.record_transition(l2.loop_id, OperatingLoopStage.EXECUTE, "fleet")
        assert l1.current_stage == OperatingLoopStage.PLAN
        assert l2.current_stage == OperatingLoopStage.EXECUTE

    def test_mixed_active_completed(self) -> None:
        rt = _build_runtime()
        l1 = rt.track("A")
        l2 = rt.track("B")
        rt.record_transition(l1.loop_id, OperatingLoopStage.COMPLETE, "done")
        assert len(rt.active_loops()) == 1
        assert len(rt.completed_loops()) == 1

    def test_correlate_returns_correct_loop(self) -> None:
        rt = _build_runtime()
        rt.track("A", intent_id="i-a")
        l2 = rt.track("B", intent_id="i-b")
        found = rt.correlate_intent("i-b")
        assert found is not None
        assert found.loop_id == l2.loop_id

    def test_trace_isolated_per_loop(self) -> None:
        rt = _build_runtime()
        l1 = rt.track("A")
        l2 = rt.track("B")
        rt.record_transition(l1.loop_id, OperatingLoopStage.PLAN, "ide")
        assert len(rt.trace(l1.loop_id)) == 2
        assert len(rt.trace(l2.loop_id)) == 1
