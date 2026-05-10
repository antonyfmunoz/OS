"""Phase 7A Memory API tests — validates memory endpoints and /run memory injection.

Tests cover CRUD operations on /memory, search, stats, memory context
in /run responses, memory stats in /metrics, and auth enforcement.
"""

import sys
import os

sys.path.insert(0, "/opt/OS")
os.environ.setdefault("UMH_API_KEY", "test-key-phase7a")
os.environ["UMH_TASK_BACKEND"] = "memory"
# Use temp SQLite for memory tests so they don't pollute production data
os.environ["UMH_MEMORY_DB_PATH"] = "/tmp/test_phase7a_memory.sqlite"

from fastapi.testclient import TestClient

from umh.control.api import app
from umh.control.identity import get_identity_store
from umh.events.stream import reset_event_stream
from umh.execution.approval import get_approval_store
from umh.memory.persistent_store import reset_memory_store
from umh.orchestrator.engine import reset_orchestrator, start_orchestrator
from umh.orchestrator.task import reset_tasks
from umh.orchestrator.task_store import InMemoryTaskBackend, reset_task_store
from umh.orchestrator.worker import reset_worker

client = TestClient(app)


def _reset():
    get_approval_store().reset()
    get_identity_store().reset()
    reset_event_stream()
    reset_orchestrator()
    reset_tasks()
    reset_task_store(backend=InMemoryTaskBackend())
    reset_worker()
    reset_memory_store()
    # Re-create with test DB path
    os.environ["UMH_MEMORY_DB_PATH"] = "/tmp/test_phase7a_memory.sqlite"
    # Clean test DB
    import pathlib

    db = pathlib.Path("/tmp/test_phase7a_memory.sqlite")
    if db.exists():
        db.unlink()


def _create_identity(name="admin", scopes=None):
    store = get_identity_store()
    identity, raw_key = store.create_identity(name, scopes or ["admin"])
    return identity, raw_key, {"X-API-Key": raw_key}


def _memory_headers(scopes=None):
    """Create identity with memory scopes and return headers."""
    return _create_identity(
        name="memory_user",
        scopes=scopes or ["memory:read", "memory:write", "execute", "metrics:read"],
    )


# ── POST /memory ───────────────────────────────────────────────────


class TestCreateMemory:
    def setup_method(self):
        _reset()
        self._identity, self._key, self._headers = _memory_headers()

    def test_create_memory_returns_created(self):
        resp = client.post(
            "/memory",
            json={
                "type": "task",
                "content": "Completed deployment to staging",
                "metadata": {"env": "staging"},
                "tags": ["deploy", "staging"],
            },
            headers=self._headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["type"] == "task"
        assert data["content"] == "Completed deployment to staging"
        assert data["tags"] == ["deploy", "staging"]
        assert data["metadata"] == {"env": "staging"}
        assert "created_at" in data

    def test_create_memory_validates_type(self):
        resp = client.post(
            "/memory",
            json={"type": "invalid_type", "content": "test"},
            headers=self._headers,
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["error"] == "validation_error"
        assert "invalid_type" in data["message"].lower() or "Invalid" in data["message"]

    def test_create_memory_requires_content(self):
        resp = client.post(
            "/memory",
            json={"type": "task", "content": ""},
            headers=self._headers,
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["error"] == "validation_error"

    def test_create_memory_whitespace_only_content(self):
        resp = client.post(
            "/memory",
            json={"type": "task", "content": "   "},
            headers=self._headers,
        )
        assert resp.status_code == 400

    def test_create_all_valid_types(self):
        for mem_type in ["task", "summary", "insight", "system"]:
            resp = client.post(
                "/memory",
                json={"type": mem_type, "content": f"Test {mem_type}"},
                headers=self._headers,
            )
            assert resp.status_code == 200, f"Failed for type={mem_type}"
            assert resp.json()["type"] == mem_type


# ── GET /memory ────────────────────────────────────────────────────


class TestListMemories:
    def setup_method(self):
        _reset()
        self._identity, self._key, self._headers = _memory_headers()

    def _seed_memories(self):
        for i, mem_type in enumerate(["task", "task", "insight", "summary"]):
            client.post(
                "/memory",
                json={
                    "type": mem_type,
                    "content": f"Memory item {i}",
                    "tags": [f"tag{i}"],
                },
                headers=self._headers,
            )

    def test_list_returns_array(self):
        resp = client.get("/memory", headers=self._headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_returns_created_memories(self):
        self._seed_memories()
        resp = client.get("/memory", headers=self._headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 4

    def test_list_filter_by_type(self):
        self._seed_memories()
        resp = client.get("/memory?type=task", headers=self._headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert all(m["type"] == "task" for m in data)

    def test_list_filter_nonexistent_type(self):
        self._seed_memories()
        resp = client.get("/memory?type=system", headers=self._headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 0


# ── GET /memory/search ─────────────────────────────────────────────


class TestSearchMemories:
    def setup_method(self):
        _reset()
        self._identity, self._key, self._headers = _memory_headers()
        # Seed some memories
        client.post(
            "/memory",
            json={
                "type": "task",
                "content": "Deployed application to production server",
                "tags": ["deploy", "production"],
            },
            headers=self._headers,
        )
        client.post(
            "/memory",
            json={
                "type": "insight",
                "content": "Database queries are slow on large tables",
                "tags": ["performance", "database"],
            },
            headers=self._headers,
        )

    def test_search_returns_matches(self):
        resp = client.get("/memory/search?q=deploy", headers=self._headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert any(
            "deploy" in m["content"].lower() or "deploy" in str(m["tags"]).lower() for m in data
        )

    def test_search_no_match(self):
        resp = client.get("/memory/search?q=zzzznonexistent", headers=self._headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 0

    def test_search_without_q_returns_400(self):
        resp = client.get("/memory/search", headers=self._headers)
        assert resp.status_code == 400
        data = resp.json()
        assert data["error"] == "validation_error"

    def test_search_empty_q_returns_400(self):
        resp = client.get("/memory/search?q=", headers=self._headers)
        assert resp.status_code == 400


# ── DELETE /memory/{id} ────────────────────────────────────────────


class TestDeleteMemory:
    def setup_method(self):
        _reset()
        self._identity, self._key, self._headers = _memory_headers()

    def test_delete_existing_memory(self):
        # Create a memory
        resp = client.post(
            "/memory",
            json={"type": "task", "content": "To be deleted"},
            headers=self._headers,
        )
        memory_id = resp.json()["id"]

        # Delete it
        resp = client.delete(f"/memory/{memory_id}", headers=self._headers)
        assert resp.status_code == 200
        assert resp.json()["deleted"] == memory_id

        # Verify gone
        resp = client.get("/memory", headers=self._headers)
        ids = [m["id"] for m in resp.json()]
        assert memory_id not in ids

    def test_delete_nonexistent_returns_404(self):
        resp = client.delete("/memory/nonexistent-id-12345", headers=self._headers)
        assert resp.status_code == 404


# ── GET /memory/stats ──────────────────────────────────────────────


class TestMemoryStats:
    def setup_method(self):
        _reset()
        self._identity, self._key, self._headers = _memory_headers()

    def test_stats_empty(self):
        resp = client.get("/memory/stats", headers=self._headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_memories"] == 0
        assert data["by_type"] == {}

    def test_stats_with_data(self):
        # Create some memories
        for mem_type in ["task", "task", "insight"]:
            client.post(
                "/memory",
                json={"type": mem_type, "content": f"Test {mem_type}"},
                headers=self._headers,
            )
        resp = client.get("/memory/stats", headers=self._headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_memories"] == 3
        assert data["by_type"]["task"] == 2
        assert data["by_type"]["insight"] == 1


# ── /run with memory ──────────────────────────────────────────────


class TestRunWithMemory:
    def setup_method(self):
        _reset()
        self._identity, self._key, self._headers = _memory_headers()
        start_orchestrator()

    def test_run_without_memory_has_empty_context(self):
        resp = client.post(
            "/run",
            json={"objective": "test objective", "dry_run": True, "use_memory": False},
            headers=self._headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "memory_context" in data
        assert data["memory_context"] == []
        assert data["memory_count"] == 0

    def test_run_with_memory_includes_context(self):
        # Seed a relevant memory
        client.post(
            "/memory",
            json={
                "type": "insight",
                "content": "Deployment requires staging validation first",
                "tags": ["deployment", "staging"],
            },
            headers=self._headers,
        )
        resp = client.post(
            "/run",
            json={
                "objective": "deploy to staging",
                "dry_run": True,
                "use_memory": True,
            },
            headers=self._headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "memory_context" in data
        assert "memory_count" in data
        # Memory search is keyword-based — "staging" should match
        assert isinstance(data["memory_context"], list)
        assert isinstance(data["memory_count"], int)

    def test_run_default_use_memory_false(self):
        """use_memory defaults to false."""
        resp = client.post(
            "/run",
            json={"objective": "test default", "dry_run": True},
            headers=self._headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["memory_context"] == []
        assert data["memory_count"] == 0


# ── /metrics memory section ───────────────────────────────────────


class TestMetricsMemorySection:
    def setup_method(self):
        _reset()
        self._identity, self._key, self._headers = _memory_headers()

    def test_metrics_includes_memory(self):
        resp = client.get("/metrics", headers=self._headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "memory" in data
        assert "total_memories" in data["memory"]
        assert data["memory"]["total_memories"] >= 0

    def test_metrics_memory_count_matches(self):
        # Seed some memories
        client.post(
            "/memory",
            json={"type": "task", "content": "test metric"},
            headers=self._headers,
        )
        client.post(
            "/memory",
            json={"type": "insight", "content": "another metric"},
            headers=self._headers,
        )
        resp = client.get("/metrics", headers=self._headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["memory"]["total_memories"] == 2


# ── Auth enforcement ──────────────────────────────────────────────


class TestMemoryAuth:
    def setup_method(self):
        _reset()

    def test_create_memory_requires_auth(self):
        resp = client.post(
            "/memory",
            json={"type": "task", "content": "no auth"},
        )
        assert resp.status_code == 401

    def test_list_memories_requires_auth(self):
        resp = client.get("/memory")
        assert resp.status_code == 401

    def test_search_memories_requires_auth(self):
        resp = client.get("/memory/search?q=test")
        assert resp.status_code == 401

    def test_delete_memory_requires_auth(self):
        resp = client.delete("/memory/some-id")
        assert resp.status_code == 401

    def test_stats_requires_auth(self):
        resp = client.get("/memory/stats")
        assert resp.status_code == 401

    def test_memory_write_requires_write_scope(self):
        # Create identity with only read scope
        _, _, headers = _create_identity(name="reader", scopes=["memory:read"])
        resp = client.post(
            "/memory",
            json={"type": "task", "content": "no write scope"},
            headers=headers,
        )
        assert resp.status_code == 403

    def test_memory_read_requires_read_scope(self):
        # Create identity with only write scope
        _, _, headers = _create_identity(name="writer", scopes=["memory:write"])
        resp = client.get("/memory", headers=headers)
        assert resp.status_code == 403
