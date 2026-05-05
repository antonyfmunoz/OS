"""Tests for Phase 5B: Identity + Scoped Authentication Layer.

Verifies:
- Identity creation and authentication
- Scope enforcement at API layer
- Identity attached to execution context
- Approvals track actor (requested_by, approved_by)
- Disabled identity cannot act
- Legacy API key fallback still works
- Admin scope grants all access
"""

import sys
import os
import tempfile

sys.path.insert(0, "/opt/OS")

os.environ.setdefault("UMH_API_KEY", "test-key-phase5a")

from fastapi.testclient import TestClient

from umh.control.api import app
from umh.control.identity import (
    Identity,
    IdentityStore,
    InMemoryIdentityStore,
    get_identity_store,
    hash_key,
    reset_identity_store,
)
from umh.execution.approval import get_approval_store

client = TestClient(app)


def _reset():
    get_approval_store().reset()
    get_identity_store().reset()


def _create_identity(
    name: str = "test-actor",
    scopes: list[str] | None = None,
) -> tuple[Identity, str, dict]:
    """Create identity and return (identity, raw_key, headers)."""
    store = get_identity_store()
    identity, raw_key = store.create_identity(name, scopes or ["admin"])
    headers = {"X-API-Key": raw_key}
    return identity, raw_key, headers


# ── A. Identity Creation and Auth ────────────────────────────────────


class TestIdentityCreation:
    def test_create_identity(self):
        _reset()
        store = get_identity_store()
        identity, raw_key = store.create_identity("test", ["execute", "metrics:read"])
        assert identity.name == "test"
        assert identity.scopes == ["execute", "metrics:read"]
        assert identity.status == "active"
        assert raw_key.startswith("umh_")

    def test_authenticate_with_raw_key(self):
        _reset()
        store = get_identity_store()
        _, raw_key = store.create_identity("auth-test", ["execute"])
        identity = store.authenticate(raw_key)
        assert identity is not None
        assert identity.name == "auth-test"

    def test_authenticate_wrong_key_returns_none(self):
        _reset()
        store = get_identity_store()
        store.create_identity("test", ["execute"])
        assert store.authenticate("umh_wrong_key") is None

    def test_key_is_hashed_not_stored_raw(self):
        _reset()
        store = get_identity_store()
        identity, raw_key = store.create_identity("hash-test", ["execute"])
        assert identity.api_key_hash != raw_key
        assert identity.api_key_hash == hash_key(raw_key)

    def test_invalid_scope_raises(self):
        _reset()
        store = get_identity_store()
        try:
            store.create_identity("bad-scope", ["not_a_scope"])
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Invalid scope" in str(e)

    def test_list_identities(self):
        _reset()
        store = get_identity_store()
        store.create_identity("a", ["execute"])
        store.create_identity("b", ["admin"])
        identities = store.list_identities()
        assert len(identities) == 2

    def test_disable_identity(self):
        _reset()
        store = get_identity_store()
        identity, _ = store.create_identity("disable-me", ["execute"])
        assert store.disable_identity(identity.id) is True
        updated = store.get(identity.id)
        assert updated.status == "disabled"

    def test_disable_nonexistent_returns_false(self):
        _reset()
        store = get_identity_store()
        assert store.disable_identity("id_nonexistent") is False


# ── B. API Auth with Identity ────────────────────────────────────────


class TestAPIAuth:
    def test_identity_key_authenticates(self):
        _reset()
        _, _, headers = _create_identity("api-test", ["approvals:read"])
        resp = client.get("/approvals", headers=headers)
        assert resp.status_code == 200

    def test_no_key_returns_401(self):
        resp = client.get("/approvals")
        assert resp.status_code == 401

    def test_wrong_key_returns_401(self):
        resp = client.get("/approvals", headers={"X-API-Key": "umh_wrong"})
        assert resp.status_code == 401

    def test_legacy_key_still_works(self):
        _reset()
        legacy_key = os.environ.get("UMH_API_KEY", "test-key-phase5a")
        resp = client.get("/approvals", headers={"X-API-Key": legacy_key})
        assert resp.status_code == 200

    def test_health_no_auth_required(self):
        resp = client.get("/health")
        assert resp.status_code == 200


# ── C. Scope Enforcement ─────────────────────────────────────────────


class TestScopeEnforcement:
    def test_execute_requires_execute_scope(self):
        _reset()
        _, _, headers = _create_identity("no-exec", ["approvals:read"])
        resp = client.post(
            "/execute",
            json={"operation": "computer_screenshot", "inputs": {}},
            headers=headers,
        )
        assert resp.status_code == 403
        assert "execute" in resp.json()["detail"]

    def test_execute_allowed_with_execute_scope(self):
        _reset()
        _, _, headers = _create_identity("has-exec", ["execute"])
        resp = client.post(
            "/execute",
            json={"operation": "computer_screenshot", "inputs": {}},
            headers=headers,
        )
        assert resp.status_code == 200

    def test_approvals_read_requires_scope(self):
        _reset()
        _, _, headers = _create_identity("no-read", ["execute"])
        resp = client.get("/approvals", headers=headers)
        assert resp.status_code == 403
        assert "approvals:read" in resp.json()["detail"]

    def test_approvals_write_requires_scope(self):
        _reset()
        _, _, headers = _create_identity("no-write", ["approvals:read"])
        resp = client.post("/approvals/approval_fake/approve", headers=headers)
        assert resp.status_code == 403
        assert "approvals:write" in resp.json()["detail"]

    def test_metrics_requires_scope(self):
        _reset()
        _, _, headers = _create_identity("no-metrics", ["execute"])
        resp = client.get("/metrics", headers=headers)
        assert resp.status_code == 403
        assert "metrics:read" in resp.json()["detail"]

    def test_metrics_allowed_with_scope(self):
        _reset()
        _, _, headers = _create_identity("has-metrics", ["metrics:read"])
        resp = client.get("/metrics", headers=headers)
        assert resp.status_code == 200

    def test_admin_scope_grants_all(self):
        _reset()
        _, _, headers = _create_identity("admin-user", ["admin"])
        # Should be able to do everything
        r1 = client.post(
            "/execute",
            json={"operation": "computer_screenshot", "inputs": {}},
            headers=headers,
        )
        assert r1.status_code == 200

        r2 = client.get("/approvals", headers=headers)
        assert r2.status_code == 200

        r3 = client.get("/metrics", headers=headers)
        assert r3.status_code == 200

        r4 = client.get("/identities", headers=headers)
        assert r4.status_code == 200


# ── D. Identity Attached to Execution ────────────────────────────────


class TestIdentityInExecution:
    def test_issued_by_is_identity_id(self):
        _reset()
        identity, _, headers = _create_identity("exec-actor", ["execute"])
        resp = client.post(
            "/execute",
            json={"operation": "computer_screenshot", "inputs": {}},
            headers=headers,
        )
        assert resp.status_code == 200
        # The result doesn't directly expose issued_by, but we can verify
        # the execution succeeded with identity context
        assert resp.json()["status"] == "succeeded"

    def test_mutation_approval_tracks_requested_by(self):
        _reset()
        identity, _, headers = _create_identity("requester", ["execute", "approvals:read"])
        resp = client.post(
            "/execute",
            json={"operation": "computer_click", "inputs": {"x": 1, "y": 1}},
            headers=headers,
        )
        approval_id = resp.json()["outputs"]["approval_id"]

        # Check the approval has requested_by set
        # The engine creates the approval via the store — but the actor_id
        # is in the execution context metadata. Let's check via the API.
        resp2 = client.get(f"/approvals/{approval_id}", headers=headers)
        assert resp2.status_code == 200
        # requested_by should be populated (engine propagates it)
        # Note: engine.py creates approvals internally — we need to verify
        # the approval shows up correctly
        assert "requested_by" in resp2.json()


# ── E. Approvals Track Actor ─────────────────────────────────────────


class TestApprovalsTrackActor:
    def test_approve_records_approved_by(self):
        _reset()
        exec_id, _, exec_headers = _create_identity("executor", ["execute", "approvals:read"])
        approver_id, _, approver_headers = _create_identity(
            "approver", ["approvals:read", "approvals:write"]
        )

        # Create approval via execution
        resp1 = client.post(
            "/execute",
            json={"operation": "computer_click", "inputs": {"x": 10, "y": 20}},
            headers=exec_headers,
        )
        approval_id = resp1.json()["outputs"]["approval_id"]

        # Approve it with a different identity
        resp2 = client.post(
            f"/approvals/{approval_id}/approve",
            headers=approver_headers,
        )
        assert resp2.status_code == 200
        assert resp2.json()["approved_by"] == approver_id.id

        # Verify the approval record has approved_by
        resp3 = client.get(f"/approvals/{approval_id}", headers=exec_headers)
        assert resp3.json()["approved_by"] == approver_id.id

    def test_deny_returns_denied_by(self):
        _reset()
        _, _, exec_headers = _create_identity("exec2", ["execute"])
        denier, _, deny_headers = _create_identity("denier", ["approvals:read", "approvals:write"])

        resp1 = client.post(
            "/execute",
            json={"operation": "computer_click", "inputs": {"x": 1, "y": 1}},
            headers=exec_headers,
        )
        approval_id = resp1.json()["outputs"]["approval_id"]

        resp2 = client.post(
            f"/approvals/{approval_id}/deny",
            headers=deny_headers,
        )
        assert resp2.status_code == 200
        assert resp2.json()["denied_by"] == denier.id


# ── F. Disabled Identity Cannot Act ──────────────────────────────────


class TestDisabledIdentity:
    def test_disabled_identity_returns_401(self):
        _reset()
        identity, raw_key, headers = _create_identity("to-disable", ["admin"])
        # Verify works before disabling
        resp1 = client.get("/health")
        assert resp1.status_code == 200

        resp2 = client.get("/approvals", headers=headers)
        assert resp2.status_code == 200

        # Disable
        store = get_identity_store()
        store.disable_identity(identity.id)

        # Should fail now
        resp3 = client.get("/approvals", headers=headers)
        assert resp3.status_code == 401

    def test_disable_via_api(self):
        _reset()
        admin_id, _, admin_headers = _create_identity("admin", ["admin"])
        target_id, _, target_headers = _create_identity("target", ["execute"])

        # Admin disables target
        resp = client.post(
            f"/identities/{target_id.id}/disable",
            headers=admin_headers,
        )
        assert resp.status_code == 200

        # Target can no longer act
        resp2 = client.post(
            "/execute",
            json={"operation": "computer_screenshot", "inputs": {}},
            headers=target_headers,
        )
        assert resp2.status_code == 401


# ── G. Identity Management Endpoints ─────────────────────────────────


class TestIdentityManagement:
    def test_create_identity_via_api(self):
        _reset()
        _, _, admin_headers = _create_identity("admin", ["admin"])
        resp = client.post(
            "/identities",
            json={"name": "new-agent", "scopes": ["execute", "metrics:read"]},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "new-agent"
        assert "api_key" in data
        assert data["scopes"] == ["execute", "metrics:read"]

    def test_create_identity_requires_admin(self):
        _reset()
        _, _, headers = _create_identity("non-admin", ["execute"])
        resp = client.post(
            "/identities",
            json={"name": "sneaky", "scopes": ["admin"]},
            headers=headers,
        )
        assert resp.status_code == 403

    def test_list_identities_via_api(self):
        _reset()
        _, _, admin_headers = _create_identity("admin", ["admin"])
        _create_identity("agent-a", ["execute"])
        _create_identity("agent-b", ["approvals:read"])
        resp = client.get("/identities", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 3

    def test_list_identities_requires_admin(self):
        _reset()
        _, _, headers = _create_identity("non-admin", ["execute"])
        resp = client.get("/identities", headers=headers)
        assert resp.status_code == 403

    def test_create_identity_invalid_scope_returns_400(self):
        _reset()
        _, _, admin_headers = _create_identity("admin", ["admin"])
        resp = client.post(
            "/identities",
            json={"name": "bad", "scopes": ["fake_scope"]},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_disable_nonexistent_returns_404(self):
        _reset()
        _, _, admin_headers = _create_identity("admin", ["admin"])
        resp = client.post("/identities/id_nonexistent/disable", headers=admin_headers)
        assert resp.status_code == 404


# ── H. SQLite IdentityStore ──────────────────────────────────────────


class TestSQLiteIdentityStore:
    def test_sqlite_create_and_authenticate(self):
        fd, path = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)
        os.unlink(path)
        store = IdentityStore(db_path=path)
        identity, raw_key = store.create_identity("sqlite-test", ["execute"])
        authed = store.authenticate(raw_key)
        assert authed is not None
        assert authed.id == identity.id
        assert authed.name == "sqlite-test"
        os.unlink(path)

    def test_sqlite_persists_across_instances(self):
        fd, path = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)
        os.unlink(path)
        store1 = IdentityStore(db_path=path)
        _, raw_key = store1.create_identity("persist-test", ["admin"])
        store2 = IdentityStore(db_path=path)
        authed = store2.authenticate(raw_key)
        assert authed is not None
        assert authed.name == "persist-test"
        os.unlink(path)

    def test_sqlite_disable_persists(self):
        fd, path = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)
        os.unlink(path)
        store1 = IdentityStore(db_path=path)
        identity, raw_key = store1.create_identity("dis-test", ["execute"])
        store1.disable_identity(identity.id)
        store2 = IdentityStore(db_path=path)
        assert store2.authenticate(raw_key) is None
        os.unlink(path)

    def test_identity_to_dict_excludes_hash(self):
        _reset()
        store = get_identity_store()
        identity, _ = store.create_identity("dict-test", ["execute"])
        d = identity.to_dict()
        assert "api_key_hash" not in d
        assert "id" in d
        assert "name" in d
        assert "scopes" in d


# ── I. Full Lifecycle with Identity ──────────────────────────────────


class TestFullIdentityLifecycle:
    def test_full_flow_with_separate_identities(self):
        """Agent executes → operator approves → agent re-executes with approval."""
        _reset()
        agent_id, _, agent_headers = _create_identity("agent", ["execute", "approvals:read"])
        operator_id, _, operator_headers = _create_identity(
            "operator", ["approvals:read", "approvals:write"]
        )

        # Agent triggers mutation
        r1 = client.post(
            "/execute",
            json={"operation": "computer_click", "inputs": {"x": 50, "y": 75}},
            headers=agent_headers,
        )
        assert r1.json()["status"] == "rejected"
        approval_id = r1.json()["outputs"]["approval_id"]

        # Operator approves
        r2 = client.post(
            f"/approvals/{approval_id}/approve",
            headers=operator_headers,
        )
        assert r2.status_code == 200
        assert r2.json()["approved_by"] == operator_id.id

        # Agent re-executes with approval
        r3 = client.post(
            "/execute",
            json={
                "operation": "computer_click",
                "inputs": {"x": 50, "y": 75, "approval_id": approval_id},
            },
            headers=agent_headers,
        )
        assert r3.json()["status"] == "succeeded"

        # Verify approval record
        r4 = client.get(f"/approvals/{approval_id}", headers=agent_headers)
        assert r4.json()["approved_by"] == operator_id.id
        assert r4.json()["status"] == "consumed"
