"""C-5 — one typed QualificationVerdict governs BOTH report and process exit.

The Round-2 CRITICAL: ``wave2_field_dispatch.py`` computed its exit status from an
ad-hoc allowlist (``_result_declares_failure``) that only knew a handful of
generic gate keys. It never inspected ``reconcile``'s ``all_passed`` nor
``teardown``'s ``run_secret_shredded`` — so a reconciliation scoring 0.0, a
reconciliation with ZERO passes, and a teardown that FAILED to shred the run
secret all exited 0. A caller reading only the exit code would treat any of those
as a green field pass.

C-5 replaces the allowlist with ONE typed ``QualificationVerdict`` that is both
embedded in the JSON report and consumed for the exit status, so the report can
never disagree with the exit code. This suite pins every mandatory predicate and,
for each fail-open behaviour, MUTATION-TESTS it: restore the old lenient rule and
prove the suite goes red.

Owner C-5 closure bar (each is a test below):
  1. one typed verdict controls report + exit          → test_verdict_drives_both_report_and_exit
  2. empty/missing reconciliation is failure            → test_empty_reconcile_*
  3. reconciliation below threshold is failure          → test_reconcile_below_threshold_fails
  4. any mandatory predicate false is failure           → test_single_false_gate_fails_whole_verdict
  5. armed injection that did not fire is failure        → test_armed_false_is_failure  (+ inject invalid)
  6. secret-shred / teardown failure is failure          → test_teardown_unshredded_secret_fails
  7. all_passed cannot override an independently-failed gate → test_all_passed_cannot_override_failed_pass
  8. teardown runs after failure but can't convert it    → test_teardown_after_failure_cannot_greenwash
  9. nested layers preserve the nonzero code             → test_main_returns_3_on_failed_reconcile / _teardown
 10. mutation tests independently restore each fail-open  → the test_mutation_* trio
"""

from __future__ import annotations

import pytest

from tests.wave2_script_import import load_wave2_script

wd = load_wave2_script("wave2_field_dispatch")


def _zero_ref_proof() -> dict:
    return {
        "ok": True,
        "zero_ref_residue": True,
        "ref_residue": [],
        "ref_inventory": [],
        "ref_enumeration_executed": True,
        "unexpected_ref_count": 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1 + 4 — the verdict object itself
# ─────────────────────────────────────────────────────────────────────────────
def test_verdict_is_a_frozen_typed_object():
    v = wd.qualification_verdict("preflight", {"ready": True})
    assert isinstance(v, wd.QualificationVerdict)
    assert v.command == "preflight"
    assert v.ok is True
    # frozen — identity fields cannot be reassigned after construction.
    with pytest.raises(Exception):
        v.ok = False  # type: ignore[misc]


def test_verdict_to_dict_round_trips_for_the_report():
    v = wd.qualification_verdict("reconcile", {"passes": [{"passed": True}], "all_passed": True})
    d = v.to_dict()
    assert d["command"] == "reconcile"
    assert d["ok"] is True
    assert "mandatory" in d and "reasons" in d


def test_single_false_gate_fails_whole_verdict():
    # A single mandatory gate at False fails the verdict regardless of others.
    v = wd.qualification_verdict("deploy-candidate", {"deploy_ok": False})
    assert v.ok is False
    assert any("deploy_ok" in r for r in v.reasons)


def test_missing_gate_key_is_not_a_failure():
    # A command that reports no verdict key keeps exiting 0 (unchanged behaviour).
    v = wd.qualification_verdict("seed-fixture", {"fixture": "written"})
    assert v.ok is True


def test_dry_run_is_never_graded_as_failure():
    # dry-run asserts no side effects; it must never be a qualification failure.
    v = wd.qualification_verdict("reconcile", {"dry_run": True})
    assert v.ok is True


# ─────────────────────────────────────────────────────────────────────────────
# 2 — empty / missing reconciliation is failure  (THE core C-5 defect)
# ─────────────────────────────────────────────────────────────────────────────
def test_empty_reconcile_passes_list_is_failure():
    v = wd.qualification_verdict("reconcile", {"passes": [], "all_passed": False})
    assert v.ok is False
    assert v.mandatory.get("reconcile:nonempty") is False
    assert any("ZERO passes" in r for r in v.reasons)


def test_missing_reconcile_passes_key_is_failure():
    v = wd.qualification_verdict("reconcile", {"sha": "abc"})
    assert v.ok is False
    assert v.mandatory.get("reconcile:nonempty") is False


def test_reconcile_all_passed_true_but_no_passes_still_fails():
    # Even a (contradictory) all_passed=True cannot rescue an empty reconciliation.
    v = wd.qualification_verdict("reconcile", {"passes": [], "all_passed": True})
    assert v.ok is False


def test_reconcile_malformed_pass_entry_cannot_qualify():
    v = wd.qualification_verdict("reconcile", {"passes": [None], "all_passed": True})
    assert v.ok is False
    assert v.mandatory.get("reconcile:passes_well_formed") is False
    assert v.mandatory.get("reconcile:every_pass_passed") is False
    assert any("malformed pass" in r for r in v.reasons)


# ─────────────────────────────────────────────────────────────────────────────
# 3 — reconciliation below threshold is failure
# ─────────────────────────────────────────────────────────────────────────────
def test_reconcile_below_threshold_fails():
    # reconcile() sets passed=False when score<0.90; the verdict must honour it.
    out = {
        "passes": [{"run_tag": "r1", "score": 0.42, "passed": False}],
        "all_passed": False,
    }
    v = wd.qualification_verdict("reconcile", out)
    assert v.ok is False
    assert v.mandatory.get("reconcile:every_pass_passed") is False


def test_reconcile_zero_score_pass_fails():
    out = {"passes": [{"run_tag": "r1", "score": 0.0, "passed": False}], "all_passed": False}
    v = wd.qualification_verdict("reconcile", out)
    assert v.ok is False


def test_reconcile_all_green_passes():
    out = {
        "passes": [
            {"run_tag": "r1", "score": 0.97, "passed": True},
            {"run_tag": "r2", "score": 0.99, "passed": True},
            {"run_tag": "r3", "score": 0.95, "passed": True},
        ],
        "all_passed": True,
    }
    v = wd.qualification_verdict("reconcile", out)
    assert v.ok is True


# ─────────────────────────────────────────────────────────────────────────────
# 7 — all_passed cannot override an independently-failed gate
# ─────────────────────────────────────────────────────────────────────────────
def test_all_passed_cannot_override_failed_pass():
    # A tampered summary claiming all_passed=True while a pass failed must FAIL.
    out = {
        "passes": [
            {"run_tag": "r1", "score": 0.97, "passed": True},
            {"run_tag": "r2", "score": 0.10, "passed": False},
        ],
        "all_passed": True,  # lie
    }
    v = wd.qualification_verdict("reconcile", out)
    assert v.ok is False
    assert v.mandatory.get("reconcile:every_pass_passed") is False


def test_all_passed_false_alone_fails_even_if_passes_look_ok():
    # Defensive: a False all_passed flag is itself a mandatory gate.
    out = {"passes": [{"run_tag": "r1", "passed": True}], "all_passed": False}
    v = wd.qualification_verdict("reconcile", out)
    assert v.ok is False
    assert v.mandatory.get("reconcile:all_passed_flag") is False


# ─────────────────────────────────────────────────────────────────────────────
# 6 — teardown / secret-shred failure is failure
# ─────────────────────────────────────────────────────────────────────────────
def test_teardown_unshredded_secret_fails():
    out = {
        "run_id": "r1",
        "torn_down": ["c1", "c2"],
        "run_secret_shredded": False,
        "serve_restored": True,
    }
    v = wd.qualification_verdict("teardown", out)
    assert v.ok is False
    assert v.mandatory.get("teardown:secret_shredded") is False
    assert any("shred" in r.lower() for r in v.reasons)


def test_teardown_missing_secret_shred_proof_fails():
    out = {
        "run_id": "r1",
        "torn_down": ["c1", "c2"],
        "serve_restored": True,
    }
    v = wd.qualification_verdict("teardown", out)
    assert v.ok is False
    assert v.mandatory.get("teardown:secret_shredded") is False
    assert any("not positively proven" in r for r in v.reasons)


def test_teardown_missing_run_binding_fails():
    out = {
        "torn_down": ["c1", "c2"],
        "collector": {"stopped": True},
        "run_secret_shredded": True,
        "serve_restored": True,
        "homes_swept": _zero_ref_proof(),
    }
    v = wd.qualification_verdict("teardown", out)
    assert v.ok is False
    assert v.mandatory.get("teardown:run_id_bound") is False
    assert any("run binding" in r for r in v.reasons)


def test_teardown_serve_not_restored_fails():
    out = {"run_id": "r1", "run_secret_shredded": True, "serve_restored": False}
    v = wd.qualification_verdict("teardown", out)
    assert v.ok is False
    assert v.mandatory.get("teardown:serve_restored") is False


def test_teardown_unknown_serve_restore_fails():
    out = {"run_id": "r1", "run_secret_shredded": True}
    v = wd.qualification_verdict("teardown", out)
    assert v.ok is False
    assert v.mandatory.get("teardown:serve_restored") is False
    assert any("serve restoration" in r.lower() for r in v.reasons)


def test_teardown_clean_passes():
    out = {
        "run_id": "r1",
        "torn_down": ["c1", "c2"],
        "collector": {"stopped": True},
        "run_secret_shredded": True,
        "serve_restored": True,
        # SEC-C1 residue proof + the zero-ref-residue proof: a CLEAN teardown
        # must show BOTH. Omitting zero_ref_residue is treated as unproven.
        "homes_swept": _zero_ref_proof(),
    }
    v = wd.qualification_verdict("teardown", out)
    assert v.ok is True


def test_teardown_zero_ref_boolean_without_inventory_fails():
    out = {
        "run_id": "r1",
        "torn_down": ["c1", "c2"],
        "collector": {"stopped": True},
        "run_secret_shredded": True,
        "serve_restored": True,
        "homes_swept": {"ok": True, "zero_ref_residue": True, "ref_residue": []},
    }
    v = wd.qualification_verdict("teardown", out)
    assert v.ok is False
    assert v.mandatory.get("teardown:zero_ref_residue") is False
    assert any("enumerated=False" in r for r in v.reasons)


def test_teardown_zero_ref_requires_positive_enumeration_flag():
    proof = _zero_ref_proof()
    proof["ref_enumeration_executed"] = False
    out = {
        "run_id": "r1",
        "torn_down": ["c1", "c2"],
        "collector": {"stopped": True},
        "run_secret_shredded": True,
        "serve_restored": True,
        "homes_swept": proof,
    }
    v = wd.qualification_verdict("teardown", out)
    assert v.ok is False
    assert v.mandatory.get("teardown:zero_ref_residue") is False
    assert any("enumerated=False" in r for r in v.reasons)


def test_teardown_with_home_residue_fails():
    # SEC-C1: a teardown that shredded the secret and restored serve but left
    # credential-home residue is STILL a security failure.
    out = {
        "run_id": "r1",
        "run_secret_shredded": True,
        "serve_restored": True,
        "homes_swept": {"ok": False, "errors": ["SECURITY: worker home residue: [...]"]},
    }
    v = wd.qualification_verdict("teardown", out)
    assert v.ok is False
    assert v.mandatory.get("teardown:homes_swept") is False


def test_teardown_missing_homes_swept_fails():
    # A teardown result with no homes_swept key cannot prove clean → failure.
    out = {"run_secret_shredded": True, "serve_restored": True}
    v = wd.qualification_verdict("teardown", out)
    assert v.ok is False
    assert v.mandatory.get("teardown:homes_swept") is False


# ─────────────────────────────────────────────────────────────────────────────
# 5 — armed injection that did not fire is failure
# ─────────────────────────────────────────────────────────────────────────────
def test_armed_false_is_failure():
    # inject-failure returning armed=False (invalid arming) must fail the verdict.
    out = {"armed": False, "variant": "tools-revoked-a", "invalid_reason": "no binding"}
    v = wd.qualification_verdict("inject-failure", out)
    assert v.ok is False


def test_armed_true_passes():
    out = {"armed": True, "variant": "tools-revoked-a", "target_task_id": "wp-1"}
    v = wd.qualification_verdict("inject-failure", out)
    assert v.ok is True


# ─────────────────────────────────────────────────────────────────────────────
# 8 — teardown after failure runs but cannot greenwash the run
# ─────────────────────────────────────────────────────────────────────────────
def test_teardown_after_failure_cannot_greenwash():
    # A teardown that itself succeeded is a PASS for the teardown command — but it
    # is graded per-command, so it can never turn a prior failed reconcile into a
    # success. Prove the two verdicts are independent and the failed one stays failed.
    recon = wd.qualification_verdict(
        "reconcile", {"passes": [{"passed": False}], "all_passed": False}
    )
    tear = wd.qualification_verdict(
        "teardown",
        {
            "run_id": "r1",
            "collector": {"stopped": True},
            "run_secret_shredded": True,
            "serve_restored": True,
            "homes_swept": _zero_ref_proof(),
        },
    )
    assert recon.ok is False
    assert tear.ok is True  # teardown ran cleanly...
    assert recon.ok is False  # ...but the reconcile verdict is untouched by it.


# ─────────────────────────────────────────────────────────────────────────────
# 9 — the exit code is driven by the SAME verdict (nested layers preserve it)
# ─────────────────────────────────────────────────────────────────────────────
def _run_main(monkeypatch, cmd, out, *, extra_argv=None):
    """Drive main() for one command, stubbing the command fn to return `out`."""
    monkeypatch.setattr(wd, "_resolve_env", lambda: None)
    monkeypatch.setattr(wd, "_candidate_sha", lambda s: "deadbeefcafe0000")
    monkeypatch.setattr(wd, "_run_id_default", lambda: "run-x")
    # Stub every side-effecting helper a given command touches.
    monkeypatch.setattr(wd, "reconcile", lambda runner, sha: out)
    monkeypatch.setattr(wd, "teardown", lambda runner, sha="", run_id="": out)
    monkeypatch.setattr(wd, "_load_serve_snapshot_path", lambda sha="": None)
    argv = [cmd] + (extra_argv or [])
    return wd.main(argv)


def test_main_returns_3_on_failed_reconcile(monkeypatch, capsys):
    rc = _run_main(monkeypatch, "reconcile", {"passes": [], "all_passed": False})
    assert rc == 3
    err = capsys.readouterr().err
    assert "NOT QUALIFIED" in err


def test_main_returns_0_on_green_reconcile(monkeypatch):
    out = {"passes": [{"run_tag": "r1", "passed": True}], "all_passed": True}
    rc = _run_main(monkeypatch, "reconcile", out)
    assert rc == 0


def test_main_returns_3_on_unshredded_teardown(monkeypatch, capsys):
    rc = _run_main(
        monkeypatch,
        "teardown",
        {"run_secret_shredded": False, "serve_restored": True},
        extra_argv=[],
    )
    assert rc == 3
    assert "NOT QUALIFIED" in capsys.readouterr().err


def test_main_returns_0_on_clean_teardown(monkeypatch):
    rc = _run_main(
        monkeypatch,
        "teardown",
        {
            "run_id": "r1",
            "collector": {"stopped": True},
            "run_secret_shredded": True,
            "serve_restored": True,
            "homes_swept": _zero_ref_proof(),
        },
    )
    assert rc == 0


def test_main_teardown_does_not_resolve_candidate_origin_before_cleanup(monkeypatch):
    def fail_resolve():
        raise AssertionError("teardown must not resolve candidate origin before cleanup")

    monkeypatch.setattr(wd, "_resolve_env", fail_resolve)
    monkeypatch.setattr(wd, "_candidate_sha", lambda s: "deadbeefcafe0000")
    monkeypatch.setattr(wd, "_load_serve_snapshot_path", lambda sha="": None)
    monkeypatch.setattr(
        wd,
        "teardown",
        lambda runner, sha="", run_id="": {
            "run_id": run_id,
            "collector": {"stopped": True},
            "run_secret_shredded": True,
            "serve_restored": True,
            "homes_swept": _zero_ref_proof(),
        },
    )

    rc = wd.main(["--sha", "deadbeefcafe0000", "--run-id", "run-1", "teardown"])

    assert rc == 0


def test_report_embeds_the_verdict(monkeypatch, capsys):
    # The verdict must be WRITTEN into the report, not merely used for exit — the
    # single-source-of-truth requirement.
    _run_main(monkeypatch, "reconcile", {"passes": [], "all_passed": False})
    out = capsys.readouterr().out
    assert "qualification_verdict" in out
    assert '"ok": false' in out.lower().replace(" ", " ")


# ─────────────────────────────────────────────────────────────────────────────
# 10 — MUTATION TESTS: restore each fail-open behaviour, prove the suite goes red
# ─────────────────────────────────────────────────────────────────────────────
def test_mutation_reconcile_ignoring_all_passed_would_pass_empty():
    """Old behaviour: exit driven only by the generic allowlist, which never read
    'passes'/'all_passed'. Simulate it and prove it green-lit an EMPTY reconcile —
    exactly the defect. The real verdict must reject the same input."""

    def old_result_declares_failure(out):  # the pre-C-5 allowlist, verbatim
        for key in ("deploy_ok", "started", "armed", "ok", "ready"):
            if out.get(key) is False:
                return True
        if out.get("refused") or out.get("invalid_reason"):
            return True
        results = out.get("results")
        if isinstance(results, list) and results:
            if any(isinstance(r, dict) and r.get("ok") is False for r in results):
                return True
        return False

    empty = {"passes": [], "all_passed": False}
    # The OLD rule would have exited 0 (declares_failure == False)...
    assert old_result_declares_failure(empty) is False
    # ...the NEW typed verdict rejects it.
    assert wd.qualification_verdict("reconcile", empty).ok is False


def test_mutation_reconcile_ignoring_all_passed_would_pass_below_threshold():
    def old_result_declares_failure(out):
        for key in ("deploy_ok", "started", "armed", "ok", "ready"):
            if out.get(key) is False:
                return True
        return bool(out.get("refused") or out.get("invalid_reason"))

    below = {"passes": [{"score": 0.0, "passed": False}], "all_passed": False}
    assert old_result_declares_failure(below) is False  # old = false green
    assert wd.qualification_verdict("reconcile", below).ok is False  # new = caught


def test_mutation_teardown_ignoring_shred_would_pass():
    def old_result_declares_failure(out):
        for key in ("deploy_ok", "started", "armed", "ok", "ready"):
            if out.get(key) is False:
                return True
        return bool(out.get("refused") or out.get("invalid_reason"))

    unshredded = {"run_id": "r1", "run_secret_shredded": False, "serve_restored": True}
    assert old_result_declares_failure(unshredded) is False  # old = false green
    assert wd.qualification_verdict("teardown", unshredded).ok is False  # new = caught


def test_backcompat_wrapper_agrees_with_verdict():
    # _result_declares_failure is retained as a thin wrapper; it must equal
    # `not verdict.ok` for every command so no external caller silently diverges.
    cases = [
        ("reconcile", {"passes": [], "all_passed": False}),
        ("reconcile", {"passes": [{"passed": True}], "all_passed": True}),
        ("teardown", {"run_id": "r1", "run_secret_shredded": False, "serve_restored": True}),
        ("teardown", {"run_id": "r1", "run_secret_shredded": True, "serve_restored": True}),
        (
            "teardown",
            {
            "run_id": "r1",
            "run_secret_shredded": True,
            "serve_restored": True,
            "homes_swept": _zero_ref_proof(),
        },
        ),
        ("preflight", {"ready": True}),
        ("deploy-candidate", {"deploy_ok": False}),
        ("inject-failure", {"armed": False, "invalid_reason": "x"}),
    ]
    for cmd, out in cases:
        assert wd._result_declares_failure(out, cmd) is (
            not wd.qualification_verdict(cmd, out).ok
        ), (cmd, out)
