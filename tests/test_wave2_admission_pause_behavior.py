"""Wave 2 — the same-run pre-dispatch pause suppresses ADMISSION, fail-closed.

Why this exists
---------------
The failure-qualification pass needs to arm an exact failure policy AFTER the
grant and execution binding are durable but BEFORE any Task is admitted. The
full scenario previously ran authorization straight into dispatch: the control
plane turned a freshly-ACTIVE grant into signed envelopes on the same cycle, so
the arming window was zero-width and cross-run binding reuse is (correctly)
refused, leaving no workaround.

The correction is a run-scoped marker checked at ADMISSION — not at dispatch.
Two designs were tried and abandoned, and BOTH are pinned as regressions here:

  1. returning silently from the dispatch fn: the scheduler transitions an
     attempt to DISPATCHED *before* invoking dispatch, so the attempt is
     stranded in DISPATCHED holding a lease with no envelope;
  2. raising from the dispatch fn: DISPATCHED may only go to
     RUNNING/FAILED/CANCELLED — never back to BLOCKED — so the recovery CAS
     refuses and the conflict is swallowed. Stranded again.

Gating admission means no Attempt, assignment, or lease is ever created, so
there is nothing to unwind and no post-dispatch rollback is needed.

These tests drive the REAL ``FieldControlPlaneDriver.run_cycle()`` over the real
scheduler, real signed spool, real CAS store and real WorkPacket queue. Only the
worker is stubbed (contract-faithful, no CLI, no quota) — exactly like the
existing driver suite, whose fixtures are imported rather than re-created so
this suite cannot drift from the shipped path.
"""

from __future__ import annotations

import json
import os

import pytest

from substrate.execution.attempts.field_failure_policy import (
    arm_pause_before_dispatch,
    dispatch_is_paused,
    pause_marker_path,
    pause_state,
    release_pause_before_dispatch,
)
from substrate.execution.attempts.field_scenario_map import (
    ExecutionBinding,
    write_execution_binding,
)
from substrate.execution.attempts.records import ExecutionAttemptStatus
from substrate.execution.attempts.spool import DispatchSpool

# Reuse the SHIPPED driver suite's fixtures/helpers verbatim: same real driver
# composition, same real queue/store/spool, same contract-faithful stub worker.
from tests.test_wave2_field_control_plane import (
    _RUN_SECRET,
    _add_approved_packet,
    _driver,
    _grant,
    _seed_active_grant,
    _stub_worker_drain,
)

_S = ExecutionAttemptStatus

_RUN_ID = "20260728T000000Z"
_SHA = "4a5217aafc6dd16e4320f8d843d186e4fb0a7c50"
_GRANT_ID = "grant-abc123"
_DECISION_REF = "objective_plan:opr-1:execution_authorization:v1"


# ── fixtures ─────────────────────────────────────────────────────────────────
#
# Defined locally (rather than imported from the driver suite) so the fixture
# names do not shadow this module's test parameters. They build the SAME real
# objects the shipped driver suite builds — a real CAS-backed
# ``ExecutionAttemptStore`` and a real ``UniversalWorkQueue`` — so these tests
# still exercise the production composition, not a stand-in.


@pytest.fixture()
def store(tmp_path):
    from substrate.execution.attempts.store import ExecutionAttemptStore

    return ExecutionAttemptStore(
        attempts_path=str(tmp_path / "a.jsonl"),
        grants_path=str(tmp_path / "g.jsonl"),
        readiness_path=str(tmp_path / "r.jsonl"),
        leases_path=str(tmp_path / "l.jsonl"),
        assignments_path=str(tmp_path / "asn.jsonl"),
    )


@pytest.fixture()
def queue(tmp_path, monkeypatch):
    from substrate.organism.universal_work_queue import UniversalWorkQueue

    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("UMH_ROOT", str(tmp_path / "repo"))
    (tmp_path / "repo").mkdir(exist_ok=True)
    return UniversalWorkQueue(store_path=str(tmp_path / "packets.jsonl"))


# ── helpers ──────────────────────────────────────────────────────────────────


def _binding(**over):
    """The run's captured execution binding (identifiers only)."""
    kw = dict(
        run_id=_RUN_ID,
        candidate_sha=_SHA,
        plan_record_id="opr-1",
        plan_version=1,
        grant_id=_GRANT_ID,
        decision_ref=_DECISION_REF,
        tenant_id="tenant-a",
        principal_id="u",
        membership_id="m",
        conversation_id="conv-1",
        correlation_id="conv-1",
    )
    kw.update(over)
    return ExecutionBinding(**kw)


def _targets(tmp_path, *, binding=None):
    """A per-run targets dir with a durable execution binding, like the field run."""
    d = tmp_path / "targets" / _RUN_ID
    d.mkdir(parents=True, exist_ok=True)
    write_execution_binding(str(d), binding or _binding())
    return str(d)


def _spool(tmp_path):
    return DispatchSpool(str(tmp_path / "spool"), _RUN_SECRET)


def _rows(path):
    """Every durable row in a store JSONL (absent file == no rows).

    Reading the DURABLE files rather than an in-memory view is deliberate: it
    proves nothing was persisted, which is the claim that matters for quota.
    """
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _attempts(tmp_path):
    return _rows(str(tmp_path / "a.jsonl"))


def _leases(tmp_path):
    return _rows(str(tmp_path / "l.jsonl"))


def _assignments(tmp_path):
    return _rows(str(tmp_path / "asn.jsonl"))


def _two_lane_graph(queue):
    """A (backend, frontend) → integration graph, all APPROVED."""
    _add_approved_packet(queue, "wp-backend", plan_record_id="opr-1")
    _add_approved_packet(queue, "wp-frontend", plan_record_id="opr-1")
    _add_approved_packet(
        queue, "wp-integration", deps=["wp-backend", "wp-frontend"], plan_record_id="opr-1"
    )
    return ["wp-backend", "wp-frontend", "wp-integration"]


def _canonical_four_task_graph(queue):
    """The exact A/B → C → D shape the graph-shape gate accepts.

    Same construction as the shipped shape-gate tests: two distinct-scope
    implementation lanes, an integration Task that fans them in, and a
    zero-write verifier depending on integration.
    """
    _add_approved_packet(queue, "A", allowed_paths=("app/main.py",), plan_record_id="opr-1")
    _add_approved_packet(queue, "B", allowed_paths=("app/static",), plan_record_id="opr-1")
    _add_approved_packet(
        queue, "C", deps=["A", "B"], allowed_paths=("app",), plan_record_id="opr-1"
    )
    _add_approved_packet(queue, "D", deps=["C"], allowed_paths=(), plan_record_id="opr-1")
    return ["A", "B", "C", "D"]


def _envelope_files(spool_root):
    """Every dispatch envelope ever written, across all spool states."""
    out = []
    for sub in ("inbox", "inflight", "processed"):
        d = os.path.join(spool_root, sub)
        if os.path.isdir(d):
            out.extend(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".json"))
    return out


# ── 1. pause before admission ────────────────────────────────────────────────


def test_paused_run_creates_no_attempt_lease_assignment_or_envelope(store, queue, tmp_path):
    """The load-bearing invariant: a paused run spends ZERO quota.

    Proves the pause precedes Attempt creation, DISPATCHED transition, assignment
    creation, lease acquisition, worker creation, and envelope publication — by
    asserting the observable ledger/spool state is completely empty after a real
    driver cycle over a valid, ACTIVE, correctly-shaped grant.
    """
    targets = _targets(tmp_path)
    frontier = _two_lane_graph(queue)
    grant = _grant(frontier)
    _seed_active_grant(store, grant)
    arm_pause_before_dispatch(targets)

    spool = _spool(tmp_path)
    driver = _driver(store, queue, spool, tmp_path, targets_dir=targets)
    reports = driver.run_cycle()

    # Nothing was admitted anywhere in the canonical ledger.
    assert _attempts(tmp_path) == [], "a paused run created an Attempt"
    assert _leases(tmp_path) == [], "a paused run acquired a lease"
    assert _assignments(tmp_path) == [], "a paused run created an assignment"
    assert _envelope_files(str(tmp_path / "spool")) == [], "a paused run published an envelope"
    assert all(not r.admitted for r in reports)
    # And the pause is reported diagnosably rather than silently.
    assert any("paused_before_dispatch" in e for r in reports for e in r.errors)


def test_pause_does_not_break_graph_shape_or_polling(store, queue, tmp_path):
    """Polling continues and the graph remains valid while paused.

    A pause must not look like a malformed graph or a dead control plane.
    """
    targets = _targets(tmp_path)
    frontier = _canonical_four_task_graph(queue)
    _seed_active_grant(store, _grant(frontier))
    arm_pause_before_dispatch(targets)

    spool = _spool(tmp_path)
    driver = _driver(store, queue, spool, tmp_path, targets_dir=targets, enforce_graph_shape=True)
    reports = driver.run_cycle()

    # The cycle ran (the grant was picked up) and reported the pause, NOT a
    # graph-shape refusal — the shape gate is independent and still satisfied.
    assert reports, "control plane stopped polling while paused"
    assert not any("graph_shape" in e for r in reports for e in r.errors)
    assert _attempts(tmp_path) == []


def test_pause_is_not_reported_as_a_completed_pass(store, queue, tmp_path):
    """A paused pass must never read as 'finished, nothing to do'."""
    targets = _targets(tmp_path)
    _seed_active_grant(store, _grant(_two_lane_graph(queue)))
    arm_pause_before_dispatch(targets)

    driver = _driver(store, queue, _spool(tmp_path), tmp_path, targets_dir=targets)
    reports = driver.run_cycle()

    for r in reports:
        assert not r.admitted
        assert any("paused_before_dispatch" in e for e in r.errors), (
            "a paused cycle reported no pause reason — indistinguishable from idle"
        )
        # A paused grant is NOT idle: idle means "no work left", paused means
        # "work deliberately withheld". Reporting idle here would tell the
        # operator (and reconciliation) the run had finished.
        assert r.idle is False, "a paused cycle reported a FALSE IDLE state"


# ── 2. result draining while paused ──────────────────────────────────────────


def test_results_still_drain_while_paused_and_no_new_work_admitted(store, queue, tmp_path):
    """A pause must never strand an already-dispatched worker's result.

    Dispatch A and B unpaused, let the stub worker finish, THEN pause and cycle:
    the terminal results are still collected and reconciled, while zero new work
    (the dependent integration Task) is admitted.
    """
    targets = _targets(tmp_path)
    frontier = _two_lane_graph(queue)
    _seed_active_grant(store, _grant(frontier))
    spool = _spool(tmp_path)
    driver = _driver(store, queue, spool, tmp_path, targets_dir=targets)

    # Unpaused: admit + dispatch the independent lanes.
    driver.run_cycle()
    dispatched = _attempts(tmp_path)
    assert dispatched, "precondition failed: nothing dispatched before pausing"
    # Worker finishes its work while we are about to pause.
    assert _stub_worker_drain(spool) > 0

    # Now pause, then cycle: results must still be drained.
    arm_pause_before_dispatch(targets)
    reports = driver.run_cycle()

    assert sum(r.results_drained for r in reports) > 0, "a pause stranded worker results"
    # No result was left un-applied: nothing is still sitting in DISPATCHED.
    stuck = [a for a in _attempts(tmp_path) if a.get("status") == _S.DISPATCHED.value]
    assert stuck == [], f"results stranded in DISPATCHED while paused: {stuck}"
    # And the dependent Task was NOT admitted despite its deps progressing.
    assert not any(a.get("task_id") == "wp-integration" for a in _attempts(tmp_path)), (
        "a paused run admitted new work after draining results"
    )


def test_paused_drain_does_not_treat_worker_output_as_proof(store, queue, tmp_path):
    """Draining while paused reconciles truthfully — success still needs verification."""
    targets = _targets(tmp_path)
    _seed_active_grant(store, _grant(_two_lane_graph(queue)))
    spool = _spool(tmp_path)
    driver = _driver(store, queue, spool, tmp_path, targets_dir=targets)

    driver.run_cycle()
    _stub_worker_drain(spool)
    arm_pause_before_dispatch(targets)
    driver.run_cycle()

    for a in _attempts(tmp_path):
        if a.get("status") == _S.SUCCEEDED.value:
            assert a.get("proof_id"), "an attempt reached SUCCEEDED with no proof while paused"


# ── 3. same-run binding ──────────────────────────────────────────────────────


def test_marker_from_another_run_does_not_release_this_run(store, queue, tmp_path):
    """A foreign marker must not be honored as this run's pause.

    Fail-closed direction matters: an unmatched marker still PAUSES (refusing to
    release is always safe). What must NOT happen is a foreign marker being
    silently accepted as a valid pause for this run's grant.
    """
    targets = _targets(tmp_path)
    arm_pause_before_dispatch(targets)

    # Rewrite the marker as though it came from a different run + grant + SHA.
    foreign = {
        "kind": "pause_before_dispatch",
        "run_id": "20990101T000000Z",
        "candidate_sha": "0" * 40,
        "grant_id": "grant-other",
        "decision_ref": "objective_plan:opr-9:execution_authorization:v1",
        "plan_record_id": "opr-9",
        "plan_version": 1,
    }
    pause_marker_path(targets).write_text(json.dumps(foreign), encoding="utf-8")

    paused, reason = pause_state(targets)
    assert paused, "a foreign marker must still fail closed"
    assert "does not match this run" in reason
    # It is NOT accepted as this run's legitimate pause…
    assert not reason.startswith("paused before dispatch")
    # …and therefore cannot be released by this run.
    released, detail = release_pause_before_dispatch(targets)
    assert released is False
    assert "refusing to release" in detail


@pytest.mark.parametrize("field", ["run_id", "candidate_sha", "grant_id", "decision_ref"])
def test_every_binding_field_is_load_bearing(tmp_path, field):
    """Each identifier is individually checked — none is decorative."""
    targets = _targets(tmp_path)
    arm_pause_before_dispatch(targets)

    data = json.loads(pause_marker_path(targets).read_text(encoding="utf-8"))
    data[field] = "tampered-value"
    pause_marker_path(targets).write_text(json.dumps(data), encoding="utf-8")

    paused, reason = pause_state(targets)
    assert paused
    assert field in reason and "does not match this run" in reason


def test_arming_requires_a_real_execution_binding(tmp_path):
    """A pause that cannot name its grant is refused at arm time."""
    bare = tmp_path / "targets" / "no-binding"
    bare.mkdir(parents=True)
    with pytest.raises(ValueError, match="execution_binding"):
        arm_pause_before_dispatch(str(bare))


def test_pause_is_scoped_to_its_own_targets_dir(tmp_path):
    """Two runs' markers are physically independent (per-run targets dir)."""
    run_a = _targets(tmp_path / "a")
    run_b_dir = tmp_path / "b" / "targets" / "run-b"
    run_b_dir.mkdir(parents=True)
    write_execution_binding(str(run_b_dir), _binding(run_id="run-b", grant_id="grant-b"))

    arm_pause_before_dispatch(run_a)

    assert dispatch_is_paused(run_a) is True
    assert dispatch_is_paused(str(run_b_dir)) is False, "one run's pause blocked another run"


# ── 4. fail-closed state ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "content,expect",
    [
        ("", "not parseable JSON"),
        ("{", "not parseable JSON"),
        ("null", "not a JSON object"),
        ("[]", "not a JSON object"),
        ('"paused"', "not a JSON object"),
        ('{"kind": "something_else"}', "unexpected kind"),
        ('{"kind": "pause_before_dispatch"}', "incomplete"),
        ('{"kind": "pause_before_dispatch", "run_id": "x"}', "incomplete"),
    ],
)
def test_malformed_marker_fails_closed_with_a_reason(tmp_path, content, expect):
    """Unreadable/malformed/incomplete/wrong-schema all SUPPRESS admission."""
    targets = _targets(tmp_path)
    pause_marker_path(targets).write_text(content, encoding="utf-8")

    paused, reason = pause_state(targets)
    assert paused is True, f"marker {content!r} failed OPEN"
    assert expect in reason, f"reason {reason!r} did not explain the refusal"


def test_unreadable_marker_fails_closed(tmp_path):
    """An unreadable marker suppresses admission rather than opening.

    chmod is useless here — this campaign runs as root, where 0o000 is still
    readable, so a permission-based test would SKIP and leave the fail-closed
    path unverified. A directory at the marker path makes the read raise
    IsADirectoryError (an OSError) for any user, root included.
    """
    targets = _targets(tmp_path)
    os.mkdir(pause_marker_path(targets))  # exists() is True, read_text() raises

    paused, reason = pause_state(targets)
    assert paused is True
    assert "unreadable" in reason


def test_unreadable_marker_cannot_be_released(tmp_path):
    """An unreadable marker is not silently destroyed by a release."""
    targets = _targets(tmp_path)
    os.mkdir(pause_marker_path(targets))

    released, detail = release_pause_before_dispatch(targets)
    assert released is False
    assert "refusing to release" in detail
    assert pause_marker_path(targets).exists()


def test_unreadable_marker_suppresses_real_admission(store, queue, tmp_path):
    """The fail-closed path is proven through the REAL driver, not just the helper."""
    targets = _targets(tmp_path)
    _seed_active_grant(store, _grant(_two_lane_graph(queue)))
    os.mkdir(pause_marker_path(targets))

    driver = _driver(store, queue, _spool(tmp_path), tmp_path, targets_dir=targets)
    driver.run_cycle()

    assert _attempts(tmp_path) == [], "an unreadable pause marker failed OPEN in the driver"
    assert _envelope_files(str(tmp_path / "spool")) == []


def test_interrupted_write_cannot_leave_a_half_marker(tmp_path):
    """Arming is atomic: a partial file is never observable at the marker path."""
    targets = _targets(tmp_path)
    arm_pause_before_dispatch(targets)
    # The temp file used during the atomic write must not survive…
    assert not pause_marker_path(targets).with_suffix(".tmp").exists()
    # …and the marker itself always parses.
    data = json.loads(pause_marker_path(targets).read_text(encoding="utf-8"))
    assert data["kind"] == "pause_before_dispatch"


def test_unstattable_path_fails_closed(tmp_path):
    """`Path.exists()` CAN raise — and when it does, the gate must fail closed.

    This is not hypothetical: probing the reachable shapes shows
    ``exists()`` raises ``OSError(ENAMETOOLONG)`` for an over-long path and
    ``TypeError`` for a non-path targets_dir, while broken symlinks, symlink
    loops, ENOTDIR parents and embedded NULs all return False. The two raising
    shapes are exactly what the ``except`` around the existence check exists for
    — without it, an unstattable path would read as "no marker" and ADMIT.
    """
    # ENAMETOOLONG — a single path component past the filesystem limit.
    too_long = str(tmp_path / ("x" * 5000))
    paused, reason = pause_state(too_long)
    assert paused is True, "an unstattable (too-long) path failed OPEN"
    assert "unreadable" in reason

    # TypeError — a targets_dir that is not a path at all.
    paused, reason = pause_state(12345)  # type: ignore[arg-type]
    assert paused is True, "a non-path targets_dir failed OPEN"
    assert "unreadable" in reason


def test_unstattable_path_cannot_be_released(tmp_path):
    """Release refuses when it cannot even determine pause state.

    Both raising shapes are covered: an over-long path (Path() accepts the
    string, exists() raises OSError) AND a non-path targets_dir (Path() itself
    raises TypeError). The second only fails closed if the construction is
    INSIDE the guard, so it pins the construction order on the release path too.
    """
    released, detail = release_pause_before_dispatch(str(tmp_path / ("x" * 5000)))
    assert released is False
    assert "unreadable" in detail

    released, detail = release_pause_before_dispatch(12345)  # type: ignore[arg-type]
    assert released is False, "a non-path targets_dir was 'released'"
    assert "unreadable" in detail


def test_missing_binding_at_check_time_fails_closed(tmp_path):
    """If the binding disappears after arming, the gate refuses rather than opens."""
    targets = _targets(tmp_path)
    arm_pause_before_dispatch(targets)
    os.remove(os.path.join(targets, "execution_binding.json"))

    paused, reason = pause_state(targets)
    assert paused is True
    assert "binding absent" in reason


def test_a_paused_driver_stays_paused_across_repeated_cycles(store, queue, tmp_path):
    """The pause is not a one-shot: repeated cycles keep spending zero quota."""
    targets = _targets(tmp_path)
    _seed_active_grant(store, _grant(_two_lane_graph(queue)))
    arm_pause_before_dispatch(targets)
    driver = _driver(store, queue, _spool(tmp_path), tmp_path, targets_dir=targets)

    for _ in range(3):
        driver.run_cycle()

    assert _attempts(tmp_path) == []
    assert _envelope_files(str(tmp_path / "spool")) == []


# ── 5. release ───────────────────────────────────────────────────────────────


def test_release_then_admission_resumes_with_exactly_one_attempt_per_task(store, queue, tmp_path):
    """After release, normal scheduling resumes — exactly once per Task."""
    targets = _targets(tmp_path)
    _seed_active_grant(store, _grant(_two_lane_graph(queue)))
    spool = _spool(tmp_path)
    driver = _driver(store, queue, spool, tmp_path, targets_dir=targets)

    arm_pause_before_dispatch(targets)
    driver.run_cycle()
    assert _attempts(tmp_path) == []

    released, detail = release_pause_before_dispatch(targets)
    assert released is True and detail == "pause released"
    assert not pause_marker_path(targets).exists(), "a stale pause marker survived release"

    driver.run_cycle()
    attempts = _attempts(tmp_path)
    assert attempts, "admission did not resume after release"
    # Exactly one initial attempt per admitted task — no duplicate dispatch.
    for task_id in {a.get("task_id") for a in attempts}:
        firsts = [
            a
            for a in attempts
            if a.get("task_id") == task_id and int(a.get("attempt_number") or 1) == 1
        ]
        assert len(firsts) == 1, f"{task_id} got {len(firsts)} initial attempts"


def test_second_release_is_refused(tmp_path):
    """A duplicate resume must not look like it re-authorized the run."""
    targets = _targets(tmp_path)
    arm_pause_before_dispatch(targets)

    assert release_pause_before_dispatch(targets)[0] is True
    released, detail = release_pause_before_dispatch(targets)
    assert released is False
    assert "nothing to release" in detail


def test_release_of_another_runs_marker_is_refused(tmp_path):
    """Release is run-scoped: it refuses a marker bound to a different run."""
    targets = _targets(tmp_path)
    arm_pause_before_dispatch(targets)
    data = json.loads(pause_marker_path(targets).read_text(encoding="utf-8"))
    data["run_id"] = "some-other-run"
    pause_marker_path(targets).write_text(json.dumps(data), encoding="utf-8")

    released, detail = release_pause_before_dispatch(targets)
    assert released is False
    assert "refusing to release" in detail
    assert pause_marker_path(targets).exists(), "a foreign marker was destroyed"


def test_release_without_a_pause_is_refused(tmp_path):
    """Releasing an unpaused run reports honestly rather than claiming success."""
    targets = _targets(tmp_path)
    released, detail = release_pause_before_dispatch(targets)
    assert released is False
    assert "not paused" in detail


# ── 6/7. abandoned designs stay abandoned (regression pins) ──────────────────


def test_pause_gate_is_not_implemented_inside_the_dispatch_fn(store, queue, tmp_path):
    """Regression pin for BOTH abandoned designs.

    If the gate ever moves back into the dispatch function, the scheduler will
    have already transitioned the attempt to DISPATCHED before the refusal, so an
    Attempt would exist after a paused cycle. Asserting zero attempts is exactly
    the condition that both abandoned designs fail.
    """
    targets = _targets(tmp_path)
    _seed_active_grant(store, _grant(_two_lane_graph(queue)))
    arm_pause_before_dispatch(targets)

    driver = _driver(store, queue, _spool(tmp_path), tmp_path, targets_dir=targets)
    driver.run_cycle()

    assert _attempts(tmp_path) == [], (
        "an Attempt exists after a paused cycle — the gate regressed to the "
        "dispatch fn, where DISPATCHED can never be unwound"
    )
    # Nothing can be stranded because nothing was ever created.
    assert _leases(tmp_path) == []


def test_no_attempt_is_left_in_dispatched_by_a_pause(store, queue, tmp_path):
    """The stranding failure mode itself, stated directly."""
    targets = _targets(tmp_path)
    _seed_active_grant(store, _grant(_two_lane_graph(queue)))
    spool = _spool(tmp_path)
    driver = _driver(store, queue, spool, tmp_path, targets_dir=targets)

    driver.run_cycle()  # unpaused: real dispatch happens
    arm_pause_before_dispatch(targets)
    _stub_worker_drain(spool)
    driver.run_cycle()  # paused: results drain, nothing new admitted

    stranded = [a for a in _attempts(tmp_path) if a.get("status") == _S.DISPATCHED.value]
    assert stranded == [], f"pause stranded attempts in DISPATCHED: {stranded}"


# ── CLI seam (the operator-visible sequence) ─────────────────────────────────


@pytest.fixture()
def dispatch_mod():
    from tests.wave2_script_import import load_wave2_script

    return load_wave2_script("wave2_field_dispatch")


class _RealRunner:
    dry_run = False


@pytest.mark.parametrize(
    "subcommand",
    ["write-scenario-map", "pause-before-dispatch", "inject-failure", "resume"],
)
def test_cli_subcommand_is_really_dispatchable(dispatch_mod, monkeypatch, subcommand):
    """Each step is a REAL registered subcommand that reaches its handler.

    Asserting on source text would pass even if the subcommand were never
    registered with argparse — so this drives ``main()`` and proves the handler
    is actually invoked. ``--dry-run`` keeps it side-effect free.
    """
    called = {}

    def _spy(name):
        def fn(*a, **kw):
            called["cmd"] = name
            return {"ok": True}

        return fn

    monkeypatch.setattr(dispatch_mod, "_resolve_env", lambda: None)
    monkeypatch.setattr(dispatch_mod, "_candidate_sha", lambda s: _SHA)
    monkeypatch.setattr(dispatch_mod, "write_scenario_map", _spy("write-scenario-map"))
    monkeypatch.setattr(dispatch_mod, "pause_before_dispatch", _spy("pause-before-dispatch"))
    monkeypatch.setattr(dispatch_mod, "inject_failure", _spy("inject-failure"))
    monkeypatch.setattr(dispatch_mod, "resume_after_pause", _spy("resume"))

    rc = dispatch_mod.main(["--dry-run", "--run-id", _RUN_ID, subcommand])

    assert rc == 0, f"{subcommand} did not exit cleanly"
    assert called.get("cmd") == subcommand, (
        f"{subcommand} is not registered/dispatched — handler never ran"
    )


def test_cli_pause_refuses_without_an_execution_binding(dispatch_mod, tmp_path, monkeypatch):
    """`pause-before-dispatch` fails closed when the run binding is absent.

    A pause armed before the binding exists could not name the grant it
    protects, so it is refused with remediation rather than armed blindly.
    """
    bare = tmp_path / "targets" / _RUN_ID
    bare.mkdir(parents=True)
    monkeypatch.setattr(dispatch_mod, "_targets_dir", lambda sha, run_id: bare)

    out = dispatch_mod.pause_before_dispatch(_RealRunner(), _SHA, _RUN_ID)
    assert out["paused"] is False
    assert "execution_binding" in out["refused"]
    assert "write-scenario-map" in out["remediation"]
    assert not pause_marker_path(str(bare)).exists()


def test_cli_pause_then_resume_round_trip(dispatch_mod, tmp_path, monkeypatch):
    """arm → observe paused → release → observe resumed, through the CLI functions."""
    targets = _targets(tmp_path)
    monkeypatch.setattr(
        dispatch_mod, "_targets_dir", lambda sha, run_id: __import__("pathlib").Path(targets)
    )
    monkeypatch.setattr(dispatch_mod, "_read_state_records", lambda sha: [])

    armed = dispatch_mod.pause_before_dispatch(_RealRunner(), _SHA, _RUN_ID)
    assert armed["paused"] is True
    # The CLI echoes the binding it bound the pause to — not a bare boolean.
    assert armed["run_id"] == _RUN_ID
    assert armed["grant_id"] == _GRANT_ID
    assert armed["decision_ref"] == _DECISION_REF
    assert armed["candidate_sha"] == _SHA
    assert dispatch_is_paused(targets) is True

    out = dispatch_mod.resume_after_pause(_RealRunner(), _SHA, _RUN_ID)
    assert out["released"] is True
    assert dispatch_is_paused(targets) is False


def test_cli_second_resume_is_refused(dispatch_mod, tmp_path, monkeypatch):
    """A duplicate resume never reports success."""
    targets = _targets(tmp_path)
    monkeypatch.setattr(
        dispatch_mod, "_targets_dir", lambda sha, run_id: __import__("pathlib").Path(targets)
    )
    monkeypatch.setattr(dispatch_mod, "_read_state_records", lambda sha: [])

    dispatch_mod.pause_before_dispatch(_RealRunner(), _SHA, _RUN_ID)
    assert dispatch_mod.resume_after_pause(_RealRunner(), _SHA, _RUN_ID)["released"] is True
    second = dispatch_mod.resume_after_pause(_RealRunner(), _SHA, _RUN_ID)
    assert second["released"] is False
    assert "nothing to release" in second["detail"]


def test_cli_resume_reports_unarmed_failure_policy(dispatch_mod, tmp_path, monkeypatch):
    """Resuming without a valid armed policy is reported, not silently accepted.

    Releasing unarmed wastes the whole window the pause exists to create — the
    run would proceed and the failure pass would silently run clean.
    """
    targets = _targets(tmp_path)
    monkeypatch.setattr(
        dispatch_mod, "_targets_dir", lambda sha, run_id: __import__("pathlib").Path(targets)
    )
    monkeypatch.setattr(dispatch_mod, "_read_state_records", lambda sha: [])

    dispatch_mod.pause_before_dispatch(_RealRunner(), _SHA, _RUN_ID)
    out = dispatch_mod.resume_after_pause(_RealRunner(), _SHA, _RUN_ID)
    # No variant armed == a CLEAN run, which is legitimately valid; the field is
    # present so the operator can SEE the arming verdict before proceeding.
    assert "arming_valid" in out and "arming" in out


# ── 8. cleanup ───────────────────────────────────────────────────────────────


def test_no_residual_pause_marker_after_release(tmp_path):
    """Zero residual pause state after a normal arm→release cycle."""
    targets = _targets(tmp_path)
    arm_pause_before_dispatch(targets)
    release_pause_before_dispatch(targets)

    assert not pause_marker_path(targets).exists()
    assert not pause_marker_path(targets).with_suffix(".tmp").exists()
    assert dispatch_is_paused(targets) is False


def test_pause_leaves_no_runtime_residue(store, queue, tmp_path):
    """A paused cycle leaves no leases, assignments, envelopes or spool entries."""
    targets = _targets(tmp_path)
    _seed_active_grant(store, _grant(_two_lane_graph(queue)))
    arm_pause_before_dispatch(targets)

    driver = _driver(store, queue, _spool(tmp_path), tmp_path, targets_dir=targets)
    driver.run_cycle()

    assert _attempts(tmp_path) == []
    assert _leases(tmp_path) == []
    assert _assignments(tmp_path) == []
    assert _envelope_files(str(tmp_path / "spool")) == []
