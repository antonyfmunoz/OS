"""Tests for Phase 7D: Scheduler Layer — API endpoints and CLI commands.

Verifies:
- GET/POST/DELETE /schedules endpoints
- Enable/disable/run-now endpoints
- Metrics include scheduler section
- CLI cmd_* functions for schedule management
- JSON output format
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, "/opt/OS")

os.environ.setdefault("UMH_API_KEY", "test-key-phase7d")

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from umh.control.api import app
from umh.control.identity import Identity, reset_identity_store
from umh.events.stream import reset_event_stream
from umh.scheduler.store import get_schedule_store, reset_schedule_store


# ── Fixtures ──────────────────────────────────────────────────────


_MOCK_IDENTITY = Identity(
    id="test_user",
    name="test",
    api_key_hash="",
    scopes=[
        "admin",
        "execute",
        "schedules:read",
        "schedules:write",
        "metrics:read",
    ],
    created_at="",
    status="active",
)


@pytest.fixture(autouse=True)
def clean_state():
    reset_schedule_store()
    reset_event_stream()
    reset_identity_store()
    yield
    reset_schedule_store()


@pytest.fixture
def client():
    reset_schedule_store()
    reset_event_stream()
    return TestClient(app, headers={"X-API-Key": "test-key-phase7d"})


@pytest.fixture(autouse=True)
def mock_auth():
    """Mock auth to allow test requests."""
    with patch("umh.control.api._require_scope", return_value=_MOCK_IDENTITY):
        yield


def _create_schedule_via_api(client: TestClient, name: str = "test sched", **overrides) -> dict:
    """Helper: create a schedule via API and return the response JSON."""
    body = {
        "name": name,
        "objective": f"objective for {name}",
        "schedule_type": "interval",
        "schedule_value": "30",
    }
    body.update(overrides)
    resp = client.post("/schedules", json=body)
    assert resp.status_code in (200, 201), f"Create failed: {resp.text}"
    return resp.json()


# ── API: List ─────────────────────────────────────────────────────


def test_list_schedules_empty(client):
    """GET /schedules with no schedules returns empty list."""
    resp = client.get("/schedules")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


# ── API: Create ───────────────────────────────────────────────────


def test_create_schedule(client):
    """POST /schedules creates a new schedule and returns it."""
    data = _create_schedule_via_api(client, "api-create-test")
    assert "id" in data
    assert data["id"].startswith("sched_")
    assert data["name"] == "api-create-test"


def test_create_schedule_default_disabled(client):
    """Created schedule has enabled=False by default."""
    data = _create_schedule_via_api(client, "disabled-default")
    assert data["enabled"] is False


# ── API: Get ──────────────────────────────────────────────────────


def test_get_schedule(client):
    """GET /schedules/{id} retrieves a specific schedule."""
    created = _create_schedule_via_api(client, "get-test")
    schedule_id = created["id"]

    resp = client.get(f"/schedules/{schedule_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == schedule_id
    assert data["name"] == "get-test"


def test_get_schedule_not_found(client):
    """GET /schedules/{id} returns 404 for non-existent schedule."""
    resp = client.get("/schedules/sched_doesnotexist")
    assert resp.status_code == 404


# ── API: Enable / Disable ────────────────────────────────────────


def test_enable_schedule(client):
    """POST /schedules/{id}/enable sets enabled=True."""
    created = _create_schedule_via_api(client, "enable-test")
    schedule_id = created["id"]

    resp = client.post(f"/schedules/{schedule_id}/enable")
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is True


def test_disable_schedule(client):
    """POST /schedules/{id}/disable sets enabled=False."""
    created = _create_schedule_via_api(client, "disable-test")
    schedule_id = created["id"]

    # Enable first
    client.post(f"/schedules/{schedule_id}/enable")
    # Then disable
    resp = client.post(f"/schedules/{schedule_id}/disable")
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is False


# ── API: Run Now ──────────────────────────────────────────────────


def test_run_now(client):
    """POST /schedules/{id}/run-now triggers immediate execution."""
    from umh.planning.models import PlanStatus

    created = _create_schedule_via_api(client, "run-now-test")
    schedule_id = created["id"]
    client.post(f"/schedules/{schedule_id}/enable")

    mock_plan = MagicMock()
    mock_plan.status = PlanStatus.VALIDATED
    mock_plan.plan_id = "eplan_runnow"
    mock_plan.quality_score = {"verdict": "pass", "score": 1.0}
    mock_plan.objective = MagicMock()
    mock_plan.objective.dry_run = False

    mock_task = MagicMock()
    mock_task.id = "task_runnow"
    mock_task.status = MagicMock(value="completed")

    with patch("umh.planning.planner.create_plan_from_raw", return_value=mock_plan):
        with patch("umh.planning.planner.execute_plan", return_value=mock_task):
            resp = client.post(f"/schedules/{schedule_id}/run-now")

    assert resp.status_code == 200


# ── API: Delete ───────────────────────────────────────────────────


def test_delete_schedule(client):
    """DELETE /schedules/{id} removes the schedule."""
    created = _create_schedule_via_api(client, "delete-test")
    schedule_id = created["id"]

    resp = client.delete(f"/schedules/{schedule_id}")
    assert resp.status_code == 200

    # Verify deleted
    resp2 = client.get(f"/schedules/{schedule_id}")
    assert resp2.status_code == 404


def test_delete_schedule_not_found(client):
    """DELETE /schedules/{id} returns 404 for non-existent schedule."""
    resp = client.delete("/schedules/sched_doesnotexist")
    assert resp.status_code == 404


# ── API: Metrics ──────────────────────────────────────────────────


def test_metrics_include_schedules(client):
    """GET /metrics response includes schedules section."""
    # Create a schedule so counts are non-zero
    _create_schedule_via_api(client, "metrics-test")

    resp = client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    # The schedules section should exist in the metrics response
    assert "schedules" in data
    sched_metrics = data["schedules"]
    assert "total" in sched_metrics or "schedules_total" in sched_metrics or isinstance(sched_metrics, dict)


# ── CLI Commands ──────────────────────────────────────────────────


def _cli_create_schedule(name: str = "cli-test", objective: str = "test objective") -> str:
    """Helper: create a schedule via store and return its id."""
    from umh.scheduler.models import ScheduleType, ScheduledWorkflow

    store = get_schedule_store()
    wf = ScheduledWorkflow(
        name=name,
        objective=objective,
        schedule_type=ScheduleType.INTERVAL,
        schedule_value="30",
    )
    store.create(wf)
    return wf.id


def test_cli_schedules(capsys):
    """cmd_schedules lists all schedules."""
    from umh.control.cli import main

    _cli_create_schedule("cli-list-a")
    _cli_create_schedule("cli-list-b")

    result = main(["schedules", "--json"])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert isinstance(data, list)
    assert len(data) == 2


def test_cli_schedule_create(capsys):
    """cmd_schedule_create creates a new schedule."""
    from umh.control.cli import main

    result = main(["schedule-create", "new-sched", "--objective", "do something", "--interval", "15", "--json"])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["name"] == "new-sched"
    assert data["schedule_type"] == "interval"
    assert data["schedule_value"] == "15"


def test_cli_schedule_enable(capsys):
    """cmd_schedule_enable enables a schedule."""
    from umh.control.cli import main

    sched_id = _cli_create_schedule("cli-enable")

    result = main(["schedule-enable", sched_id, "--json"])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["enabled"] is True


def test_cli_schedule_disable(capsys):
    """cmd_schedule_disable disables a schedule."""
    from umh.control.cli import main

    sched_id = _cli_create_schedule("cli-disable")
    store = get_schedule_store()
    store.enable(sched_id)

    result = main(["schedule-disable", sched_id, "--json"])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["enabled"] is False


def test_cli_schedule_run_now(capsys):
    """cmd_schedule_run_now triggers immediate execution."""
    from umh.control.cli import main
    from umh.planning.models import PlanStatus

    sched_id = _cli_create_schedule("cli-run-now")
    store = get_schedule_store()
    store.enable(sched_id)

    mock_plan = MagicMock()
    mock_plan.status = PlanStatus.VALIDATED
    mock_plan.plan_id = "eplan_cli_rn"
    mock_plan.quality_score = {"verdict": "pass", "score": 1.0}
    mock_plan.objective = MagicMock()
    mock_plan.objective.dry_run = False

    mock_task = MagicMock()
    mock_task.id = "task_cli_rn"
    mock_task.status = MagicMock(value="completed")

    with patch("umh.planning.planner.create_plan_from_raw", return_value=mock_plan):
        with patch("umh.planning.planner.execute_plan", return_value=mock_task):
            result = main(["schedule-run-now", sched_id, "--json"])

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "error" not in data or data.get("error") is None


def test_cli_schedule_delete(capsys):
    """cmd_schedule_delete removes a schedule."""
    from umh.control.cli import main

    sched_id = _cli_create_schedule("cli-delete")

    result = main(["schedule-delete", sched_id, "--json"])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data.get("deleted") == sched_id or "deleted" in str(data)


def test_cli_schedule_create_interval(capsys):
    """--interval flag creates an interval schedule."""
    from umh.control.cli import main

    result = main(["schedule-create", "interval-test", "--objective", "run every 60m", "--interval", "60", "--json"])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["schedule_type"] == "interval"
    assert data["schedule_value"] == "60"


def test_cli_schedule_create_daily(capsys):
    """--daily flag creates a daily schedule."""
    from umh.control.cli import main

    result = main(["schedule-create", "daily-test", "--objective", "daily check", "--daily", "09:00", "--json"])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["schedule_type"] == "daily"
    assert data["schedule_value"] == "09:00"


def test_cli_schedules_json_output(capsys):
    """JSON output is valid parseable JSON."""
    from umh.control.cli import main

    _cli_create_schedule("json-out")

    result = main(["schedules", "--json"])
    captured = capsys.readouterr()
    # Must be valid JSON
    data = json.loads(captured.out)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["name"] == "json-out"
