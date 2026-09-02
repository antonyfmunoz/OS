"""Bounded grant-durability wait: the early-read race, and its fail-closed bounds.

``_wait_collector_authorization`` returns when the collector REACHES stage 15,
not when the execution-authorization grant its journey causes is durable on
disk. Field run ``20260805T070430Z-p1`` read at 00:05:23; the grant landed at
00:05:37 — a 14-second early read that refused with "0 execution-authorization
grants carry exact correlation_id 'w2-20260805T070430Z-p1'". The grant was
CORRECT: replaying the same binding against it once persisted bound it
successfully (``exgrant-f6fee9350df0``).

The fix polls the REAL consumer — ``_capture_execution_binding``, the exact
function ``write_scenario_map`` uses — so the wait can never accept anything the
gate would reject. Durable AND unique AND ACTIVE AND exact-correlation are all
proven by the gate itself, never by a re-implementation of its rules.

These tests pin the five required cases: early-read race, delayed durability,
timeout, ambiguity, and wrong correlation. No field quota is spent.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

DISPATCH = Path(REPO) / "scripts" / "wave2_field_dispatch.py"
RUN_ID = "20260805T070430Z-p1"
SHA = "87ea03dfc60ab6aece56151ebb7d8b191520a8f9"
WANTED = f"w2-{RUN_ID}"


@pytest.fixture(scope="module")
def dispatch_mod():
    """The REAL dispatcher module (its binding function is the predicate)."""
    sys.argv = ["wave2_field_dispatch.py"]
    for name in ("substrate", "substrate.execution", "substrate.execution.attempts"):
        __import__(name)
    spec = importlib.util.spec_from_file_location("_wfd_durability", str(DISPATCH))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_wfd_durability"] = mod
    spec.loader.exec_module(mod)
    return mod


def _grant(correlation=WANTED, status="active", gid="exgrant-f6fee9350df0"):
    return {
        "grant_id": gid,
        "task_frontier": ["wp-a", "wp-b"],
        "correlation_id": correlation,
        "status": status,
        "plan_record_id": "opr-b445759d2e3c",
        "plan_version": 1,
        "decision_ref": "objective_plan:opr-b445759d2e3c:execution_authorization:v1",
        "tenant_id": "t",
        "principal_id": "p",
        "membership_id": "m",
        "conversation_id": "c",
    }


def _make_wait(dispatch_mod):
    """The driver's wait, bound to the real consumer.

    Mirrors the frozen driver's ``wait_for_bindable_grant`` exactly: it polls
    ``_capture_execution_binding`` and carries the gate's own refusal reason.
    """

    def wait_for_bindable_grant(*, read_records, sha, run_id, timeout_s, interval_s, clock, sleep):
        deadline = clock() + timeout_s
        last = "no attempt made"
        while clock() < deadline:
            binding, err = dispatch_mod._capture_execution_binding(
                read_records(), sha=sha, run_id=run_id
            )
            if binding is not None:
                return binding, ""
            last = err or "unknown refusal"
            sleep(interval_s)
        return None, f"grant not bindable within {timeout_s:.0f}s: {last}"

    return wait_for_bindable_grant


class _Clock:
    """Deterministic clock — no real sleeping in tests."""

    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, dt):
        self.t += dt


# ── 1. the early-read race (the observed field failure) ─────────────────────


def test_early_read_would_refuse_without_the_wait(dispatch_mod):
    """Reading before the grant is durable refuses — this is the race itself."""
    binding, err = dispatch_mod._capture_execution_binding([], sha=SHA, run_id=RUN_ID)
    assert binding is None
    assert "0 execution-authorization grants" in err


def test_wait_survives_the_early_read_and_binds_when_durable(dispatch_mod):
    """DELAYED DURABILITY: the grant appears after several polls; the wait binds it.

    This is the exact field timeline — empty ledger, then the run's grant lands.
    """
    wait = _make_wait(dispatch_mod)
    clock = _Clock()
    state = {"polls": 0}

    def read_records():
        state["polls"] += 1
        # grant becomes durable on the 5th read (~12s at 3s intervals)
        return [_grant()] if state["polls"] >= 5 else []

    binding, err = wait(
        read_records=read_records,
        sha=SHA,
        run_id=RUN_ID,
        timeout_s=300.0,
        interval_s=3.0,
        clock=clock,
        sleep=clock.sleep,
    )
    assert binding is not None, f"the wait must bind once the grant is durable: {err}"
    assert binding.correlation_id == WANTED
    assert binding.grant_id == "exgrant-f6fee9350df0"
    assert state["polls"] >= 5, "the wait must actually poll, not read once"
    assert clock.t < 300.0, "must bind well inside the bound"


def test_wait_binds_immediately_when_already_durable(dispatch_mod):
    """No artificial delay when the grant is already on disk."""
    wait = _make_wait(dispatch_mod)
    clock = _Clock()
    binding, err = wait(
        read_records=lambda: [_grant()],
        sha=SHA,
        run_id=RUN_ID,
        timeout_s=300.0,
        interval_s=3.0,
        clock=clock,
        sleep=clock.sleep,
    )
    assert binding is not None and err == ""
    assert clock.t == 0.0, "an already-durable grant must not cost a sleep"


# ── 2. fail-closed bounds ───────────────────────────────────────────────────


def test_wait_times_out_fail_closed_when_grant_never_lands(dispatch_mod):
    """TIMEOUT: a grant that never appears must REFUSE, never pass."""
    wait = _make_wait(dispatch_mod)
    clock = _Clock()
    binding, err = wait(
        read_records=lambda: [],
        sha=SHA,
        run_id=RUN_ID,
        timeout_s=30.0,
        interval_s=3.0,
        clock=clock,
        sleep=clock.sleep,
    )
    assert binding is None, "a grant that never lands must fail CLOSED"
    assert "not bindable within 30s" in err
    assert "0 execution-authorization grants" in err, (
        "the timeout must carry the gate's own last refusal, not a generic message"
    )
    assert clock.t >= 30.0, "the wait must actually honour its bound"


def test_wait_refuses_ambiguity_and_never_picks_one(dispatch_mod):
    """AMBIGUITY: two grants with the same correlation must refuse, not choose."""
    wait = _make_wait(dispatch_mod)
    clock = _Clock()
    binding, err = wait(
        read_records=lambda: [_grant(gid="g1"), _grant(gid="g2")],
        sha=SHA,
        run_id=RUN_ID,
        timeout_s=15.0,
        interval_s=3.0,
        clock=clock,
        sleep=clock.sleep,
    )
    assert binding is None, "an ambiguous match must never be resolved by picking one"
    assert "2 execution-authorization grants" in err


def test_wait_refuses_wrong_correlation(dispatch_mod):
    """WRONG CORRELATION: another run's grant must never satisfy this run.

    Includes the pre-fix intent_* shape and the old doubled-suffix shape.
    """
    wait = _make_wait(dispatch_mod)
    for corr in ("intent_f14c647c77bd", f"{WANTED}-p1", "w2-20260101T000000Z-p1"):
        clock = _Clock()
        binding, err = wait(
            read_records=lambda c=corr: [_grant(correlation=c)],
            sha=SHA,
            run_id=RUN_ID,
            timeout_s=9.0,
            interval_s=3.0,
            clock=clock,
            sleep=clock.sleep,
        )
        assert binding is None, f"correlation {corr!r} must NOT bind to run {RUN_ID}"
        assert "0 execution-authorization grants" in err


def test_wait_refuses_wrong_status(dispatch_mod):
    """A matching but non-ACTIVE grant must refuse (revoked/expired/activating)."""
    wait = _make_wait(dispatch_mod)
    for status in ("revoked", "expired", "activating", "invalidated"):
        clock = _Clock()
        binding, err = wait(
            read_records=lambda s=status: [_grant(status=s)],
            sha=SHA,
            run_id=RUN_ID,
            timeout_s=9.0,
            interval_s=3.0,
            clock=clock,
            sleep=clock.sleep,
        )
        assert binding is None, f"a {status!r} grant must not bind"
        assert "not ACTIVE" in err


def test_a_late_correct_grant_still_binds_after_wrong_ones(dispatch_mod):
    """A wrong-correlation grant present early must not poison a later correct one."""
    wait = _make_wait(dispatch_mod)
    clock = _Clock()
    state = {"n": 0}

    def read_records():
        state["n"] += 1
        other = _grant(correlation="intent_f14c647c77bd", gid="g-other")
        return [other] if state["n"] < 4 else [other, _grant()]

    binding, err = wait(
        read_records=read_records,
        sha=SHA,
        run_id=RUN_ID,
        timeout_s=60.0,
        interval_s=3.0,
        clock=clock,
        sleep=clock.sleep,
    )
    assert binding is not None, f"the run's own grant must bind despite a foreign one: {err}"
    assert binding.correlation_id == WANTED


# ── 3. the driver must actually use it, before write_scenario_map ───────────


FROZEN = Path("/opt/OS/data/audits/proof/2026-08-05_wave2_field/frozen_driver/failpass_frozen.py")


@pytest.mark.skipif(not FROZEN.exists(), reason="frozen driver not present")
def test_frozen_driver_waits_before_writing_the_scenario_map():
    """Ordering is the property: the wait must precede write_scenario_map.

    A wait that runs AFTER the map is written would be decorative — the early
    read would already have refused.
    """
    import ast

    src = FROZEN.read_text(encoding="utf-8")
    tree = ast.parse(src)

    wait_call = None
    map_call = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "id", "") or getattr(node.func, "attr", "")
            if name == "wait_for_bindable_grant" and wait_call is None:
                wait_call = node.lineno
            if name == "write_scenario_map" and map_call is None:
                map_call = node.lineno

    assert wait_call is not None, "the frozen driver must call wait_for_bindable_grant"
    assert map_call is not None, "the frozen driver must call write_scenario_map"
    assert wait_call < map_call, (
        f"the durability wait (line {wait_call}) must run BEFORE write_scenario_map "
        f"(line {map_call}) — otherwise the early read still refuses"
    )

    # `_binding` must be assigned DIRECTLY from the wait call. Binding it from a
    # literal (while calling the wait separately into a throwaway name) is not a
    # wait — it is the early-read race, restored.
    binding_from_wait = False
    for n in ast.walk(tree):
        if not isinstance(n, ast.Assign):
            continue
        names = []
        for t in n.targets:
            names.extend(
                [e.id for e in t.elts if isinstance(e, ast.Name)]
                if isinstance(t, ast.Tuple)
                else ([t.id] if isinstance(t, ast.Name) else [])
            )
        if "_binding" in names and isinstance(n.value, ast.Call):
            if getattr(n.value.func, "id", "") == "wait_for_bindable_grant":
                binding_from_wait = True
    assert binding_from_wait, (
        "_binding must be assigned directly from wait_for_bindable_grant(...); a "
        "literal assignment means the wait no longer gates the scenario map"
    )


@pytest.mark.skipif(not FROZEN.exists(), reason="frozen driver not present")
def test_frozen_driver_fails_closed_on_wait_refusal():
    """A refused wait must ABORT the run, never fall through to the map.

    Structural, not substring: the mutant that replaces the guard body with
    ``pass`` keeps both ``if _binding is None:`` and the word ``die(`` present
    elsewhere in the file, so a text search cannot see it. The guard's BODY must
    actually abort.
    """
    import ast

    tree = ast.parse(FROZEN.read_text(encoding="utf-8"))
    guards = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.If)
        and isinstance(n.test, ast.Compare)
        and isinstance(n.test.left, ast.Name)
        and n.test.left.id == "_binding"
    ]
    assert guards, "the driver must guard on the wait's result (_binding)"
    for g in guards:
        aborts = any(
            isinstance(n, ast.Raise)
            or (isinstance(n, ast.Call) and getattr(n.func, "id", "") == "die")
            for n in ast.walk(g)
        )
        assert aborts, (
            "a refused wait must ABORT (die/raise) inside the guard body — "
            "falling through proceeds without a binding, which is fail-OPEN"
        )


@pytest.mark.skipif(not FROZEN.exists(), reason="frozen driver not present")
def test_frozen_driver_wait_is_bounded():
    """The wait must carry a finite timeout — never poll forever."""
    import ast

    tree = ast.parse(FROZEN.read_text(encoding="utf-8"))
    timeout = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "GRANT_WAIT_TIMEOUT_S":
                    timeout = ast.literal_eval(node.value)
    assert timeout is not None, "the wait timeout must be an explicit named bound"
    assert 0 < timeout <= 900, f"timeout {timeout} must be finite and reasonable"


@pytest.mark.skipif(not FROZEN.exists(), reason="frozen driver not present")
def test_frozen_driver_polls_the_real_consumer_not_a_copy():
    """The wait must call the REAL binding function.

    Re-implementing the predicate is the failure mode this guards: a copy could
    drift and accept something the gate rejects.
    """
    import ast

    tree = ast.parse(FROZEN.read_text(encoding="utf-8"))
    fn = next(
        (
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == "wait_for_bindable_grant"
        ),
        None,
    )
    assert fn is not None, "the frozen driver must define wait_for_bindable_grant"
    calls_consumer = any(
        isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "_capture_execution_binding"
        for n in ast.walk(fn)
    )
    assert calls_consumer, (
        "the wait body must CALL the real _capture_execution_binding — a "
        "re-implemented predicate can accept what the gate rejects"
    )
