"""Deterministic virtual-time model for the Wave 2 durable authority protocol.

This is qualification infrastructure, not product runtime. It intentionally
models only the authority protocol: delivery, claim proof, cancellation,
terminalization, restarts, and late/stale frames.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

TERMINAL = {"SUCCEEDED", "FAILED", "CANCELLED", "RECONCILIATION_REQUIRED"}


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
    declared_sync_effect: str = "UNKNOWN"
    canonical_sync_effect: str = "UNKNOWN"
    sync_side_effects: int = 0
    sync_observations: int = 0
    log: list[str] = field(default_factory=list)

    def record(self, event: str) -> None:
        self.log.append(event)

    def assert_invariants(self) -> None:
        if self.executed:
            assert self.canonical_claim_proven, self.log
            assert self.candidate_sha == self.expected_candidate_sha, self.log
            assert self.claim_id, self.log
            assert self.lifecycle in {"RUNNING", "SUCCEEDED"}, self.log
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


def sync_mesh_receive(
    state: SimState,
    declared_effect: str,
    *,
    canonical_effect: str | None = None,
    retry: bool = False,
) -> None:
    resolved = canonical_effect if canonical_effect is not None else declared_effect
    state.declared_sync_effect = declared_effect
    state.canonical_sync_effect = resolved
    state.record(f"sync_mesh:declared={declared_effect}:canonical={resolved}{':retry' if retry else ''}")
    if declared_effect == resolved == "READ_ONLY":
        state.sync_observations += 1
    elif resolved in {"CONSEQUENTIAL_WRITE", "UNKNOWN"} or declared_effect != resolved:
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
    elif state.lifecycle == "RUNNING":
        state.running_announced = True
    state.assert_invariants()


def terminal(state: SimState, value: str = "SUCCEEDED") -> None:
    state.record(f"terminal:{value}")
    if state.lifecycle == "RUNNING" and value in TERMINAL:
        state.lifecycle = value
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


Scenario = Callable[[SimState], None]


def _normal_success(state: SimState) -> None:
    deliver(state)
    claim_write(state)
    canonical_read(state)
    announce_running_and_execute(state)
    terminal(state)


def _ambiguous_claimed_success(state: SimState) -> None:
    deliver(state)
    claim_write(state)
    ack_lost(state)
    canonical_read(state)
    announce_running_and_execute(state)
    terminal(state)


def _fallback_unavailable(state: SimState) -> None:
    deliver(state)
    claim_write(state)
    ack_lost(state)
    canonical_read(state, available=False)
    announce_running_and_execute(state)


def _claimed_to_running_race(state: SimState) -> None:
    deliver(state)
    claim_write(state)
    state.lifecycle = "RUNNING"
    canonical_read(state, delayed=True)
    announce_running_and_execute(state)


def _same_request_duplicates(state: SimState) -> None:
    deliver(state)
    deliver(state, duplicate=True)
    deliver(state, duplicate=True)
    claim_write(state)
    canonical_read(state)
    announce_running_and_execute(state)
    terminal(state)
    deliver(state, duplicate=True)


def _post_handler_stale_delivery(state: SimState) -> None:
    deliver(state)
    claim_write(state)
    canonical_read(state, available=False)
    deliver(state, duplicate=True)
    canonical_read(state)
    announce_running_and_execute(state)


def _redelivery_amplification_bounded(state: SimState) -> None:
    deliver(state)
    for _ in range(4):
        deliver(state, duplicate=True)
    claim_write(state)
    canonical_read(state)
    announce_running_and_execute(state)
    terminal(state)


def _delayed_return_path(state: SimState) -> None:
    deliver(state)
    claim_write(state)
    ack_lost(state)
    canonical_read(state, delayed=True)
    announce_running_and_execute(state)
    terminal(state)


def _cancel_during_acquisition(state: SimState) -> None:
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
    deliver(state)
    deliver(state, duplicate=True)
    claim_write(state)
    canonical_read(state)
    announce_running_and_execute(state)
    deliver(state, duplicate=True)
    terminal(state)


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


def _stale_operation_bound_verdict_rejected(state: SimState) -> None:
    assert not verify_operation_bound_verdict(state, request_id_matches=False)


def _altered_payload_verdict_rejected(state: SimState) -> None:
    assert not verify_operation_bound_verdict(state, payload_matches=False)


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
    "sync_read_only_retry_observation": _read_only_sync_retry_observation,
    "sync_unknown_effect_fails_closed": _unknown_sync_effect_fails_closed,
    "sync_stale_verdict_rejected": _stale_operation_bound_verdict_rejected,
    "sync_payload_substitution_rejected": _altered_payload_verdict_rejected,
    "sync_declared_read_only_for_canonical_write_denied": _declared_read_only_for_canonical_write_denied,
    "sync_generic_shell_declares_read_only_denied": _generic_shell_declares_read_only_denied,
    "sync_policy_lookup_unavailable_denied": _policy_lookup_unavailable_denied,
    "sync_stale_effect_policy_verdict_rejected": _stale_effect_policy_verdict_rejected,
    "sync_caller_effect_change_no_authority_change": _caller_changes_declared_effect_no_authority_change,
}


def run_scenario(name: str) -> SimState:
    state = SimState(scenario=name)
    SCENARIOS[name](state)
    state.assert_invariants()
    if name != "fallback_unavailable" and not name.startswith("sync_"):
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
            "log": list(state.log),
        }
    return results
