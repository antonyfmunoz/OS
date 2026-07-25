"""Wave 2 C7 — host attempt runner: spool → isolated worker → signed result."""

from __future__ import annotations

import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from substrate.execution.attempts.host_isolation import isolation_primitive  # noqa: E402
from substrate.execution.attempts.spool import DispatchEnvelope, DispatchSpool  # noqa: E402


def test_runner_preflight_requires_isolation():
    # This environment must have a real isolation primitive for the runner to run.
    assert isolation_primitive() is not None


def test_runner_processes_dispatch_and_writes_signed_result(tmp_path, monkeypatch):
    """The runner claims a signed dispatch, runs the (stubbed) worker in the lease
    worktree, and writes a SIGNED result to the outbox — without touching the
    attempt ledger (the control-plane poller owns transitions)."""
    import scripts.wave2_attempt_runner as runner

    # Stub the real worker so the test doesn't spend Claude CLI quota, but keep
    # the runner's spool + isolation-preflight logic real.
    class _Result:
        ok = True
        status = "succeeded"
        files_changed = ["app/main.py"]
        commits = ["abc add search"]
        isolated = True

        def to_dict(self):
            return {
                "ok": True,
                "status": "succeeded",
                "files_changed": self.files_changed,
                "commits": self.commits,
                "isolated": True,
            }

    seen = {}

    def _fake_worker(
        *,
        package,
        lease,
        timeout,
        max_turns,
        disallowed_tools,
        oauth_token,
        attempt_id="",
        run_root="",
    ):
        seen["worktree"] = lease.worktree_path
        seen["disallowed"] = list(disallowed_tools)
        # R1: the runner MUST pass the attempt identity + run root so the worker
        # can bind an attempt-PRIVATE credential home. Without these the worker
        # fails closed, so assert they actually arrive.
        seen["attempt_id"] = attempt_id
        seen["run_root"] = run_root
        return _Result()

    monkeypatch.setattr(runner, "run_worker_in_lease", _fake_worker, raising=False)
    # Also patch the name used inside run_loop's local import path.
    import substrate.execution.attempts.worker_claude_cli as wcc

    monkeypatch.setattr(wcc, "run_worker_in_lease", _fake_worker)

    wt = tmp_path / "wt"
    wt.mkdir()
    spool_root = str(tmp_path / "spool")
    secret = "run-secret"
    spool = DispatchSpool(spool_root, secret)
    spool.enqueue(
        DispatchEnvelope(
            dispatch_id="d1",
            attempt_id="ea-1",
            task_id="wp-a",
            authorization_ref="ref",
            package_hash="ph",
            lease_id="l1",
            worktree_path=str(wt),
            nonce="n",
            sequence=1,
            payload_hash="p",
        )
    )

    rc = runner.run_loop(spool_root=spool_root, secret=secret, max_iterations=1, poll_seconds=0.01)
    assert rc == 0
    assert seen["worktree"] == str(wt)
    # R1: attempt identity must reach the worker so it can bind an
    # attempt-private credential home (a shared home was finding SEC-C2).
    assert seen["attempt_id"] == "ea-1", "runner must pass attempt_id to the worker"
    assert seen["run_root"], "runner must pass a run_root for the private home"

    # A SIGNED result is in the outbox and drains cleanly.
    results = spool.drain_results()
    assert len(results) == 1
    assert results[0]["attempt_id"] == "ea-1"
    assert results[0]["worker_result"]["status"] == "succeeded"


def test_host_control_plane_governs_attempt_create_not_degraded(tmp_path, monkeypatch):
    """FIELD regression (fifth control-plane layer, run 20260725T202237Z).

    The host runner is a separate process from the candidate container, so its
    driver has NO organism daemon registered on the canonical organism_port. The
    driver creates attempts through governed mutations (execution_attempt_create,
    degraded_mode_allowed=False). With nothing registered,
    _substrate_native_governed_mutation degraded and every such mutation
    fail-closed — the grant activated, the packet was APPROVED, the driver
    reached admission, then refused to create the attempt ("control plane
    unavailable — FAIL CLOSED on execution_attempt_create") so NO worker ran.

    Every deterministic driver test INJECTED a stub mutation_runner that always
    succeeds (the exact wiring production lacked — same coverage-gap shape as
    layers 1-4). This pins the production path: _register_host_control_plane
    builds + registers a REAL host-side spine so a governed execution mutation
    runs non-degraded."""
    import scripts.wave2_attempt_runner as runner
    from substrate.execution.attempts.store import ExecutionAttemptStore
    from substrate.execution.intent.loop import _substrate_native_governed_mutation
    from substrate.sockets import organism_port

    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("UMH_ROOT", str(tmp_path / "repo"))
    (tmp_path / "repo").mkdir(exist_ok=True)
    monkeypatch.setattr(organism_port, "_get_organism_fn", None, raising=False)

    store = ExecutionAttemptStore()

    # BEFORE registration: a governed execution mutation degrades → fail closed.
    pre = _substrate_native_governed_mutation(
        mutation_name="execution_attempt_create",
        intent="probe",
        execute_fn=lambda: ("x", True),
        source="test",
        metadata={},
    )
    assert getattr(pre, "success", getattr(pre, "ok", None)) is False, (
        "with no control plane the mutation must fail closed (degraded_mode_allowed=False)"
    )

    # Register the host control plane (the fix).
    holder = runner._register_host_control_plane(store)
    assert hasattr(holder, "governed_spine") and hasattr(holder, "mutation_registry")

    # AFTER registration: the SAME mutation runs governed, non-degraded.
    post = _substrate_native_governed_mutation(
        mutation_name="execution_attempt_create",
        intent="probe",
        execute_fn=lambda: ("created", True),
        source="test",
        metadata={},
    )
    assert getattr(post, "success", getattr(post, "ok", None)) is True, (
        "the registered host spine must govern the mutation, not degrade it"
    )
    monkeypatch.setattr(organism_port, "_get_organism_fn", None, raising=False)


def test_runner_quarantines_bad_signature(tmp_path):
    """A tampered dispatch is quarantined by the spool the runner uses — never run."""
    spool_root = str(tmp_path / "spool")
    producer = DispatchSpool(spool_root, "real-secret")
    producer.enqueue(
        DispatchEnvelope(
            dispatch_id="d1", attempt_id="ea-1", sequence=1, worktree_path=str(tmp_path)
        )
    )
    # A runner with the WRONG secret cannot claim it (signature check fails).
    consumer = DispatchSpool(spool_root, "wrong-secret")
    assert consumer.claim_next() is None
