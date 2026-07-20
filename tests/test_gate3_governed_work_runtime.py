"""Gate 3 — Governed Work Runtime — test suite.

Tests all 8 workcells:
  A. WorkGraph (read-only projection)
  B. GovernedWorkRuntime (mandatory gateway)
  C. ApprovalPolicyRegistry (policies + decisions)
  D. ProofRuntime (before/after/evidence)
  E. WorkRecoveryRuntime (state → recovery actions)
  F. Cockpit Work Center Routes (HTTP surface)
  G. Voice Action Resolution
  H. OperatorLoopRuntime (Jarvis Runtime)
"""

from __future__ import annotations

import os
import sys
import time

# Root the import path at the repo checkout that owns THIS test file (works in
# the main checkout and in any worktree), not a hardcoded /opt/OS. Without this
# a worktree run would import substrate from main and never exercise local edits.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

import pytest


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# A — WorkGraph
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestWorkGraph:
    def test_import(self):
        from substrate.organism.work_graph import (
            BlockerType,
            WorkBlocker,
            WorkGraph,
            WorkGraphNode,
            WorkGraphSnapshot,
            WorkNodeType,
            WorkResult,
        )
        assert WorkNodeType.PACKET == "packet"
        assert BlockerType.APPROVAL == "approval"

    def test_graph_returns_lists(self):
        from substrate.organism.work_graph import WorkGraph
        g = WorkGraph()
        assert isinstance(g.all_work(), list)
        assert isinstance(g.active_work(), list)
        assert isinstance(g.blocked_work(), list)
        assert isinstance(g.executable_work(), list)
        assert isinstance(g.completed_work(), list)
        assert isinstance(g.failed_work(), list)

    def test_snapshot_structure(self):
        from substrate.organism.work_graph import WorkGraph
        g = WorkGraph()
        snap = g.snapshot()
        assert hasattr(snap, "total")
        assert hasattr(snap, "active")
        assert hasattr(snap, "blocked")
        assert hasattr(snap, "completed")
        assert hasattr(snap, "failed")
        assert isinstance(snap.nodes, list)
        assert snap.total == len(snap.nodes)

    def test_snapshot_to_dict(self):
        from substrate.organism.work_graph import WorkGraph
        g = WorkGraph()
        d = g.snapshot().to_dict()
        assert "total" in d
        assert "nodes" in d
        assert isinstance(d["total"], int)

    def test_node_not_found(self):
        from substrate.organism.work_graph import WorkGraph
        g = WorkGraph()
        assert g.node("nonexistent") is None

    def test_dependencies_of_missing(self):
        from substrate.organism.work_graph import WorkGraph
        g = WorkGraph()
        assert g.dependencies_of("x") == []

    def test_dependents_of_missing(self):
        from substrate.organism.work_graph import WorkGraph
        g = WorkGraph()
        assert g.dependents_of("x") == []

    def test_blockers_for_missing(self):
        from substrate.organism.work_graph import WorkGraph
        g = WorkGraph()
        assert g.blockers_for("x") == []

    def test_work_by_status_empty(self):
        from substrate.organism.work_graph import WorkGraph
        g = WorkGraph()
        assert g.work_by_status("active") == []

    def test_work_node_type_values(self):
        from substrate.organism.work_graph import WorkNodeType
        assert WorkNodeType.PLAN == "plan"
        assert WorkNodeType.REQUEST == "request"

    def test_blocker_type_values(self):
        from substrate.organism.work_graph import BlockerType
        assert BlockerType.DEPENDENCY == "dependency"
        assert BlockerType.RESOURCE == "resource"
        assert BlockerType.FAILURE == "failure"

    def test_work_blocker_to_dict(self):
        from substrate.organism.work_graph import BlockerType, WorkBlocker
        b = WorkBlocker(
            blocker_type=BlockerType.APPROVAL,
            description="Needs operator approval",
        )
        d = b.to_dict()
        assert d["blocker_type"] == "approval"
        assert d["description"] == "Needs operator approval"

    def test_work_result_to_dict(self):
        from substrate.organism.work_graph import WorkResult
        r = WorkResult(outcome="success", proof_id="p-123")
        d = r.to_dict()
        assert d["outcome"] == "success"
        assert d["proof_id"] == "p-123"

    def test_work_graph_node_to_dict(self):
        from substrate.organism.work_graph import WorkGraphNode, WorkNodeType
        n = WorkGraphNode(
            node_id="wp-abc",
            node_type=WorkNodeType.PACKET,
            status="active",
            risk_class="low",
            description="Test packet",
        )
        d = n.to_dict()
        assert d["node_id"] == "wp-abc"
        assert d["node_type"] == "packet"
        assert d["status"] == "active"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# C — Approval Runtime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestApprovalRuntime:
    def test_import(self):
        from substrate.organism.executors.approval_intercept import (
            ApprovalDecision,
            ApprovalPolicy,
            ApprovalPolicyRegistry,
            ApprovalScope,
        )
        assert ApprovalScope.PLAN == "plan"
        assert ApprovalScope.EXECUTION == "execution"
        assert ApprovalScope.ACTION == "action"

    def test_default_policies(self):
        from substrate.organism.executors.approval_intercept import (
            ApprovalPolicyRegistry,
        )
        reg = ApprovalPolicyRegistry()
        policies = reg.all_policies()
        assert len(policies) >= 3

    def test_evaluate_low_plan(self):
        from substrate.organism.executors.approval_intercept import (
            ApprovalPolicyRegistry,
            ApprovalScope,
        )
        reg = ApprovalPolicyRegistry()
        requires, policy_id = reg.evaluate("low", ApprovalScope.PLAN)
        assert isinstance(requires, bool)
        assert isinstance(policy_id, str)

    def test_evaluate_high_execution(self):
        from substrate.organism.executors.approval_intercept import (
            ApprovalPolicyRegistry,
            ApprovalScope,
        )
        reg = ApprovalPolicyRegistry()
        requires, policy_id = reg.evaluate("high", ApprovalScope.EXECUTION)
        assert requires is True

    def test_evaluate_critical_always_requires(self):
        from substrate.organism.executors.approval_intercept import (
            ApprovalPolicyRegistry,
            ApprovalScope,
        )
        reg = ApprovalPolicyRegistry()
        requires, _ = reg.evaluate("critical", ApprovalScope.PLAN)
        assert requires is True

    def test_for_scope(self):
        from substrate.organism.executors.approval_intercept import (
            ApprovalPolicyRegistry,
            ApprovalScope,
        )
        reg = ApprovalPolicyRegistry()
        policy = reg.for_scope(ApprovalScope.PLAN)
        assert policy is not None

    def test_approval_policy_requires_approval(self):
        from substrate.organism.executors.approval_intercept import (
            ApprovalPolicy,
            ApprovalScope,
        )
        p = ApprovalPolicy(
            policy_id="test",
            name="test",
            risk_threshold="medium",
            auto_approve_below="medium",
            scope=ApprovalScope.PLAN,
        )
        assert p.requires_approval("high") is True
        assert p.requires_approval("low") is False

    def test_approval_decision_to_dict(self):
        from substrate.organism.executors.approval_intercept import ApprovalDecision
        d = ApprovalDecision(
            work_id="wp-1",
            status="approved",
            decided_by="operator",
        )
        result = d.to_dict()
        assert result["work_id"] == "wp-1"
        assert result["status"] == "approved"

    def test_register_custom_policy(self):
        from substrate.organism.executors.approval_intercept import (
            ApprovalPolicy,
            ApprovalPolicyRegistry,
            ApprovalScope,
        )
        reg = ApprovalPolicyRegistry()
        custom = ApprovalPolicy(
            policy_id="custom-test",
            name="Custom",
            risk_threshold="critical",
            auto_approve_below="high",
            scope=ApprovalScope.EXECUTION,
        )
        reg.register(custom)
        assert reg.get("custom-test") is not None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# D — ProofRuntime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestProofRuntime:
    def test_import(self):
        from substrate.organism.proof_runtime import (
            ProofEvidence,
            ProofPackage,
            ProofRuntime,
        )
        assert ProofRuntime._MAX_HISTORY == 200

    def test_capture_before(self):
        from substrate.organism.proof_runtime import ProofRuntime
        rt = ProofRuntime()
        snap_id = rt.capture_before("wp-1", state={"version": 1})
        assert snap_id.startswith("snap-")
        assert snap_id in rt._pending

    def test_capture_after(self):
        from substrate.organism.proof_runtime import ProofRuntime
        rt = ProofRuntime()
        snap_id = rt.capture_before("wp-1", state={"version": 1})
        pkg = rt.capture_after(
            work_id="wp-1",
            snapshot_id=snap_id,
            action={"op": "deploy"},
            outcome="success",
            after_state={"version": 2},
        )
        assert pkg.proof_id.startswith("proof-")
        assert pkg.work_id == "wp-1"
        assert pkg.before_state == {"version": 1}
        assert pkg.after_state == {"version": 2}
        assert pkg.outcome == "success"

    def test_proof_evidence_in_package(self):
        from substrate.organism.proof_runtime import ProofRuntime
        rt = ProofRuntime()
        snap_id = rt.capture_before("wp-2", state={"a": 1})
        pkg = rt.capture_after(
            work_id="wp-2",
            snapshot_id=snap_id,
            after_state={"a": 2, "b": 3},
        )
        assert len(pkg.evidence) == 1
        assert pkg.evidence[0].evidence_type == "state_diff"
        diff = pkg.evidence[0].data
        assert "a" in diff

    def test_package_for(self):
        from substrate.organism.proof_runtime import ProofRuntime
        rt = ProofRuntime()
        snap = rt.capture_before("wp-3", state={})
        rt.capture_after(work_id="wp-3", snapshot_id=snap, after_state={})
        pkg = rt.package_for("wp-3")
        assert pkg is not None
        assert pkg.work_id == "wp-3"

    def test_create_direct(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
        from substrate.organism.proof_runtime import ProofRuntime
        rt = ProofRuntime()
        pkg = rt.create_direct("wp-4", action={"op": "test"}, outcome="ok")
        assert pkg.work_id == "wp-4"
        assert len(rt.all_proofs()) == 1

    def test_recent(self):
        from substrate.organism.proof_runtime import ProofRuntime
        rt = ProofRuntime()
        for i in range(5):
            rt.create_direct(f"wp-{i}", action={"i": i})
        recent = rt.recent(3)
        assert len(recent) == 3

    def test_get_by_id(self):
        from substrate.organism.proof_runtime import ProofRuntime
        rt = ProofRuntime()
        pkg = rt.create_direct("wp-5", action={})
        assert rt.get(pkg.proof_id) is not None
        assert rt.get("nonexistent") is None

    def test_to_dict(self):
        from substrate.organism.proof_runtime import ProofRuntime
        rt = ProofRuntime()
        pkg = rt.create_direct("wp-6", action={"x": 1})
        d = pkg.to_dict()
        assert d["work_id"] == "wp-6"
        assert "evidence" in d
        assert "timestamp" in d

    def test_compute_diff(self):
        from substrate.organism.proof_runtime import ProofRuntime
        diff = ProofRuntime._compute_diff(
            {"a": 1, "b": 2},
            {"a": 1, "b": 3, "c": 4},
        )
        assert "b" in diff
        assert "c" in diff
        assert "a" not in diff

    def test_capture_after_missing_snapshot(self):
        from substrate.organism.proof_runtime import ProofRuntime
        rt = ProofRuntime()
        pkg = rt.capture_after(
            work_id="wp-orphan",
            snapshot_id="snap-nonexistent",
            after_state={"done": True},
        )
        assert pkg.before_state == {}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# E — WorkRecoveryRuntime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestWorkRecoveryRuntime:
    def test_import(self):
        from substrate.organism.work_recovery_runtime import (
            RecoveryAction,
            RecoveryActionType,
            RecoveryAssessment,
            RecoveryState,
            WorkRecoveryRuntime,
        )
        assert RecoveryState.FAILED == "failed"
        assert RecoveryActionType.RETRY == "retry"

    def test_assess_unknown_id(self):
        from substrate.organism.work_recovery_runtime import (
            RecoveryState,
            WorkRecoveryRuntime,
        )
        rt = WorkRecoveryRuntime()
        assessment = rt.assess("wp-nonexistent999")
        assert assessment.state in (RecoveryState.ACTIVE, RecoveryState.COMPLETE)

    def test_recovery_actions_no_graph(self):
        from substrate.organism.work_recovery_runtime import WorkRecoveryRuntime
        rt = WorkRecoveryRuntime()
        assert rt.recovery_actions("wp-1") == []

    def test_interrupted_work_empty(self):
        from substrate.organism.work_recovery_runtime import WorkRecoveryRuntime
        rt = WorkRecoveryRuntime()
        assert rt.interrupted_work() == []

    def test_resumable_work_empty(self):
        from substrate.organism.work_recovery_runtime import WorkRecoveryRuntime
        rt = WorkRecoveryRuntime()
        assert rt.resumable_work() == []

    def test_failed_work_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
        from substrate.organism.work_recovery_runtime import WorkRecoveryRuntime
        rt = WorkRecoveryRuntime()
        assert rt.failed_work() == []

    def test_blocked_work_empty(self, tmp_path, monkeypatch):
        """Empty-state assertion needs an ISOLATED state root — without one it
        reads whatever the live runtime happens to hold (Wave 0: state lives
        under the runtime-state boundary, so point it at a temp dir)."""
        monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
        from substrate.organism.work_recovery_runtime import WorkRecoveryRuntime
        rt = WorkRecoveryRuntime()
        assert rt.blocked_work() == []

    def test_recoverable_work_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
        from substrate.organism.work_recovery_runtime import WorkRecoveryRuntime
        rt = WorkRecoveryRuntime()
        assert rt.recoverable_work() == []

    def test_recovery_state_classification(self):
        from substrate.organism.work_recovery_runtime import (
            RecoveryState,
            _classify_recovery_state,
        )
        assert _classify_recovery_state("failed") == RecoveryState.FAILED
        assert _classify_recovery_state("blocked") == RecoveryState.BLOCKED
        assert _classify_recovery_state("paused") == RecoveryState.INTERRUPTED
        assert _classify_recovery_state("completed") == RecoveryState.COMPLETE
        assert _classify_recovery_state("active") == RecoveryState.ACTIVE

    def test_recovery_action_to_dict(self):
        from substrate.organism.work_recovery_runtime import (
            RecoveryAction,
            RecoveryActionType,
        )
        a = RecoveryAction(
            action=RecoveryActionType.RETRY,
            work_id="wp-1",
            reason="test",
            auto_recoverable=True,
        )
        d = a.to_dict()
        assert d["action"] == "retry"
        assert d["auto_recoverable"] is True

    def test_recovery_assessment_to_dict(self):
        from substrate.organism.work_recovery_runtime import (
            RecoveryAssessment,
            RecoveryState,
        )
        a = RecoveryAssessment(work_id="wp-1", state=RecoveryState.FAILED)
        d = a.to_dict()
        assert d["state"] == "failed"
        assert d["work_id"] == "wp-1"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# B — GovernedWorkRuntime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestGovernedWorkRuntime:
    def test_import(self):
        from substrate.organism.governed_work_runtime import (
            ExecutionReceipt,
            GovernedWorkRuntime,
            WorkStatus,
            WorkSubmission,
        )
        assert GovernedWorkRuntime is not None

    def test_submit_work(self):
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        rt = GovernedWorkRuntime()
        sub = rt.submit_work("deploy latest changes")
        assert sub.work_id.startswith("wp-")
        assert sub.status in ("approval_pending", "queued")
        assert not sub.error

    def test_submit_empty_intent(self):
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        rt = GovernedWorkRuntime()
        sub = rt.submit_work("")
        assert sub.error == "Empty intent"

    def test_submit_whitespace_intent(self):
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        rt = GovernedWorkRuntime()
        sub = rt.submit_work("   ")
        assert sub.error == "Empty intent"

    def test_work_submission_to_dict(self):
        from substrate.organism.governed_work_runtime import WorkSubmission
        s = WorkSubmission(work_id="wp-1", status="queued")
        d = s.to_dict()
        assert d["work_id"] == "wp-1"
        assert "created_at" in d

    def test_execution_receipt_to_dict(self):
        from substrate.organism.governed_work_runtime import ExecutionReceipt
        r = ExecutionReceipt(work_id="wp-1", status="dispatched")
        d = r.to_dict()
        assert d["status"] == "dispatched"

    def test_work_status_to_dict(self):
        from substrate.organism.governed_work_runtime import WorkStatus
        s = WorkStatus(work_id="wp-1", phase="drafted")
        d = s.to_dict()
        assert d["phase"] == "drafted"

    def test_status_unknown_work(self):
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        rt = GovernedWorkRuntime()
        status = rt.status("nonexistent")
        assert status.phase == "unknown"

    def test_queue_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        rt = GovernedWorkRuntime()
        assert rt.queue() == []

    def test_blocked_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        rt = GovernedWorkRuntime()
        assert rt.blocked() == []

    def test_active_returns_list(self):
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        rt = GovernedWorkRuntime()
        result = rt.active()
        assert isinstance(result, list)

    def test_proof_not_found(self):
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        rt = GovernedWorkRuntime()
        assert rt.proof("nonexistent") is None

    def test_history_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        rt = GovernedWorkRuntime()
        assert rt.history() == []

    def test_recovery_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        rt = GovernedWorkRuntime()
        assert rt.recovery() == []

    def test_graph_snapshot_structure(self):
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        rt = GovernedWorkRuntime()
        snap = rt.graph_snapshot()
        assert "total" in snap
        assert isinstance(snap["total"], int)

    def test_cancel_missing(self):
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        rt = GovernedWorkRuntime()
        assert rt.cancel_work("nonexistent") is False

    def test_retry_creates_new_submission(self):
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        rt = GovernedWorkRuntime()
        sub = rt.retry_work("wp-old")
        assert sub.work_id.startswith("wp-")
        assert not sub.error

    def test_execute_missing(self):
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        rt = GovernedWorkRuntime()
        receipt = rt.execute_work("nonexistent")
        assert receipt.status == "error"
        assert "No plan" in receipt.error

    def test_approve_missing(self):
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        rt = GovernedWorkRuntime()
        result = rt.approve_work("nonexistent")
        assert result["status"] == "error"

    def test_reject_missing(self):
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        rt = GovernedWorkRuntime()
        result = rt.reject_work("nonexistent", reason="test")
        assert result["status"] == "error"

    def test_lazy_subsystem_init(self):
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        rt = GovernedWorkRuntime()
        assert rt.work_graph is not None
        assert rt.proof_runtime is not None
        assert rt.recovery_runtime is not None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# G — Voice Action Resolution
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestVoiceActionResolution:
    def test_import(self):
        from substrate.operator.voice_query_engine import (
            ActionResolution,
            VoiceQueryEngine,
        )
        assert ActionResolution is not None

    def test_resolve_submit(self):
        from substrate.operator.voice_query_engine import VoiceQueryEngine
        engine = VoiceQueryEngine()
        result = engine.resolve_action("create work packet for deployment")
        assert result is not None
        assert result.action_type == "submit"

    def test_resolve_approve(self):
        from substrate.operator.voice_query_engine import VoiceQueryEngine
        engine = VoiceQueryEngine()
        result = engine.resolve_action("approve wp-abcdef123456")
        assert result is not None
        assert result.action_type == "approve"
        assert result.target_id == "wp-abcdef123456"

    def test_resolve_reject(self):
        from substrate.operator.voice_query_engine import VoiceQueryEngine
        engine = VoiceQueryEngine()
        result = engine.resolve_action("reject wp-abcdef123456")
        assert result is not None
        assert result.action_type == "reject"

    def test_resolve_execute(self):
        from substrate.operator.voice_query_engine import VoiceQueryEngine
        engine = VoiceQueryEngine()
        result = engine.resolve_action("execute wp-abcdef123456")
        assert result is not None
        assert result.action_type == "execute"

    def test_resolve_cancel(self):
        from substrate.operator.voice_query_engine import VoiceQueryEngine
        engine = VoiceQueryEngine()
        result = engine.resolve_action("cancel wp-abcdef123456")
        assert result is not None
        assert result.action_type == "cancel"

    def test_resolve_retry(self):
        from substrate.operator.voice_query_engine import VoiceQueryEngine
        engine = VoiceQueryEngine()
        result = engine.resolve_action("retry wp-abcdef123456")
        assert result is not None
        assert result.action_type == "retry"

    def test_resolve_resume(self):
        from substrate.operator.voice_query_engine import VoiceQueryEngine
        engine = VoiceQueryEngine()
        result = engine.resolve_action("resume wp-abcdef123456")
        assert result is not None
        assert result.action_type == "resume"

    def test_resolve_unrecognized_defaults_submit(self):
        from substrate.operator.voice_query_engine import VoiceQueryEngine
        engine = VoiceQueryEngine()
        result = engine.resolve_action("what is the weather like")
        assert result.action_type == "submit"

    def test_action_resolution_fields(self):
        from substrate.operator.voice_query_engine import ActionResolution
        ar = ActionResolution(
            action_type="submit",
            target_id=None,
            parameters={"intent": "test"},
            requires_approval=True,
            confirmation_text="Submit work: test",
            source_text="submit test",
        )
        assert ar.action_type == "submit"
        assert ar.requires_approval is True

    def test_resolve_submit_with_intent(self):
        from substrate.operator.voice_query_engine import VoiceQueryEngine
        engine = VoiceQueryEngine()
        result = engine.resolve_action("submit work packet for database migration")
        assert result is not None
        assert result.action_type == "submit"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# F — Cockpit Work Center Routes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCockpitWorkCenterRoutes:
    def test_import(self):
        from transports.api.cockpit_work_center_routes import (
            configure,
            work_center_router,
        )
        assert work_center_router is not None

    def test_router_has_routes_via_cockpit(self):
        from transports.api.cockpit import router
        paths = [
            r.path for r in router.routes
            if hasattr(r, "path") and "/work/" in r.path
        ]
        assert len(paths) >= 16

    def test_work_routes_present_via_cockpit(self):
        from transports.api.cockpit import router
        paths = {
            r.path for r in router.routes
            if hasattr(r, "path")
        }
        expected_suffixes = [
            "/work/queue", "/work/blocked", "/work/active",
            "/work/approvals", "/work/proof", "/work/history",
            "/work/recovery", "/work/graph", "/work/submit",
        ]
        for suffix in expected_suffixes:
            found = any(p.endswith(suffix) for p in paths)
            assert found, f"Route ending in {suffix} not found"

    def test_mutation_routes_present(self):
        from transports.api.cockpit import router
        paths = {
            r.path for r in router.routes
            if hasattr(r, "path")
        }
        mutation_suffixes = [
            "/work/approve/{work_id}", "/work/reject/{work_id}",
            "/work/execute/{work_id}", "/work/cancel/{work_id}",
            "/work/retry/{work_id}",
        ]
        for suffix in mutation_suffixes:
            found = any(p.endswith(suffix) for p in paths)
            assert found, f"Route ending in {suffix} not found"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# H — OperatorLoopRuntime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestOperatorLoopRuntime:
    def test_import(self):
        from substrate.organism.operator_loop_runtime import (
            OperatorLoopPhase,
            OperatorLoopRuntime,
            OperatorLoopState,
        )
        assert OperatorLoopPhase.OBSERVE == "observe"
        assert OperatorLoopPhase.EXECUTE == "execute"
        assert OperatorLoopPhase.VERIFY == "verify"

    def test_observe(self):
        from substrate.organism.operator_loop_runtime import OperatorLoopRuntime
        rt = OperatorLoopRuntime()
        state = rt.observe()
        assert state.phase.value == "observe"
        assert "observe" in state.available_actions
        assert "decide" in state.available_actions

    def test_understand(self):
        from substrate.organism.operator_loop_runtime import OperatorLoopRuntime
        rt = OperatorLoopRuntime()
        result = rt.understand("what services are running")
        assert isinstance(result, dict)
        assert "query" in result or "result" in result or "domain" in result

    def test_decide(self):
        from substrate.organism.operator_loop_runtime import OperatorLoopRuntime
        rt = OperatorLoopRuntime()
        result = rt.decide("deploy latest changes to staging")
        assert isinstance(result, dict)
        assert "work_id" in result
        assert result.get("work_id", "").startswith("wp-") or "error" not in result

    def test_decide_empty_intent(self):
        from substrate.organism.operator_loop_runtime import OperatorLoopRuntime
        rt = OperatorLoopRuntime()
        result = rt.decide("")
        assert result.get("error") == "Empty intent"

    def test_approve_missing(self):
        from substrate.organism.operator_loop_runtime import OperatorLoopRuntime
        rt = OperatorLoopRuntime()
        result = rt.approve("nonexistent")
        assert result.get("status") == "error"

    def test_reject_missing(self):
        from substrate.organism.operator_loop_runtime import OperatorLoopRuntime
        rt = OperatorLoopRuntime()
        result = rt.reject("nonexistent", reason="test")
        assert result.get("status") == "error"

    def test_execute_missing(self):
        from substrate.organism.operator_loop_runtime import OperatorLoopRuntime
        rt = OperatorLoopRuntime()
        result = rt.execute("nonexistent")
        assert result.get("status") == "error"

    def test_verify_missing(self):
        from substrate.organism.operator_loop_runtime import OperatorLoopRuntime
        rt = OperatorLoopRuntime()
        result = rt.verify("nonexistent")
        assert result.get("proof") is None or result.get("message")

    def test_continue_loop(self):
        from substrate.organism.operator_loop_runtime import OperatorLoopRuntime
        rt = OperatorLoopRuntime()
        state = rt.continue_loop()
        assert state.phase.value == "continue"

    def test_current_state(self):
        from substrate.organism.operator_loop_runtime import OperatorLoopRuntime
        rt = OperatorLoopRuntime()
        state = rt.current_state()
        assert state.phase.value == "observe"

    def test_state_to_dict(self):
        from substrate.organism.operator_loop_runtime import (
            OperatorLoopPhase,
            OperatorLoopState,
        )
        s = OperatorLoopState(
            phase=OperatorLoopPhase.EXECUTE,
            available_actions=["verify"],
            pending_approvals=3,
        )
        d = s.to_dict()
        assert d["phase"] == "execute"
        assert d["pending_approvals"] == 3

    def test_all_phases(self):
        from substrate.organism.operator_loop_runtime import OperatorLoopPhase
        phases = [p.value for p in OperatorLoopPhase]
        assert "observe" in phases
        assert "understand" in phases
        assert "decide" in phases
        assert "approve" in phases
        assert "execute" in phases
        assert "verify" in phases
        assert "continue" in phases

    def test_available_actions_with_approvals(self):
        from substrate.organism.operator_loop_runtime import OperatorLoopRuntime
        actions = OperatorLoopRuntime._compute_available_actions(
            pending_approvals=2,
            recovery_available=0,
            work_in_flight=[{"id": "wp-1"}],
        )
        assert "approve" in actions
        assert "execute" in actions
        assert "verify" in actions

    def test_available_actions_with_recovery(self):
        from substrate.organism.operator_loop_runtime import OperatorLoopRuntime
        actions = OperatorLoopRuntime._compute_available_actions(
            pending_approvals=0,
            recovery_available=3,
            work_in_flight=[],
        )
        assert "continue" in actions
        assert "approve" not in actions

    def test_available_actions_minimal(self):
        from substrate.organism.operator_loop_runtime import OperatorLoopRuntime
        actions = OperatorLoopRuntime._compute_available_actions(
            pending_approvals=0,
            recovery_available=0,
            work_in_flight=[],
        )
        assert actions == ["observe", "understand", "decide"]

    def test_lazy_subsystem_init(self):
        from substrate.organism.operator_loop_runtime import OperatorLoopRuntime
        rt = OperatorLoopRuntime()
        assert rt.work_runtime is not None
        assert rt.proof_runtime is not None
        assert rt.recovery_runtime is not None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Integration — Full Loop
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFullLoop:
    def test_observe_decide_verify_loop(self):
        """End-to-end: observe → decide → verify cycle."""
        from substrate.organism.operator_loop_runtime import OperatorLoopRuntime
        rt = OperatorLoopRuntime()

        state = rt.observe()
        assert state.phase.value == "observe"

        decision = rt.decide("run automated tests")
        assert decision.get("work_id", "").startswith("wp-") or "error" not in decision

        verify = rt.verify(decision.get("work_id", "unknown"))
        assert isinstance(verify, dict)

    def test_governed_runtime_is_only_execution_path(self):
        """Verify GovernedWorkRuntime is the mandatory gateway."""
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        from substrate.organism.operator_loop_runtime import OperatorLoopRuntime

        loop = OperatorLoopRuntime()
        assert isinstance(loop.work_runtime, GovernedWorkRuntime)

    def test_work_graph_is_projection(self):
        """WorkGraph owns nothing — reads from source stores."""
        from substrate.organism.work_graph import WorkGraph
        g = WorkGraph()
        assert not hasattr(g, "_store")
        assert not hasattr(g, "_persist")
        assert not hasattr(g, "save")
        snap1 = g.snapshot()
        snap2 = g.snapshot()
        assert snap1.total == snap2.total

    def test_canonical_type_registrations(self):
        """All Gate 3 types are registered in canonical_types.py."""
        from substrate.canonical_types import lookup
        gate3_types = [
            "WorkGraph", "WorkGraphNode", "WorkGraphSnapshot",
            "GovernedWorkRuntime", "WorkSubmission", "ExecutionReceipt", "WorkStatus",
            "ApprovalScope", "ApprovalPolicy", "ApprovalDecision", "ApprovalPolicyRegistry",
            "ProofRuntime", "ProofPackage", "ProofEvidence",
            "WorkRecoveryRuntime", "RecoveryState", "RecoveryAction",
            "OperatorLoopRuntime", "OperatorLoopPhase", "OperatorLoopState",
            "ActionResolution",
        ]
        for name in gate3_types:
            result = lookup(name)
            assert result is not None, f"{name} not registered in canonical_types.py"

    def test_all_workcells_import(self):
        """Smoke test — every Gate 3 module imports cleanly."""
        from substrate.organism.work_graph import WorkGraph
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        from substrate.organism.proof_runtime import ProofRuntime
        from substrate.organism.work_recovery_runtime import WorkRecoveryRuntime
        from substrate.organism.operator_loop_runtime import OperatorLoopRuntime
        from substrate.organism.executors.approval_intercept import ApprovalPolicyRegistry
        from substrate.operator.voice_query_engine import ActionResolution
        from transports.api.cockpit_work_center_routes import work_center_router
        assert all([
            WorkGraph, GovernedWorkRuntime, ProofRuntime,
            WorkRecoveryRuntime, OperatorLoopRuntime,
            ApprovalPolicyRegistry, ActionResolution, work_center_router,
        ])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WP-P0-007 — Broken governed path regressions (GAP-C1-001)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSubmitWorkRoundTrip:
    """submit_work must create a REAL WorkPacket via the engine.

    Regression guard for GAP-C1-001: submit_work previously called a
    non-existent WorkPacketEngine.create_from_intent and swallowed the
    AttributeError, so it silently returned a raw-uuid packet id and never
    applied classifier-derived risk. These tests exercise the full
    intent → packet → plan path with isolated stores (no shared Neon/network).
    """

    def _isolated_runtime(self, tmp_path):
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        from substrate.organism.work_packet_engine import WorkPacketEngine
        from substrate.organism.execution_coordinator import ExecutionCoordinator

        engine = WorkPacketEngine(
            packets_path=str(tmp_path / "work_packets.jsonl"),
            workcells_path=str(tmp_path / "workcells.jsonl"),
            knowledge_path=str(tmp_path / "knowledge.jsonl"),
        )
        coordinator = ExecutionCoordinator(data_dir=str(tmp_path / "coord"))
        return GovernedWorkRuntime(
            packet_engine=engine,
            execution_coordinator=coordinator,
        ), engine

    def test_submit_creates_real_packet(self, tmp_path):
        rt, engine = self._isolated_runtime(tmp_path)
        sub = rt.submit_work("deploy latest changes to production")

        assert not sub.error, f"unexpected error: {sub.error}"
        assert sub.work_id.startswith("wp-")

        # The returned work_id must correspond to a packet the engine actually
        # created and persisted — not a raw uuid produced by a swallowed error.
        packet = engine.get_packet(sub.work_id)
        assert packet is not None, "submit_work did not create a real engine packet"
        assert packet.packet_id == sub.work_id
        assert packet.user_intent == "deploy latest changes to production"

    def test_submit_applies_classifier_risk(self, tmp_path):
        rt, engine = self._isolated_runtime(tmp_path)
        # A deployment-to-production intent classifies above "low"; submit_work
        # must adopt the classifier-derived risk instead of the default "low".
        sub = rt.submit_work("delete the production database and drop all tables")

        assert not sub.error
        packet = engine.get_packet(sub.work_id)
        assert packet is not None
        # risk_class on the submission must match the packet the engine classified
        assert sub.risk_class == packet.risk_class

    def test_submit_produces_execution_plan(self, tmp_path):
        rt, engine = self._isolated_runtime(tmp_path)
        sub = rt.submit_work("run the automated test suite")

        assert not sub.error
        assert sub.work_id.startswith("wp-")
        # A real packet feeds the coordinator, yielding a plan and a governed
        # status (never the silent-failure empty submission).
        assert sub.status in ("approval_pending", "queued")

    def test_submit_missing_engine_returns_typed_error(self):
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime

        class _NoEngine(GovernedWorkRuntime):
            @property
            def packet_engine(self):
                return None

        rt = _NoEngine()
        sub = rt.submit_work("do something")
        # Fails loud with a typed error instead of silently fabricating a packet.
        assert sub.error
        assert "WorkPacketEngine unavailable" in sub.error


class TestCommandApprovalRoundTrip:
    """CommandRouter approve/reject must call the real queue method.

    Regression guard for GAP-C1-001: _process_approval previously called a
    non-existent UniversalWorkQueue.update_status and swallowed the
    AttributeError, so every operator approve/reject returned an error dict.
    """

    def _seed_queue(self, tmp_path, status):
        """Persist a single packet at ``status`` and return a queue bound to it."""
        from substrate.organism.universal_work_queue import UniversalWorkQueue
        from substrate.organism.work_packet import WorkPacket, persist_packets

        store = str(tmp_path / "work_packets.jsonl")
        pkt = WorkPacket(
            title="approval target",
            user_intent="ship the release",
            status=status,
        )
        persist_packets([pkt], store)
        return UniversalWorkQueue(store_path=store), pkt.packet_id

    def _run_process_approval(self, monkeypatch, queue, packet_id, approved):
        """Invoke the real _process_approval, routing the queue to our store."""
        import substrate.organism.command_runtime as cr

        # _process_approval constructs UniversalWorkQueue() with no args; bind it
        # to our seeded, isolated store so the corrected call site is exercised
        # end-to-end without touching the canonical on-disk queue.
        monkeypatch.setattr(
            cr, "UniversalWorkQueue", lambda *a, **k: queue, raising=False
        )
        # command_runtime imports UniversalWorkQueue lazily inside the method, so
        # patch it at its source module too.
        import substrate.organism.universal_work_queue as uwq
        monkeypatch.setattr(uwq, "UniversalWorkQueue", lambda *a, **k: queue)

        router = cr.CommandRouter()
        return router._process_approval(packet_id, approved=approved)

    def test_approve_returns_success(self, monkeypatch, tmp_path):
        from substrate.organism.work_packet import PacketLifecycleStatus

        queue, packet_id = self._seed_queue(
            tmp_path, PacketLifecycleStatus.APPROVAL_PENDING
        )
        result = self._run_process_approval(
            monkeypatch, queue, packet_id, approved=True
        )
        assert result.get("processed") is True, f"got error dict: {result}"
        assert result.get("new_status") == "approved"
        assert "error" not in result

    def test_reject_returns_success(self, monkeypatch, tmp_path):
        from substrate.organism.work_packet import PacketLifecycleStatus

        queue, packet_id = self._seed_queue(
            tmp_path, PacketLifecycleStatus.APPROVAL_PENDING
        )
        result = self._run_process_approval(
            monkeypatch, queue, packet_id, approved=False
        )
        assert result.get("processed") is True, f"got error dict: {result}"
        assert result.get("new_status") == "rejected"
        assert "error" not in result

    def test_missing_packet_returns_error(self, monkeypatch, tmp_path):
        from substrate.organism.work_packet import PacketLifecycleStatus

        queue, _ = self._seed_queue(
            tmp_path, PacketLifecycleStatus.APPROVAL_PENDING
        )
        result = self._run_process_approval(
            monkeypatch, queue, "wp-doesnotexist", approved=True
        )
        assert "error" in result
        assert "not found" in result["error"]

    def test_invalid_transition_surfaces_typed_error(self, monkeypatch, tmp_path):
        """A packet not awaiting approval must yield a typed error, not a false success.

        This is the swallow-fix: update_packet_status returns False on an invalid
        lifecycle transition; _process_approval must report that, not claim success.
        """
        from substrate.organism.work_packet import PacketLifecycleStatus

        # CLASSIFIED cannot transition directly to APPROVED.
        queue, packet_id = self._seed_queue(
            tmp_path, PacketLifecycleStatus.CLASSIFIED
        )
        result = self._run_process_approval(
            monkeypatch, queue, packet_id, approved=True
        )
        assert result.get("processed") is not True
        assert "error" in result
        assert "invalid lifecycle transition" in result["error"]
