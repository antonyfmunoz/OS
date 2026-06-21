"""Tests for MetaIDEProjectionLoopRuntime — Campaign 3.4.

Covers: submit pipeline, projection detection, phase state machine,
error handling, status aggregation, history/active filtering.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from substrate.workstation.meta_ide_projection_loop_runtime import (
    BuildLoopPhase,
    BuildLoopStatus,
    BuildRequest,
    MetaIDEProjectionLoopRuntime,
    _detect_projection,
)


# ── Projection Detection ──────────────────────────────────────────────────

class TestProjectionDetection:
    def test_detect_eos_keyword(self) -> None:
        assert _detect_projection("Fix the EOS pipeline") == "entrepreneuros"

    def test_detect_lyfeos_keyword(self) -> None:
        assert _detect_projection("LyfeOS needs updates") == "lyfeos"

    def test_detect_creatoros_keyword(self) -> None:
        assert _detect_projection("Update CreatorOS content") == "creatoros"

    def test_detect_no_match(self) -> None:
        assert _detect_projection("Fix a generic bug") == ""

    def test_explicit_target_overrides(self) -> None:
        assert _detect_projection("Fix a bug", explicit_target="eos") == "entrepreneuros"

    def test_explicit_unknown_target_passes_through(self) -> None:
        assert _detect_projection("Fix a bug", explicit_target="unknown_proj") == "unknown_proj"

    def test_case_insensitive_keyword(self) -> None:
        assert _detect_projection("update the lyfeos integration") == "lyfeos"

    def test_outreach_maps_to_eos(self) -> None:
        assert _detect_projection("Improve outreach pipeline") == "entrepreneuros"


# ── Submit Pipeline ────────────────────────────────────────────────────────

class TestSubmitPipeline:
    def test_submit_no_deps_returns_request(self) -> None:
        runtime = MetaIDEProjectionLoopRuntime()
        req = runtime.submit("Build a feature")
        assert isinstance(req, BuildRequest)
        assert req.request_id.startswith("br-")
        assert req.text == "Build a feature"
        assert req.error == "MetaIDERuntime not available"

    def test_submit_with_embodiment(self) -> None:
        embodiment = MagicMock()
        embodiment.classify_intent.return_value = {"type": "feature_request"}
        runtime = MetaIDEProjectionLoopRuntime(embodiment=embodiment)
        req = runtime.submit("Add login screen")
        assert req.intent_classification == {"type": "feature_request"}

    def test_submit_with_meta_ide(self) -> None:
        meta_ide = MagicMock()
        plan = MagicMock()
        plan.plan_id = "plan-001"
        meta_ide.plan_from_intent.return_value = plan
        meta_ide.dispatch_plan.return_value = [MagicMock(dispatch_id="d-001")]
        runtime = MetaIDEProjectionLoopRuntime(meta_ide=meta_ide)
        req = runtime.submit("Build feature")
        assert req.plan_id == "plan-001"
        assert req.dispatch_ids == ["d-001"]
        assert req.phase == BuildLoopPhase.EXECUTION

    def test_submit_detects_projection(self) -> None:
        runtime = MetaIDEProjectionLoopRuntime()
        req = runtime.submit("Update LyfeOS signals")
        assert req.projection_target == "lyfeos"

    def test_submit_explicit_projection_target(self) -> None:
        runtime = MetaIDEProjectionLoopRuntime()
        req = runtime.submit("Fix something", projection_target="creatoros")
        assert req.projection_target == "creatoros"

    def test_submit_records_in_store(self) -> None:
        runtime = MetaIDEProjectionLoopRuntime()
        req = runtime.submit("test")
        detail = runtime.request_detail(req.request_id)
        assert detail is not None
        assert detail.request_id == req.request_id

    def test_submit_with_execution_graph(self) -> None:
        meta_ide = MagicMock()
        plan = MagicMock()
        plan.plan_id = "plan-002"
        meta_ide.plan_from_intent.return_value = plan
        meta_ide.dispatch_plan.return_value = [MagicMock(dispatch_id="d-002")]
        eg = MagicMock()
        runtime = MetaIDEProjectionLoopRuntime(meta_ide=meta_ide, execution_graph=eg)
        runtime.submit("Build it")
        eg.record.assert_called_once()

    def test_submit_embodiment_failure_graceful(self) -> None:
        embodiment = MagicMock()
        embodiment.classify_intent.side_effect = RuntimeError("boom")
        runtime = MetaIDEProjectionLoopRuntime(embodiment=embodiment)
        req = runtime.submit("Test resilience")
        assert req.intent_classification == {}


# ── Phase State Machine ────────────────────────────────────────────────────

class TestPhaseStateMachine:
    def _make_runtime_with_request(self) -> tuple[MetaIDEProjectionLoopRuntime, str]:
        meta_ide = MagicMock()
        plan = MagicMock()
        plan.plan_id = "plan-test"
        meta_ide.plan_from_intent.return_value = plan
        meta_ide.dispatch_plan.return_value = [MagicMock(dispatch_id="d-test")]
        meta_ide.review_packages.return_value = MagicMock(review_id="rv-test")
        meta_ide.approve_and_merge.return_value = {"status": "merged"}
        runtime = MetaIDEProjectionLoopRuntime(meta_ide=meta_ide)
        req = runtime.submit("Test feature")
        return runtime, req.request_id

    def test_advance_moves_phase(self) -> None:
        runtime, rid = self._make_runtime_with_request()
        req = runtime.advance(rid)
        assert req.phase == BuildLoopPhase.REVIEW

    def test_review_sets_review_phase(self) -> None:
        runtime, rid = self._make_runtime_with_request()
        req = runtime.review(rid)
        assert req.phase == BuildLoopPhase.REVIEW

    def test_merge_completes(self) -> None:
        runtime, rid = self._make_runtime_with_request()
        runtime.review(rid)
        req = runtime.merge(rid)
        assert req.phase == BuildLoopPhase.COMPLETE
        assert req.merge_result.get("status") == "merged"

    def test_reject_returns_to_planning(self) -> None:
        runtime, rid = self._make_runtime_with_request()
        runtime.review(rid)
        req = runtime.reject(rid, "Not good enough")
        assert req.phase == BuildLoopPhase.PLANNING
        assert "Rejected" in req.error

    def test_advance_unknown_request(self) -> None:
        runtime = MetaIDEProjectionLoopRuntime()
        req = runtime.advance("nonexistent")
        assert req.error == "Request not found"

    def test_review_wrong_phase(self) -> None:
        runtime = MetaIDEProjectionLoopRuntime()
        req = runtime.submit("test")
        result = runtime.review(req.request_id)
        assert "Cannot review" in result.error

    def test_merge_wrong_phase(self) -> None:
        runtime = MetaIDEProjectionLoopRuntime()
        req = runtime.submit("test")
        result = runtime.merge(req.request_id)
        assert "Cannot merge" in result.error


# ── Status Aggregation ─────────────────────────────────────────────────────

class TestStatusAggregation:
    def test_status_empty(self) -> None:
        runtime = MetaIDEProjectionLoopRuntime()
        status = runtime.status()
        assert isinstance(status, BuildLoopStatus)
        assert status.active_requests == 0

    def test_status_counts_active(self) -> None:
        runtime = MetaIDEProjectionLoopRuntime()
        runtime.submit("task 1")
        runtime.submit("task 2")
        status = runtime.status()
        assert status.active_requests == 2

    def test_status_projection_distribution(self) -> None:
        runtime = MetaIDEProjectionLoopRuntime()
        runtime.submit("Fix LyfeOS bug")
        runtime.submit("Fix EOS pipeline")
        status = runtime.status()
        assert "lyfeos" in status.projection_distribution
        assert "entrepreneuros" in status.projection_distribution

    def test_status_to_dict(self) -> None:
        runtime = MetaIDEProjectionLoopRuntime()
        d = runtime.status().to_dict()
        assert "active_requests" in d
        assert "by_phase" in d

    def test_status_with_fleet(self) -> None:
        fleet = MagicMock()
        fleet_st = MagicMock()
        fleet_st.active_agents = 3
        fleet.fleet_status.return_value = fleet_st
        runtime = MetaIDEProjectionLoopRuntime(agent_fleet=fleet)
        status = runtime.status()
        assert status.active_agents == 3


# ── History and Active ─────────────────────────────────────────────────────

class TestHistoryActive:
    def test_active_requests_empty(self) -> None:
        runtime = MetaIDEProjectionLoopRuntime()
        assert runtime.active_requests() == []

    def test_active_requests_excludes_complete(self) -> None:
        meta_ide = MagicMock()
        plan = MagicMock()
        plan.plan_id = "plan-h"
        meta_ide.plan_from_intent.return_value = plan
        meta_ide.dispatch_plan.return_value = [MagicMock(dispatch_id="d-h")]
        meta_ide.review_packages.return_value = MagicMock(review_id="rv-h")
        meta_ide.approve_and_merge.return_value = {"status": "merged"}
        runtime = MetaIDEProjectionLoopRuntime(meta_ide=meta_ide)
        req = runtime.submit("test")
        runtime.review(req.request_id)
        runtime.merge(req.request_id)
        assert len(runtime.active_requests()) == 0
        assert len(runtime.history()) == 1

    def test_history_limit(self) -> None:
        runtime = MetaIDEProjectionLoopRuntime()
        for i in range(5):
            runtime.submit(f"task {i}")
        assert len(runtime.history(limit=3)) == 0  # none completed

    def test_request_detail_none(self) -> None:
        runtime = MetaIDEProjectionLoopRuntime()
        assert runtime.request_detail("nonexistent") is None


# ── Type Serialization ─────────────────────────────────────────────────────

class TestTypeSerialization:
    def test_build_request_to_dict(self) -> None:
        req = BuildRequest(text="test build")
        d = req.to_dict()
        assert d["text"] == "test build"
        assert "request_id" in d
        assert "phase" in d

    def test_build_loop_status_to_dict(self) -> None:
        s = BuildLoopStatus(active_requests=2, by_phase={"planning": 1, "execution": 1})
        d = s.to_dict()
        assert d["active_requests"] == 2
        assert d["by_phase"]["planning"] == 1

    def test_build_request_auto_generates_id(self) -> None:
        req = BuildRequest(text="test")
        assert req.request_id.startswith("br-")
        assert len(req.request_id) > 3


# ── Full Lifecycle Validation ─────────────────────────────────────────────

class TestFullLifecycleValidation:
    """End-to-end engineering loop validation for governed changes."""

    def test_file_tree_fix_lifecycle(self) -> None:
        """Validate the Meta IDE file tree fix through full engineering loop."""
        meta_ide = MagicMock()
        plan = MagicMock()
        plan.plan_id = "plan-file-tree-fix"
        meta_ide.plan_from_intent.return_value = plan
        meta_ide.dispatch_plan.return_value = [
            MagicMock(dispatch_id="d-browse-backend"),
            MagicMock(dispatch_id="d-browse-frontend"),
            MagicMock(dispatch_id="d-cache-hydration"),
        ]
        meta_ide.review_packages.return_value = MagicMock(review_id="rv-file-tree")
        meta_ide.approve_and_merge.return_value = {"status": "merged", "commits": 6}

        eg = MagicMock()
        runtime = MetaIDEProjectionLoopRuntime(
            meta_ide=meta_ide, execution_graph=eg,
        )

        req = runtime.submit(
            "Fix Meta IDE file tree: eliminate frontend path assumptions, "
            "let backend resolve browse roots via UMH_ROOT and device_registry.json"
        )
        assert req.phase == BuildLoopPhase.EXECUTION
        assert req.plan_id == "plan-file-tree-fix"
        assert len(req.dispatch_ids) == 3

        result = runtime.review(req.request_id)
        assert result.phase == BuildLoopPhase.REVIEW
        assert result.review_id == "rv-file-tree"

        result = runtime.merge(req.request_id)
        assert result.phase == BuildLoopPhase.COMPLETE
        assert result.merge_result["status"] == "merged"

        assert len(runtime.active_requests()) == 0
        assert len(runtime.history()) == 1

        eg.record.assert_called()

    def test_no_deps_still_processes(self) -> None:
        """Engineering loop without wired dependencies records and tracks."""
        runtime = MetaIDEProjectionLoopRuntime()
        req = runtime.submit("Validate a fix without MetaIDERuntime")
        assert req.request_id.startswith("br-")
        assert runtime.request_detail(req.request_id) is not None
        assert runtime.status().active_requests == 1
