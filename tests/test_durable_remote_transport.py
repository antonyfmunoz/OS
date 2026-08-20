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
    delivered = store.mark_delivered(req.request_id)
    assert delivered.delivery_attempts == 1
    assert store.deliverable_for_node("windows-desktop", redelivery_after_s=60) == []
    claimed = store.mark_claimed(req.request_id, claim_id="claim-1", process_tree={"pid": 10})
    assert claimed.lifecycle_state == "CLAIMED"
    assert claimed.claim_id == "claim-1"
    assert store.deliverable_for_node("windows-desktop", redelivery_after_s=0) == []

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
    assert conflicted.reconciliation_deadline_at > conflicted.reconciliation_requested_at
    assert store.deliverable_for_node("windows-desktop") == []


def test_running_claim_conflict_requires_bounded_reconciliation(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")

    conflicted = store.mark_running(req.request_id, claim_id="claim-2")

    assert conflicted.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert conflicted.diagnostics["running_claim_conflict"]["existing"] == "claim-1"
    assert conflicted.reconciliation_deadline_at > conflicted.reconciliation_requested_at


def test_success_after_cancel_request_wins_before_cancel_ack(tmp_path) -> None:
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

    assert final.lifecycle_state == "SUCCEEDED"
    assert final.diagnostics["success_after_cancel_requested"]["resolution"] == (
        "success_won_before_acknowledged_cancellation"
    )
    assert store.result_for(req.request_id)["state"] == "SUCCEEDED"


def test_cancel_ack_rejects_late_success_but_preserves_evidence(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")
    store.request_cancel(req.request_id)
    cancelled = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="CANCELLED",
        result={"success": False, "error": "cancelled"},
        cleanup={"process_residue": []},
    )
    assert cancelled.lifecycle_state == "CANCELLED"

    final = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="SUCCEEDED",
        result={"success": True, "stdout": "too late"},
    )

    assert final.lifecycle_state == "CANCELLED"
    assert final.diagnostics["rejected_late_results"][0]["incoming_state"] == "SUCCEEDED"
    assert list((tmp_path / "results").glob(f"{req.request_id}.rejected-*.json"))


def test_unclaimed_result_is_rejected_and_cannot_terminalize(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())

    rejected = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="SUCCEEDED",
        result={"success": True, "stdout": "not claimed"},
    )

    assert rejected.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert rejected.diagnostics["result_without_claim"]["incoming"] == "claim-1"
    assert store.result_for(req.request_id) is None
    assert list((tmp_path / "results").glob(f"{req.request_id}.rejected-*.json"))


def test_duplicate_cancel_does_not_extend_cancellation_deadline(tmp_path, monkeypatch) -> None:
    import substrate.execution.durable_remote_transport as durable

    monkeypatch.setattr(durable, "now_s", lambda: 100.0)
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")
    first = store.request_cancel(req.request_id)

    monkeypatch.setattr(durable, "now_s", lambda: 120.0)
    second = store.request_cancel(req.request_id)

    assert second.cancellation_requested_at == first.cancellation_requested_at
    assert second.cancellation_deadline_at == first.cancellation_deadline_at


def test_update_request_cannot_regress_recovery_state(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")
    recovery = store.mark_claimed(req.request_id, claim_id="claim-2")
    stale = DurableRemoteRequest.from_dict(recovery.to_dict())
    stale.lifecycle_state = "RUNNING"

    store.update_request(stale, "RUNNING")

    final = store.get_request(req.request_id)
    assert final is not None
    assert final.lifecycle_state == "RECONCILIATION_REQUIRED"


def test_update_request_cannot_regress_active_state_or_drop_claim(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    running = store.mark_running(req.request_id, claim_id="claim-1", process_tree={"pid": 11})
    stale = DurableRemoteRequest.from_dict(running.to_dict())
    stale.lifecycle_state = "QUEUED"
    stale.claim_id = ""
    stale.process_tree = {}

    store.update_request(stale, "QUEUED")

    final = store.get_request(req.request_id)
    assert final is not None
    assert final.lifecycle_state == "RUNNING"
    assert final.claim_id == "claim-1"
    assert final.process_tree["pid"] == 11
    assert final.process_tree["running_at"] >= running.process_tree["running_at"]


def test_existing_terminal_result_recovers_active_request_after_crash_split(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")
    active = store.mark_running(req.request_id, claim_id="claim-1")
    digest = store._write_result_record(
        active,
        claim_id="claim-1",
        state="SUCCEEDED",
        result={"success": True, "stdout": "ok"},
        cleanup={"process_residue": []},
    )

    recovered = store.get_request(req.request_id)

    assert recovered is not None
    assert recovered.lifecycle_state == "SUCCEEDED"
    assert recovered.result_digest == digest
    assert recovered.diagnostics["recovered_terminal_result"] is True


def test_existing_terminal_result_without_prior_claim_is_not_recovered(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store._write_result_record(
        req,
        claim_id="claim-foreign",
        state="SUCCEEDED",
        result={"success": True, "stdout": "unclaimed"},
        cleanup={"process_residue": []},
    )

    current = store.get_request(req.request_id)

    assert current is not None
    assert current.lifecycle_state == "QUEUED"
    assert current.claim_id == ""
    assert current.diagnostics["unclaimed_terminal_result_ignored"][0]["result_claim_id"] == (
        "claim-foreign"
    )


def test_existing_terminal_result_with_bad_digest_is_not_recovered(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")
    running = store.mark_running(req.request_id, claim_id="claim-1")
    store._write_result_record(
        running,
        claim_id="claim-1",
        state="SUCCEEDED",
        result={"success": True, "stdout": "ok"},
        cleanup={"process_residue": []},
    )
    result_path = tmp_path / "results" / f"{req.request_id}.json"
    data = result_path.read_text(encoding="utf-8")
    result_path.write_text(data.replace('"stdout": "ok"', '"stdout": "tampered"'), encoding="utf-8")

    current = store.get_request(req.request_id)

    assert current is not None
    assert current.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert current.diagnostics["terminal_result_digest_mismatch"][0]["stored_result_digest"]
    assert store.result_for(req.request_id)["result"]["stdout"] == "tampered"


def test_terminal_result_with_bad_digest_enters_reconciliation(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")
    store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="SUCCEEDED",
        result={"success": True, "stdout": "ok"},
        cleanup={"process_residue": []},
    )
    result_path = tmp_path / "results" / f"{req.request_id}.json"
    data = result_path.read_text(encoding="utf-8")
    result_path.write_text(data.replace('"stdout": "ok"', '"stdout": "tampered"'), encoding="utf-8")

    current = store.get_request(req.request_id)

    assert current is not None
    assert current.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert current.diagnostics["terminal_result_digest_mismatch"][0]["stored_result_digest"]


def test_existing_terminal_result_with_residue_enters_reconciliation(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")
    running = store.mark_running(req.request_id, claim_id="claim-1")
    store._write_result_record(
        running,
        claim_id="claim-1",
        state="SUCCEEDED",
        result={"success": True, "stdout": "ok"},
        cleanup={"process_residue": [{"pid": 123, "state": "still_alive"}]},
    )

    current = store.get_request(req.request_id)

    assert current is not None
    assert current.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert current.diagnostics["success_without_cleanup"][0]["pid"] == 123
    assert current.cleanup["process_residue"][0]["state"] == "still_alive"


def test_existing_terminal_result_with_residue_is_not_deliverable(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")
    running = store.mark_running(req.request_id, claim_id="claim-1")
    store._write_result_record(
        running,
        claim_id="claim-1",
        state="FAILED",
        result={"success": False, "error": "timed out"},
        cleanup={"process_residue": [{"pid": 123, "state": "still_alive"}]},
    )

    assert store.deliverable_for_node("windows-desktop") == []
    current = store.get_request(req.request_id)
    assert current is not None
    assert current.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert current.diagnostics["failed_without_cleanup"][0]["pid"] == 123


def test_cancel_before_claim_terminalizes_without_execution(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())

    cancelled = store.request_cancel(req.request_id)

    assert cancelled.lifecycle_state == "CANCELLED"
    assert cancelled.claim_id == "unclaimed"
    assert cancelled.diagnostics["cancelled_before_claim"] is True
    assert store.result_for(req.request_id)["state"] == "CANCELLED"


def test_cancel_before_claim_terminal_result_recovers_after_crash_split(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store._write_result_record(
        req,
        claim_id="unclaimed",
        state="CANCELLED",
        result={"success": False, "error": "durable remote request cancelled before claim"},
        cleanup={"process_residue": []},
    )

    recovered = store.get_request(req.request_id)

    assert recovered is not None
    assert recovered.lifecycle_state == "CANCELLED"
    assert recovered.claim_id == "unclaimed"
    assert recovered.diagnostics["cancelled_before_claim"] is True


def test_cancel_before_claim_crash_split_is_not_deliverable(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store._write_result_record(
        req,
        claim_id="unclaimed",
        state="CANCELLED",
        result={"success": False, "error": "durable remote request cancelled before claim"},
        cleanup={"process_residue": []},
    )

    assert store.deliverable_for_node("windows-desktop") == []
    recovered = store.get_request(req.request_id)
    assert recovered is not None
    assert recovered.lifecycle_state == "CANCELLED"


def test_cancel_requested_cannot_be_regressed_by_late_claim_or_running_ack(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")
    cancelled = store.request_cancel(req.request_id)
    assert cancelled.lifecycle_state == "CANCEL_REQUESTED"

    late_claim = store.mark_claimed(req.request_id, claim_id="claim-1")
    late_running = store.mark_running(req.request_id, claim_id="claim-1")

    assert late_claim.lifecycle_state == "CANCEL_REQUESTED"
    assert late_running.lifecycle_state == "CANCEL_REQUESTED"
    final = store.get_request(req.request_id)
    assert final is not None
    assert final.lifecycle_state == "CANCEL_REQUESTED"
    assert final.cancellation_deadline_at == cancelled.cancellation_deadline_at


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
    assert conflict.lifecycle_state == "SUCCEEDED"
    assert conflict.diagnostics["rejected_late_results"][0]["existing_state"] == "SUCCEEDED"
    assert list((tmp_path / "results").glob(f"{req.request_id}.rejected-*.json"))


def test_remove_request_refuses_terminal_evidence_without_explicit_force(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")
    store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="SUCCEEDED",
        result={"success": True, "stdout": "ok"},
    )

    with pytest.raises(ValueError, match="terminal durable request"):
        store.remove_request(req.request_id)

    assert store.get_request(req.request_id) is not None
    assert store.result_for(req.request_id) is not None
    store.remove_request(req.request_id, force_terminal=True)
    assert store.get_request(req.request_id) is None


def test_expired_request_cannot_publish_success(tmp_path, monkeypatch) -> None:
    import substrate.execution.durable_remote_transport as durable

    monkeypatch.setattr(durable, "now_s", lambda: 100.0)
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request(ttl_seconds=1))
    store.mark_claimed(req.request_id, claim_id="claim-1")
    monkeypatch.setattr(durable, "now_s", lambda: 200.0)

    deliverable = store.deliverable_for_node("windows-desktop")
    assert [item.request_id for item in deliverable] == [req.request_id]
    expired = store.get_request(req.request_id)
    assert expired is not None
    assert expired.lifecycle_state == "CANCEL_REQUESTED"
    assert expired.diagnostics["expired_during_owned_execution"] is True

    final = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="SUCCEEDED",
        result={"success": True},
    )
    assert final.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert list((tmp_path / "results").glob(f"{req.request_id}.rejected-*.json"))


def test_bounded_reconciliation_terminalizes_failed_with_evidence(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1", process_tree={"root_pid": 123})
    conflicted = store.publish_result(
        req.request_id,
        claim_id="foreign-claim",
        state="SUCCEEDED",
        result={"success": True},
    )
    assert conflicted.lifecycle_state == "RECONCILIATION_REQUIRED"

    reconciled = store.reconcile_request(req.request_id, reason="unit-test-bound")

    assert reconciled.lifecycle_state == "FAILED"
    assert reconciled.diagnostics["reconciled_fail_closed"]["reason"] == "unit-test-bound"
    result = store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert result["result"]["error"] == "durable remote reconciliation failed closed"


def test_cancelled_with_process_residue_requires_reconciliation(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")
    store.request_cancel(req.request_id)

    final = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="CANCELLED",
        result={"success": False, "error": "cancelled"},
        cleanup={"process_residue": [{"pid": 123, "state": "still_alive"}]},
    )

    assert final.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert final.diagnostics["cancel_without_cleanup"][0]["state"] == "still_alive"
    assert final.cleanup["process_residue"][0]["pid"] == 123


def test_failed_with_process_residue_requires_reconciliation(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")

    final = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="FAILED",
        result={"success": False, "error": "timed out"},
        cleanup={"process_residue": [{"pid": 123, "state": "still_alive"}]},
    )

    assert final.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert final.diagnostics["failed_without_cleanup"][0]["state"] == "still_alive"
    assert final.cleanup["process_residue"][0]["pid"] == 123
    assert store.result_for(req.request_id) is None


def test_success_with_process_residue_requires_reconciliation(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")

    final = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="SUCCEEDED",
        result={"success": True, "stdout": "ok"},
        cleanup={"process_residue": [{"pid": 123, "state": "still_alive"}]},
    )

    assert final.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert final.diagnostics["success_without_cleanup"][0]["state"] == "still_alive"
    assert store.result_for(req.request_id) is None


def test_residue_bearing_reconciliation_does_not_terminalize_without_cleanup(
    tmp_path, monkeypatch
) -> None:
    import substrate.execution.durable_remote_transport as durable

    monkeypatch.setattr(durable, "now_s", lambda: 100.0)
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")
    store.request_cancel(req.request_id)
    store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="CANCELLED",
        result={"success": False, "error": "cancelled"},
        cleanup={"process_residue": [{"pid": 123, "state": "still_alive"}]},
    )

    monkeypatch.setattr(durable, "now_s", lambda: 200.0)
    final = store.get_request(req.request_id)
    unresolved = store.fail_unresolved_request(req.request_id, reason="unit-timeout")
    direct = store.reconcile_request(req.request_id, reason="direct-public-call")

    assert final is not None
    assert final.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert unresolved.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert direct.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert store.result_for(req.request_id) is None


def test_reconciliation_required_rejects_unrelated_same_claim_terminal_cleanup(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")
    conflicted = store.publish_result(
        req.request_id,
        claim_id="foreign",
        state="SUCCEEDED",
        result={"success": True},
    )
    assert conflicted.lifecycle_state == "RECONCILIATION_REQUIRED"

    assert store.request_cancel(req.request_id).lifecycle_state == "RECONCILIATION_REQUIRED"
    assert (
        store.mark_claimed(req.request_id, claim_id="claim-1").lifecycle_state
        == "RECONCILIATION_REQUIRED"
    )
    still_reconciling = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="FAILED",
        result={"success": False, "error": "late"},
        cleanup={
            "process_residue": [],
            "cancellation_generation": 100.0,
            "cancellation_deadline_at": 200.0,
        },
    )
    assert still_reconciling.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert "recovered_from_reconciliation_result" not in still_reconciling.diagnostics

    rejected = list((tmp_path / "results").glob(f"{req.request_id}.rejected-*.json"))
    assert len(rejected) >= 2


def test_reconciliation_required_rejects_same_claim_without_cleanup_proof(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")
    conflict = store.publish_result(
        req.request_id,
        claim_id="foreign",
        state="SUCCEEDED",
        result={"success": True},
    )
    assert conflict.lifecycle_state == "RECONCILIATION_REQUIRED"

    still_reconciling = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="FAILED",
        result={"success": False, "error": "late"},
    )

    assert still_reconciling.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert "recovered_from_reconciliation_result" not in still_reconciling.diagnostics
    rejected = list((tmp_path / "results").glob(f"{req.request_id}.rejected-*.json"))
    assert len(rejected) >= 2


def test_cancellation_ack_recovery_requires_matching_generation_and_deadline(
    tmp_path, monkeypatch
) -> None:
    import substrate.execution.durable_remote_transport as durable

    monkeypatch.setattr(durable, "now_s", lambda: 100.0)
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(
        _request(
            params={
                "command": "sleep",
                "timeout": 60,
                "budgets": {
                    "cancellation_delivery_timeout_s": 1,
                    "process_termination_timeout_s": 1,
                    "cancellation_ack_timeout_s": 1,
                    "reconciliation_timeout_s": 10,
                },
            }
        )
    )
    store.mark_claimed(req.request_id, claim_id="claim-1")
    cancelled = store.request_cancel(req.request_id)

    monkeypatch.setattr(durable, "now_s", lambda: 104.0)
    current = store.get_request(req.request_id)
    assert current is not None
    assert current.lifecycle_state == "RECONCILIATION_REQUIRED"

    wrong_generation = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="CANCELLED",
        result={"success": False, "error": "cancelled"},
        cleanup={
            "process_residue": [],
            "cancellation_generation": cancelled.cancellation_requested_at - 1,
            "cancellation_deadline_at": cancelled.cancellation_deadline_at,
        },
    )
    assert wrong_generation.lifecycle_state == "RECONCILIATION_REQUIRED"

    recovered = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="CANCELLED",
        result={"success": False, "error": "cancelled"},
        cleanup={
            "process_residue": [],
            "cancellation_generation": cancelled.cancellation_requested_at,
            "cancellation_deadline_at": cancelled.cancellation_deadline_at,
        },
    )

    assert recovered.lifecycle_state == "CANCELLED"
    assert recovered.diagnostics["recovered_from_reconciliation_result"][0]["claim_id"] == "claim-1"


def test_cancel_requested_eventually_fails_closed_if_not_acknowledged(tmp_path, monkeypatch) -> None:
    import substrate.execution.durable_remote_transport as durable

    monkeypatch.setattr(durable, "now_s", lambda: 100.0)
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1", process_tree={"root_pid": 123})
    store.request_cancel(req.request_id)

    monkeypatch.setattr(durable, "now_s", lambda: 176.0)
    out = store.deliverable_for_node("windows-desktop")

    assert out == []
    final = store.get_request(req.request_id)
    assert final is not None
    assert final.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert final.diagnostics["reconciliation_reasons"] == ["cancellation_ack_deadline_expired"]

    monkeypatch.setattr(durable, "now_s", lambda: 191.0)
    final = store.get_request(req.request_id)
    assert final is not None
    assert final.lifecycle_state == "FAILED"
    assert final.diagnostics["reconciled_fail_closed"]["reason"] == "reconciliation_deadline_expired"


def test_get_request_converges_overdue_cancel_without_node_delivery(tmp_path, monkeypatch) -> None:
    import substrate.execution.durable_remote_transport as durable

    monkeypatch.setattr(durable, "now_s", lambda: 100.0)
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")
    store.request_cancel(req.request_id)

    monkeypatch.setattr(durable, "now_s", lambda: 176.0)
    final = store.get_request(req.request_id)

    assert final is not None
    assert final.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert final.diagnostics["reconciliation_reasons"] == ["cancellation_ack_deadline_expired"]

    monkeypatch.setattr(durable, "now_s", lambda: 191.0)
    final = store.get_request(req.request_id)
    assert final is not None
    assert final.lifecycle_state == "FAILED"
    assert final.diagnostics["reconciled_fail_closed"]["reason"] == "reconciliation_deadline_expired"


def test_get_request_converges_overdue_reconciliation_without_health_sweep(
    tmp_path, monkeypatch
) -> None:
    import substrate.execution.durable_remote_transport as durable

    monkeypatch.setattr(durable, "now_s", lambda: 100.0)
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")
    conflict = store.mark_claimed(req.request_id, claim_id="claim-2")
    assert conflict.lifecycle_state == "RECONCILIATION_REQUIRED"

    monkeypatch.setattr(durable, "now_s", lambda: 116.0)
    final = store.get_request(req.request_id)

    assert final is not None
    assert final.lifecycle_state == "FAILED"
    assert final.diagnostics["reconciled_fail_closed"]["reason"] == "reconciliation_deadline_expired"


def test_reconcile_due_requests_advances_without_node_delivery(tmp_path, monkeypatch) -> None:
    import substrate.execution.durable_remote_transport as durable

    monkeypatch.setattr(durable, "now_s", lambda: 100.0)
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1", process_tree={"root_pid": 123})
    store.request_cancel(req.request_id)

    monkeypatch.setattr(durable, "now_s", lambda: 176.0)
    updated = store.reconcile_due_requests()

    assert [item.request_id for item in updated] == [req.request_id]
    final = store.get_request(req.request_id)
    assert final is not None
    assert final.lifecycle_state == "RECONCILIATION_REQUIRED"

    monkeypatch.setattr(durable, "now_s", lambda: 191.0)
    updated = store.reconcile_due_requests()

    assert [item.request_id for item in updated] == [req.request_id]
    final = store.get_request(req.request_id)
    assert final is not None
    assert final.lifecycle_state == "FAILED"


def test_fail_unresolved_request_terminalizes_and_records_evidence(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1", process_tree={"root_pid": 123})
    store.request_cancel(req.request_id)

    final = store.fail_unresolved_request(req.request_id, reason="unit-timeout")

    assert final.lifecycle_state == "FAILED"
    assert final.diagnostics["unresolved_failed_closed"]["reason"] == "unit-timeout"
    result = store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"


def test_terminal_replay_with_cleanup_conflict_does_not_get_dropped(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")
    first = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="CANCELLED",
        result={"success": False, "error": "cancelled"},
        cleanup={"process_residue": []},
    )
    assert first.lifecycle_state == "CANCELLED"

    conflict = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="CANCELLED",
        result={"success": False, "error": "cancelled"},
        cleanup={"process_residue": [{"pid": 999, "state": "still_alive"}]},
    )

    assert conflict.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert conflict.diagnostics["terminal_cancel_cleanup_conflict"][0]["state"] == "still_alive"
    assert conflict.cleanup["process_residue"][0]["pid"] == 999
    observed = store.get_request(req.request_id)
    assert observed is not None
    assert observed.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert observed.cleanup["process_residue"][0]["pid"] == 999
    rejected = list((tmp_path / "results").glob(f"{req.request_id}.rejected-*.json"))
    assert rejected
