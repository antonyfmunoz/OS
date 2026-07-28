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
    satisfy a new one. Asserted through the REAL function (the old version
    string-matched `pid_tag = f"pid={proc.pid} "`, which M6 defeated by rebinding
    pid_tag on a later line while leaving that exact string in place)."""
    f = _dispatch_mod().runner_readiness_announced
    stale = "control-plane driver up: pid=111 run_root=/r\n"
    assert f(stale, 111) is True
    assert f(stale, 222) is False, "a stale log satisfied a different process"


def test_b2_control_plane_failure_is_bounded():
    """The unbounded `(continuing)` log must not return, and the policy must be
    real state rather than an inline counter a mutant can silently break."""
    src = open(
        os.path.join(REPO, "scripts", "wave2_attempt_runner.py"), encoding="utf-8"
    ).read()
    assert "control-plane cycle error (continuing)" not in src, "the unbounded log survives"
    mod = _runner_mod()
    assert hasattr(mod, "ControlPlaneFailureBudget")


# ── R9 independent-review findings (NEW-1/2/3) ───────────────────────────────


@pytest.mark.parametrize(
    "bad_key", ["a/b", "../../etc/passwd", "x\ny", "..", "/abs/path"]
)
def test_new1_a_malformed_record_cannot_steer_its_own_quarantine_path(tmp_path, bad_key):
    """NEW-1, introduced BY the B5 fix and found by independent review.

    `_quarantine` built the destination as `f"{name}.{reason}"` with only spaces
    replaced. B5 started embedding the raw exception text, and
    `DispatchEnvelope(**record)` puts the attacker-supplied KEY NAME verbatim
    into the TypeError. A key containing "/" produced a destination whose parent
    does not exist; os.replace raised FileNotFoundError, which was SWALLOWED, so
    the function logged "quarantined" and did nothing. The record cycled
    inflight<->inbox forever and the evidence trail was destroyed.
    """
    import json

    sp = _spool(tmp_path)
    inbox = os.path.join(str(tmp_path), "inbox")
    os.makedirs(inbox, exist_ok=True)
    with open(os.path.join(inbox, "00000000-poison.json"), "w", encoding="utf-8") as f:
        json.dump({"envelope": {"dispatch_id": "p", bad_key: 1}, "signature": "x"}, f)

    assert sp.claim_next() is None
    quarantined = os.listdir(os.path.join(str(tmp_path), "quarantine"))
    assert quarantined, f"key {bad_key!r} escaped quarantine — evidence lost"
    leftover = [
        n for n in os.listdir(os.path.join(str(tmp_path), "inflight"))
        if n.endswith(".json")
    ]
    assert not leftover, f"key {bad_key!r} left the record stuck in inflight"
    for q in quarantined:
        assert "/" not in q


def test_new1_the_reason_slug_is_bounded_and_safe():
    from substrate.execution.attempts.spool import DispatchSpool as _S

    slug = _S._reason_slug("a/b ../c\nd" + "z" * 500)  # noqa: SLF001
    assert "/" not in slug and "\n" not in slug and " " not in slug
    assert len(slug) <= 120
    assert _S._reason_slug("") == "unspecified"  # noqa: SLF001


def test_new2_the_runner_actually_calls_heartbeat_claim():
    """NEW-2: heartbeat_claim() had ZERO production callers, so a worker running
    longer than the recovery threshold still had its claim re-queued underneath
    it — the B4 duplicate-dispatch outcome on a longer fuse."""
    import ast

    path = os.path.join(REPO, "scripts", "wave2_attempt_runner.py")
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src, filename=path)

    reachable_calls = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "heartbeat_claim"
    ]
    assert reachable_calls, "heartbeat_claim is still a dead API"

    def _statically_false(node) -> bool:
        """More than ast.Constant: R9's surviving mutant was
        `if False and not spool.heartbeat_claim(tok):` — an ast.BoolOp that
        short-circuits the call away while a Constant-only check called it live."""
        if isinstance(node, ast.Constant):
            return not node.value
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
            return any(_statically_false(v) for v in node.values)
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            return all(_statically_false(v) for v in node.values)
        return False

    dead = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and _statically_false(node.test):
            for part in [node.test, *node.body]:
                for sub in ast.walk(part):
                    if isinstance(sub, ast.Call):
                        dead.add(id(sub))
    live = [c for c in reachable_calls if id(c) not in dead]
    assert live, "every heartbeat_claim call sits under a statically-false guard"


def test_new3_a_failed_claim_stamp_refuses_the_claim(tmp_path, monkeypatch):
    """NEW-3: if os.utime fails the claim keeps the INBOX mtime and we are back
    to the pre-fix CRITICAL. The degradation mode of a Critical fix must fail
    closed, not hand a worker an unstamped claim."""
    sp = _spool(tmp_path)
    sp.enqueue(_envelope())
    import substrate.execution.attempts.spool as spool_mod

    real_utime = os.utime

    def boom(path, times=None):
        if "inflight" in str(path):
            raise OSError("stamp failed")
        return real_utime(path, times)

    monkeypatch.setattr(spool_mod.os, "utime", boom)
    assert sp.claim_next() is None, "an unstamped claim was handed to a worker"


# ── NEW-4 (round 2): tests that call the REAL code, not a replay ─────────────
#
# Round 1 of this section replayed the launcher/runner logic inside the test.
# Independent review (R9) then killed 6 of 9 mutants against it:
#   M1 `_CP_MAX_* = 10**9`        -- the regex `(\d+)` matched "10", not "10**9"
#   M2 launcher body -> `if True:` -- a replay cannot see the real body change
#   M3 `cp_consecutive_errors += 0` -- a replay never runs the real accounting
#   M4 reset moved into `except`   -- ditto
#   M6 `pid_tag` rebound after the asserted line
#   M9 `if False and not spool.heartbeat_claim(tok):` -- a BoolOp, not a Constant
#
# All six are real gaps: observable behavior differs (bound fires at cycle 5 vs
# 20; any pid accepted; a live claim stolen). The fix is structural — the
# decisions now live in named, importable units (`runner_readiness_announced`,
# `ControlPlaneFailureBudget`) and these tests drive THOSE. Values are read by
# importing the module, so a non-decimal literal cannot slip past a regex.


def _dispatch_mod():
    from tests.wave2_script_import import load_wave2_script

    return load_wave2_script("wave2_field_dispatch")


def _runner_mod():
    from tests.wave2_script_import import load_wave2_script

    return load_wave2_script("wave2_attempt_runner")


@pytest.mark.parametrize(
    "name,body,pid,expected",
    [
        ("driver up for THIS pid", "control-plane driver up: pid=4242 run_root=/r\n", 4242, True),
        ("worker-only for THIS pid", "runner ready worker-only: pid=4242 run_root=/r\n", 4242, True),
        ("stale log from ANOTHER pid", "control-plane driver up: pid=999 run_root=/r\n", 4242, False),
        ("legacy pre-driver marker", "runner up: spool=/s primitive=bwrap\n", 4242, False),
        ("startup marker only", "runner starting: pid=4242 run_root=/r\n", 4242, False),
        ("driver FAILED, nothing after", "runner starting: pid=4242\nFATAL: driver unavailable\n", 4242, False),
        ("pid prefix collision", "control-plane driver up: pid=42424 run_root=/r\n", 4242, False),
        ("stale then ours", "control-plane driver up: pid=999\ncontrol-plane driver up: pid=4242 r\n", 4242, True),
        ("empty log", "", 4242, False),
    ],
)
def test_b1_the_real_launcher_decision(name, body, pid, expected):
    """Calls the launcher's OWN function. Gutting its body to `if True:` or
    rebinding pid_tag now fails here (M2, M6)."""
    assert _dispatch_mod().runner_readiness_announced(body, pid) is expected, name


def test_b1_start_runner_uses_that_function():
    """Pin that start_runner actually delegates to it — an extracted helper that
    nothing calls would be the NEW-2 mistake all over again."""
    import ast

    path = os.path.join(REPO, "scripts", "wave2_field_dispatch.py")
    tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
    fn = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "start_runner"
    )
    calls = [
        n for n in ast.walk(fn)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "runner_readiness_announced"
    ]
    assert calls, "start_runner no longer uses runner_readiness_announced"


def test_b2_the_real_budget_bounds_a_hard_down_driver():
    """Drives the runner's OWN accounting object. `+= 0` (M3) now fails here."""
    mod = _runner_mod()
    b = mod.ControlPlaneFailureBudget(
        mod._CP_MAX_CONSECUTIVE_ERRORS, mod._CP_MAX_TOTAL_ERRORS
    )
    fired_at = None
    for cycle in range(1, 5000):
        b.record_failure(RuntimeError("driver down"))
        if b.exhausted:
            fired_at = cycle
            break
    assert fired_at == mod._CP_MAX_CONSECUTIVE_ERRORS, (
        f"hard-down driver terminated at cycle {fired_at}, "
        f"expected {mod._CP_MAX_CONSECUTIVE_ERRORS}"
    )


def test_b2_the_real_budget_bounds_a_flapping_driver():
    """Alternating success/failure keeps resetting the consecutive counter, so
    only the TOTAL bound can stop it. A reset placed in the wrong branch (M4)
    changes when this fires."""
    mod = _runner_mod()
    b = mod.ControlPlaneFailureBudget(
        mod._CP_MAX_CONSECUTIVE_ERRORS, mod._CP_MAX_TOTAL_ERRORS
    )
    failures = 0
    fired = False
    for cycle in range(20000):
        if cycle % 2:
            b.record_success()
        else:
            b.record_failure(RuntimeError("flap"))
            failures += 1
        if b.exhausted:
            fired = True
            break
    assert fired, "a flapping driver never terminated"
    assert failures == mod._CP_MAX_TOTAL_ERRORS, (
        f"flapping driver stopped after {failures} failures, "
        f"expected {mod._CP_MAX_TOTAL_ERRORS}"
    )


def test_b2_a_success_never_clears_the_total_budget():
    """record_success() must clear ONLY the consecutive counter — otherwise a
    driver that succeeds once per N failures is unbounded forever."""
    mod = _runner_mod()
    b = mod.ControlPlaneFailureBudget(5, 20)
    b.record_failure(RuntimeError("x"))
    b.record_success()
    assert b.consecutive == 0
    assert b.total == 1, "a success wrongly cleared the cumulative budget"


def test_b2_a_healthy_run_never_exhausts_the_budget():
    mod = _runner_mod()
    b = mod.ControlPlaneFailureBudget(5, 20)
    for _ in range(10000):
        b.record_success()
    assert not b.exhausted


def test_b2_the_bounds_are_actually_reachable():
    """Read by IMPORT, not regex: `_CP_MAX_* = 10**9` (M1) is caught here,
    where a decimal-only regex scrape read it as 10 and passed."""
    mod = _runner_mod()
    assert 0 < mod._CP_MAX_CONSECUTIVE_ERRORS <= 20
    assert 0 < mod._CP_MAX_TOTAL_ERRORS <= 200
    assert mod._HEARTBEAT_SECONDS < mod._INFLIGHT_RECOVERY_SECONDS / 2


def test_b2_the_terminal_return_reaches_the_teardown():
    """`return 3` must unwind through the try whose finally sweeps credentials."""
    import ast

    path = os.path.join(REPO, "scripts", "wave2_attempt_runner.py")
    tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
    guarded = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Try) and node.finalbody:
            returns_3 = [
                n for n in ast.walk(node)
                if isinstance(n, ast.Return)
                and isinstance(n.value, ast.Constant)
                and n.value.value == 3
            ]
            if returns_3 and "_run_teardown" in " ".join(
                ast.dump(f) for f in node.finalbody
            ):
                guarded = True
    assert guarded, "the bounded-failure return 3 does not unwind through the teardown"
