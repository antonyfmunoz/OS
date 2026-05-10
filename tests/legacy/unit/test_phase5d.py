"""Tests for Phase 5D: Event-Driven Orchestration Layer.

Verifies:
- Rule registration and matching
- Orchestrator handles events correctly
- Built-in rules fire on correct events
- Approval → auto re-execution works end-to-end
- No infinite loops (max replay = 1)
- Orchestration events emitted
- Ordering preserved
- API returns orchestrator rules
"""

import sys
import os
import threading

sys.path.insert(0, "/opt/OS")

os.environ.setdefault("UMH_API_KEY", "test-key-phase5a")

from fastapi.testclient import TestClient

from umh.control.api import app
from umh.control.identity import get_identity_store
from umh.events.stream import Event, get_event_stream, publish, reset_event_stream
from umh.execution.approval import ApprovalStatus, get_approval_store
from umh.execution.contract import (
    ExecutionClass,
    ExecutionConstraints,
    ExecutionContext,
    ExecutionRequest,
    ExecutionStatus,
    ExecutionTarget,
)
from umh.execution.engine import execute
from umh.orchestrator.engine import (
    Orchestrator,
    Rule,
    get_orchestrator,
    register_built_in_rules,
    reset_orchestrator,
    start_orchestrator,
)

client = TestClient(app)


def _reset():
    get_approval_store().reset()
    get_identity_store().reset()
    reset_event_stream()
    reset_orchestrator()


def _start_fresh():
    _reset()
    return start_orchestrator()


def _create_identity(name="admin", scopes=None):
    store = get_identity_store()
    identity, raw_key = store.create_identity(name, scopes or ["admin"])
    return identity, raw_key, {"X-API-Key": raw_key}


def _make_request(
    operation: str,
    execution_class: ExecutionClass = ExecutionClass.SIDE_EFFECT,
    inputs: dict | None = None,
    issued_by: str = "test",
) -> ExecutionRequest:
    return ExecutionRequest(
        execution_id=f"test_{operation}",
        correlation_id=f"test_{operation}",
        causal_event_id="",
        session_id="",
        operation=operation,
        inputs=inputs or {},
        execution_class=execution_class,
        constraints=ExecutionConstraints(timeout_s=10),
        target=ExecutionTarget(node_id="local", transport="test"),
        context=ExecutionContext(metadata={}),
        issued_at="2026-04-26T12:00:00Z",
        issued_by=issued_by,
        idempotency_key="",
    )


def _make_llm_request(operation: str = "test_op", issued_by: str = "") -> ExecutionRequest:
    return ExecutionRequest(
        execution_id=f"exec_test_{operation}",
        correlation_id="corr_test",
        causal_event_id="",
        session_id="",
        operation=operation,
        inputs={"prompt": "hello", "system_prompt": "", "max_tokens": 100},
        execution_class=ExecutionClass.LLM_CALL,
        constraints=ExecutionConstraints(timeout_s=10),
        target=ExecutionTarget(node_id="local", transport="test"),
        context=ExecutionContext(metadata={}),
        issued_at="2026-01-01T00:00:00+00:00",
        issued_by=issued_by,
        idempotency_key="",
    )


# ── A. Rule Core ───────────────────────────────────────���──────────


class TestRuleCore:
    def test_rule_creation(self):
        rule = Rule(
            id="test_rule",
            event_type="test.event",
            condition=lambda e: True,
            action=lambda e: None,
            description="Test rule",
        )
        assert rule.id == "test_rule"
        assert rule.event_type == "test.event"

    def test_rule_to_dict(self):
        rule = Rule(
            id="r1",
            event_type="t",
            condition=lambda e: True,
            action=lambda e: None,
            description="desc",
        )
        d = rule.to_dict()
        assert d["id"] == "r1"
        assert d["event_type"] == "t"
        assert d["description"] == "desc"
        assert "condition" not in d
        assert "action" not in d


# ── B. Orchestrator Core ──────────────────────────────────────────


class TestOrchestratorCore:
    def test_register_and_list_rules(self):
        orch = Orchestrator()
        rule = Rule(id="r1", event_type="t", condition=lambda e: True, action=lambda e: None)
        orch.register_rule(rule)
        assert len(orch.list_rules()) == 1
        assert orch.list_rules()[0].id == "r1"

    def test_handle_event_fires_matching_rule(self):
        orch = Orchestrator()
        fired = []
        orch.register_rule(
            Rule(
                id="r1",
                event_type="test.fire",
                condition=lambda e: True,
                action=lambda e: fired.append(e),
            )
        )
        event = Event(id="e1", type="test.fire", timestamp="ts", payload={})
        orch.handle_event(event)
        assert len(fired) == 1
        assert fired[0].id == "e1"

    def test_non_matching_event_type_skipped(self):
        orch = Orchestrator()
        fired = []
        orch.register_rule(
            Rule(
                id="r1",
                event_type="test.fire",
                condition=lambda e: True,
                action=lambda e: fired.append(e),
            )
        )
        event = Event(id="e1", type="test.other", timestamp="ts", payload={})
        orch.handle_event(event)
        assert len(fired) == 0

    def test_condition_false_skips_action(self):
        orch = Orchestrator()
        fired = []
        orch.register_rule(
            Rule(
                id="r1",
                event_type="test.fire",
                condition=lambda e: False,
                action=lambda e: fired.append(e),
            )
        )
        event = Event(id="e1", type="test.fire", timestamp="ts", payload={})
        orch.handle_event(event)
        assert len(fired) == 0

    def test_duplicate_event_handled_once(self):
        orch = Orchestrator()
        fired = []
        orch.register_rule(
            Rule(
                id="r1",
                event_type="test.fire",
                condition=lambda e: True,
                action=lambda e: fired.append(e),
            )
        )
        event = Event(id="e1", type="test.fire", timestamp="ts", payload={})
        orch.handle_event(event)
        orch.handle_event(event)
        assert len(fired) == 1

    def test_orchestration_events_ignored(self):
        orch = Orchestrator()
        fired = []
        orch.register_rule(
            Rule(
                id="r1",
                event_type="orchestration.triggered",
                condition=lambda e: True,
                action=lambda e: fired.append(e),
            )
        )
        event = Event(id="e1", type="orchestration.triggered", timestamp="ts", payload={})
        orch.handle_event(event)
        assert len(fired) == 0

    def test_condition_error_skips_rule(self):
        orch = Orchestrator()
        fired = []

        def bad_condition(e):
            raise RuntimeError("boom")

        orch.register_rule(
            Rule(
                id="r1",
                event_type="test.fire",
                condition=bad_condition,
                action=lambda e: fired.append(e),
            )
        )
        event = Event(id="e1", type="test.fire", timestamp="ts", payload={})
        orch.handle_event(event)
        assert len(fired) == 0

    def test_action_error_does_not_crash(self):
        orch = Orchestrator()

        def bad_action(e):
            raise RuntimeError("boom")

        orch.register_rule(
            Rule(id="r1", event_type="test.fire", condition=lambda e: True, action=bad_action)
        )
        event = Event(id="e1", type="test.fire", timestamp="ts", payload={})
        orch.handle_event(event)

    def test_multiple_rules_fire_in_order(self):
        orch = Orchestrator()
        order = []
        orch.register_rule(
            Rule(
                id="r1",
                event_type="test.fire",
                condition=lambda e: True,
                action=lambda e: order.append("r1"),
            )
        )
        orch.register_rule(
            Rule(
                id="r2",
                event_type="test.fire",
                condition=lambda e: True,
                action=lambda e: order.append("r2"),
            )
        )
        event = Event(id="e1", type="test.fire", timestamp="ts", payload={})
        orch.handle_event(event)
        assert order == ["r1", "r2"]

    def test_reset_clears_state(self):
        orch = Orchestrator()
        orch.register_rule(
            Rule(id="r1", event_type="t", condition=lambda e: True, action=lambda e: None)
        )
        orch.store_pending_request("exec_1", {"operation": "test"})
        orch.record_replay("appr_1")
        orch.reset()
        assert len(orch.list_rules()) == 0
        assert orch.get_pending_request("exec_1") is None
        assert orch.can_replay("appr_1") is True


# ── C. Pending Request Store ──────────────────────────────────────


class TestPendingRequestStore:
    def test_store_and_retrieve(self):
        orch = Orchestrator()
        orch.store_pending_request("exec_1", {"operation": "test"})
        assert orch.get_pending_request("exec_1") == {"operation": "test"}

    def test_missing_returns_none(self):
        orch = Orchestrator()
        assert orch.get_pending_request("nonexistent") is None

    def test_remove(self):
        orch = Orchestrator()
        orch.store_pending_request("exec_1", {"operation": "test"})
        orch.remove_pending_request("exec_1")
        assert orch.get_pending_request("exec_1") is None


# ── D. Replay Safety ─────────────────────────────────────────────


class TestReplaySafety:
    def test_can_replay_initially_true(self):
        orch = Orchestrator()
        assert orch.can_replay("appr_1") is True

    def test_replay_limit_enforced(self):
        orch = Orchestrator()
        orch.record_replay("appr_1")
        assert orch.can_replay("appr_1") is False

    def test_different_approvals_independent(self):
        orch = Orchestrator()
        orch.record_replay("appr_1")
        assert orch.can_replay("appr_2") is True


# ── E. Built-in Rules ────────────────────────────────────────────


class TestBuiltInRules:
    def test_built_in_rules_registered(self):
        orch = Orchestrator()
        register_built_in_rules(orch)
        rules = orch.list_rules()
        ids = [r.id for r in rules]
        assert "builtin:replay_on_approval" in ids
        assert "builtin:log_pending_approval" in ids

    def test_replay_rule_matches_approval_approved(self):
        orch = Orchestrator()
        register_built_in_rules(orch)
        replay_rule = next(r for r in orch.list_rules() if r.id == "builtin:replay_on_approval")
        assert replay_rule.event_type == "approval.approved"

    def test_pending_rule_matches_rejected_with_requires_approval(self):
        orch = Orchestrator()
        register_built_in_rules(orch)
        pending_rule = next(r for r in orch.list_rules() if r.id == "builtin:log_pending_approval")
        event_match = Event(
            id="e1",
            type="execution.completed",
            timestamp="ts",
            payload={"status": "rejected", "requires_approval": True},
        )
        event_nomatch = Event(
            id="e2",
            type="execution.completed",
            timestamp="ts",
            payload={"status": "rejected"},
        )
        assert pending_rule.condition(event_match)
        assert not pending_rule.condition(event_nomatch)


# ── F. Orchestration Events ──────────────────────────────────────


class TestOrchestrationEvents:
    def test_orchestration_triggered_event_emitted(self):
        _start_fresh()
        stream = get_event_stream()
        orch = get_orchestrator()
        orch.register_rule(
            Rule(
                id="test:trigger_event",
                event_type="test.fire",
                condition=lambda e: True,
                action=lambda e: None,
            )
        )
        event = Event(id="e_trigger", type="test.fire", timestamp="ts", payload={})
        orch.handle_event(event)
        events = stream.list_events()
        triggered = [e for e in events if e.type == "orchestration.triggered"]
        assert len(triggered) == 1
        assert triggered[0].payload["rule_id"] == "test:trigger_event"
        assert triggered[0].payload["source_event_id"] == "e_trigger"


# ── G. Event Stream Integration ──────────────────────────────────


class TestEventStreamIntegration:
    def test_orchestrator_subscribes_to_stream(self):
        _start_fresh()
        stream = get_event_stream()
        fired = []
        orch = get_orchestrator()
        orch.register_rule(
            Rule(
                id="test:stream_int",
                event_type="test.stream",
                condition=lambda e: True,
                action=lambda e: fired.append(e),
            )
        )
        publish("test.stream", payload={"via": "stream"})
        assert len(fired) == 1

    def test_publish_triggers_orchestrator(self):
        _start_fresh()
        orch = get_orchestrator()
        results = []
        orch.register_rule(
            Rule(
                id="test:pub_trigger",
                event_type="custom.event",
                condition=lambda e: e.payload.get("trigger") is True,
                action=lambda e: results.append(e.payload),
            )
        )
        publish("custom.event", payload={"trigger": True})
        publish("custom.event", payload={"trigger": False})
        assert len(results) == 1
        assert results[0]["trigger"] is True


# ── H. Thread Safety ─────────────────────────────────────────────


class TestOrchestratorThreadSafety:
    def test_concurrent_event_handling(self):
        orch = Orchestrator()
        counter = {"count": 0}
        lock = threading.Lock()

        def count_action(e):
            with lock:
                counter["count"] += 1

        orch.register_rule(
            Rule(id="r1", event_type="t", condition=lambda e: True, action=count_action)
        )
        barrier = threading.Barrier(4)

        def handle_events(prefix):
            barrier.wait()
            for i in range(25):
                event = Event(id=f"{prefix}_{i}", type="t", timestamp="ts", payload={})
                orch.handle_event(event)

        threads = [threading.Thread(target=handle_events, args=(f"w{t}",)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert counter["count"] == 100


# ── I. End-to-End: Approval Auto-Replay ──────────────────────────


class TestApprovalAutoReplay:
    def test_approval_triggers_replay(self):
        """Full path: execute → rejected → approve → orchestrator replays."""
        _start_fresh()
        store = get_approval_store()

        request = _make_request("computer_click", inputs={"x": 10, "y": 20})
        result = execute(request)
        assert result.status == ExecutionStatus.REJECTED
        assert result.outputs.get("requires_approval") is True
        approval_id = result.outputs["approval_id"]

        orch = get_orchestrator()
        assert orch.get_pending_request(request.execution_id) is not None

        store.approve(approval_id)

        events = get_event_stream().list_events(limit=200)
        types = [e.type for e in events]
        assert "orchestration.triggered" in types
        assert "orchestration.executed" in types

        exec_events = [e for e in events if e.type == "orchestration.executed"]
        assert len(exec_events) == 1
        assert exec_events[0].payload["original_execution_id"] == request.execution_id
        assert exec_events[0].payload["approval_id"] == approval_id

    def test_replay_produces_execution_events(self):
        _start_fresh()
        store = get_approval_store()

        request = _make_request("computer_click", inputs={"x": 10, "y": 20})
        result = execute(request)
        approval_id = result.outputs["approval_id"]

        store.approve(approval_id)

        events = get_event_stream().list_events(limit=200)
        replay_exec = [e for e in events if e.type == "orchestration.executed"]
        assert len(replay_exec) == 1
        replay_exec_id = replay_exec[0].payload["replay_execution_id"]

        started = [
            e for e in events if e.type == "execution.started" and e.execution_id == replay_exec_id
        ]
        completed = [
            e
            for e in events
            if e.type == "execution.completed" and e.execution_id == replay_exec_id
        ]
        assert len(started) == 1
        assert len(completed) == 1

    def test_no_double_replay(self):
        """Max replay = 1. Second approval of same ID should not replay."""
        _start_fresh()
        store = get_approval_store()

        request = _make_request("computer_click", inputs={"x": 5, "y": 5})
        result = execute(request)
        approval_id = result.outputs["approval_id"]

        store.approve(approval_id)

        events_before = get_event_stream().count()

        orch = get_orchestrator()
        event = Event(
            id="fake_second_approval",
            type="approval.approved",
            timestamp="ts",
            payload={},
            approval_id=approval_id,
        )
        orch.handle_event(event)

        events_after = get_event_stream().list_events(limit=500)
        replays = [e for e in events_after if e.type == "orchestration.executed"]
        assert len(replays) == 1

    def test_pending_request_cleaned_after_replay(self):
        _start_fresh()
        store = get_approval_store()

        request = _make_request("computer_click", inputs={"x": 1, "y": 1})
        result = execute(request)
        approval_id = result.outputs["approval_id"]

        store.approve(approval_id)

        orch = get_orchestrator()
        assert orch.get_pending_request(request.execution_id) is None

    def test_event_ordering_in_replay(self):
        _start_fresh()
        store = get_approval_store()

        request = _make_request("computer_click", inputs={"x": 2, "y": 2})
        result = execute(request)
        approval_id = result.outputs["approval_id"]

        store.approve(approval_id)

        events = get_event_stream().list_events(limit=200)
        types = [e.type for e in events]

        orch_triggered_idx = types.index("orchestration.triggered")
        orch_executed_idx = types.index("orchestration.executed")
        assert orch_triggered_idx < orch_executed_idx

        replay_exec_started = [
            i
            for i, e in enumerate(events)
            if e.type == "execution.started" and i > orch_executed_idx
        ]
        assert len(replay_exec_started) >= 1


# ── J. API: GET /orchestrator/rules ──────────────────────────────


class TestOrchestratorAPI:
    def test_rules_endpoint_requires_auth(self):
        _start_fresh()
        resp = client.get("/orchestrator/rules")
        assert resp.status_code == 401

    def test_rules_endpoint_requires_admin(self):
        _start_fresh()
        _, _, headers = _create_identity("viewer", ["metrics:read"])
        resp = client.get("/orchestrator/rules", headers=headers)
        assert resp.status_code == 403

    def test_rules_endpoint_returns_rules(self):
        _start_fresh()
        _, _, headers = _create_identity("admin", ["admin"])
        resp = client.get("/orchestrator/rules", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        ids = [r["id"] for r in data]
        assert "builtin:replay_on_approval" in ids
        assert "builtin:log_pending_approval" in ids

    def test_rules_have_descriptions(self):
        _start_fresh()
        _, _, headers = _create_identity("admin", ["admin"])
        resp = client.get("/orchestrator/rules", headers=headers)
        data = resp.json()
        for rule in data:
            assert "description" in rule
            assert len(rule["description"]) > 0


# ── K. Global Singleton ──────────────────────────────────────────


class TestOrchestratorSingleton:
    def test_get_orchestrator_returns_same(self):
        _reset()
        o1 = get_orchestrator()
        o2 = get_orchestrator()
        assert o1 is o2

    def test_reset_creates_new(self):
        _reset()
        o1 = get_orchestrator()
        o2 = reset_orchestrator()
        assert o1 is not o2

    def test_start_orchestrator_idempotent(self):
        _reset()
        o1 = start_orchestrator()
        o2 = start_orchestrator()
        assert o1 is o2
        assert len(o1.list_rules()) == 3
