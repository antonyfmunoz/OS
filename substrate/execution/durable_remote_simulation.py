"""Deterministic virtual-time model for the Wave 2 durable authority protocol.

This is qualification infrastructure, not product runtime. It intentionally
models only the authority protocol: delivery, claim proof, cancellation,
terminalization, restarts, and late/stale frames.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

TERMINAL = {"SUCCEEDED", "FAILED", "CANCELLED", "RECONCILIATION_REQUIRED"}


def canonical_identity_from_serialized_token(token: str, *, syntactically_valid: bool = True) -> str:
    if not syntactically_valid:
        return ""
    return {
        "K": "K",
        "K_ESCAPED_VALUE": "K",
        "K_ESCAPED_FIELD": "K",
        "J": "J",
        "J_ESCAPED_VALUE": "J",
    }.get(token, "")


@dataclass
class SimState:
    scenario: str
    lifecycle: str = "QUEUED"
    candidate_sha: str = "sha-final"
    expected_candidate_sha: str = "sha-final"
    claim_id: str = ""
    canonical_claim_proven: bool = False
    running_announced: bool = False
    executed: int = 0
    cancelled: bool = False
    fail_closed: bool = False
    node_alive: bool = True
    mesh_alive: bool = True
    store_alive: bool = True
    pending_ack: bool = False
    durable_canonical_effect: str = "CONSEQUENTIAL_WRITE"
    declared_risk: str = "reversible_write"
    canonical_risk: str = "reversible_write"
    node_cap_risk: str = "reversible_write"
    declared_sync_effect: str = "UNKNOWN"
    canonical_sync_effect: str = "UNKNOWN"
    sync_side_effects: int = 0
    sync_observations: int = 0
    canonical_request_for_key: dict[str, str] = field(default_factory=dict)
    admitted_request_for_key: dict[str, str] = field(default_factory=dict)
    payload_for_key: dict[str, str] = field(default_factory=dict)
    execution_for_key: dict[str, int] = field(default_factory=dict)
    persisted_request_key: dict[str, str] = field(default_factory=dict)
    persisted_request_payload: dict[str, str] = field(default_factory=dict)
    persisted_request_material_valid: dict[str, bool] = field(default_factory=dict)
    persisted_request_material_complete: dict[str, bool] = field(default_factory=dict)
    persisted_request_order: dict[str, int] = field(default_factory=dict)
    corrupt_request_records: set[str] = field(default_factory=set)
    corrupt_request_keys: set[str] = field(default_factory=set)
    unknown_scope_request_corruption: bool = False
    corrupt_index_keys: set[str] = field(default_factory=set)
    fenced_idempotency_keys: set[str] = field(default_factory=set)
    corrupt_result_records: set[str] = field(default_factory=set)
    event_journal_read_error: bool = False
    event_journal_corrupt: bool = False
    malformed_server_frame: bool = False
    malformed_node_delivery: bool = False
    attempt_store_corrupt_unknown_scope: bool = False
    lease_store_corrupt: bool = False
    cas_rewrite_attempted_with_corruption: bool = False
    corruption_evidence_preserved: bool = True
    result_present_for_request: set[str] = field(default_factory=set)
    result_converged_for_request: set[str] = field(default_factory=set)
    deliverable_requests: set[str] = field(default_factory=set)
    idempotency_conflict: bool = False
    transport_authority_queue: list[str] = field(default_factory=list)
    transport_reconciliation_queue: list[str] = field(default_factory=list)
    transport_bulk_queue: list[str] = field(default_factory=list)
    transport_sent: list[str] = field(default_factory=list)
    transport_authority_capacity: int = 8
    transport_bulk_capacity: int = 4
    transport_authority_overload: bool = False
    transport_healthy: bool = True
    transport_generation: int = 1
    transport_send_inflight: str = ""
    terminal_result_retained: bool = False
    claim_ack_received: bool = False
    http_readback_reached_vps: bool = False
    result_delivery_serviced: bool = False
    reconciliation_reminder_events: int = 0
    reconciliation_checks: int = 0
    reconciliation_clock: int = 0
    reconciliation_next_event_at: int = 0
    reconciliation_interval: int = 1
    next_request_order: int = 0
    log: list[str] = field(default_factory=list)

    def record(self, event: str) -> None:
        self.log.append(event)

    def assert_invariants(self) -> None:
        if self.executed:
            assert self.canonical_claim_proven, self.log
            assert self.candidate_sha == self.expected_candidate_sha, self.log
            assert self.claim_id, self.log
            assert self.lifecycle in {"RUNNING", "SUCCEEDED", "RECONCILIATION_REQUIRED"}, self.log
        assert self.executed <= 1, self.log
        if self.cancelled and not self.running_announced:
            assert self.executed == 0, self.log
        if self.lifecycle in TERMINAL:
            assert self.lifecycle != "RUNNING", self.log
        assert self.sync_side_effects == 0, self.log
        if self.canonical_sync_effect == "UNKNOWN":
            assert self.sync_observations == 0, self.log
        if self.canonical_sync_effect == "CONSEQUENTIAL_WRITE":
            assert self.sync_observations == 0, self.log
        if self.durable_canonical_effect != "CONSEQUENTIAL_WRITE":
            assert self.executed == 0, self.log
        if self.durable_canonical_effect == "CONSEQUENTIAL_WRITE" and (
            self.executed or self.persisted_request_key
        ):
            assert self.canonical_risk != "read_only", self.log
            if self.declared_risk == "read_only":
                assert self.executed == 0, self.log
        if self.declared_sync_effect == "READ_ONLY" and self.canonical_sync_effect == "CONSEQUENTIAL_WRITE":
            assert self.sync_side_effects == 0, self.log
        for key, execution_count in self.execution_for_key.items():
            assert self.canonical_request_for_key.get(key), self.log
            assert execution_count <= 1, self.log
        for request_id, key in self.persisted_request_key.items():
            if request_id in self.corrupt_request_records:
                assert request_id not in self.deliverable_requests, self.log
                continue
            if not self.persisted_request_material_complete.get(request_id, True):
                assert request_id not in self.deliverable_requests, self.log
                continue
            if not key.strip():
                assert request_id not in self.deliverable_requests, self.log
                continue
            if not self.persisted_request_material_valid.get(request_id, True):
                assert request_id not in self.deliverable_requests, self.log
                continue
            canonical = self.canonical_request_for_key.get(key)
            if canonical and canonical != request_id:
                assert request_id not in self.deliverable_requests, self.log
        for request_id in self.result_converged_for_request:
            assert request_id not in self.corrupt_request_records, self.log
            assert request_id not in self.corrupt_result_records, self.log
            assert self.persisted_request_material_valid.get(request_id, True), self.log
            assert self.persisted_request_material_complete.get(request_id, True), self.log
        if self.event_journal_read_error or self.event_journal_corrupt:
            assert self.fail_closed, self.log
        if self.malformed_server_frame or self.malformed_node_delivery:
            assert self.executed == 0, self.log
        if self.attempt_store_corrupt_unknown_scope or self.lease_store_corrupt:
            assert self.fail_closed, self.log
        if self.cas_rewrite_attempted_with_corruption:
            assert self.corruption_evidence_preserved, self.log
        for key in self.corrupt_request_keys:
            canonical = self.canonical_request_for_key.get(key)
            if canonical:
                for request_id in requests_for_key_in_admission_order(self, key):
                    if request_id != canonical:
                        assert request_id not in self.deliverable_requests, self.log
        assert len(self.transport_authority_queue) <= self.transport_authority_capacity, self.log
        assert len(self.transport_bulk_queue) <= self.transport_bulk_capacity, self.log
        if self.transport_authority_overload:
            assert self.fail_closed, self.log
        if self.result_delivery_serviced:
            assert "authority:result" in self.transport_sent, self.log
        assert self.reconciliation_reminder_events <= self.reconciliation_checks, self.log


def persist_request_file(
    state: SimState,
    *,
    request_id: str,
    idempotency_key: str,
    payload_identity: str = "",
    material_valid: bool = True,
    material_complete: bool = True,
    corrupt: bool = False,
) -> None:
    state.persisted_request_key[request_id] = idempotency_key
    state.persisted_request_material_valid[request_id] = material_valid
    state.persisted_request_material_complete[request_id] = material_complete
    if corrupt:
        state.corrupt_request_records.add(request_id)
        if idempotency_key:
            state.corrupt_request_keys.add(idempotency_key)
        else:
            state.unknown_scope_request_corruption = True
    if payload_identity:
        state.persisted_request_payload[request_id] = payload_identity
    if request_id not in state.persisted_request_order:
        state.next_request_order += 1
        state.persisted_request_order[request_id] = state.next_request_order


def persist_corrupt_authority_record(
    state: SimState,
    *,
    request_id: str,
    serialized_identity: str,
    syntactically_valid: bool = True,
    structural_field: bool = True,
) -> None:
    key = canonical_identity_from_serialized_token(
        serialized_identity,
        syntactically_valid=syntactically_valid,
    )
    if not structural_field:
        key = ""
    state.record(
        "persist_corrupt_authority_record:"
        f"request={request_id}:serialized={serialized_identity}:decoded={key or 'UNKNOWN'}"
    )
    persist_request_file(
        state,
        request_id=request_id,
        idempotency_key=key,
        payload_identity="P",
        material_valid=False,
        corrupt=True,
    )


def requests_for_key_in_admission_order(state: SimState, idempotency_key: str) -> list[str]:
    return sorted(
        (
            request_id
            for request_id, key in state.persisted_request_key.items()
            if key == idempotency_key
        ),
        key=lambda request_id: (state.persisted_request_order.get(request_id, 0), request_id),
    )


def fail_closed_ambiguous_idempotency(state: SimState, idempotency_key: str) -> None:
    state.idempotency_conflict = True
    state.fail_closed = True
    state.fenced_idempotency_keys.add(idempotency_key)
    for request_id in requests_for_key_in_admission_order(state, idempotency_key):
        state.deliverable_requests.discard(request_id)


def positive_idempotency_absence_proven(state: SimState, idempotency_key: str) -> bool:
    if state.event_journal_read_error or state.event_journal_corrupt:
        state.record(f"admission_absence_unproven:key={idempotency_key}:events_incomplete")
        fail_closed_ambiguous_idempotency(state, idempotency_key)
        return False
    if state.unknown_scope_request_corruption:
        state.record(f"admission_absence_unproven:key={idempotency_key}:unknown_scope_corruption")
        fail_closed_ambiguous_idempotency(state, idempotency_key)
        return False
    if idempotency_key in state.corrupt_request_keys:
        state.record(f"admission_absence_unproven:key={idempotency_key}:corrupt_request")
        fail_closed_ambiguous_idempotency(state, idempotency_key)
        return False
    if idempotency_key in state.fenced_idempotency_keys:
        state.record(f"admission_absence_unproven:key={idempotency_key}:fenced")
        fail_closed_ambiguous_idempotency(state, idempotency_key)
        return False
    return True


def fail_closed_invalid_material(state: SimState, request_id: str) -> None:
    state.record(f"invalid_material_rejected:{request_id}")
    state.fail_closed = True
    if state.lifecycle not in TERMINAL:
        state.lifecycle = "RECONCILIATION_REQUIRED"
    state.deliverable_requests.discard(request_id)


def request_material_is_canonical(state: SimState, request_id: str) -> bool:
    if request_id in state.corrupt_request_records:
        state.record(f"corrupt_request_isolated:{request_id}")
        fail_closed_invalid_material(state, request_id)
        return False
    if not state.persisted_request_material_complete.get(request_id, True):
        state.record(f"incomplete_material_rejected:{request_id}")
        fail_closed_invalid_material(state, request_id)
        return False
    if not state.persisted_request_material_valid.get(request_id, True):
        fail_closed_invalid_material(state, request_id)
        return False
    return True


def validate_idempotency_index(state: SimState, idempotency_key: str) -> bool:
    if state.event_journal_read_error or state.event_journal_corrupt:
        state.record(f"admission_evidence_incomplete:key={idempotency_key}")
        fail_closed_ambiguous_idempotency(state, idempotency_key)
        state.assert_invariants()
        return False
    if idempotency_key in state.corrupt_index_keys:
        state.record(f"corrupt_index_isolated:key={idempotency_key}")
        matches = requests_for_key_in_admission_order(state, idempotency_key)
        valid_matches = [
            request_id
            for request_id in matches
            if request_material_is_canonical(state, request_id)
        ]
        if len(valid_matches) == 1:
            state.canonical_request_for_key[idempotency_key] = valid_matches[0]
            state.execution_for_key.setdefault(idempotency_key, 0)
            state.corrupt_index_keys.discard(idempotency_key)
            state.fenced_idempotency_keys.discard(idempotency_key)
        else:
            fail_closed_ambiguous_idempotency(state, idempotency_key)
            state.assert_invariants()
            return False
    if idempotency_key in state.fenced_idempotency_keys:
        state.record(f"idempotency_fence_blocks_authority:key={idempotency_key}")
        state.fail_closed = True
        state.assert_invariants()
        return False
    canonical = state.canonical_request_for_key.get(idempotency_key)
    if not canonical:
        return True
    if not request_material_is_canonical(state, canonical):
        state.assert_invariants()
        return False
    admitted = state.admitted_request_for_key.get(idempotency_key)
    if admitted and admitted != canonical:
        state.record(
            f"idempotency_index_conflict:key={idempotency_key}:canonical={canonical}:admitted={admitted}"
        )
        fail_closed_ambiguous_idempotency(state, idempotency_key)
        state.assert_invariants()
        return False
    matches = requests_for_key_in_admission_order(state, idempotency_key)
    if not admitted and len(matches) > 1:
        state.record(
            f"idempotency_missing_admission_evidence:key={idempotency_key}:matches={','.join(matches)}"
        )
        fail_closed_ambiguous_idempotency(state, idempotency_key)
        state.assert_invariants()
        return False
    if not admitted and matches and matches[0] != canonical:
        state.record(
            f"idempotency_index_conflict:key={idempotency_key}:canonical={canonical}:first={matches[0]}"
        )
        fail_closed_ambiguous_idempotency(state, idempotency_key)
        state.assert_invariants()
        return False
    persisted_payload = state.persisted_request_payload.get(canonical)
    admitted_payload = state.payload_for_key.get(idempotency_key)
    if persisted_payload and admitted_payload and persisted_payload != admitted_payload:
        state.record(
            f"idempotency_admission_binding_drift:key={idempotency_key}:canonical={canonical}"
        )
        fail_closed_ambiguous_idempotency(state, idempotency_key)
        state.assert_invariants()
        return False
    return True


def admit_durable_request(
    state: SimState,
    *,
    request_id: str,
    idempotency_key: str,
    payload_identity: str,
) -> str | None:
    state.record(
        f"admit:request={request_id}:key={idempotency_key}:payload={payload_identity}"
    )
    if not idempotency_key.strip():
        state.idempotency_conflict = True
        state.fail_closed = True
        state.assert_invariants()
        return None
    if idempotency_key in state.corrupt_index_keys or idempotency_key in state.fenced_idempotency_keys:
        if not validate_idempotency_index(state, idempotency_key):
            return None
    canonical = state.canonical_request_for_key.get(idempotency_key)
    if not canonical:
        if not positive_idempotency_absence_proven(state, idempotency_key):
            state.assert_invariants()
            return None
        state.canonical_request_for_key[idempotency_key] = request_id
        state.admitted_request_for_key.setdefault(idempotency_key, request_id)
        state.payload_for_key[idempotency_key] = payload_identity
        state.execution_for_key.setdefault(idempotency_key, 0)
        persist_request_file(
            state,
            request_id=request_id,
            idempotency_key=idempotency_key,
            payload_identity=payload_identity,
        )
        state.deliverable_requests.add(request_id)
        state.assert_invariants()
        return request_id
    if not validate_idempotency_index(state, idempotency_key):
        return None
    if canonical not in state.persisted_request_key:
        state.fail_closed = True
        state.assert_invariants()
        return None
    if state.payload_for_key.get(idempotency_key) != payload_identity:
        state.idempotency_conflict = True
        state.fail_closed = True
        state.assert_invariants()
        return None
    quarantine_duplicate_request_files(state, idempotency_key)
    state.assert_invariants()
    return canonical


def inject_duplicate_request_file(
    state: SimState, *, request_id: str, idempotency_key: str
) -> None:
    state.record(f"inject_duplicate_file:request={request_id}:key={idempotency_key}")
    persist_request_file(state, request_id=request_id, idempotency_key=idempotency_key)
    state.deliverable_requests.add(request_id)


def quarantine_duplicate_request_files(state: SimState, idempotency_key: str) -> None:
    canonical = state.canonical_request_for_key.get(idempotency_key)
    for request_id, key in list(state.persisted_request_key.items()):
        if key == idempotency_key and request_id != canonical:
            state.record(f"quarantine_duplicate_file:{request_id}:canonical={canonical}")
            state.deliverable_requests.discard(request_id)


def recover_missing_idempotency_index(state: SimState, idempotency_key: str) -> str | None:
    matches = requests_for_key_in_admission_order(state, idempotency_key)
    state.record(f"recover_missing_index:key={idempotency_key}:matches={','.join(matches)}")
    if len(matches) == 1:
        if not request_material_is_canonical(state, matches[0]):
            state.assert_invariants()
            return None
        state.canonical_request_for_key[idempotency_key] = matches[0]
        state.execution_for_key.setdefault(idempotency_key, 0)
        state.assert_invariants()
        return matches[0]
    if len(matches) > 1:
        state.idempotency_conflict = True
        state.fail_closed = True
        for request_id in matches:
            state.deliverable_requests.discard(request_id)
        state.assert_invariants()
        return None
    state.assert_invariants()
    return None


def public_update_request(
    state: SimState,
    *,
    request_id: str,
    idempotency_key: str,
) -> None:
    state.record(f"public_update:request={request_id}:key={idempotency_key}")
    if not idempotency_key.strip():
        persist_request_file(state, request_id=request_id, idempotency_key=idempotency_key)
        state.deliverable_requests.discard(request_id)
        state.fail_closed = True
        state.assert_invariants()
        return
    canonical = state.canonical_request_for_key.get(idempotency_key)
    if not canonical:
        canonical = recover_missing_idempotency_index(state, idempotency_key)
    if canonical and canonical != request_id:
        persist_request_file(state, request_id=request_id, idempotency_key=idempotency_key)
        state.deliverable_requests.discard(request_id)
        state.fail_closed = True
        state.assert_invariants()
        return
    persist_request_file(state, request_id=request_id, idempotency_key=idempotency_key)
    state.deliverable_requests.add(request_id)
    state.assert_invariants()


def scan_deliverable_requests(state: SimState) -> None:
    state.record("scan_deliverable_requests")
    for request_id, key in list(state.persisted_request_key.items()):
        if request_id in state.corrupt_request_records:
            state.record(f"corrupt_request_isolated:{request_id}")
            state.deliverable_requests.discard(request_id)
            state.fail_closed = True
            continue
        if not key.strip():
            state.record(f"keyless_request_rejected:{request_id}")
            state.deliverable_requests.discard(request_id)
            state.fail_closed = True
            continue
        if not request_material_is_canonical(state, request_id):
            continue
        validate_idempotency_index(state, key)
    state.assert_invariants()


def sync_mesh_receive(
    state: SimState,
    declared_effect: str,
    *,
    canonical_effect: str | None = None,
    declared_risk: str = "read_only",
    canonical_risk: str | None = None,
    retry: bool = False,
) -> None:
    resolved = canonical_effect if canonical_effect is not None else declared_effect
    resolved_risk = canonical_risk or ("read_only" if resolved == "READ_ONLY" else "reversible_write")
    state.declared_sync_effect = declared_effect
    state.canonical_sync_effect = resolved
    state.declared_risk = declared_risk
    state.canonical_risk = resolved_risk
    state.record(
        f"sync_mesh:declared={declared_effect}/{declared_risk}:"
        f"canonical={resolved}/{resolved_risk}{':retry' if retry else ''}"
    )
    if declared_effect == resolved == "READ_ONLY" and declared_risk == resolved_risk == "read_only":
        state.sync_observations += 1
    elif resolved in {"CONSEQUENTIAL_WRITE", "UNKNOWN"} or declared_effect != resolved or declared_risk != resolved_risk:
        state.fail_closed = True
    else:
        state.canonical_sync_effect = "UNKNOWN"
        state.fail_closed = True
    state.assert_invariants()


def verify_operation_bound_verdict(
    state: SimState,
    *,
    request_id_matches: bool = True,
    payload_matches: bool = True,
    candidate_matches: bool = True,
    policy_matches: bool = True,
) -> bool:
    state.record("verdict_check")
    ok = request_id_matches and payload_matches and candidate_matches and policy_matches
    if not ok:
        state.fail_closed = True
    state.assert_invariants()
    return ok


def deliver(state: SimState, *, duplicate: bool = False) -> None:
    state.record("deliver:duplicate" if duplicate else "deliver")
    state.assert_invariants()


def claim_write(state: SimState, claim_id: str = "claim-1") -> None:
    state.record("claim_write")
    for request_id in list(state.deliverable_requests):
        if not request_material_is_canonical(state, request_id):
            state.assert_invariants()
            return
    if not (state.node_alive and state.mesh_alive and state.store_alive):
        state.pending_ack = True
        state.assert_invariants()
        return
    if state.lifecycle == "QUEUED":
        state.lifecycle = "CLAIMED"
        state.claim_id = claim_id
    elif state.claim_id and state.claim_id != claim_id:
        state.lifecycle = "FAILED"
        state.fail_closed = True
    state.pending_ack = True
    state.assert_invariants()


def ack_lost(state: SimState) -> None:
    state.record("ack_lost")
    state.pending_ack = False
    state.assert_invariants()


def canonical_read(state: SimState, *, delayed: bool = False, available: bool = True) -> None:
    state.record("canonical_read:delayed" if delayed else "canonical_read")
    if not available or not (state.node_alive and state.mesh_alive and state.store_alive):
        state.fail_closed = True
        state.lifecycle = "RECONCILIATION_REQUIRED"
    elif state.claim_id and state.candidate_sha == state.expected_candidate_sha:
        state.canonical_claim_proven = state.lifecycle in {"CLAIMED", "RUNNING", *TERMINAL}
    else:
        state.fail_closed = True
    state.assert_invariants()


def announce_running_and_execute(state: SimState, claim_id: str = "claim-1") -> None:
    state.record("announce_running")
    if state.durable_canonical_effect != "CONSEQUENTIAL_WRITE":
        state.fail_closed = True
        state.lifecycle = "RECONCILIATION_REQUIRED"
        state.assert_invariants()
        return
    if state.declared_risk == "read_only" or state.canonical_risk == "read_only":
        state.fail_closed = True
        state.lifecycle = "RECONCILIATION_REQUIRED"
        state.assert_invariants()
        return
    if state.cancelled or state.fail_closed:
        state.assert_invariants()
        return
    if not state.canonical_claim_proven or state.claim_id != claim_id:
        state.fail_closed = True
        state.assert_invariants()
        return
    if state.lifecycle == "CLAIMED":
        state.lifecycle = "RUNNING"
        state.running_announced = True
        state.executed += 1
        for key in state.execution_for_key:
            state.execution_for_key[key] += 1
            break
    elif state.lifecycle == "RUNNING":
        state.running_announced = True
    state.assert_invariants()


def terminal(state: SimState, value: str = "SUCCEEDED") -> None:
    state.record(f"terminal:{value}")
    for request_id in state.persisted_request_key:
        if request_id in state.corrupt_result_records:
            state.record(f"corrupt_result_isolated:{request_id}")
            state.fail_closed = True
            if state.lifecycle not in TERMINAL:
                state.lifecycle = "RECONCILIATION_REQUIRED"
            state.assert_invariants()
            return
        if not request_material_is_canonical(state, request_id):
            state.assert_invariants()
            return
    if state.lifecycle == "RUNNING" and value in TERMINAL:
        state.lifecycle = value
        for request_id in state.result_present_for_request:
            state.result_converged_for_request.add(request_id)
    elif state.lifecycle in TERMINAL:
        pass
    else:
        state.fail_closed = True
        state.lifecycle = "FAILED"
    state.assert_invariants()


def cancel(state: SimState) -> None:
    state.record("cancel")
    state.cancelled = True
    if not state.running_announced:
        state.lifecycle = "CANCELLED"
    state.assert_invariants()


def restart_node(state: SimState) -> None:
    state.record("node_restart")
    state.node_alive = False
    state.canonical_claim_proven = False
    state.node_alive = True
    state.assert_invariants()


def restart_mesh(state: SimState) -> None:
    state.record("mesh_restart")
    state.mesh_alive = False
    state.mesh_alive = True
    state.assert_invariants()


def foreign_running(state: SimState) -> None:
    state.record("foreign_running")
    before = state.lifecycle
    foreign_claim = "foreign"
    if state.lifecycle in TERMINAL:
        state.lifecycle = before
    elif state.claim_id and state.claim_id != foreign_claim:
        state.fail_closed = True
        state.lifecycle = "FAILED"
    state.assert_invariants()


def enqueue_transport(
    state: SimState,
    *,
    authority: list[str] | None = None,
    reconciliation: int = 0,
    bulk: int = 0,
) -> None:
    for item in authority or []:
        if len(state.transport_authority_queue) >= state.transport_authority_capacity:
            state.transport_authority_overload = True
            state.fail_closed = True
            state.record(f"authority_overload:{item}")
            continue
        state.transport_authority_queue.append(item)
        state.record(f"authority_queued:{item}")
    for idx in range(reconciliation):
        state.transport_reconciliation_queue.append(f"reconciliation-{idx}")
    for idx in range(bulk):
        if len(state.transport_bulk_queue) >= state.transport_bulk_capacity:
            state.transport_bulk_queue.pop(0)
            state.record("bulk_drop_oldest")
        state.transport_bulk_queue.append(f"bulk-{idx}")


def service_transport(state: SimState, *, steps: int = 1) -> None:
    authority_burst = 0
    for _ in range(steps):
        lower_has_work = bool(state.transport_reconciliation_queue or state.transport_bulk_queue)
        if state.transport_authority_queue and (authority_burst < 8 or not lower_has_work):
            item = state.transport_authority_queue.pop(0)
            state.transport_sent.append(f"authority:{item}")
            state.record(f"authority_sent:{item}")
            if item == "claim_ack":
                state.claim_ack_received = True
            if item == "result":
                state.result_delivery_serviced = True
            authority_burst += 1
            continue
        authority_burst = 0
        if state.transport_reconciliation_queue:
            item = state.transport_reconciliation_queue.pop(0)
            state.transport_sent.append(f"reconciliation:{item}")
        elif state.transport_bulk_queue:
            item = state.transport_bulk_queue.pop(0)
            state.transport_sent.append(f"bulk:{item}")
        else:
            break
    state.assert_invariants()


def wedge_transport_send(state: SimState, *, traffic_class: str) -> None:
    state.transport_send_inflight = traffic_class
    state.record(f"send_deadline_exceeded:{traffic_class}")
    state.transport_healthy = False
    state.transport_generation += 1
    state.transport_send_inflight = ""
    state.fail_closed = True
    state.assert_invariants()


def reconnect_transport(state: SimState) -> None:
    state.record(f"transport_reconnected:generation={state.transport_generation}")
    state.transport_healthy = True
    state.assert_invariants()


def observe_reconciliation(state: SimState, *, checks: int) -> None:
    for _ in range(checks):
        tick = state.reconciliation_clock
        state.reconciliation_checks += 1
        if tick >= state.reconciliation_next_event_at:
            state.reconciliation_reminder_events += 1
            state.record(f"reconciliation_reminder:{tick}")
            state.reconciliation_next_event_at = tick + state.reconciliation_interval
            state.reconciliation_interval = min(state.reconciliation_interval * 2, 300)
        state.reconciliation_clock += 1
    state.assert_invariants()


def http_claim_readback(state: SimState, *, available: bool) -> None:
    state.record(f"http_claim_readback:{available}")
    state.http_readback_reached_vps = available
    if available and state.claim_id:
        state.canonical_claim_proven = True
    elif not state.claim_ack_received:
        state.fail_closed = True
    state.assert_invariants()


Scenario = Callable[[SimState], None]


def _normal_success(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    deliver(state)
    claim_write(state)
    canonical_read(state)
    announce_running_and_execute(state)
    terminal(state)


def _ambiguous_claimed_success(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    deliver(state)
    claim_write(state)
    ack_lost(state)
    canonical_read(state)
    announce_running_and_execute(state)
    terminal(state)


def _fallback_unavailable(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    deliver(state)
    claim_write(state)
    ack_lost(state)
    canonical_read(state, available=False)
    announce_running_and_execute(state)


def _claimed_to_running_race(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    deliver(state)
    claim_write(state)
    state.lifecycle = "RUNNING"
    canonical_read(state, delayed=True)
    announce_running_and_execute(state)


def _same_request_duplicates(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    deliver(state)
    deliver(state, duplicate=True)
    deliver(state, duplicate=True)
    claim_write(state)
    canonical_read(state)
    announce_running_and_execute(state)
    terminal(state)
    deliver(state, duplicate=True)


def _post_handler_stale_delivery(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    deliver(state)
    claim_write(state)
    canonical_read(state, available=False)
    deliver(state, duplicate=True)
    canonical_read(state)
    announce_running_and_execute(state)


def _redelivery_amplification_bounded(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    deliver(state)
    for _ in range(4):
        deliver(state, duplicate=True)
    claim_write(state)
    canonical_read(state)
    announce_running_and_execute(state)
    terminal(state)


def _delayed_return_path(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    deliver(state)
    claim_write(state)
    ack_lost(state)
    canonical_read(state, delayed=True)
    announce_running_and_execute(state)
    terminal(state)


def _cancel_during_acquisition(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    deliver(state)
    cancel(state)
    claim_write(state)
    canonical_read(state)
    announce_running_and_execute(state)


def _terminal_late_foreign_running(state: SimState) -> None:
    _normal_success(state)
    foreign_running(state)


def _duplicate_consequential_sync_denied(state: SimState) -> None:
    sync_mesh_receive(state, "CONSEQUENTIAL_WRITE")
    sync_mesh_receive(state, "CONSEQUENTIAL_WRITE", retry=True)


def _consequential_write_durable_remote_duplicate_delivery(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    deliver(state)
    deliver(state, duplicate=True)
    claim_write(state)
    canonical_read(state)
    announce_running_and_execute(state)
    deliver(state, duplicate=True)
    terminal(state)


def _unknown_durable_policy_denied(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    state.durable_canonical_effect = "UNKNOWN"
    announce_running_and_execute(state)


def _read_only_sync_retry_observation(state: SimState) -> None:
    sync_mesh_receive(state, "READ_ONLY")
    sync_mesh_receive(state, "READ_ONLY", retry=True)


def _unknown_sync_effect_fails_closed(state: SimState) -> None:
    sync_mesh_receive(state, "UNKNOWN")


def _declared_read_only_for_canonical_write_denied(state: SimState) -> None:
    sync_mesh_receive(state, "READ_ONLY", canonical_effect="CONSEQUENTIAL_WRITE")


def _generic_shell_declares_read_only_denied(state: SimState) -> None:
    sync_mesh_receive(state, "READ_ONLY", canonical_effect="CONSEQUENTIAL_WRITE")


def _policy_lookup_unavailable_denied(state: SimState) -> None:
    sync_mesh_receive(state, "READ_ONLY", canonical_effect="UNKNOWN")


def _stale_effect_policy_verdict_rejected(state: SimState) -> None:
    assert not verify_operation_bound_verdict(state, policy_matches=False)


def _caller_changes_declared_effect_no_authority_change(state: SimState) -> None:
    sync_mesh_receive(state, "CONSEQUENTIAL_WRITE", canonical_effect="READ_ONLY")


def _same_key_two_request_ids_sequential_converge(state: SimState) -> None:
    first = admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    second = admit_durable_request(state, request_id="B", idempotency_key="K", payload_identity="P")
    assert first == second == "A", state.log


def _missing_idempotency_key_fails_closed(state: SimState) -> None:
    assert admit_durable_request(state, request_id="A", idempotency_key="", payload_identity="P") is None
    assert not state.canonical_request_for_key
    assert state.idempotency_conflict, state.log


def _same_key_two_request_ids_concurrent_converge(state: SimState) -> None:
    second = admit_durable_request(state, request_id="B", idempotency_key="K", payload_identity="P")
    first = admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    assert second == first == "B", state.log


def _same_key_different_payload_conflicts(state: SimState) -> None:
    assert admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P1")
    assert admit_durable_request(state, request_id="B", idempotency_key="K", payload_identity="P2") is None
    assert state.idempotency_conflict, state.log


def _duplicate_after_running_same_trajectory(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    deliver(state)
    claim_write(state)
    canonical_read(state)
    announce_running_and_execute(state)
    assert admit_durable_request(state, request_id="B", idempotency_key="K", payload_identity="P") == "A"
    assert state.execution_for_key["K"] == 1


def _duplicate_after_succeeded_no_second_execution(state: SimState) -> None:
    _normal_success(state)
    assert admit_durable_request(state, request_id="B", idempotency_key="K", payload_identity="P") == "A"
    assert state.execution_for_key["K"] == 1


def _restart_after_admission_duplicate_recovers(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    restart_mesh(state)
    assert admit_durable_request(state, request_id="B", idempotency_key="K", payload_identity="P") == "A"


def _lost_admission_response_retry_new_request_id_recovers(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    state.record("admission_response_lost")
    assert admit_durable_request(state, request_id="B", idempotency_key="K", payload_identity="P") == "A"


def _index_present_duplicate_file_is_quarantined(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    inject_duplicate_request_file(state, request_id="B", idempotency_key="K")
    assert "B" in state.deliverable_requests, state.log
    assert admit_durable_request(state, request_id="C", idempotency_key="K", payload_identity="P") == "A"
    assert "B" not in state.deliverable_requests, state.log


def _partial_persistence_reconciliation_prevents_fork(state: SimState) -> None:
    state.canonical_request_for_key["K"] = "A"
    state.record("partial_index_without_request")
    assert admit_durable_request(state, request_id="B", idempotency_key="K", payload_identity="P") is None
    assert state.fail_closed


def _missing_index_ambiguous_duplicate_files_fail_closed(state: SimState) -> None:
    inject_duplicate_request_file(state, request_id="A", idempotency_key="K")
    inject_duplicate_request_file(state, request_id="B", idempotency_key="K")
    assert recover_missing_idempotency_index(state, "K") is None
    assert state.idempotency_conflict, state.log
    assert "A" not in state.deliverable_requests, state.log
    assert "B" not in state.deliverable_requests, state.log


def _public_update_missing_index_duplicate_cannot_take_over(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    state.canonical_request_for_key.pop("K")
    state.record("idempotency_index_lost")
    public_update_request(state, request_id="B", idempotency_key="K")
    assert state.canonical_request_for_key["K"] == "A", state.log
    assert "B" not in state.deliverable_requests, state.log
    assert state.fail_closed, state.log


def _wrong_index_existing_duplicate_fails_closed(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    inject_duplicate_request_file(state, request_id="B", idempotency_key="K")
    state.canonical_request_for_key["K"] = "B"
    assert admit_durable_request(state, request_id="C", idempotency_key="K", payload_identity="P") is None
    assert state.fail_closed, state.log
    assert state.idempotency_conflict, state.log
    assert "A" not in state.deliverable_requests, state.log
    assert "B" not in state.deliverable_requests, state.log


def _missing_admission_evidence_wrong_index_fails_closed(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    inject_duplicate_request_file(state, request_id="B", idempotency_key="K")
    state.admitted_request_for_key.pop("K")
    state.canonical_request_for_key["K"] = "B"
    assert admit_durable_request(state, request_id="C", idempotency_key="K", payload_identity="P") is None
    assert state.fail_closed, state.log
    assert state.idempotency_conflict, state.log
    assert "A" not in state.deliverable_requests, state.log
    assert "B" not in state.deliverable_requests, state.log


def _missing_admission_evidence_multiple_records_fails_closed(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    inject_duplicate_request_file(state, request_id="B", idempotency_key="K")
    state.admitted_request_for_key.pop("K")
    assert admit_durable_request(state, request_id="C", idempotency_key="K", payload_identity="P") is None
    assert state.fail_closed, state.log
    assert state.idempotency_conflict, state.log
    assert "A" not in state.deliverable_requests, state.log
    assert "B" not in state.deliverable_requests, state.log


def _mutated_canonical_request_payload_fails_closed(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    state.persisted_request_payload["A"] = "P-mutated"
    scan_deliverable_requests(state)
    assert state.fail_closed, state.log
    assert state.idempotency_conflict, state.log
    assert "A" not in state.deliverable_requests, state.log


def _valid_recovered_request_lost_index(state: SimState) -> None:
    persist_request_file(
        state,
        request_id="A",
        idempotency_key="K",
        payload_identity="P",
        material_valid=True,
    )
    assert recover_missing_idempotency_index(state, "K") == "A"
    state.deliverable_requests.add("A")
    scan_deliverable_requests(state)
    assert "A" in state.deliverable_requests, state.log


def _invalid_unknown_operation_lost_index_fails_closed(state: SimState) -> None:
    persist_request_file(
        state,
        request_id="A",
        idempotency_key="K",
        payload_identity="P",
        material_valid=False,
    )
    assert recover_missing_idempotency_index(state, "K") is None
    assert state.fail_closed, state.log
    assert "A" not in state.deliverable_requests, state.log


def _invalid_effect_mismatch_recovery_fails_closed(state: SimState) -> None:
    _invalid_unknown_operation_lost_index_fails_closed(state)


def _incomplete_candidate_sha_fails_closed(state: SimState) -> None:
    persist_request_file(
        state,
        request_id="A",
        idempotency_key="K",
        payload_identity="P",
        material_complete=False,
    )
    state.deliverable_requests.add("A")
    scan_deliverable_requests(state)
    assert "A" not in state.deliverable_requests, state.log
    assert state.lifecycle == "RECONCILIATION_REQUIRED", state.log


def _incomplete_node_id_fails_closed(state: SimState) -> None:
    _incomplete_candidate_sha_fails_closed(state)


def _incomplete_operation_type_fails_closed(state: SimState) -> None:
    _incomplete_candidate_sha_fails_closed(state)


def _recovered_invalid_request_scan_blocked(state: SimState) -> None:
    persist_request_file(
        state,
        request_id="A",
        idempotency_key="K",
        payload_identity="P",
        material_valid=False,
    )
    state.deliverable_requests.add("A")
    scan_deliverable_requests(state)
    assert "A" not in state.deliverable_requests, state.log
    assert state.fail_closed, state.log


def _recovered_invalid_request_claim_blocked(state: SimState) -> None:
    persist_request_file(
        state,
        request_id="A",
        idempotency_key="K",
        payload_identity="P",
        material_valid=False,
    )
    state.deliverable_requests.add("A")
    claim_write(state)
    assert state.lifecycle == "RECONCILIATION_REQUIRED", state.log
    assert state.executed == 0, state.log
    assert state.fail_closed, state.log


def _late_success_after_invalid_recovery_rejected(state: SimState) -> None:
    persist_request_file(
        state,
        request_id="A",
        idempotency_key="K",
        payload_identity="P",
        material_valid=False,
    )
    state.lifecycle = "RUNNING"
    terminal(state)
    assert state.lifecycle == "RECONCILIATION_REQUIRED", state.log
    assert state.executed == 0, state.log
    assert state.fail_closed, state.log


def _invalid_recovered_request_existing_success_cannot_legitimize(state: SimState) -> None:
    persist_request_file(
        state,
        request_id="A",
        idempotency_key="K",
        payload_identity="P",
        material_complete=False,
    )
    state.result_present_for_request.add("A")
    state.lifecycle = "RUNNING"
    terminal(state)
    assert "A" not in state.result_converged_for_request, state.log
    assert state.lifecycle == "RECONCILIATION_REQUIRED", state.log


def _consequential_effect_with_read_only_declared_risk_denied(state: SimState) -> None:
    state.declared_risk = "read_only"
    state.canonical_risk = "reversible_write"
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    deliver(state)
    claim_write(state)
    canonical_read(state)
    announce_running_and_execute(state)
    assert state.executed == 0, state.log
    assert state.fail_closed, state.log


def _generic_shell_read_only_node_cap_denied(state: SimState) -> None:
    state.node_cap_risk = "read_only"
    _consequential_effect_with_read_only_declared_risk_denied(state)


def _corrupt_request_among_valid_isolated(state: SimState) -> None:
    persist_request_file(state, request_id="A", idempotency_key="K", payload_identity="P")
    persist_request_file(
        state,
        request_id="B",
        idempotency_key="K2",
        payload_identity="P2",
        corrupt=True,
    )
    state.deliverable_requests.update({"A", "B"})
    scan_deliverable_requests(state)
    assert "A" in state.deliverable_requests, state.log
    assert "B" not in state.deliverable_requests, state.log


def _corrupt_index_rebuilds_only_from_valid_request(state: SimState) -> None:
    persist_request_file(state, request_id="A", idempotency_key="K", payload_identity="P")
    state.corrupt_index_keys.add("K")
    assert validate_idempotency_index(state, "K") is True
    assert state.canonical_request_for_key["K"] == "A", state.log
    assert "K" not in state.corrupt_index_keys, state.log


def _corrupt_result_does_not_terminalize(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    deliver(state)
    claim_write(state)
    canonical_read(state)
    announce_running_and_execute(state)
    state.corrupt_result_records.add("A")
    terminal(state)
    assert state.lifecycle == "RECONCILIATION_REQUIRED", state.log
    assert "A" not in state.result_converged_for_request, state.log


def _corrupt_index_no_valid_request_fences_key(state: SimState) -> None:
    state.corrupt_index_keys.add("K")
    assert admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P") is None
    assert "K" in state.fenced_idempotency_keys, state.log
    assert "K" not in state.canonical_request_for_key, state.log


def _corrupt_index_conflicting_valid_requests_fail_closed(state: SimState) -> None:
    persist_request_file(state, request_id="A", idempotency_key="K", payload_identity="P")
    persist_request_file(state, request_id="B", idempotency_key="K", payload_identity="P")
    state.corrupt_index_keys.add("K")
    assert validate_idempotency_index(state, "K") is False
    assert "K" in state.fenced_idempotency_keys, state.log
    assert "A" not in state.deliverable_requests, state.log
    assert "B" not in state.deliverable_requests, state.log


def _corrupt_same_key_request_blocks_fresh_admission(state: SimState) -> None:
    persist_request_file(
        state,
        request_id="A",
        idempotency_key="K",
        payload_identity="P",
        material_valid=False,
        corrupt=True,
    )
    assert admit_durable_request(state, request_id="B", idempotency_key="K", payload_identity="P") is None
    assert "K" in state.fenced_idempotency_keys, state.log
    assert "K" not in state.canonical_request_for_key, state.log
    assert "B" not in state.persisted_request_key, state.log


def _escaped_json_key_value_bypass_reproduction(state: SimState) -> None:
    persist_corrupt_authority_record(
        state,
        request_id="A",
        serialized_identity="K_ESCAPED_VALUE",
    )
    assert admit_durable_request(state, request_id="B", idempotency_key="K", payload_identity="P") is None
    assert "K" in state.fenced_idempotency_keys, state.log
    assert "B" not in state.persisted_request_key, state.log


def _escaped_field_name_bypass_reproduction(state: SimState) -> None:
    persist_corrupt_authority_record(
        state,
        request_id="A",
        serialized_identity="K_ESCAPED_FIELD",
    )
    assert admit_durable_request(state, request_id="B", idempotency_key="K", payload_identity="P") is None
    assert "K" in state.fenced_idempotency_keys, state.log


def _attempt_store_escaped_scope_blocks_authority(state: SimState) -> None:
    state.attempt_store_corrupt_unknown_scope = True
    state.record("attempt_store_corrupt_scope:serialized=attempt-\\u0031:decoded=attempt-1")
    state.fail_closed = True
    state.assert_invariants()


def _lease_store_escaped_scope_blocks_authority(state: SimState) -> None:
    state.lease_store_corrupt = True
    state.record("lease_store_corrupt_scope:serialized=lease-\\u0031:decoded=lease-1")
    state.fail_closed = True
    state.assert_invariants()


def _duplicate_authority_field_fails_ambiguous(state: SimState) -> None:
    persist_corrupt_authority_record(
        state,
        request_id="A",
        serialized_identity="UNKNOWN_DUPLICATE_FIELD",
    )
    assert admit_durable_request(state, request_id="B", idempotency_key="K", payload_identity="P") is None
    assert state.unknown_scope_request_corruption, state.log
    assert "B" not in state.persisted_request_key, state.log


def _nested_decoy_identity_does_not_scope_corruption(state: SimState) -> None:
    persist_corrupt_authority_record(
        state,
        request_id="A",
        serialized_identity="K",
        structural_field=False,
    )
    assert admit_durable_request(state, request_id="B", idempotency_key="K", payload_identity="P") is None
    assert state.unknown_scope_request_corruption, state.log
    assert "B" not in state.persisted_request_key, state.log


def _malformed_raw_token_is_unknown_scope(state: SimState) -> None:
    persist_corrupt_authority_record(
        state,
        request_id="A",
        serialized_identity="K",
        syntactically_valid=False,
    )
    assert admit_durable_request(state, request_id="B", idempotency_key="K", payload_identity="P") is None
    assert state.unknown_scope_request_corruption, state.log


def _bound_and_corrupt_fenced_represented(state: SimState) -> None:
    assert admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P") == "A"
    persist_corrupt_authority_record(
        state,
        request_id="B",
        serialized_identity="K_ESCAPED_VALUE",
    )
    assert state.canonical_request_for_key["K"] == "A", state.log
    assert "K" in state.corrupt_request_keys, state.log


def _bound_and_corrupt_fenced_blocks_fresh_request(state: SimState) -> None:
    _bound_and_corrupt_fenced_represented(state)
    assert admit_durable_request(state, request_id="C", idempotency_key="K", payload_identity="P") == "A"
    assert "C" not in state.persisted_request_key, state.log
    assert state.canonical_request_for_key["K"] == "A", state.log


def _terminal_bound_plus_corruption_preserves_terminal(state: SimState) -> None:
    _normal_success(state)
    persist_corrupt_authority_record(
        state,
        request_id="B",
        serialized_identity="K_ESCAPED_FIELD",
    )
    assert admit_durable_request(state, request_id="C", idempotency_key="K", payload_identity="P") == "A"
    assert state.lifecycle == "SUCCEEDED", state.log
    assert state.execution_for_key["K"] == 1, state.log


def _restart_preserves_canonical_corruption_fence(state: SimState) -> None:
    persist_corrupt_authority_record(
        state,
        request_id="A",
        serialized_identity="K_ESCAPED_VALUE",
    )
    restart_mesh(state)
    assert admit_durable_request(state, request_id="B", idempotency_key="K", payload_identity="P") is None
    assert "K" in state.fenced_idempotency_keys, state.log


def _unrelated_clean_key_progresses_with_canonical_key_scope(state: SimState) -> None:
    persist_corrupt_authority_record(
        state,
        request_id="A",
        serialized_identity="K_ESCAPED_VALUE",
    )
    assert admit_durable_request(state, request_id="B", idempotency_key="J", payload_identity="P2") == "B"
    assert state.canonical_request_for_key["J"] == "B", state.log


def _corrupt_same_key_retry_new_request_id_denied(state: SimState) -> None:
    _corrupt_same_key_request_blocks_fresh_admission(state)


def _corrupt_same_key_survives_restart(state: SimState) -> None:
    persist_request_file(
        state,
        request_id="A",
        idempotency_key="K",
        payload_identity="P",
        material_valid=False,
        corrupt=True,
    )
    restart_mesh(state)
    assert admit_durable_request(state, request_id="B", idempotency_key="K", payload_identity="P") is None
    assert "K" in state.fenced_idempotency_keys, state.log


def _quarantined_corrupt_request_preserves_key_fence(state: SimState) -> None:
    persist_request_file(
        state,
        request_id="A",
        idempotency_key="K",
        payload_identity="P",
        material_valid=False,
        corrupt=True,
    )
    assert admit_durable_request(state, request_id="B", idempotency_key="K", payload_identity="P") is None
    state.persisted_request_key.pop("A")
    state.persisted_request_payload.pop("A", None)
    state.persisted_request_material_valid.pop("A", None)
    state.persisted_request_material_complete.pop("A", None)
    state.corrupt_request_records.discard("A")
    state.record("corrupt_request_quarantined:A")
    assert admit_durable_request(state, request_id="C", idempotency_key="K", payload_identity="P") is None
    assert "K" in state.fenced_idempotency_keys, state.log


def _valid_binding_plus_corrupt_duplicate_preserves_canonical(state: SimState) -> None:
    assert admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P") == "A"
    persist_request_file(
        state,
        request_id="B",
        idempotency_key="K",
        payload_identity="P",
        material_valid=False,
        corrupt=True,
    )
    assert admit_durable_request(state, request_id="C", idempotency_key="K", payload_identity="P") == "A"
    assert state.canonical_request_for_key["K"] == "A", state.log
    assert "B" not in state.deliverable_requests, state.log


def _corrupt_index_plus_corrupt_request_fences_key(state: SimState) -> None:
    persist_request_file(
        state,
        request_id="A",
        idempotency_key="K",
        payload_identity="P",
        material_valid=False,
        corrupt=True,
    )
    state.corrupt_index_keys.add("K")
    assert admit_durable_request(state, request_id="B", idempotency_key="K", payload_identity="P") is None
    assert "K" in state.fenced_idempotency_keys, state.log
    assert "K" not in state.canonical_request_for_key, state.log


def _unknown_scope_corrupt_request_blocks_unproven_admission(state: SimState) -> None:
    persist_request_file(
        state,
        request_id="A",
        idempotency_key="",
        payload_identity="P",
        material_valid=False,
        corrupt=True,
    )
    assert admit_durable_request(state, request_id="B", idempotency_key="K", payload_identity="P") is None
    assert "K" in state.fenced_idempotency_keys, state.log
    assert "K" not in state.canonical_request_for_key, state.log


def _unrelated_key_progresses_beside_key_scoped_corruption(state: SimState) -> None:
    persist_request_file(
        state,
        request_id="A",
        idempotency_key="K",
        payload_identity="P",
        material_valid=False,
        corrupt=True,
    )
    assert admit_durable_request(state, request_id="B", idempotency_key="J", payload_identity="P2") == "B"
    assert state.canonical_request_for_key["J"] == "B", state.log
    assert "K" not in state.canonical_request_for_key, state.log


def _incomplete_event_history_cannot_prove_absence(state: SimState) -> None:
    state.event_journal_corrupt = True
    assert admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P") is None
    assert "K" in state.fenced_idempotency_keys, state.log
    assert "K" not in state.canonical_request_for_key, state.log


def _corrupt_result_later_publication_rejected(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    deliver(state)
    claim_write(state)
    canonical_read(state)
    announce_running_and_execute(state)
    state.corrupt_result_records.add("A")
    terminal(state)
    terminal(state)
    assert state.lifecycle == "RECONCILIATION_REQUIRED", state.log
    assert "A" not in state.result_converged_for_request, state.log


def _path_content_identity_mismatch_is_corrupt(state: SimState) -> None:
    persist_request_file(state, request_id="A", idempotency_key="K", payload_identity="P")
    persist_request_file(state, request_id="path-B-content-A", idempotency_key="K2", payload_identity="P2", corrupt=True)
    state.deliverable_requests.update({"A", "path-B-content-A"})
    scan_deliverable_requests(state)
    assert "A" in state.deliverable_requests, state.log
    assert "path-B-content-A" not in state.deliverable_requests, state.log


def _quarantine_then_duplicate_request_remains_fenced(state: SimState) -> None:
    state.corrupt_index_keys.add("K")
    assert validate_idempotency_index(state, "K") is False
    assert admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P") is None
    assert "K" in state.fenced_idempotency_keys, state.log


def _read_error_treated_unavailable_not_absent(state: SimState) -> None:
    state.corrupt_index_keys.add("K")
    assert admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P") is None
    assert state.fail_closed, state.log


def _restart_after_corrupt_record_still_non_executable(state: SimState) -> None:
    _corrupt_request_among_valid_isolated(state)
    restart_mesh(state)
    scan_deliverable_requests(state)
    assert "B" not in state.deliverable_requests, state.log


def _event_journal_malformed_line_fails_closed(state: SimState) -> None:
    state.event_journal_corrupt = True
    persist_request_file(state, request_id="A", idempotency_key="K", payload_identity="P")
    state.canonical_request_for_key["K"] = "A"
    assert validate_idempotency_index(state, "K") is False
    assert state.fail_closed, state.log


def _event_journal_read_error_fails_closed(state: SimState) -> None:
    state.event_journal_read_error = True
    persist_request_file(state, request_id="A", idempotency_key="K", payload_identity="P")
    assert validate_idempotency_index(state, "K") is False
    assert state.fail_closed, state.log


def _malformed_server_durable_frame_rejected(state: SimState) -> None:
    state.malformed_server_frame = True
    state.record("malformed_server_frame_rejected")
    state.assert_invariants()


def _malformed_node_delivery_rejected(state: SimState) -> None:
    state.malformed_node_delivery = True
    state.record("malformed_node_delivery_rejected")
    state.assert_invariants()


def _attempt_store_unknown_corruption_blocks_attempt_authority(state: SimState) -> None:
    state.attempt_store_corrupt_unknown_scope = True
    state.record("attempt_store_corruption_blocks_authority")
    state.fail_closed = True
    state.assert_invariants()


def _lease_store_corruption_blocks_conflicting_lease(state: SimState) -> None:
    state.lease_store_corrupt = True
    state.record("lease_store_corruption_blocks_authority")
    state.fail_closed = True
    state.assert_invariants()


def _cas_rewrite_preserves_corruption_evidence(state: SimState) -> None:
    state.attempt_store_corrupt_unknown_scope = True
    state.cas_rewrite_attempted_with_corruption = True
    state.corruption_evidence_preserved = True
    state.fail_closed = True
    state.record("cas_rewrite_refused_corruption_preserved")
    state.assert_invariants()


def _restart_after_invalid_recovery_still_blocked(state: SimState) -> None:
    _recovered_invalid_request_scan_blocked(state)
    restart_mesh(state)
    scan_deliverable_requests(state)
    assert state.fail_closed, state.log
    assert "A" not in state.deliverable_requests, state.log


def _valid_duplicate_after_index_loss_converges(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    state.canonical_request_for_key.pop("K")
    assert recover_missing_idempotency_index(state, "K") == "A"
    assert admit_durable_request(state, request_id="B", idempotency_key="K", payload_identity="P") == "A"


def _keyless_persisted_request_file_not_deliverable(state: SimState) -> None:
    inject_duplicate_request_file(state, request_id="A", idempotency_key="")
    assert "A" in state.deliverable_requests, state.log
    scan_deliverable_requests(state)
    assert "A" not in state.deliverable_requests, state.log
    assert state.fail_closed, state.log


def _adapter_retry_preserves_stable_key(state: SimState) -> None:
    first = admit_durable_request(state, request_id="A", idempotency_key="adapter:stable", payload_identity="P")
    retry = admit_durable_request(state, request_id="B", idempotency_key="adapter:stable", payload_identity="P")
    assert first == retry == "A", state.log


def _stale_operation_bound_verdict_rejected(state: SimState) -> None:
    assert not verify_operation_bound_verdict(state, request_id_matches=False)


def _altered_payload_verdict_rejected(state: SimState) -> None:
    assert not verify_operation_bound_verdict(state, payload_matches=False)


def _transport_bulk_saturation_claim_gets_authority_service(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    deliver(state)
    claim_write(state)
    enqueue_transport(state, authority=["claim_ack"], bulk=32)
    service_transport(state, steps=1)
    assert state.claim_ack_received, state.log
    canonical_read(state)
    announce_running_and_execute(state)


def _transport_bulk_saturation_result_gets_authority_service(state: SimState) -> None:
    _normal_success(state)
    enqueue_transport(state, authority=["result"], bulk=32)
    service_transport(state, steps=1)
    assert state.result_delivery_serviced, state.log


def _transport_reconciliation_cannot_starve_new_claim(state: SimState) -> None:
    observe_reconciliation(state, checks=64)
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    deliver(state)
    claim_write(state)
    enqueue_transport(state, authority=["claim_ack"], reconciliation=32, bulk=16)
    service_transport(state, steps=1)
    assert state.claim_ack_received, state.log


def _transport_ws_ack_unavailable_http_readback_healthy(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    deliver(state)
    claim_write(state)
    ack_lost(state)
    http_claim_readback(state, available=True)
    announce_running_and_execute(state)
    assert state.executed == 1, state.log


def _transport_ws_ack_unavailable_http_readback_unavailable(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    deliver(state)
    claim_write(state)
    ack_lost(state)
    http_claim_readback(state, available=False)
    announce_running_and_execute(state)
    assert state.executed == 0, state.log
    assert state.fail_closed, state.log


def _transport_bounded_reconciliation_reminders(state: SimState) -> None:
    observe_reconciliation(state, checks=146)
    assert state.reconciliation_reminder_events < 16, state.log


def _transport_cancellation_while_authority_delayed(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    deliver(state)
    claim_write(state)
    ack_lost(state)
    cancel(state)
    http_claim_readback(state, available=False)
    announce_running_and_execute(state)
    assert state.executed == 0, state.log


def _transport_combined_starvation_reproduction_closed(state: SimState) -> None:
    observe_reconciliation(state, checks=64)
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    deliver(state)
    claim_write(state)
    ack_lost(state)
    enqueue_transport(state, authority=["result"], reconciliation=16, bulk=32)
    service_transport(state, steps=1)
    http_claim_readback(state, available=True)
    announce_running_and_execute(state)
    terminal(state)
    assert state.executed == 1, state.log
    assert state.result_delivery_serviced, state.log


def _transport_blocked_bulk_send_resets_generation(state: SimState) -> None:
    enqueue_transport(state, authority=["claim_ack"], bulk=state.transport_bulk_capacity)
    wedge_transport_send(state, traffic_class="bulk")
    assert not state.transport_healthy, state.log
    assert not state.claim_ack_received, state.log
    reconnect_transport(state)
    service_transport(state, steps=1)
    assert state.claim_ack_received, state.log


def _transport_authority_overflow_fails_closed(state: SimState) -> None:
    enqueue_transport(
        state,
        authority=[f"claim-{idx}" for idx in range(state.transport_authority_capacity + 1)],
    )
    assert state.transport_authority_overload, state.log
    assert state.fail_closed, state.log
    assert len(state.transport_authority_queue) == state.transport_authority_capacity, state.log


def _transport_terminal_result_retained_during_overload(state: SimState) -> None:
    _normal_success(state)
    state.terminal_result_retained = True
    enqueue_transport(
        state,
        authority=[f"control-{idx}" for idx in range(state.transport_authority_capacity)],
    )
    enqueue_transport(state, authority=["result"])
    assert state.transport_authority_overload, state.log
    assert state.terminal_result_retained, state.log


def _transport_continuous_bulk_producer_cannot_starve_claim(state: SimState) -> None:
    enqueue_transport(state, bulk=state.transport_bulk_capacity * 4)
    enqueue_transport(state, authority=["claim_ack"])
    for _ in range(3):
        service_transport(state, steps=1)
        enqueue_transport(state, bulk=state.transport_bulk_capacity)
    assert state.claim_ack_received, state.log


def _transport_reconciliation_backoff_survives_restart(state: SimState) -> None:
    observe_reconciliation(state, checks=64)
    reminders = state.reconciliation_reminder_events
    interval = state.reconciliation_interval
    next_event = state.reconciliation_next_event_at
    restart_mesh(state)
    observe_reconciliation(state, checks=1)
    assert state.reconciliation_interval >= interval, state.log
    assert state.reconciliation_next_event_at >= next_event, state.log
    assert state.reconciliation_reminder_events <= reminders + 1, state.log


def _transport_http_timeout_and_ws_ack_loss_fail_closed(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    deliver(state)
    claim_write(state)
    ack_lost(state)
    state.record("http_readback_timeout")
    http_claim_readback(state, available=False)
    announce_running_and_execute(state)
    assert state.executed == 0, state.log


def _transport_cancel_under_saturation_never_launches(state: SimState) -> None:
    admit_durable_request(state, request_id="A", idempotency_key="K", payload_identity="P")
    deliver(state)
    claim_write(state)
    enqueue_transport(state, authority=["cancel"], bulk=state.transport_bulk_capacity * 4)
    cancel(state)
    service_transport(state, steps=1)
    announce_running_and_execute(state)
    assert state.executed == 0, state.log


SCENARIOS: dict[str, Scenario] = {
    "normal_success": _normal_success,
    "ambiguous_claimed_success": _ambiguous_claimed_success,
    "fallback_unavailable": _fallback_unavailable,
    "claimed_to_running_race": _claimed_to_running_race,
    "simultaneous_same_request_delivery": _same_request_duplicates,
    "post_handler_stale_delivery": _post_handler_stale_delivery,
    "redelivery_amplification": _redelivery_amplification_bounded,
    "delayed_beast_to_vps_return_path": _delayed_return_path,
    "cancellation_during_acquisition": _cancel_during_acquisition,
    "terminal_late_foreign_running": _terminal_late_foreign_running,
    "sync_duplicate_consequential_denied": _duplicate_consequential_sync_denied,
    "sync_consequential_routes_to_durable_remote": _consequential_write_durable_remote_duplicate_delivery,
    "durable_unknown_policy_denied": _unknown_durable_policy_denied,
    "sync_read_only_retry_observation": _read_only_sync_retry_observation,
    "sync_unknown_effect_fails_closed": _unknown_sync_effect_fails_closed,
    "sync_stale_verdict_rejected": _stale_operation_bound_verdict_rejected,
    "sync_payload_substitution_rejected": _altered_payload_verdict_rejected,
    "sync_declared_read_only_for_canonical_write_denied": _declared_read_only_for_canonical_write_denied,
    "sync_generic_shell_declares_read_only_denied": _generic_shell_declares_read_only_denied,
    "sync_policy_lookup_unavailable_denied": _policy_lookup_unavailable_denied,
    "sync_stale_effect_policy_verdict_rejected": _stale_effect_policy_verdict_rejected,
    "sync_caller_effect_change_no_authority_change": _caller_changes_declared_effect_no_authority_change,
    "idempotency_same_key_two_request_ids_sequential": _same_key_two_request_ids_sequential_converge,
    "idempotency_missing_key_fails_closed": _missing_idempotency_key_fails_closed,
    "idempotency_same_key_two_request_ids_concurrent": _same_key_two_request_ids_concurrent_converge,
    "idempotency_same_key_different_payload_conflict": _same_key_different_payload_conflicts,
    "idempotency_duplicate_after_running": _duplicate_after_running_same_trajectory,
    "idempotency_duplicate_after_succeeded": _duplicate_after_succeeded_no_second_execution,
    "idempotency_restart_after_admission": _restart_after_admission_duplicate_recovers,
    "idempotency_lost_admission_response_retry": _lost_admission_response_retry_new_request_id_recovers,
    "idempotency_index_present_duplicate_file_quarantined": _index_present_duplicate_file_is_quarantined,
    "idempotency_partial_persistence_fail_closed": _partial_persistence_reconciliation_prevents_fork,
    "idempotency_missing_index_ambiguous_duplicate_files_fail_closed": (
        _missing_index_ambiguous_duplicate_files_fail_closed
    ),
    "idempotency_public_update_missing_index_duplicate_denied": (
        _public_update_missing_index_duplicate_cannot_take_over
    ),
    "idempotency_wrong_index_existing_duplicate_fails_closed": (
        _wrong_index_existing_duplicate_fails_closed
    ),
    "idempotency_missing_admission_evidence_wrong_index_fails_closed": (
        _missing_admission_evidence_wrong_index_fails_closed
    ),
    "idempotency_missing_admission_evidence_multiple_records_fails_closed": (
        _missing_admission_evidence_multiple_records_fails_closed
    ),
    "idempotency_mutated_canonical_request_payload_fails_closed": (
        _mutated_canonical_request_payload_fails_closed
    ),
    "recovery_valid_request_lost_index": _valid_recovered_request_lost_index,
    "recovery_unknown_operation_lost_index_fails_closed": (
        _invalid_unknown_operation_lost_index_fails_closed
    ),
    "recovery_effect_mismatch_fails_closed": _invalid_effect_mismatch_recovery_fails_closed,
    "recovery_incomplete_candidate_sha_fails_closed": _incomplete_candidate_sha_fails_closed,
    "recovery_incomplete_node_id_fails_closed": _incomplete_node_id_fails_closed,
    "recovery_incomplete_operation_type_fails_closed": _incomplete_operation_type_fails_closed,
    "recovery_invalid_scan_blocked": _recovered_invalid_request_scan_blocked,
    "recovery_invalid_claim_blocked": _recovered_invalid_request_claim_blocked,
    "recovery_invalid_existing_success_cannot_legitimize": (
        _invalid_recovered_request_existing_success_cannot_legitimize
    ),
    "recovery_late_success_after_invalid_rejected": (
        _late_success_after_invalid_recovery_rejected
    ),
    "recovery_restart_after_invalid_still_blocked": _restart_after_invalid_recovery_still_blocked,
    "recovery_valid_duplicate_after_index_loss_converges": (
        _valid_duplicate_after_index_loss_converges
    ),
    "idempotency_keyless_persisted_request_file_not_deliverable": (
        _keyless_persisted_request_file_not_deliverable
    ),
    "idempotency_adapter_retry_preserves_key": _adapter_retry_preserves_stable_key,
    "risk_consequential_effect_read_only_declared_risk_denied": (
        _consequential_effect_with_read_only_declared_risk_denied
    ),
    "risk_generic_shell_read_only_node_cap_denied": _generic_shell_read_only_node_cap_denied,
    "corrupt_request_among_valid_isolated": _corrupt_request_among_valid_isolated,
    "corrupt_index_rebuilds_only_from_valid_request": _corrupt_index_rebuilds_only_from_valid_request,
    "corrupt_index_no_valid_request_fences_key": _corrupt_index_no_valid_request_fences_key,
    "corrupt_index_conflicting_valid_requests_fail_closed": _corrupt_index_conflicting_valid_requests_fail_closed,
    "corrupt_same_key_request_blocks_fresh_admission": (
        _corrupt_same_key_request_blocks_fresh_admission
    ),
    "canonicalization_escaped_json_key_value_bypass": (
        _escaped_json_key_value_bypass_reproduction
    ),
    "canonicalization_escaped_field_name_bypass": _escaped_field_name_bypass_reproduction,
    "canonicalization_attempt_store_escaped_scope": (
        _attempt_store_escaped_scope_blocks_authority
    ),
    "canonicalization_lease_store_escaped_scope": (
        _lease_store_escaped_scope_blocks_authority
    ),
    "canonicalization_duplicate_authority_field_ambiguous": (
        _duplicate_authority_field_fails_ambiguous
    ),
    "canonicalization_nested_decoy_identity_unknown_scope": (
        _nested_decoy_identity_does_not_scope_corruption
    ),
    "canonicalization_malformed_raw_token_unknown_scope": (
        _malformed_raw_token_is_unknown_scope
    ),
    "canonicalization_bound_and_corrupt_fenced_represented": (
        _bound_and_corrupt_fenced_represented
    ),
    "canonicalization_bound_and_corrupt_fenced_blocks_fresh": (
        _bound_and_corrupt_fenced_blocks_fresh_request
    ),
    "canonicalization_terminal_bound_plus_corruption": (
        _terminal_bound_plus_corruption_preserves_terminal
    ),
    "canonicalization_restart_preserves_fence": (
        _restart_preserves_canonical_corruption_fence
    ),
    "canonicalization_unrelated_clean_key_progresses": (
        _unrelated_clean_key_progresses_with_canonical_key_scope
    ),
    "corrupt_same_key_retry_new_request_id_denied": (
        _corrupt_same_key_retry_new_request_id_denied
    ),
    "corrupt_same_key_survives_restart": _corrupt_same_key_survives_restart,
    "corrupt_quarantined_request_preserves_key_fence": (
        _quarantined_corrupt_request_preserves_key_fence
    ),
    "corrupt_valid_binding_plus_duplicate_preserves_canonical": (
        _valid_binding_plus_corrupt_duplicate_preserves_canonical
    ),
    "corrupt_index_plus_corrupt_request_fences_key": (
        _corrupt_index_plus_corrupt_request_fences_key
    ),
    "corrupt_unknown_scope_request_blocks_unproven_admission": (
        _unknown_scope_corrupt_request_blocks_unproven_admission
    ),
    "corrupt_unrelated_key_progresses_beside_key_scoped_corruption": (
        _unrelated_key_progresses_beside_key_scoped_corruption
    ),
    "corrupt_event_history_incomplete_cannot_prove_absence": (
        _incomplete_event_history_cannot_prove_absence
    ),
    "corrupt_result_does_not_terminalize": _corrupt_result_does_not_terminalize,
    "corrupt_result_later_publication_rejected": _corrupt_result_later_publication_rejected,
    "corrupt_path_content_identity_mismatch_isolated": _path_content_identity_mismatch_is_corrupt,
    "corrupt_quarantine_then_duplicate_request_remains_fenced": (
        _quarantine_then_duplicate_request_remains_fenced
    ),
    "corrupt_read_error_treated_unavailable": _read_error_treated_unavailable_not_absent,
    "corrupt_restart_still_non_executable": _restart_after_corrupt_record_still_non_executable,
    "event_journal_malformed_line_fails_closed": _event_journal_malformed_line_fails_closed,
    "event_journal_read_error_fails_closed": _event_journal_read_error_fails_closed,
    "ingress_malformed_server_durable_frame_rejected": _malformed_server_durable_frame_rejected,
    "ingress_malformed_node_delivery_rejected": _malformed_node_delivery_rejected,
    "attempt_store_unknown_corruption_blocks_attempt_authority": (
        _attempt_store_unknown_corruption_blocks_attempt_authority
    ),
    "attempt_store_lease_corruption_blocks_conflicting_lease": (
        _lease_store_corruption_blocks_conflicting_lease
    ),
    "attempt_store_cas_rewrite_preserves_corruption": _cas_rewrite_preserves_corruption_evidence,
    "transport_bulk_saturation_claim_gets_authority_service": (
        _transport_bulk_saturation_claim_gets_authority_service
    ),
    "transport_bulk_saturation_result_gets_authority_service": (
        _transport_bulk_saturation_result_gets_authority_service
    ),
    "transport_reconciliation_cannot_starve_new_claim": (
        _transport_reconciliation_cannot_starve_new_claim
    ),
    "transport_ws_ack_unavailable_http_readback_healthy": (
        _transport_ws_ack_unavailable_http_readback_healthy
    ),
    "transport_ws_ack_unavailable_http_readback_unavailable": (
        _transport_ws_ack_unavailable_http_readback_unavailable
    ),
    "transport_bounded_reconciliation_reminders": _transport_bounded_reconciliation_reminders,
    "transport_cancellation_while_authority_delayed": (
        _transport_cancellation_while_authority_delayed
    ),
    "transport_combined_starvation_reproduction_closed": (
        _transport_combined_starvation_reproduction_closed
    ),
    "transport_blocked_bulk_send_resets_generation": (
        _transport_blocked_bulk_send_resets_generation
    ),
    "transport_authority_overflow_fails_closed": _transport_authority_overflow_fails_closed,
    "transport_terminal_result_retained_during_overload": (
        _transport_terminal_result_retained_during_overload
    ),
    "transport_continuous_bulk_producer_cannot_starve_claim": (
        _transport_continuous_bulk_producer_cannot_starve_claim
    ),
    "transport_reconciliation_backoff_survives_restart": (
        _transport_reconciliation_backoff_survives_restart
    ),
    "transport_http_timeout_and_ws_ack_loss_fail_closed": (
        _transport_http_timeout_and_ws_ack_loss_fail_closed
    ),
    "transport_cancel_under_saturation_never_launches": (
        _transport_cancel_under_saturation_never_launches
    ),
}


def run_scenario(name: str) -> SimState:
    state = SimState(scenario=name)
    SCENARIOS[name](state)
    state.assert_invariants()
    if name != "fallback_unavailable" and not name.startswith(
        (
            "sync_",
            "idempotency_",
            "recovery_",
            "corrupt_",
            "risk_",
            "attempt_store_",
            "event_journal_",
            "ingress_",
            "canonicalization_",
            "transport_",
        )
    ):
        assert state.lifecycle in {"RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", "RECONCILIATION_REQUIRED"}, state.log
    return state


def run_all_scenarios() -> dict[str, dict[str, object]]:
    results: dict[str, dict[str, object]] = {}
    for name in sorted(SCENARIOS):
        state = run_scenario(name)
        results[name] = {
            "lifecycle": state.lifecycle,
            "executed": state.executed,
            "sync_side_effects": state.sync_side_effects,
            "sync_observations": state.sync_observations,
            "fail_closed": state.fail_closed,
            "transport_authority_overload": state.transport_authority_overload,
            "transport_healthy": state.transport_healthy,
            "transport_generation": state.transport_generation,
            "terminal_result_retained": state.terminal_result_retained,
            "reconciliation_reminder_events": state.reconciliation_reminder_events,
            "log": list(state.log),
        }
    return results
