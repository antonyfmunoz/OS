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


def _mint(monkeypatch, tmp_path, *, work_id: str, action: dict):
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    from substrate.organism.proof_runtime import ProofRuntime

    return ProofRuntime().create_direct(
        work_id=work_id, action=action, outcome="attempt_proof:passed", operator="verifier:v1"
    )


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
    )
    _assert_durable_proof(attempt, pkg.proof_id)  # must not raise


def test_binding_checks_are_not_truthiness_guarded():
    """Source-level: the `if recorded and recorded != ...` shape must not return."""
    src = _code_only(
        (_ROOT / "substrate/execution/attempts/lifecycle.py").read_text(encoding="utf-8")
    )
    assert "if recorded_attempt and recorded_attempt" not in src
    assert "if recorded_task and attempt.task_id and" not in src


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
