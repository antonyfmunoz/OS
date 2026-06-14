"""Tests for Phase 14 — Executor Runtime."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.organism.executor_runtime import (
    ExecutorApprovalState,
    ExecutorArtifact,
    ExecutorContract,
    ExecutorContextAssembler,
    ExecutorEventType,
    ExecutorGovernanceGate,
    ExecutorImplementationRegistry,
    ExecutorLifecycleEvent,
    ExecutorLifecycleStatus,
    ExecutorLifecycleTracker,
    ExecutorRequest,
    ExecutorRequestStatus,
    ExecutorRequestStore,
    ExecutorResult,
    ExecutorResultStore,
    ExecutorRuntime,
    ExecutorRuntimeContext,
    ExecutorRuntimeSnapshot,
    ExecutorType,
    SimulationExecutor,
    get_executor_runtime,
    reset_executor_runtime,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Enum Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExecutorLifecycleStatus:
    def test_values(self):
        assert len(ExecutorLifecycleStatus) == 9
        assert ExecutorLifecycleStatus.CREATED.value == "created"
        assert ExecutorLifecycleStatus.VALIDATED.value == "validated"
        assert ExecutorLifecycleStatus.PREPARED.value == "prepared"
        assert ExecutorLifecycleStatus.DISPATCHED.value == "dispatched"
        assert ExecutorLifecycleStatus.EXECUTING.value == "executing"
        assert ExecutorLifecycleStatus.COMPLETED.value == "completed"
        assert ExecutorLifecycleStatus.FAILED.value == "failed"
        assert ExecutorLifecycleStatus.CANCELLED.value == "cancelled"
        assert ExecutorLifecycleStatus.CLEANED_UP.value == "cleaned_up"


class TestExecutorType:
    def test_values(self):
        assert len(ExecutorType) == 7
        assert ExecutorType.WORKSTATION.value == "workstation"
        assert ExecutorType.AGENT.value == "agent"
        assert ExecutorType.CONTAINER.value == "container"
        assert ExecutorType.VPS.value == "vps"
        assert ExecutorType.BROWSER.value == "browser"
        assert ExecutorType.MOBILE.value == "mobile"
        assert ExecutorType.EXTERNAL.value == "external"


class TestExecutorRequestStatus:
    def test_values(self):
        assert len(ExecutorRequestStatus) == 12
        assert ExecutorRequestStatus.PENDING.value == "pending"
        assert ExecutorRequestStatus.EXECUTING.value == "executing"
        assert ExecutorRequestStatus.COMPLETED.value == "completed"
        assert ExecutorRequestStatus.CLEANED_UP.value == "cleaned_up"


class TestExecutorEventType:
    def test_values(self):
        assert len(ExecutorEventType) == 16
        assert ExecutorEventType.REQUEST_CREATED.value == "request_created"
        assert ExecutorEventType.EXECUTION_COMPLETED.value == "execution_completed"
        assert ExecutorEventType.CLEANUP_COMPLETED.value == "cleanup_completed"


class TestExecutorApprovalState:
    def test_values(self):
        assert len(ExecutorApprovalState) == 4
        assert ExecutorApprovalState.AUTO_APPROVED.value == "auto_approved"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Model Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExecutorRuntimeContext:
    def test_auto_defaults(self):
        ctx = ExecutorRuntimeContext()
        assert ctx.risk_class == "low"
        assert ctx.objectives == []
        assert ctx.workpacket == {}

    def test_roundtrip(self):
        ctx = ExecutorRuntimeContext(
            risk_class="high",
            objectives=["obj1", "obj2"],
            workpacket={"id": "wp-123"},
        )
        d = ctx.to_dict()
        restored = ExecutorRuntimeContext.from_dict(d)
        assert restored.risk_class == "high"
        assert restored.objectives == ["obj1", "obj2"]
        assert restored.workpacket == {"id": "wp-123"}


class TestExecutorRequest:
    def test_auto_id(self):
        req = ExecutorRequest()
        assert req.request_id.startswith("exrq-")
        assert len(req.request_id) == 17

    def test_roundtrip(self):
        req = ExecutorRequest(
            execution_plan_id="plan-abc",
            executor_type="agent",
            risk_class="high",
            description="Test request",
        )
        d = req.to_dict()
        restored = ExecutorRequest.from_dict(d)
        assert restored.execution_plan_id == "plan-abc"
        assert restored.executor_type == "agent"
        assert restored.risk_class == "high"
        assert restored.description == "Test request"

    def test_defaults(self):
        req = ExecutorRequest()
        assert req.status == ExecutorRequestStatus.PENDING.value
        assert req.approval_state == ExecutorApprovalState.PENDING.value
        assert req.priority == "normal"


class TestExecutorArtifact:
    def test_auto_id(self):
        art = ExecutorArtifact()
        assert art.artifact_id.startswith("exart-")

    def test_roundtrip(self):
        art = ExecutorArtifact(
            artifact_type="report",
            name="output.json",
            content="{}",
        )
        d = art.to_dict()
        restored = ExecutorArtifact.from_dict(d)
        assert restored.artifact_type == "report"
        assert restored.name == "output.json"


class TestExecutorResult:
    def test_auto_id(self):
        result = ExecutorResult()
        assert result.result_id.startswith("exrs-")

    def test_roundtrip(self):
        result = ExecutorResult(
            request_id="req-123",
            executor_type="container",
            success=True,
            outcome="All good",
            artifacts=[{"name": "file.txt"}],
            errors=[],
            started_at=1000.0,
            completed_at=1005.0,
            duration_seconds=5.0,
        )
        d = result.to_dict()
        restored = ExecutorResult.from_dict(d)
        assert restored.success is True
        assert restored.outcome == "All good"
        assert restored.duration_seconds == 5.0
        assert len(restored.artifacts) == 1


class TestExecutorLifecycleEvent:
    def test_auto_id(self):
        evt = ExecutorLifecycleEvent()
        assert evt.event_id.startswith("exlce-")

    def test_roundtrip(self):
        evt = ExecutorLifecycleEvent(
            request_id="req-1",
            event_type="execution_started",
            summary="Started",
        )
        d = evt.to_dict()
        restored = ExecutorLifecycleEvent.from_dict(d)
        assert restored.request_id == "req-1"
        assert restored.event_type == "execution_started"


class TestExecutorRuntimeSnapshot:
    def test_auto_id(self):
        snap = ExecutorRuntimeSnapshot()
        assert snap.snapshot_id.startswith("exsnap-")

    def test_to_dict(self):
        snap = ExecutorRuntimeSnapshot(
            total_requests=10,
            active_count=2,
            completed_count=6,
            failed_count=2,
        )
        d = snap.to_dict()
        assert d["total_requests"] == 10
        assert d["active_count"] == 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Simulation Executor Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSimulationExecutor:
    def test_executor_type(self):
        sim = SimulationExecutor()
        assert sim.executor_type == "workstation"

    def test_validate_success(self):
        sim = SimulationExecutor()
        req = ExecutorRequest(execution_plan_id="plan-1", executor_type="agent")
        ok, reason = sim.validate(req)
        assert ok is True

    def test_validate_no_plan(self):
        sim = SimulationExecutor()
        req = ExecutorRequest(executor_type="agent")
        ok, reason = sim.validate(req)
        assert ok is False
        assert "plan_id" in reason

    def test_validate_no_type(self):
        sim = SimulationExecutor()
        req = ExecutorRequest(execution_plan_id="plan-1", executor_type="")
        ok, reason = sim.validate(req)
        assert ok is False

    def test_prepare(self):
        sim = SimulationExecutor()
        req = ExecutorRequest()
        ok, reason = sim.prepare(req)
        assert ok is True

    def test_execute(self):
        sim = SimulationExecutor()
        req = ExecutorRequest(
            execution_plan_id="plan-1",
            executor_type="workstation",
            description="Test exec",
        )
        result = sim.execute(req)
        assert result.success is True
        assert result.request_id == req.request_id
        assert len(result.artifacts) == 1
        assert result.duration_seconds >= 0

    def test_monitor(self):
        sim = SimulationExecutor()
        req = ExecutorRequest()
        mon = sim.monitor(req)
        assert mon["progress_pct"] == 100

    def test_cancel(self):
        sim = SimulationExecutor()
        req = ExecutorRequest()
        assert sim.cancel(req) is True

    def test_cleanup(self):
        sim = SimulationExecutor()
        req = ExecutorRequest()
        assert sim.cleanup(req) is True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Implementation Registry Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExecutorImplementationRegistry:
    def test_simulation_pre_registered(self):
        reg = ExecutorImplementationRegistry()
        assert reg.has("workstation")
        assert reg.has("agent")
        assert reg.has("container")
        assert reg.has("vps")
        assert reg.has("browser")
        assert reg.has("mobile")
        assert reg.has("external")

    def test_available_types(self):
        reg = ExecutorImplementationRegistry()
        types = reg.available_types()
        assert len(types) == 7

    def test_get(self):
        reg = ExecutorImplementationRegistry()
        impl = reg.get("workstation")
        assert impl is not None
        assert isinstance(impl, SimulationExecutor)

    def test_register_custom(self):
        reg = ExecutorImplementationRegistry()
        custom = SimulationExecutor()
        reg.register("custom_type", custom)
        assert reg.has("custom_type")
        assert reg.get("custom_type") is custom

    def test_unregister(self):
        reg = ExecutorImplementationRegistry()
        reg.register("temp_type", SimulationExecutor())
        assert reg.unregister("temp_type") is True
        assert reg.has("temp_type") is False

    def test_unregister_missing(self):
        reg = ExecutorImplementationRegistry()
        assert reg.unregister("nonexistent") is False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Request Store Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExecutorRequestStore:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = ExecutorRequestStore(self.tmpdir)

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_and_get(self):
        req = ExecutorRequest(execution_plan_id="plan-1")
        self.store.save(req)
        loaded = self.store.get(req.request_id)
        assert loaded is not None
        assert loaded.execution_plan_id == "plan-1"

    def test_get_missing(self):
        assert self.store.get("nonexistent") is None

    def test_all_requests(self):
        for i in range(3):
            self.store.save(ExecutorRequest(description=f"req-{i}"))
        assert len(self.store.all_requests()) == 3

    def test_by_status(self):
        r1 = ExecutorRequest(status=ExecutorRequestStatus.PENDING.value)
        r2 = ExecutorRequest(status=ExecutorRequestStatus.COMPLETED.value)
        self.store.save(r1)
        self.store.save(r2)
        pending = self.store.by_status(ExecutorRequestStatus.PENDING.value)
        assert len(pending) == 1

    def test_by_executor_type(self):
        r1 = ExecutorRequest(executor_type="agent")
        r2 = ExecutorRequest(executor_type="container")
        self.store.save(r1)
        self.store.save(r2)
        agents = self.store.by_executor_type("agent")
        assert len(agents) == 1

    def test_by_plan(self):
        r1 = ExecutorRequest(execution_plan_id="plan-A")
        r2 = ExecutorRequest(execution_plan_id="plan-B")
        self.store.save(r1)
        self.store.save(r2)
        assert len(self.store.by_plan("plan-A")) == 1

    def test_active(self):
        r1 = ExecutorRequest(status=ExecutorRequestStatus.EXECUTING.value)
        r2 = ExecutorRequest(status=ExecutorRequestStatus.COMPLETED.value)
        self.store.save(r1)
        self.store.save(r2)
        assert len(self.store.active()) == 1

    def test_completed(self):
        r = ExecutorRequest(status=ExecutorRequestStatus.COMPLETED.value)
        self.store.save(r)
        assert len(self.store.completed()) == 1

    def test_failed(self):
        r = ExecutorRequest(status=ExecutorRequestStatus.FAILED.value)
        self.store.save(r)
        assert len(self.store.failed()) == 1

    def test_history(self):
        for status in [
            ExecutorRequestStatus.COMPLETED.value,
            ExecutorRequestStatus.FAILED.value,
            ExecutorRequestStatus.CANCELLED.value,
        ]:
            self.store.save(ExecutorRequest(status=status))
        assert len(self.store.history()) == 3


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Result Store Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExecutorResultStore:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = ExecutorResultStore(self.tmpdir)

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_and_get(self):
        result = ExecutorResult(request_id="req-1", success=True)
        self.store.save(result)
        loaded = self.store.get(result.result_id)
        assert loaded is not None
        assert loaded.success is True

    def test_get_missing(self):
        assert self.store.get("nonexistent") is None

    def test_by_request(self):
        result = ExecutorResult(request_id="req-42")
        self.store.save(result)
        found = self.store.by_request("req-42")
        assert found is not None
        assert found.request_id == "req-42"

    def test_by_request_missing(self):
        assert self.store.by_request("no-such-req") is None

    def test_all_results(self):
        for i in range(3):
            self.store.save(ExecutorResult(request_id=f"req-{i}"))
        assert len(self.store.all_results()) == 3

    def test_successes_and_failures(self):
        self.store.save(ExecutorResult(success=True))
        self.store.save(ExecutorResult(success=False))
        assert len(self.store.successes()) == 1
        assert len(self.store.failures()) == 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Lifecycle Tracker Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExecutorLifecycleTracker:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tracker = ExecutorLifecycleTracker(
            os.path.join(self.tmpdir, "events.jsonl")
        )

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_record(self):
        evt = self.tracker.record("req-1", "execution_started", "Started")
        assert evt.request_id == "req-1"
        assert evt.event_type == "execution_started"

    def test_events_for_request(self):
        self.tracker.record("req-1", "started")
        self.tracker.record("req-2", "started")
        self.tracker.record("req-1", "completed")
        events = self.tracker.events_for_request("req-1")
        assert len(events) == 2

    def test_recent(self):
        for i in range(5):
            self.tracker.record(f"req-{i}", "started")
        recent = self.tracker.recent(3)
        assert len(recent) == 3

    def test_by_type(self):
        self.tracker.record("req-1", "started")
        self.tracker.record("req-2", "completed")
        self.tracker.record("req-3", "started")
        assert len(self.tracker.by_type("started")) == 2

    def test_persistence(self):
        self.tracker.record("req-1", "started")
        tracker2 = ExecutorLifecycleTracker(
            os.path.join(self.tmpdir, "events.jsonl")
        )
        assert len(tracker2.events_for_request("req-1")) == 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Governance Gate Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExecutorGovernanceGate:
    def test_approved_can_execute(self):
        req = ExecutorRequest(
            approval_state=ExecutorApprovalState.APPROVED.value,
            execution_plan_id="plan-1",
            risk_class="low",
        )
        ok, reason = ExecutorGovernanceGate.can_execute(req)
        assert ok is True

    def test_auto_approved_can_execute(self):
        req = ExecutorRequest(
            approval_state=ExecutorApprovalState.AUTO_APPROVED.value,
            execution_plan_id="plan-1",
            risk_class="low",
        )
        ok, reason = ExecutorGovernanceGate.can_execute(req)
        assert ok is True

    def test_pending_cannot_execute(self):
        req = ExecutorRequest(
            approval_state=ExecutorApprovalState.PENDING.value,
            execution_plan_id="plan-1",
        )
        ok, reason = ExecutorGovernanceGate.can_execute(req)
        assert ok is False

    def test_denied_cannot_execute(self):
        req = ExecutorRequest(
            approval_state=ExecutorApprovalState.DENIED.value,
            execution_plan_id="plan-1",
        )
        ok, reason = ExecutorGovernanceGate.can_execute(req)
        assert ok is False

    def test_high_risk_needs_explicit_approval(self):
        req = ExecutorRequest(
            approval_state=ExecutorApprovalState.AUTO_APPROVED.value,
            execution_plan_id="plan-1",
            risk_class="high",
        )
        ok, reason = ExecutorGovernanceGate.can_execute(req)
        assert ok is False
        assert "explicit approval" in reason

    def test_high_risk_with_explicit_approval(self):
        req = ExecutorRequest(
            approval_state=ExecutorApprovalState.APPROVED.value,
            execution_plan_id="plan-1",
            risk_class="high",
        )
        ok, reason = ExecutorGovernanceGate.can_execute(req)
        assert ok is True

    def test_critical_risk_needs_explicit(self):
        req = ExecutorRequest(
            approval_state=ExecutorApprovalState.AUTO_APPROVED.value,
            execution_plan_id="plan-1",
            risk_class="critical",
        )
        ok, reason = ExecutorGovernanceGate.can_execute(req)
        assert ok is False

    def test_no_plan_cannot_execute(self):
        req = ExecutorRequest(
            approval_state=ExecutorApprovalState.APPROVED.value,
            execution_plan_id="",
            risk_class="low",
        )
        ok, reason = ExecutorGovernanceGate.can_execute(req)
        assert ok is False

    def test_unknown_risk_defaults_high(self):
        req = ExecutorRequest(
            approval_state=ExecutorApprovalState.AUTO_APPROVED.value,
            execution_plan_id="plan-1",
            risk_class="unknown_risk",
        )
        ok, reason = ExecutorGovernanceGate.can_execute(req)
        assert ok is False

    def test_auto_approve_eligible_low(self):
        assert ExecutorGovernanceGate.auto_approve_eligible(
            ExecutorRequest(risk_class="low")
        ) is True

    def test_auto_approve_eligible_negligible(self):
        assert ExecutorGovernanceGate.auto_approve_eligible(
            ExecutorRequest(risk_class="negligible")
        ) is True

    def test_auto_approve_not_eligible_medium(self):
        assert ExecutorGovernanceGate.auto_approve_eligible(
            ExecutorRequest(risk_class="medium")
        ) is False

    def test_requires_approval_medium(self):
        assert ExecutorGovernanceGate.requires_approval("medium") is True

    def test_requires_approval_low(self):
        assert ExecutorGovernanceGate.requires_approval("low") is False

    def test_authority_primary(self):
        req = ExecutorRequest(risk_class="critical")
        ok, _ = ExecutorGovernanceGate.validate_authority(req, "primary")
        assert ok is True

    def test_authority_secondary_critical(self):
        req = ExecutorRequest(risk_class="critical")
        ok, _ = ExecutorGovernanceGate.validate_authority(req, "secondary")
        assert ok is False

    def test_authority_secondary_low(self):
        req = ExecutorRequest(risk_class="low")
        ok, _ = ExecutorGovernanceGate.validate_authority(req, "secondary")
        assert ok is True

    def test_profile_restrictions_blocked(self):
        req = ExecutorRequest(executor_type="browser")
        ok, _ = ExecutorGovernanceGate.validate_profile_restrictions(
            req, {"blocked_executor_types": ["browser"]}
        )
        assert ok is False

    def test_profile_restrictions_allowed(self):
        req = ExecutorRequest(executor_type="agent")
        ok, _ = ExecutorGovernanceGate.validate_profile_restrictions(
            req, {"blocked_executor_types": ["browser"]}
        )
        assert ok is True

    def test_profile_restrictions_none(self):
        req = ExecutorRequest()
        ok, _ = ExecutorGovernanceGate.validate_profile_restrictions(req)
        assert ok is True

    def test_session_restrictions_at_max(self):
        req = ExecutorRequest()
        ok, _ = ExecutorGovernanceGate.validate_session_restrictions(
            req, {"max_concurrent_executions": 5, "current_execution_count": 5}
        )
        assert ok is False

    def test_session_restrictions_under_max(self):
        req = ExecutorRequest()
        ok, _ = ExecutorGovernanceGate.validate_session_restrictions(
            req, {"max_concurrent_executions": 5, "current_execution_count": 3}
        )
        assert ok is True

    def test_session_restrictions_none(self):
        req = ExecutorRequest()
        ok, _ = ExecutorGovernanceGate.validate_session_restrictions(req)
        assert ok is True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Executor Runtime Integration Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExecutorRuntime:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.runtime = ExecutorRuntime(data_dir=self.tmpdir)

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_create_request(self):
        req = self.runtime.create_request(
            execution_plan_id="plan-1",
            executor_type="workstation",
            description="Test",
        )
        assert req.request_id.startswith("exrq-")
        assert req.execution_plan_id == "plan-1"
        assert req.approval_state == ExecutorApprovalState.AUTO_APPROVED.value

    def test_create_request_high_risk(self):
        req = self.runtime.create_request(
            execution_plan_id="plan-1",
            executor_type="workstation",
            risk_class="high",
        )
        assert req.approval_state == ExecutorApprovalState.PENDING.value

    def test_approve_request(self):
        req = self.runtime.create_request(
            execution_plan_id="plan-1",
            executor_type="workstation",
            risk_class="high",
        )
        approved = self.runtime.approve_request(req.request_id)
        assert approved is not None
        assert approved.approval_state == ExecutorApprovalState.APPROVED.value

    def test_deny_request(self):
        req = self.runtime.create_request(
            execution_plan_id="plan-1",
            executor_type="workstation",
            risk_class="high",
        )
        denied = self.runtime.deny_request(req.request_id, "Not safe")
        assert denied is not None
        assert denied.approval_state == ExecutorApprovalState.DENIED.value
        assert denied.status == ExecutorRequestStatus.CANCELLED.value

    def test_full_lifecycle_low_risk(self):
        req = self.runtime.create_request(
            execution_plan_id="plan-1",
            executor_type="workstation",
            description="Simulation test",
        )
        result = self.runtime.run_lifecycle(req.request_id)
        assert result is not None
        assert result.success is True
        assert len(result.artifacts) == 1

        loaded = self.runtime.get_request(req.request_id)
        assert loaded.status == ExecutorRequestStatus.CLEANED_UP.value

    def test_full_lifecycle_high_risk_unapproved(self):
        req = self.runtime.create_request(
            execution_plan_id="plan-1",
            executor_type="workstation",
            risk_class="high",
        )
        result = self.runtime.run_lifecycle(req.request_id)
        assert result is None

        loaded = self.runtime.get_request(req.request_id)
        assert loaded.status == ExecutorRequestStatus.FAILED.value

    def test_full_lifecycle_high_risk_approved(self):
        req = self.runtime.create_request(
            execution_plan_id="plan-1",
            executor_type="workstation",
            risk_class="high",
        )
        self.runtime.approve_request(req.request_id)
        result = self.runtime.run_lifecycle(req.request_id)
        assert result is not None
        assert result.success is True

    def test_cancel_request(self):
        req = self.runtime.create_request(
            execution_plan_id="plan-1",
            executor_type="workstation",
        )
        cancelled = self.runtime.cancel_request(req.request_id)
        assert cancelled is not None
        assert cancelled.status == ExecutorRequestStatus.CANCELLED.value

    def test_cancel_completed_request(self):
        req = self.runtime.create_request(
            execution_plan_id="plan-1",
            executor_type="workstation",
        )
        self.runtime.run_lifecycle(req.request_id)
        cancelled = self.runtime.cancel_request(req.request_id)
        assert cancelled is None

    def test_monitor_request(self):
        req = self.runtime.create_request(
            execution_plan_id="plan-1",
            executor_type="workstation",
        )
        mon = self.runtime.monitor_request(req.request_id)
        assert "progress_pct" in mon

    def test_monitor_missing(self):
        mon = self.runtime.monitor_request("nonexistent")
        assert "error" in mon

    def test_get_result_for_request(self):
        req = self.runtime.create_request(
            execution_plan_id="plan-1",
            executor_type="workstation",
        )
        self.runtime.run_lifecycle(req.request_id)
        result = self.runtime.result_for_request(req.request_id)
        assert result is not None
        assert result.success is True

    def test_lifecycle_events_recorded(self):
        req = self.runtime.create_request(
            execution_plan_id="plan-1",
            executor_type="workstation",
        )
        self.runtime.run_lifecycle(req.request_id)
        events = self.runtime.lifecycle_for_request(req.request_id)
        event_types = [e.event_type for e in events]
        assert ExecutorEventType.REQUEST_CREATED.value in event_types
        assert ExecutorEventType.VALIDATION_STARTED.value in event_types
        assert ExecutorEventType.VALIDATION_PASSED.value in event_types
        assert ExecutorEventType.PREPARATION_STARTED.value in event_types
        assert ExecutorEventType.PREPARATION_COMPLETED.value in event_types
        assert ExecutorEventType.EXECUTION_STARTED.value in event_types
        assert ExecutorEventType.EXECUTION_COMPLETED.value in event_types
        assert ExecutorEventType.CLEANUP_STARTED.value in event_types
        assert ExecutorEventType.CLEANUP_COMPLETED.value in event_types

    def test_queries_by_status(self):
        self.runtime.create_request(
            execution_plan_id="plan-1", executor_type="workstation",
        )
        # auto-approved low-risk: approval_state=auto_approved but status still pending
        pending = self.runtime.requests_by_status(ExecutorRequestStatus.PENDING.value)
        assert len(pending) == 1

    def test_queries_by_type(self):
        self.runtime.create_request(
            execution_plan_id="plan-1", executor_type="agent",
        )
        agents = self.runtime.requests_by_type("agent")
        assert len(agents) == 1

    def test_active_requests(self):
        assert len(self.runtime.active_requests()) == 0

    def test_request_history(self):
        req = self.runtime.create_request(
            execution_plan_id="plan-1", executor_type="workstation",
        )
        self.runtime.run_lifecycle(req.request_id)
        history = self.runtime.request_history()
        assert len(history) >= 1

    def test_all_results(self):
        req = self.runtime.create_request(
            execution_plan_id="plan-1", executor_type="workstation",
        )
        self.runtime.run_lifecycle(req.request_id)
        results = self.runtime.all_results()
        assert len(results) == 1

    def test_register_custom_executor(self):
        self.runtime.register_executor("custom", SimulationExecutor())
        assert self.runtime.has_executor("custom")
        assert "custom" in self.runtime.registered_executor_types()

    def test_unregister_executor(self):
        self.runtime.register_executor("temp", SimulationExecutor())
        assert self.runtime.unregister_executor("temp") is True
        assert self.runtime.has_executor("temp") is False

    def test_assemble_context(self):
        ctx = self.runtime.assemble_context(
            workpacket={"id": "wp-1"},
            risk_class="medium",
        )
        assert ctx.risk_class == "medium"
        assert ctx.workpacket == {"id": "wp-1"}

    def test_snapshot(self):
        self.runtime.create_request(
            execution_plan_id="plan-1", executor_type="workstation",
        )
        snap = self.runtime.snapshot()
        assert snap.total_requests == 1
        assert snap.registered_executors == 7

    def test_multiple_requests_lifecycle(self):
        for i in range(3):
            req = self.runtime.create_request(
                execution_plan_id=f"plan-{i}",
                executor_type="workstation",
            )
            self.runtime.run_lifecycle(req.request_id)
        assert len(self.runtime.all_results()) == 3
        snap = self.runtime.snapshot()
        assert snap.total_requests == 3
        # successful runs end in cleaned_up status, not completed
        assert snap.by_status.get("cleaned_up", 0) == 3

    def test_profile_and_session_binding(self):
        req = self.runtime.create_request(
            execution_plan_id="plan-1",
            executor_type="workstation",
            profile_id="engineer",
            session_id="sess-abc",
        )
        loaded = self.runtime.get_request(req.request_id)
        assert loaded.profile_id == "engineer"
        assert loaded.session_id == "sess-abc"

    def test_request_not_found(self):
        assert self.runtime.get_request("nonexistent") is None
        result = self.runtime.run_lifecycle("nonexistent")
        assert result is None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Singleton Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSingleton:
    def setup_method(self):
        reset_executor_runtime()

    def teardown_method(self):
        reset_executor_runtime()

    def test_singleton_returns_same(self):
        a = get_executor_runtime()
        b = get_executor_runtime()
        assert a is b

    def test_reset_creates_new(self):
        a = get_executor_runtime()
        reset_executor_runtime()
        b = get_executor_runtime()
        assert a is not b


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Acceptance Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestAcceptance:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.runtime = ExecutorRuntime(data_dir=self.tmpdir)

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_full_scenario(self):
        """Acceptance: full lifecycle from request to result."""
        req = self.runtime.create_request(
            execution_plan_id="plan-accept-1",
            executor_type="workstation",
            risk_class="low",
            description="Acceptance test execution",
            profile_id="engineer",
            session_id="sess-1",
            priority="normal",
            workpacket={"id": "wp-accept-1", "title": "Test packet"},
        )
        assert req.approval_state == ExecutorApprovalState.AUTO_APPROVED.value

        result = self.runtime.run_lifecycle(req.request_id)
        assert result is not None
        assert result.success is True
        assert len(result.artifacts) >= 1
        assert result.duration_seconds >= 0

        loaded_req = self.runtime.get_request(req.request_id)
        assert loaded_req.status == ExecutorRequestStatus.CLEANED_UP.value

        loaded_result = self.runtime.result_for_request(req.request_id)
        assert loaded_result is not None
        assert loaded_result.success is True

        events = self.runtime.lifecycle_for_request(req.request_id)
        assert len(events) >= 9

        snap = self.runtime.snapshot()
        assert snap.total_requests >= 1

    def test_high_risk_approval_flow(self):
        """Acceptance: high-risk needs approval before execution."""
        req = self.runtime.create_request(
            execution_plan_id="plan-hr",
            executor_type="agent",
            risk_class="high",
        )
        assert req.approval_state == ExecutorApprovalState.PENDING.value

        result = self.runtime.run_lifecycle(req.request_id)
        assert result is None

        self.runtime.approve_request(req.request_id)
        result = self.runtime.run_lifecycle(req.request_id)
        assert result is not None
        assert result.success is True

    def test_denied_request(self):
        """Acceptance: denied requests don't execute."""
        req = self.runtime.create_request(
            execution_plan_id="plan-deny",
            executor_type="container",
            risk_class="high",
        )
        self.runtime.deny_request(req.request_id, "Not allowed")
        result = self.runtime.run_lifecycle(req.request_id)
        assert result is None

    def test_all_executor_types(self):
        """Acceptance: every executor type can run through simulation."""
        for etype in ExecutorType:
            req = self.runtime.create_request(
                execution_plan_id=f"plan-{etype.value}",
                executor_type=etype.value,
            )
            result = self.runtime.run_lifecycle(req.request_id)
            assert result is not None
            assert result.success is True

    def test_cancellation(self):
        """Acceptance: cancellation works and prevents execution."""
        req = self.runtime.create_request(
            execution_plan_id="plan-cancel",
            executor_type="workstation",
        )
        self.runtime.cancel_request(req.request_id)
        loaded = self.runtime.get_request(req.request_id)
        assert loaded.status == ExecutorRequestStatus.CANCELLED.value

    def test_failure_preservation(self):
        """Acceptance: failed requests preserve failure reason."""
        req = self.runtime.create_request(
            execution_plan_id="",  # empty plan → validation failure
            executor_type="workstation",
        )
        result = self.runtime.run_lifecycle(req.request_id)
        assert result is None
        loaded = self.runtime.get_request(req.request_id)
        assert loaded.status == ExecutorRequestStatus.FAILED.value
        assert "failure_reason" in loaded.metadata

    def test_no_automation_methods(self):
        """Acceptance: executor contract has no real automation."""
        sim = SimulationExecutor()
        import inspect
        source = inspect.getsource(SimulationExecutor)
        assert "subprocess" not in source
        assert "os.system" not in source
        assert "popen" not in source.lower()
        assert "winreg" not in source

    def test_session_profile_binding(self):
        """Acceptance: requests bind to session and profile."""
        req = self.runtime.create_request(
            execution_plan_id="plan-bind",
            executor_type="workstation",
            profile_id="engineer",
            session_id="sess-desktop-1",
        )
        loaded = self.runtime.get_request(req.request_id)
        assert loaded.profile_id == "engineer"
        assert loaded.session_id == "sess-desktop-1"

    def test_all_statuses_reachable(self):
        """Acceptance: all terminal statuses are reachable."""
        r1 = self.runtime.create_request(
            execution_plan_id="plan-1", executor_type="workstation",
        )
        self.runtime.run_lifecycle(r1.request_id)
        assert self.runtime.get_request(r1.request_id).status == ExecutorRequestStatus.CLEANED_UP.value

        r2 = self.runtime.create_request(
            execution_plan_id="", executor_type="workstation",
        )
        self.runtime.run_lifecycle(r2.request_id)
        assert self.runtime.get_request(r2.request_id).status == ExecutorRequestStatus.FAILED.value

        r3 = self.runtime.create_request(
            execution_plan_id="plan-3", executor_type="workstation",
        )
        self.runtime.cancel_request(r3.request_id)
        assert self.runtime.get_request(r3.request_id).status == ExecutorRequestStatus.CANCELLED.value

    def test_snapshot_accuracy(self):
        """Acceptance: snapshot counts match actual state."""
        for i in range(5):
            req = self.runtime.create_request(
                execution_plan_id=f"plan-{i}",
                executor_type="workstation",
            )
            if i < 3:
                self.runtime.run_lifecycle(req.request_id)
            elif i == 3:
                self.runtime.cancel_request(req.request_id)

        snap = self.runtime.snapshot()
        assert snap.total_requests == 5
        assert snap.registered_executors == 7

    def test_lifecycle_replayable(self):
        """Acceptance: lifecycle events form a complete, ordered trace."""
        req = self.runtime.create_request(
            execution_plan_id="plan-replay",
            executor_type="workstation",
        )
        self.runtime.run_lifecycle(req.request_id)
        events = self.runtime.lifecycle_for_request(req.request_id)

        timestamps = [e.timestamp for e in events]
        assert timestamps == sorted(timestamps)

        types = [e.event_type for e in events]
        assert types[0] == ExecutorEventType.REQUEST_CREATED.value
        assert ExecutorEventType.CLEANUP_COMPLETED.value in types
