"""Tests for Phase 13: Execution Coordinator Runtime."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
import unittest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from substrate.organism.execution_coordinator import (
    CoordinatorApprovalState,
    CoordinatorExecutionPlan,
    CrossRuntimeCompositor,
    ExecutionCoordinator,
    ExecutionCoordinatorSnapshot,
    ExecutionLifecycleTracker,
    ExecutionPlanStatus,
    ExecutionPriority,
    ExecutionQueue,
    ExecutionTargetType,
    ExecutionTiming,
    ExecutorDefinition,
    ExecutorRegistry,
    GovernanceGate,
    LifecycleEvent,
    LifecycleEventType,
    PlanStore,
    get_execution_coordinator,
    reset_execution_coordinator,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Enum Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExecutionPlanStatus(unittest.TestCase):
    def test_all_values(self):
        vals = [e.value for e in ExecutionPlanStatus]
        self.assertEqual(len(vals), 8)
        self.assertIn("drafted", vals)
        self.assertIn("approved", vals)
        self.assertIn("queued", vals)
        self.assertIn("dispatched", vals)
        self.assertIn("executing", vals)
        self.assertIn("completed", vals)
        self.assertIn("failed", vals)
        self.assertIn("cancelled", vals)


class TestExecutionTargetType(unittest.TestCase):
    def test_all_values(self):
        vals = [e.value for e in ExecutionTargetType]
        self.assertEqual(len(vals), 7)
        self.assertIn("workstation", vals)
        self.assertIn("agent", vals)
        self.assertIn("vps", vals)
        self.assertIn("container", vals)
        self.assertIn("browser", vals)
        self.assertIn("mobile", vals)
        self.assertIn("external", vals)


class TestExecutionTiming(unittest.TestCase):
    def test_all_values(self):
        vals = [e.value for e in ExecutionTiming]
        self.assertEqual(len(vals), 4)
        self.assertIn("synchronous", vals)
        self.assertIn("asynchronous", vals)
        self.assertIn("background", vals)
        self.assertIn("scheduled", vals)


class TestExecutionPriority(unittest.TestCase):
    def test_all_values(self):
        vals = [e.value for e in ExecutionPriority]
        self.assertEqual(len(vals), 5)
        self.assertIn("critical", vals)
        self.assertIn("high", vals)
        self.assertIn("normal", vals)
        self.assertIn("low", vals)
        self.assertIn("background", vals)


class TestCoordinatorApprovalState(unittest.TestCase):
    def test_all_values(self):
        vals = [e.value for e in CoordinatorApprovalState]
        self.assertEqual(len(vals), 4)
        self.assertIn("pending", vals)
        self.assertIn("approved", vals)
        self.assertIn("denied", vals)
        self.assertIn("expired", vals)


class TestLifecycleEventType(unittest.TestCase):
    def test_all_values(self):
        vals = [e.value for e in LifecycleEventType]
        self.assertEqual(len(vals), 11)
        self.assertIn("plan_created", vals)
        self.assertIn("plan_approved", vals)
        self.assertIn("execution_completed", vals)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Model Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCoordinatorExecutionPlan(unittest.TestCase):
    def test_auto_id(self):
        plan = CoordinatorExecutionPlan()
        self.assertTrue(plan.execution_plan_id.startswith("expl-"))

    def test_roundtrip(self):
        plan = CoordinatorExecutionPlan(
            source_workpacket_id="wp-123",
            target_executor="workstation",
            profile_id="engineer",
            session_id="sess-abc",
            priority="high",
            risk_class="medium",
            description="Test plan",
        )
        d = plan.to_dict()
        restored = CoordinatorExecutionPlan.from_dict(d)
        self.assertEqual(restored.source_workpacket_id, "wp-123")
        self.assertEqual(restored.target_executor, "workstation")
        self.assertEqual(restored.profile_id, "engineer")
        self.assertEqual(restored.session_id, "sess-abc")
        self.assertEqual(restored.priority, "high")
        self.assertEqual(restored.risk_class, "medium")
        self.assertEqual(restored.description, "Test plan")

    def test_defaults(self):
        plan = CoordinatorExecutionPlan()
        self.assertEqual(plan.status, "drafted")
        self.assertEqual(plan.approval_state, "pending")
        self.assertEqual(plan.priority, "normal")
        self.assertEqual(plan.execution_mode, "asynchronous")
        self.assertEqual(plan.risk_class, "low")


class TestExecutorDefinition(unittest.TestCase):
    def test_auto_id(self):
        ex = ExecutorDefinition()
        self.assertTrue(ex.executor_id.startswith("extr-"))

    def test_roundtrip(self):
        ex = ExecutorDefinition(
            executor_type="agent",
            name="Test Agent",
            capabilities=["code", "research"],
        )
        d = ex.to_dict()
        restored = ExecutorDefinition.from_dict(d)
        self.assertEqual(restored.executor_type, "agent")
        self.assertEqual(restored.name, "Test Agent")
        self.assertEqual(restored.capabilities, ["code", "research"])


class TestLifecycleEvent(unittest.TestCase):
    def test_auto_id(self):
        e = LifecycleEvent()
        self.assertTrue(e.event_id.startswith("lcevt-"))

    def test_roundtrip(self):
        e = LifecycleEvent(
            execution_plan_id="expl-abc",
            event_type="plan_created",
            summary="Test event",
            details={"key": "value"},
        )
        d = e.to_dict()
        restored = LifecycleEvent.from_dict(d)
        self.assertEqual(restored.execution_plan_id, "expl-abc")
        self.assertEqual(restored.event_type, "plan_created")
        self.assertEqual(restored.details["key"], "value")


class TestExecutionCoordinatorSnapshot(unittest.TestCase):
    def test_auto_id(self):
        snap = ExecutionCoordinatorSnapshot()
        self.assertTrue(snap.snapshot_id.startswith("ecsnap-"))

    def test_to_dict(self):
        snap = ExecutionCoordinatorSnapshot(
            total_plans=5,
            queue_depth=2,
            active_count=1,
            executor_count=7,
            awaiting_approval=2,
        )
        d = snap.to_dict()
        self.assertEqual(d["total_plans"], 5)
        self.assertEqual(d["queue_depth"], 2)
        self.assertEqual(d["active_count"], 1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Executor Registry Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExecutorRegistry(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store_path = os.path.join(self.tmpdir, "executors.json")
        self.reg = ExecutorRegistry(self.store_path)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_register_and_get(self):
        ex = ExecutorDefinition(executor_type="agent", name="Test")
        self.reg.register(ex)
        got = self.reg.get(ex.executor_id)
        self.assertIsNotNone(got)
        self.assertEqual(got.name, "Test")

    def test_unregister(self):
        ex = ExecutorDefinition(executor_type="vps")
        self.reg.register(ex)
        self.assertTrue(self.reg.unregister(ex.executor_id))
        self.assertIsNone(self.reg.get(ex.executor_id))

    def test_by_type(self):
        self.reg.register(ExecutorDefinition(executor_type="agent"))
        self.reg.register(ExecutorDefinition(executor_type="agent"))
        self.reg.register(ExecutorDefinition(executor_type="vps"))
        self.assertEqual(len(self.reg.by_type("agent")), 2)

    def test_availability(self):
        ex = ExecutorDefinition(executor_type="container")
        self.reg.register(ex)
        self.assertEqual(len(self.reg.available()), 1)
        self.reg.set_availability(ex.executor_id, False)
        self.assertEqual(len(self.reg.available()), 0)

    def test_seed_defaults(self):
        defaults = self.reg.seed_defaults()
        self.assertEqual(len(defaults), 7)
        types = {d.executor_type for d in defaults}
        self.assertEqual(types, {t.value for t in ExecutionTargetType})

    def test_seed_idempotent(self):
        self.reg.seed_defaults()
        self.reg.seed_defaults()
        self.assertEqual(len(self.reg.all()), 7)

    def test_persistence(self):
        self.reg.register(ExecutorDefinition(executor_type="vps", name="Persist"))
        reg2 = ExecutorRegistry(self.store_path)
        self.assertEqual(len(reg2.all()), 1)
        self.assertEqual(reg2.all()[0].name, "Persist")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Execution Queue Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExecutionQueue(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store_path = os.path.join(self.tmpdir, "queue.json")
        self.queue = ExecutionQueue(self.store_path)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_enqueue_dequeue(self):
        plan = CoordinatorExecutionPlan(source_workpacket_id="wp-1")
        self.queue.enqueue(plan)
        self.assertEqual(self.queue.depth, 1)
        got = self.queue.dequeue()
        self.assertIsNotNone(got)
        self.assertEqual(got.source_workpacket_id, "wp-1")
        self.assertEqual(self.queue.depth, 0)

    def test_priority_ordering(self):
        low = CoordinatorExecutionPlan(priority="low", source_workpacket_id="low")
        high = CoordinatorExecutionPlan(priority="high", source_workpacket_id="high")
        critical = CoordinatorExecutionPlan(priority="critical", source_workpacket_id="critical")
        self.queue.enqueue(low)
        self.queue.enqueue(high)
        self.queue.enqueue(critical)
        first = self.queue.dequeue()
        self.assertEqual(first.source_workpacket_id, "critical")
        second = self.queue.dequeue()
        self.assertEqual(second.source_workpacket_id, "high")

    def test_cancel(self):
        plan = CoordinatorExecutionPlan(source_workpacket_id="wp-cancel")
        self.queue.enqueue(plan)
        cancelled = self.queue.cancel(plan.execution_plan_id)
        self.assertIsNotNone(cancelled)
        self.assertEqual(cancelled.status, "cancelled")
        self.assertEqual(self.queue.depth, 0)

    def test_reprioritize(self):
        p1 = CoordinatorExecutionPlan(priority="low", source_workpacket_id="p1")
        p2 = CoordinatorExecutionPlan(priority="normal", source_workpacket_id="p2")
        self.queue.enqueue(p1)
        self.queue.enqueue(p2)
        self.queue.reprioritize(p1.execution_plan_id, "critical")
        first = self.queue.dequeue()
        self.assertEqual(first.source_workpacket_id, "p1")

    def test_peek(self):
        plan = CoordinatorExecutionPlan(source_workpacket_id="wp-peek")
        self.queue.enqueue(plan)
        peeked = self.queue.peek()
        self.assertEqual(peeked.source_workpacket_id, "wp-peek")
        self.assertEqual(self.queue.depth, 1)

    def test_empty_dequeue(self):
        self.assertIsNone(self.queue.dequeue())

    def test_inspect(self):
        self.queue.enqueue(CoordinatorExecutionPlan(source_workpacket_id="a"))
        self.queue.enqueue(CoordinatorExecutionPlan(source_workpacket_id="b"))
        items = self.queue.inspect()
        self.assertEqual(len(items), 2)

    def test_persistence(self):
        self.queue.enqueue(CoordinatorExecutionPlan(source_workpacket_id="persist"))
        q2 = ExecutionQueue(self.store_path)
        self.assertEqual(q2.depth, 1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Lifecycle Tracker Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExecutionLifecycleTracker(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store_path = os.path.join(self.tmpdir, "events.jsonl")
        self.tracker = ExecutionLifecycleTracker(self.store_path)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_record_and_retrieve(self):
        self.tracker.record("expl-1", "plan_created", summary="Created")
        events = self.tracker.events_for_plan("expl-1")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "plan_created")

    def test_recent(self):
        for i in range(5):
            self.tracker.record(f"expl-{i}", "plan_created")
        recent = self.tracker.recent(3)
        self.assertEqual(len(recent), 3)

    def test_by_type(self):
        self.tracker.record("expl-1", "plan_created")
        self.tracker.record("expl-1", "plan_approved")
        self.tracker.record("expl-2", "plan_created")
        created = self.tracker.by_type("plan_created")
        self.assertEqual(len(created), 2)

    def test_persistence(self):
        self.tracker.record("expl-p", "plan_queued", summary="Queued")
        t2 = ExecutionLifecycleTracker(self.store_path)
        self.assertEqual(len(t2.all_events()), 1)
        self.assertEqual(t2.all_events()[0].summary, "Queued")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Governance Gate Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestGovernanceGate(unittest.TestCase):
    def test_low_risk_auto_approve(self):
        plan = CoordinatorExecutionPlan(risk_class="low")
        self.assertTrue(GovernanceGate.auto_approve_eligible(plan))
        self.assertFalse(GovernanceGate.requires_approval(plan))

    def test_negligible_risk_auto_approve(self):
        plan = CoordinatorExecutionPlan(risk_class="negligible")
        self.assertTrue(GovernanceGate.auto_approve_eligible(plan))

    def test_canonical_plan_lineage_never_auto_approved(self):
        """Wave 2: a coordinator plan carrying canonical Wave 1/2 lineage
        (plan_record_id or execution_authorization_ref) can NEVER be
        auto-approved through the coordinator — its authorization is the HUD
        execution_authorization Decision. Fail closed even at low/negligible risk."""
        by_plan = CoordinatorExecutionPlan(
            risk_class="low", metadata={"plan_record_id": "opr-1"}
        )
        self.assertFalse(GovernanceGate.auto_approve_eligible(by_plan))
        by_auth = CoordinatorExecutionPlan(
            risk_class="negligible",
            metadata={"execution_authorization_ref": "objective_plan:opr-1:execution_authorization:v1"},
        )
        self.assertFalse(GovernanceGate.auto_approve_eligible(by_auth))
        # A plain low-risk plan (no canonical lineage) still auto-approves.
        plain = CoordinatorExecutionPlan(risk_class="low")
        self.assertTrue(GovernanceGate.auto_approve_eligible(plain))

    def test_medium_risk_requires_approval(self):
        plan = CoordinatorExecutionPlan(risk_class="medium")
        self.assertTrue(GovernanceGate.requires_approval(plan))
        self.assertFalse(GovernanceGate.auto_approve_eligible(plan))

    def test_high_risk_requires_approval(self):
        plan = CoordinatorExecutionPlan(risk_class="high")
        self.assertTrue(GovernanceGate.requires_approval(plan))

    def test_critical_risk_requires_approval(self):
        plan = CoordinatorExecutionPlan(risk_class="critical")
        self.assertTrue(GovernanceGate.requires_approval(plan))

    def test_can_dispatch_approved(self):
        plan = CoordinatorExecutionPlan(
            risk_class="medium",
            approval_state="approved",
            status="queued",
        )
        can, reason = GovernanceGate.can_dispatch(plan)
        self.assertTrue(can)

    def test_cannot_dispatch_unapproved_medium(self):
        plan = CoordinatorExecutionPlan(
            risk_class="medium",
            approval_state="pending",
            status="drafted",
        )
        can, reason = GovernanceGate.can_dispatch(plan)
        self.assertFalse(can)
        self.assertIn("approval required", reason)

    def test_cannot_dispatch_denied(self):
        plan = CoordinatorExecutionPlan(
            risk_class="low",
            approval_state="denied",
        )
        can, reason = GovernanceGate.can_dispatch(plan)
        self.assertFalse(can)

    def test_cannot_dispatch_cancelled(self):
        plan = CoordinatorExecutionPlan(status="cancelled")
        can, reason = GovernanceGate.can_dispatch(plan)
        self.assertFalse(can)

    def test_cannot_dispatch_completed(self):
        plan = CoordinatorExecutionPlan(status="completed")
        can, reason = GovernanceGate.can_dispatch(plan)
        self.assertFalse(can)

    def test_can_dispatch_low_risk_pending(self):
        plan = CoordinatorExecutionPlan(
            risk_class="low",
            approval_state="pending",
            status="drafted",
        )
        can, _ = GovernanceGate.can_dispatch(plan)
        self.assertTrue(can)

    def test_unknown_risk_requires_approval(self):
        plan = CoordinatorExecutionPlan(risk_class="unknown")
        self.assertTrue(GovernanceGate.requires_approval(plan))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Plan Store Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestPlanStore(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = PlanStore(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_save_and_get(self):
        plan = CoordinatorExecutionPlan(source_workpacket_id="wp-1")
        self.store.save(plan)
        got = self.store.get(plan.execution_plan_id)
        self.assertIsNotNone(got)
        self.assertEqual(got.source_workpacket_id, "wp-1")

    def test_by_status(self):
        self.store.save(CoordinatorExecutionPlan(status="drafted"))
        self.store.save(CoordinatorExecutionPlan(status="drafted"))
        self.store.save(CoordinatorExecutionPlan(status="completed"))
        self.assertEqual(len(self.store.by_status("drafted")), 2)

    def test_by_workpacket(self):
        self.store.save(CoordinatorExecutionPlan(source_workpacket_id="wp-a"))
        self.store.save(CoordinatorExecutionPlan(source_workpacket_id="wp-a"))
        self.store.save(CoordinatorExecutionPlan(source_workpacket_id="wp-b"))
        self.assertEqual(len(self.store.by_workpacket("wp-a")), 2)

    def test_by_session(self):
        self.store.save(CoordinatorExecutionPlan(session_id="sess-1"))
        self.store.save(CoordinatorExecutionPlan(session_id="sess-2"))
        self.assertEqual(len(self.store.by_session("sess-1")), 1)

    def test_by_profile(self):
        self.store.save(CoordinatorExecutionPlan(profile_id="engineer"))
        self.store.save(CoordinatorExecutionPlan(profile_id="founder"))
        self.assertEqual(len(self.store.by_profile("engineer")), 1)

    def test_awaiting_approval(self):
        self.store.save(CoordinatorExecutionPlan(
            approval_state="pending", status="drafted"
        ))
        self.store.save(CoordinatorExecutionPlan(
            approval_state="approved", status="approved"
        ))
        self.assertEqual(len(self.store.awaiting_approval()), 1)

    def test_active(self):
        self.store.save(CoordinatorExecutionPlan(status="executing"))
        self.store.save(CoordinatorExecutionPlan(status="dispatched"))
        self.store.save(CoordinatorExecutionPlan(status="completed"))
        self.assertEqual(len(self.store.active()), 2)

    def test_history(self):
        self.store.save(CoordinatorExecutionPlan(
            status="completed", completed_at=time.time()
        ))
        self.store.save(CoordinatorExecutionPlan(
            status="failed", failed_at=time.time()
        ))
        self.store.save(CoordinatorExecutionPlan(status="drafted"))
        self.assertEqual(len(self.store.history()), 2)

    def test_persistence(self):
        self.store.save(CoordinatorExecutionPlan(
            source_workpacket_id="persist-test"
        ))
        store2 = PlanStore(self.tmpdir)
        self.assertEqual(len(store2.all_plans()), 1)
        self.assertEqual(store2.all_plans()[0].source_workpacket_id, "persist-test")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Execution Coordinator Integration Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExecutionCoordinator(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.coord = ExecutionCoordinator(data_dir=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_create_plan_low_risk_auto_approved(self):
        plan = self.coord.create_plan(
            "wp-1", "workstation", risk_class="low"
        )
        self.assertEqual(plan.approval_state, "approved")
        self.assertEqual(plan.status, "drafted")

    def test_create_plan_medium_risk_pending(self):
        plan = self.coord.create_plan(
            "wp-2", "agent", risk_class="medium"
        )
        self.assertEqual(plan.approval_state, "pending")

    def test_approve_plan(self):
        plan = self.coord.create_plan(
            "wp-3", "vps", risk_class="high"
        )
        self.assertEqual(plan.approval_state, "pending")
        approved = self.coord.approve_plan(plan.execution_plan_id)
        self.assertEqual(approved.approval_state, "approved")
        self.assertEqual(approved.status, "approved")

    def test_deny_plan(self):
        plan = self.coord.create_plan(
            "wp-4", "container", risk_class="critical"
        )
        denied = self.coord.deny_plan(plan.execution_plan_id, reason="Too risky")
        self.assertEqual(denied.approval_state, "denied")
        self.assertEqual(denied.status, "cancelled")

    def test_enqueue_approved_plan(self):
        plan = self.coord.create_plan("wp-5", "workstation", risk_class="low")
        queued = self.coord.enqueue_plan(plan.execution_plan_id)
        self.assertIsNotNone(queued)
        self.assertEqual(queued.status, "queued")

    def test_enqueue_unapproved_blocked(self):
        plan = self.coord.create_plan("wp-6", "agent", risk_class="high")
        queued = self.coord.enqueue_plan(plan.execution_plan_id)
        self.assertIsNone(queued)

    def test_dispatch_next(self):
        plan = self.coord.create_plan("wp-7", "vps", risk_class="low")
        self.coord.enqueue_plan(plan.execution_plan_id)
        dispatched = self.coord.dispatch_next()
        self.assertIsNotNone(dispatched)
        self.assertEqual(dispatched.status, "dispatched")

    def test_full_lifecycle(self):
        plan = self.coord.create_plan(
            "wp-full", "workstation",
            risk_class="low",
            profile_id="engineer",
            session_id="sess-desktop",
            description="Full lifecycle test",
        )
        self.coord.enqueue_plan(plan.execution_plan_id)
        dispatched = self.coord.dispatch_next()
        started = self.coord.mark_started(dispatched.execution_plan_id)
        self.assertEqual(started.status, "executing")
        completed = self.coord.mark_completed(
            started.execution_plan_id, proof_id="proof-123"
        )
        self.assertEqual(completed.status, "completed")
        self.assertEqual(completed.proof_id, "proof-123")

        events = self.coord.lifecycle_for_plan(plan.execution_plan_id)
        event_types = [e.event_type for e in events]
        self.assertIn("plan_created", event_types)
        self.assertIn("plan_queued", event_types)
        self.assertIn("plan_dispatched", event_types)
        self.assertIn("execution_started", event_types)
        self.assertIn("execution_completed", event_types)

    def test_mark_failed(self):
        plan = self.coord.create_plan("wp-fail", "container", risk_class="low")
        self.coord.enqueue_plan(plan.execution_plan_id)
        dispatched = self.coord.dispatch_next()
        started = self.coord.mark_started(dispatched.execution_plan_id)
        failed = self.coord.mark_failed(started.execution_plan_id, reason="Timeout")
        self.assertEqual(failed.status, "failed")
        self.assertEqual(failed.failure_reason, "Timeout")

    def test_cancel_plan(self):
        plan = self.coord.create_plan("wp-cancel", "agent", risk_class="low")
        self.coord.enqueue_plan(plan.execution_plan_id)
        cancelled = self.coord.cancel_plan(plan.execution_plan_id)
        self.assertEqual(cancelled.status, "cancelled")

    def test_reprioritize(self):
        plan = self.coord.create_plan(
            "wp-repri", "vps", risk_class="low", priority="low"
        )
        updated = self.coord.reprioritize(plan.execution_plan_id, "critical")
        self.assertEqual(updated.priority, "critical")

    def test_session_binding(self):
        plan = self.coord.create_plan(
            "wp-sess", "workstation",
            session_id="sess-desktop",
            risk_class="low",
        )
        by_session = self.coord.plans_by_session("sess-desktop")
        self.assertEqual(len(by_session), 1)
        self.assertEqual(by_session[0].session_id, "sess-desktop")

    def test_profile_binding(self):
        plan = self.coord.create_plan(
            "wp-prof", "agent",
            profile_id="engineer",
            risk_class="low",
        )
        by_profile = self.coord.plans_by_profile("engineer")
        self.assertEqual(len(by_profile), 1)
        self.assertEqual(by_profile[0].profile_id, "engineer")

    def test_queue_depth(self):
        for i in range(3):
            p = self.coord.create_plan(f"wp-q{i}", "vps", risk_class="low")
            self.coord.enqueue_plan(p.execution_plan_id)
        self.assertEqual(self.coord.queue_depth(), 3)

    def test_awaiting_approval(self):
        self.coord.create_plan("wp-pend", "agent", risk_class="high")
        self.coord.create_plan("wp-auto", "vps", risk_class="low")
        pending = self.coord.awaiting_approval()
        self.assertEqual(len(pending), 1)

    def test_active_plans(self):
        plan = self.coord.create_plan("wp-active", "workstation", risk_class="low")
        self.coord.enqueue_plan(plan.execution_plan_id)
        self.coord.dispatch_next()
        self.assertEqual(len(self.coord.active_plans()), 1)

    def test_snapshot(self):
        self.coord.create_plan("wp-snap", "agent", risk_class="low")
        snap = self.coord.snapshot()
        self.assertEqual(snap.total_plans, 1)
        self.assertIn("drafted", snap.by_status)

    def test_seed_executors(self):
        execs = self.coord.seed_executors()
        self.assertEqual(len(execs), 7)
        types = {e.executor_type for e in execs}
        self.assertIn("workstation", types)
        self.assertIn("agent", types)

    def test_register_custom_executor(self):
        ex = ExecutorDefinition(
            executor_type="custom",
            name="Custom Executor",
            capabilities=["special"],
        )
        registered = self.coord.register_executor(ex)
        self.assertEqual(registered.name, "Custom Executor")
        got = self.coord.executors()
        self.assertEqual(len(got), 1)

    def test_cannot_start_without_dispatch(self):
        plan = self.coord.create_plan("wp-nostart", "vps", risk_class="low")
        result = self.coord.mark_started(plan.execution_plan_id)
        self.assertIsNone(result)

    def test_cannot_complete_without_start(self):
        plan = self.coord.create_plan("wp-nocomplete", "vps", risk_class="low")
        self.coord.enqueue_plan(plan.execution_plan_id)
        self.coord.dispatch_next()
        result = self.coord.mark_completed(plan.execution_plan_id)
        self.assertIsNone(result)

    def test_cannot_fail_drafted(self):
        plan = self.coord.create_plan("wp-nofail", "vps", risk_class="low")
        result = self.coord.mark_failed(plan.execution_plan_id)
        self.assertIsNone(result)

    def test_cannot_cancel_completed(self):
        plan = self.coord.create_plan("wp-nocancl", "vps", risk_class="low")
        self.coord.enqueue_plan(plan.execution_plan_id)
        dispatched = self.coord.dispatch_next()
        started = self.coord.mark_started(dispatched.execution_plan_id)
        self.coord.mark_completed(started.execution_plan_id)
        result = self.coord.cancel_plan(plan.execution_plan_id)
        self.assertIsNone(result)

    def test_gather_context(self):
        ctx = self.coord.gather_context()
        self.assertIn("profile", ctx)
        self.assertIn("session", ctx)
        self.assertIn("presence", ctx)
        self.assertIn("workstation", ctx)
        self.assertIn("projection", ctx)
        self.assertIn("continuity", ctx)

    def test_plan_history(self):
        plan = self.coord.create_plan("wp-hist", "vps", risk_class="low")
        self.coord.enqueue_plan(plan.execution_plan_id)
        dispatched = self.coord.dispatch_next()
        started = self.coord.mark_started(dispatched.execution_plan_id)
        self.coord.mark_completed(started.execution_plan_id)
        history = self.coord.plan_history()
        self.assertEqual(len(history), 1)

    def test_recent_lifecycle(self):
        plan = self.coord.create_plan("wp-recent", "agent", risk_class="low")
        recent = self.coord.recent_lifecycle()
        self.assertGreater(len(recent), 0)

    def test_workpacket_query(self):
        self.coord.create_plan("wp-query-1", "vps", risk_class="low")
        self.coord.create_plan("wp-query-1", "agent", risk_class="low")
        self.coord.create_plan("wp-query-2", "vps", risk_class="low")
        by_wp = self.coord.plans_by_workpacket("wp-query-1")
        self.assertEqual(len(by_wp), 2)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Singleton Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSingleton(unittest.TestCase):
    def test_singleton_returns_same(self):
        reset_execution_coordinator()
        c1 = get_execution_coordinator()
        c2 = get_execution_coordinator()
        self.assertIs(c1, c2)
        reset_execution_coordinator()

    def test_reset_creates_new(self):
        reset_execution_coordinator()
        c1 = get_execution_coordinator()
        reset_execution_coordinator()
        c2 = get_execution_coordinator()
        self.assertIsNot(c1, c2)
        reset_execution_coordinator()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Acceptance Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestAcceptanceScenario(unittest.TestCase):
    """Full acceptance scenario per Phase 13 specification."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.coord = ExecutionCoordinator(data_dir=self.tmpdir)
        self.coord.seed_executors()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_full_acceptance_scenario(self):
        """Operator switches to Engineer, Desktop primary, gap identified,
        WorkPacket created, approved, plan generated, queued, assigned to
        workstation, lifecycle persisted. No real execution."""

        # 1. Engineer Profile active, Desktop primary session
        plan = self.coord.create_plan(
            source_workpacket_id="wp-gap-fix-001",
            target_executor="workstation",
            profile_id="engineer",
            session_id="sess-desktop-001",
            execution_mode="asynchronous",
            priority="normal",
            risk_class="low",
            description="Fix missing test coverage identified by gap engine",
        )

        # Verify plan created with correct bindings
        self.assertEqual(plan.profile_id, "engineer")
        self.assertEqual(plan.session_id, "sess-desktop-001")
        self.assertEqual(plan.target_executor, "workstation")
        self.assertEqual(plan.source_workpacket_id, "wp-gap-fix-001")

        # Low risk → auto-approved
        self.assertEqual(plan.approval_state, "approved")

        # 2. Enqueue
        queued = self.coord.enqueue_plan(plan.execution_plan_id)
        self.assertIsNotNone(queued)
        self.assertEqual(queued.status, "queued")

        # 3. Dispatch
        dispatched = self.coord.dispatch_next()
        self.assertIsNotNone(dispatched)
        self.assertEqual(dispatched.status, "dispatched")
        self.assertEqual(dispatched.target_executor, "workstation")

        # 4. Execution started
        started = self.coord.mark_started(dispatched.execution_plan_id)
        self.assertEqual(started.status, "executing")

        # 5. Execution completed with proof
        completed = self.coord.mark_completed(
            started.execution_plan_id, proof_id="proof-gap-fix-001"
        )
        self.assertEqual(completed.status, "completed")
        self.assertEqual(completed.proof_id, "proof-gap-fix-001")

        # 6. Verify full lifecycle persisted
        events = self.coord.lifecycle_for_plan(plan.execution_plan_id)
        event_types = [e.event_type for e in events]
        self.assertEqual(event_types, [
            "plan_created",
            "plan_queued",
            "plan_dispatched",
            "execution_started",
            "execution_completed",
        ])

        # 7. Verify no real execution occurred (coordinator never executes)
        # This is structural: ExecutionCoordinator has no execute() method
        self.assertFalse(hasattr(self.coord, "execute"))
        self.assertFalse(hasattr(self.coord, "run"))

    def test_high_risk_requires_operator_approval(self):
        """High-risk plan cannot proceed without explicit approval."""
        plan = self.coord.create_plan(
            "wp-risky", "workstation",
            risk_class="high",
            profile_id="engineer",
        )
        self.assertEqual(plan.approval_state, "pending")

        # Cannot enqueue without approval
        result = self.coord.enqueue_plan(plan.execution_plan_id)
        self.assertIsNone(result)

        # Operator approves
        approved = self.coord.approve_plan(plan.execution_plan_id)
        self.assertEqual(approved.approval_state, "approved")

        # Now can enqueue
        queued = self.coord.enqueue_plan(plan.execution_plan_id)
        self.assertIsNotNone(queued)

    def test_denied_plan_cannot_proceed(self):
        """Denied plans are cancelled and cannot be dispatched."""
        plan = self.coord.create_plan(
            "wp-deny", "agent", risk_class="critical"
        )
        denied = self.coord.deny_plan(
            plan.execution_plan_id, reason="Not safe"
        )
        self.assertEqual(denied.status, "cancelled")
        result = self.coord.enqueue_plan(plan.execution_plan_id)
        self.assertIsNone(result)

    def test_all_executor_types_registered(self):
        """All 7 canonical executor types exist after seeding."""
        executors = self.coord.executors()
        types = {e.executor_type for e in executors}
        self.assertEqual(types, {
            "workstation", "agent", "vps", "container",
            "browser", "mobile", "external",
        })

    def test_multi_plan_priority_ordering(self):
        """Critical plans dispatch before normal ones."""
        normal = self.coord.create_plan(
            "wp-normal", "vps", risk_class="low", priority="normal"
        )
        critical = self.coord.create_plan(
            "wp-critical", "vps", risk_class="low", priority="critical"
        )
        self.coord.enqueue_plan(normal.execution_plan_id)
        self.coord.enqueue_plan(critical.execution_plan_id)

        first = self.coord.dispatch_next()
        self.assertEqual(first.source_workpacket_id, "wp-critical")

    def test_failure_preserves_reason(self):
        """Failed execution preserves the failure reason."""
        plan = self.coord.create_plan("wp-failr", "container", risk_class="low")
        self.coord.enqueue_plan(plan.execution_plan_id)
        dispatched = self.coord.dispatch_next()
        started = self.coord.mark_started(dispatched.execution_plan_id)
        failed = self.coord.mark_failed(started.execution_plan_id, "OOM killed")
        self.assertEqual(failed.failure_reason, "OOM killed")

        events = self.coord.lifecycle_for_plan(plan.execution_plan_id)
        fail_event = [e for e in events if e.event_type == "execution_failed"][0]
        self.assertIn("OOM killed", fail_event.summary)

    def test_no_execution_automation(self):
        """Coordinator has no methods that perform real execution."""
        forbidden = [
            "execute", "run", "launch", "start_app",
            "open_browser", "ssh", "docker_run",
        ]
        for method_name in forbidden:
            self.assertFalse(
                hasattr(self.coord, method_name),
                f"Coordinator must not have {method_name}()"
            )

    def test_session_profile_binding_explicit(self):
        """Session and profile binding is explicit in the plan."""
        plan = self.coord.create_plan(
            "wp-bind", "workstation",
            profile_id="engineer",
            session_id="sess-desktop",
            risk_class="low",
        )
        self.assertEqual(plan.profile_id, "engineer")
        self.assertEqual(plan.session_id, "sess-desktop")

        # Verify queryable
        by_prof = self.coord.plans_by_profile("engineer")
        self.assertIn(plan.execution_plan_id,
                      [p.execution_plan_id for p in by_prof])
        by_sess = self.coord.plans_by_session("sess-desktop")
        self.assertIn(plan.execution_plan_id,
                      [p.execution_plan_id for p in by_sess])

    def test_all_statuses_reachable(self):
        """Every status in ExecutionPlanStatus is reachable through the API."""
        # drafted
        p1 = self.coord.create_plan("wp-s1", "vps", risk_class="high")
        self.assertEqual(p1.status, "drafted")

        # approved
        self.coord.approve_plan(p1.execution_plan_id)
        p1 = self.coord.get_plan(p1.execution_plan_id)
        self.assertEqual(p1.status, "approved")

        # queued
        self.coord.enqueue_plan(p1.execution_plan_id)
        p1 = self.coord.get_plan(p1.execution_plan_id)
        self.assertEqual(p1.status, "queued")

        # dispatched
        p1 = self.coord.dispatch_next()
        self.assertEqual(p1.status, "dispatched")

        # executing
        self.coord.mark_started(p1.execution_plan_id)
        p1 = self.coord.get_plan(p1.execution_plan_id)
        self.assertEqual(p1.status, "executing")

        # completed
        self.coord.mark_completed(p1.execution_plan_id)
        p1 = self.coord.get_plan(p1.execution_plan_id)
        self.assertEqual(p1.status, "completed")

        # failed (separate plan)
        p2 = self.coord.create_plan("wp-s2", "vps", risk_class="low")
        self.coord.enqueue_plan(p2.execution_plan_id)
        p2 = self.coord.dispatch_next()
        self.coord.mark_started(p2.execution_plan_id)
        self.coord.mark_failed(p2.execution_plan_id, "error")
        p2 = self.coord.get_plan(p2.execution_plan_id)
        self.assertEqual(p2.status, "failed")

        # cancelled
        p3 = self.coord.create_plan("wp-s3", "vps", risk_class="low")
        self.coord.cancel_plan(p3.execution_plan_id)
        p3 = self.coord.get_plan(p3.execution_plan_id)
        self.assertEqual(p3.status, "cancelled")

    def test_snapshot_reflects_state(self):
        """Snapshot accurately reflects current coordinator state."""
        self.coord.create_plan("wp-snap1", "vps", risk_class="low")
        self.coord.create_plan("wp-snap2", "agent", risk_class="high")

        p3 = self.coord.create_plan("wp-snap3", "workstation", risk_class="low")
        self.coord.enqueue_plan(p3.execution_plan_id)

        snap = self.coord.snapshot()
        self.assertEqual(snap.total_plans, 3)
        self.assertEqual(snap.queue_depth, 1)
        self.assertEqual(snap.awaiting_approval, 1)
        self.assertEqual(snap.executor_count, 7)


if __name__ == "__main__":
    unittest.main()
