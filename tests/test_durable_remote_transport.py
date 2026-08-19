from __future__ import annotations

import pytest

from substrate.execution.durable_remote_transport import (
    DurableRemoteRequest,
    DurableRemoteStore,
    make_request,
)


def _request(**overrides: object) -> DurableRemoteRequest:
    data = {
        "correlation_id": "w2-rehearsal",
        "candidate_sha": "abc123",
        "node_id": "windows-desktop",
        "operation_type": "codex_probe",
        "capability": "shell",
        "params": {"command": "echo ok", "timeout": 5},
        "ttl_seconds": 60,
    }
    data.update(overrides)
    return make_request(**data)  # type: ignore[arg-type]


def test_request_is_persisted_before_delivery_and_claimed_idempotently(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())

    assert [item.request_id for item in store.deliverable_for_node("windows-desktop")] == [
        req.request_id
    ]
    claimed = store.mark_claimed(req.request_id, claim_id="claim-1", process_tree={"pid": 10})
    assert claimed.lifecycle_state == "CLAIMED"
    assert claimed.claim_id == "claim-1"

    again = store.mark_claimed(req.request_id, claim_id="claim-1", process_tree={"pid": 10})
    assert again.lifecycle_state == "CLAIMED"
    assert again.claim_id == "claim-1"


def test_duplicate_request_id_with_different_payload_fails_closed(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = _request(idempotency_key="same-key")
    store.put_request(req)
    duplicate = DurableRemoteRequest.from_dict(req.to_dict())
    duplicate.params = {"command": "echo different", "timeout": 5}
    duplicate.payload_digest = ""
    duplicate.__post_init__()

    with pytest.raises(ValueError, match="different payload digest"):
        store.put_request(duplicate)


def test_claim_conflict_requires_reconciliation(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")

    conflicted = store.mark_claimed(req.request_id, claim_id="claim-2")

    assert conflicted.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert store.deliverable_for_node("windows-desktop") == []


def test_cancelled_request_rejects_late_success(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")
    cancelled = store.request_cancel(req.request_id)
    assert cancelled.lifecycle_state == "CANCEL_REQUESTED"

    final = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="SUCCEEDED",
        result={"success": True, "stdout": "late"},
    )

    assert final.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert final.diagnostics["late_success_rejected"] is True
    assert store.result_for(req.request_id) is None


def test_terminal_result_is_idempotent_but_conflicting_replay_fails_closed(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")
    first = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="SUCCEEDED",
        result={"success": True, "stdout": "ok"},
    )
    assert first.lifecycle_state == "SUCCEEDED"

    same = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="SUCCEEDED",
        result={"success": True, "stdout": "ok"},
    )
    assert same.lifecycle_state == "SUCCEEDED"

    conflict = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="FAILED",
        result={"success": False, "error": "different"},
    )
    assert conflict.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert conflict.diagnostics["terminal_result_conflict"]["existing_state"] == "SUCCEEDED"


def test_expired_request_cannot_publish_success(tmp_path, monkeypatch) -> None:
    import substrate.execution.durable_remote_transport as durable

    monkeypatch.setattr(durable, "now_s", lambda: 100.0)
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request(ttl_seconds=1))
    store.mark_claimed(req.request_id, claim_id="claim-1")
    monkeypatch.setattr(durable, "now_s", lambda: 200.0)

    assert store.deliverable_for_node("windows-desktop") == []
    expired = store.get_request(req.request_id)
    assert expired is not None
    assert expired.lifecycle_state == "EXPIRED"

    final = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="SUCCEEDED",
        result={"success": True},
    )
    assert final.lifecycle_state == "RECONCILIATION_REQUIRED"
