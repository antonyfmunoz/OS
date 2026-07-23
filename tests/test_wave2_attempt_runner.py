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
            return {"ok": True, "status": "succeeded", "files_changed": self.files_changed,
                    "commits": self.commits, "isolated": True}

    seen = {}

    def _fake_worker(*, package, lease, timeout, max_turns, disallowed_tools, oauth_token):
        seen["worktree"] = lease.worktree_path
        seen["disallowed"] = list(disallowed_tools)
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
    spool.enqueue(DispatchEnvelope(
        dispatch_id="d1", attempt_id="ea-1", task_id="wp-a",
        authorization_ref="ref", package_hash="ph", lease_id="l1",
        worktree_path=str(wt), nonce="n", sequence=1, payload_hash="p",
    ))

    rc = runner.run_loop(spool_root=spool_root, secret=secret, max_iterations=1, poll_seconds=0.01)
    assert rc == 0
    assert seen["worktree"] == str(wt)

    # A SIGNED result is in the outbox and drains cleanly.
    results = spool.drain_results()
    assert len(results) == 1
    assert results[0]["attempt_id"] == "ea-1"
    assert results[0]["worker_result"]["status"] == "succeeded"


def test_runner_quarantines_bad_signature(tmp_path):
    """A tampered dispatch is quarantined by the spool the runner uses — never run."""
    spool_root = str(tmp_path / "spool")
    producer = DispatchSpool(spool_root, "real-secret")
    producer.enqueue(DispatchEnvelope(dispatch_id="d1", attempt_id="ea-1", sequence=1,
                                      worktree_path=str(tmp_path)))
    # A runner with the WRONG secret cannot claim it (signature check fails).
    consumer = DispatchSpool(spool_root, "wrong-secret")
    assert consumer.claim_next() is None
