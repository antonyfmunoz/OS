"""Wave 2 — source-level prohibitions against re-softening a guard.

Round-2 review identified one pattern behind three CRITICALs: *a check was added,
then softened with a truthiness guard, an env hatch, or a primitive exemption so
existing tests and hosts would keep passing*. Each softening is precisely where
the guarantee died.

These tests pin the prohibitions themselves, so a future edit that reintroduces
any of them fails here rather than silently in the field.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from substrate.execution.attempts.lifecycle import (
    AttemptLifecycleError,
    _assert_durable_proof,
)
from substrate.execution.attempts.records import ExecutionAttempt

_ROOT = Path(__file__).resolve().parent.parent


def _production_sources() -> list[Path]:
    """Every production python file (substrate + scripts), excluding tests."""
    out: list[Path] = []
    for base in ("substrate", "scripts"):
        for path in (_ROOT / base).rglob("*.py"):
            if "test" in path.name:
                continue
            out.append(path)
    return out


def _code_only(text: str) -> str:
    """Strip comments and docstrings so a prohibition is checked against CODE.

    These files deliberately DOCUMENT the removed softenings; a raw substring
    scan would match the explanation and fail. Assert on what executes.
    """
    out: list[str] = []
    in_doc = False
    for line in text.splitlines():
        stripped = line.strip()
        if in_doc:
            if '"""' in stripped:
                in_doc = False
            continue
        if stripped.startswith('"""') and stripped.count('"""') == 1:
            in_doc = True
            continue
        if stripped.startswith("#"):
            continue
        out.append(line.split("  #")[0])
    return "\n".join(out)


# ── SEC-C3: no proof bypass may exist in production ─────────────────────────


def test_no_proof_bypass_env_var_in_production_sources():
    """The ambient hatch is gone and may not return.

    It was inherited by the runner subprocess via `bash -c "exec env ..."`, so a
    stale export in ANY shell silently voided governed completion.
    """
    offenders = [
        str(p.relative_to(_ROOT))
        for p in _production_sources()
        if "UMH_W2_ALLOW_NONDURABLE_PROOF" in _code_only(p.read_text(encoding="utf-8"))
    ]
    assert not offenders, f"proof-bypass env var reintroduced in: {offenders}"


def test_proof_gate_holds_even_with_the_old_var_set(monkeypatch, tmp_path):
    """Behavioural proof the hatch is dead, not merely renamed."""
    monkeypatch.setenv("UMH_W2_ALLOW_NONDURABLE_PROOF", "1")
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    attempt = ExecutionAttempt(task_id="wp-a")
    attempt.attempt_id = "ea-1"
    with pytest.raises(AttemptLifecycleError):
        _assert_durable_proof(attempt, "p-DOES-NOT-EXIST")


def test_fabricated_proof_id_cannot_complete_an_attempt(monkeypatch, tmp_path):
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    attempt = ExecutionAttempt(task_id="wp-a")
    attempt.attempt_id = "ea-1"
    with pytest.raises(AttemptLifecycleError, match="not durably persisted"):
        _assert_durable_proof(attempt, "proof-made-up")


# ── SEC-C2: Proof binding is exact, and absent lineage is a rejection ───────


def _mint(monkeypatch, tmp_path, *, work_id: str, action: dict, bind_attempt=None):
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    from substrate.organism.proof_runtime import ProofRuntime

    rt = ProofRuntime()
    pkg = rt.create_direct(
        work_id=work_id, action=action, outcome="attempt_proof:passed", operator="verifier:v1"
    )
    # RV-HIGH-1: a POSITIVE (accepted) AttemptProof must carry digest-valid,
    # correctly-bound confined-verifier evidence — the completion gate now
    # validates it. Rejection tests pass bind_attempt=None (they must fail on the
    # lineage check first, which runs BEFORE the evidence check). Only the
    # correctly-bound control attaches evidence.
    if bind_attempt is not None:
        from substrate.execution.attempts.verifier_isolation import (
            VERIFIER_EVIDENCE_TYPE,
            VerifierEvidence,
        )
        from substrate.organism.proof_runtime import ProofEvidence

        ev = VerifierEvidence(
            verifier_lease_id="vl-1",
            attempt_id=bind_attempt.attempt_id,
            task_id=bind_attempt.task_id,
            assignment_id="",
            verifier_identity="verifier:v1",
            verifier_role_id="role-verifier-op",
            worker_identity="worker:w1",
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
        rt._persist_package(pkg)  # noqa: SLF001 - canonical seam
    return pkg


def test_proof_with_absent_lineage_is_rejected(monkeypatch, tmp_path):
    """The fail-open: a Proof carrying no attempt_id used to satisfy the gate for
    EVERY attempt on the same task."""
    pkg = _mint(
        monkeypatch, tmp_path, work_id="wp-shared", action={"classification": "attempt_proof"}
    )
    attempt = ExecutionAttempt(task_id="wp-shared")
    attempt.attempt_id = "ea-VICTIM"
    with pytest.raises(AttemptLifecycleError, match="absent lineage|bound to attempt"):
        _assert_durable_proof(attempt, pkg.proof_id)


def test_proof_for_another_attempt_is_rejected(monkeypatch, tmp_path):
    pkg = _mint(
        monkeypatch,
        tmp_path,
        work_id="wp-a",
        action={"classification": "attempt_proof", "attempt_id": "ea-OTHER"},
    )
    attempt = ExecutionAttempt(task_id="wp-a")
    attempt.attempt_id = "ea-MINE"
    with pytest.raises(AttemptLifecycleError, match="bound to attempt"):
        _assert_durable_proof(attempt, pkg.proof_id)


def test_proof_for_another_task_is_rejected(monkeypatch, tmp_path):
    pkg = _mint(
        monkeypatch,
        tmp_path,
        work_id="wp-OTHER",
        action={"classification": "attempt_proof", "attempt_id": "ea-1"},
    )
    attempt = ExecutionAttempt(task_id="wp-MINE")
    attempt.attempt_id = "ea-1"
    with pytest.raises(AttemptLifecycleError, match="proves task"):
        _assert_durable_proof(attempt, pkg.proof_id)


def test_correctly_bound_proof_is_accepted(monkeypatch, tmp_path):
    """Control: the guard must not be so tight that a legitimate Proof fails,
    otherwise the rejection tests above prove nothing."""
    attempt = ExecutionAttempt(task_id="wp-a")
    attempt.attempt_id = "ea-1"
    pkg = _mint(
        monkeypatch,
        tmp_path,
        work_id="wp-a",
        action={"classification": "attempt_proof", "attempt_id": "ea-1"},
        bind_attempt=attempt,
    )
    _assert_durable_proof(attempt, pkg.proof_id)  # must not raise


def test_binding_checks_are_not_truthiness_guarded():
    """Source-level: the `if recorded and recorded != ...` shape must not return."""
    src = _code_only(
        (_ROOT / "substrate/execution/attempts/lifecycle.py").read_text(encoding="utf-8")
    )
    assert "if recorded_attempt and recorded_attempt" not in src
    assert "if recorded_task and attempt.task_id and" not in src


def test_context_only_attempt_proof_without_evidence_is_allowed(monkeypatch, tmp_path):
    """RV-HIGH-1 boundary: a context-only / harness AttemptProof (no confined-
    verifier evidence record) is EXEMPT from evidence validation by design — the
    confined verifier (field path) always threads a record, a bare-list harness
    supplier legitimately does not. The outer lineage + mint-time checks gate it.
    This is the correct boundary: the gate validates evidence WHEN PRESENT; it does
    not fabricate a requirement the design never made."""
    attempt = ExecutionAttempt(task_id="wp-a")
    attempt.attempt_id = "ea-1"
    pkg = _mint(  # bind_attempt=None → no verifier evidence attached
        monkeypatch,
        tmp_path,
        work_id="wp-a",
        action={"classification": "attempt_proof", "attempt_id": "ea-1"},
    )
    _assert_durable_proof(attempt, pkg.proof_id)  # must NOT raise (context-only)


def test_tampered_attempt_proof_evidence_is_rejected_at_completion(monkeypatch, tmp_path):
    """RV-HIGH-1 (the reviewer's exact reproduction): a durable AttemptProof whose
    persisted verifier evidence is edited (zero_diff/tests_ok flipped) with a stale
    evidence_sha256 must be REJECTED at verifying→succeeded. Before wiring the C-4a
    validators into _assert_durable_proof, this tampered proof still completed."""
    import json

    attempt = ExecutionAttempt(task_id="wp-a")
    attempt.attempt_id = "ea-1"
    pkg = _mint(
        monkeypatch,
        tmp_path,
        work_id="wp-a",
        action={"classification": "attempt_proof", "attempt_id": "ea-1"},
        bind_attempt=attempt,
    )
    # Sanity: the untampered proof is accepted.
    _assert_durable_proof(attempt, pkg.proof_id)

    # Tamper the persisted proof store: flip zero_diff/tests_ok in the verifier
    # evidence WITHOUT recomputing evidence_sha256 (a plaintext-store edit).
    from substrate.execution.attempts.verifier_isolation import VERIFIER_EVIDENCE_TYPE

    store = tmp_path / "state" / "organism" / "proof_packages.jsonl"
    lines = store.read_text(encoding="utf-8").splitlines()
    out = []
    for ln in lines:
        obj = json.loads(ln)
        for e in obj.get("evidence", []):
            if e.get("evidence_type") == VERIFIER_EVIDENCE_TYPE:
                e["data"]["zero_diff"] = False
                e["data"]["tests_ok"] = False
        out.append(json.dumps(obj))
    store.write_text("\n".join(out) + "\n", encoding="utf-8")

    with pytest.raises(
        AttemptLifecycleError, match="tampered|does not recompute|evidence is missing"
    ):
        _assert_durable_proof(attempt, pkg.proof_id)


# ── SEC-C4: qualification requires bwrap specifically ───────────────────────


def test_non_bwrap_primitive_cannot_qualify(monkeypatch):
    """systemd-run / nsjail provide no mount namespace and must not pass."""
    import substrate.execution.attempts.host_isolation as hi

    for primitive in ("systemd-run", "nsjail"):
        monkeypatch.setattr(hi, "isolation_primitive", lambda p=primitive: p)
        ok, detail = hi.preflight_isolation("/opt/OS")
        assert ok is False, f"{primitive} must not qualify execution"
        assert "bwrap" in detail


def test_isolation_gates_fail_closed_for_every_primitive():
    """Source-level: neither gate may special-case bwrap in its failure branch."""
    src = _code_only((_ROOT / "scripts/wave2_attempt_runner.py").read_text(encoding="utf-8"))
    assert 'if not ok and prim == "bwrap"' not in src, "runner gate re-exempted non-bwrap"
    assert 'ok or prim != "bwrap"' not in src, "preflight gate re-exempted non-bwrap"
    assert "if not ok:" in src, "runner must fail closed for every primitive"


def test_bwrap_preflight_actually_probes(monkeypatch):
    """Control: with real bwrap present the preflight still passes, so the
    fail-closed change did not simply disable qualification."""
    import substrate.execution.attempts.host_isolation as hi

    if hi.isolation_primitive() != "bwrap":
        pytest.skip("bwrap not available on this host")
    ok, detail = hi.preflight_isolation("/opt/OS")
    assert ok is True and "hidden" in detail
