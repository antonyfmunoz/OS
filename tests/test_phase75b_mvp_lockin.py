"""Phase 75B MVP Lock-In — end-to-end test suite.

Tests all Phase 75B deliverables:
  - Identity persistence (get_or_create)
  - Trace store (create, append, complete, fail, query)
  - Governance gate (evaluate, all outcomes)
  - Backend registry (register, select, reject unknown)
  - Governed execution wrapper (full flow)
  - Control plane endpoints (/run/direct, /traces)
  - Intelligence kernel hook (enrichment module)
  - Layering invariants (no bypass, no deletion, no circular)

40+ tests.  All use in-memory stores — no SQLite, no network.
"""

from __future__ import annotations

import os
import pytest
from unittest.mock import patch

os.environ.setdefault("PYTEST_CURRENT_TEST", "1")


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def _reset_stores():
    """Reset all global singletons before each test."""
    from umh.control.trace_store import InMemoryTraceStore, reset_trace_store
    from umh.control.identity import InMemoryIdentityStore, reset_identity_store
    from umh.execution.backend_registry import reset_backend_registry

    reset_trace_store(InMemoryTraceStore())
    reset_identity_store(InMemoryIdentityStore())
    reset_backend_registry(None)
    yield
    reset_trace_store(None)
    reset_identity_store(None)
    reset_backend_registry(None)


# ═══════════════════════════════════════════════════════════════════════
# 1. Identity Persistence
# ═══════════════════════════════════════════════════════════════════════


class TestIdentityPersistence:
    def test_create_identity(self):
        from umh.control.identity import InMemoryIdentityStore

        store = InMemoryIdentityStore()
        identity, key = store.create_identity("test-agent", ["execute"])
        assert identity.name == "test-agent"
        assert identity.status == "active"
        assert key.startswith("umh_")

    def test_authenticate_valid_key(self):
        from umh.control.identity import InMemoryIdentityStore

        store = InMemoryIdentityStore()
        _, key = store.create_identity("test-agent", ["execute"])
        auth = store.authenticate(key)
        assert auth is not None
        assert auth.name == "test-agent"

    def test_authenticate_invalid_key(self):
        from umh.control.identity import InMemoryIdentityStore

        store = InMemoryIdentityStore()
        store.create_identity("test-agent", ["execute"])
        auth = store.authenticate("umh_invalid_key_000000")
        assert auth is None

    def test_get_or_create_new(self):
        from umh.control.identity import InMemoryIdentityStore

        store = InMemoryIdentityStore()
        identity, key = store.get_or_create("new-agent", ["execute"])
        assert identity.name == "new-agent"
        assert key is not None

    def test_get_or_create_existing(self):
        from umh.control.identity import InMemoryIdentityStore

        store = InMemoryIdentityStore()
        store.create_identity("existing-agent", ["execute"])
        identity, key = store.get_or_create("existing-agent")
        assert identity.name == "existing-agent"
        assert key is None

    def test_get_by_name(self):
        from umh.control.identity import InMemoryIdentityStore

        store = InMemoryIdentityStore()
        store.create_identity("lookup-agent", ["execute"])
        found = store.get_by_name("lookup-agent")
        assert found is not None
        assert found.name == "lookup-agent"

    def test_get_by_name_not_found(self):
        from umh.control.identity import InMemoryIdentityStore

        store = InMemoryIdentityStore()
        found = store.get_by_name("nonexistent")
        assert found is None

    def test_get_by_name_disabled(self):
        from umh.control.identity import InMemoryIdentityStore

        store = InMemoryIdentityStore()
        identity, _ = store.create_identity("disabled-agent", ["execute"])
        store.disable_identity(identity.id)
        found = store.get_by_name("disabled-agent")
        assert found is None

    def test_scope_check_admin(self):
        from umh.control.identity import InMemoryIdentityStore

        store = InMemoryIdentityStore()
        identity, _ = store.create_identity("admin", ["admin"])
        assert identity.has_scope("execute")
        assert identity.has_scope("metrics:read")
        assert identity.has_scope("anything")

    def test_scope_check_limited(self):
        from umh.control.identity import InMemoryIdentityStore

        store = InMemoryIdentityStore()
        identity, _ = store.create_identity("reader", ["metrics:read"])
        assert identity.has_scope("metrics:read")
        assert not identity.has_scope("execute")
        assert not identity.has_scope("admin")

    def test_invalid_scope_rejected(self):
        from umh.control.identity import InMemoryIdentityStore

        store = InMemoryIdentityStore()
        with pytest.raises(ValueError, match="Invalid scope"):
            store.create_identity("bad", ["not_a_real_scope"])


# ═══════════════════════════════════════════════════════════════════════
# 2. Trace Store
# ═══════════════════════════════════════════════════════════════════════


class TestTraceStore:
    def test_create_trace(self):
        from umh.control.trace_store import InMemoryTraceStore

        store = InMemoryTraceStore()
        tid = store.create_trace(user_id="user1", input_summary="hello")
        assert tid.startswith("trace_")

    def test_append_event(self):
        from umh.control.trace_store import InMemoryTraceStore

        store = InMemoryTraceStore()
        tid = store.create_trace(user_id="user1")
        store.append_event(tid, "governance_decision", {"allowed": True})
        record = store.get_trace(tid)
        assert len(record.events) == 1
        assert record.events[0].event_type == "governance_decision"

    def test_complete_trace(self):
        from umh.control.trace_store import InMemoryTraceStore

        store = InMemoryTraceStore()
        tid = store.create_trace()
        store.complete_trace(tid, {"response": "done"})
        record = store.get_trace(tid)
        assert record.status == "completed"
        assert record.result == {"response": "done"}
        assert record.completed_at is not None

    def test_fail_trace(self):
        from umh.control.trace_store import InMemoryTraceStore

        store = InMemoryTraceStore()
        tid = store.create_trace()
        store.fail_trace(tid, "something broke")
        record = store.get_trace(tid)
        assert record.status == "failed"
        assert record.error == "something broke"

    def test_get_nonexistent_trace(self):
        from umh.control.trace_store import InMemoryTraceStore

        store = InMemoryTraceStore()
        assert store.get_trace("trace_nonexistent") is None

    def test_list_traces_ordering(self):
        from umh.control.trace_store import InMemoryTraceStore

        store = InMemoryTraceStore()
        t1 = store.create_trace(input_summary="first")
        t2 = store.create_trace(input_summary="second")
        t3 = store.create_trace(input_summary="third")
        traces = store.list_traces()
        assert len(traces) == 3
        assert traces[0].trace_id == t3

    def test_list_traces_limit(self):
        from umh.control.trace_store import InMemoryTraceStore

        store = InMemoryTraceStore()
        for i in range(10):
            store.create_trace(input_summary=f"trace_{i}")
        traces = store.list_traces(limit=3)
        assert len(traces) == 3

    def test_trace_to_dict(self):
        from umh.control.trace_store import InMemoryTraceStore

        store = InMemoryTraceStore()
        tid = store.create_trace(user_id="user1", input_summary="test")
        store.append_event(tid, "step", {"n": 1})
        store.complete_trace(tid, {"ok": True})
        record = store.get_trace(tid)
        d = record.to_dict()
        assert d["trace_id"] == tid
        assert d["status"] == "completed"
        assert len(d["events"]) == 1

    def test_append_to_nonexistent(self):
        from umh.control.trace_store import InMemoryTraceStore

        store = InMemoryTraceStore()
        store.append_event("trace_ghost", "event", {"x": 1})

    def test_input_summary_truncation(self):
        from umh.control.trace_store import InMemoryTraceStore

        store = InMemoryTraceStore()
        long_input = "x" * 600
        tid = store.create_trace(input_summary=long_input)
        record = store.get_trace(tid)
        assert len(record.input_summary) == 500


# ═══════════════════════════════════════════════════════════════════════
# 3. Governance Gate — evaluate()
# ═══════════════════════════════════════════════════════════════════════


class TestGovernanceGate:
    def test_deny_empty_operation(self):
        from umh.execution.governance_gate import GateOutcome, ExecutionDirective, evaluate

        d = ExecutionDirective(operation="", environment="local")
        result = evaluate(d)
        assert result.outcome == GateOutcome.DENY
        assert "Empty" in result.reason

    def test_deny_no_environment(self):
        from umh.execution.governance_gate import GateOutcome, ExecutionDirective, evaluate

        d = ExecutionDirective(operation="answer_query")
        result = evaluate(d)
        assert result.outcome == GateOutcome.DENY
        assert "environment" in result.reason.lower()

    def test_deny_unsafe_operation(self):
        from umh.execution.governance_gate import GateOutcome, ExecutionDirective, evaluate

        for op in [
            "delete_data",
            "execute_shell",
            "send_external",
            "modify_config",
            "financial_transaction",
        ]:
            d = ExecutionDirective(operation=op, environment="local")
            result = evaluate(d)
            assert result.outcome == GateOutcome.DENY, f"{op} should be DENY"
            assert "unsafe" in result.reason.lower()

    def test_allow_safe_operation(self):
        from umh.execution.governance_gate import GateOutcome, ExecutionDirective, evaluate
        from umh.governance.authority import AuthorityLevel

        d = ExecutionDirective(
            operation="answer_query",
            environment="local",
            authority=AuthorityLevel.ANALYZE,
        )
        result = evaluate(d)
        assert result.outcome in (GateOutcome.ALLOW, GateOutcome.NOTIFY)

    def test_gate_decision_to_dict(self):
        from umh.execution.governance_gate import ExecutionDirective, evaluate

        d = ExecutionDirective(operation="answer_query", environment="local")
        result = evaluate(d)
        d_dict = result.to_dict()
        assert "outcome" in d_dict
        assert "reason" in d_dict
        assert "authority_level" in d_dict
        assert "evaluated_at" in d_dict

    def test_user_id_in_metadata(self):
        from umh.execution.governance_gate import ExecutionDirective, evaluate

        d = ExecutionDirective(operation="answer_query", environment="local")
        result = evaluate(d, user_id="user_123")
        if result.outcome.value in ("allow", "notify"):
            assert result.metadata.get("user_id") == "user_123"

    def test_no_user_id_empty_metadata(self):
        from umh.execution.governance_gate import ExecutionDirective, evaluate

        d = ExecutionDirective(operation="answer_query", environment="local")
        result = evaluate(d, user_id="")
        if result.outcome.value in ("allow", "notify"):
            assert "user_id" not in result.metadata


# ═══════════════════════════════════════════════════════════════════════
# 4. Backend Registry
# ═══════════════════════════════════════════════════════════════════════


class TestBackendRegistry:
    def test_default_environments(self):
        from umh.execution.backend_registry import ExecutionBackendRegistry

        reg = ExecutionBackendRegistry()
        envs = reg.list_environments()
        assert "null" in envs
        assert "local" in envs
        assert "test" in envs

    def test_register_custom_backend(self):
        from umh.execution.backend_registry import ExecutionBackendRegistry
        from umh.execution.interfaces import NullExecutionBackend

        reg = ExecutionBackendRegistry()
        backend = NullExecutionBackend()
        reg.register("sandbox", backend, name="SandboxBackend")
        assert reg.has("sandbox")
        assert reg.get("sandbox") is backend

    def test_select_backend(self):
        from umh.execution.backend_registry import ExecutionBackendRegistry

        reg = ExecutionBackendRegistry()
        result = reg.select_backend("local")
        assert result["name"] == "null"
        assert result["environment"] == "local"
        assert result["backend"] is not None

    def test_select_unknown_raises(self):
        from umh.execution.backend_registry import ExecutionBackendRegistry

        reg = ExecutionBackendRegistry()
        with pytest.raises(ValueError, match="No backend registered"):
            reg.select_backend("production_cluster")

    def test_register_empty_name_raises(self):
        from umh.execution.backend_registry import ExecutionBackendRegistry
        from umh.execution.interfaces import NullExecutionBackend

        reg = ExecutionBackendRegistry()
        with pytest.raises(ValueError, match="must not be empty"):
            reg.register("", NullExecutionBackend())

    def test_reset_restores_defaults(self):
        from umh.execution.backend_registry import ExecutionBackendRegistry
        from umh.execution.interfaces import NullExecutionBackend

        reg = ExecutionBackendRegistry()
        reg.register("custom", NullExecutionBackend())
        assert reg.has("custom")
        reg.reset()
        assert not reg.has("custom")
        assert reg.has("local")

    def test_discover_default_backends(self):
        from umh.execution.backend_registry import ExecutionBackendRegistry

        reg = ExecutionBackendRegistry()
        envs = reg.discover_default_backends()
        assert isinstance(envs, list)
        assert "null" in envs

    def test_singleton_get_backend_registry(self):
        from umh.execution.backend_registry import get_backend_registry

        r1 = get_backend_registry()
        r2 = get_backend_registry()
        assert r1 is r2


# ═══════════════════════════════════════════════════════════════════════
# 5. Governed Execution (full flow)
# ═══════════════════════════════════════════════════════════════════════


class TestGovernedExecution:
    def _make_stores(self):
        from umh.control.trace_store import InMemoryTraceStore
        from umh.execution.backend_registry import ExecutionBackendRegistry

        return InMemoryTraceStore(), ExecutionBackendRegistry()

    def test_blocked_no_environment(self):
        from umh.execution.governance_gate import ExecutionDirective, execute_governed

        ts, br = self._make_stores()
        d = ExecutionDirective(operation="answer_query")
        result = execute_governed(d, trace_store=ts, backend_registry=br)
        assert result["success"] is False
        assert result["trace_id"].startswith("trace_")

    def test_blocked_unsafe_op(self):
        from umh.execution.governance_gate import ExecutionDirective, execute_governed

        ts, br = self._make_stores()
        d = ExecutionDirective(operation="delete_data", environment="local")
        result = execute_governed(d, trace_store=ts, backend_registry=br)
        assert result["success"] is False
        assert "unsafe" in result["response"].lower()

    def test_full_flow_with_null_backend(self):
        from umh.execution.governance_gate import ExecutionDirective, execute_governed
        from umh.governance.authority import AuthorityLevel

        ts, br = self._make_stores()
        d = ExecutionDirective(
            operation="answer_query",
            inputs={"prompt": "hello"},
            environment="local",
            authority=AuthorityLevel.ANALYZE,
        )
        result = execute_governed(d, user_id="test_user", trace_store=ts, backend_registry=br)
        assert result["trace_id"].startswith("trace_")
        assert result["execution_id"].startswith("exec_")
        assert "governance" in result

    def test_trace_events_recorded(self):
        from umh.execution.governance_gate import ExecutionDirective, execute_governed
        from umh.governance.authority import AuthorityLevel

        ts, br = self._make_stores()
        d = ExecutionDirective(
            operation="answer_query",
            inputs={"prompt": "test"},
            environment="local",
            authority=AuthorityLevel.ANALYZE,
        )
        result = execute_governed(d, trace_store=ts, backend_registry=br)
        trace = ts.get_trace(result["trace_id"])
        assert trace is not None
        event_types = [e.event_type for e in trace.events]
        assert "directive_received" in event_types
        assert "governance_decision" in event_types

    def test_unknown_environment_fails(self):
        from umh.execution.governance_gate import ExecutionDirective, execute_governed
        from umh.governance.authority import AuthorityLevel

        ts, br = self._make_stores()
        d = ExecutionDirective(
            operation="answer_query",
            environment="nonexistent_cluster",
            authority=AuthorityLevel.ANALYZE,
        )
        result = execute_governed(d, trace_store=ts, backend_registry=br)
        assert result["success"] is False

    def test_governance_dict_in_result(self):
        from umh.execution.governance_gate import ExecutionDirective, execute_governed

        ts, br = self._make_stores()
        d = ExecutionDirective(operation="answer_query", environment="local")
        result = execute_governed(d, trace_store=ts, backend_registry=br)
        gov = result["governance"]
        assert "outcome" in gov
        assert "reason" in gov


# ═══════════════════════════════════════════════════════════════════════
# 6. Control Plane Endpoints
# ═══════════════════════════════════════════════════════════════════════


class TestControlPlaneEndpoints:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from umh.control.api import app
        from umh.control.identity import get_identity_store

        store = get_identity_store()
        _, self.api_key = store.create_identity("test-admin", ["admin"])
        return TestClient(app, raise_server_exceptions=False)

    def _headers(self):
        return {"X-API-Key": self.api_key}

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_run_direct_missing_auth(self, client):
        resp = client.post("/run/direct", json={"operation": "answer_query"})
        assert resp.status_code == 401

    def test_run_direct_safe_op(self, client):
        resp = client.post(
            "/run/direct",
            headers=self._headers(),
            json={
                "operation": "answer_query",
                "environment": "local",
                "inputs": {"prompt": "test"},
            },
        )
        assert resp.status_code in (200, 422)
        data = resp.json()
        assert "trace_id" in data
        assert "governance" in data

    def test_run_direct_unsafe_op(self, client):
        resp = client.post(
            "/run/direct",
            headers=self._headers(),
            json={
                "operation": "delete_data",
                "environment": "local",
            },
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["success"] is False

    def test_run_direct_invalid_authority(self, client):
        resp = client.post(
            "/run/direct",
            headers=self._headers(),
            json={
                "operation": "answer_query",
                "environment": "local",
                "authority": "godmode",
            },
        )
        assert resp.status_code == 400

    def test_get_traces_empty(self, client):
        resp = client.get("/traces", headers=self._headers())
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_trace_not_found(self, client):
        resp = client.get("/traces/trace_nonexistent", headers=self._headers())
        assert resp.status_code == 404

    def test_run_then_fetch_trace(self, client):
        resp = client.post(
            "/run/direct",
            headers=self._headers(),
            json={
                "operation": "answer_query",
                "environment": "local",
                "inputs": {"prompt": "end to end"},
            },
        )
        data = resp.json()
        trace_id = data["trace_id"]

        trace_resp = client.get(f"/traces/{trace_id}", headers=self._headers())
        assert trace_resp.status_code == 200
        trace_data = trace_resp.json()
        assert trace_data["trace_id"] == trace_id
        assert len(trace_data["events"]) >= 2

    def test_traces_list_after_run(self, client):
        client.post(
            "/run/direct",
            headers=self._headers(),
            json={"operation": "summarize", "environment": "local"},
        )
        resp = client.get("/traces", headers=self._headers())
        assert resp.status_code == 200
        traces = resp.json()
        assert len(traces) >= 1

    def test_run_direct_scope_check(self, client):
        from umh.control.identity import get_identity_store

        store = get_identity_store()
        _, reader_key = store.create_identity("reader", ["metrics:read"])
        resp = client.post(
            "/run/direct",
            headers={"X-API-Key": reader_key},
            json={"operation": "answer_query", "environment": "local"},
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════
# 7. Intelligence Kernel Hook
# ═══════════════════════════════════════════════════════════════════════


class TestIntelligenceHook:
    def test_disabled_by_default(self):
        from umh.runtime.enrichment import is_enabled

        assert not is_enabled()

    def test_returns_empty_when_disabled(self):
        from umh.runtime.enrichment import enrich_decision

        result = enrich_decision(
            operation="answer_query",
            intent_confidence=0.9,
            goal_active=False,
        )
        assert result == {}

    def test_returns_empty_on_kernel_error(self):
        """When the kernel raises, enrichment returns {} instead of propagating."""
        import importlib
        import umh.runtime.enrichment as enrichment_mod

        with patch.dict(os.environ, {"UMH_INTELLIGENCE_ENRICHMENT": "1"}):
            original_import = (
                __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__
            )

            def mock_import(name, *args, **kwargs):
                if "weighted_decision" in name:
                    raise ImportError("simulated kernel failure")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                result = enrichment_mod.enrich_decision(
                    operation="answer_query",
                    intent_confidence=0.9,
                    goal_active=False,
                )
                assert result == {}

    def test_enabled_flag(self):
        from umh.runtime.enrichment import is_enabled

        with patch.dict(os.environ, {"UMH_INTELLIGENCE_ENRICHMENT": "1"}):
            assert is_enabled()


# ═══════════════════════════════════════════════════════════════════════
# 8. Layering Invariants
# ═══════════════════════════════════════════════════════════════════════


class TestLayeringInvariants:
    def test_governance_gate_does_not_import_substrate(self):
        import ast

        with open("umh/execution/governance_gate.py") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = getattr(node, "module", "") or ""
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "substrate" not in alias.name, (
                            f"governance_gate imports substrate: {alias.name}"
                        )
                else:
                    assert "substrate" not in module, f"governance_gate imports substrate: {module}"

    def test_trace_store_does_not_import_execution(self):
        import ast

        with open("umh/control/trace_store.py") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("umh.execution"), (
                    f"trace_store imports execution: {node.module}"
                )

    def test_backend_registry_does_not_import_governance(self):
        import ast

        with open("umh/execution/backend_registry.py") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("umh.governance"), (
                    f"backend_registry imports governance: {node.module}"
                )

    def test_enrichment_is_pure_computation(self):
        import ast

        with open("umh/runtime/enrichment.py") as f:
            tree = ast.parse(f.read())
        forbidden = {"subprocess", "umh.adapters", "umh.substrate", "umh.cells"}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for f_mod in forbidden:
                    assert not node.module.startswith(f_mod), (
                        f"enrichment.py imports forbidden module: {node.module}"
                    )

    def test_all_new_modules_import_clean(self):
        modules = [
            "umh.control.trace_store",
            "umh.execution.governance_gate",
            "umh.execution.backend_registry",
            "umh.runtime.enrichment",
        ]
        for mod in modules:
            __import__(mod)

    def test_gate_outcome_values(self):
        from umh.execution.governance_gate import GateOutcome

        expected = {"allow", "notify", "approve_required", "escalate", "deny"}
        actual = {o.value for o in GateOutcome}
        assert actual == expected

    def test_execution_directive_frozen(self):
        from umh.execution.governance_gate import ExecutionDirective

        d = ExecutionDirective(operation="test", environment="local")
        with pytest.raises(AttributeError):
            d.operation = "changed"

    def test_gate_decision_frozen(self):
        from umh.execution.governance_gate import GateDecision, GateOutcome
        from umh.governance.authority import AuthorityLevel

        gd = GateDecision(
            outcome=GateOutcome.ALLOW,
            reason="ok",
            authority_level=AuthorityLevel.ANALYZE,
            evaluated_at="2026-01-01T00:00:00Z",
        )
        with pytest.raises(AttributeError):
            gd.outcome = GateOutcome.DENY


# ═══════════════════════════════════════════════════════════════════════
# 9. Cross-component Integration
# ═══════════════════════════════════════════════════════════════════════


class TestCrossComponentIntegration:
    def test_identity_to_governed_execution(self):
        from umh.control.identity import InMemoryIdentityStore
        from umh.control.trace_store import InMemoryTraceStore
        from umh.execution.backend_registry import ExecutionBackendRegistry
        from umh.execution.governance_gate import ExecutionDirective, execute_governed

        id_store = InMemoryIdentityStore()
        identity, _ = id_store.create_identity("api-caller", ["execute"])

        ts = InMemoryTraceStore()
        br = ExecutionBackendRegistry()

        d = ExecutionDirective(
            operation="answer_query",
            inputs={"prompt": "What time is it?"},
            environment="local",
        )
        result = execute_governed(d, user_id=identity.id, trace_store=ts, backend_registry=br)
        assert result["trace_id"].startswith("trace_")

        trace = ts.get_trace(result["trace_id"])
        assert trace is not None
        assert trace.user_id == identity.id

    def test_multiple_runs_produce_distinct_traces(self):
        from umh.control.trace_store import InMemoryTraceStore
        from umh.execution.backend_registry import ExecutionBackendRegistry
        from umh.execution.governance_gate import ExecutionDirective, execute_governed

        ts = InMemoryTraceStore()
        br = ExecutionBackendRegistry()

        trace_ids = set()
        for i in range(5):
            d = ExecutionDirective(
                operation="answer_query",
                inputs={"n": i},
                environment="local",
            )
            result = execute_governed(d, trace_store=ts, backend_registry=br)
            trace_ids.add(result["trace_id"])

        assert len(trace_ids) == 5
        assert len(ts.list_traces()) == 5

    def test_governance_blocks_before_backend_selection(self):
        from umh.control.trace_store import InMemoryTraceStore
        from umh.execution.backend_registry import ExecutionBackendRegistry
        from umh.execution.governance_gate import ExecutionDirective, execute_governed

        ts = InMemoryTraceStore()
        br = ExecutionBackendRegistry()

        d = ExecutionDirective(operation="delete_data", environment="local")
        result = execute_governed(d, trace_store=ts, backend_registry=br)
        assert result["success"] is False

        trace = ts.get_trace(result["trace_id"])
        event_types = [e.event_type for e in trace.events]
        assert "governance_decision" in event_types
        assert "backend_selected" not in event_types
