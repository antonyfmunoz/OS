"""Operator Loop MVP — end-to-end integration test.

Tests the full lifecycle:
  submit intent → create packet → approve → execute → verify → complete → record outcome

Section 8 of the spec: "Real Self-Build Test"
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def _isolate_data(tmp_path, monkeypatch):
    """Route all data writes to a temp directory."""
    monkeypatch.setenv("UMH_ROOT", str(tmp_path))
    monkeypatch.setenv("UMH_ORG_ID", "test-org")
    monkeypatch.setenv("UMH_USER_ID", "test-user")
    os.makedirs(tmp_path / "data" / "umh" / "audit", exist_ok=True)
    os.makedirs(tmp_path / "data" / "umh" / "universal_work", exist_ok=True)
    os.makedirs(tmp_path / "data" / "umh" / "sandboxes", exist_ok=True)


class TestIntentContract:
    """Section 1: full intent contract accepted and persisted."""

    def test_submit_minimal_intent(self):
        from substrate.organism.universal_work_queue import UniversalWorkQueue
        q = UniversalWorkQueue()
        pkt = q.ingest_user_intent(user_intent="Add a health check endpoint")
        assert pkt.packet_id
        assert pkt.user_intent == "Add a health check endpoint"
        assert pkt.status.value == "classified"

    def test_submit_full_contract_fields(self):
        from substrate.organism.universal_work_queue import UniversalWorkQueue
        from substrate.organism.work_packet import WorkPacket
        q = UniversalWorkQueue()
        pkt = q.ingest_user_intent(
            user_intent="Add health check endpoint",
            desired_end_state="GET /health returns JSON with queue summary",
            constraints=["no new dependencies", "under 50 lines"],
        )
        pkt.success_criteria = ["returns 200", "includes queue_summary field"]
        pkt.failure_criteria = ["must not break existing routes"]
        pkt.validation_plan = "Quality bar: production. Proof required: test output, import check"
        pkt.risk_class = "low"
        q._save()

        reloaded = q.get_packet(pkt.packet_id)
        assert reloaded.desired_end_state == "GET /health returns JSON with queue summary"
        assert len(reloaded.constraints) == 2
        assert reloaded.success_criteria == ["returns 200", "includes queue_summary field"]
        assert reloaded.failure_criteria == ["must not break existing routes"]
        assert "production" in reloaded.validation_plan
        assert reloaded.risk_class == "low"


class TestApprovalGate:
    """Section 4: governance + approval enforcement."""

    def test_low_risk_no_approval_needed(self):
        from substrate.organism.universal_work_queue import UniversalWorkQueue
        from substrate.organism.work_packet import PacketLifecycleStatus
        q = UniversalWorkQueue()
        pkt = q.ingest_user_intent(user_intent="Read a file")
        assert not pkt.approval_gates or len(pkt.approval_gates) == 0

    def test_status_transitions_through_approval(self):
        from substrate.organism.universal_work_queue import UniversalWorkQueue
        from substrate.organism.work_packet import PacketLifecycleStatus
        q = UniversalWorkQueue()
        pkt = q.ingest_user_intent(user_intent="Deploy service")
        pid = pkt.packet_id

        assert q.update_packet_status(pid, PacketLifecycleStatus.PLANNED, "planned")
        assert q.update_packet_status(pid, PacketLifecycleStatus.READY_FOR_REVIEW, "ready")
        assert q.update_packet_status(pid, PacketLifecycleStatus.APPROVAL_PENDING, "pending")
        assert q.update_packet_status(pid, PacketLifecycleStatus.APPROVED, "approved")

        pkt = q.get_packet(pid)
        assert pkt.status == PacketLifecycleStatus.APPROVED

    def test_invalid_transition_blocked(self):
        from substrate.organism.universal_work_queue import UniversalWorkQueue
        from substrate.organism.work_packet import PacketLifecycleStatus
        q = UniversalWorkQueue()
        pkt = q.ingest_user_intent(user_intent="Something")
        assert not q.update_packet_status(pkt.packet_id, PacketLifecycleStatus.COMPLETED, "skip")


class TestSandboxManager:
    """Section 3: sandbox/worktree creation and validation tracking.

    Note: create_sandbox requires a real git repo, so we test in
    the actual worktree. Validation result tracking uses in-memory
    sandbox state and works without git.
    """

    @pytest.mark.skip(reason="requires real git repo as cwd — integration test only")
    def test_create_sandbox(self):
        from substrate.organism.worktree_sandbox import SandboxManager
        mgr = SandboxManager()
        sb = mgr.create_sandbox(
            candidate_id="test-pkt-001",
            candidate_slug="health-check",
            agent_type="operator_loop",
        )
        assert sb.sandbox_id
        assert sb.worktree_path
        assert sb.branch_name

        detail = mgr.get_sandbox(sb.sandbox_id)
        assert detail is not None

        mgr.cleanup_sandbox(sb.sandbox_id)

    def test_validation_result_tracking(self):
        from substrate.organism.worktree_sandbox import SandboxManager, SandboxValidationResult, WorktreeSandbox, SandboxStatus
        mgr = SandboxManager()
        sb = WorktreeSandbox(
            sandbox_id="sb-val-test",
            candidate_id="test-pkt-002",
            worktree_path="/tmp/fake-worktree",
            branch_name="test-branch",
            agent_type="operator_loop",
            status=SandboxStatus.CREATED,
        )
        mgr._sandboxes[sb.sandbox_id] = sb

        mgr.add_validation_result(sb.sandbox_id, SandboxValidationResult(
            passed=True,
            command="python3 -c 'print(1)'",
            stdout="1\n",
            stderr="",
            exit_code=0,
            duration_seconds=0.1,
        ))
        mgr.add_validation_result(sb.sandbox_id, SandboxValidationResult(
            passed=False,
            command="python3 -c 'raise'",
            stdout="",
            stderr="error",
            exit_code=1,
            duration_seconds=0.2,
        ))
        detail = mgr.get_sandbox(sb.sandbox_id)
        assert len(detail.validation_results) == 2
        assert detail.validation_results[0].passed
        assert not detail.validation_results[1].passed


class TestExecutionArtifacts:
    """Section 3: linking execution artifacts to work packets."""

    def test_link_sandbox_to_packet(self):
        from substrate.organism.universal_work_queue import UniversalWorkQueue
        q = UniversalWorkQueue()
        pkt = q.ingest_user_intent(user_intent="Test linking")
        q.link_execution_artifacts(pkt.packet_id, {"sandbox_id": "sb-123"})
        reloaded = q.get_packet(pkt.packet_id)
        assert reloaded.linked_sandbox_id == "sb-123"

    def test_link_pr_to_packet(self):
        from substrate.organism.universal_work_queue import UniversalWorkQueue
        q = UniversalWorkQueue()
        pkt = q.ingest_user_intent(user_intent="Test PR linking")
        q.link_execution_artifacts(pkt.packet_id, {"pr_url": "https://github.com/test/repo/pull/1"})
        reloaded = q.get_packet(pkt.packet_id)
        assert reloaded.linked_pr_url == "https://github.com/test/repo/pull/1"


class TestValidationCommands:
    """Section 3: validation command derivation."""

    def test_derive_commands_default(self):
        from transports.api.cockpit_operator_loop_routes import _derive_validation_commands
        from substrate.organism.work_packet import WorkPacket
        pkt = WorkPacket(title="test", user_intent="test")
        cmds = _derive_validation_commands(pkt)
        assert len(cmds) >= 2
        labels = [c["label"] for c in cmds]
        assert "substrate import check" in labels

    def test_derive_commands_with_test_plan(self):
        from transports.api.cockpit_operator_loop_routes import _derive_validation_commands
        from substrate.organism.work_packet import WorkPacket
        pkt = WorkPacket(title="test", user_intent="test", validation_plan="run pytest and ruff lint")
        cmds = _derive_validation_commands(pkt)
        labels = [c["label"] for c in cmds]
        assert any("test" in l for l in labels)
        assert any("lint" in l for l in labels)

    def test_derive_commands_infrastructure(self):
        from transports.api.cockpit_operator_loop_routes import _derive_validation_commands
        from substrate.organism.work_packet import WorkPacket
        pkt = WorkPacket(title="test gate", user_intent="test", domain="infrastructure")
        cmds = _derive_validation_commands(pkt)
        labels = [c["label"] for c in cmds]
        assert any("dependency" in l for l in labels)


class TestAuditTrail:
    """Section 5: audit trail persistence."""

    def test_audit_log_writes(self, tmp_path, monkeypatch):
        import transports.api.cockpit_operator_loop_routes as routes
        monkeypatch.setattr(routes, "_REPO_ROOT", str(tmp_path))
        routes._audit_log("test_event", {"key": "value"})
        audit_path = tmp_path / "data" / "umh" / "audit" / "operator_loop_audit.jsonl"
        assert audit_path.exists()
        lines = audit_path.read_text().strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["event_type"] == "test_event"
        assert entry["data"]["key"] == "value"

    def test_audit_log_accumulates(self, tmp_path, monkeypatch):
        import transports.api.cockpit_operator_loop_routes as routes
        monkeypatch.setattr(routes, "_REPO_ROOT", str(tmp_path))
        routes._audit_log("event_1", {"a": 1})
        routes._audit_log("event_2", {"b": 2})
        routes._audit_log("event_3", {"c": 3})
        audit_path = tmp_path / "data" / "umh" / "audit" / "operator_loop_audit.jsonl"
        lines = audit_path.read_text().strip().split("\n")
        assert len(lines) == 3


class TestOutcomeRecording:
    """Section 6: outcome recording in reality model."""

    def test_record_outcome_internal(self):
        from transports.api.cockpit_operator_loop_routes import _record_outcome_internal
        obs_id = _record_outcome_internal(
            packet_id="pkt-001",
            outcome_text="Test passed successfully",
            domain="testing",
            confidence=0.9,
        )
        assert obs_id is not None


class TestFullLifecycle:
    """Section 8: end-to-end lifecycle test."""

    def test_intent_to_completion(self):
        from substrate.organism.universal_work_queue import UniversalWorkQueue
        from substrate.organism.work_packet import PacketLifecycleStatus
        from transports.api.cockpit_operator_loop_routes import _audit_log, _record_outcome_internal

        q = UniversalWorkQueue()

        pkt = q.ingest_user_intent(
            user_intent="Add operator-loop health endpoint",
            desired_end_state="GET /health returns queue summary and audit status",
            constraints=["under 50 lines", "no new dependencies"],
        )
        pid = pkt.packet_id
        assert pkt.status == PacketLifecycleStatus.CLASSIFIED

        _audit_log("intent_submitted", {"packet_id": pid})

        assert q.update_packet_status(pid, PacketLifecycleStatus.PLANNED, "auto-planned")
        assert q.update_packet_status(pid, PacketLifecycleStatus.READY_FOR_REVIEW, "reviewed")
        assert q.update_packet_status(pid, PacketLifecycleStatus.APPROVAL_PENDING, "pending")
        assert q.update_packet_status(pid, PacketLifecycleStatus.APPROVED, "operator approved")

        _audit_log("packet_approved", {"packet_id": pid})

        assert q.update_packet_status(pid, PacketLifecycleStatus.DELEGATED, "delegated")
        assert q.update_packet_status(pid, PacketLifecycleStatus.EXECUTING, "executing")

        _audit_log("packet_executing", {"packet_id": pid})

        q.link_execution_artifacts(pid, {"sandbox_id": "sb-e2e-001"})

        pkt = q.get_packet(pid)
        pkt.verification_results = [
            {"command": "python3 -m pytest", "passed": True, "exit_code": 0, "label": "tests", "stdout": "", "stderr": "", "duration_seconds": 1.0, "timestamp": time.time()},
        ]
        pkt.verification_passed = True
        q._save()

        assert q.update_packet_status(pid, PacketLifecycleStatus.VALIDATING, "validating")

        obs_id = _record_outcome_internal(
            packet_id=pid,
            outcome_text="Health endpoint added, all tests pass",
            domain="infrastructure",
            confidence=0.9,
        )
        assert obs_id is not None

        assert q.update_packet_status(pid, PacketLifecycleStatus.COMPLETED, "completed")

        pkt = q.get_packet(pid)
        assert pkt.status == PacketLifecycleStatus.COMPLETED
        assert pkt.verification_passed
        assert pkt.linked_sandbox_id == "sb-e2e-001"

    def test_rejected_packet(self):
        from substrate.organism.universal_work_queue import UniversalWorkQueue
        from substrate.organism.work_packet import PacketLifecycleStatus

        q = UniversalWorkQueue()
        pkt = q.ingest_user_intent(user_intent="Delete production DB")
        pid = pkt.packet_id
        assert q.update_packet_status(pid, PacketLifecycleStatus.PLANNED, "planned")
        assert q.update_packet_status(pid, PacketLifecycleStatus.READY_FOR_REVIEW, "ready")
        assert q.update_packet_status(pid, PacketLifecycleStatus.APPROVAL_PENDING, "pending")

        from substrate.organism.work_packet import _VALID_TRANSITIONS
        if PacketLifecycleStatus.REJECTED in _VALID_TRANSITIONS.get(PacketLifecycleStatus.APPROVAL_PENDING, frozenset()):
            assert q.update_packet_status(pid, PacketLifecycleStatus.REJECTED, "too dangerous")
            pkt = q.get_packet(pid)
            assert pkt.status == PacketLifecycleStatus.REJECTED

    def test_failed_execution(self):
        from substrate.organism.universal_work_queue import UniversalWorkQueue
        from substrate.organism.work_packet import PacketLifecycleStatus

        q = UniversalWorkQueue()
        pkt = q.ingest_user_intent(user_intent="Run failing task")
        pid = pkt.packet_id

        assert q.update_packet_status(pid, PacketLifecycleStatus.PLANNED, "planned")
        assert q.update_packet_status(pid, PacketLifecycleStatus.READY_FOR_REVIEW, "ready")
        assert q.update_packet_status(pid, PacketLifecycleStatus.APPROVAL_PENDING, "pending")
        assert q.update_packet_status(pid, PacketLifecycleStatus.APPROVED, "approved")
        assert q.update_packet_status(pid, PacketLifecycleStatus.DELEGATED, "delegated")
        assert q.update_packet_status(pid, PacketLifecycleStatus.EXECUTING, "executing")
        assert q.update_packet_status(pid, PacketLifecycleStatus.FAILED, "tests failed")

        pkt = q.get_packet(pid)
        assert pkt.status == PacketLifecycleStatus.FAILED


class TestQueueSummary:
    """Queue summary for health endpoint."""

    def test_compute_queue_summary(self):
        from substrate.organism.universal_work_queue import UniversalWorkQueue
        q = UniversalWorkQueue()
        q.ingest_user_intent(user_intent="task 1")
        q.ingest_user_intent(user_intent="task 2")
        summary = q.compute_queue_summary()
        assert summary is not None
