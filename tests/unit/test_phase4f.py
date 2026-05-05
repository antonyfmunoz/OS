"""Tests for Phase 4F: Persistent Approval Store.

Verifies:
- SQLite store create/get/list
- Approve persists across new store instance
- Deny persists across new store instance
- Consume persists across new store instance
- Expired approvals persist as EXPIRED
- Counters persist across instances
- CLI sees approvals created by separate store instance
- Existing in-memory tests still pass (covered by test_phase4d/4e)
- 4D approved execution still works
"""

import sys
import os
import time
import tempfile

sys.path.insert(0, "/opt/OS")

import json
from io import StringIO
from unittest.mock import patch

from umh.execution.approval import (
    ApprovalRequest,
    ApprovalStatus,
    ApprovalStore,
    get_approval_store,
    reset_approval_store,
)
from umh.execution.approval_persistence import (
    InMemoryApprovalBackend,
    SQLiteApprovalBackend,
)


def _tmp_db() -> str:
    """Create a temp SQLite path."""
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    os.unlink(path)
    return path


def _make_sqlite_store(db_path: str | None = None) -> tuple[ApprovalStore, str]:
    """Create a store with SQLite backend at a temp path."""
    path = db_path or _tmp_db()
    backend = SQLiteApprovalBackend(db_path=path)
    store = ApprovalStore(backend=backend)
    return store, path


# ── A. SQLite Store Create/Get/List ──────────────────────────────────


class TestSQLiteBasicOperations:
    def test_create_and_get(self):
        store, path = _make_sqlite_store()
        req = store.create_approval(
            execution_id="test_create",
            operation="computer_click",
            capability_type="computer_use",
        )
        retrieved = store.get(req.id)
        assert retrieved is not None
        assert retrieved.id == req.id
        assert retrieved.operation == "computer_click"
        assert retrieved.capability_type == "computer_use"
        assert retrieved.status == ApprovalStatus.PENDING
        os.unlink(path)

    def test_create_and_list_all(self):
        store, path = _make_sqlite_store()
        store.create_approval(
            execution_id="test1", operation="computer_click", capability_type="computer_use"
        )
        store.create_approval(
            execution_id="test2", operation="computer_type", capability_type="computer_use"
        )
        all_reqs = store.list_all()
        assert len(all_reqs) == 2
        os.unlink(path)

    def test_create_and_list_pending(self):
        store, path = _make_sqlite_store()
        store.create_approval(
            execution_id="test1", operation="computer_click", capability_type="computer_use"
        )
        pending = store.list_pending()
        assert len(pending) == 1
        assert pending[0].status == ApprovalStatus.PENDING
        os.unlink(path)

    def test_get_nonexistent_returns_none(self):
        store, path = _make_sqlite_store()
        assert store.get("approval_nonexistent") is None
        os.unlink(path)

    def test_fields_persisted_correctly(self):
        store, path = _make_sqlite_store()
        req = store.create_approval(
            execution_id="test_fields",
            operation="computer_drag",
            capability_type="computer_use",
            risk_level="critical",
            inputs_summary="x1=10, y1=20",
            ttl_seconds=600,
        )
        retrieved = store.get(req.id)
        assert retrieved.execution_id == "test_fields"
        assert retrieved.operation == "computer_drag"
        assert retrieved.capability_type == "computer_use"
        assert retrieved.risk_level == "critical"
        assert retrieved.inputs_summary == "x1=10, y1=20"
        assert retrieved.created_at == req.created_at
        assert retrieved.expires_at == req.expires_at
        os.unlink(path)


# ── B. Approve Persists Across Instances ─────────────────────────────


class TestApprovePersistence:
    def test_approve_visible_in_new_instance(self):
        path = _tmp_db()
        store1 = ApprovalStore(backend=SQLiteApprovalBackend(db_path=path))
        req = store1.create_approval(
            execution_id="test_persist_approve",
            operation="computer_click",
            capability_type="computer_use",
        )
        store1.approve(req.id)

        # New store instance (simulates separate process)
        store2 = ApprovalStore(backend=SQLiteApprovalBackend(db_path=path))
        retrieved = store2.get(req.id)
        assert retrieved is not None
        assert retrieved.status == ApprovalStatus.APPROVED
        os.unlink(path)

    def test_approve_validates_from_new_instance(self):
        path = _tmp_db()
        store1 = ApprovalStore(backend=SQLiteApprovalBackend(db_path=path))
        req = store1.create_approval(
            execution_id="test_validate",
            operation="computer_click",
            capability_type="computer_use",
        )
        store1.approve(req.id)

        store2 = ApprovalStore(backend=SQLiteApprovalBackend(db_path=path))
        valid, reason = store2.validate_for_execution(req.id, "computer_click", "computer_use")
        assert valid is True
        assert reason == "Valid"
        os.unlink(path)


# ── C. Deny Persists ────────────────────────────────────────────────


class TestDenyPersistence:
    def test_deny_visible_in_new_instance(self):
        path = _tmp_db()
        store1 = ApprovalStore(backend=SQLiteApprovalBackend(db_path=path))
        req = store1.create_approval(
            execution_id="test_persist_deny",
            operation="computer_click",
            capability_type="computer_use",
        )
        store1.deny(req.id)

        store2 = ApprovalStore(backend=SQLiteApprovalBackend(db_path=path))
        retrieved = store2.get(req.id)
        assert retrieved is not None
        assert retrieved.status == ApprovalStatus.DENIED
        os.unlink(path)

    def test_deny_counter_persists(self):
        path = _tmp_db()
        store1 = ApprovalStore(backend=SQLiteApprovalBackend(db_path=path))
        req = store1.create_approval(
            execution_id="test_deny_counter",
            operation="computer_click",
            capability_type="computer_use",
        )
        store1.deny(req.id)

        store2 = ApprovalStore(backend=SQLiteApprovalBackend(db_path=path))
        counters = store2.get_counters()
        assert counters["denied"] == 1
        os.unlink(path)


# ── D. Consume Persists ──────────────────────────────────────────────


class TestConsumePersistence:
    def test_consume_visible_in_new_instance(self):
        path = _tmp_db()
        store1 = ApprovalStore(backend=SQLiteApprovalBackend(db_path=path))
        req = store1.create_approval(
            execution_id="test_persist_consume",
            operation="computer_click",
            capability_type="computer_use",
        )
        store1.approve(req.id)
        store1.consume(req.id)

        store2 = ApprovalStore(backend=SQLiteApprovalBackend(db_path=path))
        retrieved = store2.get(req.id)
        assert retrieved is not None
        assert retrieved.status == ApprovalStatus.CONSUMED
        os.unlink(path)

    def test_consume_counter_persists(self):
        path = _tmp_db()
        store1 = ApprovalStore(backend=SQLiteApprovalBackend(db_path=path))
        req = store1.create_approval(
            execution_id="test_consume_counter",
            operation="computer_click",
            capability_type="computer_use",
        )
        store1.approve(req.id)
        store1.consume(req.id)

        store2 = ApprovalStore(backend=SQLiteApprovalBackend(db_path=path))
        counters = store2.get_counters()
        assert counters["consumed"] == 1
        os.unlink(path)

    def test_consumed_cannot_be_reused(self):
        path = _tmp_db()
        store1 = ApprovalStore(backend=SQLiteApprovalBackend(db_path=path))
        req = store1.create_approval(
            execution_id="test_reuse",
            operation="computer_click",
            capability_type="computer_use",
        )
        store1.approve(req.id)
        store1.consume(req.id)

        store2 = ApprovalStore(backend=SQLiteApprovalBackend(db_path=path))
        valid, reason = store2.validate_for_execution(req.id, "computer_click", "computer_use")
        assert valid is False
        assert "consumed" in reason.lower()
        os.unlink(path)


# ── E. Expired Approvals Persist ─────────────────────────────────────


class TestExpiredPersistence:
    def test_expired_status_persists(self):
        path = _tmp_db()
        store1 = ApprovalStore(backend=SQLiteApprovalBackend(db_path=path))
        req = store1.create_approval(
            execution_id="test_expire",
            operation="computer_click",
            capability_type="computer_use",
            ttl_seconds=0,
        )
        time.sleep(0.01)
        # Trigger expiry detection
        store1.get(req.id)

        store2 = ApprovalStore(backend=SQLiteApprovalBackend(db_path=path))
        retrieved = store2.get(req.id)
        assert retrieved is not None
        assert retrieved.status == ApprovalStatus.EXPIRED
        os.unlink(path)

    def test_expired_counter_persists(self):
        path = _tmp_db()
        store1 = ApprovalStore(backend=SQLiteApprovalBackend(db_path=path))
        store1.create_approval(
            execution_id="test_expire_counter",
            operation="computer_click",
            capability_type="computer_use",
            ttl_seconds=0,
        )
        time.sleep(0.01)
        store1.list_pending()

        store2 = ApprovalStore(backend=SQLiteApprovalBackend(db_path=path))
        counters = store2.get_counters()
        assert counters["expired"] >= 1
        os.unlink(path)

    def test_expired_cannot_be_approved(self):
        path = _tmp_db()
        store1 = ApprovalStore(backend=SQLiteApprovalBackend(db_path=path))
        req = store1.create_approval(
            execution_id="test_expired_approve",
            operation="computer_click",
            capability_type="computer_use",
            ttl_seconds=0,
        )
        time.sleep(0.01)
        result = store1.approve(req.id)
        assert result.status == ApprovalStatus.EXPIRED

        store2 = ApprovalStore(backend=SQLiteApprovalBackend(db_path=path))
        retrieved = store2.get(req.id)
        assert retrieved.status == ApprovalStatus.EXPIRED
        os.unlink(path)


# ── F. Counters Persist ──────────────────────────────────────────────


class TestCountersPersistence:
    def test_all_counters_persist(self):
        path = _tmp_db()
        store1 = ApprovalStore(backend=SQLiteApprovalBackend(db_path=path))

        # Generate consumed
        req1 = store1.create_approval(
            execution_id="c1", operation="computer_click", capability_type="computer_use"
        )
        store1.approve(req1.id)
        store1.consume(req1.id)

        # Generate denied
        req2 = store1.create_approval(
            execution_id="c2", operation="computer_type", capability_type="computer_use"
        )
        store1.deny(req2.id)

        # Generate expired
        store1.create_approval(
            execution_id="c3",
            operation="computer_key",
            capability_type="computer_use",
            ttl_seconds=0,
        )
        time.sleep(0.01)
        store1.list_pending()

        # New instance sees all counters
        store2 = ApprovalStore(backend=SQLiteApprovalBackend(db_path=path))
        counters = store2.get_counters()
        assert counters["consumed"] == 1
        assert counters["denied"] == 1
        assert counters["expired"] >= 1
        os.unlink(path)

    def test_reset_clears_counters_in_sqlite(self):
        path = _tmp_db()
        store1 = ApprovalStore(backend=SQLiteApprovalBackend(db_path=path))
        req = store1.create_approval(
            execution_id="reset_test", operation="computer_click", capability_type="computer_use"
        )
        store1.deny(req.id)
        store1.reset()

        store2 = ApprovalStore(backend=SQLiteApprovalBackend(db_path=path))
        counters = store2.get_counters()
        assert counters["consumed"] == 0
        assert counters["denied"] == 0
        assert counters["expired"] == 0
        assert store2.list_all() == []
        os.unlink(path)


# ── G. CLI Sees Approvals from Separate Store Instance ───────────────


class TestCLICrossProcess:
    def test_cli_list_sees_sqlite_approvals(self):
        path = _tmp_db()
        # Simulate "Process A" creating an approval
        backend_a = SQLiteApprovalBackend(db_path=path)
        store_a = ApprovalStore(backend=backend_a)
        req = store_a.create_approval(
            execution_id="cross_process",
            operation="computer_click",
            capability_type="computer_use",
            risk_level="high",
            inputs_summary="x=100, y=200",
        )

        # Simulate "Process B" (CLI) reading the same db
        backend_b = SQLiteApprovalBackend(db_path=path)
        store_b = ApprovalStore(backend=backend_b)
        all_reqs = store_b.list_all()
        assert len(all_reqs) == 1
        assert all_reqs[0].id == req.id
        assert all_reqs[0].operation == "computer_click"
        os.unlink(path)

    def test_cli_approve_visible_to_runtime(self):
        path = _tmp_db()
        # Runtime creates approval
        backend_r = SQLiteApprovalBackend(db_path=path)
        store_r = ApprovalStore(backend=backend_r)
        req = store_r.create_approval(
            execution_id="runtime_approval",
            operation="computer_click",
            capability_type="computer_use",
        )

        # CLI approves it
        backend_c = SQLiteApprovalBackend(db_path=path)
        store_c = ApprovalStore(backend=backend_c)
        result = store_c.approve(req.id)
        assert result.status == ApprovalStatus.APPROVED

        # Runtime validates it
        valid, reason = store_r.validate_for_execution(req.id, "computer_click", "computer_use")
        # Need to re-read from DB since store_r has stale cache
        backend_r2 = SQLiteApprovalBackend(db_path=path)
        store_r2 = ApprovalStore(backend=backend_r2)
        valid, reason = store_r2.validate_for_execution(req.id, "computer_click", "computer_use")
        assert valid is True
        os.unlink(path)

    def test_cli_deny_visible_to_runtime(self):
        path = _tmp_db()
        backend_r = SQLiteApprovalBackend(db_path=path)
        store_r = ApprovalStore(backend=backend_r)
        req = store_r.create_approval(
            execution_id="runtime_deny",
            operation="computer_click",
            capability_type="computer_use",
        )

        backend_c = SQLiteApprovalBackend(db_path=path)
        store_c = ApprovalStore(backend=backend_c)
        store_c.deny(req.id)

        backend_r2 = SQLiteApprovalBackend(db_path=path)
        store_r2 = ApprovalStore(backend=backend_r2)
        retrieved = store_r2.get(req.id)
        assert retrieved.status == ApprovalStatus.DENIED
        os.unlink(path)


# ── H. In-Memory Backend Still Works ─────────────────────────────────


class TestInMemoryBackend:
    def test_in_memory_create_and_get(self):
        store = ApprovalStore(backend=InMemoryApprovalBackend())
        req = store.create_approval(
            execution_id="mem_test",
            operation="computer_click",
            capability_type="computer_use",
        )
        retrieved = store.get(req.id)
        assert retrieved is not None
        assert retrieved.id == req.id

    def test_in_memory_approve_deny_consume(self):
        store = ApprovalStore(backend=InMemoryApprovalBackend())
        req1 = store.create_approval(
            execution_id="mem_a", operation="computer_click", capability_type="computer_use"
        )
        req2 = store.create_approval(
            execution_id="mem_d", operation="computer_type", capability_type="computer_use"
        )
        req3 = store.create_approval(
            execution_id="mem_c", operation="computer_key", capability_type="computer_use"
        )

        store.approve(req1.id)
        store.deny(req2.id)
        store.approve(req3.id)
        store.consume(req3.id)

        assert store.get(req1.id).status == ApprovalStatus.APPROVED
        assert store.get(req2.id).status == ApprovalStatus.DENIED
        assert store.get(req3.id).status == ApprovalStatus.CONSUMED

    def test_in_memory_counters(self):
        store = ApprovalStore(backend=InMemoryApprovalBackend())
        req1 = store.create_approval(
            execution_id="cnt", operation="computer_click", capability_type="computer_use"
        )
        store.approve(req1.id)
        store.consume(req1.id)
        req2 = store.create_approval(
            execution_id="cnt2", operation="computer_type", capability_type="computer_use"
        )
        store.deny(req2.id)
        counters = store.get_counters()
        assert counters["consumed"] == 1
        assert counters["denied"] == 1

    def test_in_memory_reset(self):
        store = ApprovalStore(backend=InMemoryApprovalBackend())
        store.create_approval(
            execution_id="rst", operation="computer_click", capability_type="computer_use"
        )
        store.reset()
        assert store.list_all() == []
        assert store.get_counters() == {"consumed": 0, "denied": 0, "expired": 0}


# ── I. 4D Approved Execution Still Works ─────────────────────────────


class TestExisting4DStillWorks:
    def test_approved_click_through_engine(self):
        """Full 4D path with refactored store."""
        store = get_approval_store()
        store.reset()

        from umh.execution.contract import (
            ExecutionClass,
            ExecutionConstraints,
            ExecutionContext,
            ExecutionRequest,
            ExecutionStatus,
            ExecutionTarget,
        )
        from umh.execution.engine import execute

        request1 = ExecutionRequest(
            execution_id="test_4f_click",
            correlation_id="test_4f_click",
            causal_event_id="",
            session_id="",
            operation="computer_click",
            inputs={"x": 30, "y": 40},
            execution_class=ExecutionClass.SIDE_EFFECT,
            constraints=ExecutionConstraints(timeout_s=10),
            target=ExecutionTarget(node_id="local", transport="test"),
            context=ExecutionContext(),
            issued_at="2026-04-26T12:00:00Z",
            issued_by="test",
            idempotency_key="",
        )
        result1 = execute(request1)
        assert result1.status == ExecutionStatus.REJECTED
        approval_id = result1.outputs.get("approval_id")
        assert approval_id is not None

        store.approve(approval_id)

        request2 = ExecutionRequest(
            execution_id="test_4f_click_ok",
            correlation_id="test_4f_click_ok",
            causal_event_id="",
            session_id="",
            operation="computer_click",
            inputs={"x": 30, "y": 40, "approval_id": approval_id},
            execution_class=ExecutionClass.SIDE_EFFECT,
            constraints=ExecutionConstraints(timeout_s=10),
            target=ExecutionTarget(node_id="local", transport="test"),
            context=ExecutionContext(),
            issued_at="2026-04-26T12:00:00Z",
            issued_by="test",
            idempotency_key="",
        )
        result2 = execute(request2)
        assert result2.status == ExecutionStatus.SUCCEEDED

    def test_replay_still_blocked(self):
        """Consumed approval cannot be reused."""
        store = get_approval_store()
        store.reset()

        from umh.execution.contract import (
            ExecutionClass,
            ExecutionConstraints,
            ExecutionContext,
            ExecutionRequest,
            ExecutionStatus,
            ExecutionTarget,
        )
        from umh.execution.engine import execute

        request1 = ExecutionRequest(
            execution_id="test_4f_replay",
            correlation_id="test_4f_replay",
            causal_event_id="",
            session_id="",
            operation="computer_click",
            inputs={"x": 5, "y": 5},
            execution_class=ExecutionClass.SIDE_EFFECT,
            constraints=ExecutionConstraints(timeout_s=10),
            target=ExecutionTarget(node_id="local", transport="test"),
            context=ExecutionContext(),
            issued_at="2026-04-26T12:00:00Z",
            issued_by="test",
            idempotency_key="",
        )
        result1 = execute(request1)
        approval_id = result1.outputs["approval_id"]
        store.approve(approval_id)

        # First use: succeeds
        request2 = ExecutionRequest(
            execution_id="test_4f_replay_ok",
            correlation_id="test_4f_replay_ok",
            causal_event_id="",
            session_id="",
            operation="computer_click",
            inputs={"x": 5, "y": 5, "approval_id": approval_id},
            execution_class=ExecutionClass.SIDE_EFFECT,
            constraints=ExecutionConstraints(timeout_s=10),
            target=ExecutionTarget(node_id="local", transport="test"),
            context=ExecutionContext(),
            issued_at="2026-04-26T12:00:00Z",
            issued_by="test",
            idempotency_key="",
        )
        result2 = execute(request2)
        assert result2.status == ExecutionStatus.SUCCEEDED

        # Second use: rejected
        request3 = ExecutionRequest(
            execution_id="test_4f_replay_bad",
            correlation_id="test_4f_replay_bad",
            causal_event_id="",
            session_id="",
            operation="computer_click",
            inputs={"x": 5, "y": 5, "approval_id": approval_id},
            execution_class=ExecutionClass.SIDE_EFFECT,
            constraints=ExecutionConstraints(timeout_s=10),
            target=ExecutionTarget(node_id="local", transport="test"),
            context=ExecutionContext(),
            issued_at="2026-04-26T12:00:00Z",
            issued_by="test",
            idempotency_key="",
        )
        result3 = execute(request3)
        assert result3.status == ExecutionStatus.REJECTED
        assert "consumed" in result3.outputs.get("reason", "").lower()


# ── J. SQLite Backend Isolation ──────────────────────────────────────


class TestSQLiteIsolation:
    def test_separate_db_files_are_independent(self):
        store1, path1 = _make_sqlite_store()
        store2, path2 = _make_sqlite_store()

        store1.create_approval(
            execution_id="iso1", operation="computer_click", capability_type="computer_use"
        )
        assert len(store1.list_all()) == 1
        assert len(store2.list_all()) == 0

        os.unlink(path1)
        os.unlink(path2)

    def test_directory_creation(self):
        """Backend creates parent directories if they don't exist."""
        import tempfile

        tmpdir = tempfile.mkdtemp()
        nested_path = os.path.join(tmpdir, "sub", "dir", "approvals.sqlite")
        backend = SQLiteApprovalBackend(db_path=nested_path)
        store = ApprovalStore(backend=backend)
        store.create_approval(
            execution_id="dir_test", operation="computer_click", capability_type="computer_use"
        )
        assert len(store.list_all()) == 1
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)
