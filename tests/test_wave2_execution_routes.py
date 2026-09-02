"""Wave 2 C6 — execution read-surface routes (thin adapter, never 500 on reads)."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from fastapi import FastAPI  # noqa: E402

from substrate.execution.attempts.records import ExecutionAttempt  # noqa: E402
from substrate.execution.attempts.store import ExecutionAttemptStore  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Point the store's module-level default paths at a tmp dir (the documented
    # monkeypatch seam) so the route's ExecutionAttemptStore() and the seed store
    # share the same files regardless of import order.
    import substrate.execution.attempts.store as store_mod

    monkeypatch.setattr(store_mod, "_DEFAULT_ATTEMPTS_PATH", str(tmp_path / "a.jsonl"))
    monkeypatch.setattr(store_mod, "_DEFAULT_GRANTS_PATH", str(tmp_path / "g.jsonl"))
    monkeypatch.setattr(store_mod, "_DEFAULT_READINESS_PATH", str(tmp_path / "r.jsonl"))
    monkeypatch.setattr(store_mod, "_DEFAULT_LEASES_PATH", str(tmp_path / "l.jsonl"))
    monkeypatch.setattr(store_mod, "_DEFAULT_ASSIGNMENTS_PATH", str(tmp_path / "asn.jsonl"))

    store = ExecutionAttemptStore()
    # The attempt carries a REAL tenant, and the caller resolves to the same
    # one. This fixture previously seeded tenant_id="" and relied on the read
    # routes treating an empty tenant as "visible to everyone" — i.e. these
    # tests were passing BECAUSE of the fail-open that adversarial review found
    # (an empty-tenant attempt was globally readable AND cancellable). Empty is
    # now DENY on both sides, so the fixture must model a real operator.
    a = ExecutionAttempt(
        task_id="wp-a",
        plan_record_id="opr-1",
        tenant_id="tenant-fixture",
        execution_authorization_ref="ref",
        status="running",
        worker_identity="w",
    )
    store.create_attempt_idempotent(a)

    import substrate.contracts.principal_resolution as principal

    class _Ctx:
        tenant_id = "tenant-fixture"

    monkeypatch.setattr(principal, "resolve_principal_context", lambda *args, **kw: _Ctx())

    from transports.api import execution_attempt_routes

    app = FastAPI()
    execution_attempt_routes.mount(app)
    return TestClient(app), a


def test_attempts_list(client):
    c, a = client
    resp = c.get("/execution/attempts")
    assert resp.status_code == 200
    body = resp.json()
    assert "attempts" in body
    assert any(r["attempt_id"] == a.attempt_id for r in body["attempts"])


def test_attempt_detail(client):
    c, a = client
    resp = c.get(f"/execution/attempts/{a.attempt_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["attempt_id"] == a.attempt_id
    assert body["cancel_allowed"] is True  # running → cancellable
    assert "transitions" in body


def test_reads_never_500(client):
    c, _ = client
    for path in (
        "/execution/attempts",
        "/execution/frontier",
        "/execution/authorizations",
        "/execution/by-plan/opr-1",
        "/execution/overlay?packet_ids=wp-a",
        "/execution/attempts/nonexistent",
    ):
        assert c.get(path).status_code == 200, path


def test_retry_fails_closed_without_active_grant(client):
    c, a = client
    # The attempt is running (not failed) → retry refused.
    resp = c.post(f"/execution/attempts/{a.attempt_id}/retry", json={})
    assert resp.status_code == 200
    assert resp.json()["success"] is False
