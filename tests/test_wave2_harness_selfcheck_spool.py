"""Wave 2 harness self-check — the signed_spool check must stay load-bearing.

The self-check's ``signed_spool`` case regressed to FAIL when the write-barrier
fix (commit 55c57c472, finding F-2) made the transport refuse envelopes carrying
no enforceable ``writable_path_scope=``. The check was building a synthetic
``DispatchEnvelope`` with no governance constraints at all, so the production
gate quarantined it — correctly. The harness was stale; the candidate was right.

These tests pin the CORRECTION so it cannot rot back:

* the positive case must be minted by the REAL compiler + projector, so the
  check fails if production stops sealing the scope (mutation M1);
* every fail-closed negative must stay armed — missing scope (M2), forged
  signature (M3), scope widened after signing (M4).

A test that inlined ``governance_constraints=["writable_path_scope=[...]"]``
would keep passing through all four mutations, which is exactly the blindness
being removed here.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

_WORKTREE = Path(__file__).resolve().parent.parent
if str(_WORKTREE) not in sys.path:
    sys.path.insert(0, str(_WORKTREE))


def _selfcheck():
    """Import the self-check script by path (scripts/ is not a package)."""
    path = _WORKTREE / "scripts" / "wave2_harness_selfcheck.py"
    spec = importlib.util.spec_from_file_location("wave2_harness_selfcheck", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_clerk_origin_uses_tailnet_status_not_env_override(monkeypatch):
    module = _selfcheck()
    monkeypatch.setenv("UMH_CANDIDATE_ORIGIN", "https://bypass.example:1234")

    def fake_run(cmd, **_kwargs):
        assert cmd == ["tailscale", "status", "--json"]
        return type(
            "Proc",
            (),
            {
                "returncode": 0,
                "stdout": json.dumps({"Self": {"DNSName": "srv1500858.tail6b4aa2.ts.net."}}),
                "stderr": "",
            },
        )()

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = module.check_clerk_origin()

    assert result["status"] == "PASS"
    assert result["evidence"] == "https://srv1500858.tail6b4aa2.ts.net:10443"
    assert "bypass.example" not in result["detail"]


def test_clerk_origin_override_cannot_greenlight_selfcheck(monkeypatch):
    module = _selfcheck()
    monkeypatch.setenv("UMH_CANDIDATE_ORIGIN", "https://bypass.example:1234")

    def fake_run(_cmd, **_kwargs):
        raise RuntimeError("tailscale unavailable")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = module.check_clerk_origin()

    assert result["status"] == "FAIL"
    assert "tailscale status" in result["detail"]


# ── the canonical minting path ───────────────────────────────────────────────


def test_governance_fields_come_from_the_real_compiler():
    """The scope is minted by compile_attempt_package, never inlined."""
    fields = _selfcheck().canonical_governance_fields(["app/main.py"])
    constraints = fields["governance_constraints"]

    scope = [c for c in constraints if str(c).startswith("writable_path_scope=")]
    assert scope == ["writable_path_scope=['app/main.py']"], constraints

    # The sealed package hash rides along; an envelope that claims authority
    # without naming the package it came from is not traceable to a compilation.
    assert fields["package_hash"], "no sealed package_hash projected"
    # Authority bounds the real dispatcher seals — proof this is the production
    # projection and not a hand-built subset.
    for key in ("authorization_ref=", "risk_ceiling=", "allowed_tools="):
        assert any(str(c).startswith(key) for c in constraints), f"missing {key}"


def test_declared_scope_is_honoured_not_hardcoded():
    """A different declared scope must change the minted constraint."""
    fields = _selfcheck().canonical_governance_fields(["svc/api.py", "svc/db.py"])
    assert "writable_path_scope=['svc/api.py', 'svc/db.py']" in fields["governance_constraints"]


def test_undeclared_scope_is_refused_by_the_dispatcher():
    """scope_declared=False must fail closed inside the real compiler."""
    from types import SimpleNamespace as NS

    from substrate.execution.attempts.dispatch import DispatchBlocked, compile_attempt_package

    with pytest.raises(DispatchBlocked):
        compile_attempt_package(
            attempt=NS(
                attempt_id="ea",
                task_id="wp",
                plan_record_id="pr",
                plan_version=1,
                execution_authorization_ref="auth",
                timeout_seconds=600,
                max_turns=30,
            ),
            packet=NS(
                packet_id="wp",
                title="t",
                user_intent="i",
                desired_end_state="d",
                constraints=[],
                validation_plan="pytest -q",
                requirements={"scope_declared": False, "writable_path_scope": ["app/main.py"]},
            ),
            assignment=NS(
                role_contract_id="role-impl-op",
                skill_requirement_refs=[],
                tool_profile=["shell"],
                environment_class="container",
                model_profile={"model": "claude-opus-5"},
            ),
            grant=NS(
                decision_ref="dec",
                authorized_scope_hash="h",
                risk_ceiling="reversible_write",
                task_frontier=["wp"],
                tenant_id="ten",
                verification_obligations=[],
                cost_limit_usd=1.0,
                cost_enforceable=True,
            ),
        )


# ── the four transport outcomes the check asserts ────────────────────────────


def test_signed_spool_check_passes_and_reports_every_control(tmp_path):
    result = _selfcheck().check_spool(tmp_path)
    assert result["status"] == "PASS", result
    for control in (
        "delivered=True",
        "bad_sig_rejected=True",
        "no_scope_rejected=True",
        "widened_scope_rejected=True",
    ):
        assert control in result["detail"], result["detail"]


def test_canonical_envelope_is_delivered_through_the_real_spool(tmp_path):
    """Positive control: the real write→sign→read→verify path delivers it."""
    from substrate.execution.attempts.spool import DispatchEnvelope, DispatchSpool

    gov = _selfcheck().canonical_governance_fields(["app/main.py"])
    spool = DispatchSpool(str(tmp_path / "s"), "secret")
    spool.enqueue(
        DispatchEnvelope(
            dispatch_id="d1",
            attempt_id="ea1",
            task_id="wp-selfcheck",
            nonce="n1",
            sequence=1,
            worktree_path=str(tmp_path),
            expires_at=2**40,  # far future: not a freshness test
            **gov,
        )
    )
    claimed = DispatchSpool(str(tmp_path / "s"), "secret").claim_next()
    assert claimed is not None
    _claim_token, envelope = claimed  # contract: (claim_token, envelope)
    assert "writable_path_scope=['app/main.py']" in envelope.governance_constraints


def test_envelope_without_scope_is_quarantined_even_when_signed(tmp_path):
    """Negative control (F-2): valid HMAC is not enough — authority must exist."""
    from substrate.execution.attempts.spool import DispatchEnvelope, DispatchSpool

    spool = DispatchSpool(str(tmp_path / "s"), "secret")
    spool.enqueue(
        DispatchEnvelope(
            dispatch_id="d1",
            attempt_id="ea1",
            nonce="n1",
            sequence=1,
            worktree_path=str(tmp_path),
            expires_at=2**40,
            governance_constraints=[],
        )
    )
    assert DispatchSpool(str(tmp_path / "s"), "secret").claim_next() is None


def test_scope_widened_after_signing_is_quarantined(tmp_path):
    """Negative control: constraints are inside the HMAC, so widening breaks it."""
    from substrate.execution.attempts.spool import DispatchEnvelope, DispatchSpool

    gov = _selfcheck().canonical_governance_fields(["app/main.py"])
    root = tmp_path / "s"
    spool = DispatchSpool(str(root), "secret")
    spool.enqueue(
        DispatchEnvelope(
            dispatch_id="d1",
            attempt_id="ea1",
            nonce="n1",
            sequence=1,
            worktree_path=str(tmp_path),
            expires_at=2**40,
            **gov,
        )
    )

    records = sorted((root / "inbox").glob("*.json"))
    assert records, "no inbox record written"
    for path in records:
        record = json.loads(path.read_text())
        record["envelope"]["governance_constraints"] = ["writable_path_scope=['/']"]
        path.write_text(json.dumps(record))

    assert DispatchSpool(str(root), "secret").claim_next() is None


def test_widen_helper_fails_closed_when_no_record_exists(tmp_path):
    """The widening probe must not pass vacuously on an empty/relocated spool."""
    assert _selfcheck()._widen_scope_on_disk(tmp_path / "absent") is False
