from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

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
        "idempotency_key": f"test-idem-{uuid4().hex}",
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


def test_store_rejects_unknown_capability_before_queue_persistence(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = _request(capability="unknown.execute")

    with pytest.raises(ValueError, match="canonical consequential policy"):
        store.put_request(req)

    assert store.get_request(req.request_id) is None
    assert store.deliverable_for_node("windows-desktop") == []


def test_same_claim_claimed_replay_does_not_regress_running_state(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1", process_tree={"node_pid": 10})
    running = store.mark_running(
        req.request_id,
        claim_id="claim-1",
        process_tree={"node_pid": 10, "root_pid": 11, "running_at": 2.0},
    )
    assert running.lifecycle_state == "RUNNING"

    replay = store.mark_claimed(
        req.request_id,
        claim_id="claim-1",
        process_tree={"node_pid": 10, "claimed_at": 3.0},
    )

    assert replay.lifecycle_state == "RUNNING"
    assert replay.claim_id == "claim-1"
    assert replay.process_tree["root_pid"] == 11
    assert replay.process_tree["running_at"] == 2.0


def test_duplicate_request_id_with_different_payload_fails_closed(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = _request(idempotency_key="same-key")
    store.put_request(req)
    duplicate = DurableRemoteRequest.from_dict(req.to_dict())
    duplicate.params = {"command": "echo different", "timeout": 5}
    duplicate.payload_digest = ""
    duplicate.__post_init__()

    with pytest.raises(ValueError, match="idempotency conflict: payload_digest"):
        store.put_request(duplicate)


def test_different_request_id_same_idempotency_key_returns_canonical_request(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    first = store.put_request(_request(idempotency_key="logical-key"))
    replay = _request(idempotency_key="logical-key")

    returned = store.put_request(replay)

    assert returned.request_id == first.request_id
    assert returned.request_id != replay.request_id
    assert len(list((tmp_path / "requests").glob("*.json"))) == 1
    stored = store.get_request(first.request_id)
    assert stored is not None
    assert stored.diagnostics["idempotent_replays"][0]["incoming_transport_request_id"] == (
        replay.request_id
    )


def test_same_idempotency_key_different_payload_fails_closed(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    original = store.put_request(_request(idempotency_key="conflict-key"))
    conflicting = _request(
        idempotency_key="conflict-key",
        params={"command": "echo different", "timeout": 5},
    )

    with pytest.raises(ValueError, match="idempotency conflict: payload_digest"):
        store.put_request(conflicting)

    assert store.get_request(original.request_id).request_id == original.request_id  # type: ignore[union-attr]
    assert len(list((tmp_path / "requests").glob("*.json"))) == 1


def test_same_key_tampered_params_with_copied_digest_fails_closed(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    original = store.put_request(_request(idempotency_key="copied-digest-key"))
    tampered = _request(idempotency_key="copied-digest-key")
    tampered.params = {"command": "echo tampered", "timeout": 5}
    tampered.payload_digest = original.payload_digest

    with pytest.raises(ValueError, match="idempotency conflict: payload_digest"):
        store.put_request(tampered)

    assert len(list((tmp_path / "requests").glob("*.json"))) == 1


@pytest.mark.parametrize(
    ("field_name", "override"),
    [
        ("capability", {"capability": "terminal.create"}),
        ("operation_type", {"operation_type": "different_operation"}),
        ("candidate_sha", {"candidate_sha": "different-sha"}),
        ("node_id", {"node_id": "different-node"}),
        ("risk_class", {"risk_class": "write"}),
        ("authority_id", {"authority_id": "different-authority"}),
    ],
)
def test_same_idempotency_key_different_operation_identity_fails_closed(
    tmp_path,
    field_name: str,
    override: dict[str, object],
) -> None:
    store = DurableRemoteStore(tmp_path)
    store.put_request(_request(idempotency_key=f"conflict-{field_name}"))

    with pytest.raises(ValueError, match=f"idempotency conflict: {field_name}"):
        store.put_request(_request(idempotency_key=f"conflict-{field_name}", **override))

    assert len(list((tmp_path / "requests").glob("*.json"))) == 1


def test_same_idempotency_key_different_correlation_returns_canonical_request(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    first = store.put_request(_request(idempotency_key="correlation-replay", correlation_id="corr-a"))

    replay = store.put_request(
        _request(idempotency_key="correlation-replay", correlation_id="corr-b")
    )

    assert replay.request_id == first.request_id
    stored = store.get_request(first.request_id)
    assert stored is not None
    assert stored.correlation_id == "corr-a"
    assert stored.diagnostics["idempotent_replays"][0]["incoming_correlation_id"] == "corr-b"


def test_concurrent_same_key_admission_creates_one_canonical_request(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)

    def admit() -> str:
        return store.put_request(_request(idempotency_key="concurrent-key")).request_id

    with ThreadPoolExecutor(max_workers=2) as pool:
        request_ids = list(pool.map(lambda _: admit(), range(2)))

    assert len(set(request_ids)) == 1
    assert len(list((tmp_path / "requests").glob("*.json"))) == 1


def test_live_idempotency_lock_is_not_stolen_by_age(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    lock_path = store._idempotency_lock_path("live-holder-key")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(f"{os.getpid()} 1.0\n", encoding="ascii")
    os.utime(lock_path, (1.0, 1.0))

    with pytest.raises(TimeoutError, match="idempotency"):
        with store._idempotency_lock("live-holder-key", timeout_s=0.01):
            raise AssertionError("live idempotency lock was stolen")

    assert lock_path.exists()


def test_malformed_idempotency_lock_is_reclaimed_after_timeout(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    lock_path = store._idempotency_lock_path("malformed-holder-key")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("", encoding="ascii")
    os.utime(lock_path, (1.0, 1.0))

    with store._idempotency_lock("malformed-holder-key", timeout_s=0.01):
        assert lock_path.exists()

    assert not lock_path.exists()


def test_update_request_cannot_mutate_admitted_operation_identity(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    original = store.put_request(_request(idempotency_key="immutable-identity"))
    mutated = DurableRemoteRequest.from_dict(original.to_dict())
    mutated.candidate_sha = "different-sha"
    mutated.params = {"command": "echo altered", "timeout": 5}
    mutated.payload_digest = original.payload_digest
    mutated.lifecycle_state = "CLAIMED"
    mutated.claim_id = "claim-1"

    store.update_request(mutated, "MUTATED_UPDATE")

    stored = store.get_request(original.request_id)
    assert stored is not None
    assert stored.request_id == original.request_id
    assert stored.candidate_sha == original.candidate_sha
    assert stored.params == original.params
    assert stored.payload_digest == original.payload_digest
    assert stored.lifecycle_state == "QUEUED"
    assert stored.claim_id == ""
    rejected = stored.diagnostics["identity_mutation_rejected"][0]
    assert set(rejected["fields"]) == {"candidate_sha", "payload_digest", "params"}


def test_update_request_cannot_mutate_admitted_verdict_material(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    original = _request(
        idempotency_key="immutable-verdict",
        params={"command": "echo ok", "timeout": 5, "governance_verdict_id": "verdict-A"},
    )
    original.diagnostics["verdict_payload_digest"] = "digest-A"
    original = store.put_request(original)
    mutated = DurableRemoteRequest.from_dict(original.to_dict())
    mutated.params["governance_verdict_id"] = "verdict-B"
    mutated.diagnostics["verdict_payload_digest"] = "digest-B"
    mutated.lifecycle_state = "CLAIMED"
    mutated.claim_id = "claim-1"

    store.update_request(mutated, "MUTATED_VERDICT_UPDATE")

    stored = store.get_request(original.request_id)
    assert stored is not None
    assert stored.params["governance_verdict_id"] == "verdict-A"
    assert stored.diagnostics["verdict_payload_digest"] == "digest-A"
    assert stored.lifecycle_state == "QUEUED"
    rejected = stored.diagnostics["identity_mutation_rejected"][0]
    assert set(rejected["fields"]) == {"params", "diagnostics.verdict_payload_digest"}


def test_missing_index_recovery_with_duplicate_same_key_records_fails_closed(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    original = store.put_request(_request(idempotency_key="legacy-duplicate"))
    duplicate = _request(idempotency_key="legacy-duplicate")
    duplicate.created_at = original.created_at + 1.0
    (tmp_path / "requests" / f"{duplicate.request_id}.json").write_text(
        json.dumps(duplicate.to_dict(), sort_keys=True),
        encoding="utf-8",
    )
    for path in (tmp_path / "idempotency").glob("*.json"):
        path.unlink()

    with pytest.raises(ValueError, match="ambiguous idempotency recovery"):
        store.put_request(_request(idempotency_key="legacy-duplicate"))

    for request_id in (original.request_id, duplicate.request_id):
        quarantined = store.get_request(request_id)
        assert quarantined is not None
        assert quarantined.lifecycle_state == "RECONCILIATION_REQUIRED"
        assert quarantined.diagnostics["ambiguous_idempotency_recovery"]["request_ids"] == sorted(
            [original.request_id, duplicate.request_id]
        )
    assert store.deliverable_for_node("windows-desktop") == []


def test_missing_index_recovery_rejects_earlier_created_duplicate_takeover(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    original = store.put_request(_request(idempotency_key="created-at-takeover"))
    duplicate = _request(idempotency_key="created-at-takeover")
    duplicate.created_at = original.created_at - 100.0
    (tmp_path / "requests" / f"{duplicate.request_id}.json").write_text(
        json.dumps(duplicate.to_dict(), sort_keys=True),
        encoding="utf-8",
    )
    for path in (tmp_path / "idempotency").glob("*.json"):
        path.unlink()

    with pytest.raises(ValueError, match="ambiguous idempotency recovery"):
        store.put_request(_request(idempotency_key="created-at-takeover"))

    assert store.deliverable_for_node("windows-desktop") == []


def test_index_present_replay_quarantines_duplicate_same_key_records(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    original = store.put_request(_request(idempotency_key="indexed-legacy-duplicate"))
    duplicate = _request(idempotency_key="indexed-legacy-duplicate")
    duplicate.created_at = original.created_at + 1.0
    (tmp_path / "requests" / f"{duplicate.request_id}.json").write_text(
        json.dumps(duplicate.to_dict(), sort_keys=True),
        encoding="utf-8",
    )

    replay = store.put_request(_request(idempotency_key="indexed-legacy-duplicate"))

    assert replay.request_id == original.request_id
    quarantined = store.get_request(duplicate.request_id)
    assert quarantined is not None
    assert quarantined.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert quarantined.diagnostics["duplicate_idempotency_noncanonical"]["canonical_request_id"] == (
        original.request_id
    )
    assert [req.request_id for req in store.deliverable_for_node("windows-desktop", limit=1)] == [
        original.request_id
    ]


def test_delivery_scan_quarantines_index_present_duplicate_same_key_records(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    original_req = _request(idempotency_key="deliverable-duplicate")
    original_req.request_id = "drc-a-canonical"
    original = store.put_request(original_req)
    duplicate = _request(idempotency_key="deliverable-duplicate")
    duplicate.request_id = "drc-z-duplicate"
    duplicate.created_at = original.created_at + 1.0
    (tmp_path / "requests" / f"{duplicate.request_id}.json").write_text(
        json.dumps(duplicate.to_dict(), sort_keys=True),
        encoding="utf-8",
    )

    assert [req.request_id for req in store.deliverable_for_node("windows-desktop", limit=1)] == [
        original.request_id
    ]
    quarantined = store.get_request(duplicate.request_id)
    assert quarantined is not None
    assert quarantined.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert quarantined.diagnostics["duplicate_idempotency_noncanonical"]["canonical_request_id"] == (
        original.request_id
    )


def test_noncanonical_duplicate_cannot_mutate_lifecycle_or_index(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    original = store.put_request(_request(idempotency_key="stale-inbound-duplicate"))
    duplicate = _request(idempotency_key="stale-inbound-duplicate")
    duplicate.created_at = original.created_at + 1.0
    (tmp_path / "requests" / f"{duplicate.request_id}.json").write_text(
        json.dumps(duplicate.to_dict(), sort_keys=True),
        encoding="utf-8",
    )

    diagnosed = store.record_transport_diagnostic(
        duplicate.request_id,
        "control_frame_received",
    )
    claimed = store.mark_claimed(duplicate.request_id, claim_id="stale-claim")
    running = store.mark_running(duplicate.request_id, claim_id="stale-claim")

    for observed in (diagnosed, claimed, running):
        assert observed is not None
        assert observed.request_id == duplicate.request_id
        assert observed.lifecycle_state == "RECONCILIATION_REQUIRED"
        assert observed.claim_id == ""
        assert observed.diagnostics["duplicate_idempotency_noncanonical"]["canonical_request_id"] == (
            original.request_id
        )

    index_files = list((tmp_path / "idempotency").glob("*.json"))
    assert len(index_files) == 1
    index = json.loads(index_files[0].read_text(encoding="utf-8"))
    assert index["canonical_request_id"] == original.request_id


def test_update_request_rejects_noncanonical_duplicate_before_lifecycle_write(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    original = store.put_request(_request(idempotency_key="stale-update-duplicate"))
    duplicate = _request(idempotency_key="stale-update-duplicate")
    (tmp_path / "requests" / f"{duplicate.request_id}.json").write_text(
        json.dumps(duplicate.to_dict(), sort_keys=True),
        encoding="utf-8",
    )
    forged = DurableRemoteRequest.from_dict(duplicate.to_dict())
    forged.lifecycle_state = "RUNNING"
    forged.claim_id = "evil-claim"
    forged.process_tree = {"root_pid": 99999}

    store.update_request(forged, "FORGED_DUPLICATE_RUNNING")

    rejected = store.get_request(duplicate.request_id)
    assert rejected is not None
    assert rejected.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert rejected.claim_id == ""
    assert rejected.process_tree == {}
    assert rejected.diagnostics["duplicate_idempotency_noncanonical"]["canonical_request_id"] == (
        original.request_id
    )
    assert rejected.diagnostics["noncanonical_event_rejected"][-1]["event"] == (
        "FORGED_DUPLICATE_RUNNING"
    )
    stored_original = store.get_request(original.request_id)
    assert stored_original is not None
    assert stored_original.lifecycle_state == "QUEUED"
    index_files = list((tmp_path / "idempotency").glob("*.json"))
    assert len(index_files) == 1
    index = json.loads(index_files[0].read_text(encoding="utf-8"))
    assert index["canonical_request_id"] == original.request_id


def test_update_request_cannot_admit_duplicate_when_index_missing(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    original = store.put_request(_request(idempotency_key="update-missing-index"))
    store.mark_claimed(original.request_id, claim_id="claim-1")
    store.mark_running(original.request_id, claim_id="claim-1", process_tree={"root_pid": 111})
    for path in (tmp_path / "idempotency").glob("*.json"):
        path.unlink()
    duplicate = _request(idempotency_key="update-missing-index")
    duplicate.lifecycle_state = "QUEUED"

    store.update_request(duplicate, "FORGED_UPDATE_ADMISSION")

    rejected = store.get_request(duplicate.request_id)
    assert rejected is not None
    assert rejected.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert rejected.diagnostics["duplicate_idempotency_noncanonical"]["canonical_request_id"] == (
        original.request_id
    )
    stored_original = store.get_request(original.request_id)
    assert stored_original is not None
    assert stored_original.lifecycle_state == "RUNNING"
    assert stored_original.claim_id == "claim-1"
    assert stored_original.process_tree["root_pid"] == 111
    assert store.deliverable_for_node("windows-desktop") == []
    index_files = list((tmp_path / "idempotency").glob("*.json"))
    assert len(index_files) == 1
    index = json.loads(index_files[0].read_text(encoding="utf-8"))
    assert index["canonical_request_id"] == original.request_id


def test_noncanonical_duplicate_claim_is_rejected_without_prior_diagnostic(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    original = store.put_request(_request(idempotency_key="direct-stale-claim"))
    duplicate = _request(idempotency_key="direct-stale-claim")
    duplicate.created_at = original.created_at + 1.0
    (tmp_path / "requests" / f"{duplicate.request_id}.json").write_text(
        json.dumps(duplicate.to_dict(), sort_keys=True),
        encoding="utf-8",
    )

    claimed = store.mark_claimed(duplicate.request_id, claim_id="stale-claim")

    assert claimed.request_id == duplicate.request_id
    assert claimed.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert claimed.claim_id == ""
    assert claimed.diagnostics["duplicate_idempotency_noncanonical"]["canonical_request_id"] == (
        original.request_id
    )
    index_files = list((tmp_path / "idempotency").glob("*.json"))
    assert len(index_files) == 1
    index = json.loads(index_files[0].read_text(encoding="utf-8"))
    assert index["canonical_request_id"] == original.request_id


def test_noncanonical_duplicate_result_is_rejected_without_index_takeover(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    original = store.put_request(_request(idempotency_key="stale-result-duplicate"))
    duplicate = _request(idempotency_key="stale-result-duplicate")
    duplicate.created_at = original.created_at + 1.0
    duplicate.lifecycle_state = "RUNNING"
    duplicate.claim_id = "stale-claim"
    (tmp_path / "requests" / f"{duplicate.request_id}.json").write_text(
        json.dumps(duplicate.to_dict(), sort_keys=True),
        encoding="utf-8",
    )

    rejected = store.publish_result(
        duplicate.request_id,
        claim_id="stale-claim",
        state="SUCCEEDED",
        result={"ok": True},
        cleanup={"process_residue": []},
    )

    assert rejected.request_id == duplicate.request_id
    assert rejected.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert rejected.result_digest == ""
    assert store.result_for(duplicate.request_id) is None
    index_files = list((tmp_path / "idempotency").glob("*.json"))
    assert len(index_files) == 1
    index = json.loads(index_files[0].read_text(encoding="utf-8"))
    assert index["canonical_request_id"] == original.request_id
    stored_original = store.get_request(original.request_id)
    assert stored_original is not None
    assert stored_original.lifecycle_state == "QUEUED"


def test_noncanonical_duplicate_reconcile_cannot_write_terminal_result(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    original = store.put_request(_request(idempotency_key="stale-reconcile-duplicate"))
    duplicate = _request(idempotency_key="stale-reconcile-duplicate")
    duplicate.created_at = original.created_at + 1.0
    duplicate.lifecycle_state = "RECONCILIATION_REQUIRED"
    duplicate.reconciliation_requested_at = 1.0
    duplicate.reconciliation_deadline_at = 1.0
    (tmp_path / "requests" / f"{duplicate.request_id}.json").write_text(
        json.dumps(duplicate.to_dict(), sort_keys=True),
        encoding="utf-8",
    )

    rejected = store.reconcile_request(duplicate.request_id, reason="duplicate-timeout")

    assert rejected.request_id == duplicate.request_id
    assert rejected.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert rejected.result_digest == ""
    assert store.result_for(duplicate.request_id) is None
    stored_original = store.get_request(original.request_id)
    assert stored_original is not None
    assert stored_original.lifecycle_state == "QUEUED"


def test_noncanonical_duplicate_fail_unresolved_cannot_write_terminal_result(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    original = store.put_request(_request(idempotency_key="stale-unresolved-duplicate"))
    duplicate = _request(idempotency_key="stale-unresolved-duplicate")
    duplicate.created_at = original.created_at + 1.0
    duplicate.lifecycle_state = "CLAIMED"
    duplicate.claim_id = "stale-claim"
    (tmp_path / "requests" / f"{duplicate.request_id}.json").write_text(
        json.dumps(duplicate.to_dict(), sort_keys=True),
        encoding="utf-8",
    )

    rejected = store.fail_unresolved_request(duplicate.request_id, reason="duplicate-timeout")

    assert rejected.request_id == duplicate.request_id
    assert rejected.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert rejected.result_digest == ""
    assert store.result_for(duplicate.request_id) is None
    stored_original = store.get_request(original.request_id)
    assert stored_original is not None
    assert stored_original.lifecycle_state == "QUEUED"


def test_idempotency_index_write_cannot_take_over_existing_canonical_binding(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    original = store.put_request(_request(idempotency_key="index-takeover"))
    duplicate = _request(idempotency_key="index-takeover")

    with pytest.raises(ValueError, match="idempotency index canonical request mismatch"):
        store._write_idempotency_index(duplicate)

    index_files = list((tmp_path / "idempotency").glob("*.json"))
    assert len(index_files) == 1
    index = json.loads(index_files[0].read_text(encoding="utf-8"))
    assert index["canonical_request_id"] == original.request_id


@pytest.mark.parametrize("state", ["RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", "RECONCILIATION_REQUIRED"])
def test_duplicate_after_existing_lifecycle_returns_same_trajectory(tmp_path, state: str) -> None:
    store = DurableRemoteStore(tmp_path)
    original = store.put_request(_request(idempotency_key=f"terminal-{state.lower()}"))
    if state == "RUNNING":
        store.mark_claimed(original.request_id, claim_id="claim-1")
        store.mark_running(original.request_id, claim_id="claim-1")
    elif state == "SUCCEEDED":
        store.mark_claimed(original.request_id, claim_id="claim-1")
        store.mark_running(original.request_id, claim_id="claim-1")
        store.publish_result(
            original.request_id,
            claim_id="claim-1",
            state="SUCCEEDED",
            result={"ok": True},
            cleanup={"process_residue": []},
        )
    elif state == "FAILED":
        store.mark_claimed(original.request_id, claim_id="claim-1")
        store.mark_running(original.request_id, claim_id="claim-1")
        store.publish_result(
            original.request_id,
            claim_id="claim-1",
            state="FAILED",
            result={"ok": False},
            cleanup={"process_residue": []},
        )
    elif state == "CANCELLED":
        store.request_cancel(original.request_id)
    else:
        store.mark_claimed(original.request_id, claim_id="claim-1")
        store.mark_claimed(original.request_id, claim_id="claim-2")

    replay = store.put_request(_request(idempotency_key=f"terminal-{state.lower()}"))

    assert replay.request_id == original.request_id
    assert len(list((tmp_path / "requests").glob("*.json"))) == 1


def test_missing_idempotency_key_on_consequential_request_fails_closed(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = make_request(
        correlation_id="missing-key",
        candidate_sha="abc123",
        node_id="windows-desktop",
        operation_type="codex_probe",
        capability="shell",
        params={"command": "echo ok", "timeout": 5},
        ttl_seconds=60,
    )

    with pytest.raises(ValueError, match="requires idempotency_key"):
        store.put_request(req)

    assert list((tmp_path / "requests").glob("*.json")) == []


def test_omitted_key_retry_with_new_correlation_cannot_fork_request(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    first = make_request(
        correlation_id="retry-a",
        candidate_sha="abc123",
        node_id="windows-desktop",
        operation_type="codex_probe",
        capability="shell",
        params={"command": "echo ok", "timeout": 5},
        ttl_seconds=60,
    )
    second = make_request(
        correlation_id="retry-b",
        candidate_sha="abc123",
        node_id="windows-desktop",
        operation_type="codex_probe",
        capability="shell",
        params={"command": "echo ok", "timeout": 5},
        ttl_seconds=60,
    )

    for req in (first, second):
        with pytest.raises(ValueError, match="requires idempotency_key"):
            store.put_request(req)

    assert list((tmp_path / "requests").glob("*.json")) == []


def test_missing_idempotency_index_is_recovered_from_request_scan(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    original = store.put_request(_request(idempotency_key="scan-recovery"))
    for path in (tmp_path / "idempotency").glob("*.json"):
        path.unlink()

    replay = store.put_request(_request(idempotency_key="scan-recovery"))

    assert replay.request_id == original.request_id
    assert len(list((tmp_path / "idempotency").glob("*.json"))) == 1
    assert len(list((tmp_path / "requests").glob("*.json"))) == 1


def test_idempotency_index_pointing_nowhere_fails_closed(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    original = store.put_request(_request(idempotency_key="dangling-index"))
    (tmp_path / "requests" / f"{original.request_id}.json").unlink()

    with pytest.raises(ValueError, match="points to missing canonical request"):
        store.put_request(_request(idempotency_key="dangling-index"))

    assert len(list((tmp_path / "requests").glob("*.json"))) == 0


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


def test_running_without_prior_claim_fails_closed(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())

    rejected = store.mark_running(req.request_id, claim_id="claim-1")

    assert rejected.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert not rejected.claim_id
    assert rejected.diagnostics["running_without_claim"] == {"incoming": "claim-1"}
    assert store.deliverable_for_node("windows-desktop") == []


def test_running_requires_current_claimed_lifecycle(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    delivered = store.mark_delivered(req.request_id)
    delivered.claim_id = "claim-1"
    store.update_request(delivered, "MALFORMED_CLAIM_INJECTION")

    current = store.get_request(req.request_id)
    assert current is not None
    assert not current.claim_id

    rejected = store.mark_running(req.request_id, claim_id="claim-1")

    assert rejected.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert rejected.diagnostics["running_without_claim"] == {"incoming": "claim-1"}


def test_running_rejects_corrupt_active_claim_outside_claimed_state(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    corrupt = store.mark_delivered(req.request_id)
    corrupt.lifecycle_state = "DELIVERED"
    corrupt.claim_id = "claim-1"
    store._update_request_locked(corrupt, "CORRUPT_CLAIM_FOR_TEST")

    rejected = store.mark_running(req.request_id, claim_id="claim-1")

    assert rejected.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert rejected.diagnostics["running_without_claimed_state"]["state"] == "DELIVERED"


def test_same_claim_running_replay_updates_execution_evidence_without_reconciliation(
    tmp_path,
) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1", process_tree={"node_pid": 10})
    pre_start = store.mark_running(
        req.request_id,
        claim_id="claim-1",
        process_tree={"node_pid": 10, "root_pid": None, "pre_start_containment": True},
    )
    assert pre_start.lifecycle_state == "RUNNING"

    updated = store.mark_running(
        req.request_id,
        claim_id="claim-1",
        process_tree={"root_pid": 1234, "command_digest": req.payload_digest},
    )

    assert updated.lifecycle_state == "RUNNING"
    assert updated.claim_id == "claim-1"
    assert updated.process_tree["node_pid"] == 10
    assert updated.process_tree["root_pid"] == 1234
    assert updated.process_tree["command_digest"] == req.payload_digest
    assert "running_without_claimed_state" not in updated.diagnostics


def test_late_running_after_succeeded_is_ignored_even_for_foreign_claim(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")
    store.mark_running(req.request_id, claim_id="claim-1", process_tree={"root_pid": 22})
    store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="SUCCEEDED",
        result={"success": True, "stdout": "done"},
        cleanup={"process_residue": []},
    )

    late = store.mark_running(req.request_id, claim_id="foreign-claim")

    assert late.lifecycle_state == "SUCCEEDED"
    assert late.claim_id == "claim-1"
    assert "running_claim_conflict" not in late.diagnostics
    events = [
        json.loads(line)["event"]
        for line in store.events_path.read_text(encoding="utf-8").splitlines()
        if json.loads(line)["request_id"] == req.request_id
    ]
    assert events[-1] == "LATE_RUNNING_IGNORED"


def test_same_claim_late_running_after_succeeded_is_ignored(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")
    store.mark_running(req.request_id, claim_id="claim-1", process_tree={"root_pid": 22})
    store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="SUCCEEDED",
        result={"success": True, "stdout": "done"},
        cleanup={"process_residue": []},
    )

    late = store.mark_running(
        req.request_id,
        claim_id="claim-1",
        process_tree={"root_pid": 99, "late": True},
    )

    assert late.lifecycle_state == "SUCCEEDED"
    assert late.process_tree["root_pid"] == 22
    assert "running_without_claimed_state" not in late.diagnostics
    assert "running_claim_conflict" not in late.diagnostics
    events = [
        json.loads(line)["event"]
        for line in store.events_path.read_text(encoding="utf-8").splitlines()
        if json.loads(line)["request_id"] == req.request_id
    ]
    assert events[-1] == "LATE_RUNNING_IGNORED"


def test_late_running_after_failed_cancelled_or_recovery_terminal_does_not_regress(
    tmp_path,
) -> None:
    store = DurableRemoteStore(tmp_path)

    failed = store.put_request(_request(idempotency_key="failed"))
    store.mark_claimed(failed.request_id, claim_id="claim-failed")
    store.mark_running(failed.request_id, claim_id="claim-failed")
    store.publish_result(
        failed.request_id,
        claim_id="claim-failed",
        state="FAILED",
        result={"success": False, "error": "boom"},
        cleanup={"process_residue": []},
    )
    assert store.mark_running(failed.request_id, claim_id="late").lifecycle_state == "FAILED"

    cancelled = store.put_request(_request(idempotency_key="cancelled"))
    store.mark_claimed(cancelled.request_id, claim_id="claim-cancelled")
    current = store.request_cancel(cancelled.request_id)
    store.publish_result(
        cancelled.request_id,
        claim_id="claim-cancelled",
        state="CANCELLED",
        result={"success": False, "error": "cancelled"},
        cleanup={
            "process_residue": [],
            **current.cancellation_identity(claim_id="claim-cancelled"),
        },
    )
    assert (
        store.mark_running(cancelled.request_id, claim_id="late").lifecycle_state
        == "CANCELLED"
    )

    recovery = store.put_request(_request(idempotency_key="recovery"))
    store.mark_claimed(recovery.request_id, claim_id="claim-1")
    assert store.mark_claimed(recovery.request_id, claim_id="claim-2").lifecycle_state == (
        "RECONCILIATION_REQUIRED"
    )
    assert (
        store.mark_running(recovery.request_id, claim_id="claim-2").lifecycle_state
        == "RECONCILIATION_REQUIRED"
    )


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
        cleanup={"process_residue": []},
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
    current = store.get_request(req.request_id)
    assert current is not None
    cancelled = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="CANCELLED",
        result={"success": False, "error": "cancelled"},
        cleanup={
            "process_residue": [],
            **current.cancellation_identity(claim_id="claim-1"),
        },
    )
    assert cancelled.lifecycle_state == "CANCELLED"
    request_path = store._request_path(req.request_id)
    terminal_bytes = request_path.read_bytes()

    final = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="SUCCEEDED",
        result={"success": True, "stdout": "too late"},
    )

    assert final.lifecycle_state == "CANCELLED"
    assert list((tmp_path / "results").glob(f"{req.request_id}.rejected-*.json"))
    assert request_path.read_bytes() == terminal_bytes


def test_cancel_ack_zero_generation_rejected_before_terminal_cancelled(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")
    cancelled = store.request_cancel(req.request_id)

    rejected = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="CANCELLED",
        result={"success": False, "error": "cancelled"},
        cleanup={
            "process_residue": [],
            "request_id": req.request_id,
            "correlation_id": req.correlation_id,
            "node_id": req.node_id,
            "claim_id": "claim-1",
            "cancellation_generation": 0.0,
            "cancellation_requested_at": 0.0,
            "cancellation_deadline_at": cancelled.cancellation_deadline_at,
            "cancellation_envelope_digest": "wrong",
        },
    )

    assert rejected.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert rejected.cancellation_acknowledged_at == 0.0
    assert rejected.diagnostics["cancel_ack_rejected"][0]["reason"].startswith(
        "cancel_ack_identity_mismatch"
    )
    assert store.result_for(req.request_id) is None
    assert list((tmp_path / "results").glob(f"{req.request_id}.rejected-*.json"))


def test_cancel_ack_cleanup_proof_without_identity_rejected(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")
    store.request_cancel(req.request_id)

    rejected = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="CANCELLED",
        result={"success": False, "error": "cancelled"},
        cleanup={"process_residue": []},
    )

    assert rejected.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert rejected.cancellation_acknowledged_at == 0.0
    assert rejected.diagnostics["cancel_ack_rejected"][0]["reason"].startswith(
        "cancel_ack_identity_mismatch"
    )
    assert store.result_for(req.request_id) is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("cancellation_generation", None),
        ("cancellation_generation", 0.0),
        ("cancellation_generation", 99.0),
        ("cancellation_generation", 101.0),
        ("cancellation_requested_at", None),
        ("cancellation_deadline_at", None),
        ("cancellation_deadline_at", 0.0),
        ("claim_id", "other-claim"),
        ("request_id", "other-request"),
        ("correlation_id", "other-correlation"),
        ("cancellation_envelope_digest", "wrong"),
    ],
)
def test_cancel_ack_identity_fields_must_match_active_cancellation(
    tmp_path, monkeypatch, field, value
) -> None:
    import substrate.execution.durable_remote_transport as durable

    monkeypatch.setattr(durable, "now_s", lambda: 100.0)
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")
    cancelled = store.request_cancel(req.request_id)
    cleanup = {"process_residue": [], **cancelled.cancellation_identity(claim_id="claim-1")}
    if value is None:
        cleanup.pop(field)
    else:
        cleanup[field] = value

    rejected = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="CANCELLED",
        result={"success": False, "error": "cancelled"},
        cleanup=cleanup,
    )

    assert rejected.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert rejected.cancellation_acknowledged_at == 0.0
    assert rejected.diagnostics["cancel_ack_rejected"]
    assert store.result_for(req.request_id) is None


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
    store.mark_claimed(req.request_id, claim_id="claim-1")
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
        cleanup={"process_residue": []},
    )
    assert first.lifecycle_state == "SUCCEEDED"
    request_path = store._request_path(req.request_id)
    terminal_bytes = request_path.read_bytes()

    same = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="SUCCEEDED",
        result={"success": True, "stdout": "ok"},
        cleanup={"process_residue": []},
    )
    assert same.lifecycle_state == "SUCCEEDED"

    conflict = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="FAILED",
        result={"success": False, "error": "different"},
    )
    assert conflict.lifecycle_state == "SUCCEEDED"
    assert list((tmp_path / "results").glob(f"{req.request_id}.rejected-*.json"))
    assert request_path.read_bytes() == terminal_bytes


def test_remove_request_refuses_terminal_evidence_without_explicit_force(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request(idempotency_key="remove-terminal"))
    store.mark_claimed(req.request_id, claim_id="claim-1")
    store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="SUCCEEDED",
        result={"success": True, "stdout": "ok"},
        cleanup={"process_residue": []},
    )

    with pytest.raises(ValueError, match="terminal durable request"):
        store.remove_request(req.request_id)

    assert store.get_request(req.request_id) is not None
    assert store.result_for(req.request_id) is not None
    store.remove_request(req.request_id, force_terminal=True)
    assert store.get_request(req.request_id) is None
    with pytest.raises(ValueError, match="points to missing canonical request"):
        store.put_request(_request(idempotency_key="remove-terminal"))


def test_remove_request_preserves_recovery_idempotency_tombstone(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request(idempotency_key="remove-recovery"))
    store.mark_claimed(req.request_id, claim_id="claim-1")
    store.mark_claimed(req.request_id, claim_id="claim-2")
    current = store.get_request(req.request_id)
    assert current is not None
    assert current.lifecycle_state == "RECONCILIATION_REQUIRED"

    store.remove_request(req.request_id)

    assert store.get_request(req.request_id) is None
    with pytest.raises(ValueError, match="points to missing canonical request"):
        store.put_request(_request(idempotency_key="remove-recovery"))


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
        cleanup={
            "process_residue": [{"pid": 123, "state": "still_alive"}],
            **store.get_request(req.request_id).cancellation_identity(claim_id="claim-1"),
        },
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


def test_success_without_cleanup_proof_requires_reconciliation(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")

    final = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="SUCCEEDED",
        result={"success": True, "stdout": "ok"},
        cleanup=None,
    )

    assert final.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert final.diagnostics["success_without_cleanup"] == [
        {"state": "cleanup_proof_missing"}
    ]
    assert final.cleanup == {}
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
        cleanup={
            "process_residue": [{"pid": 123, "state": "still_alive"}],
            **store.get_request(req.request_id).cancellation_identity(claim_id="claim-1"),
        },
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
            "cancellation_requested_at": cancelled.cancellation_requested_at - 1,
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
            **cancelled.cancellation_identity(claim_id="claim-1"),
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


def test_terminal_replay_with_cleanup_conflict_preserves_terminal_lifecycle(tmp_path) -> None:
    store = DurableRemoteStore(tmp_path)
    req = store.put_request(_request())
    store.mark_claimed(req.request_id, claim_id="claim-1")
    store.request_cancel(req.request_id)
    current = store.get_request(req.request_id)
    assert current is not None
    first = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="CANCELLED",
        result={"success": False, "error": "cancelled"},
        cleanup={
            "process_residue": [],
            **current.cancellation_identity(claim_id="claim-1"),
        },
    )
    assert first.lifecycle_state == "CANCELLED"

    conflict = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="CANCELLED",
        result={"success": False, "error": "cancelled"},
        cleanup={"process_residue": [{"pid": 999, "state": "still_alive"}]},
    )

    assert conflict.lifecycle_state == "CANCELLED"
    assert conflict.cleanup["process_residue"] == []
    observed = store.get_request(req.request_id)
    assert observed is not None
    assert observed.lifecycle_state == "CANCELLED"
    assert observed.cleanup["process_residue"] == []
    rejected = list((tmp_path / "results").glob(f"{req.request_id}.rejected-*.json"))
    assert rejected
    rejected_payload = json.loads(rejected[0].read_text(encoding="utf-8"))
    assert rejected_payload["rejected_reason"] == "terminal_cancel_cleanup_conflict"
    assert rejected_payload["cleanup"]["process_residue"][0]["state"] == "still_alive"
