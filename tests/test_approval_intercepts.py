"""Phase 15C: Approval Intercepts — comprehensive test suite.

Tests:
  1. ApprovalInterceptRequest creation and serialization
  2. ApprovalInterceptStore operations (create, approve, reject, expire)
  3. ApprovalInterceptService layer
  4. Risk classification
  5. State transition validation
  6. Timeout handling
  7. Pause/resume flow
  8. Proof integration (approval_events field)
  9. Telemetry integration
  10. Double-decision prevention
  11. Concurrent access
  12. Store eviction
"""

from __future__ import annotations

import os
import sys
import threading
import time

import pytest

sys.path.insert(0, "/opt/OS")

from substrate.organism.executors.approval_intercept import (
    ApprovalInterceptRequest,
    ApprovalInterceptService,
    ApprovalInterceptStatus,
    ApprovalInterceptStore,
    classify_operation_risk,
    get_approval_intercept_service,
    requires_approval,
    reset_approval_intercept_service,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fixtures
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.fixture
def store():
    return ApprovalInterceptStore()


@pytest.fixture
def service():
    return ApprovalInterceptService()


@pytest.fixture
def pending_intercept(store):
    req = ApprovalInterceptRequest(
        execution_id="exec-001",
        request_id="req-001",
        executor_type="workstation",
        operation="run_command",
        risk_class="high",
        reason="Remote push requires approval",
        details={"command": "git push"},
    )
    store.create(req)
    return req


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. Request Creation and Serialization
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRequestCreation:
    def test_default_fields(self):
        req = ApprovalInterceptRequest()
        assert req.approval_id.startswith("apvl-")
        assert req.status == "pending"
        assert req.expires_at > req.requested_at
        assert req.decided_by == ""

    def test_custom_fields(self):
        req = ApprovalInterceptRequest(
            execution_id="ex-1",
            executor_type="workstation",
            operation="run_command",
            risk_class="critical",
            reason="destructive op",
        )
        assert req.execution_id == "ex-1"
        assert req.risk_class == "critical"
        assert req.reason == "destructive op"

    def test_to_dict_roundtrip(self):
        req = ApprovalInterceptRequest(
            execution_id="ex-2",
            reason="test",
            details={"key": "value"},
        )
        d = req.to_dict()
        restored = ApprovalInterceptRequest.from_dict(d)
        assert restored.execution_id == "ex-2"
        assert restored.reason == "test"
        assert restored.details == {"key": "value"}

    def test_is_pending_property(self):
        req = ApprovalInterceptRequest()
        assert req.is_pending is True
        req.status = "approved"
        assert req.is_pending is False

    def test_age_seconds(self):
        req = ApprovalInterceptRequest(requested_at=time.time() - 10)
        assert req.age_seconds >= 10


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. Store Operations
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestStoreOperations:
    def test_create_and_get(self, store):
        req = ApprovalInterceptRequest(execution_id="ex-1")
        store.create(req)
        retrieved = store.get(req.approval_id)
        assert retrieved is not None
        assert retrieved.execution_id == "ex-1"

    def test_get_nonexistent(self, store):
        assert store.get("nonexistent") is None

    def test_approve(self, store, pending_intercept):
        result = store.approve(pending_intercept.approval_id, decided_by="afm")
        assert result is not None
        assert result.status == "approved"
        assert result.decided_by == "afm"
        assert result.decided_at > 0

    def test_reject(self, store, pending_intercept):
        result = store.reject(
            pending_intercept.approval_id,
            reason="too risky",
            decided_by="afm",
        )
        assert result is not None
        assert result.status == "rejected"
        assert result.rejection_reason == "too risky"

    def test_expire(self, store, pending_intercept):
        result = store.expire(pending_intercept.approval_id)
        assert result is not None
        assert result.status == "expired"

    def test_list_pending(self, store):
        for i in range(3):
            store.create(ApprovalInterceptRequest(execution_id=f"ex-{i}"))
        assert len(store.list_pending()) == 3

    def test_list_pending_excludes_decided(self, store):
        req1 = ApprovalInterceptRequest(execution_id="ex-1")
        req2 = ApprovalInterceptRequest(execution_id="ex-2")
        store.create(req1)
        store.create(req2)
        store.approve(req1.approval_id)
        pending = store.list_pending()
        assert len(pending) == 1
        assert pending[0].execution_id == "ex-2"

    def test_count(self, store):
        assert store.count == 0
        store.create(ApprovalInterceptRequest())
        assert store.count == 1

    def test_pending_count(self, store):
        req1 = ApprovalInterceptRequest()
        req2 = ApprovalInterceptRequest()
        store.create(req1)
        store.create(req2)
        store.approve(req1.approval_id)
        assert store.pending_count == 1

    def test_clear(self, store, pending_intercept):
        assert store.count == 1
        store.clear()
        assert store.count == 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. Service Layer
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestServiceLayer:
    def test_request_approval(self, service):
        intercept = service.request_approval(
            execution_id="ex-1",
            executor_type="workstation",
            operation="run_command",
            risk_class="high",
            reason="Remote push",
        )
        assert intercept.status == "pending"
        assert intercept.execution_id == "ex-1"

    def test_approve_via_service(self, service):
        intercept = service.request_approval(
            execution_id="ex-2",
            reason="test",
        )
        result = service.approve(intercept.approval_id, operator_id="afm")
        assert result is not None
        assert result.status == "approved"
        assert result.decided_by == "afm"

    def test_reject_via_service(self, service):
        intercept = service.request_approval(
            execution_id="ex-3",
            reason="test",
        )
        result = service.reject(
            intercept.approval_id,
            reason="not now",
            operator_id="afm",
        )
        assert result is not None
        assert result.status == "rejected"
        assert result.rejection_reason == "not now"

    def test_pending_list(self, service):
        service.request_approval(execution_id="ex-1", reason="a")
        service.request_approval(execution_id="ex-2", reason="b")
        assert len(service.pending()) == 2

    def test_get(self, service):
        intercept = service.request_approval(execution_id="ex-1", reason="a")
        retrieved = service.get(intercept.approval_id)
        assert retrieved is not None
        assert retrieved.execution_id == "ex-1"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. Risk Classification
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRiskClassification:
    def test_read_file_is_low(self):
        assert classify_operation_risk("read_file", {"path": "/opt/OS/f.py"}) == "low"

    def test_list_directory_is_low(self):
        assert classify_operation_risk("list_directory", {"path": "/opt/OS"}) == "low"

    def test_create_worktree_is_low(self):
        assert classify_operation_risk("create_worktree", {"branch_name": "test"}) == "low"

    def test_write_file_is_medium(self):
        assert classify_operation_risk("write_file", {"path": "/opt/OS/test.py"}) == "medium"

    def test_write_env_is_critical(self):
        assert classify_operation_risk("write_file", {"path": "/opt/OS/.env"}) == "critical"

    def test_run_command_git_push_is_high(self):
        assert classify_operation_risk("run_command", {"command": "git push origin main"}) == "high"

    def test_run_command_force_push_is_critical(self):
        assert classify_operation_risk("run_command", {"command": "git push --force"}) == "critical"

    def test_run_command_rm_rf_is_critical(self):
        assert classify_operation_risk("run_command", {"command": "rm -rf /tmp/test"}) == "critical"

    def test_run_command_echo_is_medium(self):
        assert classify_operation_risk("run_command", {"command": "echo hello"}) == "medium"

    def test_run_command_delete_is_high(self):
        assert classify_operation_risk("run_command", {"command": "delete old-branch"}) == "high"

    def test_run_command_list_is_high(self):
        assert classify_operation_risk("run_command", {"command": ["rm", "old_file.py"]}) == "high"

    def test_run_command_branch_delete_is_high(self):
        assert classify_operation_risk("run_command", {"command": "git branch -D feature"}) == "high"

    def test_requires_approval_low(self):
        assert requires_approval("low") is False

    def test_requires_approval_medium(self):
        assert requires_approval("medium") is False

    def test_requires_approval_high(self):
        assert requires_approval("high") is True

    def test_requires_approval_critical(self):
        assert requires_approval("critical") is True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. State Transition Validation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestStateTransitions:
    def test_approve_already_approved(self, store, pending_intercept):
        store.approve(pending_intercept.approval_id)
        result = store.approve(pending_intercept.approval_id)
        assert result is None

    def test_reject_already_approved(self, store, pending_intercept):
        store.approve(pending_intercept.approval_id)
        result = store.reject(pending_intercept.approval_id)
        assert result is None

    def test_approve_already_rejected(self, store, pending_intercept):
        store.reject(pending_intercept.approval_id)
        result = store.approve(pending_intercept.approval_id)
        assert result is None

    def test_reject_already_rejected(self, store, pending_intercept):
        store.reject(pending_intercept.approval_id)
        result = store.reject(pending_intercept.approval_id)
        assert result is None

    def test_approve_expired(self, store):
        req = ApprovalInterceptRequest(
            execution_id="ex-expired",
            expires_at=time.time() - 1,
        )
        store.create(req)
        result = store.approve(req.approval_id)
        assert result is None

    def test_expire_already_approved(self, store, pending_intercept):
        store.approve(pending_intercept.approval_id)
        result = store.expire(pending_intercept.approval_id)
        assert result is None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. Timeout Handling
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestTimeoutHandling:
    def test_wait_timeout(self, store):
        req = ApprovalInterceptRequest(
            execution_id="ex-timeout",
            expires_at=time.time() + 0.2,
        )
        store.create(req)
        start = time.time()
        result = store.wait_for_decision(req.approval_id, timeout=0.3)
        elapsed = time.time() - start
        assert result is not None
        assert result.status == "expired"
        assert elapsed < 1.0

    def test_custom_timeout_seconds(self, service):
        intercept = service.request_approval(
            execution_id="ex-custom",
            reason="test",
            timeout_seconds=5.0,
        )
        assert intercept.expires_at <= time.time() + 6

    def test_no_hanging_on_short_timeout(self, store):
        req = ApprovalInterceptRequest(
            execution_id="ex-short",
            expires_at=time.time() + 0.1,
        )
        store.create(req)
        start = time.time()
        result = store.wait_for_decision(req.approval_id, timeout=0.2)
        elapsed = time.time() - start
        assert elapsed < 0.5
        assert result.status == "expired"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 7. Pause/Resume Flow
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestPauseResume:
    def test_approve_unblocks_waiter(self, store):
        req = ApprovalInterceptRequest(execution_id="ex-wait")
        store.create(req)

        result_holder = [None]

        def waiter():
            result_holder[0] = store.wait_for_decision(req.approval_id)

        t = threading.Thread(target=waiter)
        t.start()
        time.sleep(0.05)
        store.approve(req.approval_id, decided_by="afm")
        t.join(timeout=2.0)
        assert not t.is_alive()
        assert result_holder[0].status == "approved"

    def test_reject_unblocks_waiter(self, store):
        req = ApprovalInterceptRequest(execution_id="ex-reject")
        store.create(req)

        result_holder = [None]

        def waiter():
            result_holder[0] = store.wait_for_decision(req.approval_id)

        t = threading.Thread(target=waiter)
        t.start()
        time.sleep(0.05)
        store.reject(req.approval_id, reason="nope")
        t.join(timeout=2.0)
        assert not t.is_alive()
        assert result_holder[0].status == "rejected"

    def test_service_await_approve(self, service):
        intercept = service.request_approval(
            execution_id="ex-svc-await",
            reason="test",
        )

        result_holder = [None]

        def waiter():
            result_holder[0] = service.await_decision(intercept.approval_id)

        t = threading.Thread(target=waiter)
        t.start()
        time.sleep(0.05)
        service.approve(intercept.approval_id, operator_id="afm")
        t.join(timeout=2.0)
        assert not t.is_alive()
        assert result_holder[0].status == "approved"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 8. Proof Integration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestProofIntegration:
    def test_execution_proof_has_approval_events(self):
        from substrate.organism.executors.workstation_executor import ExecutionProof

        proof = ExecutionProof(
            execution_id="ex-1",
            operation="run_command",
            approval_events=[
                {
                    "approval_id": "apvl-abc123",
                    "decision": "approved",
                    "operator": "afm",
                    "timestamp": 1718300000.0,
                },
            ],
        )
        d = proof.to_dict()
        assert "approval_events" in d
        assert len(d["approval_events"]) == 1
        assert d["approval_events"][0]["decision"] == "approved"

    def test_proof_empty_approval_events(self):
        from substrate.organism.executors.workstation_executor import ExecutionProof

        proof = ExecutionProof(execution_id="ex-2", operation="read_file")
        d = proof.to_dict()
        assert d["approval_events"] == []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 9. Telemetry Integration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestTelemetryIntegration:
    def test_telemetry_events_include_approval_types(self):
        from substrate.organism.executors.execution_telemetry import TelemetryEventType

        assert TelemetryEventType.APPROVAL_REQUESTED.value == "approval_requested"
        assert TelemetryEventType.APPROVAL_GRANTED.value == "approval_granted"
        assert TelemetryEventType.APPROVAL_REJECTED.value == "approval_rejected"
        assert TelemetryEventType.APPROVAL_EXPIRED.value == "approval_expired"
        assert TelemetryEventType.APPROVAL_VIEWED.value == "approval_viewed"
        assert TelemetryEventType.EXECUTION_PAUSED.value == "execution_paused"
        assert TelemetryEventType.EXECUTION_RESUMED.value == "execution_resumed"

    def test_service_emits_on_request(self):
        from substrate.organism.executors.execution_telemetry import (
            ExecutionTelemetryEmitter,
            InMemoryExecutionTelemetryStore,
        )

        tel_store = InMemoryExecutionTelemetryStore()
        emitter = ExecutionTelemetryEmitter(store=tel_store)
        svc = ApprovalInterceptService(telemetry_emitter=emitter)

        svc.request_approval(
            execution_id="ex-tel-1",
            reason="test",
        )
        events = tel_store.get_latest(10)
        assert any(e.event_type == "approval_requested" for e in events)

    def test_service_emits_on_approve(self):
        from substrate.organism.executors.execution_telemetry import (
            ExecutionTelemetryEmitter,
            InMemoryExecutionTelemetryStore,
        )

        tel_store = InMemoryExecutionTelemetryStore()
        emitter = ExecutionTelemetryEmitter(store=tel_store)
        svc = ApprovalInterceptService(telemetry_emitter=emitter)

        intercept = svc.request_approval(execution_id="ex-tel-2", reason="test")
        svc.approve(intercept.approval_id, operator_id="afm")
        events = tel_store.get_latest(10)
        assert any(e.event_type == "approval_granted" for e in events)

    def test_service_emits_on_reject(self):
        from substrate.organism.executors.execution_telemetry import (
            ExecutionTelemetryEmitter,
            InMemoryExecutionTelemetryStore,
        )

        tel_store = InMemoryExecutionTelemetryStore()
        emitter = ExecutionTelemetryEmitter(store=tel_store)
        svc = ApprovalInterceptService(telemetry_emitter=emitter)

        intercept = svc.request_approval(execution_id="ex-tel-3", reason="test")
        svc.reject(intercept.approval_id, reason="no", operator_id="afm")
        events = tel_store.get_latest(10)
        assert any(e.event_type == "approval_rejected" for e in events)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 10. Double-Decision Prevention
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestDoubleDecision:
    def test_double_approve(self, store, pending_intercept):
        first = store.approve(pending_intercept.approval_id)
        second = store.approve(pending_intercept.approval_id)
        assert first is not None
        assert second is None

    def test_approve_then_reject(self, store, pending_intercept):
        store.approve(pending_intercept.approval_id)
        result = store.reject(pending_intercept.approval_id)
        assert result is None

    def test_reject_then_approve(self, store, pending_intercept):
        store.reject(pending_intercept.approval_id)
        result = store.approve(pending_intercept.approval_id)
        assert result is None

    def test_expire_then_approve(self, store):
        req = ApprovalInterceptRequest(
            execution_id="ex-exp-apv",
            expires_at=time.time() - 1,
        )
        store.create(req)
        result = store.approve(req.approval_id)
        assert result is None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 11. Concurrent Access
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestConcurrentAccess:
    def test_concurrent_approvals(self, store):
        req = ApprovalInterceptRequest(execution_id="ex-conc")
        store.create(req)

        results = []

        def try_approve():
            r = store.approve(req.approval_id, decided_by="thread")
            results.append(r)

        threads = [threading.Thread(target=try_approve) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=2.0)

        successes = [r for r in results if r is not None]
        assert len(successes) == 1

    def test_concurrent_waiters_and_approver(self, store):
        req = ApprovalInterceptRequest(execution_id="ex-multi-wait")
        store.create(req)

        results = []

        def waiter():
            r = store.wait_for_decision(req.approval_id, timeout=5.0)
            results.append(r)

        threads = [threading.Thread(target=waiter) for _ in range(3)]
        for t in threads:
            t.start()
        time.sleep(0.1)
        store.approve(req.approval_id)
        for t in threads:
            t.join(timeout=2.0)

        assert len(results) == 3
        assert all(r.status == "approved" for r in results)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 12. Store Eviction
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestStoreEviction:
    def test_eviction_at_capacity(self):
        store = ApprovalInterceptStore(max_intercepts=5)
        ids = []
        for i in range(5):
            req = ApprovalInterceptRequest(execution_id=f"ex-{i}")
            store.create(req)
            ids.append(req.approval_id)
            if i < 3:
                store.approve(req.approval_id)

        extra = ApprovalInterceptRequest(execution_id="ex-extra")
        store.create(extra)
        assert store.count <= 5

    def test_eviction_removes_oldest_decided(self):
        store = ApprovalInterceptStore(max_intercepts=3)
        req1 = ApprovalInterceptRequest(execution_id="ex-old")
        req2 = ApprovalInterceptRequest(execution_id="ex-mid")
        req3 = ApprovalInterceptRequest(execution_id="ex-new")
        store.create(req1)
        store.create(req2)
        store.create(req3)
        store.approve(req1.approval_id)
        store.approve(req2.approval_id)

        req4 = ApprovalInterceptRequest(execution_id="ex-newest")
        store.create(req4)
        assert store.get(req1.approval_id) is None

    def test_eviction_preserves_pending(self):
        store = ApprovalInterceptStore(max_intercepts=3)
        pending = ApprovalInterceptRequest(execution_id="ex-pend")
        decided1 = ApprovalInterceptRequest(execution_id="ex-d1")
        decided2 = ApprovalInterceptRequest(execution_id="ex-d2")
        store.create(pending)
        store.create(decided1)
        store.create(decided2)
        store.approve(decided1.approval_id)
        store.approve(decided2.approval_id)

        extra = ApprovalInterceptRequest(execution_id="ex-extra")
        store.create(extra)
        assert store.get(pending.approval_id) is not None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 13. Singleton
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSingleton:
    def test_singleton_returns_same_instance(self):
        reset_approval_intercept_service()
        svc1 = get_approval_intercept_service()
        svc2 = get_approval_intercept_service()
        assert svc1 is svc2
        reset_approval_intercept_service()

    def test_reset_creates_new_instance(self):
        reset_approval_intercept_service()
        svc1 = get_approval_intercept_service()
        reset_approval_intercept_service()
        svc2 = get_approval_intercept_service()
        assert svc1 is not svc2
        reset_approval_intercept_service()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 14. Runtime Integration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRuntimeIntegration:
    def test_executor_runtime_request_approval(self, tmp_path):
        os.environ["UMH_ROOT"] = str(tmp_path)
        from substrate.organism.executor_runtime import (
            ExecutorRequest,
            ExecutorRuntime,
            reset_executor_runtime,
        )

        reset_executor_runtime()
        runtime = ExecutorRuntime(data_dir=str(tmp_path / "data"))

        req = ExecutorRequest(
            execution_plan_id="plan-1",
            executor_type="workstation",
            risk_class="high",
            metadata={"operation": "run_command"},
        )
        runtime._request_store.save(req)

        result_holder = [None]

        def do_approval():
            result_holder[0] = runtime.request_approval(req, reason="test approval")

        t = threading.Thread(target=do_approval)
        t.start()
        time.sleep(0.1)

        svc = get_approval_intercept_service()
        pending = svc.pending()
        assert len(pending) >= 1

        svc.approve(pending[0].approval_id, operator_id="afm")
        t.join(timeout=3.0)
        assert not t.is_alive()
        approved, msg = result_holder[0]
        assert approved is True
        assert "afm" in msg

        reset_approval_intercept_service()
        reset_executor_runtime()

    def test_executor_runtime_reject(self, tmp_path):
        os.environ["UMH_ROOT"] = str(tmp_path)
        from substrate.organism.executor_runtime import (
            ExecutorRequest,
            ExecutorRuntime,
            reset_executor_runtime,
        )

        reset_executor_runtime()
        reset_approval_intercept_service()
        runtime = ExecutorRuntime(data_dir=str(tmp_path / "data"))

        req = ExecutorRequest(
            execution_plan_id="plan-2",
            executor_type="workstation",
            risk_class="critical",
            metadata={"operation": "run_command"},
        )
        runtime._request_store.save(req)

        result_holder = [None]

        def do_approval():
            result_holder[0] = runtime.request_approval(req, reason="dangerous op")

        t = threading.Thread(target=do_approval)
        t.start()
        time.sleep(0.1)

        svc = get_approval_intercept_service()
        pending = svc.pending()
        svc.reject(pending[0].approval_id, reason="too dangerous", operator_id="afm")
        t.join(timeout=3.0)
        assert not t.is_alive()
        approved, msg = result_holder[0]
        assert approved is False
        assert "dangerous" in msg

        reset_approval_intercept_service()
        reset_executor_runtime()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 15. Auto-Expiry of Stale in list_pending
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestAutoExpiry:
    def test_list_pending_expires_stale(self, store):
        req = ApprovalInterceptRequest(
            execution_id="ex-stale",
            expires_at=time.time() - 1,
        )
        store.create(req)
        pending = store.list_pending()
        assert len(pending) == 0
        assert store.get(req.approval_id).status == "expired"

    def test_list_all_includes_expired(self, store):
        req = ApprovalInterceptRequest(
            execution_id="ex-exp",
            expires_at=time.time() - 1,
        )
        store.create(req)
        all_items = store.list_all()
        assert len(all_items) == 1
        assert all_items[0].status == "expired"
