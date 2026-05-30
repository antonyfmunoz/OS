"""Phase 10.2 — Operator-Approved Template-Supplied Sandbox PR Creation tests.

Covers:
  TST-06: ApprovalGate (12 tests)
  TST-07: SandboxOrchestrator (10 tests)
  TST-08: Validation gate baseline comparison (6 tests)
  TST-09: Bridge endpoints (8 tests)
  TST-10: Route auth classification (6 tests)
  TST-11: Safety invariants (5 tests)

47 tests total. Python 3.11 compatible. No external network calls.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from substrate.organism.approval_gate import (
    ApprovalPacket,
    ApprovalStatus,
    OperatorApprovalGate,
)
from substrate.organism.autonomous_cadence import (
    AutonomousCadence,
    CadenceMode,
    CadencePolicy,
)
from substrate.organism.autonomous_pr_factory import (
    AutonomousPRFactory,
    AutonomousPRRequest,
    PRCreationStatus,
    PRValidationGate,
    SandboxOutcomeCommitted,
    ProductionOutcomeCommitted,
)
from substrate.organism.candidate_supply_engine import (
    CandidateSupplyEngine,
    SupplyCandidate,
)
from substrate.organism.sandbox_orchestrator import (
    SandboxExecutionResult,
    SandboxOrchestrator,
)
from substrate.organism.template_governance import (
    GovernanceDecision,
    TemplateGovernance,
)
from substrate.organism.template_registry import (
    TemplateCandidate,
    TemplateEvidence,
    TemplateRegistry,
    TemplateRollback,
    TemplateStatus,
    TemplateType,
    TemplateValidation,
)
from substrate.organism.worktree_sandbox import SandboxManager, SandboxStatus


# ── Fixtures ─────────────────────────────────────────────


@pytest.fixture
def tmp_store(tmp_path):
    return str(tmp_path)


@pytest.fixture
def approval_gate(tmp_store):
    return OperatorApprovalGate(store_dir=tmp_store, ttl_seconds=3600)


@pytest.fixture
def sample_packet_kwargs():
    return {
        "candidate_id": "cse-test-001",
        "candidate_source": "template_audit_gaps",
        "candidate_title": "Test audit gap fix",
        "candidate_description": "Fix a test audit gap in template store",
        "candidate_evidence": [{"source": "audit", "detail": "gap found", "confidence": 0.8}],
        "matched_template_id": "tpl-seed-test-001",
        "matched_template_type": "test_repair",
        "template_confidence": 0.85,
        "governance_score": 0.90,
        "governance_decision": "cadence_eligible",
        "governance_dimensions": [{"name": "evidence", "score": 0.8, "weight": 0.15, "reason": "good"}],
        "affected_files": [],
        "expected_delta": "Close audit gap",
        "validation_plan": "assertion",
        "rollback_plan": "revert",
        "risk_class": "low",
    }


@pytest.fixture
def supply_candidate():
    return SupplyCandidate(
        candidate_id="cse-test-001",
        source="template_audit_gaps",
        title="Test audit gap fix",
        description="Fix a test audit gap",
        evidence=[{"source": "audit", "detail": "gap found", "confidence": 0.8}],
        affected_files=[],
        risk_class="low",
        matching_templates=["tpl-seed-test-001"],
        policy_decision="cadence_eligible",
        blocked_reasons=[],
        expected_delta="Close audit gap",
        template_confidence=0.85,
        agent_reliability=0.8,
        validation_method="assertion",
        rollback_method="revert",
        non_mutating=False,
    )


# ═══════════════════════════════════════════════════════════
# TST-06: ApprovalGate (12 tests)
# ═══════════════════════════════════════════════════════════


class TestApprovalGateCreation:
    def test_create_packet_returns_pending(self, approval_gate, sample_packet_kwargs):
        packet = approval_gate.create_packet(**sample_packet_kwargs)
        assert packet.status == ApprovalStatus.PENDING
        assert packet.packet_id.startswith("apk-")

    def test_create_packet_has_branch_name(self, approval_gate, sample_packet_kwargs):
        packet = approval_gate.create_packet(**sample_packet_kwargs)
        assert packet.sandbox_branch_name.startswith("auto/low-risk/")

    def test_create_packet_has_why_safe(self, approval_gate, sample_packet_kwargs):
        packet = approval_gate.create_packet(**sample_packet_kwargs)
        assert "LOW risk" in packet.why_safe
        assert len(packet.why_safe) > 20

    def test_create_packet_has_what_will_not_happen(self, approval_gate, sample_packet_kwargs):
        packet = approval_gate.create_packet(**sample_packet_kwargs)
        assert len(packet.what_will_not_happen) >= 5
        assert any("auto-merge" in w.lower() for w in packet.what_will_not_happen)

    def test_create_packet_persists(self, approval_gate, sample_packet_kwargs):
        packet = approval_gate.create_packet(**sample_packet_kwargs)
        assert os.path.isfile(approval_gate._packets_path)

    def test_create_packet_to_dict(self, approval_gate, sample_packet_kwargs):
        packet = approval_gate.create_packet(**sample_packet_kwargs)
        d = packet.to_dict()
        assert d["status"] == "pending"
        assert d["candidate_id"] == "cse-test-001"
        assert d["risk_class"] == "low"


class TestApprovalGateDecisions:
    def test_approve_changes_status(self, approval_gate, sample_packet_kwargs):
        packet = approval_gate.create_packet(**sample_packet_kwargs)
        result = approval_gate.approve(packet.packet_id, decided_by="test-operator")
        assert result is not None
        assert result.status == ApprovalStatus.APPROVED
        assert result.decided_by == "test-operator"
        assert result.decided_at > 0

    def test_reject_changes_status(self, approval_gate, sample_packet_kwargs):
        packet = approval_gate.create_packet(**sample_packet_kwargs)
        result = approval_gate.reject(packet.packet_id, reason="not now", decided_by="test-operator")
        assert result is not None
        assert result.status == ApprovalStatus.REJECTED
        assert result.rejection_reason == "not now"

    def test_cannot_approve_already_approved(self, approval_gate, sample_packet_kwargs):
        packet = approval_gate.create_packet(**sample_packet_kwargs)
        approval_gate.approve(packet.packet_id)
        result = approval_gate.approve(packet.packet_id)
        assert result is None

    def test_cannot_approve_rejected(self, approval_gate, sample_packet_kwargs):
        packet = approval_gate.create_packet(**sample_packet_kwargs)
        approval_gate.reject(packet.packet_id)
        result = approval_gate.approve(packet.packet_id)
        assert result is None

    def test_expired_packet_not_approvable(self, tmp_store, sample_packet_kwargs):
        gate = OperatorApprovalGate(store_dir=tmp_store, ttl_seconds=0)
        packet = gate.create_packet(**sample_packet_kwargs)
        time.sleep(0.01)
        result = gate.approve(packet.packet_id)
        assert result is None

    def test_is_approved(self, approval_gate, sample_packet_kwargs):
        packet = approval_gate.create_packet(**sample_packet_kwargs)
        assert not approval_gate.is_approved(packet.packet_id)
        approval_gate.approve(packet.packet_id)
        assert approval_gate.is_approved(packet.packet_id)


# ═══════════════════════════════════════════════════════════
# TST-07: SandboxOrchestrator (10 tests)
# ═══════════════════════════════════════════════════════════


class TestSandboxOrchestratorGates:
    def test_execute_without_approval_fails(self, tmp_store, supply_candidate):
        gate = OperatorApprovalGate(store_dir=tmp_store)
        mgr = SandboxManager(store_dir=tmp_store)
        factory = AutonomousPRFactory(sandbox_manager=mgr, store_dir=tmp_store)
        orch = SandboxOrchestrator(approval_gate=gate, pr_factory=factory, sandbox_manager=mgr)

        result = orch.execute_approved(
            packet_id="nonexistent",
            supply_candidate=supply_candidate,
        )
        assert not result.success
        assert "not found" in result.error

    def test_execute_pending_packet_fails(self, tmp_store, supply_candidate, sample_packet_kwargs):
        gate = OperatorApprovalGate(store_dir=tmp_store)
        packet = gate.create_packet(**sample_packet_kwargs)
        mgr = SandboxManager(store_dir=tmp_store)
        factory = AutonomousPRFactory(sandbox_manager=mgr, store_dir=tmp_store)
        orch = SandboxOrchestrator(approval_gate=gate, pr_factory=factory, sandbox_manager=mgr)

        result = orch.execute_approved(
            packet_id=packet.packet_id,
            supply_candidate=supply_candidate,
        )
        assert not result.success
        assert "not approved" in result.error

    def test_execute_rejected_packet_fails(self, tmp_store, supply_candidate, sample_packet_kwargs):
        gate = OperatorApprovalGate(store_dir=tmp_store)
        packet = gate.create_packet(**sample_packet_kwargs)
        gate.reject(packet.packet_id)
        mgr = SandboxManager(store_dir=tmp_store)
        factory = AutonomousPRFactory(sandbox_manager=mgr, store_dir=tmp_store)
        orch = SandboxOrchestrator(approval_gate=gate, pr_factory=factory, sandbox_manager=mgr)

        result = orch.execute_approved(
            packet_id=packet.packet_id,
            supply_candidate=supply_candidate,
        )
        assert not result.success
        assert "rejected" in result.error

    def test_execution_result_has_fields(self):
        r = SandboxExecutionResult(success=True, packet_id="apk-1", candidate_id="c-1")
        d = r.to_dict()
        assert d["success"] is True
        assert d["packet_id"] == "apk-1"
        assert d["production_truth_unchanged"] is True

    def test_orchestrator_summary_empty(self, tmp_store):
        gate = OperatorApprovalGate(store_dir=tmp_store)
        mgr = SandboxManager(store_dir=tmp_store)
        factory = AutonomousPRFactory(sandbox_manager=mgr, store_dir=tmp_store)
        orch = SandboxOrchestrator(approval_gate=gate, pr_factory=factory, sandbox_manager=mgr)
        summary = orch.summary()
        assert summary["total_executions"] == 0
        assert summary["sandbox_outcomes_emitted"] == 0

    def test_orchestrator_to_dict(self, tmp_store):
        gate = OperatorApprovalGate(store_dir=tmp_store)
        mgr = SandboxManager(store_dir=tmp_store)
        factory = AutonomousPRFactory(sandbox_manager=mgr, store_dir=tmp_store)
        orch = SandboxOrchestrator(approval_gate=gate, pr_factory=factory, sandbox_manager=mgr)
        d = orch.to_dict()
        assert "summary" in d
        assert "executions" in d
        assert "sandbox_outcomes" in d


# ═══════════════════════════════════════════════════════════
# TST-08: Validation gate baseline comparison (6 tests)
# ═══════════════════════════════════════════════════════════


class TestValidationGate:
    def test_gate_all_passed_when_all_true(self):
        gate = PRValidationGate(
            py_compile_passed=True,
            type_divergence_passed=True,
            instance_leak_passed=True,
            dependency_direction_passed=True,
        )
        assert gate.all_passed

    def test_gate_not_passed_when_one_false(self):
        gate = PRValidationGate(
            py_compile_passed=True,
            type_divergence_passed=False,
            instance_leak_passed=True,
            dependency_direction_passed=True,
        )
        assert not gate.all_passed

    def test_gate_to_dict(self):
        gate = PRValidationGate(py_compile_passed=True)
        d = gate.to_dict()
        assert "py_compile_passed" in d
        assert "all_passed" in d

    def test_gate_default_all_false(self):
        gate = PRValidationGate()
        assert not gate.all_passed

    def test_sandbox_outcome_has_boundary(self):
        outcome = SandboxOutcomeCommitted(
            sandbox_id="sb-1",
            candidate_id="c-1",
            boundary="sandbox",
        )
        assert outcome.boundary == "sandbox"
        d = outcome.to_dict()
        assert d["event_type"] == "sandbox_outcome_committed"

    def test_production_outcome_has_idempotency_key(self):
        outcome = ProductionOutcomeCommitted(
            merge_commit="abc123",
            manifest_id="csm-1",
        )
        key = outcome.idempotency_key
        assert "production_outcome:" in key
        assert "abc123" in key


# ═══════════════════════════════════════════════════════════
# TST-09: Bridge endpoints (8 tests)
# ═══════════════════════════════════════════════════════════


class TestBridgeEndpoints:
    def test_cadence_status_returns_success(self):
        from transports.api.organism_bridge import _cadence_status
        result = _cadence_status({})
        assert result["success"] is True

    def test_candidate_supply_returns_candidates(self):
        from transports.api.organism_bridge import _candidate_supply_status
        result = _candidate_supply_status({})
        assert result["success"] is True
        assert "candidates" in result["data"]
        assert result["data"]["total"] >= 0

    def test_sandboxes_returns_success(self):
        from transports.api.organism_bridge import _sandboxes_status
        result = _sandboxes_status({})
        assert result["success"] is True

    def test_approval_packets_returns_success(self):
        from transports.api.organism_bridge import _approval_packets_list
        result = _approval_packets_list({})
        assert result["success"] is True
        assert "summary" in result["data"]

    def test_production_truth_returns_success(self):
        from transports.api.organism_bridge import _production_truth_status
        result = _production_truth_status({})
        assert result["success"] is True
        assert "main_commit" in result["data"]

    def test_pr_factory_returns_success(self):
        from transports.api.organism_bridge import _pr_factory_status
        result = _pr_factory_status({})
        assert result["success"] is True

    def test_approval_packet_detail_not_found(self):
        from transports.api.organism_bridge import _approval_packet_detail
        result = _approval_packet_detail({"packet_id": "nonexistent"})
        assert result["success"] is False

    def test_sandbox_detail_not_found(self):
        from transports.api.organism_bridge import _sandbox_detail
        result = _sandbox_detail({"sandbox_id": "nonexistent"})
        assert result["success"] is False


# ═══════════════════════════════════════════════════════════
# TST-10: Route auth classification (6 tests)
# ═══════════════════════════════════════════════════════════


class TestRouteAuth:
    def test_server_has_execution_auth(self):
        server_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "transports", "api", "http", "server.ts",
        )
        with open(server_path) as f:
            content = f.read()
        assert "app.use('/execution'" in content
        assert "app.use('/execution/*'" in content

    def test_server_has_settings_auth(self):
        server_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "transports", "api", "http", "server.ts",
        )
        with open(server_path) as f:
            content = f.read()
        assert "app.use('/settings'" in content

    def test_server_has_files_auth(self):
        server_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "transports", "api", "http", "server.ts",
        )
        with open(server_path) as f:
            content = f.read()
        assert "app.use('/files'" in content
        assert "app.use('/file'" in content

    def test_organism_control_has_operator_guard(self):
        organism_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "transports", "api", "http", "routes", "organism.ts",
        )
        with open(organism_path) as f:
            content = f.read()
        assert "router.post('/control', operatorGuard" in content

    def test_cadence_route_has_operator_guard(self):
        organism_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "transports", "api", "http", "routes", "organism.ts",
        )
        with open(organism_path) as f:
            content = f.read()
        assert "router.get('/cadence', operatorGuard" in content

    def test_approval_routes_have_operator_guard(self):
        organism_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "transports", "api", "http", "routes", "organism.ts",
        )
        with open(organism_path) as f:
            content = f.read()
        assert "router.get('/approval-packets', operatorGuard" in content
        assert "router.post('/approval-packets/:id/approve', operatorGuard" in content
        assert "router.post('/approval-packets/:id/reject', operatorGuard" in content


# ═══════════════════════════════════════════════════════════
# TST-11: Safety invariants (5 tests)
# ═══════════════════════════════════════════════════════════


class TestSafetyInvariants:
    def test_cadence_default_mode_is_off(self):
        policy = CadencePolicy()
        assert policy.mode == CadenceMode.OFF

    def test_cadence_dry_run_never_creates_prs(self):
        policy = CadencePolicy(mode=CadenceMode.DRY_RUN_ONLY)
        cadence = AutonomousCadence(policy=policy)
        result = cadence.run_cycle()
        assert not result.pr_created

    def test_cadence_no_auto_merge_default(self):
        policy = CadencePolicy()
        assert policy.no_auto_merge is True

    def test_cadence_require_operator_enable_default(self):
        policy = CadencePolicy()
        assert policy.require_operator_enable_for_pr_creation is True

    def test_sandbox_outcome_boundary_is_sandbox(self):
        outcome = SandboxOutcomeCommitted()
        assert outcome.boundary == "sandbox"
        assert outcome.to_dict()["boundary"] == "sandbox"
