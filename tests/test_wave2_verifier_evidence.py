"""Wave 2 C-4a — durable verifier evidence + exact-commit binding.

C-4 confinement is accepted. C-4a closes the evidence chain: the confined
verifier's structured evidence is persisted INSIDE the exact AttemptProof
(one typed ProofEvidence), digest-bound over the complete canonical payload
(lineage + BOTH commits + timestamps + trusted process identity + isolation
results), and reread-validatable from disk after a process restart — with NO
process-local ``_last_verifier_evidence`` authority.

Three defects closed:
1. evidence is threaded run_confined_verifier_checks → verify_attempt →
   _persist_proof → ProofPackage (not a process-local field);
2. verified_commit is the ACTUAL worktree HEAD (parent-read), never the base
   (lease.snapshot_ref), which is recorded separately as base_commit;
3. finalize() hashes the complete payload incl. started_at/ended_at + a REAL
   trusted process identity (verifier_pid never 0 on success).
"""

from __future__ import annotations

import subprocess

import pytest

from substrate.execution.attempts import verifier_isolation as vi
from substrate.execution.attempts.host_isolation import isolation_primitive
from substrate.execution.attempts.verification import verify_attempt
from tests.test_wave2_verifier_isolation import _skip_if_cpu_gated

_HAS_BWRAP = isolation_primitive() == "bwrap"
_needs_bwrap = pytest.mark.skipif(not _HAS_BWRAP, reason="bwrap unavailable in this environment")


class _Att:
    def __init__(self, attempt_id="att-1", task_id="wp-1"):
        self.attempt_id = attempt_id
        self.task_id = task_id
        self.assignment_id = "asg-" + attempt_id
        self.lease_id = "lease-" + attempt_id
        self.tenant_id = "tenant-a"
        self.plan_record_id = "opr-1"
        self.plan_version = 1
        self.attempt_number = 1
        self.worker_identity = "worker:role-impl:" + attempt_id
        self.instruction_package_hash = "pkg-" + attempt_id


class _WR:
    def __init__(self, head):
        self.files_changed = ["app.py"]
        self.commits = [head]


class _Lease:
    def __init__(self, worktree, snapshot_ref):
        self.worktree_path = worktree
        self.snapshot_ref = snapshot_ref


def _fixture_with_worker_commit(tmp_path):
    """A committed source where HEAD (worker commit) != base_commit."""
    src = tmp_path / "src"
    (src / "tests").mkdir(parents=True)
    (src / "tests" / "test_ok.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")

    def _g(*a):
        subprocess.run(
            ["git", "-c", "user.email=a@b.c", "-c", "user.name=t", *a], cwd=src, check=True
        )

    subprocess.run(["git", "init", "-q"], cwd=src, check=True)
    _g("add", "-A")
    _g("commit", "-qm", "base")
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=src, capture_output=True, text=True
    ).stdout.strip()
    (src / "app.py").write_text("x = 1\n", encoding="utf-8")
    _g("add", "-A")
    _g("commit", "-qm", "worker")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=src, capture_output=True, text=True
    ).stdout.strip()
    return str(src), base, head


def _mint_durable_proof(tmp_path, att, *, source, base, head, expected=None, monkeypatch=None):
    """Run the real confined seam through verify_attempt and mint a durable Proof.
    Returns (proof_id, proof_runtime, verdict). diff-scope is stubbed (C-1 covers it)."""
    import substrate.execution.attempts.verification as V
    from substrate.organism.proof_runtime import ProofRuntime

    # C-1 diff-scope is separately covered; stub it so THIS test isolates C-4a.
    orig = V._diff_scope_verdict
    V._diff_scope_verdict = lambda **k: (True, "scope ok (c4a harness)")

    def supplier(a):
        return vi.run_confined_verifier_checks(
            attempt=a,
            run_root=str(tmp_path / "run"),
            source_path=source,
            verifier_role_id="role-verifier-op",
            worker_identity=a.worker_identity,
            base_commit=base,
            expected_result_commit=expected if expected is not None else head,
            assignment_id=a.assignment_id,
            package_hash=a.instruction_package_hash,
            timeout_s=120,
        )

    pr = ProofRuntime()
    try:
        verdict = verify_attempt(
            attempt=att,
            assignment=att,
            lease=_Lease(source, base),
            worker_result=_WR(head),
            package_hash=att.instruction_package_hash,
            verifier_identity=f"verifier:role-verifier-op:{att.attempt_id}",
            verifier_role_id="role-verifier-op",
            packet=object(),
            semantic_label="",
            independent_checks=supplier,
            proof_runtime=pr,
        )
    finally:
        V._diff_scope_verdict = orig
    return verdict.proof_id, pr, verdict


# ── exact-commit binding (item 2) ───────────────────────────────────────────


@_needs_bwrap
def test_verified_commit_is_worker_head_not_base(tmp_path):
    _skip_if_cpu_gated()
    src, base, head = _fixture_with_worker_commit(tmp_path)
    assert base != head
    att = _Att()
    checks, ev = vi.run_confined_verifier_checks(
        attempt=att,
        run_root=str(tmp_path / "run"),
        source_path=src,
        verifier_role_id="role-verifier-op",
        worker_identity=att.worker_identity,
        base_commit=base,
        assignment_id=att.assignment_id,
        package_hash=att.instruction_package_hash,
        timeout_s=120,
    )
    assert ev.verified_commit == head, "verified_commit must be the tested worktree HEAD"
    assert ev.base_commit == base and ev.verified_commit != ev.base_commit


@_needs_bwrap
def test_expected_result_commit_mismatch_fails(tmp_path):
    _skip_if_cpu_gated()
    src, base, head = _fixture_with_worker_commit(tmp_path)
    att = _Att()
    checks, ev = vi.run_confined_verifier_checks(
        attempt=att,
        run_root=str(tmp_path / "run"),
        source_path=src,
        verifier_role_id="role-verifier-op",
        worker_identity=att.worker_identity,
        base_commit=base,
        expected_result_commit="0" * 40,  # wrong expected HEAD
        timeout_s=120,
    )
    cb = next(c for c in checks if c.check_id == "verifier_commit_binding")
    assert cb.ok is False and "expected" in cb.detail.lower()


@_needs_bwrap
def test_head_movement_during_verification_fails(tmp_path, monkeypatch):
    _skip_if_cpu_gated()
    src, base, head = _fixture_with_worker_commit(tmp_path)
    # make the AFTER head-read return a different sha → head moved
    calls = {"n": 0}
    orig = vi._parent_side_head

    def _fake(source):
        calls["n"] += 1
        if calls["n"] >= 2:  # the AFTER read
            return True, "f" * 40
        return orig(source)

    monkeypatch.setattr(vi, "_parent_side_head", _fake)
    att = _Att()
    checks, ev = vi.run_confined_verifier_checks(
        attempt=att,
        run_root=str(tmp_path / "run"),
        source_path=src,
        verifier_role_id="role-verifier-op",
        worker_identity=att.worker_identity,
        base_commit=base,
        timeout_s=120,
    )
    zd = next(c for c in checks if c.check_id == "verifier_zero_diff")
    assert zd.ok is False and "head_moved" in zd.detail.lower()


# ── real process identity (item 4) ──────────────────────────────────────────


@_needs_bwrap
def test_real_trusted_process_identity(tmp_path):
    _skip_if_cpu_gated()
    src, base, head = _fixture_with_worker_commit(tmp_path)
    att = _Att()
    checks, ev = vi.run_confined_verifier_checks(
        attempt=att,
        run_root=str(tmp_path / "run"),
        source_path=src,
        verifier_role_id="role-verifier-op",
        worker_identity=att.worker_identity,
        base_commit=base,
        timeout_s=120,
    )
    pi = next(c for c in checks if c.check_id == "verifier_process_identity")
    assert pi.ok is True
    assert ev.verifier_pid > 0, "a successful proof must carry a real pid, never 0"
    assert ev.process_identity.get("valid") is True
    assert ev.process_identity.get("nonce")  # parent-generated nonce recorded


# ── integrity digest (item 3) ───────────────────────────────────────────────


@_needs_bwrap
def test_digest_covers_timestamps_and_identity(tmp_path):
    _skip_if_cpu_gated()
    src, base, head = _fixture_with_worker_commit(tmp_path)
    _, ev = vi.run_confined_verifier_checks(
        attempt=_Att(),
        run_root=str(tmp_path / "run"),
        source_path=src,
        verifier_role_id="role-verifier-op",
        worker_identity="worker:x",
        base_commit=base,
        timeout_s=120,
    )
    assert ev.evidence_sha256 == ev.recompute_digest()
    # mutating ANY claimed field changes the digest
    for field, val in (
        ("started_at", ev.started_at + 1),
        ("ended_at", ev.ended_at + 1),
        ("verifier_pid", ev.verifier_pid + 1),
        ("verified_commit", "0" * 40),
        ("base_commit", "1" * 40),
        ("attempt_id", "other"),
    ):
        clone = vi.VerifierEvidence.from_dict(ev.to_dict())
        setattr(clone, field, val)
        assert clone.recompute_digest() != ev.evidence_sha256, field


def test_digest_does_not_hash_itself():
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(vi.VerifierEvidence._canonical_payload).lstrip())
    fn = tree.body[0]
    body = fn.body[1:] if isinstance(fn.body[0], ast.Expr) else fn.body  # drop docstring
    code = "\n".join(ast.unparse(n) for n in body)
    assert "evidence_sha256" not in code, "the digest must not be hashed into itself"


# ── durable persistence + restart reread (item 6) ───────────────────────────


@_needs_bwrap
def test_durable_proof_reread_binds_full_lineage(tmp_path, monkeypatch):
    _skip_if_cpu_gated()
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    from substrate.organism.proof_runtime import ProofRuntime

    src, base, head = _fixture_with_worker_commit(tmp_path)
    att = _Att(attempt_id="att-reread")
    proof_id, pr, verdict = _mint_durable_proof(tmp_path, att, source=src, base=base, head=head)
    assert verdict.passed and proof_id, [c for c in verdict.checks if not c["ok"]]

    # destroy runtime; fresh store rereads from DISK
    del pr
    pr2 = ProofRuntime()
    proof = pr2.reread_durable(proof_id)
    assert proof is not None, "Proof not durable on disk"

    ev = vi.validate_evidence_binding(
        proof,
        attempt_id=att.attempt_id,
        task_id=att.task_id,
        assignment_id=att.assignment_id,
        verifier_identity=f"verifier:role-verifier-op:{att.attempt_id}",
        verified_commit=head,
        package_hash=att.instruction_package_hash,
    )
    assert ev.verified_commit == head and ev.base_commit == base
    assert ev.verifier_pid > 0


@_needs_bwrap
def test_reread_rejects_base_as_verified_commit(tmp_path, monkeypatch):
    _skip_if_cpu_gated()
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    from substrate.organism.proof_runtime import ProofRuntime

    src, base, head = _fixture_with_worker_commit(tmp_path)
    att = _Att(attempt_id="att-base")
    proof_id, pr, verdict = _mint_durable_proof(tmp_path, att, source=src, base=base, head=head)
    del pr
    proof = ProofRuntime().reread_durable(proof_id)
    # a validator that expects the BASE as verified must fail closed
    with pytest.raises(vi.VerifierEvidenceBindingError):
        vi.validate_evidence_binding(
            proof, attempt_id=att.attempt_id, task_id=att.task_id, verified_commit=base
        )


@_needs_bwrap
def test_exactly_one_verifier_evidence_in_proof(tmp_path, monkeypatch):
    _skip_if_cpu_gated()
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    from substrate.organism.proof_runtime import ProofRuntime

    src, base, head = _fixture_with_worker_commit(tmp_path)
    att = _Att(attempt_id="att-one")
    proof_id, pr, _ = _mint_durable_proof(tmp_path, att, source=src, base=base, head=head)
    del pr
    proof = ProofRuntime().reread_durable(proof_id)
    records = [e for e in proof.evidence if e.evidence_type == vi.VERIFIER_EVIDENCE_TYPE]
    assert len(records) == 1
    # evidence_from_proof enforces exactly-one + digest recompute
    ev = vi.evidence_from_proof(proof)
    assert ev.evidence_sha256 == ev.recompute_digest()


def test_no_verifier_evidence_fails_closed():
    class _P:
        evidence = []

    with pytest.raises(vi.VerifierEvidenceBindingError, match="no verifier evidence"):
        vi.evidence_from_proof(_P())


def test_multiple_verifier_evidence_fails_closed():
    from substrate.organism.proof_runtime import ProofEvidence

    class _P:
        evidence = [
            ProofEvidence(evidence_type=vi.VERIFIER_EVIDENCE_TYPE, data={}),
            ProofEvidence(evidence_type=vi.VERIFIER_EVIDENCE_TYPE, data={}),
        ]

    with pytest.raises(vi.VerifierEvidenceBindingError, match="2 verifier evidence"):
        vi.evidence_from_proof(_P())


def test_tampered_digest_fails_reread():
    from substrate.organism.proof_runtime import ProofEvidence

    src_att = _Att()
    ev = vi.VerifierEvidence(
        verifier_lease_id="vl",
        attempt_id=src_att.attempt_id,
        task_id=src_att.task_id,
        assignment_id="asg",
        verifier_identity="v",
        verifier_role_id="role-verifier-op",
        worker_identity="w",
        package_hash="p",
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
    d = ev.to_dict()
    d["verified_commit"] = "e" * 40  # tamper AFTER the digest was computed

    class _P:
        evidence = [ProofEvidence(evidence_type=vi.VERIFIER_EVIDENCE_TYPE, data=d)]

    with pytest.raises(vi.VerifierEvidenceBindingError, match="does not recompute"):
        vi.evidence_from_proof(_P())


# ── concurrency (item 7) ────────────────────────────────────────────────────


@_needs_bwrap
def test_two_attempts_have_distinct_bound_evidence(tmp_path, monkeypatch):
    _skip_if_cpu_gated()
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    from substrate.organism.proof_runtime import ProofRuntime

    src1, base1, head1 = _fixture_with_worker_commit(tmp_path / "a")
    src2, base2, head2 = _fixture_with_worker_commit(tmp_path / "b")
    att1 = _Att(attempt_id="att-A", task_id="wp-A")
    att2 = _Att(attempt_id="att-B", task_id="wp-B")
    pid1, pr1, v1 = _mint_durable_proof(tmp_path / "a", att1, source=src1, base=base1, head=head1)
    pid2, pr2, v2 = _mint_durable_proof(tmp_path / "b", att2, source=src2, base=base2, head=head2)
    assert pid1 and pid2 and pid1 != pid2
    del pr1, pr2
    store = ProofRuntime()
    p1 = store.reread_durable(pid1)
    p2 = store.reread_durable(pid2)
    e1 = vi.evidence_from_proof(p1)
    e2 = vi.evidence_from_proof(p2)
    # each Proof binds to its own attempt; digests differ; no cross-substitution
    assert e1.attempt_id == "att-A" and e2.attempt_id == "att-B"
    assert e1.evidence_sha256 != e2.evidence_sha256
    with pytest.raises(vi.VerifierEvidenceBindingError):
        # att-A's proof must NOT validate as att-B
        vi.validate_evidence_binding(p1, attempt_id="att-B", task_id="wp-B")


# ── source/AST guards (item 8 mutation guards) ──────────────────────────────


def test_no_process_local_last_evidence_authority():
    """The control plane must NOT store evidence in a process-local field as the
    authority; it returns (checks, evidence) threaded into the Proof."""
    import ast
    import inspect

    from substrate.execution.attempts import field_control_plane as fcp

    code = ast.unparse(ast.parse(inspect.getsource(fcp.FieldControlPlaneDriver).lstrip()))
    assert "_last_verifier_evidence =" not in code, (
        "evidence must not be assigned to a process-local authority field"
    )
    ic = ast.unparse(
        ast.parse(inspect.getsource(fcp.FieldControlPlaneDriver._independent_checks_for).lstrip())
    )
    assert "return run_confined_verifier_checks(" in ic, "must return (checks, evidence)"


def test_verify_attempt_threads_evidence_to_proof():
    """verify_attempt must pass verifier_evidence into _persist_proof."""
    import ast
    import inspect

    from substrate.execution.attempts import verification as V

    code = ast.unparse(ast.parse(inspect.getsource(V.verify_attempt).lstrip()))
    assert "verifier_evidence" in code
    assert "_persist_proof" in code


def test_persist_proof_adds_typed_verifier_evidence():
    import ast
    import inspect

    from substrate.execution.attempts import verification as V

    code = ast.unparse(ast.parse(inspect.getsource(V._persist_proof).lstrip()))
    assert "VERIFIER_EVIDENCE_TYPE" in code
    assert "verifier_evidence.to_dict()" in code


def test_seam_uses_parent_head_not_snapshot_ref():
    """run_confined_verifier_checks must read verified_commit via _parent_side_head,
    never assign snapshot_ref/base to verified_commit."""
    import ast
    import inspect

    code = ast.unparse(ast.parse(inspect.getsource(vi.run_confined_verifier_checks).lstrip()))
    assert "_parent_side_head(source_path)" in code
    assert "verified_commit = base_commit" not in code
    assert "verified_commit=verified_commit" in code
