"""Wave 2 C-2 — ONE idempotent lease/home terminalization authority.

The C-2 deadlock: A1 fails → its lease stays ACTIVE (LeaseManager.release had
ZERO production callers) → the scheduler mints A2 → acquire() raises (one active
lease per task) → A2 BLOCKED → re-READY → BLOCKED, forever. Worse, the failure
pass then produced the EXACT observable shape the qualification expects ("A
failed, C blocked, no false Proof") for entirely the wrong reason.

These tests exercise the single authority over REAL stores and REAL credential
homes on disk, and prove:
  * terminalize releases the lease so the retry becomes admissible;
  * it destroys the attempt-private credential home (SEC-C1 residue);
  * it is idempotent (a second call is a verified no-op);
  * cleanup failure is a BLOCKING SECURITY condition, not a warning;
  * it refuses to terminalize a still-live attempt (would strand a worker);
  * every one of the eleven terminal reasons is covered.
"""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from substrate.execution.attempts.records import ExecutionAttempt, ExecutionAttemptStatus
from substrate.execution.attempts.store import ExecutionAttemptStore
from substrate.execution.attempts.terminalization import (
    TERMINAL_REASONS,
    TerminalizationError,
    retry_admissible,
    terminalize,
)
from substrate.execution.attempts.worker_credential_boundary import (
    assert_no_credential_residue,
    open_attempt_credential_home,
)

_S = ExecutionAttemptStatus


@pytest.fixture()
def store(tmp_path):
    return ExecutionAttemptStore(
        attempts_path=str(tmp_path / "a.jsonl"),
        grants_path=str(tmp_path / "g.jsonl"),
        readiness_path=str(tmp_path / "r.jsonl"),
        leases_path=str(tmp_path / "l.jsonl"),
        assignments_path=str(tmp_path / "asn.jsonl"),
    )


class _RealSandbox:
    """Real git worktrees so LeaseManager.release actually removes something."""

    def __init__(self, base):
        self._repo_root = str(base / "repo")
        os.makedirs(self._repo_root, exist_ok=True)
        self._base = base
        self._i = 0

    def create_sandbox(self, candidate_id, candidate_slug, agent_type="developer_agent"):
        import subprocess

        self._i += 1
        wt = str(self._base / f"wt-{self._i}")
        os.makedirs(wt, exist_ok=True)
        open(os.path.join(wt, "f.txt"), "w").write("x")
        for a in (
            ("init", "-q"),
            ("config", "user.email", "t@e.com"),
            ("config", "user.name", "t"),
            ("add", "-A"),
            ("commit", "-q", "-m", "b"),
        ):
            subprocess.run(["git", *a], cwd=wt, capture_output=True, check=True)
        return SimpleNamespace(
            worktree_path=wt, branch_name=f"b{self._i}", base_commit="", sandbox_id=f"sb{self._i}"
        )

    def cleanup_sandbox(self, sandbox_id):
        pass


def _lease_manager(store, base):
    from substrate.execution.attempts.leases import LeaseManager

    def _runner(**kw):
        fn = kw.get("execute_fn")
        out, ok = fn() if fn else ("", True)
        return SimpleNamespace(success=ok, output=out)

    return LeaseManager(store, _RealSandbox(base), mutation_runner=_runner)


def _leased_attempt(store, lm, task="wp-a"):
    """Create an attempt with a REAL active lease, walked to a failed state."""
    a = ExecutionAttempt(task_id=task, tenant_id="t", worker_identity="w")
    a, _ = store.create_attempt_idempotent(a)
    lease = lm.acquire(
        attempt=a,
        assignment=SimpleNamespace(worker_identity="w", compute_node_id="n", tool_profile=[]),
        grant=SimpleNamespace(tenant_id="t", credential_scope_refs=[]),
    )
    a.lease_id = lease.lease_id
    return a, lease


# ── the deadlock: terminalize is what unblocks the retry ─────────────────────


def test_failed_attempt_lease_blocks_retry_until_terminalized(store, tmp_path):
    lm = _lease_manager(store, tmp_path)
    a1, lease = _leased_attempt(store, lm)

    # Before terminalization: the task has an active lease → retry NOT admissible.
    ok, reason = retry_admissible(store, "wp-a")
    assert ok is False, reason
    assert store.active_lease_for_task("wp-a") is not None

    # A1 reaches a terminal status, then terminalizes.
    a1.status = _S.FAILED.value
    result = terminalize(
        attempt=a1,
        reason="failed",
        lease_manager=lm,
        run_root=str(tmp_path),
        raise_on_security_failure=False,
    )
    assert result.lease_released is True

    # After terminalization: no active lease → retry admissible → A2 can acquire.
    ok, reason = retry_admissible(store, "wp-a")
    assert ok is True, reason
    assert store.active_lease_for_task("wp-a") is None


def test_retry_can_acquire_a_new_lease_after_terminalization(store, tmp_path):
    """End-to-end: A2's acquire() would raise LeaseError before terminalize and
    succeeds after — the exact deadlock, closed."""
    from substrate.execution.attempts.leases import LeaseError

    lm = _lease_manager(store, tmp_path)
    a1, _ = _leased_attempt(store, lm)

    a2 = ExecutionAttempt(task_id="wp-a", tenant_id="t", worker_identity="w", attempt_number=2)
    a2, _ = store.create_attempt_idempotent(a2)
    asn = SimpleNamespace(worker_identity="w", compute_node_id="n", tool_profile=[])
    grant = SimpleNamespace(tenant_id="t", credential_scope_refs=[])

    with pytest.raises(LeaseError):  # deadlock BEFORE terminalization
        lm.acquire(attempt=a2, assignment=asn, grant=grant)

    a1.status = _S.FAILED.value
    terminalize(
        attempt=a1,
        reason="failed",
        lease_manager=lm,
        run_root=str(tmp_path),
        raise_on_security_failure=False,
    )

    lease2 = lm.acquire(attempt=a2, assignment=asn, grant=grant)  # now succeeds
    assert lease2.lease_id and lease2.lease_id != a1.lease_id


# ── credential home destruction (SEC-C1 overlap) ─────────────────────────────


def test_terminalize_destroys_the_attempt_credential_home(store, tmp_path):
    lm = _lease_manager(store, tmp_path)
    a1, _ = _leased_attempt(store, lm)
    # Place a REAL credential home for this attempt.
    src = tmp_path / "src_claude"
    (src).mkdir()
    (src / ".credentials.json").write_text('{"token":"SECRET"}')
    home = open_attempt_credential_home(
        attempt_id=a1.attempt_id, run_root=str(tmp_path), source_claude_dir=str(src)
    )
    assert os.path.exists(home.home_path)
    assert assert_no_credential_residue(str(tmp_path)), "sanity: a credential exists"

    a1.status = _S.FAILED.value
    result = terminalize(attempt=a1, reason="failed", lease_manager=lm, run_root=str(tmp_path))
    assert result.home_destroyed is True
    assert not os.path.exists(home.home_path)
    assert assert_no_credential_residue(str(tmp_path)) == [], "no credential may survive"
    assert result.ok is True


def test_worker_crash_path_destroys_home_even_though_worker_never_cleaned(store, tmp_path):
    """SEC-C1: the SIGTERM/crash path never ran the worker's finally. The
    authority is what sweeps the home the worker abandoned."""
    lm = _lease_manager(store, tmp_path)
    a1, _ = _leased_attempt(store, lm)
    src = tmp_path / "src"
    src.mkdir()
    (src / ".credentials.json").write_text('{"token":"X"}')
    home = open_attempt_credential_home(
        attempt_id=a1.attempt_id, run_root=str(tmp_path), source_claude_dir=str(src)
    )
    # The worker "crashed": home still on disk, never closed.
    a1.status = _S.FAILED.value
    result = terminalize(
        attempt=a1, reason="worker_crash", lease_manager=lm, run_root=str(tmp_path)
    )
    assert not os.path.exists(home.home_path)
    assert result.ok is True


# ── idempotence ──────────────────────────────────────────────────────────────


def test_terminalize_is_idempotent(store, tmp_path):
    lm = _lease_manager(store, tmp_path)
    a1, _ = _leased_attempt(store, lm)
    a1.status = _S.FAILED.value
    r1 = terminalize(attempt=a1, reason="failed", lease_manager=lm, run_root=str(tmp_path))
    assert r1.ok
    # Second call: lease already released, home already gone → clean no-op.
    r2 = terminalize(attempt=a1, reason="failed", lease_manager=lm, run_root=str(tmp_path))
    assert r2.ok is True
    assert assert_no_credential_residue(str(tmp_path)) == []


# ── cleanup failure is a BLOCKING SECURITY condition ─────────────────────────


def test_cleanup_failure_is_a_blocking_security_condition(store, tmp_path, monkeypatch):
    """If the credential home cannot be destroyed, terminalize RAISES by default
    — a run may never be reported clean while credential material survives."""
    lm = _lease_manager(store, tmp_path)
    a1, _ = _leased_attempt(store, lm)
    src = tmp_path / "src"
    src.mkdir()
    (src / ".credentials.json").write_text('{"token":"X"}')
    open_attempt_credential_home(
        attempt_id=a1.attempt_id, run_root=str(tmp_path), source_claude_dir=str(src)
    )
    a1.status = _S.FAILED.value

    # Make destruction a no-op so the credential survives; the residue scan must
    # then catch it. `_destroy_home` imports the closer from the boundary module
    # at call time, so patch it THERE (patching the terminalization namespace
    # would miss the local import — which is itself worth pinning).
    import substrate.execution.attempts.worker_credential_boundary as wcb

    monkeypatch.setattr(wcb, "close_attempt_credential_home", lambda home: None)
    with pytest.raises(TerminalizationError):
        terminalize(attempt=a1, reason="failed", lease_manager=lm, run_root=str(tmp_path))

    # With raising disabled the failure is on the result, never silently dropped.
    result = terminalize(
        attempt=a1,
        reason="failed",
        lease_manager=lm,
        run_root=str(tmp_path),
        raise_on_security_failure=False,
    )
    assert result.ok is False
    assert result.credential_residue, "residue must be reported, not hidden"


def test_missing_close_hook_is_patched_for_the_test_only(store, tmp_path):
    """Control: without the monkeypatch, real destruction succeeds — proving the
    failure test fails for the injected reason, not a broken import."""
    lm = _lease_manager(store, tmp_path)
    a1, _ = _leased_attempt(store, lm)
    src = tmp_path / "src"
    src.mkdir()
    (src / ".credentials.json").write_text('{"token":"X"}')
    open_attempt_credential_home(
        attempt_id=a1.attempt_id, run_root=str(tmp_path), source_claude_dir=str(src)
    )
    a1.status = _S.FAILED.value
    assert (
        terminalize(attempt=a1, reason="failed", lease_manager=lm, run_root=str(tmp_path)).ok
        is True
    )


# ── refuses a still-live attempt ─────────────────────────────────────────────


def test_terminalize_refuses_a_non_terminal_attempt(store, tmp_path):
    """Releasing a lease under a RUNNING worker would strand it — refuse."""
    lm = _lease_manager(store, tmp_path)
    a1, _ = _leased_attempt(store, lm)
    a1.status = _S.RUNNING.value  # still live
    with pytest.raises(TerminalizationError, match="not terminal"):
        terminalize(attempt=a1, reason="failed", lease_manager=lm, run_root=str(tmp_path))
    # The lease is untouched — the running worker keeps its workspace.
    assert store.active_lease_for_task("wp-a") is not None


# ── every terminal reason is covered ─────────────────────────────────────────


@pytest.mark.parametrize("reason", sorted(TERMINAL_REASONS))
def test_every_terminal_reason_terminalizes_cleanly(store, tmp_path, reason):
    lm = _lease_manager(store, tmp_path)
    a1, _ = _leased_attempt(store, lm, task=f"wp-{reason[:4]}")
    a1.status = _S.CANCELLED.value if reason == "cancelled" else _S.FAILED.value
    result = terminalize(attempt=a1, reason=reason, lease_manager=lm, run_root=str(tmp_path))
    assert result.ok is True, f"{reason}: {result.errors}"
    assert result.lease_released is True


def test_unknown_reason_fails_closed(store, tmp_path):
    lm = _lease_manager(store, tmp_path)
    a1, _ = _leased_attempt(store, lm)
    a1.status = _S.FAILED.value
    with pytest.raises(TerminalizationError, match="unknown terminal reason"):
        terminalize(attempt=a1, reason="whatever", lease_manager=lm, run_root=str(tmp_path))
