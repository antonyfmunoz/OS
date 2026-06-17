"""Tests for W2 — Meta IDE Runtime.

Validates the unified development surface: inspect → plan → assign →
monitor → review → merge, composing meta_ide subsystems + W3 fleet.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import Any

import pytest

sys.path.insert(0, "/opt/OS")

from substrate.organism.meta_ide_runtime import (
    DevelopmentPhase,
    DevelopmentStream,
    IDEPlan,
    IDEStatusSnapshot,
    MergeResult,
    MetaIDERuntime,
    ReviewDetail,
    ReviewStatus,
    WorkspaceSnapshot,
)


# ── Mock W3 Fleet ────────────────────────────────────────────────


@dataclass
class MockFleetAssignment:
    assignment_id: str = "fa-test"
    agent_type: str = "builder"
    agent_label: str = "Builder"
    compute_node_id: str = "dn-a1b2c3d4"
    compute_node_type: str = "vps"
    capabilities_required: list[str] = field(default_factory=lambda: ["code"])
    capabilities_matched: list[str] = field(default_factory=lambda: ["code"])
    risk_class: str = "low"

    def to_dict(self) -> dict:
        return {
            "assignment_id": self.assignment_id,
            "agent_type": self.agent_type,
            "compute_node_id": self.compute_node_id,
        }


@dataclass
class MockFleetDispatch:
    dispatch_id: str = "fd-test"
    assignment_id: str = "fa-test"
    agent_type: str = "builder"
    compute_node_id: str = "dn-a1b2c3d4"
    status: str = "dispatched"
    description: str = "test dispatch"

    def to_dict(self) -> dict:
        return {
            "dispatch_id": self.dispatch_id,
            "agent_type": self.agent_type,
            "status": self.status,
        }


class MockAgentFleet:
    def __init__(self):
        self._assign_count = 0
        self._dispatch_count = 0

    def assign(self, capabilities_required=None, risk_class="low", domain=""):
        self._assign_count += 1
        return MockFleetAssignment(
            assignment_id=f"fa-{self._assign_count}",
            capabilities_required=capabilities_required or ["code"],
        )

    def dispatch(self, assignment, description=""):
        self._dispatch_count += 1
        return MockFleetDispatch(
            dispatch_id=f"fd-{self._dispatch_count}",
            assignment_id=assignment.assignment_id,
            description=description,
        )

    def fleet_status(self):
        @dataclass
        class S:
            active_dispatches: int = 0
        return S(active_dispatches=self._dispatch_count)


class MockExecutionGraph:
    def __init__(self):
        self._nodes: list[dict] = []

    def add_node(self, node_id="", node_type="", metadata=None):
        self._nodes.append({"node_id": node_id, "node_type": node_type})

    def get_chain(self, plan_id):
        return [n["node_id"] for n in self._nodes if plan_id in str(n)]


# ── Helper ───────────────────────────────────────────────────────


def _make_ide(**kwargs) -> MetaIDERuntime:
    defaults = {
        "agent_fleet": MockAgentFleet(),
    }
    defaults.update(kwargs)
    return MetaIDERuntime(**defaults)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestWorkspaceSnapshot:
    def test_snapshot_structure(self):
        ide = _make_ide()
        snap = ide.workspace_snapshot()
        d = snap.to_dict()
        assert "repos" in d
        assert "active_sessions" in d
        assert "open_reviews" in d
        assert "pending_merges" in d

    def test_snapshot_empty(self):
        ide = _make_ide()
        snap = ide.workspace_snapshot()
        assert snap.active_sessions == 0
        assert snap.open_reviews == 0

    def test_snapshot_counts_active(self):
        ide = _make_ide()
        plan = ide.plan_from_intent("Build feature X")
        ide.dispatch_plan(plan.plan_id)
        snap = ide.workspace_snapshot()
        assert snap.active_sessions >= 1


class TestPlanFromIntent:
    def test_creates_plan(self):
        ide = _make_ide()
        plan = ide.plan_from_intent("Add health check endpoint")
        assert plan.plan_id.startswith("idp-")
        assert plan.intent_text == "Add health check endpoint"
        assert len(plan.tasks) >= 1

    def test_extracts_code_capability(self):
        ide = _make_ide()
        plan = ide.plan_from_intent("Build a new authentication module")
        assert "code" in plan.capabilities_needed

    def test_extracts_test_capability(self):
        ide = _make_ide()
        plan = ide.plan_from_intent("Test the payment flow")
        assert "test" in plan.capabilities_needed

    def test_extracts_deploy_capability(self):
        ide = _make_ide()
        plan = ide.plan_from_intent("Deploy the new version")
        assert "deploy" in plan.capabilities_needed

    def test_classifies_high_risk(self):
        ide = _make_ide()
        plan = ide.plan_from_intent("Run database migration for production")
        assert plan.risk_class == "high"

    def test_classifies_low_risk_default(self):
        ide = _make_ide()
        plan = ide.plan_from_intent("Add a new utility function")
        assert plan.risk_class == "low"

    def test_plan_stored(self):
        ide = _make_ide()
        plan = ide.plan_from_intent("Fix the bug")
        assert plan.plan_id in ide._plans

    def test_plan_to_dict(self):
        ide = _make_ide()
        plan = ide.plan_from_intent("Fix the bug")
        d = plan.to_dict()
        assert "plan_id" in d
        assert "tasks" in d
        assert "capabilities_needed" in d


class TestAssignPlan:
    def test_assign_returns_assignments(self):
        ide = _make_ide()
        plan = ide.plan_from_intent("Build feature X")
        assignments = ide.assign_plan(plan.plan_id)
        assert len(assignments) >= 1
        assert assignments[0]["agent_type"] == "builder"

    def test_assign_updates_status(self):
        ide = _make_ide()
        plan = ide.plan_from_intent("Build feature X")
        ide.assign_plan(plan.plan_id)
        assert ide._plans[plan.plan_id].status == "assigned"

    def test_assign_nonexistent_plan(self):
        ide = _make_ide()
        result = ide.assign_plan("nonexistent")
        assert result == []


class TestDispatchPlan:
    def test_dispatch_creates_streams(self):
        ide = _make_ide()
        plan = ide.plan_from_intent("Build feature X")
        dispatches = ide.dispatch_plan(plan.plan_id)
        assert len(dispatches) >= 1
        assert len(ide._streams) >= 1

    def test_dispatch_updates_plan_status(self):
        ide = _make_ide()
        plan = ide.plan_from_intent("Build feature X")
        ide.dispatch_plan(plan.plan_id)
        assert ide._plans[plan.plan_id].status == "dispatched"

    def test_dispatch_with_execution_graph(self):
        graph = MockExecutionGraph()
        ide = _make_ide(execution_graph=graph)
        plan = ide.plan_from_intent("Build feature X")
        ide.dispatch_plan(plan.plan_id)
        assert len(graph._nodes) >= 1

    def test_dispatch_nonexistent_plan(self):
        ide = _make_ide()
        result = ide.dispatch_plan("nonexistent")
        assert result == []


class TestActiveDevelopment:
    def test_active_streams(self):
        ide = _make_ide()
        plan = ide.plan_from_intent("Build feature X")
        ide.dispatch_plan(plan.plan_id)
        active = ide.active_development()
        assert len(active) >= 1
        assert active[0].agent_type == "builder"

    def test_no_active_initially(self):
        ide = _make_ide()
        assert ide.active_development() == []


class TestReviewFlow:
    def test_create_review(self):
        ide = _make_ide()
        review = ide.create_review(plan_id="test-plan", artifacts=[{"file": "main.py"}])
        assert review.review_id.startswith("rv-")
        assert review.status == ReviewStatus.PENDING

    def test_review_packages_filter(self):
        ide = _make_ide()
        ide.create_review(plan_id="p1")
        ide.create_review(plan_id="p2")
        pending = ide.review_packages("pending")
        assert len(pending) == 2

    def test_review_detail(self):
        ide = _make_ide()
        review = ide.create_review(plan_id="p1")
        detail = ide.review_detail(review.review_id)
        assert detail is not None
        assert detail.plan_id == "p1"


class TestMergeFlow:
    def test_approve_and_merge(self):
        ide = _make_ide()
        review = ide.create_review(plan_id="p1")
        result = ide.approve_and_merge(review.review_id)
        assert result.success is True
        assert result.commit_sha.startswith("merge-")
        assert result.branch == "plan/p1"

    def test_merge_nonexistent_review(self):
        ide = _make_ide()
        result = ide.approve_and_merge("nonexistent")
        assert result.success is False
        assert "not found" in result.error

    def test_merge_already_merged(self):
        ide = _make_ide()
        review = ide.create_review(plan_id="p1")
        ide.approve_and_merge(review.review_id)
        result = ide.approve_and_merge(review.review_id)
        assert result.success is False

    def test_merge_completes_streams(self):
        ide = _make_ide()
        plan = ide.plan_from_intent("Build X")
        ide.dispatch_plan(plan.plan_id)
        review = ide.create_review(plan_id=plan.plan_id)
        ide.approve_and_merge(review.review_id)
        active = ide.active_development()
        assert len(active) == 0


class TestRejectReview:
    def test_reject(self):
        ide = _make_ide()
        review = ide.create_review(plan_id="p1")
        ok = ide.reject_review(review.review_id, "needs rework")
        assert ok is True
        assert ide._reviews[review.review_id].status == ReviewStatus.REJECTED

    def test_reject_nonexistent(self):
        ide = _make_ide()
        ok = ide.reject_review("nonexistent", "reason")
        assert ok is False


class TestIDEStatus:
    def test_status_snapshot(self):
        ide = _make_ide()
        s = ide.ide_status()
        d = s.to_dict()
        assert "active_agents" in d
        assert "pending_reviews" in d
        assert "total_plans" in d

    def test_status_counts(self):
        ide = _make_ide()
        ide.plan_from_intent("Build X")
        ide.plan_from_intent("Fix Y")
        s = ide.ide_status()
        assert s.total_plans == 2


class TestFullLoop:
    """Acceptance test: inspect → plan → assign → review → merge."""

    def test_full_development_loop(self):
        ide = _make_ide()

        snap = ide.workspace_snapshot()
        assert snap is not None

        plan = ide.plan_from_intent("Add health check endpoint")
        assert plan.plan_id

        dispatches = ide.dispatch_plan(plan.plan_id)
        assert len(dispatches) >= 1

        active = ide.active_development()
        assert len(active) >= 1

        review = ide.create_review(plan_id=plan.plan_id, artifacts=[{"file": "healthcheck.py"}])
        assert review.status == ReviewStatus.PENDING

        result = ide.approve_and_merge(review.review_id)
        assert result.success is True
        assert result.commit_sha

        assert ide.active_development() == []
