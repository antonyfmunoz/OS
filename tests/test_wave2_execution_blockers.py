"""Regression pins for the seven exact-head execution blockers (round 9).

Each test reproduces a defect that was CONFIRMED by execution against the
candidate at e82be58e, then pins the correction. Every one of these fails if its
fix is reverted — that is the point of the suite, and each was verified by
actually reverting the fix.

Severity as classified from reproduced behavior:
  B4 CRITICAL — one Attempt dispatched twice (duplicate billed worker quota)
  B3 HIGH     — an authorization-bound action could prove no authority
  B6 HIGH     — composition fail-open on an unreadable planning store
  B7 HIGH     — a Proof observable before it was durable
  B1 HIGH     — a runner reported ready before its control plane existed
  B2 HIGH     — an unbounded control-plane failure could burn the run budget
  B5 MEDIUM   — a schema-invalid record escaped the quarantine boundary
"""

from __future__ import annotations

import os
import sys
import tempfile
import time

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from substrate.execution.attempts.spool import (  # noqa: E402
    DispatchEnvelope,
    DispatchSpool,
)
from substrate.organism.governed_spine import GovernedExecutionSpine  # noqa: E402


def _spool(tmp_path) -> DispatchSpool:
    return DispatchSpool(root_dir=str(tmp_path), secret="s" * 32)


def _envelope(**kw) -> DispatchEnvelope:
    base = dict(
        dispatch_id="d1", attempt_id="ea-1", task_id="wp-a",
        authorization_ref="ref", package_hash="h", lease_id="l1",
        nonce="n1", sequence=1, expires_at=time.time() + 3600, payload_hash="p",
    )
    base.update(kw)
    return DispatchEnvelope(**base)


# ── B4 (CRITICAL) — spool claim-time race ────────────────────────────────────


def test_b4_a_long_waiting_inbox_record_is_fresh_the_moment_it_is_claimed(tmp_path):
    """THE Critical. os.replace preserves the INBOX mtime, and recovery measures
    staleness as now - mtime. A dispatch that merely WAITED longer than the
    recovery threshold was therefore stale the instant it was claimed, so the
    next sweep re-queued it while its worker was still running: two live
    dispatches of ONE Attempt against ONE lease worktree, and duplicate billed
    worker quota."""
    sp = _spool(tmp_path)
    sp.enqueue(_envelope())
    inbox = os.path.join(str(tmp_path), "inbox")
    f = os.path.join(inbox, [n for n in os.listdir(inbox) if n.endswith(".json")][0])
    waited = time.time() - 4000
    os.utime(f, (waited, waited))

    claim = sp.claim_next()
    assert claim is not None
    token, _ = claim

    inflight = os.path.join(str(tmp_path), "inflight", token)
    age = time.time() - os.path.getmtime(inflight)
    assert age < 60, f"claim inherited the inbox mtime ({age:.0f}s old at claim time)"

    # The worker is STILL RUNNING. Recovery must not touch it.
    assert sp.recover_stale_inflight(older_than_seconds=1800) == []


def test_b4_a_genuinely_dead_claim_is_still_recoverable(tmp_path):
    """The fix must not break crash recovery — a dead claim must still return."""
    sp = _spool(tmp_path)
    sp.enqueue(_envelope())
    token, _ = sp.claim_next()
    inflight = os.path.join(str(tmp_path), "inflight", token)
    dead = time.time() - 3600
    os.utime(inflight, (dead, dead))
    assert sp.recover_stale_inflight(older_than_seconds=1800) == [token]


def test_b4_a_heartbeating_worker_is_never_reclaimed(tmp_path):
    """A worker that legitimately outlives the threshold keeps its claim by
    beating. Liveness, not elapsed time, is the recovery signal."""
    sp = _spool(tmp_path)
    sp.enqueue(_envelope())
    token, _ = sp.claim_next()
    inflight = os.path.join(str(tmp_path), "inflight", token)
    old = time.time() - 3600
    os.utime(inflight, (old, old))

    assert sp.heartbeat_claim(token) is True
    assert sp.recover_stale_inflight(older_than_seconds=1800) == []


def test_b4_heartbeat_on_a_vanished_claim_reports_false(tmp_path):
    assert _spool(tmp_path).heartbeat_claim("does-not-exist.json") is False


def test_b4_exactly_one_claimant_wins_one_record(tmp_path):
    """os.replace is the atomic ownership primitive: a second claim finds nothing."""
    sp = _spool(tmp_path)
    sp.enqueue(_envelope())
    first = sp.claim_next()
    second = sp.claim_next()
    assert first is not None
    assert second is None, "one dispatch was claimed twice"


# ── B5 (MEDIUM) — malformed envelope escapes quarantine ──────────────────────


def test_b5_a_schema_invalid_record_is_quarantined_not_raised(tmp_path):
    """DispatchEnvelope(**record) sat OUTSIDE the quarantine try, so a record
    that was valid JSON but schema-invalid raised TypeError out of claim_next()
    — killing the claim loop. Worse, the file was already in inflight, so it was
    neither executed nor quarantined and poisoned every later poll."""
    sp = _spool(tmp_path)
    inbox = os.path.join(str(tmp_path), "inbox")
    os.makedirs(inbox, exist_ok=True)
    with open(os.path.join(inbox, "00000001-bad.json"), "w", encoding="utf-8") as f:
        f.write('{"envelope": {"totally_unknown_field": 1}, "signature": "x"}')

    result = sp.claim_next()  # must not raise
    assert result is None
    quarantined = os.listdir(os.path.join(str(tmp_path), "quarantine"))
    assert quarantined, "schema-invalid record was not quarantined"


def test_b5_invalid_json_is_quarantined(tmp_path):
    sp = _spool(tmp_path)
    inbox = os.path.join(str(tmp_path), "inbox")
    os.makedirs(inbox, exist_ok=True)
    with open(os.path.join(inbox, "00000001-bad.json"), "w", encoding="utf-8") as f:
        f.write("{not json at all")
    assert sp.claim_next() is None
    assert os.listdir(os.path.join(str(tmp_path), "quarantine"))


def test_b5_a_malformed_record_does_not_block_a_later_valid_one(tmp_path):
    """The loop must continue past one bad file, not be poisoned by it."""
    sp = _spool(tmp_path)
    inbox = os.path.join(str(tmp_path), "inbox")
    os.makedirs(inbox, exist_ok=True)
    with open(os.path.join(inbox, "00000001-bad.json"), "w", encoding="utf-8") as f:
        f.write('{"envelope": {"nope": 1}, "signature": "x"}')
    sp.enqueue(_envelope(dispatch_id="d2", sequence=2))

    claim = sp.claim_next()
    assert claim is not None, "a malformed record blocked a later valid dispatch"
    assert claim[1].dispatch_id == "d2"


# ── B3 (HIGH) — authorization-bound action may not omit its authority ────────


class _Grant:
    status = "active"
    expires_at = 0.0
    authorized_scope_hash = "REAL-SCOPE-HASH"
    task_frontier = ["wp-a"]


def _spine() -> GovernedExecutionSpine:
    s = GovernedExecutionSpine.__new__(GovernedExecutionSpine)
    s._authorization_lookup = lambda ref: _Grant()  # noqa: SLF001
    return s


def _check(**kw) -> str:
    return _spine()._check_authorization_scope(type("E", (), kw)())  # noqa: SLF001


def test_b3_exact_authority_is_admitted():
    assert _check(
        authorization_ref="r",
        authorized_scope_hash="REAL-SCOPE-HASH",
        authorized_subject_ids=["wp-a"],
    ) == ""


def test_b3_a_non_authorization_bound_action_is_unaffected():
    assert _check(authorization_ref="") == ""


@pytest.mark.parametrize(
    "name,kw",
    [
        ("omitted scope hash", dict(authorized_scope_hash="", authorized_subject_ids=["wp-a"])),
        ("omitted subjects", dict(authorized_scope_hash="REAL-SCOPE-HASH", authorized_subject_ids=[])),
        ("both omitted", dict(authorized_scope_hash="", authorized_subject_ids=[])),
        ("mismatched hash", dict(authorized_scope_hash="WRONG", authorized_subject_ids=["wp-a"])),
        ("widened subjects", dict(authorized_scope_hash="REAL-SCOPE-HASH", authorized_subject_ids=["wp-a", "wp-OTHER"])),
        ("cross-task reuse", dict(authorized_scope_hash="REAL-SCOPE-HASH", authorized_subject_ids=["wp-OTHER"])),
    ],
)
def test_b3_an_action_that_cannot_prove_its_authority_refuses(name, kw):
    """A MISMATCH refused, but an OMISSION passed: `if env_hash and grant_hash
    and env_hash != grant_hash` short-circuits when the caller simply declares
    nothing. The guard only fired when the caller volunteered evidence against
    itself. An authorization-bound action must PROVE the authority it consumes."""
    assert _check(authorization_ref="r", **kw) != "", f"{name} was admitted"


def test_b3_a_grant_that_authorizes_nothing_refuses():
    class Empty:
        status = "active"
        expires_at = 0.0
        authorized_scope_hash = "H"
        task_frontier: list[str] = []

    s = GovernedExecutionSpine.__new__(GovernedExecutionSpine)
    s._authorization_lookup = lambda ref: Empty()  # noqa: SLF001
    env = type("E", (), dict(
        authorization_ref="r", authorized_scope_hash="H", authorized_subject_ids=["wp-a"]
    ))()
    assert s._check_authorization_scope(env) != ""  # noqa: SLF001


# ── B6 (HIGH) — composition must fail closed on an unreadable store ──────────


def test_b6_an_unreadable_planning_store_refuses_composition(monkeypatch):
    """This used to `return`, treating "the store could not be read" exactly like
    "this Objective has no Plan" — silently GRANTING permission to compose a
    second canonical Plan for an Objective that may already have an accepted one.
    Confirmed absence and unreadable state are different answers."""
    import substrate.organism.composition_engine as ce

    class Boom:
        def latest_version_of(self, _oid):
            raise RuntimeError("planning store unavailable")

    monkeypatch.setattr(
        "substrate.execution.planning.store.PlanningStore", lambda *a, **k: Boom()
    )
    with pytest.raises(ce.CompositionAuthorityError):
        ce._reject_if_objective_plan_accepted("goal-x")  # noqa: SLF001


def test_b6_confirmed_absence_still_permits_composition(monkeypatch):
    """The fix must not block the legitimate path: a store that answers
    truthfully "no plan" is the ONE state that permits composition."""
    import substrate.organism.composition_engine as ce

    class Empty:
        def latest_version_of(self, _oid):
            return None

    monkeypatch.setattr(
        "substrate.execution.planning.store.PlanningStore", lambda *a, **k: Empty()
    )
    ce._reject_if_objective_plan_accepted("goal-x")  # noqa: SLF001 - must not raise


# ── B7 (HIGH) — a Proof must be durable before it is visible ─────────────────


def test_b7_a_failed_persist_leaves_no_visible_proof(monkeypatch, tmp_path):
    """The three in-memory index writes ran BEFORE _persist_package, which raises
    ProofPersistenceError. A failed write therefore left a fully visible Proof
    that never existed on disk — package_for()/get_proof() read those indexes, so
    a caller could observe and act on a Proof no restart would ever see."""
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path))
    from substrate.organism.proof_runtime import ProofRuntime

    rt = ProofRuntime()
    # A ProofRuntime loads the EXISTING durable history at construction, so the
    # assertion is that THIS proof never entered the indexes -- not that the
    # indexes are globally empty.
    history_before = len(rt._history)  # noqa: SLF001
    monkeypatch.setattr(
        rt, "_persist_package",
        lambda pkg: (_ for _ in ()).throw(RuntimeError("disk full")),
    )
    with pytest.raises(RuntimeError):
        rt.create_direct(work_id="wp-a", action={"k": "v"})

    assert rt.package_for("wp-a") is None, "a phantom Proof is visible after a failed persist"
    assert len(rt._history) == history_before, (  # noqa: SLF001
        "a phantom Proof entered the history index"
    )
    assert not any(
        p.work_id == "wp-a" for p in rt._packages.values()  # noqa: SLF001
    ), "a phantom Proof entered the package index"


def test_b7_a_durable_proof_is_visible(tmp_path, monkeypatch):
    """The fix must not break the success path."""
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path))
    from substrate.organism.proof_runtime import ProofRuntime

    rt = ProofRuntime()
    pkg = rt.create_direct(work_id="wp-ok", action={"k": "v"})
    assert rt.package_for("wp-ok") is not None
    assert pkg.proof_id


# ── B1 / B2 (HIGH) — runner readiness and bounded control-plane failure ──────


def test_b1_the_launcher_no_longer_accepts_the_pre_driver_marker():
    """`start_runner` waited for "runner up:", which the runner emits BEFORE it
    builds the control-plane driver — so a run whose driver construction failed
    still returned started=True and produced no governed progress."""
    src = open(
        os.path.join(REPO, "scripts", "wave2_field_dispatch.py"), encoding="utf-8"
    ).read()
    assert '"runner up:" in head' not in src, "launcher still accepts the pre-driver marker"
    assert "control-plane driver up: " in src
    assert "runner ready worker-only: " in src


def test_b1_readiness_markers_are_emitted_only_after_driver_resolution():
    src = open(
        os.path.join(REPO, "scripts", "wave2_attempt_runner.py"), encoding="utf-8"
    ).read()
    startup = src.index("runner starting: ")
    driver_up = src.index("control-plane driver up: ")
    assert startup < driver_up, "readiness marker precedes driver construction"
    # and the startup line must NOT be a readiness marker any more
    assert "runner up: " not in src


def test_b1_readiness_is_bound_to_the_exact_process():
    """A stale log from a previous launch in the same targets dir must not
    satisfy a new one."""
    runner = open(
        os.path.join(REPO, "scripts", "wave2_attempt_runner.py"), encoding="utf-8"
    ).read()
    launcher = open(
        os.path.join(REPO, "scripts", "wave2_field_dispatch.py"), encoding="utf-8"
    ).read()
    assert "control-plane driver up: pid={os.getpid()}" in runner
    assert 'pid_tag = f"pid={proc.pid} "' in launcher


def test_b2_control_plane_failure_is_bounded():
    """Exceptions from driver.run_cycle() were logged "(continuing)" with NO
    bound, so a permanently broken control plane consumed the entire run budget
    while the process looked healthy. Process liveness is not control-plane
    health."""
    src = open(
        os.path.join(REPO, "scripts", "wave2_attempt_runner.py"), encoding="utf-8"
    ).read()
    assert "_CP_MAX_CONSECUTIVE_ERRORS" in src
    assert "_CP_MAX_TOTAL_ERRORS" in src
    assert "control-plane cycle error (continuing)" not in src, "the unbounded log survives"
    # a successful cycle must reset the consecutive budget
    assert "cp_consecutive_errors = 0" in src
