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
}


def run_scenario(name: str) -> SimState:
    state = SimState(scenario=name)
    SCENARIOS[name](state)
    state.assert_invariants()
    if name != "fallback_unavailable":
        assert state.lifecycle in {"RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", "RECONCILIATION_REQUIRED"}, state.log
    return state


def run_all_scenarios() -> dict[str, dict[str, object]]:
    results: dict[str, dict[str, object]] = {}
    for name in sorted(SCENARIOS):
        state = run_scenario(name)
        results[name] = {
            "lifecycle": state.lifecycle,
            "executed": state.executed,
            "fail_closed": state.fail_closed,
            "log": list(state.log),
        }
    return results
