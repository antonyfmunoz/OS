"""tests for approval store — JSONL persistence for governance-blocked signals."""

import pytest
from services.umh.organism.approval_store import ApprovalStore


@pytest.fixture
def store(tmp_path):
    return ApprovalStore(store_dir=tmp_path / "organism")


def test_create_approval(store):
    record = store.create_approval(
        title="High-risk write blocked",
        description="Attempted irreversible write to production DB",
        agent="governance",
        risk_level="high",
    )
    assert record["status"] == "pending"
    assert record["risk_level"] == "high"
    assert record["id"] is not None


def test_list_approvals(store):
    store.create_approval(title="A", description="first")
    store.create_approval(title="B", description="second")
    all_a = store.list_approvals()
    assert len(all_a) == 2


def test_list_approvals_filter_status(store):
    store.create_approval(title="A", description="first")
    record = store.create_approval(title="B", description="second")
    store.decide(record["id"], "approved")
    pending = store.list_approvals(status="pending")
    assert len(pending) == 1
    approved = store.list_approvals(status="approved")
    assert len(approved) == 1


def test_approve_item(store):
    record = store.create_approval(title="Test", description="desc")
    result = store.decide(record["id"], "approved")
    assert result is not None
    assert result["status"] == "approved"
    assert result["decided_at"] is not None
    assert result["decided_by"] == "operator"


def test_deny_item(store):
    record = store.create_approval(title="Test", description="desc")
    result = store.decide(record["id"], "denied")
    assert result is not None
    assert result["status"] == "denied"


def test_decide_nonexistent(store):
    result = store.decide("nonexistent-id", "approved")
    assert result is None


def test_pending_count(store):
    store.create_approval(title="A", description="first")
    store.create_approval(title="B", description="second")
    assert store.pending_count() == 2
    record = store.create_approval(title="C", description="third")
    store.decide(record["id"], "approved")
    assert store.pending_count() == 2
