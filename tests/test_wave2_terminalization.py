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
        # Record the REAL base. The real SandboxManager always resolves one (it
        # raises otherwise), and reporting "" here made the stub claim a state no
        # production sandbox can produce: a worktree holding a commit whose origin
        # is unknowable. Terminalization now (correctly) refuses to destroy that,
        # so an honest stub is required to exercise the ordinary cleanup path.
        base = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=wt, capture_output=True, text=True
        ).stdout.strip()
        return SimpleNamespace(
            worktree_path=wt, branch_name=f"b{self._i}", base_commit=base, sandbox_id=f"sb{self._i}"
        )

    def cleanup_sandbox(self, sandbox_id, *, preserve_branch=False):
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


def test_residue_scoping_is_path_boundary_not_substring(store, tmp_path):
    """RV-MED-1: terminalizing attempt `ea-1` must NOT mis-attribute a SIBLING
    attempt's residue whose id has `ea-1` as a prefix (`ea-11`). The old
    `home_path in p` substring match flagged the wrong attempt; a path-boundary
    match (`== or startswith(home_path + sep)`) does not."""

    lm = _lease_manager(store, tmp_path)
    # ea-1 with a CLEAN home (its own credential destroyed).
    a1, _ = _leased_attempt(store, lm)
    a1.attempt_id = "ea-1"
    home1 = open_attempt_credential_home(attempt_id="ea-1", run_root=str(tmp_path))
    # ea-11 (a DIFFERENT attempt whose id has ea-1 as a prefix) keeps a live
    # credential — it is NOT part of this terminalization.
    src = tmp_path / "src11"
    src.mkdir()
    (src / ".credentials.json").write_text('{"token":"SIBLING"}')
    open_attempt_credential_home(
        attempt_id="ea-11", run_root=str(tmp_path), source_claude_dir=str(src)
    )

    a1.status = _S.FAILED.value
    result = terminalize(attempt=a1, reason="failed", lease_manager=lm, run_root=str(tmp_path))
    # ea-1's own home was destroyed; the sibling ea-11 credential is NOT counted
    # against ea-1 (no substring mis-attribution).
    assert not os.path.exists(home1.home_path)
    assert result.credential_residue == [], (
        f"sibling residue mis-attributed: {result.credential_residue}"
    )
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


# ── C-2 microfix: ok fails for ANY error, not just SECURITY-prefixed ─────────
#
# The first cut of `ok` returned True unless a SECURITY-prefixed error or
# credential residue was present, so a lease-release failure reported ok=True and
# the run would pass while the task's lease stayed ACTIVE. That is the exact
# fail-open this campaign exists to kill.


def test_lease_release_failure_fails_the_terminalization(store, tmp_path, monkeypatch):
    lm = _lease_manager(store, tmp_path)
    a1, _ = _leased_attempt(store, lm)
    a1.status = _S.FAILED.value

    def _boom(*a, **k):
        raise RuntimeError("release blew up")

    monkeypatch.setattr(lm, "release", _boom)
    result = terminalize(
        attempt=a1,
        reason="failed",
        lease_manager=lm,
        run_root=str(tmp_path),
        raise_on_security_failure=False,
    )
    assert result.ok is False, "a lease-release failure must fail the terminalization"
    assert result.lease_released is False
    assert any("lease release failed" in e for e in result.errors)
    # The lease is STILL active → retry must remain inadmissible.
    assert store.active_lease_for_task("wp-a") is not None
    ok, _ = retry_admissible(store, "wp-a")
    assert ok is False, "a failed release must not let a retry be admitted"


def test_missing_lease_manager_with_a_lease_fails(store, tmp_path):
    a1, _ = _leased_attempt(store, _lease_manager(store, tmp_path))
    a1.status = _S.FAILED.value
    result = terminalize(
        attempt=a1,
        reason="failed",
        lease_manager=None,
        run_root=str(tmp_path),
        raise_on_security_failure=False,
    )
    assert result.ok is False
    assert any("no lease_manager" in e for e in result.errors)


def test_missing_run_root_fails(store, tmp_path):
    lm = _lease_manager(store, tmp_path)
    a1, _ = _leased_attempt(store, lm)
    a1.status = _S.FAILED.value
    result = terminalize(
        attempt=a1,
        reason="failed",
        lease_manager=lm,
        run_root="",
        raise_on_security_failure=False,
    )
    assert result.ok is False
    assert any("run_root" in e for e in result.errors)


# ── spool reconciliation ─────────────────────────────────────────────────────


def test_spool_reconcile_failure_fails_the_terminalization(store, tmp_path):
    lm = _lease_manager(store, tmp_path)
    a1, _ = _leased_attempt(store, lm)
    a1.status = _S.FAILED.value

    class _BoomSpool:
        def drop_inflight_for_attempt(self, attempt_id):
            raise RuntimeError("spool exploded")

    result = terminalize(
        attempt=a1,
        reason="failed",
        lease_manager=lm,
        run_root=str(tmp_path),
        spool=_BoomSpool(),
        raise_on_security_failure=False,
    )
    assert result.ok is False
    assert any("spool reconcile failed" in e for e in result.errors)


def test_spool_without_drop_hook_is_not_reconciled(store, tmp_path):
    """A spool was SUPPLIED but exposes no hook — that is a missing capability,
    an explicit failure, not a benign 'ledger is truth' no-op."""
    lm = _lease_manager(store, tmp_path)
    a1, _ = _leased_attempt(store, lm)
    a1.status = _S.FAILED.value
    result = terminalize(
        attempt=a1,
        reason="failed",
        lease_manager=lm,
        run_root=str(tmp_path),
        spool=object(),  # no drop_inflight_for_attempt
        raise_on_security_failure=False,
    )
    assert result.spool_reconciled is False
    assert result.ok is False
    assert any("no drop_inflight_for_attempt" in e for e in result.errors)


def test_no_spool_is_a_clean_noop(store, tmp_path):
    """CONTROL: spool=None means 'nothing to reconcile' and stays clean — the
    failure cases above are about a SUPPLIED spool, not the absence of one."""
    lm = _lease_manager(store, tmp_path)
    a1, _ = _leased_attempt(store, lm)
    a1.status = _S.FAILED.value
    assert (
        terminalize(attempt=a1, reason="failed", lease_manager=lm, run_root=str(tmp_path)).ok
        is True
    )


# ── DispatchSpool.drop_inflight_for_attempt ──────────────────────────────────


def _real_spool(tmp_path):
    from substrate.execution.attempts.spool import DispatchSpool

    return DispatchSpool(str(tmp_path / "spool"), "run-secret")


def _enqueue(spool, *, attempt_id, dispatch_id):
    from substrate.execution.attempts.spool import DispatchEnvelope

    spool.enqueue(
        DispatchEnvelope(
            dispatch_id=dispatch_id,
            attempt_id=attempt_id,
            task_id="wp-a",
            nonce=dispatch_id,
            sequence=1,
            worktree_path="/x",
            base_commit="b",
            governance_constraints=["writable_path_scope=['app/main.py']"],
        )
    )


def test_drop_inflight_removes_exact_attempt_only(tmp_path):
    spool = _real_spool(tmp_path)
    _enqueue(spool, attempt_id="ea-target", dispatch_id="d-target")
    _enqueue(spool, attempt_id="ea-sibling", dispatch_id="d-sibling")

    reconciled = spool.drop_inflight_for_attempt("ea-target")
    assert reconciled == ["d-target"], reconciled

    # The SIBLING envelope must survive and still be claimable.
    claim = spool.claim_next()
    assert claim is not None
    _tok, env = claim
    assert env.attempt_id == "ea-sibling", "reconcile must never touch a sibling attempt"


def test_drop_inflight_covers_both_inbox_and_inflight(tmp_path):
    spool = _real_spool(tmp_path)
    _enqueue(spool, attempt_id="ea-1", dispatch_id="d-inbox")
    _enqueue(spool, attempt_id="ea-1", dispatch_id="d-inflight")
    # Claim one → it moves to inflight; the other stays in inbox.
    spool.claim_next()
    reconciled = spool.drop_inflight_for_attempt("ea-1")
    assert set(reconciled) == {"d-inbox", "d-inflight"}, reconciled
    assert spool.claim_next() is None, "nothing claimable after reconcile"


def test_drop_inflight_is_idempotent(tmp_path):
    spool = _real_spool(tmp_path)
    _enqueue(spool, attempt_id="ea-1", dispatch_id="d-1")
    assert spool.drop_inflight_for_attempt("ea-1") == ["d-1"]
    assert spool.drop_inflight_for_attempt("ea-1") == [], "second call is a clean no-op"


def test_drop_inflight_quarantines_a_tampered_envelope(tmp_path):
    """A badly-signed envelope naming the attempt must be quarantined (fail
    closed), never left claimable."""
    import json
    import os

    spool = _real_spool(tmp_path)
    _enqueue(spool, attempt_id="ea-1", dispatch_id="d-1")
    # Tamper the on-disk record's signature.
    inbox = os.path.join(str(tmp_path / "spool"), "inbox")
    name = os.listdir(inbox)[0]
    path = os.path.join(inbox, name)
    rec = json.load(open(path))
    rec["signature"] = "0" * 64
    json.dump(rec, open(path, "w"))

    reconciled = spool.drop_inflight_for_attempt("ea-1")
    assert reconciled, "a tampered envelope for this attempt must be reconciled (quarantined)"
    assert spool.claim_next() is None, "the tampered envelope must not remain claimable"


# ── truthful wiring: exactly the two reasons the live poller performs ─────────
#
# The authority SUPPORTS eleven reasons; the production pipeline WIRES two. This
# test pins that boundary so the count can neither silently shrink (a terminal
# path stops terminalizing) nor be overclaimed (docs say eleven wired).


def test_poller_wires_exactly_succeeded_and_verification_rejected():
    """AST-level: ControlPlanePoller._verify_and_settle invokes _terminalize with
    exactly the two reasons the live pipeline transitions an attempt through."""
    import ast
    import inspect

    from substrate.execution.attempts import poller as P

    src = inspect.getsource(P.ControlPlanePoller)
    tree = ast.parse(src.lstrip())
    reasons = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "_terminalize"
        ):
            # second positional arg is the reason string literal
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                reasons.add(node.args[1].value)
    assert reasons == {"succeeded", "verification_rejected"}, (
        f"the live poller wires exactly these terminal reasons; got {reasons}. "
        f"If a new terminal path was wired, update this test AND the ledger — "
        f"the authority supporting a reason is not the pipeline wiring it."
    )


def test_scheduler_does_not_claim_a_revoke_cascade_it_lacks():
    """The scheduler docstring must not claim it cancels/revokes attempts: it has
    no such code, and the overclaim previously masked that the cascade is a
    Wave 2 follow-on (order §4/§6 truthfulness)."""
    import inspect

    from substrate.execution.attempts import scheduler as SCH

    src = inspect.getsource(SCH)
    # No production cascade code exists...
    assert "def _cascade" not in src and "def _sweep_revoked" not in src
    # ...so the module docstring must say the wiring is pending, not done.
    module_doc = SCH.__doc__ or ""
    assert "pending" in module_doc.lower(), (
        "the scheduler must state the revoke/expire cascade is pending, not claim it"
    )
