"""Tests for Phase 5A: Control Plane Interface (HTTP API).

Verifies:
- Execute endpoint works
- Approval lifecycle via API works
- Metrics endpoint returns expected structure
- Unauthorized requests are rejected
- Health endpoint is public
"""

import sys
import os

sys.path.insert(0, "/opt/OS")

os.environ.setdefault("UMH_API_KEY", "test-key-phase5a")

from unittest.mock import patch

from fastapi.testclient import TestClient

from umh.control.api import app
from umh.execution.approval import get_approval_store

client = TestClient(app)
HEADERS = {"X-API-Key": "test-key-phase5a"}


def _reset():
    get_approval_store().reset()


# ── A. Health Endpoint (Public) ──────────────────────────────────────


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_health_requires_no_auth(self):
        resp = client.get("/health")
        assert resp.status_code == 200


# ── B. Auth Enforcement ──────────────────────────────────────────────


class TestAuthEnforcement:
    def test_no_key_returns_401(self):
        resp = client.get("/approvals")
        assert resp.status_code == 401
        assert "Invalid" in resp.json()["error"]

    def test_wrong_key_returns_401(self):
        resp = client.get("/approvals", headers={"X-API-Key": "wrong-key"})
        assert resp.status_code == 401

    def test_correct_key_passes(self):
        _reset()
        resp = client.get("/approvals", headers=HEADERS)
        assert resp.status_code == 200

    def test_execute_requires_auth(self):
        resp = client.post("/execute", json={"operation": "shell_command", "inputs": {}})
        assert resp.status_code == 401

    def test_metrics_requires_auth(self):
        resp = client.get("/metrics")
        assert resp.status_code == 401

    def test_no_api_key_configured_returns_401(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("UMH_API_KEY", None)
            resp = client.get("/approvals")
            assert resp.status_code == 401
        os.environ["UMH_API_KEY"] = "test-key-phase5a"


# ── C. Execute Endpoint ──────────────────────────────────────────────


class TestExecuteEndpoint:
    def test_execute_shell_uptime(self):
        resp = client.post(
            "/execute",
            json={"operation": "shell_command", "inputs": {"command": "uptime", "args": []}},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "execution_id" in data
        assert "status" in data
        assert data["status"] in ("succeeded", "failed")
        assert data["operation"] == "shell_command"

    def test_execute_screenshot(self):
        resp = client.post(
            "/execute",
            json={"operation": "computer_screenshot", "inputs": {}},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "succeeded"

    def test_execute_mutation_requires_approval(self):
        _reset()
        resp = client.post(
            "/execute",
            json={
                "operation": "computer_click",
                "inputs": {"x": 100, "y": 200},
            },
            headers=HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"
        assert data["outputs"]["requires_approval"] is True
        assert "approval_id" in data["outputs"]

    def test_execute_with_approval(self):
        _reset()
        # Step 1: get approval_id from rejection
        resp1 = client.post(
            "/execute",
            json={"operation": "computer_click", "inputs": {"x": 10, "y": 20}},
            headers=HEADERS,
        )
        approval_id = resp1.json()["outputs"]["approval_id"]

        # Step 2: approve via API
        resp2 = client.post(f"/approvals/{approval_id}/approve", headers=HEADERS)
        assert resp2.status_code == 200

        # Step 3: execute with approval_id
        resp3 = client.post(
            "/execute",
            json={
                "operation": "computer_click",
                "inputs": {"x": 10, "y": 20, "approval_id": approval_id},
            },
            headers=HEADERS,
        )
        assert resp3.status_code == 200
        data = resp3.json()
        assert data["status"] == "succeeded"

    def test_execute_result_has_expected_fields(self):
        resp = client.post(
            "/execute",
            json={"operation": "computer_screenshot", "inputs": {}},
            headers=HEADERS,
        )
        data = resp.json()
        required_fields = [
            "execution_id",
            "correlation_id",
            "operation",
            "status",
            "outputs",
            "latency_ms",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_execute_custom_execution_class(self):
        resp = client.post(
            "/execute",
            json={
                "operation": "computer_screenshot",
                "inputs": {},
                "execution_class": "side_effect",
            },
            headers=HEADERS,
        )
        assert resp.status_code == 200

    def test_execute_invalid_body_returns_422(self):
        resp = client.post(
            "/execute",
            json={"not_operation": "bad"},
            headers=HEADERS,
        )
        assert resp.status_code == 422


# ── D. Approvals Lifecycle via API ───────────────────────────────────


class TestApprovalsAPI:
    def test_list_empty(self):
        _reset()
        resp = client.get("/approvals", headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_after_creation(self):
        _reset()
        # Create an approval by triggering a mutation
        client.post(
            "/execute",
            json={"operation": "computer_click", "inputs": {"x": 1, "y": 1}},
            headers=HEADERS,
        )
        resp = client.get("/approvals", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["status"] == "pending"

    def test_list_pending_filter(self):
        _reset()
        client.post(
            "/execute",
            json={"operation": "computer_click", "inputs": {"x": 1, "y": 1}},
            headers=HEADERS,
        )
        resp = client.get("/approvals?status=pending", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["status"] == "pending"

    def test_get_specific_approval(self):
        _reset()
        resp1 = client.post(
            "/execute",
            json={"operation": "computer_click", "inputs": {"x": 5, "y": 5}},
            headers=HEADERS,
        )
        approval_id = resp1.json()["outputs"]["approval_id"]

        resp2 = client.get(f"/approvals/{approval_id}", headers=HEADERS)
        assert resp2.status_code == 200
        data = resp2.json()
        assert data["id"] == approval_id
        assert data["operation"] == "computer_click"

    def test_get_nonexistent_returns_404(self):
        resp = client.get("/approvals/approval_nonexistent", headers=HEADERS)
        assert resp.status_code == 404

    def test_approve_pending(self):
        _reset()
        resp1 = client.post(
            "/execute",
            json={"operation": "computer_click", "inputs": {"x": 1, "y": 1}},
            headers=HEADERS,
        )
        approval_id = resp1.json()["outputs"]["approval_id"]

        resp2 = client.post(f"/approvals/{approval_id}/approve", headers=HEADERS)
        assert resp2.status_code == 200
        assert resp2.json()["approved"] == approval_id

    def test_approve_nonexistent_returns_404(self):
        resp = client.post("/approvals/approval_nonexistent/approve", headers=HEADERS)
        assert resp.status_code == 404

    def test_approve_already_approved_returns_409(self):
        _reset()
        resp1 = client.post(
            "/execute",
            json={"operation": "computer_click", "inputs": {"x": 1, "y": 1}},
            headers=HEADERS,
        )
        approval_id = resp1.json()["outputs"]["approval_id"]
        client.post(f"/approvals/{approval_id}/approve", headers=HEADERS)

        resp2 = client.post(f"/approvals/{approval_id}/approve", headers=HEADERS)
        assert resp2.status_code == 409

    def test_deny_pending(self):
        _reset()
        resp1 = client.post(
            "/execute",
            json={"operation": "computer_click", "inputs": {"x": 1, "y": 1}},
            headers=HEADERS,
        )
        approval_id = resp1.json()["outputs"]["approval_id"]

        resp2 = client.post(f"/approvals/{approval_id}/deny", headers=HEADERS)
        assert resp2.status_code == 200
        assert resp2.json()["denied"] == approval_id

    def test_deny_nonexistent_returns_404(self):
        resp = client.post("/approvals/approval_nonexistent/deny", headers=HEADERS)
        assert resp.status_code == 404

    def test_deny_consumed_returns_409(self):
        _reset()
        resp1 = client.post(
            "/execute",
            json={"operation": "computer_click", "inputs": {"x": 1, "y": 1}},
            headers=HEADERS,
        )
        approval_id = resp1.json()["outputs"]["approval_id"]
        client.post(f"/approvals/{approval_id}/approve", headers=HEADERS)
        # Consume it by executing
        client.post(
            "/execute",
            json={
                "operation": "computer_click",
                "inputs": {"x": 1, "y": 1, "approval_id": approval_id},
            },
            headers=HEADERS,
        )

        resp2 = client.post(f"/approvals/{approval_id}/deny", headers=HEADERS)
        assert resp2.status_code == 409
        assert "consumed" in resp2.json()["detail"].lower()


# ── E. Metrics Endpoint ──────────────────────────────────────────────


class TestMetricsEndpoint:
    def test_metrics_returns_expected_structure(self):
        resp = client.get("/metrics", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "capabilities" in data
        assert "environments" in data
        assert "scoring" in data
        assert "approvals" in data

    def test_metrics_approvals_section(self):
        resp = client.get("/metrics", headers=HEADERS)
        data = resp.json()
        approvals = data["approvals"]
        assert "pending_count" in approvals
        assert "approvals_consumed" in approvals
        assert "approvals_denied" in approvals
        assert "approvals_expired" in approvals

    def test_metrics_capabilities_is_list(self):
        resp = client.get("/metrics", headers=HEADERS)
        data = resp.json()
        assert isinstance(data["capabilities"], list)
        assert len(data["capabilities"]) > 0

    def test_metrics_environments_is_list(self):
        resp = client.get("/metrics", headers=HEADERS)
        data = resp.json()
        assert isinstance(data["environments"], list)


# ── F. Full Lifecycle via API ────────────────────────────────────────


class TestFullLifecycle:
    def test_full_approval_lifecycle(self):
        """Execute → rejected → approve → execute → succeeded → consumed."""
        _reset()

        # 1. Execute mutation → REJECTED with approval_id
        r1 = client.post(
            "/execute",
            json={"operation": "computer_click", "inputs": {"x": 50, "y": 75}},
            headers=HEADERS,
        )
        assert r1.json()["status"] == "rejected"
        approval_id = r1.json()["outputs"]["approval_id"]

        # 2. Check approval is listed
        r2 = client.get("/approvals", headers=HEADERS)
        ids = [a["id"] for a in r2.json()]
        assert approval_id in ids

        # 3. Approve it
        r3 = client.post(f"/approvals/{approval_id}/approve", headers=HEADERS)
        assert r3.status_code == 200

        # 4. Check status is approved
        r4 = client.get(f"/approvals/{approval_id}", headers=HEADERS)
        assert r4.json()["status"] == "approved"

        # 5. Execute with approval → SUCCEEDED
        r5 = client.post(
            "/execute",
            json={
                "operation": "computer_click",
                "inputs": {"x": 50, "y": 75, "approval_id": approval_id},
            },
            headers=HEADERS,
        )
        assert r5.json()["status"] == "succeeded"

        # 6. Approval is now consumed
        r6 = client.get(f"/approvals/{approval_id}", headers=HEADERS)
        assert r6.json()["status"] == "consumed"

        # 7. Replay blocked
        r7 = client.post(
            "/execute",
            json={
                "operation": "computer_click",
                "inputs": {"x": 50, "y": 75, "approval_id": approval_id},
            },
            headers=HEADERS,
        )
        assert r7.json()["status"] == "rejected"
        assert "consumed" in r7.json()["outputs"].get("reason", "").lower()
