"""tests for daemon approval creation on governance rejection."""

import pytest
from services.umh.organism.daemon import OrganismDaemon, _map_risk_level


def test_map_risk_level_deny():
    assert _map_risk_level({"decision": "DENY"}) == "high"


def test_map_risk_level_escalate():
    assert _map_risk_level({"decision": "ESCALATE"}) == "critical"


def test_map_risk_level_defer():
    assert _map_risk_level({"decision": "DEFER"}) == "medium"


def test_map_risk_level_unknown():
    assert _map_risk_level({"decision": "UNKNOWN"}) == "medium"


def test_daemon_creates_approval_on_governance_deny(tmp_path):
    daemon = OrganismDaemon(store_dir=str(tmp_path / "organism"))
    daemon.start()

    daemon._on_pipeline_event(
        "governance",
        {
            "approved": False,
            "decision": "DENY",
            "rationale": "Irreversible write to production",
            "verdict_id": "v-123",
        },
    )

    approvals = daemon.approval_store.list_approvals()
    assert len(approvals) == 1
    assert approvals[0]["status"] == "pending"
    assert approvals[0]["risk_level"] == "high"
    assert "Irreversible write" in approvals[0]["description"]


def test_daemon_ignores_approved_governance_events(tmp_path):
    daemon = OrganismDaemon(store_dir=str(tmp_path / "organism"))
    daemon.start()

    daemon._on_pipeline_event(
        "governance",
        {
            "approved": True,
            "decision": "APPROVE",
        },
    )

    approvals = daemon.approval_store.list_approvals()
    assert len(approvals) == 0


def test_daemon_ignores_non_governance_events(tmp_path):
    daemon = OrganismDaemon(store_dir=str(tmp_path / "organism"))
    daemon.start()

    daemon._on_pipeline_event("execution", {"result_id": "r-1"})

    approvals = daemon.approval_store.list_approvals()
    assert len(approvals) == 0
