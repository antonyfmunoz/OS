"""Wave 2 C5 — independent verification + two Proof classifications."""

from __future__ import annotations

import os

from types import SimpleNamespace

import pytest

from substrate.execution.attempts.lifecycle import AttemptLifecycleError
from substrate.execution.attempts.records import ExecutionAttempt, ExecutionAttemptStatus
from substrate.execution.attempts.store import AttemptStoreConflict, ExecutionAttemptStore
from substrate.execution.attempts.verification import (
    ATTEMPT_PROOF,
    PLAN_EXECUTION_PROOF,
    VerificationCheck,
    verify_attempt,
    verify_plan_execution,
)

_GUARD_ERRORS = (AttemptStoreConflict, AttemptLifecycleError)
_S = ExecutionAttemptStatus


def _attach_valid_verifier_evidence(rt, pkg, attempt):
    """Attach a digest-valid, correctly-bound confined-verifier evidence record to
    a durable AttemptProof and re-persist — mirroring production _persist_proof.

    RV-HIGH-1: the verifying→succeeded gate validates this evidence, so a proof
    used to complete an attempt must carry it (a bare proof no longer completes).
    """
    from substrate.execution.attempts.verifier_isolation import (
        VERIFIER_EVIDENCE_TYPE,
        VerifierEvidence,
    )
    from substrate.organism.proof_runtime import ProofEvidence

    ev = VerifierEvidence(
        verifier_lease_id="vl-1",
        attempt_id=attempt.attempt_id,
        task_id=attempt.task_id,
        assignment_id="",
        verifier_identity="verifier:v1",
        verifier_role_id="role-verifier-op",
        worker_identity=getattr(attempt, "worker_identity", "") or "worker:w1",
        package_hash="",
        base_commit="b" * 40,
        verified_commit="c" * 40,
        bwrap_argv=["bwrap"],
        bwrap_argv_digest="d",
        env_var_names=["PATH"],
        mount_policy={},
        isolation_probe={"ok": True},
        source_hashes_before={},
        source_hashes_after={},
        zero_diff=True,
        tests_ok=True,
        tests_detail="ok",
        started_at=1.0,
        ended_at=2.0,
        process_identity={"pid": 7, "valid": True},
        verifier_pid=7,
    ).finalize()
    pkg.evidence.append(
        ProofEvidence(
            evidence_type=VERIFIER_EVIDENCE_TYPE,
            description="confined verifier run",
            data=ev.to_dict(),
        )
    )
    rt._persist_package(pkg)  # noqa: SLF001 - canonical seam, as production does


def _ProofRT(tmp_path=None):
    """The REAL canonical ProofRuntime, pointed at a temp store.

    Replaces a former stub that only held an in-memory `_packages` dict — the
    exact shape that let a dangling proof_id complete an attempt (finding C1).
    Tests now exercise durable persistence and canonical reread.
    """
    import tempfile

    from substrate.organism.proof_runtime import ProofRuntime

    base = str(tmp_path) if tmp_path is not None else tempfile.mkdtemp()
    return ProofRuntime(store_path=os.path.join(base, "proof_packages.jsonl"))


def _attempt(worker="worker-1", pkg_hash="h1"):
    a = ExecutionAttempt(task_id="wp-a", instruction_package_hash=pkg_hash, worker_identity=worker)
    a.attempt_id = "ea-1"
    return a


def _assignment(worker="worker-1"):
    return SimpleNamespace(worker_identity=worker)


def _lease(writable=("app", "tests")):
    # Allowlist entries are worktree-RELATIVE, matching how git reports changed
    # paths. The former "/tmp/wt" absolute entry could never match a real diff —
    # it only passed because diff_scope was hardcoded ok=True (finding C4).
    return SimpleNamespace(writable_paths=list(writable), worktree_path="", snapshot_ref="")


def _real_worktree(tmp_path, name="wt"):
    """A real git worktree with one base commit.

    Diff-scope is now computed by running git against the lease worktree, so a
    stub lease cannot exercise it. Tests that assert on scope must supply a real
    tree; a stub is exactly the shape that hid finding C-1.
    """
    import subprocess

    root = tmp_path / name
    (root / "app").mkdir(parents=True)
    (root / "app" / "main.py").write_text("# base\n", encoding="utf-8")
    for args in (
        ("init", "-q"),
        ("config", "user.email", "t@example.com"),
        ("config", "user.name", "t"),
        ("add", "-A"),
        ("commit", "-q", "-m", "base"),
    ):
        subprocess.run(["git", *args], cwd=str(root), check=True, capture_output=True)
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(root), capture_output=True, text=True
    ).stdout.strip()
    return SimpleNamespace(path=str(root), base=base)


def _scoped(tmp_path, allowed=("app",), name="wt"):
    """(lease, packet) pair over a real worktree with a declared path scope."""
    wt = _real_worktree(tmp_path, name)
    lease = SimpleNamespace(worktree_path=wt.path, snapshot_ref=wt.base, writable_paths=[wt.path])
    packet = SimpleNamespace(
        packet_id="wp-a",
        requirements={"writable_path_scope": list(allowed), "scope_declared": True},
    )
    return wt, lease, packet


def _worker_result(files=("app/main.py",), commits=("abc123 add search",)):
    return SimpleNamespace(files_changed=list(files), commits=list(commits))


# ── AttemptProof ─────────────────────────────────────────────────────────────


def test_attempt_proof_passes_with_real_artifacts(tmp_path):
    """The PASS control. Requires a real worktree + declared scope, because the
    repaired diff-scope check is computed independently via git — a stub lease
    can no longer produce a pass, which is the point of finding C-1."""
    rt = _ProofRT(tmp_path)
    wt, lease, packet = _scoped(tmp_path, allowed=("app",))
    with open(os.path.join(wt.path, "app", "main.py"), "a", encoding="utf-8") as f:
        f.write("# in-scope change\n")
    verdict = verify_attempt(
        attempt=_attempt(pkg_hash="h1"),
        assignment=_assignment(),
        lease=lease,
        worker_result=_worker_result(),
        package_hash="h1",
        verifier_identity="verifier-1",
        verifier_role_id="role-verify-op",
        packet=packet,
        proof_runtime=rt,
    )
    assert verdict.classification == ATTEMPT_PROOF
    assert verdict.passed is True
    assert verdict.proof_id  # a proof was persisted
    assert rt.reread_durable(verdict.proof_id) is not None, "Proof must be DURABLE, not in-memory"


def test_verifier_must_differ_from_worker():
    with pytest.raises(ValueError):
        verify_attempt(
            attempt=_attempt(worker="same"),
            assignment=_assignment(worker="same"),
            lease=_lease(),
            worker_result=_worker_result(),
            package_hash="h1",
            verifier_identity="same",
            verifier_role_id="role-verify-op",
        )


def test_no_artifacts_fails_verification(tmp_path):
    rt = _ProofRT(tmp_path)
    verdict = verify_attempt(
        attempt=_attempt(),
        assignment=_assignment(),
        lease=_lease(),
        worker_result=_worker_result(files=(), commits=()),  # nothing produced
        package_hash="h1",
        verifier_identity="v",
        verifier_role_id="r",
        proof_runtime=rt,
    )
    assert verdict.passed is False
    assert verdict.proof_id == ""  # no success proof for a failed verification


def test_package_hash_mismatch_fails():
    verdict = verify_attempt(
        attempt=_attempt(pkg_hash="h1"),
        assignment=_assignment(),
        lease=_lease(),
        worker_result=_worker_result(),
        package_hash="h-TAMPERED",
        verifier_identity="v",
        verifier_role_id="r",
    )
    assert verdict.passed is False


def test_independent_checks_can_fail_verdict():
    def failing_checks(attempt):
        return [VerificationCheck(check_id="tests", kind="tests", ok=False, detail="2 failing")]

    verdict = verify_attempt(
        attempt=_attempt(),
        assignment=_assignment(),
        lease=_lease(),
        worker_result=_worker_result(),
        package_hash="h1",
        verifier_identity="v",
        verifier_role_id="r",
        independent_checks=failing_checks,
    )
    assert verdict.passed is False  # verifier ran its OWN tests, which failed


# ── Proof-gated completion (integrates with the lifecycle guard) ─────────────


@pytest.fixture()
def store(tmp_path):
    return ExecutionAttemptStore(
        attempts_path=str(tmp_path / "a.jsonl"),
        grants_path=str(tmp_path / "g.jsonl"),
        readiness_path=str(tmp_path / "r.jsonl"),
        leases_path=str(tmp_path / "l.jsonl"),
        assignments_path=str(tmp_path / "asn.jsonl"),
    )


def test_attempt_completes_only_with_proof_and_distinct_verifier(store, tmp_path, monkeypatch):
    """Completion requires a DURABLE Proof bound to this attempt, a distinct
    verifier, and a verifier actor. A fabricated proof_id is refused (finding
    C1: the guard used to accept any truthy string)."""
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    a = ExecutionAttempt(task_id="wp-a", worker_identity="worker-1")
    a.status = _S.VERIFYING.value
    store.create_attempt_idempotent(a)

    # Without a proof_id → the lifecycle guard rejects succeeded.
    with pytest.raises(_GUARD_ERRORS):
        store.transition_cas(
            a.attempt_id,
            "succeeded",
            a.record_version,
            ("verifying",),
            actor="verifier:v1",
            updates={"verifier_identity": "v1"},
        )

    # A FABRICATED proof_id that was never persisted → rejected. This is the
    # dangling-proof hole: any truthy string used to complete an attempt.
    with pytest.raises(_GUARD_ERRORS):
        store.transition_cas(
            a.attempt_id,
            "succeeded",
            a.record_version,
            ("verifying",),
            actor="verifier:v1",
            updates={"proof_id": "p-NEVER-PERSISTED", "verifier_identity": "v1"},
        )

    # Mint a REAL durable Proof bound to this attempt.
    from substrate.organism.proof_runtime import ProofRuntime

    rt = ProofRuntime()  # honors UMH_STATE_DIR (the guard rereads the same store)
    pkg = rt.create_direct(
        work_id=a.task_id,
        action={"classification": ATTEMPT_PROOF, "attempt_id": a.attempt_id},
        outcome=f"{ATTEMPT_PROOF}:passed",
        operator="verifier:v1",
    )
    # RV-HIGH-1: the completion gate now requires an AttemptProof to carry a
    # digest-valid, correctly-bound confined-verifier evidence record (the C-4a
    # validators are wired into _assert_durable_proof). Attach one, as the real
    # field _persist_proof path does, so a COMPLETE proof reaches SUCCEEDED.
    _attach_valid_verifier_evidence(rt, pkg, a)

    # Verifier == worker → still rejected even with a durable proof.
    with pytest.raises(_GUARD_ERRORS):
        store.transition_cas(
            a.attempt_id,
            "succeeded",
            a.record_version,
            ("verifying",),
            actor="verifier:worker-1",
            updates={"proof_id": pkg.proof_id, "verifier_identity": "worker-1"},
        )

    # Durable Proof + distinct verifier + verifier actor → succeeds.
    updated = store.transition_cas(
        a.attempt_id,
        "succeeded",
        a.record_version,
        ("verifying",),
        actor="verifier:v1",
        updates={"proof_id": pkg.proof_id, "verifier_identity": "v1"},
    )
    assert updated.status == "succeeded"
    assert updated.proof_id == pkg.proof_id


def test_durable_proof_for_another_attempt_cannot_complete_this_one(store, tmp_path, monkeypatch):
    """A Proof that IS durable but belongs to a different attempt must not
    complete this attempt — lineage binding, not mere existence."""
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    from substrate.organism.proof_runtime import ProofRuntime

    a = ExecutionAttempt(task_id="wp-a", worker_identity="worker-1")
    a.status = _S.VERIFYING.value
    store.create_attempt_idempotent(a)

    rt = ProofRuntime()
    other = rt.create_direct(
        work_id="wp-a",
        action={"classification": ATTEMPT_PROOF, "attempt_id": "ea-SOMEONE-ELSE"},
        outcome=f"{ATTEMPT_PROOF}:passed",
        operator="verifier:v1",
    )
    with pytest.raises(_GUARD_ERRORS, match="another attempt|bound to attempt"):
        store.transition_cas(
            a.attempt_id,
            "succeeded",
            a.record_version,
            ("verifying",),
            actor="verifier:v1",
            updates={"proof_id": other.proof_id, "verifier_identity": "v1"},
        )


def test_proof_survives_process_restart(tmp_path, monkeypatch):
    """A Proof minted by one runtime instance must be rereadable by a FRESH one
    — the restart-durability property the qualification depends on."""
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    from substrate.organism.proof_runtime import ProofRuntime

    minted = ProofRuntime().create_direct(
        work_id="wp-restart",
        action={"classification": ATTEMPT_PROOF, "attempt_id": "ea-restart"},
        outcome=f"{ATTEMPT_PROOF}:passed",
        operator="verifier:v1",
    )
    # A brand-new runtime (simulating a restarted process) must find it on disk.
    assert ProofRuntime().reread_durable(minted.proof_id) is not None


# ── PlanExecutionProof ───────────────────────────────────────────────────────


def test_plan_execution_proof(tmp_path):
    rt = _ProofRT(tmp_path)

    def recon_checks():
        return [
            VerificationCheck(check_id="reconvergence", kind="diff", ok=True, detail="merged"),
            VerificationCheck(check_id="full_tests", kind="tests", ok=True, detail="all green"),
            VerificationCheck(check_id="live_http", kind="http", ok=True, detail="200"),
            VerificationCheck(check_id="browser", kind="browser", ok=True, detail="renders"),
            VerificationCheck(
                check_id="source_integrity", kind="policy", ok=True, detail="/opt/OS unchanged"
            ),
            VerificationCheck(check_id="zero_deploy", kind="policy", ok=True, detail="no fly/gh"),
        ]

    verdict = verify_plan_execution(
        plan_record_id="opr-1",
        integration_task_id="wp-c",
        verifier_identity="verifier-D",
        verifier_role_id="role-verify-op",
        reconvergence_checks=recon_checks,
        proof_runtime=rt,
    )
    assert verdict.classification == PLAN_EXECUTION_PROOF
    assert verdict.passed is True
    assert rt.reread_durable(verdict.proof_id) is not None, "Proof must be DURABLE, not in-memory"


def test_plan_execution_proof_fails_on_any_check():
    def recon_checks():
        return [
            VerificationCheck(check_id="full_tests", kind="tests", ok=True, detail="green"),
            VerificationCheck(
                check_id="zero_deploy", kind="policy", ok=False, detail="fly deploy detected!"
            ),
        ]

    verdict = verify_plan_execution(
        plan_record_id="opr-1",
        integration_task_id="wp-c",
        verifier_identity="v",
        verifier_role_id="r",
        reconvergence_checks=recon_checks,
    )
    assert verdict.passed is False


def test_diff_outside_allowlist_fails_verification(tmp_path):
    """R3 / finding C-1: a worker writing outside its allowed paths must FAIL.

    This test previously passed a stub lease and asserted on the worker's OWN
    reported file list — which the repaired verifier no longer trusts, because a
    scope verdict resting on the worker's narrative is not an independent check.
    It now uses a REAL git worktree and a canonical packet, so the assertion is
    about what the verifier independently observed. Full mutation coverage lives
    in tests/test_wave2_diff_scope_authority.py.
    """
    rt = _ProofRT(tmp_path)
    wt = _real_worktree(tmp_path)
    # The worker writes outside its authorized scope.
    with open(os.path.join(wt.path, "infra_secrets.tf"), "w", encoding="utf-8") as f:
        f.write("# not authorized\n")
    verdict = verify_attempt(
        attempt=_attempt(),
        assignment=_assignment(),
        lease=SimpleNamespace(
            worktree_path=wt.path, snapshot_ref=wt.base, writable_paths=[wt.path]
        ),
        worker_result=_worker_result(files=("app/main.py",), commits=("abc",)),
        package_hash="h1",
        verifier_identity="v",
        verifier_role_id="r",
        packet=SimpleNamespace(
            packet_id="wp-a", requirements={"writable_path_scope": ["app"], "scope_declared": True}
        ),
        proof_runtime=rt,
    )
    assert verdict.passed is False, "an out-of-allowlist diff must fail verification"
    scope = next(c for c in verdict.checks if c["check_id"] == "diff_scope")
    assert scope["ok"] is False
    assert "infra_secrets.tf" in scope["detail"]
    assert verdict.proof_id == "", "no Proof for a scope violation"


def test_missing_assignment_fails_verification(tmp_path):
    """Absent verification context is a FAILURE, not a quiet pass — the
    assignment lookup used to return None for every attempt (finding C4)."""
    rt = _ProofRT(tmp_path)
    verdict = verify_attempt(
        attempt=_attempt(),
        assignment=None,  # lookup resolved nothing
        lease=_lease(),
        worker_result=_worker_result(),
        package_hash="h1",
        verifier_identity="v",
        verifier_role_id="r",
        proof_runtime=rt,
    )
    assert verdict.passed is False
    ctx = next(c for c in verdict.checks if c["check_id"] == "verification_context")
    assert ctx["ok"] is False and "assignment" in ctx["detail"]


def test_missing_lease_fails_verification(tmp_path):
    rt = _ProofRT(tmp_path)
    verdict = verify_attempt(
        attempt=_attempt(),
        assignment=_assignment(),
        lease=None,
        worker_result=_worker_result(),
        package_hash="h1",
        verifier_identity="v",
        verifier_role_id="r",
        proof_runtime=rt,
    )
    assert verdict.passed is False
    ctx = next(c for c in verdict.checks if c["check_id"] == "verification_context")
    assert ctx["ok"] is False and "lease" in ctx["detail"]
